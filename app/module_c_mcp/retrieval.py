import logging
from typing import List, Dict, Any
from app.db.repository import GraphRepository, get_graph_repository

logger = logging.getLogger(__name__)

def expand_meta_graph_concept(concept_name: str, repo: GraphRepository = None) -> List[str]:
    """Step 1 (Meta-Expansion): Find concept and all descendant subclasses/synonyms."""
    active_repo = repo or get_graph_repository()
    return active_repo.expand_meta_graph_concept(concept_name)

def fetch_approved_facts(query: str = "ALL", repo: GraphRepository = None) -> List[Dict[str, Any]]:
    """Retrieval Engine: Term Overlap Search + Meta-Expansion + Approved Facts."""
    active_repo = repo or get_graph_repository()
    return active_repo.get_approved_facts(query=query)
