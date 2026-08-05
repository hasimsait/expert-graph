import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.db.neo4j_client import run_cypher
from app.module_a_sieve.extractor import extract_triples
from app.module_a_sieve.critic import evaluate_triples
from app.module_a_sieve.ingester import ingest_sieve_output

from app.db.mock_graph import mock_graph_store

router = APIRouter(prefix="/api", tags=["Annotator Dashboard"])

class IngestRequest(BaseModel):
    chunk_id: Optional[str] = None
    text: str

class DecisionRequest(BaseModel):
    user_id: str = "thesis_annotator_1"

@router.post("/ingest")
def ingest_text(req: IngestRequest):
    """Run Sieve extraction & critic, then push pending triples to graph."""
    chunk_id = req.chunk_id or f"chk_{int(time.time()*1000)}"
    extraction = extract_triples(chunk_id, req.text)
    critic_evals = evaluate_triples(extraction)
    sieve_res = ingest_sieve_output(extraction, critic_evals)
    return {"status": "success", "chunk_id": chunk_id, "triples_ingested": len(sieve_res.processed_triples)}

@router.get("/queue")
def get_pending_queue(limit: int = Query(20, ge=1, le=100)):
    """Fetch pending edges with source chunk text for annotation."""
    cypher = """
    MATCH (s:Entity)-[r]->(o:Entity)
    WHERE r.status = "pending"
    MATCH (ch:Chunk {id: r.chunk_id})
    OPTIONAL MATCH (c1:Concept {name: type(r)})-[m:SUBCLASS_OF|SYNONYM_OF]->(c2:Concept)
    RETURN 
        r.edge_id AS edge_id,
        s.name AS subject_name,
        s.type AS subject_type,
        type(r) AS relation,
        o.name AS object_name,
        o.type AS object_type,
        r.chunk_id AS chunk_id,
        ch.text AS chunk_text,
        r.confidence AS confidence,
        c2.name AS meta_concept,
        type(m) AS meta_mapping
    LIMIT $limit
    """
    db_results = run_cypher(cypher, {"limit": limit})
    
    items = []
    if db_results:
        for rec in db_results:
            items.append({
                "edge_id": rec["edge_id"],
                "subject": {"name": rec["subject_name"], "type": rec["subject_type"]},
                "relation": rec["relation"],
                "object": {"name": rec["object_name"], "type": rec["object_type"]},
                "chunk_id": rec["chunk_id"],
                "chunk_text": rec["chunk_text"],
                "confidence": rec["confidence"],
                "meta_concept": rec.get("meta_concept"),
                "meta_mapping": rec.get("meta_mapping")
            })
    else:
        # Fallback to mock graph store
        items = mock_graph_store.get_pending_queue(limit)

    return {"queue": items, "count": len(items)}

@router.post("/approve/{edge_id}")
def approve_edge(edge_id: str, body: DecisionRequest = DecisionRequest()):
    """Approve a pending edge in Neo4j (or mock graph store)."""
    now = int(time.time())
    cypher = """
    MATCH (s:Entity)-[r]->(o:Entity)
    WHERE r.edge_id = $edge_id OR (r.status = "pending" AND r.chunk_id = $edge_id)
    SET r.status = "approved", r.approved_by = $user_id, r.timestamp = $timestamp
    RETURN r.edge_id AS edge_id
    """
    res = run_cypher(cypher, {"edge_id": edge_id, "user_id": body.user_id, "timestamp": now})
    
    # Update mock graph store
    mock_graph_store.update_edge_status(edge_id, "approved", body.user_id)

    return {"status": "approved", "edge_id": edge_id, "approved_by": body.user_id}

@router.post("/reject/{edge_id}")
def reject_edge(edge_id: str, body: DecisionRequest = DecisionRequest()):
    """Reject a pending edge in Neo4j (or mock graph store)."""
    now = int(time.time())
    cypher = """
    MATCH (s:Entity)-[r]->(o:Entity)
    WHERE r.edge_id = $edge_id OR (r.status = "pending" AND r.chunk_id = $edge_id)
    SET r.status = "rejected", r.approved_by = $user_id, r.timestamp = $timestamp
    RETURN r.edge_id AS edge_id
    """
    res = run_cypher(cypher, {"edge_id": edge_id, "user_id": body.user_id, "timestamp": now})

    # Update mock graph store
    mock_graph_store.update_edge_status(edge_id, "rejected", body.user_id)

    return {"status": "rejected", "edge_id": edge_id, "rejected_by": body.user_id}

@router.get("/stats")
def get_dashboard_stats():
    """Get count of pending, approved, and rejected facts."""
    cypher = """
    MATCH ()-[r]->()
    WHERE r.status IS NOT NULL
    RETURN r.status AS status, count(r) AS cnt
    """
    results = run_cypher(cypher)
    stats = {"pending": 0, "approved": 0, "rejected": 0}
    if results:
        for row in results:
            st = row.get("status")
            if st in stats:
                stats[st] = row.get("cnt", 0)
    else:
        # Fallback to mock graph store stats
        stats = mock_graph_store.get_stats()

    return stats

@router.post("/reset")
def reset_database_and_queue():
    """Wipe all nodes & edges in Neo4j and reset mock graph store."""
    cypher_wipe = "MATCH (n) DETACH DELETE n"
    run_cypher(cypher_wipe)
    mock_graph_store.reset()
    return {"status": "success", "message": "Database and queue reset successfully."}
