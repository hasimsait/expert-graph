import logging
import re
from typing import List
import instructor
from pydantic import BaseModel
from app.config import settings
from app.module_a_sieve.schemas import ExtractionOutput, ExtractedTriple, Entity, ConceptMapping

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """
You are an expert Information Extraction Sieve. Your task is to pull factual triples (Subject, Relation, Object) from raw text chunks.
Follow these strict rules:
1. Normalize entity names and uppercase relation names (e.g., OWES_DEBT, LAWSUIT_AGAINST, TRANSFERS_FUNDS, SUBSIDIARY_OF).
2. If you introduce a relation name that is NOT standard, you MUST output a concept_mapping tying it to an existing Meta-Graph concept via SUBCLASS_OF or SYNONYM_OF.
3. Never hallucinate facts that are not explicitly stated in the chunk text.
"""

def mock_extract(chunk_id: str, chunk_text: str) -> ExtractionOutput:
    """Intelligent rule-based extractor fallback when LLM keys are absent."""
    triples: List[ExtractedTriple] = []
    
    # 1. Pathology / Medical Specimen & Diagnosis patterns
    specimen_match = re.search(r'SPECIMEN:\s*([^.]+?\b(?:biopsy|resection|aspiration|tissue|lesion)\b[^.]*?)(?=\.|\s+DIAGNOSIS|$)', chunk_text, re.IGNORECASE)
    diag_match = re.search(r'DIAGNOSIS:\s*([^.]+?\b(?:carcinoma|adenocarcinoma|melanoma|dysplasia|adenoma|lesion|tumor)\b[^.]*?)(?=\.|\s+BIOMARKERS|\s+MARGINS|$)', chunk_text, re.IGNORECASE)
    gene_match = re.search(r'\b(HER2|EGFR|BRAF|TP53|KRAS|ALK|BRCA1|BRCA2|PD-L1)\b', chunk_text, re.IGNORECASE)
    
    if specimen_match and diag_match:
        spec_text = specimen_match.group(1).strip()
        diag_text = diag_match.group(1).strip()
        
        triples.append(ExtractedTriple(
            subject=Entity(name=spec_text, type="PATHOLOGY_SPECIMEN"),
            relation="FOUND_IN_SPECIMEN",
            object=Entity(name=diag_text, type="DISEASE_DIAGNOSIS"),
            concept_mapping=ConceptMapping(
                new_relation="FOUND_IN_SPECIMEN",
                existing_concept="MEDICAL_CONDITION",
                mapping_type="SUBCLASS_OF",
                description="Clinical specimen diagnosed with pathological condition"
            )
        ))

    if gene_match and diag_match:
        gene_name = gene_match.group(1).upper()
        diag_text = diag_match.group(1).strip()
        
        triples.append(ExtractedTriple(
            subject=Entity(name=diag_text, type="DISEASE_DIAGNOSIS"),
            relation="ASSOCIATED_GENE",
            object=Entity(name=gene_name, type="GENE_BIOMARKER"),
            concept_mapping=ConceptMapping(
                new_relation="ASSOCIATED_GENE",
                existing_concept="BIOLOGICAL_PROCESS",
                mapping_type="SUBCLASS_OF",
                description="Pathological diagnosis associated with specific gene mutation or biomarker"
            )
        ))

    # 2. Debt / Owes
    debt_match = re.search(r'([A-Z][a-zA-Z0-9\s]+?)\s+(?:owes|is indebted to|has a debt of)\s+(?:\$?\d+[\d,]*\s+to\s+)?([A-Z][a-zA-Z0-9\s]+?)(?=\s+following|\s+under|\s+as|\.|$)', chunk_text)
    if debt_match:
        subj = debt_match.group(1).strip()
        obj = debt_match.group(2).strip()
        triples.append(ExtractedTriple(
            subject=Entity(name=subj, type="ORGANIZATION"),
            relation="OWES_DEBT",
            object=Entity(name=obj, type="ORGANIZATION"),
            concept_mapping=None
        ))

    # 3. Lawsuit / Legal conflict
    lawsuit_match = re.search(r'([A-Z][a-zA-Z0-9\s]+?)\s+(?:filed a lawsuit against|sued|is suing)\s+([A-Z][a-zA-Z0-9\s]+?)(?=\s+regarding|\s+for|\s+in|\.|$)', chunk_text)
    if lawsuit_match:
        subj = lawsuit_match.group(1).strip()
        obj = lawsuit_match.group(2).strip()
        triples.append(ExtractedTriple(
            subject=Entity(name=subj, type="ORGANIZATION"),
            relation="LAWSUIT_AGAINST",
            object=Entity(name=obj, type="ORGANIZATION"),
            concept_mapping=None
        ))

    # 4. Investment / Equity
    invest_match = re.search(r'([A-Z][a-zA-Z0-9\s]+?)\s+(?:invested \$?\d+[\d,]* in|acquired a \d+%\s+equity stake in|acquired a stake in)\s+([A-Z][a-zA-Z0-9\s]+?)(?=\s+as|\s+in|\.|$)', chunk_text)
    if invest_match:
        subj = invest_match.group(1).strip()
        obj = invest_match.group(2).strip()
        triples.append(ExtractedTriple(
            subject=Entity(name=subj, type="ORGANIZATION"),
            relation="EQUITY_STAKE",
            object=Entity(name=obj, type="ORGANIZATION"),
            concept_mapping=ConceptMapping(
                new_relation="EQUITY_STAKE",
                existing_concept="INVESTED_IN",
                mapping_type="SUBCLASS_OF"
            )
        ))

    # Default fallback if regex does not hit
    if not triples:
        caps = [c for c in re.findall(r'[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*', chunk_text) if c.lower() not in {'specimen', 'diagnosis', 'biomarkers', 'margins'}]
        if len(caps) >= 2:
            triples.append(ExtractedTriple(
                subject=Entity(name=caps[0], type="ENTITY"),
                relation="ASSOCIATED_WITH",
                object=Entity(name=caps[1], type="ENTITY"),
                concept_mapping=ConceptMapping(
                    new_relation="ASSOCIATED_WITH",
                    existing_concept="RELATIONSHIP",
                    mapping_type="SUBCLASS_OF"
                )
            ))
        else:
            words = [w for w in re.findall(r'\b[a-zA-Z0-9]{3,}\b', chunk_text) if w.lower() not in {'specimen', 'diagnosis', 'biomarkers', 'margins', 'the', 'and', 'for', 'that', 'with', 'from', 'this', 'have', 'were'}]
            subj_name = words[0].title() if len(words) >= 1 else "Sample Entity A"
            obj_name = words[-1].title() if len(words) >= 2 else "Sample Entity B"
            triples.append(ExtractedTriple(
                subject=Entity(name=subj_name, type="CLINICAL_TERM"),
                relation="ASSOCIATED_WITH",
                object=Entity(name=obj_name, type="CLINICAL_TERM"),
                concept_mapping=ConceptMapping(
                    new_relation="ASSOCIATED_WITH",
                    existing_concept="RELATIONSHIP",
                    mapping_type="SUBCLASS_OF"
                )
            ))

    return ExtractionOutput(chunk_id=chunk_id, chunk_text=chunk_text, triples=triples)


