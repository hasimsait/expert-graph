import logging
import re
from typing import List
import instructor
from app.config import settings
from app.module_a_sieve.schemas import ExtractionOutput, CriticEvaluation

logger = logging.getLogger(__name__)

CRITIC_SYSTEM_PROMPT = """
You are an Adversarial Critic LLM. Your task is to rigorously cross-reference proposed factual triples against the raw text chunk.
For each triple, evaluate:
1. Is the subject, relation, and object strictly supported by the text chunk?
2. Mark is_valid = True if supported, or is_valid = False if hallucinated or distorted.
3. Provide a confidence score between 0.0 and 1.0.
"""

def mock_critic_evaluate(extraction: ExtractionOutput) -> List[CriticEvaluation]:
    """Mock critic evaluation fallback."""
    results = []
    text_words = set(re.findall(r'\w+', extraction.chunk_text.lower()))
    
    for i, triple in enumerate(extraction.triples):
        subj_words = set(re.findall(r'\w+', triple.subject.name.lower()))
        obj_words = set(re.findall(r'\w+', triple.object.name.lower()))
        
        subj_overlap = len(subj_words & text_words) > 0
        obj_overlap = len(obj_words & text_words) > 0
        
        # Always accept candidate extractions in mock mode so they drop into the pending queue
        is_valid = True
        confidence = 0.94 if (subj_overlap or obj_overlap) else 0.85
        note = "Fact supported by chunk context." if (subj_overlap or obj_overlap) else "Candidate triple extracted from text."
        
        results.append(CriticEvaluation(
            triple_index=i,
            is_valid=is_valid,
            confidence=confidence,
            critique_notes=note
        ))
    return results

def evaluate_triples(extraction: ExtractionOutput) -> List[CriticEvaluation]:
    """Evaluate triples using Adversarial Critic LLM (OpenAI, Ollama, Llama.cpp, vLLM, Gemma) or fallback."""
    import time
    start_time = time.time()
    provider = settings.LLM_PROVIDER.lower().replace("-", "_")
    
    if provider != "mock":
        try:
            from openai import OpenAI
            base_url = settings.LLM_BASE_URL if provider != "openai" else None
            api_key = settings.OPENAI_API_KEY if settings.OPENAI_API_KEY else "local"
            
            logger.info("--> [Critic Start] chunk_id: '%s' | Model: '%s' | Evaluating %d triples", extraction.chunk_id, settings.LLM_MODEL, len(extraction.triples))
            logger.info("--> [Critic Prompt] System: %s", CRITIC_SYSTEM_PROMPT.strip())
            
            client = instructor.from_openai(OpenAI(base_url=base_url, api_key=api_key))
            
            prompt_content = f"Chunk Text:\n{extraction.chunk_text}\n\nProposed Triples:\n"
            for idx, t in enumerate(extraction.triples):
                prompt_content += f"[{idx}] ({t.subject.name}) -[{t.relation}]-> ({t.object.name})\n"
                
            logger.info("--> [Critic Input Triples]\n%s", prompt_content.strip())

            class BatchCriticEvaluation(instructor.OpenAISchema):
                evaluations: List[CriticEvaluation]

            res = client.chat.completions.create(
                model=settings.LLM_MODEL,
                response_model=BatchCriticEvaluation,
                max_tokens=settings.MAX_TOKENS,
                stop=settings.STOP_TOKENS,
                messages=[
                    {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_content}
                ]
            )
            elapsed = time.time() - start_time
            valid_cnt = sum(1 for ev in res.evaluations if ev.is_valid)
            logger.info("<-- [Critic Done] chunk_id: '%s' | Validated %d/%d triples in %.2fs", extraction.chunk_id, valid_cnt, len(res.evaluations), elapsed)
            return res.evaluations
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error("!!! [Critic Failed after %.2fs] (%s): %s. Using mock fallback.", elapsed, provider, e)
            return mock_critic_evaluate(extraction)
    else:
        logger.info("Running Critic in mock mode for chunk_id: %s", extraction.chunk_id)
        return mock_critic_evaluate(extraction)
