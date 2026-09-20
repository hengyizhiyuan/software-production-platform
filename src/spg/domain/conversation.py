"""Provider-neutral Human-facing conversation contracts.

Conversation turns governed collaboration semantics into language for a Human.
None of the types in this module own Work, Design, Plan, Authority, Evidence, or
Runtime truth.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Callable, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from spg.domain.design_intent import DesignIntentFrame
from spg.domain.engineering_semantics import (
    EngineeringSemanticFact,
    EngineeringSemanticFactCandidate,
)


class ConversationTurnIntent(StrEnum):
    """The Human's purpose for this turn, independent of cognitive maturity.

    The older collaboration intents remain valid for persisted history and
    compatibility.  The concise intents below are the preferred vocabulary for
    new interaction-intelligence results.
    """

    BUILD = "BUILD"
    HOW_TO = "HOW_TO"
    RECOMMEND = "RECOMMEND"
    COMPARE = "COMPARE"
    EXPLORE = "EXPLORE"
    MODIFY = "MODIFY"
    DEPLOY = "DEPLOY"
    ACTION_REQUEST = "ACTION_REQUEST"
    DIRECT_QUESTION = "DIRECT_QUESTION"
    NEW_GOAL = "NEW_GOAL"
    CONTEXT_ADDITION = "CONTEXT_ADDITION"
    CORRECTION = "CORRECTION"
    DISAGREEMENT = "DISAGREEMENT"
    REQUEST_RECOMMENDATION = "REQUEST_RECOMMENDATION"
    REQUEST_DECISION_SUPPORT = "REQUEST_DECISION_SUPPORT"
    REQUEST_DETAIL = "REQUEST_DETAIL"
    SIDE_QUESTION = "SIDE_QUESTION"
    CONTINUE_CURRENT_WORK = "CONTINUE_CURRENT_WORK"
    MATERIAL_BRANCH = "MATERIAL_BRANCH"
    FEEDBACK = "FEEDBACK"
    HUMAN_DECISION = "HUMAN_DECISION"


class ConversationAttentionLevel(StrEnum):
    NORMAL = "NORMAL"
    IMPORTANT = "IMPORTANT"
    URGENT = "URGENT"


class ConversationPolicyHint(StrEnum):
    ANSWER_FIRST = "ANSWER_FIRST"
    GUIDE_PROACTIVELY = "GUIDE_PROACTIVELY"
    ACKNOWLEDGE_CORRECTION = "ACKNOWLEDGE_CORRECTION"
    EXPLAIN_TRADE_OFFS = "EXPLAIN_TRADE_OFFS"
    EXPLAIN_FAILURE_DIRECTLY = "EXPLAIN_FAILURE_DIRECTLY"
    PRESERVE_HUMAN_DECISION = "PRESERVE_HUMAN_DECISION"
    RETURN_TO_CURRENT_FOCUS = "RETURN_TO_CURRENT_FOCUS"


class HumanAbstractionLevel(StrEnum):
    """Altitude of the Human's latest expression, not product readiness."""

    VISION = "VISION"
    DOMAIN = "DOMAIN"
    SOLUTION = "SOLUTION"
    IMPLEMENTATION = "IMPLEMENTATION"


class CognitiveMaturity(StrEnum):
    """How formed the Human's current thinking is for this turn."""

    EXPLORING = "EXPLORING"
    FRAMING = "FRAMING"
    EVALUATING = "EVALUATING"
    SPECIFYING = "SPECIFYING"


class HumanConversationMode(StrEnum):
    EXPLORING = "EXPLORING"
    DECIDING = "DECIDING"
    CORRECTING = "CORRECTING"
    ASKING = "ASKING"
    SPECIFYING = "SPECIFYING"


class ConversationalMove(StrEnum):
    ORIENT = "ORIENT"
    EXPLAIN = "EXPLAIN"
    PROPOSE = "PROPOSE"
    COMPARE = "COMPARE"
    ANSWER = "ANSWER"
    ASK = "ASK"
    CONFIRM = "CONFIRM"
    CORRECT = "CORRECT"
    ESCALATE_HUMAN_DECISION = "ESCALATE_HUMAN_DECISION"


