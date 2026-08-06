import logging
import re
import difflib
import time
from typing import List
import instructor
from app.config import settings
from app.module_a_sieve.schemas import ExtractionOutput, CriticEvaluation, ExtractedTriple, TypoCorrection

logger = logging.getLogger(__name__)

CRITIC_SYSTEM_PROMPT = """
You are an Adversarial Critic LLM. Your task is to rigorously cross-reference proposed factual triples against the raw text chunk.
For each triple, evaluate:
1. Is the subject, relation, and object strictly supported by the text chunk?
2. Mark is_valid = True if supported, or is_valid = False if hallucinated or distorted.
3. Provide a confidence score between 0.0 and 1.0.
4. If an entity name contains a minor spelling typo (e.g., 'Carcinma' instead of 'Carcinoma'), do NOT use freetext. Instead, provide a structured typo correction specifying 'original_typo' and 'replacement'.
"""

def validate_and_apply_typo_corrections(
    triple: ExtractedTriple,
    corrections: List[TypoCorrection],
    chunk_text: str
) -> ExtractedTriple:
    """
    Validates Critic typo correction suggestions and applies them to extracted entity names.
    Rules:
    1. Critic specifies 'original_typo' and 'replacement'.
    2. Check if 'original_typo' appears in extracted entity name or text (or fuzzy matches >= 0.8).
    3. Ensure 'replacement' is a valid typo fix (fuzzy similarity >= 0.65 or replacement appears in chunk_text).
    4. If validated, replace original_typo with replacement in triple's subject and object names.
    """
    if not corrections:
        return triple

    for corr in corrections:
        typo = corr.original_typo.strip()
        rep = corr.replacement.strip()
        if not typo or not rep or typo == rep:
            continue

        sim = difflib.SequenceMatcher(None, typo.lower(), rep.lower()).ratio()
        rep_in_text = rep.lower() in chunk_text.lower()
        if sim < 0.65 and not rep_in_text:
            logger.info("Rejected Critic typo fix '%s' -> '%s' (similarity %.2f too low and replacement not in text)", typo, rep, sim)
            continue

        # Subject Replacement
        if typo.lower() in triple.subject.name.lower():
            triple.subject.name = re.sub(re.escape(typo), rep, triple.subject.name, flags=re.IGNORECASE)
            logger.info("Accepted Critic typo edit in subject: '%s' -> '%s' (Result: '%s')", typo, rep, triple.subject.name)
        else:
            words = triple.subject.name.split()
            new_words = []
            for w in words:
                w_sim = difflib.SequenceMatcher(None, typo.lower(), w.lower()).ratio()
                if w_sim >= 0.8:
                    new_words.append(rep)
                    logger.info("Accepted Critic fuzzy typo edit in subject: '%s' -> '%s'", w, rep)
                else:
                    new_words.append(w)
            triple.subject.name = " ".join(new_words)

        # Object Replacement
        if typo.lower() in triple.object.name.lower():
            triple.object.name = re.sub(re.escape(typo), rep, triple.object.name, flags=re.IGNORECASE)
            logger.info("Accepted Critic typo edit in object: '%s' -> '%s' (Result: '%s')", typo, rep, triple.object.name)
        else:
            words = triple.object.name.split()
            new_words = []
            for w in words:
                w_sim = difflib.SequenceMatcher(None, typo.lower(), w.lower()).ratio()
                if w_sim >= 0.8:
                    new_words.append(rep)
                    logger.info("Accepted Critic fuzzy typo edit in object: '%s' -> '%s'", w, rep)
                else:
                    new_words.append(w)
            triple.object.name = " ".join(new_words)

    return triple

def evaluate_triples(extraction: ExtractionOutput) -> List[CriticEvaluation]:
    """Evaluate triples using Adversarial Critic LLM (OpenAI, Ollama, Llama.cpp, vLLM, Gemma)."""
    start_time = time.time()
    provider = settings.LLM_PROVIDER.lower().replace("-", "_")
    
    try:
        from openai import OpenAI
        base_url = settings.LLM_BASE_URL if provider != "openai" else None
        api_key = settings.OPENAI_API_KEY if settings.OPENAI_API_KEY else "local"
        
        logger.info("--> [Critic Start] chunk_id: '%s' | Model: '%s' | Evaluating %d triples", extraction.chunk_id, settings.LLM_MODEL, len(extraction.triples))
        logger.info("--> [Critic Prompt] System: %s", CRITIC_SYSTEM_PROMPT.strip())
        
        mode = instructor.Mode.MD_JSON if provider != "openai" else instructor.Mode.TOOLS
        client = instructor.from_openai(OpenAI(base_url=base_url, api_key=api_key), mode=mode)
        
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
        logger.error("!!! [Critic Failed after %.2fs] (%s): %s", elapsed, provider, e)
        raise RuntimeError(f"LLM Critic evaluation failed: {e}") from e
