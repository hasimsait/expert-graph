import logging
from typing import List, Dict, Any
from app.db.repository import GraphRepository, get_graph_repository

logger = logging.getLogger(__name__)

async def expand_meta_graph_concept(concept_name: str, repo: GraphRepository = None) -> List[str]:
    """Step 1 (Meta-Expansion): Find concept and all descendant subclasses/synonyms asynchronously."""
    active_repo = repo or get_graph_repository()
    return await active_repo.expand_meta_graph_concept(concept_name)

async def fetch_approved_facts(query: str = "ALL", repo: GraphRepository = None) -> List[Dict[str, Any]]:
    """Retrieval Engine: TF-IDF Search + Meta-Expansion + Approved Facts asynchronously."""
    active_repo = repo or get_graph_repository()
    return await active_repo.get_approved_facts(query=query)
