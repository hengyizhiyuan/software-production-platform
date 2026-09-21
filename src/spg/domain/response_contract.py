"""Turn-scoped expression obligations, never Work truth or production authority."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


RESPONSE_CONTRACT_REVISION = "wic-response-contract-v1"


class InteractionMode(StrEnum):
    EXPLORE = "EXPLORE"
    ANALYZE = "ANALYZE"
    DESIGN = "DESIGN"
    DECIDE = "DECIDE"
    ANSWER = "ANSWER"
    DIAGNOSE = "DIAGNOSE"
    EXECUTE = "EXECUTE"
    CORRECT = "CORRECT"
    STATUS = "STATUS"


class PrimaryObligation(StrEnum):
    EXPLAIN = "EXPLAIN"
    DIAGNOSE = "DIAGNOSE"
    ANSWER = "ANSWER"
    RECOMMEND = "RECOMMEND"
    COMPARE = "COMPARE"
    ASSESS = "ASSESS"
    REPORT_REALITY = "REPORT_REALITY"
    PROPOSE = "PROPOSE"
    EXECUTE = "EXECUTE"
    CORRECT = "CORRECT"
    CLARIFY_BLOCKER = "CLARIFY_BLOCKER"


class OpeningMove(StrEnum):
    CAUSE_FIRST = "CAUSE_FIRST"
    JUDGMENT_FIRST = "JUDGMENT_FIRST"
    ANSWER_FIRST = "ANSWER_FIRST"
    REALITY_FIRST = "REALITY_FIRST"
    RECOMMENDATION_FIRST = "RECOMMENDATION_FIRST"
    CONTRIBUTION_FIRST = "CONTRIBUTION_FIRST"
    ACK_AND_EXECUTE = "ACK_AND_EXECUTE"
    ACKNOWLEDGE_CORRECTION = "ACKNOWLEDGE_CORRECTION"
    CLARIFICATION_FIRST = "CLARIFICATION_FIRST"


class ResponseMove(StrEnum):
    DIRECT_ANSWER = "DIRECT_ANSWER"
    CONCLUSION = "CONCLUSION"
    POSSIBILITIES = "POSSIBILITIES"
    USEFUL_DISTINCTIONS = "USEFUL_DISTINCTIONS"
    REASONING = "REASONING"
    TRADEOFF = "TRADEOFF"
    COMPARISON = "COMPARISON"
    DECISIVE_FACTORS = "DECISIVE_FACTORS"
    RECOMMENDATION = "RECOMMENDATION"
    CURRENT_REALITY = "CURRENT_REALITY"
    GAP = "GAP"
    NEXT_STEP = "NEXT_STEP"
    CAUSE = "CAUSE"
    EVIDENCE = "EVIDENCE"
    FIX = "FIX"
    VERIFY = "VERIFY"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    PROCEED = "PROCEED"
    CORRECT_UNDERSTANDING = "CORRECT_UNDERSTANDING"
    ASSESS_OBJECTION = "ASSESS_OBJECTION"
    CLARIFY_BLOCKER = "CLARIFY_BLOCKER"
    OPTIONAL_ADJACENT_INSIGHT = "OPTIONAL_ADJACENT_INSIGHT"
    ACKNOWLEDGE_FAILED_STRATEGY = "ACKNOWLEDGE_FAILED_STRATEGY"
    CHALLENGE_ASSUMPTIONS = "CHALLENGE_ASSUMPTIONS"
    INDEPENDENT_EVIDENCE = "INDEPENDENT_EVIDENCE"
    CHANGE_DIAGNOSTIC_ROUTE = "CHANGE_DIAGNOSTIC_ROUTE"
    STOP_UNPRODUCTIVE_ROUTE = "STOP_UNPRODUCTIVE_ROUTE"


class InformationBudget(StrEnum):
    RELEVANT_DIVERGENCE = "RELEVANT_DIVERGENCE"
    REASONED_TRADEOFFS = "REASONED_TRADEOFFS"
    DECISIVE_FACTORS = "DECISIVE_FACTORS"
    MINIMUM_SUFFICIENT = "MINIMUM_SUFFICIENT"
    FOCUSED_DIAGNOSIS = "FOCUSED_DIAGNOSIS"
    MINIMAL_ACKNOWLEDGEMENT = "MINIMAL_ACKNOWLEDGEMENT"
    CORRECTION_AND_CONTINUE = "CORRECTION_AND_CONTINUE"
    CONCISE_REALITY = "CONCISE_REALITY"


class JudgmentStance(StrEnum):
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    RECOMMENDATION = "RECOMMENDATION"
    WORKING_ASSUMPTION = "WORKING_ASSUMPTION"
    PREFERENCE = "PREFERENCE"
    UNCERTAINTY = "UNCERTAINTY"


class AdvancementObligation(StrEnum):
    ANSWER_ONLY = "ANSWER_ONLY"
    ANSWER_AND_PROCEED = "ANSWER_AND_PROCEED"
    PROPOSE_AND_WAIT = "PROPOSE_AND_WAIT"
    ASK_ONE_BLOCKING_QUESTION = "ASK_ONE_BLOCKING_QUESTION"
    CONTINUE_PRODUCTION = "CONTINUE_PRODUCTION"
    ACK_AND_EXECUTE = "ACK_AND_EXECUTE"
    PAUSE_FOR_HUMAN_AUTHORITY = "PAUSE_FOR_HUMAN_AUTHORITY"
    REPLAN_REQUEST = "REPLAN_REQUEST"


class ResponseIntent(BaseModel):
    """Provider interpretation of the desired collaboration, subject to admission.

    Basis entries cite existing facts, deltas or Reality references. A provider's
    claim that its basis changed is not, by itself, evidence of a change.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    interaction_mode: InteractionMode
    rationale: str = Field(min_length=1)
    judgment_stance: JudgmentStance = JudgmentStance.UNCERTAINTY
    judgment_subject: str | None = Field(default=None, min_length=1, max_length=255)
    judgment_proposition: str | None = Field(default=None, min_length=1)
    judgment_basis: tuple[str, ...] = ()
    judgment_basis_changed: bool = False
    judgment_change_reason: str | None = Field(default=None, min_length=1)
    repeated_failure_signature: str | None = Field(default=None, min_length=1, max_length=255)
    prior_strategy_failed: bool = False
    executable_context: bool = False


