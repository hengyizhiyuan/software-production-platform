"""Human-visible WIC response lifecycle without creating semantic authority."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Callable, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from spg.domain.conversation import ConversationContextMessage, InteractionStrategy
from spg.domain.production_intelligence import CognitiveContextPackage
from spg.domain.response_contract import ResponseContract


class WicRuntimeMode(StrEnum):
    LEGACY_WIC = "LEGACY_WIC"
    WIC_VNEXT_SHADOW = "WIC_VNEXT_SHADOW"
    WIC_VNEXT_CONTROLLED = "WIC_VNEXT_CONTROLLED"


class WicResponseEventType(StrEnum):
    TURN_ACCEPTED = "TURN_ACCEPTED"
    FAST_RECEPTION_STARTED = "FAST_RECEPTION_STARTED"
    PROVISIONAL_RESPONSE = "PROVISIONAL_RESPONSE"
    FAST_SUPPRESSED = "FAST_SUPPRESSED"
    RESPONSE_CONTRACT_READY = "RESPONSE_CONTRACT_READY"
    RESPONSE_REFINEMENT = "RESPONSE_REFINEMENT"
    RESPONSE_CORRECTION = "RESPONSE_CORRECTION"
    RESPONSE_STREAM_STARTED = "RESPONSE_STREAM_STARTED"
    RESPONSE_DELTA = "RESPONSE_DELTA"
    FINAL_RESPONSE = "FINAL_RESPONSE"
    TURN_COMPLETED = "TURN_COMPLETED"
    TURN_FAILED = "TURN_FAILED"
    TURN_RECOVERY_STARTED = "TURN_RECOVERY_STARTED"


class ResponseTrustStage(StrEnum):
    """Human-visible response maturity; only FINAL is settled Conversation truth."""

    PROVISIONAL = "PROVISIONAL"
    GOVERNED = "GOVERNED"
    FINAL = "FINAL"


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
    AMBIGUOUS = "AMBIGUOUS"
    UNRECOGNIZED = "UNRECOGNIZED"


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


class GovernedResponseEnvelope(BaseModel):
    """Read-only expression handoff derived from already governed WIC Reality.

    The envelope is not a new Truth owner. It constrains a replaceable Realizer
    to wording and pacing after semantic admission has completed.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    governed_content: str = Field(min_length=1)
    provisional_content: str | None = None
    reconciliation: ResponseReconciliation
    working_motive: str | None = None
    working_desired_outcome: str | None = None
    facts_to_preserve: tuple[str, ...] = ()
    semantic_truth_to_preserve: tuple[str, ...] = ()
    constraints_to_preserve: tuple[str, ...] = ()
    unresolved_human_decisions: tuple[str, ...] = ()
    explicit_assumptions: tuple[str, ...] = ()
    selected_question: str | None = None
    governance_candidate: str
    forbidden_claims: tuple[str, ...] = ()
    source_references: tuple[str, ...] = ()
    semantic_policy_revision: str
    question_policy_revision: str
    response_language: str
    interaction_strategy: InteractionStrategy
    cognitive_context_package: CognitiveContextPackage | None = None
    # Optional only for already persisted/legacy callers. Controlled WIC supplies
    # an admitted turn contract before expression; it does not confer authority.
    response_contract: ResponseContract | None = None
    previous_response_contract: ResponseContract | None = None
    latest_human_input: str | None = None
    recent_relevant_messages: tuple[ConversationContextMessage, ...] = ()


class GovernedResponseRealization(BaseModel):
    """Provider-neutral expression evidence; never Conversation truth itself."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str = Field(min_length=1)
    provider_identity: str = Field(min_length=1)
    model_identity: str | None = None
    request_id: str | None = None
    usage: dict[str, Any] | None = None
    timing: dict[str, Any] | None = None


class GovernedResponseRealizer(Protocol):
    """Express an admitted envelope without owning its semantics."""

    provider_identity: str
    model_identity: str | None

    def realize_stream(
        self,
        envelope: GovernedResponseEnvelope,
        *,
        on_response_delta: Callable[[str], None],
    ) -> GovernedResponseRealization: ...
