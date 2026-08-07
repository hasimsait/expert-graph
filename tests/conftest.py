import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pytest
from app.main import container
from app.db.repository.edge_repo import Neo4jEdgeRepository
from app.db.repository.concept_repo import Neo4jConceptRepository
from app.db.repository.document_repo import Neo4jDocumentRepository

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
    real Neo4j repositories and closes connections to avoid event loop issues.
    """
    is_integration = request.node.get_closest_marker("integration") is not None
    
    # Ensure a fresh state for services
    container.reset_singletons()
    search_service = container.search_service()
    search_service.reset_cache()
    
    if is_integration:
        test_edge = Neo4jEdgeRepository()
        test_concept = Neo4jConceptRepository()
        test_document = Neo4jDocumentRepository()
        
        with container.edge_repo.override(test_edge), \
             container.concept_repo.override(test_concept), \
             container.document_repo.override(test_document):
             
            monkeypatch.setattr("app.module_a_sieve.extractor.extract_triples", mock_sieve_extract)
            monkeypatch.setattr("app.module_a_sieve.critic.evaluate_triples", mock_sieve_evaluate)
            
            yield test_edge
            
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

            search_service.reset_cache()
            from app.db.neo4j_client import Neo4jConnection
            Neo4jConnection._driver = None
    else:
        test_repo = InMemoryGraphRepository()
        
        with container.edge_repo.override(test_repo), \
             container.concept_repo.override(test_repo), \
             container.document_repo.override(test_repo):
             
            monkeypatch.setattr("app.module_a_sieve.extractor.extract_triples", mock_sieve_extract)
            monkeypatch.setattr("app.module_a_sieve.critic.evaluate_triples", mock_sieve_evaluate)
            monkeypatch.setattr("app.db.neo4j_client.run_cypher", _mock_run_cypher)
            
            yield test_repo
            
            asyncio.run(test_repo.reset_graph())
            search_service.reset_cache()
