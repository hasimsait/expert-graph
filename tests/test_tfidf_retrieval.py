import pytest
from app.services.tfidf_retrieval import TFIDFRetriever
from tests.mocks.mock_graph import InMemoryGraphRepository

def test_tfidf_rank_facts_breast_cancer():
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
    ranked = TFIDFRetriever.rank_facts(query, facts)

    assert len(ranked) == 1
    assert ranked[0]["edge_id"] == "edge_88d7e3510e"
    assert ranked[0]["object"] == "HER2"

def test_tfidf_rank_facts_financial():
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
    ranked = TFIDFRetriever.rank_facts(query, facts)

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
    TFIDFRetriever.reset_cache()

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
    her2_facts = await repo.get_approved_facts("HER2 gene biomarker in breast carcinoma")
    assert len(her2_facts) == 1
    assert her2_facts[0]["edge_id"] == "edge_path_001"
    assert her2_facts[0]["subject"] == "Invasive Ductal Carcinoma"

    # 3. Query for financial debt
    debt_facts = await repo.get_approved_facts("Acme Capital debt liabilities to Global Credit")
    assert len(debt_facts) == 1
    assert debt_facts[0]["edge_id"] == "edge_fin_001"
    assert debt_facts[0]["subject"] == "Acme Capital"

    # 4. Approve pending edge and verify incremental delta update
    await repo.update_edge_status("edge_pending_001", "approved", "Dr_Smith")
    updated_her2_facts = await repo.get_approved_facts("HER2")
    assert len(updated_her2_facts) == 2
    assert {f["edge_id"] for f in updated_her2_facts} == {"edge_path_001", "edge_pending_001"}
