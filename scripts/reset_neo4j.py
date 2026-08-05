import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.neo4j_client import run_cypher, Neo4jConnection
from app.db.schema import init_db_schema
from app.db.mock_graph import mock_graph_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_neo4j")

def reset_neo4j():
    print("\n=======================================================")
    print("  RESETTING NEO4J DUAL GRAPH DATABASE")
    print("=======================================================\n")

    logger.info("Wiping all nodes, edges, and relationships from Neo4j & Mock Store...")
    cypher_wipe = "MATCH (n) DETACH DELETE n"
    run_cypher(cypher_wipe)
    mock_graph_store.reset()
    print("  ✓ All existing nodes and edges deleted successfully.")

    logger.info("Re-initializing constraints and Meta-Graph ontology baseline...")
    init_db_schema()
    print("  ✓ Baseline Meta-Graph concepts and relationships re-seeded.")

    print("\n=======================================================")
    print("  NEO4J DATABASE FRESHENED & READY FOR INGESTION!")
    print("=======================================================\n")

if __name__ == "__main__":
    reset_neo4j()
