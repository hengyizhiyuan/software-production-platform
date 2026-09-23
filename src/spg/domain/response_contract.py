"""Turn-scoped expression obligations, never Work truth or production authority."""

from __future__ import annotations

from enum import StrEnum
import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from spg.domain.conversation import ConversationTurnIntent


RESPONSE_CONTRACT_REVISION = "wic-response-contract-v4"


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


class ExploreInteractionStrategy(StrEnum):
    """Turn-local EXPLORE posture; never a separate capability or lifecycle."""

    OPEN_EXPLORATION = "OPEN_EXPLORATION"
    INTENT_REFINEMENT = "INTENT_REFINEMENT"


class CapabilityAlignmentMode(StrEnum):
    KNOWLEDGE = "KNOWLEDGE"
    PRODUCTION_ADVISORY = "PRODUCTION_ADVISORY"
    PRODUCTION_REQUEST = "PRODUCTION_REQUEST"
    # Historical contracts used PRODUCTION. Keep it readable while new
    # decisions use the more precise request/admission vocabulary.
    PRODUCTION = "PRODUCTION"


class ProductionRelevance(StrEnum):
    GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"
    POTENTIAL_PRODUCTION_GOAL = "POTENTIAL_PRODUCTION_GOAL"
    DIRECT_PRODUCTION_GOAL = "DIRECT_PRODUCTION_GOAL"


class CapabilityAlignmentContext(BaseModel):
    """Turn-scoped capability match; advisory only and never production authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_intent: ConversationTurnIntent | None = None
    production_relevance: ProductionRelevance = ProductionRelevance.GENERAL_KNOWLEDGE
    current_work_context: bool = False
    watt_capability_match: bool = False
    response_mode: CapabilityAlignmentMode = CapabilityAlignmentMode.KNOWLEDGE
    explicit_capability_question: bool = False
    capability_reality_reference: str = "system-capability-reality:legacy"
    rationale: str = "Historical Response Contract has no capability-alignment evidence."
    authority: Literal["ADVISORY_ONLY"] = "ADVISORY_ONLY"

    @model_validator(mode="after")
    def coherent_alignment(self) -> "CapabilityAlignmentContext":
        expected = {
            CapabilityAlignmentMode.KNOWLEDGE: ProductionRelevance.GENERAL_KNOWLEDGE,
            CapabilityAlignmentMode.PRODUCTION_ADVISORY: (
                ProductionRelevance.POTENTIAL_PRODUCTION_GOAL
            ),
            CapabilityAlignmentMode.PRODUCTION_REQUEST: (
                ProductionRelevance.DIRECT_PRODUCTION_GOAL
            ),
            CapabilityAlignmentMode.PRODUCTION: ProductionRelevance.DIRECT_PRODUCTION_GOAL,
        }[self.response_mode]
        if self.production_relevance is not expected:
            raise ValueError("Capability alignment mode and production relevance disagree")
        if (
            self.response_mode is not CapabilityAlignmentMode.KNOWLEDGE
            and not self.watt_capability_match
        ):
            raise ValueError("Production alignment requires an evidenced Watt capability match")
        return self


class ProductionIntentEvidence(BaseModel):
    """Turn evidence used by Response Contract and governed admission projection.

    This does not grant Work authority. It makes an explicit Human production
    request stable across Provider classifications and records the repository
    source that the existing admission path may bind after Human authorization.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    production_request: bool = False
    repository_relevant: bool = False
    repository_source: str | None = None
    action_requested: bool = False
    advisory_question: bool = False
    evidence: tuple[str, ...] = ()


