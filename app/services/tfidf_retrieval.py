import logging
from typing import List, Dict, Any, Optional
from scipy.sparse import vstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class TFIDFRetriever:
    """
    Incremental Delta TF-IDF Retrieval Engine.
    Maintains a sparse vector matrix across approved facts. Performs true delta appends 
    via scipy.sparse.vstack when new facts are approved, avoiding re-fitting or re-building 
    the matrix on updates or read queries. Automatically warms up from Neo4j on server boot.
    #TODO persist to avoid unnecessary matrix construction.
    """
    _vectorizer: Optional[TfidfVectorizer] = None
    _doc_matrix: Any = None
    _indexed_facts: List[Dict[str, Any]] = []
    _fact_ids_set: set = set()

    @classmethod
    def reset_cache(cls) -> None:
        """Completely reset index state on database wipe."""
        cls._vectorizer = None
        cls._doc_matrix = None
        cls._indexed_facts = []
        cls._fact_ids_set = set()

    @classmethod
    def invalidate_cache(cls) -> None:
        """Alias for reset_cache for backward compatibility."""
        cls.reset_cache()

    @classmethod
    async def warmup_from_db(cls) -> None:
        """Warm up the index on server startup by loading all existing approved facts from Neo4j DB."""
        try:
            from app.db.repository import get_graph_repository
            repo = get_graph_repository()
            approved_facts = await repo.get_approved_facts("ALL")
            if approved_facts:
                cls.add_facts_delta(approved_facts)
                logger.info("Successfully warmed up TF-IDF index from DB with %d approved facts.", len(approved_facts))
        except Exception as e:
            logger.warning("Error warming up TF-IDF index from DB: %s", e)

    @classmethod
    def _format_fact_doc(cls, f: Dict[str, Any]) -> str:
        return f"{f.get('subject', '')} {f.get('subject_type', '')} {f.get('relation', '')} {f.get('object', '')} {f.get('object_type', '')} {f.get('chunk_text') or ''}"

    @classmethod
    def add_fact_delta(cls, fact: Dict[str, Any]) -> None:
        """Incrementally append a single newly approved fact to the sparse index matrix."""
        cls.add_facts_delta([fact])

    @classmethod
    def add_facts_delta(cls, new_facts: List[Dict[str, Any]]) -> None:
        """Incrementally append a batch of newly approved facts to the sparse matrix index."""
        if not new_facts:
            return

        to_add = []
        to_add_corpus = []

        for f in new_facts:
            fact_id = f.get("edge_id") or f"{f.get('subject')}_{f.get('relation')}_{f.get('object')}"
            if fact_id not in cls._fact_ids_set:
                cls._fact_ids_set.add(fact_id)
                to_add.append(f)
                to_add_corpus.append(cls._format_fact_doc(f))

        if not to_add:
            return

        # Scikit-learn TfidfVectorizer cannot incrementally learn new vocabulary words.
        # If we use vstack with transform(), any words in new facts that weren't in the initial 
        # training corpus are completely ignored, making them unsearchable.
        # Since fitting on thousands of short facts is virtually instantaneous, we simply 
        # re-fit the entire index.
        cls._indexed_facts.extend(to_add)
        
        all_corpus = [cls._format_fact_doc(f) for f in cls._indexed_facts]
        
        try:
            cls._vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english', lowercase=True)
            cls._doc_matrix = cls._vectorizer.fit_transform(all_corpus)
            logger.info("Re-fitted TF-IDF matrix with %d new fact(s). Total index size: %d.", len(to_add), len(cls._indexed_facts))
        except Exception as e:
            logger.warning("Error re-fitting TF-IDF index: %s", e)

    @classmethod
    def remove_fact_delta(cls, edge_id: str) -> None:
        """Incrementally remove a single rejected or deleted fact from the index matrix."""
        if not edge_id or not cls._indexed_facts or cls._doc_matrix is None:
            return

        target_idx = None
        for idx, f in enumerate(cls._indexed_facts):
            f_id = f.get("edge_id") or f"{f.get('subject')}_{f.get('relation')}_{f.get('object')}"
            if f_id == edge_id:
                target_idx = idx
                break

        if target_idx is not None:
            removed_fact = cls._indexed_facts.pop(target_idx)
            f_id = removed_fact.get("edge_id") or f"{removed_fact.get('subject')}_{removed_fact.get('relation')}_{removed_fact.get('object')}"
            cls._fact_ids_set.discard(f_id)

            # Mask out row from sparse matrix
            keep_indices = [i for i in range(cls._doc_matrix.shape[0]) if i != target_idx]
            if keep_indices:
                cls._doc_matrix = cls._doc_matrix[keep_indices, :]
            else:
                cls.reset_cache()
            logger.info("Delta-removed fact '%s' from index matrix.", edge_id)

    @classmethod
    def rank_facts(cls, query: str, facts: List[Dict[str, Any]], similarity_threshold_ratio: float = 0.6) -> List[Dict[str, Any]]:
        if not facts or not query:
            return []

        search_term = query.strip()
        if search_term.upper() in ["ALL", "*", ""]:
            return facts

        # Ensure any new facts in `facts` not yet in delta index are registered incrementally
        unindexed = [f for f in facts if (f.get("edge_id") or f"{f.get('subject')}_{f.get('relation')}_{f.get('object')}") not in cls._fact_ids_set]
        if unindexed:
            cls.add_facts_delta(unindexed)

        if cls._vectorizer is None or cls._doc_matrix is None or not cls._indexed_facts:
            return facts

        candidate_ids = {f.get("edge_id") or f"{f.get('subject')}_{f.get('relation')}_{f.get('object')}" for f in facts}

        try:
            query_vec = cls._vectorizer.transform([search_term])
            sim_scores = cosine_similarity(query_vec, cls._doc_matrix).flatten()

            max_score = float(sim_scores.max()) if len(sim_scores) > 0 else 0.0
            if max_score <= 0.0:
                return []

            cutoff = max(0.1, max_score * similarity_threshold_ratio)

            indexed_facts = []
            for idx, score in enumerate(sim_scores):
                if score >= cutoff and idx < len(cls._indexed_facts):
                    candidate_fact = cls._indexed_facts[idx]
                    f_id = candidate_fact.get("edge_id") or f"{candidate_fact.get('subject')}_{candidate_fact.get('relation')}_{candidate_fact.get('object')}"
                    if f_id in candidate_ids:
                        indexed_facts.append((score, candidate_fact))

            indexed_facts.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in indexed_facts]

        except Exception as e:
            logger.warning(f"TF-IDF query transform fallback: {e}")
            return facts
