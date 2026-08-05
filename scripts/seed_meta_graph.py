import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.schema import init_db_schema

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    print("Seeding ExpertGraph Meta-Graph Ontology...")
    init_db_schema()
    print("Meta-Graph Seeding Complete.")
