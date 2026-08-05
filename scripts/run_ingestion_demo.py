import sys
import os
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.module_a_sieve.extractor import extract_triples
from app.module_a_sieve.critic import evaluate_triples
from app.module_a_sieve.ingester import ingest_sieve_output

logging.basicConfig(level=logging.INFO)

SAMPLE_CHUNKS = [
    {
        "id": "chk_001",
        "text": "Acme Corporation owes $12,500,000 to Horizon Financial Trust following the restructuring agreement."
    },
    {
        "id": "chk_002",
        "text": "Vanguard Tech filed a lawsuit against Quantum Dynamics regarding alleged patent infringement on neural chips."
    },
    {
        "id": "chk_003",
        "text": "Apex Capital invested $45,000,000 in BioGenix Systems as part of Series C funding."
    },
    {
        "id": "chk_004",
        "text": "Starlight Global acquired a 40% equity stake in SolarTech Solutions."
    }
]

def run_demo():
    print("=== EXPERTGRAPH SIEVE INGESTION DEMO ===")
    for chunk in SAMPLE_CHUNKS:
        print(f"\nProcessing Chunk ID: {chunk['id']}")
        print(f"Text: '{chunk['text']}'")
        
        # 1. Extractor
        extraction = extract_triples(chunk["id"], chunk["text"])
        print(f"-> Extracted {len(extraction.triples)} proposed triples.")
        
        # 2. Critic
        evaluations = evaluate_triples(extraction)
        valid_count = sum(1 for e in evaluations if e.is_valid)
        print(f"-> Critic validated {valid_count}/{len(evaluations)} triples.")
        
        # 3. Ingester
        sieve_result = ingest_sieve_output(extraction, evaluations)
        print(f"-> Ingested {len(sieve_result.processed_triples)} pending edges into graph.")
        for record in sieve_result.processed_triples:
            print(f"   • ({record['subject']['name']}) -[{record['relation']}]-> ({record['object']['name']}) [status: pending]")

    print("\nDemo Sieve Pipeline completed successfully.")

if __name__ == "__main__":
    run_demo()
