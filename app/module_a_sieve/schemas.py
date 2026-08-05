from typing import List, Optional
from pydantic import BaseModel, Field

class Entity(BaseModel):
    name: str = Field(..., description="Unique entity name, e.g., 'Acme Corp', 'Alice Smith'")
    type: str = Field("ORGANIZATION", description="Type of entity: PERSON, ORGANIZATION, CONCEPT, etc.")

class ConceptMapping(BaseModel):
    new_relation: str = Field(..., description="The proposed relation name if not in standard Meta-Graph (e.g. 'INHIBITS_ENZYME', 'TREATS_CONDITION', 'DEBT_OBLIGATION')")
    existing_concept: str = Field("RELATIONSHIP", description="Existing Meta-Graph concept to map to (e.g. 'BIOLOGICAL_PROCESS', 'OWES_DEBT', 'RELATIONSHIP')")
    mapping_type: str = Field("SUBCLASS_OF", description="Relationship mapping type: 'SUBCLASS_OF', 'SYNONYM_OF', 'RELATED_TO', 'CAUSES', 'PART_OF'")
    description: Optional[str] = Field(None, description="Definition or rationale for adding this new relation concept to the ontology")

class ExtractedTriple(BaseModel):
    subject: Entity
    relation: str = Field(..., description="Relation name, UPPERCASE_SNAKE_CASE (e.g. 'OWES_DEBT', 'EMPLOYED_BY')")
    object: Entity
    concept_mapping: Optional[ConceptMapping] = Field(
        None, 
        description="Required if relation is a novel concept requiring mapping to Meta-Graph"
    )

class ExtractionOutput(BaseModel):
    chunk_id: str
    chunk_text: str
    triples: List[ExtractedTriple] = Field(default_factory=list)

class CriticEvaluation(BaseModel):
    triple_index: int
    is_valid: bool = Field(..., description="Adversarial check: Is this fact explicitly supported by the text chunk?")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    critique_notes: str = Field("", description="Reasoning or notes on discrepancy")

class SieveResult(BaseModel):
    chunk_id: str
    chunk_text: str
    processed_triples: List[dict] # Contains triple, critic result, status: pending
