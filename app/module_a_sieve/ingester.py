import logging
import time
import uuid
import re
from typing import List, Dict, Any
from dependency_injector.wiring import Provide, inject
from app.db.repository.document_repo import DocumentRepository
from app.db.repository.concept_repo import ConceptRepository
from app.db.repository.edge_repo import EdgeRepository
from app.core.container import Container
from app.module_a_sieve.schemas import ExtractionOutput, CriticEvaluation, SieveResult
from app.services.entity_resolution import EntityResolver

logger = logging.getLogger(__name__)

@inject
async def ingest_sieve_output(
    extraction: ExtractionOutput,
    evaluations: List[CriticEvaluation],
    repo: DocumentRepository = Provide[Container.document_repo],
    concept_repo: ConceptRepository = Provide[Container.concept_repo],
    edge_repo: EdgeRepository = Provide[Container.edge_repo],
    resolver: EntityResolver = Provide[Container.entity_resolver]
) -> SieveResult:
    """Ingest Critic-verified triples into graph database asynchronously with status 'pending'."""
    timestamp = int(time.time())
    processed_records = []
    
    await repo.store_chunk(extraction.chunk_id, extraction.chunk_text, timestamp)

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

            await concept_repo.store_concept_mapping(
                triple.concept_mapping.new_relation,
                triple.concept_mapping.existing_concept,
                mapping_type
            )

        # Insert Entities & Dynamic Data-Graph Edge
        try:
            await edge_repo.create_pending_edge(
                chunk_id=extraction.chunk_id,
                edge_id=edge_id,
                subj_name=triple.subject.name,
                subj_type=triple.subject.type,
                obj_name=triple.object.name,
                obj_type=triple.object.type,
                rel_type=rel_type,
                confidence=crit.confidence,
                timestamp=timestamp
            )
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

