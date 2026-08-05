import logging
from app.db.neo4j_client import run_cypher

logger = logging.getLogger(__name__)

INITIAL_CONSTRAINTS = [
    # Meta-Graph constraints
    "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE;",
    
    # Data-Graph constraints
    "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE;",
    "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (ch:Chunk) REQUIRE ch.id IS UNIQUE;"
]

DEFAULT_META_GRAPH_CONCEPTS = [
    # Top-level concept domain
    {"name": "RELATIONSHIP", "description": "Root relationship concept"},
    
    {"name": "FINANCIAL_RELATION", "description": "Financial links between entities"},
    {"name": "OWES_DEBT", "description": "Financial obligation or debt relationship"},
    {"name": "TRANSFERS_FUNDS", "description": "Direct monetary transfer"},
    {"name": "INVESTED_IN", "description": "Equity or venture investment"},
    {"name": "LIABLE_FOR", "description": "Debt liability synonym"},
    {"name": "PAID_TO", "description": "Fund transfer synonym"},
    
    {"name": "LEGAL_RELATION", "description": "Legal or regulatory connection"},
    {"name": "LAWSUIT_AGAINST", "description": "Litigation or legal conflict"},
    {"name": "CONTRACT_WITH", "description": "Binding agreement between entities"},
    {"name": "SUED", "description": "Lawsuit synonym"},
    
    {"name": "ORGANIZATIONAL_RELATION", "description": "Corporate or structural link"},
    {"name": "SUBSIDIARY_OF", "description": "Corporate ownership hierarchy"},
    {"name": "EMPLOYED_BY", "description": "Employment or executive relationship"},
    {"name": "PARTNERED_WITH", "description": "Strategic business partnership"}
]

DEFAULT_META_GRAPH_EDGES = [
    # Subclass mappings: (Child, Parent)
    ("FINANCIAL_RELATION", "RELATIONSHIP", "SUBCLASS_OF"),
    ("OWES_DEBT", "FINANCIAL_RELATION", "SUBCLASS_OF"),
    ("TRANSFERS_FUNDS", "FINANCIAL_RELATION", "SUBCLASS_OF"),
    ("INVESTED_IN", "FINANCIAL_RELATION", "SUBCLASS_OF"),
    
    ("LEGAL_RELATION", "RELATIONSHIP", "SUBCLASS_OF"),
    ("LAWSUIT_AGAINST", "LEGAL_RELATION", "SUBCLASS_OF"),
    ("CONTRACT_WITH", "LEGAL_RELATION", "SUBCLASS_OF"),
    
    ("ORGANIZATIONAL_RELATION", "RELATIONSHIP", "SUBCLASS_OF"),
    ("SUBSIDIARY_OF", "ORGANIZATIONAL_RELATION", "SUBCLASS_OF"),
    ("EMPLOYED_BY", "ORGANIZATIONAL_RELATION", "SUBCLASS_OF"),
    ("PARTNERED_WITH", "ORGANIZATIONAL_RELATION", "SUBCLASS_OF"),
    
    # Synonyms
    ("LIABLE_FOR", "OWES_DEBT", "SYNONYM_OF"),
    ("PAID_TO", "TRANSFERS_FUNDS", "SYNONYM_OF"),
    ("SUED", "LAWSUIT_AGAINST", "SYNONYM_OF")
]

def init_db_schema():
    """Create constraints and seed Meta-Graph ontology baseline."""
    logger.info("Initializing Neo4j Dual Graph constraints...")
    for constraint_cypher in INITIAL_CONSTRAINTS:
        try:
            run_cypher(constraint_cypher)
        except Exception as e:
            logger.warning("Error running constraint query: %s", e)

    # Seed Meta-Graph Concepts
    for concept in DEFAULT_META_GRAPH_CONCEPTS:
        query = """
        MERGE (c:Concept {name: $name})
        ON CREATE SET c.description = $description, c.created_at = timestamp()
        """
        run_cypher(query, concept)

    # Seed Meta-Graph Edges (MERGE concept nodes first to ensure existence)
    for child, parent, rel_type in DEFAULT_META_GRAPH_EDGES:
        query = f"""
        MERGE (c1:Concept {{name: $child}})
        MERGE (c2:Concept {{name: $parent}})
        MERGE (c1)-[r:{rel_type}]->(c2)
        """
        run_cypher(query, {"child": child, "parent": parent})

    logger.info("Meta-Graph ontology initialized successfully.")
