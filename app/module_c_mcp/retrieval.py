import logging
from typing import List, Dict, Any
from app.db.neo4j_client import run_cypher
from app.db.mock_graph import mock_graph_store

logger = logging.getLogger(__name__)

def expand_meta_graph_concept(concept_name: str) -> List[str]:
    """Step 1 (Meta-Expansion): Find concept and all descendant subclasses/synonyms."""
    concept_upper = concept_name.upper()
    cypher = """
    MATCH (root:Concept)
    WHERE root.name = $concept_name
    OPTIONAL MATCH (child:Concept)-[:SUBCLASS_OF|SYNONYM_OF*1..4]->(root)
    RETURN root.name AS root, collect(DISTINCT child.name) AS children
    """
    res = run_cypher(cypher, {"concept_name": concept_upper})
    
    expanded = {concept_upper}
    if res and res[0].get("root"):
        children = res[0].get("children") or []
        expanded.update(children)
    else:
        # Fallback to in-memory mock graph meta expansion
        expanded.update(mock_graph_store.expand_concept(concept_upper))
        
    logger.info("Meta-Expansion for '%s' returned concepts: %s", concept_name, list(expanded))
    return list(expanded)

def fetch_approved_facts(concept_name: str) -> List[Dict[str, Any]]:
    """Two-Step Cypher Retrieval Engine: Meta-Expansion then Approved Data-Graph facts."""
    concept_upper = (concept_name or "ALL").upper()
    
    if concept_upper in ["ALL", "RELATIONSHIP", "*"]:
        cypher = """
        MATCH (s:Entity)-[r]->(o:Entity)
        WHERE r.status = "approved"
        OPTIONAL MATCH (ch:Chunk {id: r.chunk_id})
        RETURN 
            r.edge_id AS edge_id,
            s.name AS subject_name,
            s.type AS subject_type,
            type(r) AS relation,
            o.name AS object_name,
            o.type AS object_type,
            r.confidence AS confidence,
            r.approved_by AS approved_by,
            r.timestamp AS timestamp,
            r.chunk_id AS chunk_id,
            ch.text AS chunk_text
        """
        db_facts = run_cypher(cypher)
        if not db_facts:
            facts = mock_graph_store.get_approved_facts("RELATIONSHIP")
        else:
            facts = []
            for row in db_facts:
                facts.append({
                    "edge_id": row.get("edge_id"),
                    "subject": row.get("subject_name"),
                    "subject_type": row.get("subject_type"),
                    "relation": row.get("relation"),
                    "object": row.get("object_name"),
                    "object_type": row.get("object_type"),
                    "confidence": row.get("confidence"),
                    "approved_by": row.get("approved_by"),
                    "timestamp": row.get("timestamp"),
                    "chunk_id": row.get("chunk_id"),
                    "chunk_text": row.get("chunk_text")
                })
        return facts

    expanded_concepts = expand_meta_graph_concept(concept_name)

    cypher = """
    MATCH (s:Entity)-[r]->(o:Entity)
    WHERE type(r) IN $concepts AND r.status = "approved"
    OPTIONAL MATCH (ch:Chunk {id: r.chunk_id})
    RETURN 
        r.edge_id AS edge_id,
        s.name AS subject_name,
        s.type AS subject_type,
        type(r) AS relation,
        o.name AS object_name,
        o.type AS object_type,
        r.confidence AS confidence,
        r.approved_by AS approved_by,
        r.timestamp AS timestamp,
        r.chunk_id AS chunk_id,
        ch.text AS chunk_text
    """
    db_facts = run_cypher(cypher, {"concepts": expanded_concepts})

    facts = []
    if db_facts:
        for row in db_facts:
            facts.append({
                "edge_id": row.get("edge_id"),
                "subject": row.get("subject_name"),
                "subject_type": row.get("subject_type"),
                "relation": row.get("relation"),
                "object": row.get("object_name"),
                "object_type": row.get("object_type"),
                "confidence": row.get("confidence"),
                "approved_by": row.get("approved_by"),
                "timestamp": row.get("timestamp"),
                "chunk_id": row.get("chunk_id"),
                "chunk_text": row.get("chunk_text")
            })
    else:
        # Fallback to mock graph store
        facts = mock_graph_store.get_approved_facts(concept_name)

    return facts
