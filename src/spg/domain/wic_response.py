"""Human-visible WIC response lifecycle without creating semantic authority."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WicRuntimeMode(StrEnum):
    LEGACY_WIC = "LEGACY_WIC"
    WIC_VNEXT_SHADOW = "WIC_VNEXT_SHADOW"
    WIC_VNEXT_CONTROLLED = "WIC_VNEXT_CONTROLLED"


class WicResponseEventType(StrEnum):
    TURN_ACCEPTED = "TURN_ACCEPTED"
    FAST_RECEPTION_STARTED = "FAST_RECEPTION_STARTED"
    PROVISIONAL_RESPONSE = "PROVISIONAL_RESPONSE"
    FAST_SUPPRESSED = "FAST_SUPPRESSED"
    RESPONSE_REFINEMENT = "RESPONSE_REFINEMENT"
    RESPONSE_CORRECTION = "RESPONSE_CORRECTION"
    FINAL_RESPONSE = "FINAL_RESPONSE"
    TURN_COMPLETED = "TURN_COMPLETED"
    TURN_FAILED = "TURN_FAILED"


class ResponseReconciliation(StrEnum):
    CONFIRM = "CONFIRM"
    REFINE = "REFINE"
    MATERIAL_CORRECTION = "MATERIAL_CORRECTION"


class FastSuppressionReason(StrEnum):
    MODE_DISABLED = "MODE_DISABLED"
    NO_EXPLICIT_MEANING = "NO_EXPLICIT_MEANING"
    STALE_CONTEXT = "STALE_CONTEXT"
    INSUFFICIENT_GROUNDING = "INSUFFICIENT_GROUNDING"
    MATERIAL_CONFLICT = "MATERIAL_CONFLICT"
    AUTHORITY_POLICY = "AUTHORITY_POLICY"
    FAST_FAILURE = "FAST_FAILURE"


class WicResponseEvent(BaseModel):
    """Replayable UX evidence. Conversation and Work remain the truth owners."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    interaction_id: UUID
    turn_id: UUID
    response_id: UUID
    sequence: int = Field(ge=1)
    event_type: WicResponseEventType
    content: str | None = None
    basis_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    reconciliation: ResponseReconciliation | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
