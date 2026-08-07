from fastapi import APIRouter, Depends
from typing import Dict, Any, List
from dependency_injector.wiring import Provide, inject
from app.services.graph_service import GraphService
from app.core.container import Container

router = APIRouter(prefix="/api/analytics", tags=["Graph Analytics"])

@router.get("/documents")
@inject
async def list_documents_endpoint(service: GraphService = Depends(Provide[Container.graph_service])) -> Dict[str, Any]:
    """List all ingested SourceDocument / Chunk nodes currently available in active repository asynchronously."""
    docs = await service.get_all_documents()
    return {
        "documents": docs,
        "count": len(docs)
    }

@router.get("/implications/{document_id}")
@inject
async def document_implications_endpoint(
    document_id: str,
    service: GraphService = Depends(Provide[Container.graph_service])
) -> Dict[str, Any]:
    """Expose 4-hop graph traversal from SourceDocument to DownstreamImplications asynchronously."""
    implications = await service.get_document_implications(document_id)
    return {
        "document_id": document_id,
        "implications": implications,
        "count": len(implications)
    }

@router.get("/pagerank/concepts")
@inject
async def concept_pagerank_endpoint(service: GraphService = Depends(Provide[Container.graph_service])) -> Dict[str, Any]:
    """Expose PageRank centrality scores for CanonicalConcept nodes asynchronously."""
    top_concepts = await service.run_concept_pagerank()
    return {
        "top_concepts": top_concepts,
        "count": len(top_concepts)
    }
