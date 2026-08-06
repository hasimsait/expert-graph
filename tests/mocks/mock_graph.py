import time
import logging
from typing import List, Dict, Any, Optional
from app.db.repository import GraphRepository

logger = logging.getLogger(__name__)

class InMemoryGraphRepository(GraphRepository):
    """
    In-memory test double repository implementation of GraphRepository
    used exclusively in automated test suites (pytest).
    """

    def __init__(self):
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

        self.edges: List[Dict[str, Any]] = [
            {
                "edge_id": "edge_path_01",
                "subject": {"name": "Invasive Ductal Breast Carcinoma", "type": "DISEASE_DIAGNOSIS"},
                "relation": "ASSOCIATED_GENE",
                "object": {"name": "HER2 Receptor Overexpression", "type": "GENE_BIOMARKER"},
                "confidence": 0.98,
                "status": "approved",
                "approved_by": "Dr_Pathologist_Smith",
                "timestamp": 1770000000,
                "chunk_id": "PATH_TEST_001",
                "chunk_text": "SPECIMEN: Breast tissue core biopsy. DIAGNOSIS: Invasive Ductal Carcinoma. BIOMARKERS: Overexpresses HER2 receptor."
            },
            {
                "edge_id": "edge_path_02",
                "subject": {"name": "Papillary Thyroid Carcinoma", "type": "DISEASE_DIAGNOSIS"},
                "relation": "ASSOCIATED_GENE",
                "object": {"name": "BRAF V600E Mutation", "type": "GENE_BIOMARKER"},
                "confidence": 0.95,
                "status": "approved",
                "approved_by": "Dr_Pathologist_Smith",
                "timestamp": 1770000000,
                "chunk_id": "PATH_TEST_003",
                "chunk_text": "SPECIMEN: Thyroid fine needle aspiration. DIAGNOSIS: Papillary Thyroid Carcinoma. BIOMARKERS: BRAF V600E mutation."
            },
            {
                "edge_id": "edge_fin_01",
                "subject": {"name": "Acme Corp", "type": "ORGANIZATION"},
                "relation": "OWES_DEBT",
                "object": {"name": "Horizon Bank", "type": "ORGANIZATION"},
                "confidence": 0.99,
                "status": "approved",
                "approved_by": "thesis_annotator_1",
                "timestamp": 1770000000,
                "chunk_id": "test_chk_101",
                "chunk_text": "Acme Corp owes $500,000 to Horizon Bank."
            }
        ]

        # Graph Analytics Mock Storage
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.raw_entities: List[Dict[str, Any]] = []
        self.canonical_concepts: Dict[str, Dict[str, Any]] = {}
        self.downstream_implications: List[Dict[str, Any]] = []
        self.concept_links: List[tuple] = []

        # Seed default analytics baseline
        self._seed_default_analytics()

    def _seed_default_analytics(self):
        self.seed_analytics_data(
            documents=[
                {"id": "doc_101", "title": "Diagnostic Biopsy Report A"},
                {"id": "doc_102", "title": "Endocrine Biopsy Report B"}
            ],
            raw_entities=[
                {"name": "invasive ductal breast carcinoma", "doc_id": "doc_101", "mapped_to": "C001"},
                {"name": "papillary thyroid carcinoma", "doc_id": "doc_102", "mapped_to": "C002"}
            ],
            concepts=[
                {"id": "C001", "name": "Invasive Ductal Carcinoma"},
                {"id": "C002", "name": "Papillary Thyroid Carcinoma"},
                {"id": "C003", "name": "General Oncology Hub"}
            ],
            implications=[
                {"id": "imp_201", "name": "Targeted Chemotherapy Regimen", "description": "HER2 targeted therapy indicated", "concept_id": "C001"},
                {"id": "imp_202", "name": "Thyroidectomy Evaluation", "description": "Surgical excision recommended", "concept_id": "C002"}
            ],
            concept_links=[
                ("C002", "C001"),
                ("C003", "C001")
            ]
        )

    def add_meta_concept(self, name: str, parent: str, rel_type: str = "SUBCLASS_OF"):
        name_upper = name.upper()
        parent_upper = parent.upper()
        if name_upper not in self.meta_concepts:
            self.meta_concepts[name_upper] = {
                "description": f"Dynamic concept {name_upper}",
                "parent": parent_upper,
                "rel_type": rel_type
            }

    async def expand_meta_graph_concept(self, concept_name: str) -> List[str]:
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

    async def get_pending_queue(self, limit: int = 20) -> List[Dict[str, Any]]:
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

    async def update_edge_status(self, edge_id: str, status: str, user_id: str) -> bool:
        now = int(time.time())
        updated = False
        for edge in self.edges:
            if edge.get("edge_id") == edge_id or (edge.get("status") == "pending" and edge.get("chunk_id") == edge_id):
                edge["status"] = status
                edge["approved_by"] = user_id
                edge["timestamp"] = now
                updated = True
        return updated

    async def get_approved_facts(self, query: str = "ALL") -> List[Dict[str, Any]]:
        search_term = (query or "ALL").strip()
        concept_upper = search_term.upper()

        all_approved = []
        for edge in self.edges:
            if edge.get("status") == "approved":
                fact = {
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
                }
                all_approved.append(fact)

        if concept_upper in ["ALL", "RELATIONSHIP", "*", ""]:
            return all_approved

        from app.services.tfidf_retrieval import TFIDFRetriever
        return TFIDFRetriever.rank_facts(search_term, all_approved)

    async def get_stats(self) -> Dict[str, int]:
        stats = {"pending": 0, "approved": 0, "rejected": 0}
        for edge in self.edges:
            st = edge.get("status", "pending")
            if st in stats:
                stats[st] += 1
        return stats

    def seed_analytics_data(self, documents: list, raw_entities: list, concepts: list, implications: list, concept_links: list = None):
        self.documents = {doc["id"]: doc for doc in documents}
        self.raw_entities = raw_entities
        self.canonical_concepts = {c["id"]: c for c in concepts}
        self.downstream_implications = implications
        self.concept_links = concept_links or []

    async def get_document_implications(self, document_id: str) -> List[Dict[str, Any]]:
        results = []
        raw_entities = getattr(self, "raw_entities", [])
        canonical_concepts = getattr(self, "canonical_concepts", {})
        downstream_implications = getattr(self, "downstream_implications", [])

        target_ids = [document_id]
        if not document_id or document_id.upper() in ["ALL", "ALL_DOCS"]:
            target_ids = list(self.documents.keys()) + [r.get("doc_id") for r in raw_entities if r.get("doc_id")]

        for doc_id in set(target_ids):
            raw_matches = [r for r in raw_entities if r.get("doc_id") == doc_id]
            for raw in raw_matches:
                concept_id = raw.get("mapped_to")
                concept = canonical_concepts.get(concept_id)
                if not concept:
                    continue
                imp_matches = [i for i in downstream_implications if i.get("concept_id") == concept_id]
                for imp in imp_matches:
                    results.append({
                        "document_id": doc_id,
                        "raw_entity": raw["name"],
                        "canonical_id": concept["id"],
                        "canonical_name": concept["name"],
                        "implication_id": imp["id"],
                        "implication_name": imp["name"],
                        "description": imp.get("description", "")
                    })
        return results

    async def run_concept_pagerank(self) -> List[Dict[str, Any]]:
        canonical_concepts = getattr(self, "canonical_concepts", {})
        if not canonical_concepts:
            return []
        
        raw_entities = getattr(self, "raw_entities", [])
        downstream_implications = getattr(self, "downstream_implications", [])
        concept_links = getattr(self, "concept_links", [])

        scores = {c_id: 1.0 for c_id in canonical_concepts}
        for raw in raw_entities:
            c_id = raw.get("mapped_to")
            if c_id in scores:
                scores[c_id] += 1.5
        for imp in downstream_implications:
            c_id = imp.get("concept_id")
            if c_id in scores:
                scores[c_id] += 1.5
        for src, target in concept_links:
            if target in scores:
                scores[target] += 2.0

        results = []
        for c_id, concept in canonical_concepts.items():
            results.append({
                "concept_id": c_id,
                "concept_name": concept["name"],
                "score": round(scores.get(c_id, 1.0), 4)
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:10]

    async def get_all_documents(self) -> List[Dict[str, Any]]:
        docs = []
        for doc_id, doc in self.documents.items():
            docs.append({"id": doc_id, "title": doc.get("title", doc_id), "type": "SourceDocument"})
        seen_ids = {d["id"] for d in docs}
        for edge in self.edges:
            chunk_id = edge.get("chunk_id")
            if chunk_id and chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                chunk_text = edge.get("chunk_text", "")
                title = (chunk_text[:35] + "...") if len(chunk_text) > 35 else (chunk_text or chunk_id)
                docs.append({"id": chunk_id, "title": title, "type": "Chunk"})
        return docs

    async def reset_graph(self) -> None:
        self.edges = []
        self.documents = {}
        self.raw_entities = []
        self.canonical_concepts = {}
        self.downstream_implications = []
        self.concept_links = []

# Global Test Mock Instance for pytest usage
mock_graph_store = InMemoryGraphRepository()
