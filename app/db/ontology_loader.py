import os
import csv
import json
import logging
from typing import List, Dict, Any, Optional
from app.db.neo4j_client import run_cypher
from app.db.mock_graph import mock_graph_store

logger = logging.getLogger(__name__)

def load_custom_ontology_json(filepath: str) -> Dict[str, int]:
    """
    Loads a custom ontology JSON file into Neo4j (and mock store).
    Expected JSON structure:
    {
        "concepts": [
            {"name": "BIOLOGICAL_PROCESS", "description": "Cellular or metabolic process"},
            {"name": "INHIBITS", "description": "Blockade or suppression mechanism"}
        ],
        "relationships": [
            {"child": "INHIBITS", "parent": "BIOLOGICAL_PROCESS", "rel_type": "SUBCLASS_OF"}
        ]
    }
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Ontology file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    concepts = data.get("concepts", [])
    relationships = data.get("relationships", [])

    # Load Concepts into Neo4j
    cypher_concepts = """
    UNWIND $concepts AS c
    MERGE (concept:Concept {name: c.name})
    ON CREATE SET concept.description = c.description, concept.created_at = timestamp()
    """
    run_cypher(cypher_concepts, {"concepts": concepts})

    # Load Relationships into Neo4j
    for rel in relationships:
        cypher_rel = f"""
        MERGE (c1:Concept {{name: $child}})
        MERGE (c2:Concept {{name: $parent}})
        MERGE (c1)-[r:{rel.get('rel_type', 'SUBCLASS_OF')}]->(c2)
        """
        run_cypher(cypher_rel, {"child": rel["child"], "parent": rel["parent"]})

        # Also register in mock store
        mock_graph_store.add_meta_concept(
            rel["child"],
            rel["parent"],
            rel.get("rel_type", "SUBCLASS_OF")
        )

    logger.info("Loaded %d concepts and %d relationships from %s.", len(concepts), len(relationships), filepath)
    return {"concepts_loaded": len(concepts), "relationships_loaded": len(relationships)}


def load_umls_rrf(mrconso_path: str, mrrel_path: str, max_records: int = 1000) -> Dict[str, int]:
    """
    Parses UMLS RRF files (MRCONSO.RRF and MRREL.RRF) and populates the Meta-Graph.
    - MRCONSO.RRF: CUI | LAT | TS | STT | ISPREF | AUI | SAUI | SCUI | SDUI | SAB | TTY | CODE | STR | SRL | SUPPRESS | CVF
    - MRREL.RRF: CUI1 | AUI1 | STYPE1 | REL | CUI2 | AUI2 | STYPE2 | RELA | RUI | SRUI | SAB | SL | RG | DIR | SUPPRESS | CVF
    """
    if not os.path.exists(mrconso_path):
        logger.warning("MRCONSO.RRF not found at %s. Skipping UMLS RRF load.", mrconso_path)
        return {"concepts_loaded": 0, "relationships_loaded": 0}

    cui_map: Dict[str, str] = {}
    
    # 1. Parse MRCONSO for CUI -> Preferred String Mapping
    logger.info("Parsing UMLS MRCONSO.RRF...")
    with open(mrconso_path, "r", encoding="utf-8", errors="ignore") as f:
        count = 0
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 13:
                cui = parts[0]
                lat = parts[1] # Language
                is_pref = parts[4] # Preferred
                str_val = parts[12] # String name
                
                if lat == "ENG" and (cui not in cui_map or is_pref == "Y"):
                    # Normalize to UPPERCASE_SNAKE_CASE concept name
                    concept_name = str_val.upper().replace(" ", "_").replace("-", "_")[:50]
                    cui_map[cui] = concept_name
                    count += 1
                    if count >= max_records:
                        break

    # Seed UMLS concepts into Neo4j & Mock Store
    concepts_batch = [{"name": name, "cui": cui, "description": f"UMLS Concept CUI: {cui}"} for cui, name in cui_map.items()]
    
    cypher_umls = """
    UNWIND $concepts AS c
    MERGE (concept:Concept {name: c.name})
    ON CREATE SET concept.cui = c.cui, concept.description = c.description, concept.source = "UMLS"
    """
    run_cypher(cypher_umls, {"concepts": concepts_batch})

    for c in concepts_batch:
        mock_graph_store.add_meta_concept(c["name"], "MEDICAL_CONCEPT", "SUBCLASS_OF")

    # 2. Parse MRREL for CUI Relationships if file exists
    rel_count = 0
    if os.path.exists(mrrel_path):
        logger.info("Parsing UMLS MRREL.RRF...")
        with open(mrrel_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) >= 5:
                    cui1 = parts[0]
                    rel = parts[3] # REL: PAR (Parent), CHD (Child), SY (Synonym), RO (Other)
                    cui2 = parts[4]
                    
                    child_name = cui_map.get(cui1)
                    parent_name = cui_map.get(cui2)
                    
                    if child_name and parent_name:
                        rel_type = "SUBCLASS_OF" if rel in ["PAR", "CHD"] else "SYNONYM_OF" if rel == "SY" else "RELATED_TO"
                        
                        cypher_rel = f"""
                        MERGE (c1:Concept {{name: $child}})
                        MERGE (c2:Concept {{name: $parent}})
                        MERGE (c1)-[r:{rel_type}]->(c2)
                        """
                        run_cypher(cypher_rel, {"child": child_name, "parent": parent_name})
                        mock_graph_store.add_meta_concept(child_name, parent_name, rel_type)
                        rel_count += 1
                        if rel_count >= max_records:
                            break

    logger.info("UMLS Load completed: %d concepts, %d relationships.", len(cui_map), rel_count)
    return {"concepts_loaded": len(cui_map), "relationships_loaded": rel_count}
