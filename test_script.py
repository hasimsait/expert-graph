import asyncio
from app.db.neo4j_client import run_cypher
from tests.test_graph_analytics import _setup_test_db, _teardown_test_db

async def main():
    await _setup_test_db()
    
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
    res = await run_cypher(cypher, {"document_id": "test_doc_101"})
    print("RES:", res)
    
    await _teardown_test_db()

asyncio.run(main())
