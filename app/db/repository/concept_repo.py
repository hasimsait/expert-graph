import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.db import neo4j_client

logger = logging.getLogger(__name__)

class ConceptRepository(ABC):
    @abstractmethod
    async def expand_meta_graph_concept(self, concept_name: str) -> List[str]:
        pass

    @abstractmethod
    async def store_concept_mapping(self, new_relation: str, existing_concept: str, mapping_type: str) -> None:
        pass

    @abstractmethod
    async def run_concept_pagerank(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_canonical_concepts(self) -> Dict[str, str]:
        pass

class Neo4jConceptRepository(ConceptRepository):
    async def store_concept_mapping(self, new_relation: str, existing_concept: str, mapping_type: str) -> None:
        mapping_type = mapping_type.upper().replace(" ", "_").replace("`", "") or "RELATED_TO"
        concept_cypher = f"""
        MERGE (c1:Concept {{name: $new_relation}})
        MERGE (c2:Concept {{name: $existing_concept}})
        MERGE (c1)-[:`{mapping_type}`]->(c2)
        """
        await neo4j_client.run_cypher(concept_cypher, {
            "new_relation": new_relation,
            "existing_concept": existing_concept
        })

    async def expand_meta_graph_concept(self, concept_name: str) -> List[str]:
        concept_upper = concept_name.upper()
        cypher = """
        MATCH (root:Concept)
        WHERE root.name = $concept_name
        OPTIONAL MATCH (child:Concept)-[:SUBCLASS_OF|SYNONYM_OF*1..4]->(root)
        RETURN root.name AS root, collect(DISTINCT child.name) AS children
        """
        res = await neo4j_client.run_cypher(cypher, {"concept_name": concept_name})
        expanded = {concept_upper}
        if res and res[0].get("root"):
            children = res[0].get("children") or []
            expanded.update(children)
        return list(expanded)

    async def run_concept_pagerank(self) -> List[Dict[str, Any]]:
        try:
            import uuid
            graph_name = f"pagerankGraph_{uuid.uuid4().hex}"

            project_cypher = f"""
            CALL gds.graph.project(
              '{graph_name}',
              'CanonicalConcept',
              {{ RELATED_TO: {{ type: 'RELATED_TO', orientation: 'UNDIRECTED' }} }}
            ) YIELD graphName
            """
            await neo4j_client.run_cypher(project_cypher)

            try:
                pagerank_cypher = f"""
                CALL gds.pageRank.stream('{graph_name}')
                YIELD nodeId, score
                RETURN gds.util.asNode(nodeId).id AS concept_id,
                       gds.util.asNode(nodeId).name AS concept_name,
                       score
                ORDER BY score DESC LIMIT 10
                """
                results = await neo4j_client.run_cypher(pagerank_cypher)
                if results:
                    return results
            finally:
                drop_cypher = f"CALL gds.graph.drop('{graph_name}', false) YIELD graphName"
                await neo4j_client.run_cypher(drop_cypher)
        except Exception as e:
            logger.debug(
                "GDS PageRank failed (plugin missing?), falling back to centrality: %s", e)

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
        return await neo4j_client.run_cypher(cypher_centrality)

    async def get_canonical_concepts(self) -> Dict[str, str]:
        cypher = """
        MATCH (c)
        WHERE c:CanonicalConcept OR c:Concept
        RETURN COALESCE(c.id, c.name) AS id, COALESCE(c.name, c.id) AS name
        """
        results = await neo4j_client.run_cypher(cypher)
        return {r["id"]: r["name"] for r in results if r.get("id") and r.get("name")}
