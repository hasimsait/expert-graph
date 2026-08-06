import logging
import time
from typing import List
import instructor
from app.config import settings
from app.module_a_sieve.schemas import ExtractionOutput

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """
You are an expert Information Extraction Sieve. Your task is to pull factual triples (Subject, Relation, Object) from raw text chunks.

CRITICAL JSON STRUCTURAL REQUIREMENT:
You MUST format each triple with top-level keys "subject", "relation", and "object" as sibling fields.
Do NOT nest "relation" or "object" inside the "subject" object. You MUST close the "subject" object brace } before writing "relation".

EXACT JSON OUTPUT STRUCTURE EXAMPLE:
{
  "chunk_id": "chk_101",
  "chunk_text": "Acme Corp owes $500,000 to Horizon Bank.",
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

async def extract_triples(chunk_id: str, chunk_text: str) -> ExtractionOutput:
    """Extract structured triples using Instructor LLM asynchronously (OpenAI, Ollama, Llama.cpp, vLLM, Gemma)."""
    start_time = time.time()
    provider = settings.LLM_PROVIDER.lower().replace("-", "_")
    
    try:
        from openai import AsyncOpenAI
        base_url = settings.LLM_BASE_URL if provider != "openai" else None
        if base_url:
            if not (base_url.startswith("http://") or base_url.startswith("https://")):
                base_url = f"http://{base_url}"
            if not base_url.endswith("/v1") and not base_url.endswith("/v1/"):
                base_url = f"{base_url.rstrip('/')}/v1"

        api_key = settings.OPENAI_API_KEY if settings.OPENAI_API_KEY else "local"
        
        logger.info("--> [Extractor Start] chunk_id: '%s' | Model: '%s' | Provider: '%s' | Endpoint: '%s'", chunk_id, settings.LLM_MODEL, provider, base_url or "OpenAI Cloud")
        logger.info("--> [Extractor Prompt] System: %s", EXTRACTION_SYSTEM_PROMPT.strip())
        logger.info("--> [Extractor Input Text] %s", chunk_text)

        mode = instructor.Mode.MD_JSON if provider != "openai" else instructor.Mode.TOOLS
        client = instructor.from_openai(AsyncOpenAI(base_url=base_url, api_key=api_key), mode=mode)
        result = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            response_model=ExtractionOutput,
            max_tokens=settings.MAX_TOKENS,
            stop=settings.STOP_TOKENS,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Chunk ID: {chunk_id}\nText: {chunk_text}"}
            ]
        )
        elapsed = time.time() - start_time
        logger.info("<-- [Extractor Done] chunk_id: '%s' | Extracted %d triples in %.2fs", chunk_id, len(result.triples), elapsed)
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("!!! [Extractor Failed after %.2fs] (%s): %s", elapsed, provider, e)
        raise RuntimeError(f"LLM Extractor execution failed: {e}") from e
