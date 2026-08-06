import os
import json
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from app.services.entity_resolution import EntityResolver, get_entity_resolver, reset_entity_resolver
from app.module_a_sieve.schemas import ExtractionOutput, ExtractedTriple, Entity, CriticEvaluation
from app.module_a_sieve.ingester import ingest_sieve_output
from app.db.neo4j_client import run_cypher

MOCK_ONTOLOGY = {
    "C001": "Invasive Ductal Carcinoma",
    "C002": "Papillary Thyroid Carcinoma"
}

def test_tfidf_vectorizer_setup():
    """Verify raw TF-IDF vectorizer fitting on mock ontology values."""
    values = list(MOCK_ONTOLOGY.values())
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
    matrix = vectorizer.fit_transform(values)
    assert matrix.shape[0] == 2

def test_exact_match():
    """Test exact_match: Input 'Invasive Ductal Carcinoma', expect C001 and confidence 1.0."""
    resolver = EntityResolver(ontology_dict=MOCK_ONTOLOGY)
    result = resolver.resolve_entity("Invasive Ductal Carcinoma")
    
    assert result is not None
    assert result["canonical_id"] == "C001"
    assert result["canonical_name"] == "Invasive Ductal Carcinoma"
    assert result["confidence"] == pytest.approx(1.0, abs=1e-3)

def test_fuzzy_match():
    """Test fuzzy_match: Input 'invasive ductal breast carcinoma', expect C001 with confidence > 0.6."""
    resolver = EntityResolver(ontology_dict=MOCK_ONTOLOGY)
    result = resolver.resolve_entity("invasive ductal breast carcinoma")
    
    assert result is not None
    assert result["canonical_id"] == "C001"
    assert result["canonical_name"] == "Invasive Ductal Carcinoma"
    assert result["confidence"] > 0.6

def test_no_match():
    """Test no_match: Input 'completely irrelevant string', expect None or confidence < 0.4."""
    resolver = EntityResolver(ontology_dict=MOCK_ONTOLOGY, threshold=0.4)
    result = resolver.resolve_entity("completely irrelevant string")
    
    assert result is None or result["confidence"] < 0.4

def test_ontology_loading_from_env(tmp_path, monkeypatch):
    """Test initializing EntityResolver from JSON file specified in ONTOLOGY_PATH environment variable."""
    ontology_file = tmp_path / "medical_ontology.json"
    ontology_file.write_text(json.dumps(MOCK_ONTOLOGY))
    
    monkeypatch.setenv("ONTOLOGY_PATH", str(ontology_file))
    
    resolver = EntityResolver()
    assert resolver.ontology == MOCK_ONTOLOGY
    
    res = resolver.resolve_entity("Invasive Ductal Carcinoma")
    assert res is not None
    assert res["canonical_id"] == "C001"

@pytest.mark.anyio
async def test_graph_ingester_entity_resolution_integration():
    """Test that Graph Ingester performs ER and maps raw text entities to canonical concepts."""
    resolver = EntityResolver(ontology_dict=MOCK_ONTOLOGY)
    reset_entity_resolver(resolver)
    
    extraction = ExtractionOutput(
        chunk_id="er_test_chk_01",
        chunk_text="Patient presents with invasive ductal breast carcinoma.",
        triples=[
            ExtractedTriple(
                subject=Entity(name="invasive ductal breast carcinoma", type="DISEASE"),
                relation="DIAGNOSED_WITH",
                object=Entity(name="Breast biopsy", type="PROCEDURE")
            )
        ]
    )
    evaluations = [
        CriticEvaluation(triple_index=0, is_valid=True, confidence=0.95, critique_notes="Valid diagnosis")
    ]
    
    sieve_res = await ingest_sieve_output(extraction, evaluations)
    assert len(sieve_res.processed_triples) == 1
    processed = sieve_res.processed_triples[0]
    
    assert processed["subject_resolution"] is not None
    assert processed["subject_resolution"]["canonical_id"] == "C001"
    assert processed["subject_resolution"]["confidence"] > 0.6
    
    # Cleanup global resolver
    reset_entity_resolver(None)
