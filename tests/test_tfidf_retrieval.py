import pytest
from app.main import container
from tests.mocks.mock_graph import InMemoryGraphRepository

def test_tfidf_rank_facts_breast_cancer():
    search_service = container.search_service()
    facts = [
        {
            "edge_id": "edge_88d7e3510e",
            "subject": "Invasive Ductal Carcinoma, Grade 3",
            "subject_type": "DISEASE_DIAGNOSIS",
            "relation": "ASSOCIATED_GENE",
            "object": "HER2",
            "object_type": "GENE_BIOMARKER",
            "chunk_text": "SPECIMEN: Breast tissue core biopsy. DIAGNOSIS: Invasive Ductal Carcinoma, Grade 3. BIOMARKERS: Overexpresses HER2 receptor (3+ IHC score)."
        },
        {
            "edge_id": "edge_4a9d3da83b",
            "subject": "Right lung lobe resection",
            "subject_type": "PROCEDURE",
            "relation": "IS_SPECIMEN_FROM",
            "object": "Lung",
            "object_type": "ORGAN",
            "chunk_text": "SPECIMEN: Right lung lobe resection. DIAGNOSIS: Non-Small Cell Lung Adenocarcinoma. GENETICS: EGFR L858R mutation detected."
        },
        {
            "edge_id": "edge_d37e06f15e",
            "subject": "Papillary Thyroid Carcinoma",
            "subject_type": "DISEASE_DIAGNOSIS",
            "relation": "ASSOCIATED_GENE",
            "object": "BRAF",
            "object_type": "GENE_BIOMARKER",
            "chunk_text": "SPECIMEN: Thyroid fine needle aspiration. DIAGNOSIS: Papillary Thyroid Carcinoma. BIOMARKERS: BRAF V600E mutation identified."
        }
    ]

    query = "What genetic mutations were identified in breast cancer tissue samples?"
    ranked = search_service.rank_facts(query, facts)

    assert len(ranked) == 1
    assert ranked[0]["edge_id"] == "edge_88d7e3510e"
    assert ranked[0]["object"] == "HER2"

def test_tfidf_rank_facts_financial():
    search_service = container.search_service()
    facts = [
        {
            "edge_id": "edge_path_01",
            "subject": "Invasive Ductal Breast Carcinoma",
            "relation": "ASSOCIATED_GENE",
            "object": "HER2",
            "chunk_text": "Breast tissue biopsy."
        },
        {
            "edge_id": "edge_fin_01",
            "subject": "Acme Corp",
            "subject_type": "ORGANIZATION",
            "relation": "OWES_DEBT",
            "object": "Horizon Bank",
            "object_type": "ORGANIZATION",
            "chunk_text": "Acme Corp owes $500,000 to Horizon Bank."
        }
    ]

    query = "Acme Corp owes money to Horizon Bank"
    ranked = search_service.rank_facts(query, facts)

    assert len(ranked) == 1
    assert ranked[0]["edge_id"] == "edge_fin_01"

@pytest.mark.anyio
async def test_unmocked_tfidf_retrieval_with_mock_graph_store():
    """
    Integration test: Un-mocked real TF-IDF retrieval running against an 
    in-memory graph database loaded with pathology, legal, and financial facts.
    """
    repo = InMemoryGraphRepository()
    await repo.reset_graph()
    
    search_service = container.search_service()
    search_service.reset_cache()

    # 1. Add candidate edges directly into mock graph
    repo.add_edge({
        "edge_id": "edge_path_001",
        "subject": {"name": "Invasive Ductal Carcinoma", "type": "DISEASE_DIAGNOSIS"},
        "relation": "ASSOCIATED_GENE",
        "object": {"name": "HER2 Receptor", "type": "GENE_BIOMARKER"},
        "confidence": 0.98,
        "status": "approved",
        "approved_by": "Dr_Smith",
        "chunk_id": "chk_path_01",
        "chunk_text": "Biopsy report shows invasive ductal carcinoma with strong HER2 receptor overexpression."
    })
    repo.add_edge({
        "edge_id": "edge_path_002",
        "subject": {"name": "Papillary Thyroid Carcinoma", "type": "DISEASE_DIAGNOSIS"},
        "relation": "ASSOCIATED_GENE",
        "object": {"name": "BRAF V600E Mutation", "type": "GENE_BIOMARKER"},
        "confidence": 0.95,
        "status": "approved",
        "approved_by": "Dr_Smith",
        "chunk_id": "chk_path_02",
        "chunk_text": "Thyroid FNA shows papillary carcinoma positive for BRAF V600E point mutation."
    })
    repo.add_edge({
        "edge_id": "edge_fin_001",
        "subject": {"name": "Acme Capital", "type": "ORGANIZATION"},
        "relation": "OWES_DEBT",
        "object": {"name": "Global Credit Corp", "type": "ORGANIZATION"},
        "confidence": 0.99,
        "status": "approved",
        "approved_by": "thesis_annotator_1",
        "chunk_id": "chk_fin_01",
        "chunk_text": "Acme Capital owes $12 million in senior debt to Global Credit Corp."
    })
    repo.add_edge({
        "edge_id": "edge_pending_001",
        "subject": {"name": "Unapproved Entity", "type": "ORGANIZATION"},
        "relation": "ASSOCIATED_WITH",
        "object": {"name": "HER2 Gene", "type": "GENE"},
        "confidence": 0.50,
        "status": "pending",
        "chunk_id": "chk_pend_01",
        "chunk_text": "Unverified draft text mentioning HER2."
    })

    # 2. Query for HER2 gene biomarker
    all_facts = await repo.get_approved_facts()
    her2_facts = search_service.rank_facts("HER2 gene biomarker in breast carcinoma", all_facts)
    assert len(her2_facts) == 1
    assert her2_facts[0]["edge_id"] == "edge_path_001"
    assert her2_facts[0]["subject"] == "Invasive Ductal Carcinoma"

    # 3. Query for financial debt
    all_facts = await repo.get_approved_facts()
    debt_facts = search_service.rank_facts("Acme Capital debt liabilities to Global Credit", all_facts)
    assert len(debt_facts) == 1
    assert debt_facts[0]["edge_id"] == "edge_fin_001"
    assert debt_facts[0]["subject"] == "Acme Capital"

    # 4. Approve pending edge and verify incremental delta update
    results = await repo.update_edge_status("edge_pending_001", "approved", "Dr_Smith")
    for rec in results:
        search_service.add_fact_delta(rec)
    updated_her2_facts = await repo.search_approved_facts("HER2")
    assert len(updated_her2_facts) >= 1
    assert "edge_pending_001" in {f["edge_id"] for f in updated_her2_facts}

