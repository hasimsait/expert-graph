import pytest
from app.services.tfidf_retrieval import TFIDFRetriever

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