def extract_triples(chunk_id: str, chunk_text: str) -> ExtractionOutput:
    """Extract structured triples using Instructor LLM (OpenAI, Ollama, Llama.cpp, vLLM, Gemma) or fallback."""
    import time
    start_time = time.time()
    provider = settings.LLM_PROVIDER.lower().replace("-", "_")
    
    if provider != "mock":
        try:
            from openai import OpenAI
            base_url = settings.LLM_BASE_URL if provider != "openai" else None
            api_key = settings.OPENAI_API_KEY if settings.OPENAI_API_KEY else "local"
            
            logger.info("--> [Extractor Start] chunk_id: '%s' | Model: '%s' | Provider: '%s' | Endpoint: '%s'", chunk_id, settings.LLM_MODEL, provider, base_url or "OpenAI Cloud")
            logger.info("--> [Extractor Prompt] System: %s", EXTRACTION_SYSTEM_PROMPT.strip())
            logger.info("--> [Extractor Input Text] %s", chunk_text)

            client = instructor.from_openai(OpenAI(base_url=base_url, api_key=api_key))
            result = client.chat.completions.create(
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
            logger.error("!!! [Extractor Failed after %.2fs] (%s): %s. Using mock fallback.", elapsed, provider, e)
            return mock_extract(chunk_id, chunk_text)
    else:
        logger.info("Running Extractor in mock mode for chunk_id: %s", chunk_id)
        return mock_extract(chunk_id, chunk_text)
