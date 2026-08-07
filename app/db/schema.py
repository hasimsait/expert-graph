import logging
from app.db import neo4j_client

logger = logging.getLogger(__name__)

INITIAL_CONSTRAINTS = [
    # Meta-Graph constraints
    "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE;",
    
    # Data-Graph constraints
    "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE;",
    "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (ch:Chunk) REQUIRE ch.id IS UNIQUE;",

    # Graph Analytics & Entity Resolution constraints
    "CREATE CONSTRAINT source_doc_id IF NOT EXISTS FOR (d:SourceDocument) REQUIRE d.id IS UNIQUE;",
    "CREATE CONSTRAINT raw_entity_name IF NOT EXISTS FOR (r:RawEntity) REQUIRE r.name IS UNIQUE;",
    "CREATE CONSTRAINT canonical_concept_id IF NOT EXISTS FOR (c:CanonicalConcept) REQUIRE c.id IS UNIQUE;",
    "CREATE CONSTRAINT downstream_imp_id IF NOT EXISTS FOR (i:DownstreamImplication) REQUIRE i.id IS UNIQUE;"
]

DEFAULT_META_GRAPH_CONCEPTS = [
    # Top-level concept domain
    {"name": "RELATIONSHIP", "description": "Root relationship concept"}
]

DEFAULT_META_GRAPH_EDGES = []

async def init_db_schema():
    """Create constraints and seed Meta-Graph ontology baseline asynchronously."""
    logger.info("Initializing Neo4j Dual Graph constraints asynchronously...")
    for constraint_cypher in INITIAL_CONSTRAINTS:
        try:
            await neo4j_client.run_cypher(constraint_cypher)
        except Exception as e:
            logger.warning("Error running constraint query: %s", e)

    # Seed Meta-Graph Concepts
    for concept in DEFAULT_META_GRAPH_CONCEPTS:
        query = """
        MERGE (c:Concept {name: $name})
        ON CREATE SET c.description = $description, c.created_at = timestamp()
        """
        await neo4j_client.run_cypher(query, concept)

    # Seed Meta-Graph Edges (MERGE concept nodes first to ensure existence)
    for child, parent, rel_type in DEFAULT_META_GRAPH_EDGES:
        query = f"""
        MERGE (c1:Concept {{name: $child}})
        MERGE (c2:Concept {{name: $parent}})
        MERGE (c1)-[r:{rel_type}]->(c2)
        """
        await neo4j_client.run_cypher(query, {"child": child, "parent": parent})



    logger.info("Meta-Graph ontology and Graph Analytics schema initialized successfully.")
