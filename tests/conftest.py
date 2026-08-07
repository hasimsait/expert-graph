import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.db.repository import set_graph_repository, Neo4jGraphRepository
from app.services.tfidf_retrieval import TFIDFRetriever
from tests.mocks.mock_graph import InMemoryGraphRepository
from tests.mocks.mock_sieve import mock_sieve_extract, mock_sieve_evaluate

async def _mock_run_cypher(query, parameters=None):
    """No-op Cypher mock for tests — returns empty results without needing Neo4j."""
    return []

@pytest.fixture(autouse=True)
def setup_test_repository(monkeypatch, request):
    """
    Autouse fixture that installs InMemoryGraphRepository and patches Sieve LLM calls
    for all pytest test executions. If the test is marked 'integration', it uses the 
    real Neo4jGraphRepository and closes connections to avoid event loop issues.
    """
    TFIDFRetriever.reset_cache()
    
    is_integration = request.node.get_closest_marker("integration") is not None
    
    if is_integration:
        test_repo = Neo4jGraphRepository()
        set_graph_repository(test_repo)
        
        monkeypatch.setattr("app.module_a_sieve.extractor.extract_triples", mock_sieve_extract)
        monkeypatch.setattr("app.module_a_sieve.critic.evaluate_triples", mock_sieve_evaluate)
        monkeypatch.setattr("app.module_b_annotator.router.extract_triples", mock_sieve_extract)
        monkeypatch.setattr("app.module_b_annotator.router.evaluate_triples", mock_sieve_evaluate)
        
        yield test_repo
        
        async def cleanup():
            from app.db.neo4j_client import run_cypher
            # Clean up edges, chunks, and orphaned entities created by tests
            await run_cypher("MATCH ()-[r]->() WHERE r.chunk_id STARTS WITH 'test_' DELETE r")
            await run_cypher("MATCH (c:Chunk) WHERE c.id STARTS WITH 'test_' DETACH DELETE c")
            await run_cypher("MATCH (n:Entity) WHERE NOT (n)--() DETACH DELETE n")
            
        try:
            asyncio.run(cleanup())
        except Exception as e:
            print("Failed to clean up integration test database:", e)

        TFIDFRetriever.reset_cache()
        from app.db.neo4j_client import Neo4jConnection
        # Clear the driver cache so the next test (in a new event loop) recreates it
        Neo4jConnection._driver = None
    else:
        test_repo = InMemoryGraphRepository()
        set_graph_repository(test_repo)
        
        monkeypatch.setattr("app.module_a_sieve.extractor.extract_triples", mock_sieve_extract)
        monkeypatch.setattr("app.module_a_sieve.critic.evaluate_triples", mock_sieve_evaluate)
        monkeypatch.setattr("app.module_b_annotator.router.extract_triples", mock_sieve_extract)
        monkeypatch.setattr("app.module_b_annotator.router.evaluate_triples", mock_sieve_evaluate)
        monkeypatch.setattr("app.module_a_sieve.ingester.run_cypher", _mock_run_cypher)
        
        yield test_repo
        
        asyncio.run(test_repo.reset_graph())
        TFIDFRetriever.reset_cache()
        set_graph_repository(Neo4jGraphRepository())


