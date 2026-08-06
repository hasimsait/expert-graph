import logging
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class TFIDFRetriever:
    """
    Fast, lightweight, domain-agnostic TF-IDF and Cosine Similarity retrieval engine.
    Computes Inverse Document Frequency (IDF) weights across candidate facts to score query relevance.
    """

    @staticmethod
    def rank_facts(query: str, facts: List[Dict[str, Any]], similarity_threshold_ratio: float = 0.6) -> List[Dict[str, Any]]:
        if not facts or not query:
            return []

        search_term = query.strip()
        if search_term.upper() in ["ALL", "*", ""]:
            return facts

        # Build document text representation for each fact
        corpus = []
        for f in facts:
            doc_str = f"{f.get('subject', '')} {f.get('subject_type', '')} {f.get('relation', '')} {f.get('object', '')} {f.get('object_type', '')} {f.get('chunk_text') or ''}"
            corpus.append(doc_str)

        if not any(corpus):
            return []

        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english', lowercase=True)
            doc_matrix = vectorizer.fit_transform(corpus)
            query_vec = vectorizer.transform([search_term])

            sim_scores = cosine_similarity(query_vec, doc_matrix).flatten()

            max_score = float(sim_scores.max()) if len(sim_scores) > 0 else 0.0
            if max_score <= 0.0:
                return []

            # Dynamic similarity thresholding (relative to max similarity score)
            cutoff = max(0.1, max_score * similarity_threshold_ratio)

            indexed_facts = []
            for idx, score in enumerate(sim_scores):
                if score >= cutoff:
                    indexed_facts.append((score, facts[idx]))

            indexed_facts.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in indexed_facts]

        except Exception as e:
            logger.warning(f"TF-IDF vectorizer fallback: {e}")
            return facts
