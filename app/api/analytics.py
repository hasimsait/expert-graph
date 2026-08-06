from fastapi import APIRouter, Depends
from typing import Dict, Any, List
from app.db.repository import GraphRepository, get_graph_repository
from app.services.graph_analytics import get_document_implications, run_concept_pagerank, get_all_documents

router = APIRouter(prefix="/api/analytics", tags=["Graph Analytics"])

@router.get("/documents")
def list_documents_endpoint(repo: GraphRepository = Depends(get_graph_repository)) -> Dict[str, Any]:
    """List all ingested SourceDocument / Chunk nodes currently available in active repository."""
    docs = get_all_documents(repo=repo)
    return {
        "documents": docs,
        "count": len(docs)
    }

@router.get("/implications/{document_id}")
def document_implications_endpoint(
    document_id: str,
    repo: GraphRepository = Depends(get_graph_repository)
) -> Dict[str, Any]:
    """Expose 4-hop graph traversal from SourceDocument to DownstreamImplications."""
    implications = get_document_implications(document_id, repo=repo)
    return {
        "document_id": document_id,
        "implications": implications,
        "count": len(implications)
    }

@router.get("/pagerank/concepts")
def concept_pagerank_endpoint(repo: GraphRepository = Depends(get_graph_repository)) -> Dict[str, Any]:
    """Expose PageRank centrality scores for CanonicalConcept nodes."""
    top_concepts = run_concept_pagerank(repo=repo)
    return {
        "top_concepts": top_concepts,
        "count": len(top_concepts)
    }
