import logging
import time
import uuid
from typing import List, Dict, Any
from app.db.neo4j_client import run_cypher
from app.module_a_sieve.schemas import ExtractionOutput, CriticEvaluation, SieveResult

from app.db.mock_graph import mock_graph_store

logger = logging.getLogger(__name__)

def ingest_sieve_output(extraction: ExtractionOutput, evaluations: List[CriticEvaluation]) -> SieveResult:
    """Ingest Critic-verified triples into Neo4j with status 'pending' (and mock store)."""
    timestamp = int(time.time())
    processed_records = []
    
    # 1. Store/Merge Chunk
    chunk_cypher = """
    MERGE (ch:Chunk {id: $chunk_id})
    ON CREATE SET ch.text = $chunk_text, ch.created_at = $timestamp
    """
    run_cypher(chunk_cypher, {
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

        edge_id = f"edge_{uuid.uuid4().hex[:10]}"
        rel_type = triple.relation.upper().replace(" ", "_")
        
        # Handle Meta-Graph concept mapping if present
        if triple.concept_mapping:
            concept_cypher = f"""
            MERGE (c1:Concept {{name: $new_relation}})
            MERGE (c2:Concept {{name: $existing_concept}})
            MERGE (c1)-[:{triple.concept_mapping.mapping_type}]->(c2)
            """
            run_cypher(concept_cypher, {
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
        
        CREATE (s)-[r:{rel_type} {{
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

        db_result = run_cypher(ingest_cypher, params)

        record = {
            "edge_id": edge_id,
            "subject": triple.subject.model_dump(),
            "relation": rel_type,
            "object": triple.object.model_dump(),
            "chunk_id": extraction.chunk_id,
            "chunk_text": extraction.chunk_text,
            "confidence": crit.confidence,
            "status": "pending",
            "concept_mapping": triple.concept_mapping.model_dump() if triple.concept_mapping else None
        }

        # Save to mock graph store
        mock_graph_store.add_edge(record)
        processed_records.append(record)

    return SieveResult(
        chunk_id=extraction.chunk_id,
        chunk_text=extraction.chunk_text,
        processed_triples=processed_records
    )
