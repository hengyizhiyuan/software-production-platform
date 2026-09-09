"""Provider-neutral candidate framing for the object of a design interaction."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DesignObjectType(StrEnum):
    PRODUCT_SYSTEM = "PRODUCT_SYSTEM"
    BUSINESS_PROCESS = "BUSINESS_PROCESS"
    FEATURE = "FEATURE"
    OPERATIONAL_ACTIVITY = "OPERATIONAL_ACTIVITY"
    REVIEW_ANALYSIS = "REVIEW_ANALYSIS"
    UNKNOWN = "UNKNOWN"


class DesignScopeLevel(StrEnum):
    STRATEGIC = "strategic"
    PRODUCT = "product"
    CAPABILITY = "capability"
    IMPLEMENTATION = "implementation"


class DesignCollaborationMode(StrEnum):
    EXPLORATION = "exploration"
    DESIGN = "design"
    EXECUTION = "execution"
    REVIEW = "review"


class DesignIntentFrame(BaseModel):
    """Concise advisory interpretation; never Work or Design truth by itself."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    design_subject: str = Field(min_length=1)
    object_type: DesignObjectType
    business_context: str | None = None
    desired_outcome: str | None = None
    scope_level: DesignScopeLevel
    collaboration_mode: DesignCollaborationMode
    candidate_assumptions: tuple[str, ...] = ()
    ambiguities: tuple[str, ...] = ()
    confidence: float = Field(ge=0, le=1)

    @field_validator(
        "design_subject",
        "business_context",
        "desired_outcome",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("candidate_assumptions", "ambiguities")
    @classmethod
    def normalize_items(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))

    @model_validator(mode="after")
    def unknown_object_exposes_ambiguity(self) -> "DesignIntentFrame":
        if self.object_type is DesignObjectType.UNKNOWN and not self.ambiguities:
            raise ValueError("UNKNOWN design object requires an explicit ambiguity")
        return self
