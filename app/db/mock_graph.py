import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class InMemoryDualGraph:
    """High-performance in-memory Dual Graph store for offline / mock mode."""
    
    def __init__(self):
        # Meta-Graph Ontology: concept_name -> {description, parent, rel_type}
        self.meta_concepts: Dict[str, Dict[str, Any]] = {
            "RELATIONSHIP": {"description": "Root relationship concept", "parent": None},
            
            "FINANCIAL_RELATION": {"description": "Financial links between entities", "parent": "RELATIONSHIP", "rel_type": "SUBCLASS_OF"},
            "OWES_DEBT": {"description": "Financial obligation or debt relationship", "parent": "FINANCIAL_RELATION", "rel_type": "SUBCLASS_OF"},
            "TRANSFERS_FUNDS": {"description": "Direct monetary transfer", "parent": "FINANCIAL_RELATION", "rel_type": "SUBCLASS_OF"},
            "INVESTED_IN": {"description": "Equity or venture investment", "parent": "FINANCIAL_RELATION", "rel_type": "SUBCLASS_OF"},
            "VENTURE_INVESTMENT": {"description": "Venture funding round", "parent": "INVESTED_IN", "rel_type": "SUBCLASS_OF"},
            "EQUITY_STAKE": {"description": "Shareholding or equity acquisition", "parent": "INVESTED_IN", "rel_type": "SUBCLASS_OF"},
            "LIABLE_FOR": {"description": "Debt liability synonym", "parent": "OWES_DEBT", "rel_type": "SYNONYM_OF"},
            
            "LEGAL_RELATION": {"description": "Legal or regulatory connection", "parent": "RELATIONSHIP", "rel_type": "SUBCLASS_OF"},
            "LAWSUIT_AGAINST": {"description": "Litigation or legal conflict", "parent": "LEGAL_RELATION", "rel_type": "SUBCLASS_OF"},
            "CONTRACT_WITH": {"description": "Binding agreement between entities", "parent": "LEGAL_RELATION", "rel_type": "SUBCLASS_OF"},
            
            "ORGANIZATIONAL_RELATION": {"description": "Corporate structural link", "parent": "RELATIONSHIP", "rel_type": "SUBCLASS_OF"},
            "SUBSIDIARY_OF": {"description": "Corporate ownership hierarchy", "parent": "ORGANIZATIONAL_RELATION", "rel_type": "SUBCLASS_OF"},
            "EMPLOYED_BY": {"description": "Employment relationship", "parent": "ORGANIZATIONAL_RELATION", "rel_type": "SUBCLASS_OF"},
            "PARTNERED_WITH": {"description": "Strategic business partnership", "parent": "ORGANIZATIONAL_RELATION", "rel_type": "SUBCLASS_OF"}
        }

        # Data-Graph Edges list (starts clean & empty)
        self.edges: List[Dict[str, Any]] = []

    def add_meta_concept(self, name: str, parent: str, rel_type: str = "SUBCLASS_OF"):
        name_upper = name.upper()
        parent_upper = parent.upper()
        if name_upper not in self.meta_concepts:
            self.meta_concepts[name_upper] = {
                "description": f"Dynamic concept {name_upper}",
                "parent": parent_upper,
                "rel_type": rel_type
            }

    def expand_concept(self, concept_name: str) -> List[str]:
        """Traverse Meta-Graph in-memory to find all descendant subclasses and synonyms."""
        root = concept_name.upper()
        results = {root}
        
        changed = True
        while changed:
            changed = False
            for child_name, info in self.meta_concepts.items():
                if info.get("parent") in results and child_name not in results:
                    results.add(child_name)
                    changed = True

        return list(results)

    def add_edge(self, edge_dict: Dict[str, Any]):
        mapping = edge_dict.get("concept_mapping")
        if mapping:
            self.add_meta_concept(
                mapping.get("new_relation"),
                mapping.get("existing_concept"),
                mapping.get("mapping_type", "SUBCLASS_OF")
            )
        self.edges.append(edge_dict)

    def get_pending_queue(self, limit: int = 20) -> List[Dict[str, Any]]:
        pending = []
        for edge in self.edges:
            if edge.get("status") == "pending":
                rel = edge.get("relation", "").upper()
                meta_info = self.meta_concepts.get(rel, {})
                
                item = dict(edge)
                item["meta_concept"] = meta_info.get("parent")
                item["meta_mapping"] = meta_info.get("rel_type")
                pending.append(item)
                if len(pending) >= limit:
                    break
        return pending

    def update_edge_status(self, edge_id: str, status: str, user_id: str) -> bool:
        now = int(time.time())
        updated = False
        for edge in self.edges:
            if edge.get("edge_id") == edge_id or (edge.get("status") == "pending" and edge.get("chunk_id") == edge_id):
                edge["status"] = status
                edge["approved_by"] = user_id
                edge["timestamp"] = now
                updated = True
        return updated

    def get_approved_facts(self, concept_name: str) -> List[Dict[str, Any]]:
        expanded = self.expand_concept(concept_name)
        approved = []
        for edge in self.edges:
            if edge.get("status") == "approved" and edge.get("relation", "").upper() in expanded:
                approved.append({
                    "edge_id": edge.get("edge_id"),
                    "subject": edge["subject"]["name"] if isinstance(edge["subject"], dict) else edge["subject"],
                    "subject_type": edge["subject"].get("type", "ENTITY") if isinstance(edge["subject"], dict) else "ENTITY",
                    "relation": edge.get("relation"),
                    "object": edge["object"]["name"] if isinstance(edge["object"], dict) else edge["object"],
                    "object_type": edge["object"].get("type", "ENTITY") if isinstance(edge["object"], dict) else "ENTITY",
                    "confidence": edge.get("confidence", 0.95),
                    "approved_by": edge.get("approved_by", "thesis_annotator_1"),
                    "timestamp": edge.get("timestamp"),
                    "chunk_id": edge.get("chunk_id"),
                    "chunk_text": edge.get("chunk_text")
                })
        return approved

    def get_stats(self) -> Dict[str, int]:
        stats = {"pending": 0, "approved": 0, "rejected": 0}
        for edge in self.edges:
            st = edge.get("status", "pending")
            if st in stats:
                stats[st] += 1
        return stats

    def reset(self):
        """Reset in-memory mock graph store edges and state."""
        self.edges = []

# Global Singleton Instance for Mock Dual Graph
mock_graph_store = InMemoryDualGraph()