class InteractionStrategy(BaseModel):
    """Turn-taking advice over governed semantics; never a Product Truth owner."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    turn_intent: ConversationTurnIntent = ConversationTurnIntent.EXPLORE
    human_abstraction_level: HumanAbstractionLevel
    cognitive_maturity: CognitiveMaturity
    human_mode: HumanConversationMode
    primary_move: ConversationalMove
    next_conversational_granularity: str = Field(min_length=1)
    question_allowed: bool = False
    max_questions: int = Field(default=0, ge=0, le=1)
    question_guidance: str | None = None
    candidate_first: bool = False
    answer_first: bool = False
    demonstrate_understanding_without_restating: bool = True

    @model_validator(mode="after")
    def question_contract_is_consistent(self) -> "InteractionStrategy":
        if self.question_allowed != (self.max_questions == 1):
            raise ValueError("question allowance and maximum must agree")
        if not self.question_allowed and self.question_guidance is not None:
            raise ValueError("question guidance requires an allowed question")
        return self


class ConversationContextMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    actor: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1)


class ConversationContext(BaseModel):
    """Minimum turn-scoped context, assembled from persisted source Reality."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    latest_human_message: str = Field(min_length=1)
    recent_relevant_messages: tuple[ConversationContextMessage, ...] = ()
    known_relevant_facts: tuple[str, ...] = ()
    governed_work_facts: tuple[str, ...] = ()
    governing_constraints: tuple[str, ...] = ()
    candidate_constraints: tuple[str, ...] = ()
    current_requests: tuple[str, ...] = ()
    governed_work_requests: tuple[str, ...] = ()
    governed_engineering_semantic_facts: tuple[EngineeringSemanticFact, ...] = ()
    candidate_engineering_semantic_facts: tuple[
        EngineeringSemanticFactCandidate, ...
    ] = ()
    current_objective: str | None = None
    current_collaboration_focus: str | None = None
    current_work_reference: str | None = None
    current_plan_reference: str | None = None
    current_attention: str | None = None
    relevant_reality_references: tuple[str, ...] = ()
    response_language: str = Field(min_length=1, max_length=32)
    detailed_explanation_requested: bool = False
    interaction_strategy: InteractionStrategy | None = None


class CollaborationAlternative(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    option: str = Field(min_length=1)
    trade_off: str = Field(min_length=1)


class StructuredCollaborationResult(BaseModel):
    """Advisory semantic handoff from a Watt domain capability to conversation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    turn_intent: ConversationTurnIntent
    direct_answer: str | None = None
    known_relevant_facts: tuple[str, ...] = ()
    current_objective: str | None = None
    current_collaboration_focus: str | None = None
    design_intent_frame: DesignIntentFrame | None = None
    recommended_next_action: str | None = None
    concise_basis: str | None = None
    unresolved_human_decision: str | None = None
    alternatives: tuple[CollaborationAlternative, ...] = ()
    attention_level: ConversationAttentionLevel = ConversationAttentionLevel.NORMAL
    progression_guidance_appropriate: bool = True
    detailed_explanation_requested: bool = False
    response_language: str = Field(min_length=1, max_length=32)
    policy_hints: tuple[ConversationPolicyHint, ...] = ()

    @model_validator(mode="after")
    def direct_questions_have_an_answer(self) -> "StructuredCollaborationResult":
        if self.turn_intent in {
            ConversationTurnIntent.DIRECT_QUESTION,
            ConversationTurnIntent.HOW_TO,
        } and not (
            self.direct_answer and self.direct_answer.strip()
        ):
            raise ValueError(
                f"{self.turn_intent.value} requires direct_answer content"
            )
        if self.turn_intent is ConversationTurnIntent.REQUEST_DETAIL and not (
            self.detailed_explanation_requested
        ):
            raise ValueError("REQUEST_DETAIL requires detailed explanation mode")
        return self


class ConversationResponseCandidate(BaseModel):
    """Human-facing wording; advisory text and provenance, never domain truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str = Field(min_length=1)
    provider_identity: str = Field(min_length=1, max_length=255)
    model_identity: str | None = Field(default=None, max_length=255)


class ConversationContextProvider(Protocol):
    """Future ECF implementations may replace this provider, not its contract."""

    def assemble(
        self,
        basis: Any,
        collaboration: StructuredCollaborationResult,
    ) -> ConversationContext: ...


class ConversationProvider(Protocol):
    """Dedicated natural-language realization boundary."""

    def respond(
        self,
        context: ConversationContext,
        collaboration: StructuredCollaborationResult,
    ) -> ConversationResponseCandidate: ...

    def respond_stream(
        self,
        context: ConversationContext,
        collaboration: StructuredCollaborationResult,
        *,
        on_response_delta: Callable[[str], None],
    ) -> ConversationResponseCandidate: ...