class ResponseContract(BaseModel):
    """Immutable advisory contract for one turn's natural-language realization.

    Persisting this object records a response decision, not a semantic fact,
    authorization, lifecycle transition or assurance judgment.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    revision: str = RESPONSE_CONTRACT_REVISION
    authority: Literal["ADVISORY_ONLY"] = "ADVISORY_ONLY"
    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_record_ids: tuple[UUID, ...] = ()
    interaction_mode: InteractionMode
    primary_obligation: PrimaryObligation
    opening_move: OpeningMove
    response_moves: tuple[ResponseMove, ...] = Field(min_length=1)
    information_budget: InformationBudget
    question_budget: int = Field(default=0, ge=0, le=1)
    selected_question: str | None = Field(default=None, min_length=1)
    judgment_stance: JudgmentStance = JudgmentStance.UNCERTAINTY
    judgment_subject: str | None = Field(default=None, min_length=1, max_length=255)
    judgment_proposition: str | None = Field(default=None, min_length=1)
    judgment_basis: tuple[str, ...] = ()
    judgment_change_accepted: bool = False
    material_grounding_snapshot: tuple[str, ...] = ()
    advancement_obligation: AdvancementObligation
    adjacent_insight_budget: int = Field(default=0, ge=0, le=1)
    repeated_failure_signature: str | None = Field(default=None, min_length=1, max_length=255)
    prior_strategy_failed: bool = False
    strategy_revision: int = Field(default=0, ge=0)
    decision_basis: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def coherent_response_boundary(self) -> "ResponseContract":
        if (self.selected_question is not None) != (self.question_budget == 1):
            raise ValueError("One admitted blocking question is required for a question budget")
        if self.judgment_stance is JudgmentStance.FACT and (
            self.judgment_proposition is None or not self.judgment_basis
        ):
            raise ValueError("A factual judgment requires a proposition and cited basis")
        if self.interaction_mode in {InteractionMode.EXPLORE, InteractionMode.STATUS, InteractionMode.ANSWER} and self.advancement_obligation in {
            AdvancementObligation.ACK_AND_EXECUTE,
            AdvancementObligation.CONTINUE_PRODUCTION,
        }:
            raise ValueError("Exploration, answer and status contracts cannot request execution")
        if self.adjacent_insight_budget and (
            ResponseMove.OPTIONAL_ADJACENT_INSIGHT not in self.response_moves
            or self.response_moves[0] is ResponseMove.OPTIONAL_ADJACENT_INSIGHT
        ):
            raise ValueError("Adjacent insight is optional and follows the primary obligation")
        if self.interaction_mode is InteractionMode.EXECUTE and self.information_budget is not InformationBudget.MINIMAL_ACKNOWLEDGEMENT:
            raise ValueError("Executable collaboration has minimal conversational overhead")
        if self.advancement_obligation is AdvancementObligation.PAUSE_FOR_HUMAN_AUTHORITY and ResponseMove.PROCEED in self.response_moves:
            raise ValueError("An authority pause cannot also instruct the Realizer to proceed")
        if self.advancement_obligation is AdvancementObligation.ASK_ONE_BLOCKING_QUESTION and self.question_budget != 1:
            raise ValueError("A blocking-question advancement needs an admitted question")
        return self
