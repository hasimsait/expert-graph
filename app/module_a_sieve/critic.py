import logging
import re
import difflib
import time
from typing import List
from pydantic import BaseModel
from app.config import settings
from app.module_a_sieve.schemas import ExtractionOutput, CriticEvaluation, ExtractedTriple, TypoCorrection
from app.services.llm_service import get_llm_service
from app.services.prompt_manager import get_prompt_manager

logger = logging.getLogger(__name__)

def _apply_typo_to_string(text: str, typo: str, rep: str) -> str:
    pattern = r'\b' + re.escape(typo) + r'\b'
    if re.search(pattern, text, flags=re.IGNORECASE):
        new_text = re.sub(pattern, rep, text, flags=re.IGNORECASE)
        logger.info("Accepted Critic typo edit: '%s' -> '%s' (Result: '%s')", typo, rep, new_text)
        return new_text
        
    words = text.split()
    new_words = []
    for w in words:
        w_sim = difflib.SequenceMatcher(None, typo.lower(), w.lower()).ratio()
        if w_sim >= 0.8:
            new_words.append(rep)
            logger.info("Accepted Critic fuzzy typo edit: '%s' -> '%s'", w, rep)
        else:
            new_words.append(w)
    return " ".join(new_words)

def validate_and_apply_typo_corrections(
    triple: ExtractedTriple,
    corrections: List[TypoCorrection],
    chunk_text: str
) -> ExtractedTriple:
    """Validates Critic typo correction suggestions and applies them to extracted entity names."""
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

        triple.subject.name = _apply_typo_to_string(triple.subject.name, typo, rep)
        triple.object.name = _apply_typo_to_string(triple.object.name, typo, rep)

    return triple

class BatchCriticEvaluation(BaseModel):
    evaluations: List[CriticEvaluation]

async def evaluate_triples(extraction: ExtractionOutput) -> List[CriticEvaluation]:
    """Evaluate triples using Adversarial Critic LLM asynchronously."""
    start_time = time.time()
    
    llm_service = get_llm_service()
    prompt_manager = get_prompt_manager()
    
    provider = llm_service.provider
    system_prompt = prompt_manager.get_critic_prompt()
    
    try:
        logger.info("--> [Critic Start] chunk_id: '%s' | Model: '%s' | Evaluating %d triples", extraction.chunk_id, settings.LLM_MODEL, len(extraction.triples))
        logger.info("--> [Critic Prompt] System: %s", system_prompt.strip())
        
        client = llm_service.get_instructor_client()
        
        prompt_content = f"Chunk Text:\n{extraction.chunk_text}\n\nProposed Triples:\n"
        for idx, t in enumerate(extraction.triples):
            prompt_content += f"[{idx}] ({t.subject.name}) -[{t.relation}]-> ({t.object.name})\n"
            
        logger.info("--> [Critic Input Triples]\n%s", prompt_content.strip())

        llm_kwargs = llm_service.get_llm_kwargs(
            response_model=BatchCriticEvaluation,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_content}
            ]
        )

        res = await client.chat.completions.create(**llm_kwargs)
        elapsed = time.time() - start_time
        valid_cnt = sum(1 for ev in res.evaluations if ev.is_valid)
        logger.info("<-- [Critic Done] chunk_id: '%s' | Validated %d/%d triples in %.2fs", extraction.chunk_id, valid_cnt, len(res.evaluations), elapsed)
        return res.evaluations
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("!!! [Critic Failed after %.2fs] (%s): %s", elapsed, provider, e)
        raise RuntimeError(f"LLM Critic evaluation failed: {e}") from e
