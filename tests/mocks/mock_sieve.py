import re
from typing import List
from app.module_a_sieve.schemas import ExtractionOutput, ExtractedTriple, Entity, ConceptMapping, CriticEvaluation

async def test_mock_extract(chunk_id: str, chunk_text: str) -> ExtractionOutput:
    """Rule-based extractor used exclusively in unit test suite asynchronously."""
    triples: List[ExtractedTriple] = []
    
    specimen_match = re.search(r'SPECIMEN:\s*([^.]+?\b(?:biopsy|resection|aspiration|tissue|lesion)\b[^.]*?)(?=\.|\s+DIAGNOSIS|$)', chunk_text, re.IGNORECASE)
    diag_match = re.search(r'DIAGNOSIS:\s*([^.]+?\b(?:carcinoma|adenocarcinoma|melanoma|dysplasia|adenoma|lesion|tumor)\b[^.]*?)(?=\.|\s+BIOMARKERS|\s+MARGINS|$)', chunk_text, re.IGNORECASE)
    gene_match = re.search(r'\b(HER2|EGFR|BRAF|TP53|KRAS|ALK|BRCA1|BRCA2|PD-L1)\b', chunk_text, re.IGNORECASE)
    
    if specimen_match and diag_match:
        triples.append(ExtractedTriple(
            subject=Entity(name=specimen_match.group(1).strip(), type="PATHOLOGY_SPECIMEN"),
            relation="FOUND_IN_SPECIMEN",
            object=Entity(name=diag_match.group(1).strip(), type="DISEASE_DIAGNOSIS"),
            concept_mapping=ConceptMapping(
                new_relation="FOUND_IN_SPECIMEN",
                existing_concept="MEDICAL_CONDITION",
                mapping_type="SUBCLASS_OF"
            )
        ))

    if gene_match and diag_match:
        triples.append(ExtractedTriple(
            subject=Entity(name=diag_match.group(1).strip(), type="DISEASE_DIAGNOSIS"),
            relation="ASSOCIATED_GENE",
            object=Entity(name=gene_match.group(1).upper(), type="GENE_BIOMARKER"),
            concept_mapping=ConceptMapping(
                new_relation="ASSOCIATED_GENE",
                existing_concept="BIOLOGICAL_PROCESS",
                mapping_type="SUBCLASS_OF"
            )
        ))

    debt_match = re.search(r'([A-Z][a-zA-Z0-9\s]+?)\s+(?:owes|is indebted to|has a debt of)\s+(?:\$?\d+[\d,]*\s+to\s+)?([A-Z][a-zA-Z0-9\s]+?)(?=\s+following|\s+under|\s+as|\.|$)', chunk_text)
    if debt_match:
        triples.append(ExtractedTriple(
            subject=Entity(name=debt_match.group(1).strip(), type="ORGANIZATION"),
            relation="OWES_DEBT",
            object=Entity(name=debt_match.group(2).strip(), type="ORGANIZATION")
        ))

    lawsuit_match = re.search(r'([A-Z][a-zA-Z0-9\s]+?)\s+(?:filed a lawsuit against|sued|is suing)\s+([A-Z][a-zA-Z0-9\s]+?)(?=\s+regarding|\s+for|\s+in|\.|$)', chunk_text)
    if lawsuit_match:
        triples.append(ExtractedTriple(
            subject=Entity(name=lawsuit_match.group(1).strip(), type="ORGANIZATION"),
            relation="LAWSUIT_AGAINST",
            object=Entity(name=lawsuit_match.group(2).strip(), type="ORGANIZATION")
        ))

    if not triples:
        triples.append(ExtractedTriple(
            subject=Entity(name="Test Subject", type="ENTITY"),
            relation="ASSOCIATED_WITH",
            object=Entity(name="Test Object", type="ENTITY")
        ))

    return ExtractionOutput(chunk_id=chunk_id, chunk_text=chunk_text, triples=triples)

async def test_mock_evaluate(extraction: ExtractionOutput) -> List[CriticEvaluation]:
    """Rule-based critic evaluator used exclusively in unit test suite asynchronously."""
    results = []
    for i, _ in enumerate(extraction.triples):
        results.append(CriticEvaluation(
            triple_index=i,
            is_valid=True,
            confidence=0.95,
            critique_notes="Test mock critique verification"
        ))
    return results
