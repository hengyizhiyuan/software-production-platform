"""Derived WIC expression input. No Engineering or Semantic Truth is owned here."""
from pydantic import BaseModel, ConfigDict, Field


class HumanVisibleProjection(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    schema_version: str = 'wic-human-visible-v1'
    basis_fingerprint: str
    governed_motive: str
    governed_semantic_ir: dict | None
    owner_facts: dict
    agenda: tuple[dict, ...]
    decision_needs: tuple[dict, ...]
    production_units: tuple[dict, ...]
    source_references: tuple[str, ...]


class SurfaceText(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    id: str
    text: str = Field(min_length=1, max_length=500)


class SurfaceDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    id: str
    title: str = Field(min_length=1, max_length=150)
    question: str = Field(min_length=1, max_length=600)
    why_now: str = Field(min_length=1, max_length=600)


class HumanVisibleWording(BaseModel):
    """Only expression fields; no status, readiness, outcome, authority or action."""
    model_config = ConfigDict(extra='forbid', frozen=True)
    headline: str = Field(min_length=1, max_length=250)
    summary: str = Field(min_length=1, max_length=600)
    current_activity: str = Field(min_length=1, max_length=400)
    next_step: str = Field(min_length=1, max_length=400)
    agenda: tuple[SurfaceText, ...]
    decisions: tuple[SurfaceDecision, ...]
    production_units: tuple[SurfaceText, ...]
