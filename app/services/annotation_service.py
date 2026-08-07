import logging
from typing import List, Dict, Any, Optional
from app.db.repository.edge_repo import EdgeRepository
from app.services.search_service import SearchService
from app.services.entity_resolution import EntityResolver

logger = logging.getLogger(__name__)

class AnnotationService:
    def __init__(self, 
                 edge_repo: EdgeRepository, 
                 search_service: SearchService,
                 entity_resolver: EntityResolver,
                 concept_repo):
        self.edge_repo = edge_repo
        self.search_service = search_service
        self.entity_resolver = entity_resolver
        self.concept_repo = concept_repo

    async def approve_edge(self, edge_id: str, user_id: str) -> bool:
        results = await self.edge_repo.update_edge_status(edge_id, "approved", user_id)
        if results:
            for rec in results:
                self.search_service.add_fact_delta(rec)
            try:
                await self.entity_resolver.load_ontology_from_db(self.concept_repo)
            except Exception as e:
                logger.warning("Error refreshing EntityResolver on edge approval: %s", e)
            return True
        return False

    async def reject_edge(self, edge_id: str, user_id: str) -> bool:
        results = await self.edge_repo.update_edge_status(edge_id, "rejected", user_id)
        if results:
            self.search_service.remove_fact_delta(edge_id)
            return True
        return False

    async def get_pending_queue(self, limit: int) -> List[Dict[str, Any]]:
        return await self.edge_repo.get_pending_queue(limit)

    async def get_stats(self) -> Dict[str, int]:
        return await self.edge_repo.get_stats()

