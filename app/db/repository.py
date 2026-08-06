import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.db.neo4j_client import run_cypher

logger = logging.getLogger(__name__)

class GraphRepository(ABC):
    """Abstract Repository interface for Graph Database operations."""

    @abstractmethod
    async def get_pending_queue(self, limit: int = 20) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def update_edge_status(self, edge_id: str, status: str, user_id: str) -> bool:
        pass

    @abstractmethod
    async def get_approved_facts(self, query: str = "ALL") -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, int]:
        pass

    @abstractmethod
    async def get_document_implications(self, document_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def run_concept_pagerank(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_all_documents(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def expand_meta_graph_concept(self, concept_name: str) -> List[str]:
        pass

    @abstractmethod
    async def get_canonical_concepts(self) -> Dict[str, str]:
        pass

    @abstractmethod
    async def reset_graph(self) -> None:
        pass


class Neo4jGraphRepository(GraphRepository):
    """Production implementation of GraphRepository targeting Neo4j database asynchronously."""

    async def get_pending_queue(self, limit: int = 20) -> List[Dict[str, Any]]:
        cypher = """
        MATCH (s:Entity)-[r]->(o:Entity)
        WHERE r.status = "pending"
        MATCH (ch:Chunk {id: r.chunk_id})
        OPTIONAL MATCH (c1:Concept {name: type(r)})-[m:SUBCLASS_OF|SYNONYM_OF]->(c2:Concept)
        RETURN 
            r.edge_id AS edge_id,
            s.name AS subject_name,
            s.type AS subject_type,
            type(r) AS relation,
            o.name AS object_name,
            o.type AS object_type,
            r.chunk_id AS chunk_id,
            ch.text AS chunk_text,
            r.confidence AS confidence,
            c2.name AS meta_concept,
            type(m) AS meta_mapping
        LIMIT $limit
        """
        results = await run_cypher(cypher, {"limit": limit})
        items = []
        for rec in results:
            items.append({
                "edge_id": rec["edge_id"],
                "subject": {"name": rec["subject_name"], "type": rec["subject_type"]},
                "relation": rec["relation"],
                "object": {"name": rec["object_name"], "type": rec["object_type"]},
                "chunk_id": rec["chunk_id"],
                "chunk_text": rec["chunk_text"],
                "confidence": rec["confidence"],
                "meta_concept": rec.get("meta_concept"),
                "meta_mapping": rec.get("meta_mapping")
            })
        return items

    async def update_edge_status(self, edge_id: str, status: str, user_id: str) -> bool:
        cypher = """
        MATCH (s:Entity)-[r]->(o:Entity)
        WHERE r.edge_id = $edge_id OR (r.status = "pending" AND r.chunk_id = $edge_id)
        SET r.status = $status, r.approved_by = $user_id, r.timestamp = timestamp()
        WITH s, r, o
        OPTIONAL MATCH (ch:Chunk {id: r.chunk_id})
        RETURN 
            r.edge_id AS edge_id,
            s.name AS subject,
            s.type AS subject_type,
            type(r) AS relation,
            o.name AS object,
            o.type AS object_type,
            r.confidence AS confidence,
            r.approved_by AS approved_by,
            r.timestamp AS timestamp,
            r.chunk_id AS chunk_id,
            ch.text AS chunk_text
        """
        results = await run_cypher(cypher, {"edge_id": edge_id, "status": status, "user_id": user_id})
        if results:
            from app.services.tfidf_retrieval import TFIDFRetriever
            from app.services.entity_resolution import get_entity_resolver
            if status == "approved":
                for rec in results:
                    TFIDFRetriever.add_fact_delta(rec)
                try:
                    resolver = await get_entity_resolver()
                    await resolver.load_ontology_from_db()
                except Exception as e:
                    logger.warning("Error refreshing EntityResolver on edge approval: %s", e)
            elif status in ["rejected", "deleted"]:
                for rec in results:
                    TFIDFRetriever.remove_fact_delta(rec.get("edge_id") or edge_id)
        return len(results) > 0

    async def expand_meta_graph_concept(self, concept_name: str) -> List[str]:
        concept_upper = concept_name.upper()
        cypher = """
        MATCH (root:Concept)
        WHERE root.name = $concept_name
        OPTIONAL MATCH (child:Concept)-[:SUBCLASS_OF|SYNONYM_OF*1..4]->(root)
        RETURN root.name AS root, collect(DISTINCT child.name) AS children
        """
        res = await run_cypher(cypher, {"concept_name": concept_upper})
        expanded = {concept_upper}
        if res and res[0].get("root"):
            children = res[0].get("children") or []
            expanded.update(children)
        return list(expanded)

    async def get_approved_facts(self, query: str = "ALL") -> List[Dict[str, Any]]:
        search_term = (query or "ALL").strip()
        concept_upper = search_term.upper()

        if concept_upper in ["ALL", "RELATIONSHIP", "*", ""]:
            cypher = """
            MATCH (s:Entity)-[r]->(o:Entity)
            WHERE r.status = "approved"
            OPTIONAL MATCH (ch:Chunk {id: r.chunk_id})
            RETURN 
                r.edge_id AS edge_id,
                s.name AS subject_name,
                s.type AS subject_type,
                type(r) AS relation,
                o.name AS object_name,
                o.type AS object_type,
                r.confidence AS confidence,
                r.approved_by AS approved_by,
                r.timestamp AS timestamp,
                r.chunk_id AS chunk_id,
                ch.text AS chunk_text
            """
            db_facts = await run_cypher(cypher)
        else:
            import re
            raw_tokens = [t.strip().lower() for t in re.split(r'\s+', search_term) if t.strip()]
            tokens = []
            for t in raw_tokens:
                clean_t = re.sub(r'^[^\w-]+|[^\w-]+$', '', t)
                if len(clean_t) >= 2:
                    tokens.append(clean_t)

            if not tokens:
                tokens = [search_term.strip().lower()]

            token_conditions = []
            token_params = {}
            for idx, token in enumerate(tokens):
                param_name = f"t_{idx}"
                token_params[param_name] = token
                token_conditions.append(f"""
                    toLower(s.name) CONTAINS toLower(${param_name}) OR
                    toLower(o.name) CONTAINS toLower(${param_name}) OR
                    toLower(type(r)) CONTAINS toLower(${param_name}) OR
                    toLower(s.type) CONTAINS toLower(${param_name}) OR
                    toLower(o.type) CONTAINS toLower(${param_name}) OR
                    toLower(ch.text) CONTAINS toLower(${param_name})
                """)

            cypher_search = f"""
            MATCH (s:Entity)-[r]->(o:Entity)
            OPTIONAL MATCH (ch:Chunk {{id: r.chunk_id}})
            WHERE r.status = "approved" AND ({" OR ".join(token_conditions)})
            RETURN 
                r.edge_id AS edge_id,
                s.name AS subject_name,
                s.type AS subject_type,
                type(r) AS relation,
                o.name AS object_name,
                o.type AS object_type,
                r.confidence AS confidence,
                r.approved_by AS approved_by,
                r.timestamp AS timestamp,
                r.chunk_id AS chunk_id,
                ch.text AS chunk_text
            """
            db_facts = await run_cypher(cypher_search, token_params)

            if not db_facts:
                expanded_concepts = await self.expand_meta_graph_concept(search_term)
                cypher_meta = """
                MATCH (s:Entity)-[r]->(o:Entity)
                WHERE type(r) IN $concepts AND r.status = "approved"
                OPTIONAL MATCH (ch:Chunk {id: r.chunk_id})
                RETURN 
                    r.edge_id AS edge_id,
                    s.name AS subject_name,
                    s.type AS subject_type,
                    type(r) AS relation,
                    o.name AS object_name,
                    o.type AS object_type,
                    r.confidence AS confidence,
                    r.approved_by AS approved_by,
                    r.timestamp AS timestamp,
                    r.chunk_id AS chunk_id,
                    ch.text AS chunk_text
                """
                db_facts = await run_cypher(cypher_meta, {"concepts": expanded_concepts})

        if not db_facts:
            return []

        facts = []
        for row in db_facts:
            facts.append({
                "edge_id": row.get("edge_id"),
                "subject": row.get("subject_name"),
                "subject_type": row.get("subject_type"),
                "relation": row.get("relation"),
                "object": row.get("object_name"),
                "object_type": row.get("object_type"),
                "confidence": row.get("confidence"),
                "approved_by": row.get("approved_by"),
                "timestamp": row.get("timestamp"),
                "chunk_id": row.get("chunk_id"),
                "chunk_text": row.get("chunk_text")
            })

        from app.services.tfidf_retrieval import TFIDFRetriever
        return TFIDFRetriever.rank_facts(search_term, facts)

    async def get_stats(self) -> Dict[str, int]:
        cypher = """
        MATCH ()-[r]->()
        WHERE r.status IS NOT NULL
        RETURN r.status AS status, count(r) AS cnt
        """
        results = await run_cypher(cypher)
        stats = {"pending": 0, "approved": 0, "rejected": 0}
        for row in results:
            st = row.get("status")
            if st in stats:
                stats[st] = row.get("cnt", 0)
        return stats

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
        results = await run_cypher(cypher, {"document_id": document_id})
        if not results:
            cypher_fallback = """
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
            results = await run_cypher(cypher_fallback, {"document_id": document_id})

        return results

    async def run_concept_pagerank(self) -> List[Dict[str, Any]]:
        try:
            cypher = """
            CALL gds.pageRank.stream({
              nodeProjection: 'CanonicalConcept',
              relationshipProjection: { RELATED_TO: { type: 'RELATED_TO', orientation: 'UNDIRECTED' } }
            })
            YIELD nodeId, score
            RETURN gds.util.asNode(nodeId).id AS concept_id,
                   gds.util.asNode(nodeId).name AS concept_name,
                   score
            ORDER BY score DESC LIMIT 10
            """
            results = await run_cypher(cypher)
            if results:
                return results
        except Exception:
            pass

        cypher_centrality = """
        MATCH (c)
        WHERE c:CanonicalConcept OR c:Concept
        OPTIONAL MATCH (c)-[r]-()
        RETURN COALESCE(c.id, c.name) AS concept_id,
               COALESCE(c.name, c.id) AS concept_name,
               COUNT(r) * 1.0 AS score
        ORDER BY score DESC
        LIMIT 10
        """
        return await run_cypher(cypher_centrality)

    async def get_all_documents(self) -> List[Dict[str, Any]]:
        cypher = """
        MATCH (d)
        WHERE d:SourceDocument OR d:Chunk
        RETURN DISTINCT COALESCE(d.id, d.chunk_id) AS id,
                        COALESCE(d.title, substring(d.text, 0, 40), d.id, d.chunk_id) AS title,
                        labels(d)[0] AS type
        LIMIT 50
        """
        return await run_cypher(cypher)

    async def get_canonical_concepts(self) -> Dict[str, str]:
        cypher = """
        MATCH (c)
        WHERE c:CanonicalConcept OR c:Concept
        RETURN COALESCE(c.id, c.name) AS id, COALESCE(c.name, c.id) AS name
        """
        results = await run_cypher(cypher)
        return {r["id"]: r["name"] for r in results if r.get("id") and r.get("name")}

    async def reset_graph(self) -> None:
        cypher = "MATCH (n) DETACH DELETE n"
        await run_cypher(cypher)
        from app.services.tfidf_retrieval import TFIDFRetriever
        TFIDFRetriever.reset_cache()


# Repository Factory / Dependency Injector
_default_repo: Optional[GraphRepository] = None

def get_graph_repository() -> GraphRepository:
    """Dependency provider function for FastAPI Depends() and business logic."""
    global _default_repo
    if _default_repo is None:
        _default_repo = Neo4jGraphRepository()
    return _default_repo

def set_graph_repository(repo: GraphRepository) -> None:
    """Override default repository instance (used primarily in test fixtures)."""
    global _default_repo
    _default_repo = repo