_HTTPS_REPOSITORY = re.compile(
    r"https://(?:github\.com|gitlab\.com|bitbucket\.org)/[^\s<>'\"，。]+",
    re.IGNORECASE,
)
_REPOSITORY_SIGNAL = re.compile(
    r"(?:github\s+(?:repo(?:sitory)?|project)|git\s+repo(?:sitory)?|"
    r"(?:my|this|the|our)\s+repo(?:sitory)?|code\s+archive|source\s+archive|"
    r"代码仓库|源码仓库|项目仓库|这个仓库|我的仓库|代码包|源码包)",
    re.IGNORECASE,
)
_PRODUCTION_ACTION = re.compile(
    r"(?:拉取|克隆|开发|修改|修复|新增|添加|实现|改造|接入|升级|重构|"
    r"\b(?:pull|clone|develop|modify|fix|add|implement|change|update|refactor)\b)",
    re.IGNORECASE,
)
_DIRECT_REQUEST = re.compile(
    r"(?:请|帮我|帮忙|需要你|给我|直接|"
    r"\b(?:please|help\s+me|can\s+you|could\s+you)\b)",
    re.IGNORECASE,
)
_ACTION_OPENING = re.compile(
    r"^\s*(?:请\s*)?(?:拉取|克隆|开发|修改|修复|新增|添加|实现|改造|接入|升级|重构|"
    r"(?:please\s+)?(?:pull|clone|develop|modify|fix|add|implement|change|update|refactor)\b)",
    re.IGNORECASE,
)
_ADVISORY_OPENING = re.compile(
    r"^\s*(?:如何|怎么|怎样|有什么办法|how\s+(?:do|can|should)\s+i\b)",
    re.IGNORECASE,
)
_REPOSITORY_RECOVERY_ACTION = re.compile(
    r"(?:重试|再试|继续(?:拉取|克隆|下载|获取)?|拉取|克隆|下载(?:代码|仓库)|获取(?:代码|仓库)|"
    r"\b(?:retry|continue|resume|pull|clone|download)\b)",
    re.IGNORECASE,
)


def repository_acquisition_recovery_requested(text: str) -> bool:
    """Recognize an action on an already-governed acquisition, not new intent."""

    return bool(_REPOSITORY_RECOVERY_ACTION.search(text.strip()))


def production_intent_evidence(text: str) -> ProductionIntentEvidence:
    """Extract bounded, source-backed production-routing evidence from one Turn."""

    value = text.strip()
    url_match = _HTTPS_REPOSITORY.search(value)
    repository_source = (
        None
        if url_match is None
        else url_match.group(0).rstrip(".,;:!?)]}，。；：！？")
    )
    repository_relevant = bool(repository_source or _REPOSITORY_SIGNAL.search(value))
    action_requested = bool(_PRODUCTION_ACTION.search(value))
    advisory_question = bool(_ADVISORY_OPENING.search(value))
    explicit_request = bool(
        _DIRECT_REQUEST.search(value) or _ACTION_OPENING.search(value)
    )
    production_request = bool(
        action_requested
        and (explicit_request or repository_relevant)
        and not advisory_question
    )
    evidence: list[str] = []
    if repository_source:
        evidence.append("HUMAN_SUPPLIED_REPOSITORY_URL")
    elif repository_relevant:
        evidence.append("HUMAN_REFERENCED_REPOSITORY")
    if action_requested:
        evidence.append("HUMAN_REQUESTED_SOFTWARE_CHANGE")
    if explicit_request:
        evidence.append("DIRECT_EXECUTION_LANGUAGE")
    if advisory_question:
        evidence.append("ADVISORY_QUESTION_FORM")
    return ProductionIntentEvidence(
        production_request=production_request,
        repository_relevant=repository_relevant,
        repository_source=repository_source,
        action_requested=action_requested,
        advisory_question=advisory_question,
        evidence=tuple(evidence),
    )


class DesignCollaborationMode(StrEnum):
    """Composable design posture; it refines rather than replaces InteractionMode."""

    DESIGN_EXPLORE = "DESIGN_EXPLORE"
    DESIGN_REVIEW = "DESIGN_REVIEW"
    DESIGN_DECIDE = "DESIGN_DECIDE"


