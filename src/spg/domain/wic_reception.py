"""Provider-neutral, read-only contracts for low-latency WIC reception."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FastReceptionVisibility(StrEnum):
    SHADOW = "SHADOW"
    SAFE_TO_EMIT = "SAFE_TO_EMIT"
    BLOCKED = "BLOCKED"


class FastReceptionState(StrEnum):
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"


class FastReceptionPurpose(StrEnum):
    WIC_FAST_RECEPTION = "WIC_FAST_RECEPTION"
    WIC_DEEP_SEMANTICS = "WIC_DEEP_SEMANTICS"
    WIC_RESPONSE_REALIZATION = "WIC_RESPONSE_REALIZATION"
    WIC_EVALUATION = "WIC_EVALUATION"


class WicCapabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    purpose: FastReceptionPurpose
    latency_budget_ms: int = Field(gt=0)
    reasoning_need: Literal["NONE", "LOW", "DEEP"]
    max_output_tokens: int = Field(gt=0)
    allowed_data_sensitivity: Literal["PUBLIC", "INTERNAL", "SENSITIVE"]
    fallback: Literal["SUPPRESS", "DEEP_ONLY"]
    require_provenance: bool = True


class FastContextCard(BaseModel):
    """Small rebuildable projection; never governed or conversation truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    interaction_id: UUID
    interaction_sequence: int = Field(ge=1)
    condition: Literal["PRE_WORK", "ACTIVE_WORK"]
    motive: str | None = None
    desired_outcome: str | None = None
    active_work_id: UUID | None = None
    active_work_revision_id: UUID | None = None
    active_work_revision_number: int | None = Field(default=None, ge=1)
    current_focus: str | None = None
    material_facts: tuple[str, ...] = ()
    material_constraints: tuple[str, ...] = ()
    current_requests: tuple[str, ...] = ()
    unresolved_human_decisions: tuple[str, ...] = ()
    last_correction: str | None = None
    correction_supersedes: str | None = None
    response_language: str
    source_references: tuple[str, ...] = ()
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    serialized_characters: int = Field(ge=0)
    serialized_bytes: int = Field(ge=0)
    estimated_tokens: int = Field(ge=0)
    source_count: int = Field(ge=1)
    build_latency_ms: float = Field(ge=0)
    built_at: datetime


class FastReceptionCandidate(BaseModel):
    """A provisional observation with no mutation or admission surface."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    interaction_id: UUID
    turn_id: UUID
    source_record_id: UUID
    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    fast_context_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    active_work_id: UUID | None = None
    active_work_revision_id: UUID | None = None
    provisional_turn_intent: str
    captured_object: str | None = None
    current_focus: str | None = None
    captured_explicit_constraints: tuple[str, ...] = ()
    detected_correction: str | None = None
    detected_human_owned_decision: str | None = None
    confidence: float = Field(ge=0, le=1)
    grounding_references: tuple[str, ...] = Field(min_length=1)
    meaningful_sentence: str = Field(min_length=1)
    provider: str
    model: str | None = None
    profile: str
    started_at: datetime
    first_delta_ms: float | None = Field(default=None, ge=0)
    candidate_ready_ms: float = Field(ge=0)
    provider_request_id: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    retry_count: int = Field(default=0, ge=0)
    authority: Literal["PROVISIONAL_READ_ONLY"] = "PROVISIONAL_READ_ONLY"
    visibility_disposition: FastReceptionVisibility
    policy_disposition: FastReceptionVisibility
    state: FastReceptionState = FastReceptionState.CURRENT


class FastReceptionObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    turn_id: UUID
    correlation_id: UUID
    purpose: Literal["WIC_FAST_RECEPTION"] = "WIC_FAST_RECEPTION"
    started_at: datetime
    terminal_at: datetime
    status: Literal["CANDIDATE", "NO_EMISSION", "FAILED", "TIMED_OUT"]
    stage: str
    provider: str | None = None
    model: str | None = None
    profile: str | None = None
    first_delta_ms: float | None = Field(default=None, ge=0)
    terminal_ms: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    request_sent: bool | None = None
    usage_unknown: bool | None = None
    retryable: bool | None = None
    candidate: FastReceptionCandidate | None = None
    failure_type: str | None = None
    failure_message: str | None = None
    retry_count: int = 0
