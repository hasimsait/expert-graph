import pytest
import asyncio
from app.services.tfidf_retrieval import TFIDFRetriever

def test_dynamic_vocab_append():
    TFIDFRetriever.reset_cache()
    
    # Simulate DB load with just one document
    doc1 = {
        "edge_id": "e1",
        "subject": "cancer",
        "subject_type": "DISEASE",
        "relation": "has_gene",
        "object": "BRCA1",
        "object_type": "GENE",
        "chunk_text": "Cancer often involves BRCA1 mutations."
    }
    
    # Initialize index
    TFIDFRetriever.add_fact_delta(doc1)
    initial_vocab_size = len(TFIDFRetriever._vectorizer.vocabulary_)
    
    # Now simulate delta append with ENTIRELY NOVEL words
    doc2 = {
        "edge_id": "e2",
        "subject": "TARDIS",
        "subject_type": "MACHINE",
        "relation": "travels_through",
        "object": "TIME",
        "object_type": "DIMENSION",
        "chunk_text": "The TARDIS travels through space and time vortex."
    }
    
    TFIDFRetriever.add_fact_delta(doc2)
    new_vocab_size = len(TFIDFRetriever._vectorizer.vocabulary_)
    
    assert new_vocab_size > initial_vocab_size, "Vocabulary should expand with novel words"
    
    # Query for the completely novel word
    results = TFIDFRetriever.rank_facts("TARDIS", [doc1, doc2])
    
    # Since we are using true TF-IDF, it should match the novelty, 
    # not fall back to the unranked DB facts
    assert len(results) == 1
    assert results[0]["subject"] == "TARDIS"

