import asyncio
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.neo4j_client import run_cypher
from tests.mocks.mock_graph import mock_graph_store

client = TestClient(app)

def setup_module(module):
    """Seed a mock database setup for graph analytics tests using generic schema."""
    # 1. Clean existing graph state
    try:
        asyncio.run(run_cypher("MATCH (n) DETACH DELETE n"))
        asyncio.run(mock_graph_store.reset_graph())
    except Exception:
        pass

    # 2. Seed generic schema:
    seed_cypher = """
    CREATE (doc1:SourceDocument {id: 'doc_101', title: 'Diagnostic Biopsy Report A'})
    CREATE (doc2:SourceDocument {id: 'doc_102', title: 'Endocrine Biopsy Report B'})

    CREATE (raw1:RawEntity {name: 'invasive ductal breast carcinoma'})
    CREATE (raw2:RawEntity {name: 'papillary thyroid carcinoma'})

    CREATE (c1:CanonicalConcept {id: 'C001', name: 'Invasive Ductal Carcinoma'})
    CREATE (c2:CanonicalConcept {id: 'C002', name: 'Papillary Thyroid Carcinoma'})
    CREATE (c3:CanonicalConcept {id: 'C003', name: 'General Oncology Hub'})

    CREATE (imp1:DownstreamImplication {id: 'imp_201', name: 'Targeted Chemotherapy Regimen', description: 'HER2 targeted therapy indicated'})
    CREATE (imp2:DownstreamImplication {id: 'imp_202', name: 'Thyroidectomy Evaluation', description: 'Surgical excision recommended'})

    CREATE (doc1)-[:CONTAINS]->(raw1)
    CREATE (doc2)-[:CONTAINS]->(raw2)

    CREATE (raw1)-[:MAPPED_TO {confidence: 0.95}]->(c1)
    CREATE (raw2)-[:MAPPED_TO {confidence: 0.91}]->(c2)

    CREATE (c1)<-[:RELATED_TO]-(imp1)
    CREATE (c2)<-[:RELATED_TO]-(imp2)

    CREATE (c2)-[:RELATED_TO]->(c1)
    CREATE (c3)-[:RELATED_TO]->(c1)
    """
    try:
        asyncio.run(run_cypher(seed_cypher))
    except Exception:
        pass

    # Seed mock store for offline/test fallback mode
    mock_graph_store.seed_analytics_data(
        documents=[
            {"id": "doc_101", "title": "Diagnostic Biopsy Report A"},
            {"id": "doc_102", "title": "Endocrine Biopsy Report B"}
        ],
        raw_entities=[
            {"name": "invasive ductal breast carcinoma", "doc_id": "doc_101", "mapped_to": "C001"},
            {"name": "papillary thyroid carcinoma", "doc_id": "doc_102", "mapped_to": "C002"}
        ],
        concepts=[
            {"id": "C001", "name": "Invasive Ductal Carcinoma"},
            {"id": "C002", "name": "Papillary Thyroid Carcinoma"},
            {"id": "C003", "name": "General Oncology Hub"}
        ],
        implications=[
            {"id": "imp_201", "name": "Targeted Chemotherapy Regimen", "description": "HER2 targeted therapy indicated", "concept_id": "C001"},
            {"id": "imp_202", "name": "Thyroidectomy Evaluation", "description": "Surgical excision recommended", "concept_id": "C002"}
        ],
        concept_links=[
            ("C002", "C001"),
            ("C003", "C001")
        ]
    )

def test_4_hop_implication_match():
    """Test calling /api/analytics/implications/{document_id} and assert 4-hop linked DownstreamImplication nodes."""
    response = client.get("/api/analytics/implications/doc_101")
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == "doc_101"
    
    implications = data["implications"]
    assert len(implications) >= 1
    
    imp_ids = [item["implication_id"] for item in implications]
    assert "imp_201" in imp_ids
    
    matched = next(item for item in implications if item["implication_id"] == "imp_201")
    assert matched["canonical_id"] == "C001"
    assert matched["implication_name"] == "Targeted Chemotherapy Regimen"

def test_concept_pagerank():
    """Test calling /api/analytics/pagerank/concepts and assert C001 returns highest centrality score."""
    response = client.get("/api/analytics/pagerank/concepts")
    assert response.status_code == 200
    data = response.json()
    
    top_concepts = data["top_concepts"]
    assert len(top_concepts) >= 1
    
    top_concept = top_concepts[0]
    assert top_concept["concept_id"] == "C001"
    assert top_concept["score"] > 0
    
    scores = [item["score"] for item in top_concepts]
    assert scores == sorted(scores, reverse=True)
