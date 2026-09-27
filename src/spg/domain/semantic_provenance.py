"""Typed source witnesses shared by IRK and Engineering Semantic Truth."""
from enum import StrEnum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

class SemanticOrigin(StrEnum):
    HUMAN_EXPLICIT = "HUMAN_EXPLICIT"
    HUMAN_CORRECTION = "HUMAN_CORRECTION"
    REPOSITORY_OBSERVED = "REPOSITORY_OBSERVED"
    SYSTEM_INFERRED = "SYSTEM_INFERRED"
    MODEL_CANDIDATE = "MODEL_CANDIDATE"
    POLICY_DERIVED = "POLICY_DERIVED"


class FrozenContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SemanticProvenance(FrozenContract):
    origin: SemanticOrigin
    source_record_id: UUID | None = None
    source_text: str | None = None
    evidence_reference: str | None = None

    @model_validator(mode="after")
    def requires_evidence(self):
        if self.origin in {SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}:
            if self.source_record_id is None or not self.source_text:
                raise ValueError("ACTION_ARGUMENT_PROVENANCE_INVALID: Human provenance requires an exact source span")
        elif not self.evidence_reference:
            raise ValueError("ACTION_ARGUMENT_PROVENANCE_INVALID: non-Human provenance requires evidence")
        return self


class SemanticArgument(FrozenContract):
    value: str = Field(min_length=1)
    provenance: SemanticProvenance


