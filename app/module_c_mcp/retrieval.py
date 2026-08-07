import logging
from typing import List, Dict, Any
from dependency_injector.wiring import Provide, inject
from app.core.container import Container
from app.services.graph_service import GraphService
from app.services.search_service import SearchService
from app.db.repository.edge_repo import EdgeRepository

logger = logging.getLogger(__name__)

@inject
async def expand_meta_graph_concept(
    concept_name: str,
    graph_service: GraphService = Provide[Container.graph_service]
) -> List[str]:
    """Step 1 (Meta-Expansion): Find concept and all descendant subclasses/synonyms asynchronously."""
    return await graph_service.expand_meta_graph_concept(concept_name)

@inject
async def fetch_approved_facts(
    query: str = "ALL",
    edge_repo: EdgeRepository = Provide[Container.edge_repo],
    search_service: SearchService = Provide[Container.search_service]
) -> List[Dict[str, Any]]:
    """Retrieval Engine: TF-IDF Search + Meta-Expansion + Approved Facts asynchronously."""
    db_facts = await edge_repo.search_approved_facts(query)
    return search_service.rank_facts(query, db_facts)
