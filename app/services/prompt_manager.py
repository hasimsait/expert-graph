import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_EXTRACTION_PROMPT = """
You are an expert Information Extraction Sieve. Your task is to pull factual triples (Subject, Relation, Object) from raw text chunks.

CRITICAL JSON STRUCTURAL REQUIREMENT:
You MUST format each triple with top-level keys "subject", "relation", and "object" as sibling fields.
Do NOT nest "relation" or "object" inside the "subject" object. You MUST close the "subject" object brace } before writing "relation".

EXACT JSON OUTPUT STRUCTURE EXAMPLE:
{
  "chunk_id": "chk_101",
  "chunk_text": "... ENTITY A .... <relation> ... <ENTITY B> ...",
  "triples": [
    {
      "subject": {"name": "Entity A", "type": "CONCEPT"},
      "relation": "ASSOCIATED_WITH",
      "object": {"name": "Entity B", "type": "CONCEPT"},
      "concept_mapping": null
    }
  ]
}

STRICT EXTRACTION RULES:
1. Normalize entity names and uppercase relation names (e.g., OWES_DEBT, LAWSUIT_AGAINST, TRANSFERS_FUNDS, SUBSIDIARY_OF, ASSOCIATED_GENE, FOUND_IN_SPECIMEN).
2. If you introduce a relation name that is NOT standard, you MUST output a concept_mapping object with new_relation, existing_concept, and mapping_type ("SUBCLASS_OF" or "SYNONYM_OF"). Otherwise, set concept_mapping to null.
3. Never hallucinate facts that are not explicitly stated in the chunk text.
4. ENSURE ALL BRACKETS ARE PROPERLY CLOSED: "subject": {"name": "...", "type": "..."}, "relation": "...", "object": {"name": "...", "type": "..."}.
"""

DEFAULT_CRITIC_PROMPT = """
You are an Adversarial Critic LLM. Your task is to rigorously cross-reference proposed factual triples against the raw text chunk.

EXACT JSON OUTPUT STRUCTURE EXAMPLE:
{
  "evaluations": [
    {
      "triple_index": 0,
      "is_valid": true,
      "confidence": 0.95,
      "typo_corrections": [
        {
          "original_typo": "forgor",
          "replacement": "forgot"
        }
      ]
    }
  ]
}

STRICT EVALUATION RULES:
1. Is the subject, relation, and object strictly supported by the text chunk?
2. Mark is_valid = true if supported, or is_valid = false if hallucinated or distorted.
3. Provide a confidence score between 0.0 and 1.0.
4. If an entity name contains a minor spelling typo (e.g., 'forgor' instead of 'forgot'), do NOT use freetext. Instead, provide a structured typo_corrections list specifying 'original_typo' and 'replacement'.
"""


class PromptManager:
    """Manages domain-specific prompts for the LLM pipeline."""

    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = prompts_dir

    def _load_prompt(self, env_key: str, filename: str, default: str) -> str:
        # 1. Try environment variable
        if env_val := os.getenv(env_key):
            return env_val

        # 2. Try file in prompts_dir
        filepath = os.path.join(self.prompts_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception as e:
                logger.warning(
                    "Failed to read prompt file %s: %s", filepath, e)

        # 3. Fallback to default
        return default.strip()

    def get_extraction_prompt(self) -> str:
        return self._load_prompt("EXTRACTION_PROMPT", "extractor.txt", DEFAULT_EXTRACTION_PROMPT)

    def get_critic_prompt(self) -> str:
        return self._load_prompt("CRITIC_PROMPT", "critic.txt", DEFAULT_CRITIC_PROMPT)


_prompt_manager_instance: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    global _prompt_manager_instance
    if _prompt_manager_instance is None:
        from app.config import settings
        prompts_dir = getattr(settings, "PROMPTS_DIR", "prompts")
        if not os.path.isabs(prompts_dir):
            import pathlib
            project_root = pathlib.Path(__file__).parent.parent.parent
            prompts_dir = str(project_root / prompts_dir)
        _prompt_manager_instance = PromptManager(prompts_dir=prompts_dir)
    return _prompt_manager_instance
