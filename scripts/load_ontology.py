import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.ontology_loader import load_custom_ontology_json, load_umls_rrf

logging.basicConfig(level=logging.INFO)

def main():
    parser = argparse.ArgumentParser(description="Load custom ontologies or UMLS RRF files into ExpertGraph Meta-Graph.")
    parser.add_argument("--json", type=str, help="Path to custom ontology JSON file.")
    parser.add_argument("--mrconso", type=str, help="Path to UMLS MRCONSO.RRF file.")
    parser.add_argument("--mrrel", type=str, help="Path to UMLS MRREL.RRF file.")
    parser.add_argument("--limit", type=int, default=1000, help="Max UMLS records to import.")

    args = parser.parse_args()

    if args.json:
        print(f"Loading custom ontology JSON from '{args.json}'...")
        res = load_custom_ontology_json(args.json)
        print(f"-> Success: {res['concepts_loaded']} concepts, {res['relationships_loaded']} relationships loaded.")
    elif args.mrconso:
        print(f"Loading UMLS RRF files ('{args.mrconso}', '{args.mrrel}')...")
        res = load_umls_rrf(args.mrconso, args.mrrel or "", max_records=args.limit)
        print(f"-> Success: {res['concepts_loaded']} concepts, {res['relationships_loaded']} relationships loaded.")
    else:
        print("Defaulting to loading sample medical ontology...")
        sample_path = os.path.join(os.path.dirname(__file__), "sample_medical_ontology.json")
        res = load_custom_ontology_json(sample_path)
        print(f"-> Success: {res['concepts_loaded']} concepts, {res['relationships_loaded']} relationships loaded.")

if __name__ == "__main__":
    main()
