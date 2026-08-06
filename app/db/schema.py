import logging
from app.db.neo4j_client import run_cypher

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

    # Seed baseline Graph Analytics nodes & relationships
    seed_analytics_cypher = """
    MERGE (doc1:SourceDocument {id: 'doc_101'}) ON CREATE SET doc1.title = 'Diagnostic Biopsy Report A'
    MERGE (doc2:SourceDocument {id: 'doc_102'}) ON CREATE SET doc2.title = 'Endocrine Biopsy Report B'

    MERGE (raw1:RawEntity {name: 'invasive ductal breast carcinoma'})
    MERGE (raw2:RawEntity {name: 'papillary thyroid carcinoma'})

    MERGE (c1:CanonicalConcept {id: 'C001'}) ON CREATE SET c1.name = 'Invasive Ductal Carcinoma'
    MERGE (c2:CanonicalConcept {id: 'C002'}) ON CREATE SET c2.name = 'Papillary Thyroid Carcinoma'
    MERGE (c3:CanonicalConcept {id: 'C003'}) ON CREATE SET c3.name = 'General Oncology Hub'

    MERGE (imp1:DownstreamImplication {id: 'imp_201'}) ON CREATE SET imp1.name = 'Targeted Chemotherapy Regimen', imp1.description = 'HER2 targeted therapy indicated'
    MERGE (imp2:DownstreamImplication {id: 'imp_202'}) ON CREATE SET imp2.name = 'Thyroidectomy Evaluation', imp2.description = 'Surgical excision recommended'

    MERGE (doc1)-[:CONTAINS]->(raw1)
    MERGE (doc2)-[:CONTAINS]->(raw2)

    MERGE (raw1)-[:MAPPED_TO {confidence: 0.95}]->(c1)
    MERGE (raw2)-[:MAPPED_TO {confidence: 0.91}]->(c2)

    MERGE (c1)<-[:RELATED_TO]-(imp1)
    MERGE (c2)<-[:RELATED_TO]-(imp2)

    MERGE (c2)-[:RELATED_TO]->(c1)
    MERGE (c3)-[:RELATED_TO]->(c1)
    """
    try:
        run_cypher(seed_analytics_cypher)
    except Exception as e:
        logger.warning("Error seeding baseline Graph Analytics cypher: %s", e)

    logger.info("Meta-Graph ontology and Graph Analytics schema initialized successfully.")
