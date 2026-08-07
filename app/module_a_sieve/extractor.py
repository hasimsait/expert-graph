import logging
import time
from typing import List
from app.config import settings
from app.module_a_sieve.schemas import ExtractionOutput
from app.services.llm_service import get_llm_service
from app.services.prompt_manager import get_prompt_manager

logger = logging.getLogger(__name__)

async def extract_triples(chunk_id: str, chunk_text: str) -> ExtractionOutput:
    """Extract structured triples using Instructor LLM asynchronously."""
    start_time = time.time()
    
    llm_service = get_llm_service()
    prompt_manager = get_prompt_manager()
    
    provider = llm_service.provider
    system_prompt = prompt_manager.get_extraction_prompt()
    
    try:
        logger.info("--> [Extractor Start] chunk_id: '%s' | Model: '%s' | Provider: '%s' | Endpoint: '%s'", 
                    chunk_id, settings.LLM_MODEL, provider, llm_service.base_url or "OpenAI Cloud")
        logger.info("--> [Extractor Prompt] System: %s", system_prompt.strip())
        logger.info("--> [Extractor Input Text] %s", chunk_text)

        client = llm_service.get_instructor_client()

        llm_kwargs = llm_service.get_llm_kwargs(
            response_model=ExtractionOutput,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Chunk ID: {chunk_id}\nText: {chunk_text}"}
            ]
        )

        result = await client.chat.completions.create(**llm_kwargs)
        elapsed = time.time() - start_time
        logger.info("<-- [Extractor Done] chunk_id: '%s' | Extracted %d triples in %.2fs", chunk_id, len(result.triples), elapsed)
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("!!! [Extractor Failed after %.2fs] (%s): %s", elapsed, provider, e)
        raise RuntimeError(f"LLM Extractor execution failed: {e}") from e