class ReasoningStep(StrEnum):
    """Order of useful cognition to expose, never fixed prose or private chain of thought."""

    CONTEXT_MAP = "CONTEXT_MAP"
    OPTION_SPACE = "OPTION_SPACE"
    COMPARISON = "COMPARISON"
    RISKS_AND_CONSTRAINTS = "RISKS_AND_CONSTRAINTS"
    DECISION_POINT = "DECISION_POINT"
    GOAL = "GOAL"
    CONSTRAINTS = "CONSTRAINTS"
    ARCHITECTURE_OPTIONS = "ARCHITECTURE_OPTIONS"
    TRADE_OFFS = "TRADE_OFFS"
    RECOMMENDATION = "RECOMMENDATION"
    JUDGMENT = "JUDGMENT"
    DIRECT_ANSWER = "DIRECT_ANSWER"
    OBSERVED_SYMPTOM = "OBSERVED_SYMPTOM"
    EVIDENCE = "EVIDENCE"
    HYPOTHESIS = "HYPOTHESIS"
    ROOT_CAUSE = "ROOT_CAUSE"
    FIX = "FIX"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    PROCEED = "PROCEED"
    REPORT_RESULT = "REPORT_RESULT"
    CURRENT_CONCLUSION = "CURRENT_CONCLUSION"
    KEY_PROGRESS = "KEY_PROGRESS"
    CURRENT_OWNER_OR_NEXT_STEP = "CURRENT_OWNER_OR_NEXT_STEP"
    IMPORTANT_LIMITATION = "IMPORTANT_LIMITATION"
    CORRECTED_TRUTH = "CORRECTED_TRUTH"
    CONTINUE = "CONTINUE"
    CAPABILITY_ALIGNMENT = "CAPABILITY_ALIGNMENT"


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
    ALIGN_WITH_PRODUCTION_CAPABILITY = "ALIGN_WITH_PRODUCTION_CAPABILITY"


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
    design_collaboration_mode: DesignCollaborationMode | None = None
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
    capability_alignment: CapabilityAlignmentContext = CapabilityAlignmentContext()
    interaction_mode: InteractionMode
    explore_strategy: ExploreInteractionStrategy | None = None
    design_collaboration_mode: DesignCollaborationMode | None = None
    primary_obligation: PrimaryObligation
    opening_move: OpeningMove
    response_moves: tuple[ResponseMove, ...] = Field(min_length=1)
    reasoning_sequence: tuple[ReasoningStep, ...] = ()
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
        if self.revision == RESPONSE_CONTRACT_REVISION and not self.reasoning_sequence:
            raise ValueError("Current Response Contracts require a reasoning sequence")
        if self.revision == RESPONSE_CONTRACT_REVISION:
            if (
                self.interaction_mode is InteractionMode.EXPLORE
                and self.explore_strategy is None
            ):
                raise ValueError("Current EXPLORE contracts require an interaction strategy")
            if (
                self.interaction_mode is not InteractionMode.EXPLORE
                and self.explore_strategy is not None
            ):
                raise ValueError("EXPLORE strategy is only valid for EXPLORE mode")
            if (
                self.explore_strategy is ExploreInteractionStrategy.INTENT_REFINEMENT
                and (self.question_budget != 1 or self.selected_question is None)
            ):
                raise ValueError(
                    "Intent refinement requires exactly one admitted high-value question"
                )
            if (
                self.explore_strategy is ExploreInteractionStrategy.OPEN_EXPLORATION
                and self.question_budget != 0
            ):
                raise ValueError(
                    "Open exploration cannot carry an intent-refinement question"
                )
        if self.design_collaboration_mode is not None and self.interaction_mode not in {
            InteractionMode.EXPLORE,
            InteractionMode.ANALYZE,
            InteractionMode.DESIGN,
            InteractionMode.DECIDE,
        }:
            raise ValueError("Design collaboration refinement requires a design-capable mode")
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
        if (
            self.capability_alignment.response_mode
            is CapabilityAlignmentMode.PRODUCTION_ADVISORY
        ) != (ResponseMove.ALIGN_WITH_PRODUCTION_CAPABILITY in self.response_moves):
            raise ValueError(
                "Only production-advisory responses carry a capability-alignment move"
            )
        if (
            self.capability_alignment.response_mode
            is CapabilityAlignmentMode.PRODUCTION_ADVISORY
            and self.interaction_mode is not InteractionMode.ANSWER
        ):
            raise ValueError("Production advisory must answer before offering a production path")
        return self
