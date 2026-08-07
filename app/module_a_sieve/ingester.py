import logging
import time
import uuid
import re
from typing import List, Dict, Any
from app.db.neo4j_client import run_cypher
from app.db.repository import GraphRepository, get_graph_repository
from app.module_a_sieve.schemas import ExtractionOutput, CriticEvaluation, SieveResult
from app.services.entity_resolution import get_entity_resolver

logger = logging.getLogger(__name__)


async def ingest_sieve_output(
    extraction: ExtractionOutput,
    evaluations: List[CriticEvaluation],
    repo: GraphRepository = None
) -> SieveResult:
    """Ingest Critic-verified triples into graph database asynchronously with status 'pending'."""
    if repo is None:
        repo = get_graph_repository()
    
    timestamp = int(time.time())
    processed_records = []
    resolver = await get_entity_resolver()
    
    # Store/Merge Chunk
    chunk_cypher = """
    MERGE (ch:Chunk {id: $chunk_id})
    ON CREATE SET ch.text = $chunk_text, ch.created_at = $timestamp
    """
    await run_cypher(chunk_cypher, {
        "chunk_id": extraction.chunk_id,
        "chunk_text": extraction.chunk_text,
        "timestamp": timestamp
    })

    eval_map = {eval_item.triple_index: eval_item for eval_item in evaluations}

    for idx, triple in enumerate(extraction.triples):
        crit = eval_map.get(idx)
        if not crit or not crit.is_valid:
            logger.info("Triple [%d] rejected by Critic: %s", idx, getattr(crit, 'critique_notes', 'Invalid'))
            continue

        # Apply validated Critic typo corrections to subject/object entity names
        if hasattr(crit, 'typo_corrections') and crit.typo_corrections:
            from app.module_a_sieve.critic import validate_and_apply_typo_corrections
            triple = validate_and_apply_typo_corrections(triple, crit.typo_corrections, extraction.chunk_text)

        edge_id = f"edge_{uuid.uuid4().hex[:10]}"
        rel_type = triple.relation.upper().replace(" ", "_")
        # Target specific injection method: strip backticks to prevent escaping Cypher quotes
        rel_type = rel_type.replace("`", "")
        if not rel_type:
            rel_type = "UNKNOWN_RELATION"
        
        # Bug 7 fix: Force concept_mapping.new_relation to match rel_type so
        # get_pending_queue's OPTIONAL MATCH (c1:Concept {name: type(r)}) finds the mapping
        if triple.concept_mapping:
            triple.concept_mapping.new_relation = rel_type

        # Handle Meta-Graph concept mapping if present
        if triple.concept_mapping:
            mapping_type = triple.concept_mapping.mapping_type.upper().replace(" ", "_")
            mapping_type = mapping_type.replace("`", "")
            if not mapping_type:
                mapping_type = "RELATED_TO"

            concept_cypher = f"""
            MERGE (c1:Concept {{name: $new_relation}})
            MERGE (c2:Concept {{name: $existing_concept}})
            MERGE (c1)-[:`{mapping_type}`]->(c2)
            """
            await run_cypher(concept_cypher, {
                "new_relation": triple.concept_mapping.new_relation,
                "existing_concept": triple.concept_mapping.existing_concept
            })

        # Insert Entities & Dynamic Data-Graph Edge
        ingest_cypher = f"""
        MATCH (ch:Chunk {{id: $chunk_id}})
        
        MERGE (s:Entity {{name: $subj_name}})
        ON CREATE SET s.type = $subj_type
        
        MERGE (o:Entity {{name: $obj_name}})
        ON CREATE SET o.type = $obj_type
        
        MERGE (ch)-[:MENTIONS]->(s)
        MERGE (ch)-[:MENTIONS]->(o)
        
        CREATE (s)-[r:`{rel_type}` {{
            edge_id: $edge_id,
            chunk_id: $chunk_id,
            confidence: $confidence,
            status: "pending",
            approved_by: "",
            timestamp: $timestamp
        }}]->(o)
        RETURN r
        """
        
        params = {
            "subj_name": triple.subject.name,
            "subj_type": triple.subject.type,
            "obj_name": triple.object.name,
            "obj_type": triple.object.type,
            "chunk_id": extraction.chunk_id,
            "edge_id": edge_id,
            "confidence": crit.confidence,
            "timestamp": timestamp
        }

        # Bug 1 fix: Only count triples that actually reach Neo4j
        try:
            db_result = await run_cypher(ingest_cypher, params)
        except Exception as e:
            logger.warning(
                "Failed to ingest triple [%d] edge_id='%s' (%s)-[%s]->(%s): %s",
                idx, edge_id, triple.subject.name, rel_type, triple.object.name, e
            )
            continue

        # Entity Resolution (ER) step: Map raw strings to canonical ontology concept
        subj_res = resolver.resolve_entity(triple.subject.name)
        if subj_res:
            await repo.store_er_mapping(extraction.chunk_id, triple.subject.name, subj_res)

        obj_res = resolver.resolve_entity(triple.object.name)
        if obj_res:
            await repo.store_er_mapping(extraction.chunk_id, triple.object.name, obj_res)

        record = {
            "edge_id": edge_id,
            "subject": triple.subject.model_dump(),
            "relation": rel_type,
            "object": triple.object.model_dump(),
            "chunk_id": extraction.chunk_id,
            "chunk_text": extraction.chunk_text,
            "confidence": crit.confidence,
            "status": "pending",
            "concept_mapping": triple.concept_mapping.model_dump() if triple.concept_mapping else None,
            "subject_resolution": subj_res,
            "object_resolution": obj_res
        }

        processed_records.append(record)

    return SieveResult(
        chunk_id=extraction.chunk_id,
        chunk_text=extraction.chunk_text,
        processed_triples=processed_records
    )

