import logging
from typing import List, Dict, Any, Optional
from app.db.repository.concept_repo import ConceptRepository
from app.db.repository.document_repo import DocumentRepository
class GraphService:
    def __init__(self, 
                 concept_repo: ConceptRepository, 
                 document_repo: DocumentRepository):
        self.concept_repo = concept_repo
        self.document_repo = document_repo

    async def get_document_implications(self, document_id: str) -> List[Dict[str, Any]]:
        return await self.document_repo.get_document_implications(document_id)

    async def run_concept_pagerank(self) -> List[Dict[str, Any]]:
        return await self.concept_repo.run_concept_pagerank()

    async def expand_meta_graph_concept(self, concept_name: str) -> List[str]:
        return await self.concept_repo.expand_meta_graph_concept(concept_name)

    async def get_canonical_concepts(self) -> Dict[str, str]:
        return await self.concept_repo.get_canonical_concepts()
        
    async def get_all_documents(self) -> List[Dict[str, Any]]:
        return await self.document_repo.get_all_documents()

