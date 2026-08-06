import logging
from typing import List, Dict, Any
from app.db.repository import GraphRepository, get_graph_repository

logger = logging.getLogger(__name__)

async def get_all_documents(repo: GraphRepository = None) -> List[Dict[str, Any]]:
    """Query all ingested Document / Chunk nodes from active graph repository asynchronously."""
    active_repo = repo or get_graph_repository()
    return await active_repo.get_all_documents()

async def get_document_implications(document_id: str, repo: GraphRepository = None) -> List[Dict[str, Any]]:
    """Execute 4-hop query to discover linked DownstreamImplication nodes via active graph repository asynchronously."""
    active_repo = repo or get_graph_repository()
    return await active_repo.get_document_implications(document_id)

async def run_concept_pagerank(repo: GraphRepository = None) -> List[Dict[str, Any]]:
    """Execute PageRank or degree centrality on CanonicalConcept nodes via active graph repository asynchronously."""
    active_repo = repo or get_graph_repository()
    return await active_repo.run_concept_pagerank()
