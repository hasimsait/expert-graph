import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.module_a_sieve import extractor, critic
from app.module_a_sieve.ingester import ingest_sieve_output
from app.module_c_mcp.retrieval import expand_meta_graph_concept, fetch_approved_facts

# These tests require a running Neo4j instance — they exercise the full
# ingestion pipeline including direct run_cypher writes to the database.
@pytest.mark.integration
@pytest.mark.anyio
async def test_sieve_pipeline():
    chunk_id = "test_chk_101"
    text = "Acme Corp owes $500,000 to Horizon Bank."
    
    # 1. Extractor
    extraction = await extractor.extract_triples(chunk_id, text)
    assert len(extraction.triples) > 0
    assert extraction.triples[0].relation in ["OWES_DEBT", "DEBT_OBLIGATION"]
    
    # 2. Critic
    evals = await critic.evaluate_triples(extraction)
    assert len(evals) == len(extraction.triples)
    assert evals[0].is_valid is True
    
    # 3. Ingester
    sieve_res = await ingest_sieve_output(extraction, evals)
    assert len(sieve_res.processed_triples) > 0
    assert sieve_res.processed_triples[0]["status"] == "pending"

@pytest.mark.integration
def test_annotator_api():
    with TestClient(app) as client:
        # Ingest text first via API
        ingest_res = client.post("/api/ingest", json={
            "chunk_id": "test_api_chk_1",
            "text": "Apex Corp filed a lawsuit against Cyber Dynamics."
        })
        assert ingest_res.status_code == 200
        assert ingest_res.json()["status"] == "success"

        # Get Pending Queue
        queue_res = client.get("/api/queue")
        assert queue_res.status_code == 200
        queue = queue_res.json()["queue"]
        assert len(queue) > 0

        edge_to_test = queue[0]["edge_id"]

        # Approve Edge
        app_res = client.post(f"/api/approve/{edge_to_test}", json={"user_id": "test_annotator"})
        assert app_res.status_code == 200
        assert app_res.json()["status"] == "approved"

        # Verify Stats
        stats_res = client.get("/api/stats")
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["approved"] >= 1

@pytest.mark.anyio
async def test_meta_expansion_and_retrieval():
    concepts = await expand_meta_graph_concept("FINANCIAL_RELATION")
    assert isinstance(concepts, list)
    assert "FINANCIAL_RELATION" in concepts

    facts = await fetch_approved_facts("OWES_DEBT")
    assert isinstance(facts, list)

def test_mcp_ui_widget_endpoint():
    with TestClient(app) as client:
        response = client.get("/ui/facts-widget?concept=OWES_DEBT")
        assert response.status_code == 200
        assert "ExpertGraph Ground Truth Facts" in response.text
        assert "OWES_DEBT" in response.text

def test_root_dashboard():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200

def test_health_and_stateless_mcp():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["mcp_endpoint"] == "/mcp"

@pytest.mark.integration
def test_pathology_ingestion_and_queue():
    with TestClient(app) as client:
        ingest_res = client.post("/api/ingest", json={
            "chunk_id": "test_path_99",
            "text": "SPECIMEN: Breast biopsy. DIAGNOSIS: Invasive Ductal Carcinoma overexpressing HER2 receptor."
        })
        assert ingest_res.status_code == 200
        assert ingest_res.json()["triples_ingested"] >= 1

        queue_res = client.get("/api/queue")
        assert queue_res.status_code == 200
        queue = queue_res.json()["queue"]
        assert any(q["chunk_id"] == "test_path_99" for q in queue)