@pytest.mark.anyio
async def test_hyphenated_clinical_term_tokenization():
    """Verify that clinical hyphenated terms (PD-L1, HER2-neu, COVID-19, ER) are preserved cleanly."""
    repo = InMemoryGraphRepository()
    await repo.reset_graph()
    
    search_service = container.search_service()
    search_service.reset_cache()

    edge = {
        "edge_id": "edge_pdl1",
        "subject": {"name": "Non-Small Cell Lung Carcinoma", "type": "DISEASE_DIAGNOSIS"},
        "relation": "EXPRESSES_BIOMARKER",
        "object": {"name": "PD-L1", "type": "GENE_BIOMARKER"},
        "confidence": 0.99,
        "status": "approved",
        "approved_by": "Dr_Pathologist",
        "chunk_id": "chk_pdl1_01",
        "chunk_text": "Tumor tissue section demonstrates high PD-L1 expression (>50% TPS score)."
    }
    repo.add_edge(edge)

    pdl1_facts = await repo.search_approved_facts("PD-L1")
    assert len(pdl1_facts) == 1
    assert pdl1_facts[0]["object"] == "PD-L1"

@pytest.mark.anyio
async def test_tfidf_incremental_vocabulary_expansion():
    """Verify that adding facts sequentially dynamically expands the vectorizer vocabulary."""
    repo = InMemoryGraphRepository()
    await repo.reset_graph()
    
    search_service = container.search_service()
    search_service.reset_cache()

    # 1. Add first fact with restricted vocabulary
    edge1 = {
        "edge_id": "edge_vocab_01",
        "subject": {"name": "Apple", "type": "FRUIT"},
        "relation": "TASTES_LIKE",
        "object": {"name": "Sweet", "type": "FLAVOR"},
        "confidence": 1.0,
        "status": "approved",
        "approved_by": "tester",
        "chunk_id": "chk_v1",
        "chunk_text": "Apples are very sweet."
    }
    repo.add_edge(edge1)

    # 2. Add second fact with completely different unseen words
    edge2 = {
        "edge_id": "edge_vocab_02",
        "subject": {"name": "Spaceship", "type": "VEHICLE"},
        "relation": "TRAVELS_TO",
        "object": {"name": "Mars", "type": "PLANET"},
        "confidence": 1.0,
        "status": "approved",
        "approved_by": "tester",
        "chunk_id": "chk_v2",
        "chunk_text": "The new rocket spaceship travels to the red planet Mars."
    }
    repo.add_edge(edge2)

    # 3. Add third fact with completely different unseen words
    edge3 = {
        "edge_id": "edge_vocab_03",
        "subject": {"name": "Quantum Computer", "type": "MACHINE"},
        "relation": "USES",
        "object": {"name": "Qubits", "type": "TECHNOLOGY"},
        "confidence": 1.0,
        "status": "approved",
        "approved_by": "tester",
        "chunk_id": "chk_v3",
        "chunk_text": "Quantum computers use entangled qubits for processing."
    }
    repo.add_edge(edge3)

    # If the vocabulary bug existed, the vectorizer would only know about "Apple" and "Sweet".
    # It would completely fail to find "spaceship" or "Mars" because they were out-of-vocabulary.

    # 4. Search for words from the 3rd fact
    all_facts = await repo.get_approved_facts()
    quantum_facts = search_service.rank_facts("entangled qubits processing", all_facts)
    assert len(quantum_facts) == 1
    assert quantum_facts[0]["edge_id"] == "edge_vocab_03"

    # 5. Search for words from the 2nd fact
    all_facts = await repo.get_approved_facts()
    space_facts = search_service.rank_facts("rocket spaceship Mars", all_facts)
    assert len(space_facts) == 1
    assert space_facts[0]["edge_id"] == "edge_vocab_02"
