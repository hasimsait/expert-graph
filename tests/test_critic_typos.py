import pytest
from app.module_a_sieve.schemas import ExtractedTriple, Entity, TypoCorrection, CriticEvaluation
from app.module_a_sieve.critic import validate_and_apply_typo_corrections
from app.main import container

def test_critic_exact_typo_correction():
    triple = ExtractedTriple(
        subject=Entity(name="Invasive Ductal Carcinma", type="DISEASE"),
        relation="ASSOCIATED_GENE",
        object=Entity(name="HER2", type="GENE")
    )
    corrections = [TypoCorrection(original_typo="Carcinma", replacement="Carcinoma")]
    fixed = validate_and_apply_typo_corrections(triple, corrections, "Invasive Ductal Carcinoma biopsy")
    
    assert fixed.subject.name == "Invasive Ductal Carcinoma"

def test_critic_fuzzy_typo_correction():
    triple = ExtractedTriple(
        subject=Entity(name="Papilary Thyroid Carcinoma", type="DISEASE"),
        relation="ASSOCIATED_GENE",
        object=Entity(name="BRAF", type="GENE")
    )
    corrections = [TypoCorrection(original_typo="Papilary", replacement="Papillary")]
    fixed = validate_and_apply_typo_corrections(triple, corrections, "Papillary Thyroid Carcinoma sample")
    
    assert fixed.subject.name == "Papillary Thyroid Carcinoma"

def test_critic_rejects_unrelated_freetext_substitution():
    triple = ExtractedTriple(
        subject=Entity(name="Invasive Ductal Carcinoma", type="DISEASE"),
        relation="ASSOCIATED_GENE",
        object=Entity(name="HER2", type="GENE")
    )
    corrections = [TypoCorrection(original_typo="Carcinoma", replacement="Heart Failure")]
    fixed = validate_and_apply_typo_corrections(triple, corrections, "Invasive Ductal Carcinoma biopsy")
    
    assert fixed.subject.name == "Invasive Ductal Carcinoma"

def test_critic_word_boundary_prevents_substring_corruption():
    """Verify that typo 'art' -> 'heart' does NOT corrupt 'Artery' into 'Heartery' or 'Cartilage' into 'Cheartilage'."""
    triple = ExtractedTriple(
        subject=Entity(name="Coronary Artery Disease", type="DISEASE"),
        relation="AFFECTS",
        object=Entity(name="Costal Cartilage", type="ANATOMY")
    )
    corrections = [TypoCorrection(original_typo="art", replacement="heart")]
    fixed = validate_and_apply_typo_corrections(triple, corrections, "Patient has heart disease and coronary artery issues.")
    
    # Must remain 'Coronary Artery Disease' and 'Costal Cartilage', not 'Heartery' or 'Cheartilage'
    assert fixed.subject.name == "Coronary Artery Disease"
    assert fixed.object.name == "Costal Cartilage"

@pytest.mark.anyio
async def test_graph_analytics_implications_and_pagerank():
    repo = container.document_repo()
    
    implications = await repo.get_document_implications("doc_101")
    assert isinstance(implications, list)
    
    pagerank = await repo.run_concept_pagerank()
    assert isinstance(pagerank, list)
