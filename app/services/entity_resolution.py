import os
import json
import logging
from typing import Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.config import settings

logger = logging.getLogger(__name__)

class EntityResolver:
    """
    Plug-and-play Entity Resolution using scikit-learn TF-IDF and Cosine Similarity.
    Loads a single-domain canonical JSON ontology at runtime or dynamically from GraphRepository asynchronously.
    """
    def __init__(
        self,
        ontology_path: Optional[str] = None,
        ontology_dict: Optional[Dict[str, str]] = None,
        threshold: float = 0.4
    ):
        self.threshold = threshold
        self.ontology: Dict[str, str] = {}
        self.ids: list[str] = []
        self.names: list[str] = []
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
        self.tfidf_matrix = None

        if ontology_dict is not None:
            self.load_ontology_dict(ontology_dict)
        else:
            path = ontology_path or getattr(settings, "ONTOLOGY_PATH", None) or os.getenv("ONTOLOGY_PATH")
            if path and os.path.exists(path):
                self.load_ontology_file(path)

    def load_ontology_dict(self, ontology_dict: Dict[str, str]) -> None:
        self.ontology = dict(ontology_dict)
        self.ids = list(self.ontology.keys())
        self.names = list(self.ontology.values())
        if self.names:
            self.tfidf_matrix = self.vectorizer.fit_transform(self.names)
        else:
            self.tfidf_matrix = None

    def load_ontology_file(self, file_path: str) -> None:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.load_ontology_dict(data)

    async def load_ontology_from_db(self, repo: Optional[Any] = None) -> None:
        """Dynamically load active ontology concepts via GraphRepository abstraction asynchronously."""
        try:
            from app.db.repository import get_graph_repository
            active_repo = repo or get_graph_repository()
            concepts_dict = await active_repo.get_canonical_concepts()
            if concepts_dict:
                self.load_ontology_dict(concepts_dict)
                logger.info("Loaded %d ontology concepts via GraphRepository.", len(concepts_dict))
        except Exception as e:
            logger.warning("Error fetching ontology concepts from GraphRepository: %s", e)

    def resolve_entity(self, raw_string: str) -> Optional[Dict[str, Any]]:
        """
        Fuzzily match raw_string against loaded canonical JSON ontology.
        
        Returns:
            {"canonical_id": str, "canonical_name": str, "confidence": float}
            or None if best match score is below confidence threshold.
        """
        if not raw_string or not self.names or self.tfidf_matrix is None:
            return None

        query_vec = self.vectorizer.transform([raw_string])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        if len(similarities) == 0:
            return None

        best_idx = int(similarities.argmax())
        best_score = float(similarities[best_idx])

        if best_score < self.threshold:
            return None

        return {
            "canonical_id": self.ids[best_idx],
            "canonical_name": self.names[best_idx],
            "confidence": round(best_score, 4)
        }

_resolver_instance: Optional[EntityResolver] = None

async def get_entity_resolver(repo: Optional[Any] = None) -> EntityResolver:
    """Get global EntityResolver singleton or initialize standard instance asynchronously."""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = EntityResolver()
        if not _resolver_instance.ontology:
            await _resolver_instance.load_ontology_from_db(repo=repo)
    return _resolver_instance

def reset_entity_resolver(resolver: Optional[EntityResolver] = None) -> None:
    """Reset or override global EntityResolver singleton for testing or runtime reconfig."""
    global _resolver_instance
    _resolver_instance = resolver
