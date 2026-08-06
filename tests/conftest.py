import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.db.repository import set_graph_repository, Neo4jGraphRepository
from tests.mocks.mock_graph import InMemoryGraphRepository
from tests.mocks.mock_sieve import test_mock_extract, test_mock_evaluate

@pytest.fixture(autouse=True)
def setup_test_repository(monkeypatch):
    """
    Autouse fixture that installs InMemoryGraphRepository and patches Sieve LLM calls
    for all pytest test executions. Automatically resets state after each test.
    """
    test_repo = InMemoryGraphRepository()
    set_graph_repository(test_repo)
    
    # Auto-patch LLM calls in test environment
    monkeypatch.setattr("app.module_a_sieve.extractor.extract_triples", test_mock_extract)
    monkeypatch.setattr("app.module_a_sieve.critic.evaluate_triples", test_mock_evaluate)
    monkeypatch.setattr("app.module_b_annotator.router.extract_triples", test_mock_extract)
    monkeypatch.setattr("app.module_b_annotator.router.evaluate_triples", test_mock_evaluate)
    
    yield test_repo
    test_repo.reset_graph()
    set_graph_repository(Neo4jGraphRepository())
