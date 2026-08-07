import time
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from dependency_injector.wiring import Provide, inject
from app.services.annotation_service import AnnotationService
from app.services.search_service import SearchService
from app.db.neo4j_client import reset_neo4j_graph
from app.core.container import Container
from app.module_a_sieve import extractor
from app.module_a_sieve import critic
from app.module_a_sieve import ingester

logger = logging.getLogger(__name__)

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
    extraction = await extractor.extract_triples(chunk_id, req.text)
    critic_evals = await critic.evaluate_triples(extraction)
    sieve_res = await ingester.ingest_sieve_output(extraction, critic_evals)
    return {"status": "success", "chunk_id": chunk_id, "triples_ingested": len(sieve_res.processed_triples)}

@router.get("/queue")
@inject
async def get_pending_queue(
    limit: int = Query(20, ge=1, le=100),
    service: AnnotationService = Depends(Provide[Container.annotation_service])
):
    """Fetch pending edges with source chunk text for annotation asynchronously."""
    items = await service.get_pending_queue(limit)
    return {"queue": items, "count": len(items)}

@router.post("/approve/{edge_id}")
@inject
async def approve_edge(
    edge_id: str,
    body: DecisionRequest = DecisionRequest(),
    service: AnnotationService = Depends(Provide[Container.annotation_service])
):
    """Approve a pending edge using AnnotationService."""
    success = await service.approve_edge(edge_id, body.user_id)
    if not success:
        logger.warning(f"Failed to approve edge: {edge_id}")
    return {"status": "approved", "edge_id": edge_id, "approved_by": body.user_id}

@router.post("/reject/{edge_id}")
@inject
async def reject_edge(
    edge_id: str,
    body: DecisionRequest = DecisionRequest(),
    service: AnnotationService = Depends(Provide[Container.annotation_service])
):
    """Reject a pending edge using AnnotationService."""
    success = await service.reject_edge(edge_id, body.user_id)
    if not success:
        logger.warning(f"Failed to reject edge: {edge_id}")
    return {"status": "rejected", "edge_id": edge_id, "rejected_by": body.user_id}

@router.get("/stats")
@inject
async def get_dashboard_stats(service: AnnotationService = Depends(Provide[Container.annotation_service])):
    """Get count of pending, approved, and rejected facts asynchronously."""
    return await service.get_stats()

@router.post("/reset")
@inject
async def reset_database_and_queue(
    search_service: SearchService = Depends(Provide[Container.search_service])
):
    """Wipe graph database and reset state asynchronously."""
    await reset_neo4j_graph()
    search_service.reset_cache()
    return {"status": "success", "message": "Database and queue reset successfully."}
