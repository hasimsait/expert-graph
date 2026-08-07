import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.db import neo4j_client

logger = logging.getLogger(__name__)

class DocumentRepository(ABC):
    @abstractmethod
    async def get_all_documents(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def store_chunk(self, chunk_id: str, chunk_text: str, timestamp: int) -> None:
        pass

    @abstractmethod
    async def get_document_implications(self, document_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def store_er_mapping(self, chunk_id: str, raw_string: str, res: Dict[str, Any]) -> None:
        pass

class Neo4jDocumentRepository(DocumentRepository):
    async def store_chunk(self, chunk_id: str, chunk_text: str, timestamp: int) -> None:
        chunk_cypher = """
        MERGE (ch:Chunk {id: $chunk_id})
        ON CREATE SET ch.text = $chunk_text, ch.created_at = $timestamp
        """
        await neo4j_client.run_cypher(chunk_cypher, {
            "chunk_id": chunk_id,
            "chunk_text": chunk_text,
            "timestamp": timestamp
        })

    async def get_all_documents(self) -> List[Dict[str, Any]]:
        cypher = """
        MATCH (d)
        WHERE d:SourceDocument OR d:Chunk
        RETURN DISTINCT COALESCE(d.id, d.chunk_id) AS id,
                        COALESCE(d.title, substring(d.text, 0, 40), d.id, d.chunk_id) AS title,
                        labels(d)[0] AS type
        LIMIT 50
        """
        return await neo4j_client.run_cypher(cypher)

    async def get_document_implications(self, document_id: str) -> List[Dict[str, Any]]:
        cypher = """
        MATCH (doc)
        WHERE (doc:SourceDocument OR doc:Chunk) AND (COALESCE(doc.id, doc.chunk_id) = $document_id OR $document_id IN ["ALL", "ALL_DOCS", ""])
        MATCH (doc)-[:CONTAINS|MENTIONS*1..2]->(raw)
        MATCH (raw)-[:MAPPED_TO]->(c:CanonicalConcept)
        MATCH (c)-[:RELATED_TO]-(imp:DownstreamImplication)
        RETURN DISTINCT COALESCE(doc.id, doc.chunk_id) AS document_id,
                        raw.name AS raw_entity,
                        c.id AS canonical_id,
                        c.name AS canonical_name,
                        imp.id AS implication_id,
                        imp.name AS implication_name,
                        imp.description AS description
        """
        results = await neo4j_client.run_cypher(cypher, {"document_id": document_id})
        if not results:
            cypher_fallback = """
            MATCH (doc)
            WHERE (doc:SourceDocument OR doc:Chunk) AND (COALESCE(doc.id, doc.chunk_id) = $document_id OR $document_id IN ["ALL", "ALL_DOCS", ""])
            MATCH (doc)-[:CONTAINS|MENTIONS|MAPPED_TO*1..3]->(c:CanonicalConcept)
            MATCH (c)-[:RELATED_TO]-(imp:DownstreamImplication)
            RETURN DISTINCT COALESCE(doc.id, doc.chunk_id, $document_id) AS document_id,
                            c.name AS raw_entity,
                            c.id AS canonical_id,
                            c.name AS canonical_name,
                            imp.id AS implication_id,
                            imp.name AS implication_name,
                            imp.description AS description
            LIMIT 20
            """
            results = await neo4j_client.run_cypher(cypher_fallback, {"document_id": document_id})

        return results

    async def store_er_mapping(self, chunk_id: str, raw_string: str, res: Dict[str, Any]) -> None:
        map_cypher = """
        MATCH (ch:Chunk {id: $chunk_id})
        MERGE (r:RawEntity {name: $raw_string})
        MERGE (c:CanonicalConcept {id: $canonical_id})
        ON CREATE SET c.name = $canonical_name
        MERGE (ch)-[:MENTIONS]->(r)
        MERGE (r)-[m:MAPPED_TO]->(c)
        ON CREATE SET m.confidence = $confidence
        ON MATCH SET m.confidence = $confidence
        """
        try:
            await neo4j_client.run_cypher(map_cypher, {
                "chunk_id": chunk_id,
                "raw_string": raw_string,
                "canonical_id": res["canonical_id"],
                "canonical_name": res["canonical_name"],
                "confidence": res["confidence"]
            })
        except Exception as e:
            logger.warning(
                "Failed to store ER mapping for '%s': %s", raw_string, e)
