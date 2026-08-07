import logging
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.db import neo4j_client

logger = logging.getLogger(__name__)

class EdgeRepository(ABC):
    @abstractmethod
    async def get_pending_queue(self, limit: int = 20) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def create_pending_edge(self, chunk_id: str, edge_id: str, subj_name: str, subj_type: str, obj_name: str, obj_type: str, rel_type: str, confidence: float, timestamp: int) -> None:
        pass

    @abstractmethod
    async def update_edge_status(self, edge_id: str, status: str, user_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_approved_facts(self) -> List[Dict[str, Any]]:
        """Returns all approved facts for rebuilding caches or analytics."""
        pass

    @abstractmethod
    async def search_approved_facts(self, query: str) -> List[Dict[str, Any]]:
        """Returns facts matching a specific search term or meta concept."""
        pass



    async def get_stats(self) -> Dict[str, int]:
        pass

class Neo4jEdgeRepository(EdgeRepository):
    async def create_pending_edge(self, chunk_id: str, edge_id: str, subj_name: str, subj_type: str, obj_name: str, obj_type: str, rel_type: str, confidence: float, timestamp: int) -> None:
        rel_type = rel_type.upper().replace(" ", "_").replace("`", "") or "UNKNOWN_RELATION"
        ingest_cypher = f"""
        MATCH (ch:Chunk {{id: $chunk_id}})
        
        MERGE (s:Entity {{name: $subj_name}})
        ON CREATE SET s.type = $subj_type
        
        MERGE (o:Entity {{name: $obj_name}})
        ON CREATE SET o.type = $obj_type
        
        MERGE (ch)-[:MENTIONS]->(s)
        MERGE (ch)-[:MENTIONS]->(o)
        
        CREATE (s)-[r:`{rel_type}` {{
            edge_id: $edge_id,
            chunk_id: $chunk_id,
            confidence: $confidence,
            status: "pending",
            approved_by: "",
            timestamp: $timestamp
        }}]->(o)
        RETURN r
        """
        await neo4j_client.run_cypher(ingest_cypher, {
            "subj_name": subj_name,
            "subj_type": subj_type,
            "obj_name": obj_name,
            "obj_type": obj_type,
            "chunk_id": chunk_id,
            "edge_id": edge_id,
            "confidence": confidence,
            "timestamp": timestamp
        })

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
        results = await neo4j_client.run_cypher(cypher, {"limit": limit})
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

    async def update_edge_status(self, edge_id: str, status: str, user_id: str) -> List[Dict[str, Any]]:
        cypher = """
        MATCH (s:Entity)-[r]->(o:Entity)
        WHERE r.edge_id = $edge_id OR (r.status = "pending" AND r.chunk_id = $edge_id)
        SET r.status = $status, r.approved_by = $user_id, r.timestamp = $timestamp
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
        results = await neo4j_client.run_cypher(cypher, {"edge_id": edge_id, "status": status, "user_id": user_id, "timestamp": int(time.time())})
        return results

    async def get_approved_facts(self) -> List[Dict[str, Any]]:
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
        db_facts = await neo4j_client.run_cypher(cypher)
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
        return facts


    async def search_approved_facts(self, query: str) -> List[Dict[str, Any]]:
        search_term = query.strip()
        concept_upper = search_term.upper()

        if concept_upper in ["ALL", "RELATIONSHIP", "*", ""]:
            return await self.get_approved_facts()

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
        WHERE r.status = "approved"
        OPTIONAL MATCH (ch:Chunk {{id: r.chunk_id}})
        WITH s, r, o, ch
        WHERE ({" OR ".join(token_conditions)})
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
        db_facts = await neo4j_client.run_cypher(cypher_search, token_params)

        if not db_facts:
            from app.db.repository.concept_repo import get_concept_repository
            concept_repo = get_concept_repository()
            expanded_concepts = await concept_repo.expand_meta_graph_concept(search_term)
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
            db_facts = await neo4j_client.run_cypher(cypher_meta, {"concepts": expanded_concepts})

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
        return facts

    async def get_stats(self) -> Dict[str, int]:
        cypher = """
        MATCH ()-[r]->()
        WHERE r.status IS NOT NULL
        RETURN r.status AS status, count(r) AS cnt
        """
        results = await neo4j_client.run_cypher(cypher)
        stats = {"pending": 0, "approved": 0, "rejected": 0}
        for row in results:
            st = row.get("status")
            if st in stats:
                stats[st] = row.get("cnt", 0)
        return stats
