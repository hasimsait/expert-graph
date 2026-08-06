import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from app.db.repository import GraphRepository, get_graph_repository
from app.module_a_sieve.extractor import extract_triples
from app.module_a_sieve.critic import evaluate_triples
from app.module_a_sieve.ingester import ingest_sieve_output

router = APIRouter(prefix="/api", tags=["Annotator Dashboard"])

class IngestRequest(BaseModel):
    chunk_id: Optional[str] = None
    text: str

class DecisionRequest(BaseModel):
    user_id: str = "thesis_annotator_1"

@router.post("/ingest")
async def ingest_text(req: IngestRequest):
    """Run Sieve extraction & critic, then push pending triples to graph asynchronously."""
    chunk_id = req.chunk_id or f"chk_{int(time.time()*1000)}"
    extraction = await extract_triples(chunk_id, req.text)
    critic_evals = await evaluate_triples(extraction)
    sieve_res = await ingest_sieve_output(extraction, critic_evals)
    return {"status": "success", "chunk_id": chunk_id, "triples_ingested": len(sieve_res.processed_triples)}

@router.get("/queue")
async def get_pending_queue(
    limit: int = Query(20, ge=1, le=100),
    repo: GraphRepository = Depends(get_graph_repository)
):
    """Fetch pending edges with source chunk text for annotation asynchronously."""
    items = await repo.get_pending_queue(limit)
    return {"queue": items, "count": len(items)}

@router.post("/approve/{edge_id}")
async def approve_edge(
    edge_id: str,
    body: DecisionRequest = DecisionRequest(),
    repo: GraphRepository = Depends(get_graph_repository)
):
    """Approve a pending edge in the active graph repository asynchronously."""
    await repo.update_edge_status(edge_id, "approved", body.user_id)
    return {"status": "approved", "edge_id": edge_id, "approved_by": body.user_id}

@router.post("/reject/{edge_id}")
async def reject_edge(
    edge_id: str,
    body: DecisionRequest = DecisionRequest(),
    repo: GraphRepository = Depends(get_graph_repository)
):
    """Reject a pending edge in the active graph repository asynchronously."""
    await repo.update_edge_status(edge_id, "rejected", body.user_id)
    return {"status": "rejected", "edge_id": edge_id, "rejected_by": body.user_id}

@router.get("/stats")
async def get_dashboard_stats(repo: GraphRepository = Depends(get_graph_repository)):
    """Get count of pending, approved, and rejected facts asynchronously."""
    return await repo.get_stats()

@router.post("/reset")
async def reset_database_and_queue(repo: GraphRepository = Depends(get_graph_repository)):
    """Wipe graph database and reset state asynchronously."""
    await repo.reset_graph()
    return {"status": "success", "message": "Database and queue reset successfully."}
