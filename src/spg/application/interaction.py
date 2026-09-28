"""Pre-Work Interaction application service and governed assessment admission."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
import hashlib
import json
import re
from threading import RLock
from time import monotonic, sleep
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.intent_realization import (
    IntentRealizationKernel, executable_semantic_actions, latest_assessment_revision,
    legacy_action_projection, production_evidence, project_interaction_candidate,
)
from spg.domain.intent_realization import EffectPredicate, GovernedSemanticIR, SemanticKind, SemanticOrigin, ObligationPlane, ObligationState, ObservedEffect, TERMINAL_OBLIGATION_STATES
from spg.infrastructure.persistence.intent_realization_store import IntentRealizationStore

from spg.application.guided_design import (
    design_schema_by_identity,
    match_design_schema_frame,
)
from spg.application.design_intent import frame_design_intent_text
from spg.application.engineering_semantics import bind_engineering_semantic_facts
from spg.application.repository_branch_authority import (
    BRANCH_EXTRACTION_SUBJECTS,
    exact_branch_creation_command,
    explicit_human_branch_command,
)
from spg.application.response_contract import build_response_contract
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.domain.response_contract import (
    InteractionMode,
    JudgmentStance,
    ResponseIntent,
    production_intent_evidence,
    repository_acquisition_recovery_requested,
)

from spg.domain.conversation import ConversationContextMessage, ConversationTurnIntent
from spg.domain.engineering_semantics import (
    EngineeringSemanticFact,
    EngineeringSemanticFactCandidate,
    SemanticEpistemicStatus,
    SemanticFactAuthority,
    SemanticRelation,
    SemanticRoleOrigin,
    current_semantic_facts,
)
from spg.domain.interaction import (
    ActiveWorkInterpretationContext,
    Interaction,
    InteractionActor,
    InteractionAssessment,
    InteractionAssessmentCandidate,
    InteractionCondition,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InteractionRecord,
    InteractionRecordNotFound,
    InteractionTurn,
    InteractionTurnStatus,
    ProductionAdmissionExecutionState,
    RepositoryAcquisitionState,
    StructuredResponseSchemaViolation,
    InterpretationMeaningKind,
    SharedUnderstanding,
    WorkEvolutionCandidateChange,
    WorkFocusClassification,
    WorkImpactDisposition,
    WorkRevisionAdmissionStatus,
    WorkSatisfactionState,
    WorkTransitionChoice,
    WorkAdmissionReadiness,
    WorkAdmissionReadinessStatus,
    WorkInteractionCapability,
)
from spg.domain.design_intent import DesignObjectType
from spg.application.wic_reception import (
    ShadowFastReceptionRuntime,
    neutral_fast_provisional_message,
)
from spg.application.wic_intelligence import build_progressive_semantics
from spg.application.external_research import (
    GovernedExternalResearch, potential_external_research,
)
from spg.domain.wic_intelligence import GovernanceCandidateKind
from spg.application.wic_response import (
    DeterministicGovernedResponseRealizer,
    GovernedDeltaGate,
    corrected_continuation,
    governed_response_envelope,
    policy_governed_response,
    reconcile_fast_and_deep,
    reconcile_contract_response,
    reconcile_provisional_intent,
)
from spg.domain.product import (
    ProductionCycleBindingCondition,
    WorkCondition,
    WorkMode,
)
from spg.domain.wic_reception import FastReceptionVisibility
from spg.domain.wic_response import (
    FastSuppressionReason,
    GovernedResponseRealization,
    GovernedResponseRealizer,
    ResponseReconciliation,
    ResponseTrustStage,
    WicResponseEvent,
    WicResponseEventType,
    WicRuntimeMode,
)
from spg.domain.steering import (
    RealityReferenceKind,
    SteeringAttentionReason,
    SteeringOutcome,
    SteeringStepType,
)
from spg.infrastructure.model_runtime import ModelFailureKind, ModelProviderError
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.interaction_store import InteractionStore
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.steering_store import SteeringStore


ASSESSMENT_SCHEMA_VERSION = "wic-assessment-v8"
READINESS_PROFILE = "LONG_LIVED_STEERING"
READINESS_PROFILE_VERSION = "v0"


def _grounded_status_facts(item, observations):
    """Render typed owner facts only while their cited observation is current.

    The returned identities are the coverage receipt. Generated answer prose is
    never compared with an earlier model sentence to decide completion.
    """
    if not item.observed_facts:
        return None
    by_reference = {reference: observation for observation in observations
        for reference in observation.evidence_references}
    facts = []
    identities = []
    for key, claim in item.observed_facts.items():
        reference = claim.provenance.evidence_reference
        observation = by_reference.get(reference)
        if observation is None or str(observation.facts.get(key)) != claim.value:
            return None
        facts.append(f"{key}={claim.value}")
        identities.append(f"{reference}:{key}")
    return "已核对当前状态：" + "；".join(facts) + "。", tuple(identities)


def _grounded_named_branch_question(item, observation, source_record_id):
    """Answer a typed branch existence question from the current repository owner."""
    if (item.kind is not SemanticKind.QUESTION or not item.subject
            or not item.subject.startswith("branch:") or observation is None
            or observation.facts.get("condition") != "READY"
            or not isinstance(observation.facts.get("branches"), (list, tuple))):
        return None
    branch = item.subject.removeprefix("branch:")
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", branch)
            or not any(source.origin in {SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}
                and source.source_record_id == source_record_id
                and source.source_text is not None
                and re.search(rf"(?<![A-Za-z0-9._/-]){re.escape(branch)}(?![A-Za-z0-9._/-])",
                    source.source_text) for source in item.provenance)):
        return None
    branches = observation.facts["branches"]
    if not all(isinstance(value, str) for value in branches):
        return None
    answer = (f"已核对当前仓库：本地分支 {branch} "
        + ("存在。" if branch in branches else "不存在。"))
    return answer, tuple(f"{reference}:branches:{branch}"
        for reference in observation.evidence_references)


def _research_repository_source(assessment):
    """Select one confirmed, Human-owned repository fact for project research."""
    from urllib.parse import urlsplit
    def supported_url(value):
        try:
            parsed = urlsplit(value)
            return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
        except ValueError:
            return False
    direct = assessment.semantic_ir.repository_source
    if direct is not None:
        return direct
    def repository_reference_subject(subject):
        parts = set(re.split(r"[._]", subject.lower()))
        return (bool(parts & {"repository", "repo"})
            and bool(parts & {"url", "source", "reference"}))
    sources = {fact.value for fact in assessment.engineering_semantic_facts
        if fact.is_current and repository_reference_subject(fact.subject)
        and fact.relation is SemanticRelation.REFERENCE
        and fact.authority is SemanticFactAuthority.HUMAN_EXPLICIT
        and fact.epistemic_status is SemanticEpistemicStatus.CONFIRMED
        and fact.provenance.role_origin is SemanticRoleOrigin.EXPLICIT
        and isinstance(fact.value, str)
        and fact.value in fact.provenance.source_text
        and supported_url(fact.value)}
    for item in getattr(assessment.semantic_ir, "items", ()):
        if item.kind is not SemanticKind.FACT or not item.subject:
            continue
        if "repository" not in set(re.split(r"[._]", item.subject.lower())):
            continue
        for provenance in item.provenance:
            if (provenance.origin is not SemanticOrigin.HUMAN_EXPLICIT
                    or not provenance.source_text):
                continue
            for value in re.findall(r"https?://[^\s，。]+", provenance.source_text):
                value = value.rstrip(".,;:!?)]}、")
                if supported_url(value):
                    sources.add(value)
    return next(iter(sources)) if len(sources) == 1 else None


def _repository_branch_status_question(content: str) -> bool:
    return bool(
        re.search(r"(?:分支|branch)", content, re.IGNORECASE)
        and re.search(
            r"(?:切好|当前|目前|现在|什么|哪个|已经|状态|好了|yet|current)",
            content,
            re.IGNORECASE,
        )
    )


def _repository_branch_status_answer(
    content: str, reality: SharedUnderstanding
) -> str | None:
    """Answer an exact branch-state query from current admitted Work Reality."""

    observation = getattr(reality, 'repository_observation', None)
    if reality.governed_revision is None and observation is not None:
        if observation.get('condition') != 'READY' or not observation.get('repository_ref'):
            return f"仓库操作状态为 {observation.get('condition')}；尚不能确认本地分支。"
        return (f"当前本地分支是 {observation['repository_ref'].removeprefix('refs/heads/')}，"
            f"提交 {observation['revision']}。生产 Work 尚未准入；没有推送远端。")
    revision = reality.governed_revision
    if revision is None or revision.repository_ref is None:
        return "当前 Work 尚未绑定可确认的仓库分支；不能说分支已经切好。"
    branch = revision.repository_ref.removeprefix("refs/heads/")
    commit = revision.source_revision or "未知"
    state = reality.repository_acquisition_state
    if state in {RepositoryAcquisitionState.REQUESTED, RepositoryAcquisitionState.RUNNING}:
        return (
            f"当前 Work 仍绑定本地分支 {branch}，提交 {commit}。"
            "新的分支操作已记录但尚未完成；完成后才会更新 Work 的分支。"
        )
    if state in {
        RepositoryAcquisitionState.FAILED_RETRYABLE,
        RepositoryAcquisitionState.FAILED_TERMINAL,
    }:
        return (
            f"当前 Work 仍绑定本地分支 {branch}，提交 {commit}。"
            "新的分支操作失败，尚未切换；请查看 Reality 面板中的失败原因。"
        )
    return (
        f"当前 Work 绑定的本地分支是 {branch}，提交 {commit}。"
        "这不表示该分支已经推送到远端。"
    )


_LONG_LIVED_OBJECT_TERMS = (
    "system",
    "platform",
    "application",
    " app",
    "product",
    "service",
    "portal",
    "website",
    "系统",
    "平台",
    "应用",
    "软件",
    "服务",
    "门户",
    "网站",
)
_NEW_OBJECT_PATTERNS = (
    re.compile(
        r"\b(?:i\s+(?:want|would like|need)\s+to|let(?:'s| us))\s+"
        r"(?:build|develop|create|make|launch|design)\s+(?:an|a|the)?\s*(?P<object>.+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:我想|我要|希望)(?:做|开发|创建|搭建|建设|设计)"
        r"(?:一个|一套|新的?)?(?P<object>.+)"
    ),
    re.compile(r"(?:再给我|再)(?:做|开发|创建|搭建|设计)(?:一个|一套)?(?P<object>.+)"),
)
_GENERIC_OBJECT_WORDS = {
    "a",
    "an",
    "the",
    "new",
    "system",
    "platform",
    "application",
    "app",
    "product",
    "service",
    "portal",
    "website",
}


def _declares_distinct_long_lived_object(
    latest_human_input: str,
    active: ActiveWorkInterpretationContext | None,
) -> bool:
    """Conservatively detect an explicitly declared, different Work-scale object."""

    if active is None:
        return False
    value = latest_human_input.strip()
    lowered = value.casefold()
    if not any(term in lowered for term in _LONG_LIVED_OBJECT_TERMS):
        return False
    declared = next(
        (
            match.group("object").strip(" .。!！?？")
            for pattern in _NEW_OBJECT_PATTERNS
            if (match := pattern.search(value)) is not None
        ),
        None,
    )
    if not declared:
        return False
    current = (
        f"{active.work_revision.motive} {active.work_revision.desired_outcome}"
    ).casefold()
    declared_words = tuple(
        word
        for word in re.findall(r"[a-z0-9]+", declared.casefold())
        if word not in _GENERIC_OBJECT_WORDS
    )
    if declared_words:
        return not any(word in current for word in declared_words)
    declared_core = re.sub(
        r"(?:一个|一套|新的?|系统|平台|应用|软件|服务|门户|网站)",
        "",
        declared,
    ).strip()
    return bool(declared_core) and declared_core.casefold() not in current


def _new_work_confirmation(latest_human_input: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", latest_human_input):
        return "这看起来是一个新的 Work。你想创建一个新的 Work 吗？当前 Work 不会被自动修改。"
    return (
        "This appears to be a new Work. Would you like to create a new Work? "
        "The current Work will not be changed automatically."
    )


def _nonmutating_question(value: str) -> bool:
    text = value.strip()
    question = text.endswith(("?", "？", "吗", "么", "呢"))
    change = re.search(r"(?:请|帮我|给我|把|将).*(?:改|调整|新增|删除|做成)|(?:改成|修改为|换成)", text)
    return question and change is None


def _work_history_question(value: str) -> bool:
    """Read persisted results without turning a historical question into intent."""
    text = value.strip().casefold()
    return bool(_nonmutating_question(text) and re.search(
        r"(?:上一次|上一轮|上个|之前|历史|last|previous).*"
        r"(?:改了什么|修改|变更|结果|做了什么|changed|change|result|did)", text,
    ))


def _work_reality_status_question(value: str) -> bool:
    """Narrow read-only operational question, not a new intent taxonomy."""

    text = value.strip().casefold()
    return _work_history_question(text) or bool(_nonmutating_question(text) and re.search(
        r"(?:目前|现在|当前|执行|进度|等待|状态|running|progress|status)"
        r".*(?:状态|进度|做到|执行|等待|卡住|哪里|哪了|了吗|什么|how|why|running|progress|status)"
        r"|(?:为什么|怎么|why|how).*(?:等待|执行|进度|卡住|卡在|queued|waiting|running|progress)", text,
    ))


def _is_candidate_or_delivery_lifecycle_turn(semantic_ir: GovernedSemanticIR) -> bool:
    """Keep lifecycle authority out of the long-lived Work objective."""
    def lifecycle_subject(subject: str | None) -> bool:
        # Subject is a compiler supplied structured key, never Human prose.
        return bool(subject and {"candidate", "delivery"}
            & set(re.split(r"[^a-z0-9]+", subject.lower())))

    return bool(
        any(item.kind is SemanticKind.OPERATIONAL_ACTION and item.action is not None
            and item.action.current for item in semantic_ir.items)
        and all(
            item.kind is SemanticKind.OPERATIONAL_ACTION
            or (item.kind is SemanticKind.CONSTRAINT
                and lifecycle_subject(item.subject))
            for item in semantic_ir.items
        )
    )


def _provider_supplied_human_wording(evidence: object) -> bool:
    """Semantic-only admission still needs the governed Conversation realizer."""

    if isinstance(evidence, dict):
        mode = evidence.get("pipeline_mode")
        conversation_request = evidence.get("conversation_request_id")
    else:
        mode = getattr(evidence, "pipeline_mode", None)
        conversation_request = getattr(evidence, "conversation_request_id", None)
    return mode == "coalesced_pre_work" or bool(conversation_request)


def interaction_basis_fingerprint(
    interaction: Interaction,
    records: tuple[InteractionRecord, ...],
    active_work_context: ActiveWorkInterpretationContext | None = None,
) -> str:
    payload = {
        "interaction_id": str(interaction.id),
        "current_work_id": (
            None if interaction.current_work_id is None else str(interaction.current_work_id)
        ),
        "records": [
            {
                "id": str(record.id),
                "sequence": record.sequence,
                "actor": record.actor.value,
                "source": record.source,
                "content_fingerprint": record.content_fingerprint,
                "work_focus_id": (
                    None if record.work_focus_id is None else str(record.work_focus_id)
                ),
                "supporting_references": list(record.supporting_references),
            }
            for record in records
        ],
        "active_work_context": (
            None
            if active_work_context is None
            else active_work_context.model_dump(mode="json")
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class DeterministicWorkInteractionCapability:
    """Conservative deterministic test capability; not the Watt product Provider."""

    _IDLE = {"hi", "hello", "hey", "你好", "在吗", "谢谢", "thanks"}
    _CONTINUATION_MARKERS = (
        "also",
        "slightly",
        "improve",
        "再",
        "也",
        "稍微",
        "继续",
    )

    def interpret(
        self, basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        human = [record for record in basis.records if record.actor is InteractionActor.HUMAN]
        latest = human[-1]
        active = basis.active_work_context
        if active is not None:
            value = latest.content.strip()
            normalized_latest = value.casefold()
            references = latest.supporting_references
            distinct_object = _declares_distinct_long_lived_object(value, active)
            if distinct_object or any(
                marker in normalized_latest
                for marker in ("另一个需求", "另外一个需求", "unrelated", "new work")
            ):
                focus = WorkFocusClassification.UNRELATED_NEW_DEMAND
                impact = WorkImpactDisposition.NEW_WORK_RECOMMENDED
            elif any(
                marker in normalized_latest
                for marker in ("探索", "设想", "未来是否", "maybe", "what if")
            ):
                focus = WorkFocusClassification.RELEVANT_EXPLORATION
                impact = WorkImpactDisposition.NO_GOVERNED_CHANGE
            elif _nonmutating_question(value) and not (
                active.satisfaction_state
                is WorkSatisfactionState.CURRENTLY_SATISFIED
                and any(
                    marker in normalized_latest
                    for marker in self._CONTINUATION_MARKERS
                )
            ):
                focus = WorkFocusClassification.SIDE_QUESTION
                impact = WorkImpactDisposition.NO_GOVERNED_CHANGE
            else:
                focus = WorkFocusClassification.ON_TOPIC
                impact = (
                    WorkImpactDisposition.CURRENT_RESULT_MAY_BE_INSUFFICIENT
                    if (
                        active.active_production_binding_id is not None
                        or active.satisfaction_state
                        is WorkSatisfactionState.CURRENTLY_SATISFIED
                    )
                    else WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED
                )
            revision = active.work_revision
            contextual = (
                revision.context_facts
                if impact is WorkImpactDisposition.NO_GOVERNED_CHANGE
                else (*revision.context_facts, value)
            )
            return InteractionAssessmentCandidate(
                interpreted_motive=revision.motive,
                desired_outcome=revision.desired_outcome,
                candidate_context=contextual,
                candidate_constraints=revision.constraints,
                current_requests=revision.requests,
                focus_classification=focus,
                impact_disposition=impact,
                supporting_references=references,
                natural_response=(
                    _new_work_confirmation(value)
                    if impact is WorkImpactDisposition.NEW_WORK_RECOMMENDED
                    else
                    "I kept the current Work focus and recorded this without changing governed Work."
                    if impact is WorkImpactDisposition.NO_GOVERNED_CHANGE
                    else "I assessed this against the current Work. Human governance is required before any Work revision."
                ),
                provider_identity="watt-native:deterministic-v1",
            )
        combined = "\n".join(record.content.strip() for record in human).strip()
        normalized = combined.lower().strip("。.!！?？ ")
        idle = normalized in self._IDLE or len(normalized) < 8
        constraints = tuple(
            fragment.strip(" 。.;；")
            for fragment in combined.replace("。", "\n").replace("；", "\n").splitlines()
            if any(marker in fragment.lower() for marker in ("不要", "不得", "必须", "do not", "must "))
        )
        if idle:
            return InteractionAssessmentCandidate(
                unresolved_material_questions=("What would you like Watt to help change?",),
                natural_response="Tell me what you would like to change or explore, and we can shape it together.",
                provider_identity="watt-native:deterministic-v0",
            )
        outcome_clear = len(combined) >= 28 and any(
            marker in combined.lower()
            for marker in ("希望", "需要", "改进", "实现", "want", "need", "improve", "build")
        )
        questions = () if outcome_clear else (
            "What observable outcome would show that this Motive has been satisfied?",
        )
        return InteractionAssessmentCandidate(
            interpreted_motive=combined,
            desired_outcome=combined if outcome_clear else None,
            candidate_constraints=constraints,
            current_requests=(latest.content.strip(),),
            unresolved_material_questions=questions,
            natural_response=(
                "I have enough to show a candidate Motive and outcome. Review the Shared Understanding before forming Work."
                if not questions
                else "I understand the direction, but need one material clarification before this is ready to form Work."
            ),
            provider_identity="watt-native:deterministic-v0",
        )


class UnavailableWorkInteractionCapability:
    """Fail truthfully when the sole MVP Watt Native Provider is not configured."""

    def interpret(
        self, _basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        raise InteractionInvariantViolation(
            "Watt Native interpretation Provider is not configured"
        )


_TURN_TIMING_MILESTONES = (
    "acknowledged", "processing_started", "reality_load_started",
    "reality_load_completed", "basis_prepared", "assessment_cache_hit",
    "provider_started", "provider_context_started", "provider_context_prepared",
    "context_assembly_started", "context_assembly_completed",
    "provider_starting", "provider_turn_started", "provider_request_queued",
    "provider_request_sent", "provider_response_accepted",
    "provider_first_response_event", "provider_first_token", "first_response_delta",
    "fast_path_started", "fast_candidate_ready", "fast_no_emission", "fast_failed",
    "first_sse_event", "natural_response_completed", "semantic_envelope_completed",
    "provider_teardown_completed", "payload_validation_started", "payload_validated",
    "semantic_result_completed", "semantic_payload_validated", "validation_completed", "provider_returned",
    "admission_started", "candidate_validated", "assessment_persisted",
    "final_persistence_started", "persistence_completed", "completed", "failed",
    "realization_started", "first_realizer_output_chunk", "first_realization_delta", "realization_completed",
    "response_stream_completed",
)


@dataclass(slots=True)
class _TurnTiming:
    """Bounded process-local diagnostics, never persisted collaboration truth."""

    received_at: datetime
    received_clock: float
    milestones: dict[str, tuple[datetime, float]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _TurnFailure:
    code: str
    message: str
    metadata: dict[str, object]


class _AssessmentBasisStale(InteractionInvariantViolation):
    """Owner Reality advanced while this Turn's interpretation was in flight."""


def _classify_turn_failure(error: Exception, failed_at: datetime) -> _TurnFailure:
    if isinstance(error, _AssessmentBasisStale):
        return _TurnFailure(
            code="ASSESSMENT_BASIS_STALE",
            message="Owner Reality advanced during interpretation. The saved Turn can be reassessed.",
            metadata={"failure_class": "ASSESSMENT_BASIS_STALE",
                "timestamp": failed_at.isoformat(), "retryable": True,
                "provisional_is_not_final": True},
        )
    if (
        isinstance(error, ModelProviderError)
        and error.kind is ModelFailureKind.INCOMPLETE_RESPONSE
    ):
        return _TurnFailure(
            code="INCOMPLETE_RESPONSE",
            message=(
                "The model response was incomplete. Your message was saved and this "
                "Turn can be retried."
            ),
            metadata={
                "failure_class": "INCOMPLETE_RESPONSE",
                "provider_status": error.provider_status,
                "termination_reason": error.termination_reason,
                "request_id": error.request_id,
                "timestamp": error.occurred_at.isoformat(),
                "retryable": error.retryable,
                "provisional_is_not_final": True,
            },
        )
    if isinstance(error, StructuredResponseSchemaViolation):
        return _TurnFailure(
            code="SCHEMA_VIOLATION",
            message=(
                "The model result did not satisfy Watt's governed response contract "
                "after bounded repair attempts. Your message was saved and this Turn "
                "can be retried."
            ),
            metadata={
                "failure_class": "SCHEMA_VIOLATION",
                "provider_status": "completed",
                "validation_issue": error.validation_issue,
                "request_id": error.request_id,
                "repair_attempted": error.repair_attempted,
                "refinement_observation": (
                    {
                        "semantic_version": 2,
                        "refinement_class": "SYSTEMIC_OR_NON_CONVERGING_INCIDENT",
                        "signal_kind": ("EXPLICIT_ACTION_LOST_BEFORE_EXECUTION"
                            if (error.validation_issue or '').startswith('ACTION_')
                            else "SCHEMA_INVALID"),
                        "component": "wic/semantic-provider",
                        "attempt_count": 1 + (error.repair_attempts or 1),
                        "converged": False,
                        "human_escalation": False,
                    } if error.repair_attempted else None
                ),
                "timestamp": failed_at.isoformat(),
                "retryable": True,
                "provisional_is_not_final": True,
            },
        )
    return _TurnFailure(
        code=type(error).__name__,
        message=str(error),
        metadata={
            "failure_class": type(error).__name__,
            "timestamp": failed_at.isoformat(),
            "retryable": False,
            "provisional_is_not_final": True,
        },
    )


def _pipeline_refinement_observation(evidence: object) -> dict[str, object] | None:
    if evidence is None:
        return None
    def count(name: str) -> int:
        value = evidence.get(name) if isinstance(evidence, dict) else getattr(evidence, name, None)
        return int(value or 0)

    repairs = count("semantic_structured_repair_count") + count(
        "coalesced_structured_repair_count"
    )
    if not repairs:
        return None
    return {
        "semantic_version": 2,
        "refinement_class": "ROUTINE_STOCHASTIC_REFINEMENT",
        "signal_kind": ((evidence.get("semantic_action_repair_signal")
            if isinstance(evidence, dict) else getattr(evidence, "semantic_action_repair_signal", None))
            or "SCHEMA_INVALID"),
        "component": "wic/semantic-provider",
        "attempt_count": repairs + 1,
        "converged": True,
        "human_escalation": False,
    }


class WorkInteractionService:
    def __init__(
        self,
        database: Database,
        *,
        capability: WorkInteractionCapability,
        fast_reception: ShadowFastReceptionRuntime | None = None,
        runtime_mode: WicRuntimeMode = WicRuntimeMode.LEGACY_WIC,
        response_realizer: GovernedResponseRealizer | None = None,
        external_research: GovernedExternalResearch | None = None,
    ) -> None:
        self.database = database
        self.capability = capability
        self.fast_reception = fast_reception
        self.runtime_mode = runtime_mode
        self.response_realizer = (
            response_realizer
            or getattr(capability, "governed_response_realizer", None)
            or DeterministicGovernedResponseRealizer()
        )
        self.external_research = external_research
        self._intent_observation_providers = []
        self._operational_owner_handlers = {}
        self._repository_action_handler = None
        self._repository_observation_provider = None
        self._turn_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="watt-interaction",
        )
        self._turn_futures: dict[UUID, Future[None]] = {}
        self._turn_response_streams: OrderedDict[UUID, str] = OrderedDict()
        self._turn_timings: OrderedDict[UUID, _TurnTiming] = OrderedDict()
        self._turn_fast_candidates: OrderedDict[UUID, object] = OrderedDict()
        self._turn_realization_started: set[UUID] = set()
        self._production_admission_handler: Callable[
            [UUID, InteractionAssessment, InteractionRecord], None
        ] | None = None
        self._governed_work_handler = None
        self._governed_branch_handler: Callable[
            [UUID, InteractionAssessment, InteractionRecord], str | None
        ] | None = None
        self._production_admission_prepare_handler: Callable[
            [UUID, InteractionAssessment, InteractionRecord], None
        ] | None = None
        self._production_admission_reality_provider: Callable[
            [UUID, UUID | None],
            tuple[
                ProductionAdmissionExecutionState,
                RepositoryAcquisitionState,
                str,
                str | None,
            ]
            | None,
        ] | None = None
        self._work_execution_reality_provider: Callable[
            [UUID], tuple[str | None, str | None]
        ] | None = None
        self._production_admission_progress: OrderedDict[
            UUID,
            tuple[
                ProductionAdmissionExecutionState,
                RepositoryAcquisitionState | None,
                str | None,
            ],
        ] = OrderedDict()
        self._turn_lock = RLock()

    def configure_production_admission(
        self,
        handler: Callable[
            [UUID, InteractionAssessment, InteractionRecord], None
        ] | None,
        *,
        prepare_handler: Callable[
            [UUID, InteractionAssessment, InteractionRecord], None
        ] | None = None,
        reality_provider: Callable[
            [UUID, UUID | None],
            tuple[
                ProductionAdmissionExecutionState,
                RepositoryAcquisitionState,
                str,
                str | None,
            ]
            | None,
        ] | None = None,
    ) -> None:
        """Attach the existing governed admission path to completed WIC Turns."""

        with self._turn_lock:
            self._production_admission_handler = handler
            self._production_admission_prepare_handler = prepare_handler
            self._production_admission_reality_provider = reality_provider

    def configure_work_execution_reality(
        self,
        provider: Callable[[UUID], tuple[str | None, str | None]] | None,
    ) -> None:
        """Attach a read-only persisted-operation projection for response truth."""

        with self._turn_lock:
            self._work_execution_reality_provider = provider

    def configure_governed_branch_handler(
        self,
        handler: Callable[
            [UUID, InteractionAssessment, InteractionRecord], str | None
        ] | None,
        *, work_handler=None,
    ) -> None:
        """Attach the bounded branch action authorized by the current Human Turn."""

        with self._turn_lock:
            self._governed_branch_handler = handler
            self._governed_work_handler = work_handler

    def configure_intent_observations(self, provider):
        self._intent_observation_providers.append(provider)

    def configure_operational_owner(self, operation, handler):
        """An existing owner receives governed semantics, never raw Human prose."""
        from spg.application.intent_realization import canonical_operation
        self._operational_owner_handlers[canonical_operation(operation)] = handler

    def configure_repository_actions(self, handler, observation_provider) -> None:
        """Repository Asset retains independent Interaction action ownership."""
        self._repository_action_handler = handler
        self._repository_observation_provider = observation_provider

    def record_production_admission_progress(
        self,
        interaction_id: UUID,
        *,
        admission_state: ProductionAdmissionExecutionState,
        repository_state: RepositoryAcquisitionState | None = None,
        next_step: str | None = None,
    ) -> None:
        """Expose bounded in-flight admission truth between durable transitions."""

        with self._turn_lock:
            self._production_admission_progress[interaction_id] = (
                admission_state,
                repository_state,
                next_step,
            )
            while len(self._production_admission_progress) > 128:
                self._production_admission_progress.popitem(last=False)

    def clear_production_admission_progress(self, interaction_id: UUID) -> None:
        with self._turn_lock:
            self._production_admission_progress.pop(interaction_id, None)

    def _prepare_production_admission_if_ready(
        self,
        interaction_id: UUID,
        assessment: InteractionAssessment,
        request_record: InteractionRecord,
    ) -> bool:
        evidence = production_evidence(assessment.semantic_ir)
        projection = self.get_shared_understanding(interaction_id)
        recovery = bool(
            projection.governed_work_id is not None
            and any(item.action.operation == "ACQUIRE_REPOSITORY"
                for item in executable_semantic_actions(assessment.semantic_ir))
        )
        with self._turn_lock:
            admission_handler = (
                self._production_admission_prepare_handler
                or self._production_admission_handler
            )
        if (
            admission_handler is None
            or (
                not recovery
                and (
                    not evidence.production_request
                    or not evidence.repository_relevant
                    or not evidence.action_requested
                    or assessment.readiness.status
                    is not WorkAdmissionReadinessStatus.READY
                )
            )
        ):
            return False
        self.record_production_admission_progress(
            interaction_id,
            admission_state=ProductionAdmissionExecutionState.ADMISSION_RUNNING,
            repository_state=(
                RepositoryAcquisitionState.NOT_STARTED
                if evidence.repository_source
                else None
                if recovery
                else RepositoryAcquisitionState.WAITING_FOR_REPOSITORY_SOURCE
            ),
            next_step=(
                "Acquire the Human-supplied repository baseline."
                if evidence.repository_source
                else "Bind the referenced repository source."
            ),
        )
        try:
            admission_handler(interaction_id, assessment, request_record)
        except Exception:
            # Conversation truth has already settled successfully. Keep
            # admission retryable and visible without rewriting that Turn into
            # a model/response failure. Startup reconciliation may retry it.
            self.record_production_admission_progress(
                interaction_id,
                admission_state=(
                    ProductionAdmissionExecutionState.ADMISSION_RETRY_REQUIRED
                ),
                repository_state=(
                    RepositoryAcquisitionState.FAILED_RETRYABLE
                    if evidence.repository_source
                    else RepositoryAcquisitionState.WAITING_FOR_REPOSITORY_SOURCE
                ),
                next_step=(
                    "Retry governed Work admission from the preserved request."
                ),
            )
        return True

    def _execute_prepared_production_admission(
        self,
        interaction_id: UUID,
        assessment: InteractionAssessment,
        request_record: InteractionRecord,
    ) -> bool:
        with self._turn_lock:
            handler = self._production_admission_handler
        if handler is None:
            return False
        try:
            handler(interaction_id, assessment, request_record)
        except Exception as error:
            projection = self.get_shared_understanding(interaction_id)
            admission = (
                ProductionAdmissionExecutionState.WORK_CREATED
                if projection.governed_work_id is not None
                else ProductionAdmissionExecutionState.ADMISSION_RETRY_REQUIRED
            )
            self.record_production_admission_progress(
                interaction_id,
                admission_state=admission,
                repository_state=RepositoryAcquisitionState.FAILED_RETRYABLE,
                next_step=(
                    "Repository acquisition completed but Work binding failed; retry "
                    f"the governed operation. ({type(error).__name__})"
                ),
            )
        return True

    def _trigger_production_admission_if_ready(
        self,
        interaction_id: UUID,
        assessment: InteractionAssessment,
        request_record: InteractionRecord,
    ) -> bool:
        prepared = self._prepare_production_admission_if_ready(
            interaction_id, assessment, request_record
        )
        if prepared:
            self._execute_prepared_production_admission(
                interaction_id, assessment, request_record
            )
        return prepared

    def resume_ready_production_admissions(self) -> tuple[UUID, ...]:
        """Reconcile completed explicit requests left before Work formation."""

        resumed: list[UUID] = []
        for projection in self.list_interactions():
            assessment = projection.latest_assessment
            request_record = next(
                (
                    record
                    for record in reversed(projection.records)
                    if record.actor is InteractionActor.HUMAN
                ),
                None,
            )
            if assessment is None or request_record is None:
                continue
            if projection.governed_work_id is None:
                if not projection.latest_assessment_current:
                    continue
                recovered = self._trigger_production_admission_if_ready(
                    projection.interaction.id,
                    assessment,
                    request_record,
                )
            else:
                with self._turn_lock:
                    provider = self._production_admission_reality_provider
                reality = (
                    None
                    if provider is None
                    else provider(
                        projection.interaction.id,
                        projection.governed_work_id,
                    )
                )
                # Resume persisted active/retryable acquisition lineage. The
                # acquisition owner checks network-only retry budgets; permanent
                # failures and completed attempts remain immutable. A Work does not require the latest
                # conversational assessment to remain current: the persisted
                # Attempt is the recovery authority and exact operation basis.
                recovered = bool(
                    reality is not None
                    and reality[1]
                    in {
                        RepositoryAcquisitionState.REQUESTED,
                        RepositoryAcquisitionState.RUNNING,
                        RepositoryAcquisitionState.FAILED_RETRYABLE,
                    }
                    and self._execute_prepared_production_admission(
                        projection.interaction.id,
                        assessment,
                        request_record,
                    )
                )
            if recovered:
                resumed.append(projection.interaction.id)
        return tuple(resumed)

    def schedule_ready_production_admission_recovery(self) -> None:
        """Reconcile admission gaps without blocking application startup."""

        self._turn_executor.submit(self.resume_ready_production_admissions)

    def create_interaction(
        self,
        *,
        human_identity: str,
        start_work_context: bool = False,
    ) -> Interaction:
        identity = human_identity.strip()
        if not identity:
            raise InteractionInvariantViolation("Human identity is required")
        now = datetime.now(UTC)
        interaction_id = uuid4()
        work_id = uuid4() if start_work_context else None
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            if work_id is not None:
                self._insert_pre_work(
                    ProductStore(uow.session),
                    work_id=work_id,
                    timestamp=now,
                )
            store.insert_interaction(
                {
                    "id": interaction_id,
                    "condition": InteractionCondition.OPEN.value,
                    "current_work_id": work_id,
                    "created_by": identity,
                    "updated_by": identity,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            uow.commit()
        return self.get_interaction(interaction_id)

    @staticmethod
    def _insert_pre_work(
        product: ProductStore,
        *,
        work_id: UUID,
        timestamp: datetime,
    ) -> None:
        product.insert_work(
            {
                "id": work_id,
                "goal_id": None,
                "work_mode": WorkMode.LONG_LIVED_STEERING.value,
                "raw_user_requirement": "",
                "refined_title": "New Work",
                "desired_outcome": None,
                "constraints": [],
                "tags": [],
                "condition": WorkCondition.PRE_WORK.value,
                "scope_summary": None,
                "production_objective": None,
                "expected_artifact_path": None,
                "artifact_operation": None,
                "artifact_placement_rationale": None,
                "artifact_target_confidence": None,
                "artifact_source_baseline_id": None,
                "artifact_source_revision": None,
                "verification_expectation": None,
                "code_change_proposal": None,
                "production_plan_proposal": None,
                "current_work_reality_revision_id": None,
                "current_engineering_scope_id": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )

    def list_interactions(self) -> tuple[SharedUnderstanding, ...]:
        with self.database.unit_of_work() as uow:
            interactions = InteractionStore(uow.session).list_interactions()
        return tuple(self.get_shared_understanding(item.id) for item in interactions)

    def get_interaction(self, interaction_id: UUID) -> Interaction:
        with self.database.unit_of_work() as uow:
            interaction = InteractionStore(uow.session).interaction(interaction_id)
        if interaction is None:
            raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
        return interaction

    def append_human_input(
        self,
        interaction_id: UUID,
        content: str,
        *,
        human_identity: str,
        supporting_references: tuple[str, ...] = (),
    ) -> InteractionRecord:
        value = content.strip()
        identity = human_identity.strip()
        if not value or not identity:
            raise InteractionInvariantViolation("Human input and identity are required")
        now = datetime.now(UTC)
        record_id = uuid4()
        content_fingerprint = hashlib.sha256(value.encode()).hexdigest()
        references = self._normalize_supporting_references(supporting_references)
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            interaction = store.interaction(interaction_id, for_update=True)
            if interaction is None:
                raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
            if interaction.condition is not InteractionCondition.OPEN:
                raise InteractionInvariantViolation("Archived Interaction cannot accept input")
            sequence = store.next_sequence(interaction_id)
            store.insert_record(
                {
                    "id": record_id,
                    "interaction_id": interaction_id,
                    "sequence": sequence,
                    "actor": InteractionActor.HUMAN.value,
                    "source": identity,
                    "content": value,
                    "content_fingerprint": content_fingerprint,
                    "work_focus_id": interaction.current_work_id,
                    "supporting_references": list(references),
                    "created_at": now,
                }
            )
            self._capture_pre_work_requirement(
                uow.session,
                work_id=interaction.current_work_id,
                content=value,
                timestamp=now,
            )
            store.touch_interaction(
                interaction_id,
                updated_by=identity,
                updated_at=now,
            )
            uow.commit()
        return self.get_shared_understanding(interaction_id).records[-1]

    def append_and_assess(
        self,
        interaction_id: UUID,
        content: str,
        *,
        human_identity: str,
        supporting_references: tuple[str, ...] = (),
    ) -> SharedUnderstanding:
        # The Human record commits first. A failed Provider call therefore leaves an
        # honest, recoverable unassessed basis rather than losing communication.
        request_record = self.append_human_input(
            interaction_id,
            content,
            human_identity=human_identity,
            supporting_references=supporting_references,
        )
        assessment = self.assess_current(interaction_id)
        self._trigger_production_admission_if_ready(
            interaction_id,
            assessment,
            request_record,
        )
        return self.get_shared_understanding(interaction_id)

    def submit_turn(
        self,
        interaction_id: UUID,
        content: str,
        *,
        human_identity: str,
        supporting_references: tuple[str, ...] = (),
    ) -> InteractionTurn:
        """Persist and acknowledge one Turn before Provider-backed processing."""

        received_clock = monotonic()
        received_at = datetime.now(UTC)
        value = content.strip()
        identity = human_identity.strip()
        if not value or not identity:
            raise InteractionInvariantViolation("Human input and identity are required")
        now = datetime.now(UTC)
        record_id = uuid4()
        turn_id = uuid4()
        references = self._normalize_supporting_references(supporting_references)
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            interaction = store.interaction(interaction_id, for_update=True)
            if interaction is None:
                raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
            if interaction.condition is not InteractionCondition.OPEN:
                raise InteractionInvariantViolation("Archived Interaction cannot accept input")
            if store.unfinished_turn(interaction_id) is not None:
                raise InteractionInvariantViolation(
                    "Interaction already has a Turn in progress"
                )
            store.insert_record(
                {
                    "id": record_id,
                    "interaction_id": interaction_id,
                    "sequence": store.next_sequence(interaction_id),
                    "actor": InteractionActor.HUMAN.value,
                    "source": identity,
                    "content": value,
                    "content_fingerprint": hashlib.sha256(value.encode()).hexdigest(),
                    "work_focus_id": interaction.current_work_id,
                    "supporting_references": list(references),
                    "created_at": now,
                }
            )
            store.insert_turn(
                {
                    "id": turn_id,
                    "interaction_id": interaction_id,
                    "request_record_id": record_id,
                    "assessment_id": None,
                    "wic_mode": self.runtime_mode.value,
                    "status": InteractionTurnStatus.RECEIVED.value,
                    "failure_code": None,
                    "failure_message": None,
                    "created_at": now,
                    "started_at": None,
                    "completed_at": None,
                    "updated_at": now,
                }
            )
            IntentRealizationStore(uow.session).create_envelope(
                turn_id=turn_id, source_record_id=record_id,
                human_content_hash=hashlib.sha256(value.encode()).hexdigest(),
                provenance_basis={"interaction_id": str(interaction_id),
                    "source_record_id": str(record_id),
                    "work_focus_id": None if interaction.current_work_id is None
                        else str(interaction.current_work_id),
                    "supporting_references": list(references)})
            store.insert_message(
                {
                    "id": uuid4(),
                    "interaction_id": interaction_id,
                    "turn_id": turn_id,
                    "sequence": store.next_message_sequence(interaction_id),
                    "actor": InteractionActor.HUMAN.value,
                    "content": value,
                    "processing_status": InteractionTurnStatus.RECEIVED.value,
                    "interaction_record_id": record_id,
                    "interpretation_assessment_id": None,
                    "design_result_references": [],
                    "governance_event_references": [],
                    "supporting_references": list(references),
                    "created_at": now,
                    "updated_at": now,
                }
            )
            self._capture_pre_work_requirement(
                uow.session,
                work_id=interaction.current_work_id,
                content=value,
                timestamp=now,
            )
            if self.runtime_mode is not WicRuntimeMode.LEGACY_WIC:
                store.insert_response_event(
                    {
                        "id": uuid4(), "interaction_id": interaction_id,
                        "turn_id": turn_id, "response_id": turn_id, "sequence": 1,
                        "event_type": WicResponseEventType.TURN_ACCEPTED.value,
                        "content": None, "basis_fingerprint": None,
                        "reconciliation": None,
                        "event_metadata": {"wic_mode": self.runtime_mode.value},
                        "created_at": now,
                    }
                )
            store.touch_interaction(interaction_id, updated_by=identity, updated_at=now)
            uow.commit()
        with self._turn_lock:
            self._turn_timings[turn_id] = _TurnTiming(received_at, received_clock)
            while len(self._turn_timings) > 128:
                self._turn_timings.popitem(last=False)
        turn = self.get_turn(turn_id)
        self._mark_turn_timing(turn_id, "acknowledged")
        self.schedule_turn(turn_id)
        return turn

    @staticmethod
    def _capture_pre_work_requirement(
        session,
        *,
        work_id: UUID | None,
        content: str,
        timestamp: datetime,
    ) -> None:
        if work_id is None:
            return
        product = ProductStore(session)
        work = product.work(work_id, for_update=True)
        if (
            work is None
            or work.condition is not WorkCondition.PRE_WORK
            or work.raw_user_requirement
        ):
            return
        compact = " ".join(content.split())
        title = compact if len(compact) <= 72 else compact[:69].rstrip() + "..."
        product.update_work(
            work_id,
            {
                "raw_user_requirement": content,
                "refined_title": title or "New Work",
                "updated_at": timestamp,
            },
        )

    def get_turn(self, turn_id: UUID) -> InteractionTurn:
        with self.database.unit_of_work() as uow:
            turn = InteractionStore(uow.session).turn(turn_id)
        if turn is None:
            raise InteractionRecordNotFound(f"Interaction Turn not found: {turn_id}")
        return turn

    def retry_turn(self, interaction_id: UUID, turn_id: UUID, *, automatic: bool = False) -> InteractionTurn:
        """Retry one preserved failed Human Turn without creating duplicate input."""

        now = datetime.now(UTC)
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            turn = store.turn(turn_id, for_update=True)
            if turn is None or turn.interaction_id != interaction_id:
                raise InteractionRecordNotFound(
                    f"Interaction Turn not found: {turn_id}"
                )
            if turn.status is not InteractionTurnStatus.FAILED:
                raise InteractionInvariantViolation(
                    "Only a failed Interaction Turn can be retried"
                )
            records = store.records(interaction_id)
            if not records or records[-1].id != turn.request_record_id:
                raise InteractionInvariantViolation(
                    "A failed Turn cannot be retried after newer Human input"
                )
            if store.message_for_turn(turn_id, InteractionActor.WATT) is not None:
                raise InteractionInvariantViolation(
                    "A Turn with a settled Watt response cannot be retried"
                )
            events = store.response_events(turn_id)
            recovery_attempt = 1 + sum(
                event.event_type is WicResponseEventType.TURN_RECOVERY_STARTED
                for event in events
            )
            if automatic and (turn.wic_mode is not WicRuntimeMode.WIC_VNEXT_CONTROLLED
                    or recovery_attempt > 2):
                raise InteractionInvariantViolation("Automatic Turn recovery budget is exhausted")
            previous_failure_code = turn.failure_code
            store.reset_turn_for_retry(turn_id, updated_at=now)
            store.update_turn_messages_status(
                turn_id,
                status=InteractionTurnStatus.RECEIVED,
                updated_at=now,
            )
            if turn.wic_mode is not WicRuntimeMode.LEGACY_WIC:
                store.insert_response_event(
                    {
                        "id": uuid4(),
                        "interaction_id": interaction_id,
                        "turn_id": turn_id,
                        "response_id": turn_id,
                        "sequence": store.next_response_event_sequence(turn_id),
                        "event_type": WicResponseEventType.TURN_RECOVERY_STARTED.value,
                        "content": None,
                        "basis_fingerprint": None,
                        "reconciliation": None,
                        "event_metadata": {
                            "attempt": recovery_attempt,
                            "previous_failure_class": previous_failure_code,
                            "human_input_reused": True,
                            "automatic": automatic,
                            "backoff_seconds": recovery_attempt if automatic else 0,
                            "attempt_budget": 3 if automatic else None,
                        },
                        "created_at": now,
                    }
                )
            uow.commit()
        self._schedule_preserved_turn(turn_id)
        return self.get_turn(turn_id)

    def _schedule_preserved_turn(self, turn_id: UUID) -> None:
        with self._turn_lock:
            self._turn_response_streams.pop(turn_id, None)
            self._turn_fast_candidates.pop(turn_id, None)
            self._turn_realization_started.discard(turn_id)
            self._turn_timings[turn_id] = _TurnTiming(datetime.now(UTC), monotonic())
        if not self.schedule_turn(turn_id):
            # The failed processor can still be unwinding after its durable FAILED
            # transition. Re-enter only after that exact attempt releases ownership.
            with self._turn_lock:
                current = self._turn_futures.get(turn_id)
                if current is not None and not current.done():
                    current.add_done_callback(
                        lambda _completed: self.schedule_turn(turn_id)
                    )
                else:
                    self.schedule_turn(turn_id)

    def schedule_turn(self, turn_id: UUID) -> bool:
        with self._turn_lock:
            current = self._turn_futures.get(turn_id)
            if current is not None and not current.done():
                return False
            future = self._turn_executor.submit(self._process_turn, turn_id)
            self._turn_futures[turn_id] = future
            future.add_done_callback(
                lambda completed: self._forget_turn(turn_id, completed)
            )
        return True

    def resume_pending_turns(self) -> tuple[UUID, ...]:
        with self.database.unit_of_work() as uow:
            pending = InteractionStore(uow.session).pending_turns()
        return tuple(turn.id for turn in pending if self.schedule_turn(turn.id))

    def shutdown(self) -> None:
        self._turn_executor.shutdown(wait=True, cancel_futures=False)
        close_capability = getattr(self.capability, "close", None)
        if callable(close_capability):
            close_capability()
        if self.fast_reception is not None:
            self.fast_reception.close()
        with self._turn_lock:
            self._turn_response_streams.clear()
            self._turn_timings.clear()
            self._turn_fast_candidates.clear()
            self._turn_realization_started.clear()
            self._production_admission_progress.clear()

    def turn_timing(self, turn_id: UUID) -> dict[str, object] | None:
        """Observe monotonic latency; absent/restarted observations remain unknown.

        Acknowledgement means the durable response is ready to return. The first
        SSE event is the server yield, not confirmed browser receipt. A response
        delta measures text delivery separately from that status acknowledgement.
        Provider phases distinguish text/envelope arrival from payload validation.
        Assessment and final-message persistence mark their separate committed
        transactions; cache reuse does not fabricate either earlier phase.
        """

        with self._turn_lock:
            timing = self._turn_timings.get(turn_id)
            if timing is None:
                return None
            result: dict[str, object] = {
                "request_received_at": timing.received_at.isoformat(),
                "request_received_ms": 0.0,
            }
            for event in _TURN_TIMING_MILESTONES:
                milestone = timing.milestones.get(event)
                result[f"{event}_at"] = (
                    None if milestone is None else milestone[0].isoformat()
                )
                result[f"{event}_ms"] = (
                    None if milestone is None
                    else round(1000 * (milestone[1] - timing.received_clock), 3)
                )
            with self.database.unit_of_work() as uow:
                response_events = InteractionStore(uow.session).response_events(
                    turn_id
                )
            deltas = [
                event
                for event in response_events
                if event.event_type is WicResponseEventType.RESPONSE_DELTA
            ]
            provisional = next(
                (
                    event
                    for event in response_events
                    if event.event_type is WicResponseEventType.PROVISIONAL_RESPONSE
                ),
                None,
            )
            final = next(
                (
                    event
                    for event in response_events
                    if event.event_type is WicResponseEventType.FINAL_RESPONSE
                ),
                None,
            )
            fast_suppressed = next(
                (
                    event
                    for event in response_events
                    if event.event_type is WicResponseEventType.FAST_SUPPRESSED
                ),
                None,
            )
            first_meaningful = provisional or (deltas[0] if deltas else None)
            intervals = [
                round(
                    1000
                    * (current.created_at - previous.created_at).total_seconds(),
                    3,
                )
                for previous, current in zip(deltas, deltas[1:])
            ]
            sorted_intervals = sorted(intervals)
            middle = len(sorted_intervals) // 2
            median_interval = (
                None
                if not sorted_intervals
                else sorted_intervals[middle]
                if len(sorted_intervals) % 2
                else round(
                    (sorted_intervals[middle - 1] + sorted_intervals[middle]) / 2,
                    3,
                )
            )
            elapsed = lambda event: (
                None
                if event is None
                else round(
                    1000 * (event.created_at - timing.received_at).total_seconds(),
                    3,
                )
            )
            realization_started = timing.milestones.get("realization_started")
            realization_elapsed = lambda event: (
                None
                if event is None or realization_started is None
                else round(
                    1000
                    * (event.created_at - realization_started[0]).total_seconds(),
                    3,
                )
            )
            contract_event = next((event for event in response_events
                                   if event.event_type is WicResponseEventType.RESPONSE_CONTRACT_READY), None)
            result.update(
                response_contract=None if contract_event is None else contract_event.metadata.get("response_contract"),
                ttfms_ms=elapsed(first_meaningful),
                ttfsr_ms=realization_elapsed(deltas[0] if deltas else None),
                ttcr_ms=elapsed(final),
                response_delta_count=len(deltas),
                first_response_delta_at=(
                    None if not deltas else deltas[0].created_at.isoformat()
                ),
                last_response_delta_at=(
                    None if not deltas else deltas[-1].created_at.isoformat()
                ),
                response_delta_intervals_ms=intervals,
                response_delta_average_interval_ms=(
                    None
                    if not intervals
                    else round(sum(intervals) / len(intervals), 3)
                ),
                response_delta_median_interval_ms=median_interval,
                fast_visible=provisional is not None,
                fast_suppression_reason=(
                    None
                    if fast_suppressed is None
                    else fast_suppressed.metadata.get("reason")
                ),
                semantic_provider_evidence=(
                    None
                    if final is None
                    else final.metadata.get("semantic_provider_evidence")
                ),
                realizer_provider=(
                    None if final is None else final.metadata.get("realizer_provider")
                ),
                realizer_model=(
                    None if final is None else final.metadata.get("realizer_model")
                ),
                realizer_timing=(
                    None if final is None else final.metadata.get("realizer_timing")
                ),
                interaction_strategy=(
                    None
                    if final is None
                    else final.metadata.get("interaction_strategy")
                ),
            )
            return result

    def record_turn_stream_event(self, turn_id: UUID) -> None:
        """Record the first status/text event emitted to any SSE subscriber."""

        self._mark_turn_timing(turn_id, "first_sse_event")

    def record_turn_stream_completed(self, turn_id: UUID) -> None:
        """Record final SSE message emission separately from durable completion."""

        self._mark_turn_timing(turn_id, "response_stream_completed")

    def fast_reception_observation(self, turn_id: UUID):
        """Return bounded shadow evidence; it is never Conversation or Work truth."""

        return None if self.fast_reception is None else self.fast_reception.observation(turn_id)

    def response_events(
        self, turn_id: UUID, *, after_sequence: int = 0
    ) -> tuple[WicResponseEvent, ...]:
        with self.database.unit_of_work() as uow:
            return InteractionStore(uow.session).response_events(
                turn_id, after_sequence=after_sequence
            )

    def _record_response_event(
        self,
        turn_id: UUID,
        event_type: WicResponseEventType,
        *,
        content: str | None = None,
        basis_fingerprint: str | None = None,
        reconciliation: ResponseReconciliation | None = None,
        metadata: dict[str, object] | None = None,
        only_while_processing: bool = False,
    ) -> WicResponseEvent | None:
        now = datetime.now(UTC)
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            # The Turn row serializes sequence allocation without coupling the
            # database lock to the process-local stream lock.
            turn = store.turn(turn_id, for_update=True)
            if turn is None:
                return None
            if only_while_processing and turn.status not in {
                InteractionTurnStatus.RECEIVED,
                InteractionTurnStatus.PROCESSING,
            }:
                return None
            sequence = store.next_response_event_sequence(turn_id)
            event_id = uuid4()
            store.insert_response_event(
                {
                    "id": event_id, "interaction_id": turn.interaction_id,
                    "turn_id": turn_id, "response_id": turn_id,
                    "sequence": sequence, "event_type": event_type.value,
                    "content": content, "basis_fingerprint": basis_fingerprint,
                    "reconciliation": None if reconciliation is None else reconciliation.value,
                    "event_metadata": metadata or {}, "created_at": now,
                }
            )
            uow.commit()
        return WicResponseEvent(
            id=event_id, interaction_id=turn.interaction_id, turn_id=turn_id,
            response_id=turn_id, sequence=sequence, event_type=event_type,
            content=content, basis_fingerprint=basis_fingerprint,
            reconciliation=reconciliation, metadata=metadata or {}, created_at=now,
        )

    def _mark_turn_timing(self, turn_id: UUID, event: str) -> None:
        if event not in _TURN_TIMING_MILESTONES:
            return
        with self._turn_lock:
            timing = self._turn_timings.get(turn_id)
            if timing is not None and event not in timing.milestones:
                timing.milestones[event] = (datetime.now(UTC), monotonic())

    def _forget_turn(self, turn_id: UUID, completed: Future[None]) -> None:
        with self._turn_lock:
            if self._turn_futures.get(turn_id) is completed:
                self._turn_futures.pop(turn_id, None)
                self._turn_realization_started.discard(turn_id)

    def turn_response_delta(self, turn_id: UUID, offset: int) -> tuple[str, int]:
        """Read ephemeral UX output; persisted messages remain conversation truth."""

        with self._turn_lock:
            content = self._turn_response_streams.get(turn_id, "")
        safe_offset = min(max(offset, 0), len(content))
        return content[safe_offset:], len(content)

    def _publish_turn_response_delta(self, turn_id: UUID, delta: str) -> None:
        if not delta:
            return
        with self._turn_lock:
            if delta.strip():
                self._mark_turn_timing(turn_id, "first_response_delta")
            self._turn_response_streams[turn_id] = (
                self._turn_response_streams.get(turn_id, "") + delta
            )
            self._turn_response_streams.move_to_end(turn_id)
            while len(self._turn_response_streams) > 32:
                self._turn_response_streams.popitem(last=False)

    def _reconcile_turn_response(self, turn_id: UUID, content: str) -> None:
        """Align bounded streaming UX state with the final persisted message."""

        with self._turn_lock:
            self._turn_response_streams[turn_id] = content
            self._turn_response_streams.move_to_end(turn_id)
            while len(self._turn_response_streams) > 32:
                self._turn_response_streams.popitem(last=False)

    def _realize_controlled_response(
        self,
        turn_id: UUID,
        assessment: InteractionAssessment,
        *,
        latest_human_input: str,
        observed_action_answer: str | None = None,
    ) -> tuple[
        str,
        GovernedResponseRealization,
        ResponseReconciliation,
        int,
        dict[str, object],
    ]:
        """Stream expression only after semantic/policy governance has settled."""

        with self._turn_lock:
            self._turn_realization_started.add(turn_id)
        deep_content = self._human_facing_response(assessment.natural_response)
        action_reality = self.get_shared_understanding(assessment.interaction_id)
        branch_status_answer = observed_action_answer
        if branch_status_answer is not None:
            deep_content = branch_status_answer
        events = self.response_events(turn_id)
        provisional_event = next(
            (
                event
                for event in events
                if event.event_type is WicResponseEventType.PROVISIONAL_RESPONSE
            ),
            None,
        )
        provisional = None if provisional_event is None else provisional_event.content
        with self._turn_lock:
            fast = self._turn_fast_candidates.get(turn_id)
        semantics = assessment.progressive_semantics
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            contract = store.latest_response_contract(
                assessment.interaction_id, basis_fingerprint=assessment.basis_fingerprint,
            )
            previous_contract = store.latest_response_contract(
                assessment.interaction_id, completed_only=True,
            )
            recent_messages = tuple(
                ConversationContextMessage(actor=message.actor.value, content=message.content)
                for message in store.messages(assessment.interaction_id, limit=8)
                if message.processing_status is InteractionTurnStatus.COMPLETED
            )
        reconciliation = (
            ResponseReconciliation.REFINE
            if semantics is None
            else reconcile_fast_and_deep(fast, semantics)
            if fast is not None
            else reconcile_provisional_intent(
                str(provisional_event.metadata.get("eligibility")), semantics
            )
            if provisional_event is not None
            else ResponseReconciliation.REFINE
        )
        reconciliation = reconcile_contract_response(contract, reconciliation, semantics)
        if provisional:
            if reconciliation is ResponseReconciliation.MATERIAL_CORRECTION:
                continuation = "\n\n" + corrected_continuation(
                    deep_content,
                    chinese=bool(re.search(r"[\u4e00-\u9fff]", deep_content)),
                )
            elif deep_content.startswith(provisional):
                continuation = deep_content[len(provisional) :]
            else:
                continuation = "\n\n" + deep_content
        else:
            continuation = deep_content
        execution_kind = None
        execution_reference = None
        with self._turn_lock:
            execution_provider = self._work_execution_reality_provider
        if (
            execution_provider is not None
            and action_reality.governed_work_id is not None
        ):
            execution_kind, execution_reference = execution_provider(
                action_reality.governed_work_id
            )
        envelope = governed_response_envelope(
            assessment,
            governed_content=continuation,
            provisional_content=provisional,
            reconciliation=reconciliation,
            latest_human_input=latest_human_input,
            response_contract=contract,
            previous_response_contract=previous_contract,
            recent_relevant_messages=recent_messages,
            production_admission_state=(
                None
                if action_reality.production_admission_state is None
                else action_reality.production_admission_state.value
            ),
            repository_acquisition_state=(
                None
                if action_reality.repository_acquisition_state is None
                else action_reality.repository_acquisition_state.value
            ),
            production_next_step=action_reality.production_next_step,
            execution_operation_kind=execution_kind,
            execution_operation_reference=execution_reference,
        )
        with self.database.unit_of_work() as uow:
            obligations = IntentRealizationStore(uow.session).obligations(turn_id)
        envelope = envelope.model_copy(update={"obligation_ledger": tuple(o.model_dump(mode="json") for o in obligations)})
        response_realizer = self.response_realizer
        if branch_status_answer is not None:
            response_realizer = DeterministicGovernedResponseRealizer()
        pipeline_evidence = getattr(self.capability, "last_pipeline_evidence", None)
        if (_provider_supplied_human_wording(pipeline_evidence)
                or assessment.provider_identity == "watt-native:work-reality-query"
                or (assessment.basis_work_revision_id is not None and assessment.semantic_ir is not None
                    and any(item.kind is SemanticKind.STATUS_QUERY and item.subject in {
                        "WORK_CURRENT", "WORK_HISTORY", "WORK_DIAGNOSTIC"} for item in assessment.semantic_ir.items))):
            # The dedicated/coalesced Conversation provider already supplied
            # natural wording. After semantic policy and Interaction Strategy
            # admission, another external wording call adds latency and can only
            # introduce drift. Keep the Realizer seam, but make it deterministic.
            response_realizer = DeterministicGovernedResponseRealizer()
        if (
            envelope.governance_candidate
            == GovernanceCandidateKind.HUMAN_DECISION_REQUIRED.value
        ):
            # A replaceable language model may phrase admitted semantics, but it
            # must not invent a concrete value for a decision that still belongs
            # to the Human.  Stream the governed wording itself for this narrow
            # authority-sensitive case instead of asking a model to paraphrase it.
            response_realizer = DeterministicGovernedResponseRealizer()
        phase_type = (
            WicResponseEventType.RESPONSE_CORRECTION
            if reconciliation is ResponseReconciliation.MATERIAL_CORRECTION
            else WicResponseEventType.RESPONSE_REFINEMENT
        )
        realizer_identity = getattr(
            response_realizer, "provider_identity", "unknown-realizer"
        )
        realizer_model = getattr(response_realizer, "model_identity", None)
        self._record_response_event(
            turn_id,
            phase_type,
            basis_fingerprint=assessment.basis_fingerprint,
            reconciliation=reconciliation,
            metadata={
                "policy_governed": True,
                "content_streamed_separately": True,
                "trust_stage": ResponseTrustStage.GOVERNED.value,
            },
            only_while_processing=True,
        )
        self._record_response_event(
            turn_id,
            WicResponseEventType.RESPONSE_STREAM_STARTED,
            basis_fingerprint=assessment.basis_fingerprint,
            reconciliation=reconciliation,
            metadata={
                "provider": realizer_identity,
                "model": realizer_model,
                "provisional_present": provisional is not None,
                "trust_stage": ResponseTrustStage.GOVERNED.value,
            },
            only_while_processing=True,
        )
        self._mark_turn_timing(turn_id, "realization_started")
        delta_count = 0
        raw_parts: list[str] = []

        def emit_admitted(delta: str) -> None:
            nonlocal delta_count
            delta_count += 1
            self._mark_turn_timing(turn_id, "first_realization_delta")
            event = self._record_response_event(
                turn_id,
                WicResponseEventType.RESPONSE_DELTA,
                content=delta,
                basis_fingerprint=assessment.basis_fingerprint,
                reconciliation=reconciliation,
                metadata={
                    "delta_index": delta_count,
                    "trust_stage": ResponseTrustStage.GOVERNED.value,
                },
                only_while_processing=True,
            )
            if event is None:
                raise InteractionInvariantViolation(
                    "Governed response Turn stopped before delta persistence"
                )
            self._publish_turn_response_delta(turn_id, delta)

        gate = GovernedDeltaGate(envelope, emit_admitted)

        def receive_raw(delta: str) -> None:
            self._mark_turn_timing(turn_id, "first_realizer_output_chunk")
            raw_parts.append(delta)
            gate.feed(delta)

        realization = response_realizer.realize_stream(
            envelope,
            on_response_delta=receive_raw,
        )
        raw_content = "".join(raw_parts)
        if realization.content.startswith(raw_content):
            gate.feed(realization.content[len(raw_content) :])
        elif realization.content != raw_content:
            raise InteractionInvariantViolation(
                "Governed response stream and settled realization diverged"
            )
        admitted_content = gate.finish()
        if admitted_content != realization.content:
            if not gate.suppressed:
                raise InteractionInvariantViolation(
                    "Governed response delta sequence does not reconstruct the result"
                )
            realization = realization.model_copy(update={"content": admitted_content})
        if realization.structural_repair_count:
            self._record_response_event(
                turn_id, WicResponseEventType.RESPONSE_REFINEMENT,
                basis_fingerprint=assessment.basis_fingerprint,
                metadata={
                    "component": "wic/governed-response-realizer",
                    "signal": "PROVIDER_SCHEMA_MISMATCH", "automatic": True,
                    "recovery_scope": "EXPRESSION_ONLY", "work_converged": False,
                    "attempt_budget": 2, "attempt_count": 2,
                    "final_condition": "LOCAL_OBLIGATION_RECOVERED",
                    "evidence_reference": f"provider-request:{realization.request_id}",
                }, only_while_processing=True,
            )
        self._mark_turn_timing(turn_id, "realization_completed")
        response_content = (provisional or "") + admitted_content
        return (
            response_content,
            realization,
            reconciliation,
            delta_count,
            envelope.interaction_strategy.model_dump(mode="json"),
        )

    def realization_projection(self, turn_id: UUID):
        self.get_turn(turn_id)
        with self.database.unit_of_work() as uow:
            return IntentRealizationStore(uow.session).projection(turn_id)

    def _close_owner_obligation(self, obligation, observation, *, blocker=None, refresh=None):
        from spg.application.intent_realization import IntentRealizationViolation
        from spg.domain.intent_realization import RealizationRefinement, RealizationScope, RealizationSignal
        with self.database.unit_of_work() as uow:
            ledger = IntentRealizationStore(uow.session)
            current = next(o for o in ledger.obligations(obligation.turn_id) if o.id == obligation.id)
            if current.state in TERMINAL_OBLIGATION_STATES:
                return current
            history = tuple(r for r in ledger.refinements(current.turn_id)
                if r.obligation_id == current.id)
            prior = history[-1] if history else None
            while observation is not None:
                try:
                    value = ledger.transition(current, observation=observation)
                    if prior is not None and prior.attempt < prior.attempt_budget:
                        ledger.record_refinement(RealizationRefinement(id=uuid4(), parent_id=prior.id,
                            turn_id=current.turn_id, obligation_id=current.id, scope=prior.scope,
                            signal=prior.signal, attempt=prior.attempt + 1, attempt_budget=prior.attempt_budget,
                            evidence_references=observation.evidence_references, local_recovered=True))
                    uow.commit()
                    return value
                except IntentRealizationViolation as error:
                    if not str(error).startswith("EXPECTED_EFFECT_NOT_REALIZED"):
                        raise
                    if prior is None or prior.attempt < prior.attempt_budget:
                        prior = RealizationRefinement(id=uuid4(), parent_id=None if prior is None else prior.id,
                            turn_id=current.turn_id, obligation_id=current.id,
                            scope=RealizationScope.ACTION if current.plane is ObligationPlane.ACTION else RealizationScope.WORK,
                            signal=RealizationSignal.EXPECTED_EFFECT_NOT_REALIZED,
                            attempt=1 if prior is None else prior.attempt + 1, attempt_budget=2,
                            evidence_references=observation.evidence_references)
                        ledger.record_refinement(prior)
                    # Recovery refreshes owner Reality once on this same basis.
                    # It never blindly repeats a write, requests credentials,
                    # changes Human authority or claims parent Work convergence.
                    if refresh is not None and prior.attempt < prior.attempt_budget:
                        observation = refresh()
                        refresh = None
                        continue
                    break
            value = ledger.transition(current, state=ObligationState.BLOCKED_WITH_EVIDENCE,
                blocker_reference=blocker or (f"realization-refinement:{prior.id}" if prior else
                    f"semantic-ir:{current.semantic_ir_id}:owner-not-materialized"))
            if observation is not None:
                payload = value.model_copy(update={"observed_effect": observation})
                from sqlalchemy import update
                from spg.infrastructure.persistence.intent_realization_schema import turn_obligations
                uow.session.execute(update(turn_obligations).where(turn_obligations.c.id == value.id,
                    turn_obligations.c.version == value.version).values(payload=payload.model_dump(mode="json")))
                value = payload
            uow.commit()
        return value

    def _semantic_owner_observations(self, interaction_id):
        observations = []
        with self.database.unit_of_work() as uow:
            interaction_store = InteractionStore(uow.session)
            interaction = interaction_store.interaction(interaction_id)
            ledger = IntentRealizationStore(uow.session)
            for previous_turn in interaction_store.turns(interaction_id):
                for obligation in ledger.obligations(previous_turn.id):
                    if obligation.state in {ObligationState.PENDING,ObligationState.RUNNING}:
                        observations.append(ObservedEffect(owner="turn-obligation-ledger",
                            evidence_references=(f"obligation:{obligation.id}",),
                            facts={"obligation_id":str(obligation.id),"state":obligation.state.value,
                                "semantic_item_id":obligation.semantic_item_id,"version":obligation.version}))
            revision = None if interaction is None or interaction.current_work_id is None else (
                ProductStore(uow.session).current_work_reality_revision(interaction.current_work_id))
        if revision is not None:
            observations.append(ObservedEffect(owner="work-reality",
                evidence_references=(f"work-reality-revision:{revision.id}",),
                facts={"work_id": str(revision.work_id), "work_revision_id": str(revision.id),
                    "desired_outcome": revision.desired_outcome, "context_facts": list(revision.context_facts),
                    "constraints": list(revision.constraints), "requests": list(revision.requests)}))
        observation = (self._repository_observation_provider(interaction_id)
            if self._repository_observation_provider is not None else None)
        if observation is not None:
            observations.append(ObservedEffect(owner="repository-asset",
            evidence_references=(f"repository-intake:{observation['intake_request_id']}",
                *((f"runtime-snapshot:{observation['current_trusted_snapshot_id']}",)
                    if observation.get("current_trusted_snapshot_id") else ())),
            facts={key: value for key, value in observation.items() if key not in {"request", "technical_evidence"}}))
        return tuple(observations)

    def _repository_effect(self, interaction_id):
        projection = self.get_shared_understanding(interaction_id)
        observation = (self._repository_observation_provider(interaction_id)
            if self._repository_observation_provider is not None else None)
        if observation is not None:
            facts = {key: value for key, value in observation.items() if key != "request"}
            # An exact intake observes the repository metadata/tree. Inspection
            # proof is the retained exact owner receipt, never response wording.
            if facts.get("condition") == "READY" and facts.get("tree"):
                facts["inspected_references"] = (facts.get("repository_identity"), facts["tree"])
            references = (f"repository-intake:{facts['intake_request_id']}",
                *((f"runtime-snapshot:{facts['current_trusted_snapshot_id']}",)
                    if facts.get("current_trusted_snapshot_id") else ()))
            revision = projection.governed_revision
            if projection.governed_work_id is not None and revision is not None:
                # A new asset alone cannot claim to have switched an existing
                # Work. Observe its selected binding as the current branch.
                facts["current_branch"] = revision.repository_ref
                facts["work_repository_revision"] = revision.source_revision
                references += (f"work-reality-revision:{revision.id}",)
            return ObservedEffect(owner="repository-asset",
                evidence_references=references, facts=facts)
        revision = projection.governed_revision
        if revision is not None and revision.repository_ref and revision.source_revision:
            return ObservedEffect(owner="work-repository-binding",
                evidence_references=(f"work-reality-revision:{revision.id}",),
                facts={"repository_ref": revision.repository_ref, "revision": revision.source_revision})
        return None

    def _dispatch_repository_obligations(self, turn, assessment, record):
        from spg.domain.interaction_actions import CanonicalOperation as O
        repository_ops = {O.ACQUIRE_REPOSITORY, O.INSPECT_REPOSITORY,
            O.SEARCH_REPOSITORY, O.CREATE_AND_SWITCH_BRANCH, O.CREATE_BRANCH, O.SWITCH_BRANCH, O.QUERY_CURRENT_BRANCH}
        with self.database.unit_of_work() as uow:
            ledger = IntentRealizationStore(uow.session)
            ledger.initialize(turn.id, assessment.id, assessment.semantic_ir)
            for item in assessment.semantic_ir.items:
                if not item.supersedes:
                    continue
                obligation = next(o for o in ledger.obligations(turn.id) if o.semantic_item_id == item.item_id)
                if obligation.state in TERMINAL_OBLIGATION_STATES:
                    continue
                superseded = []
                for previous_turn in InteractionStore(uow.session).turns(turn.interaction_id):
                    for prior in ledger.obligations(previous_turn.id):
                        if str(prior.id) not in item.supersedes:
                            continue
                        if prior.state is ObligationState.PENDING:
                            ledger.supersede(prior,replacement_ir=assessment.semantic_ir,replacement_item_id=item.item_id)
                            superseded.append(str(prior.id))
                proof = ObservedEffect(owner="turn-obligation-ledger",
                    evidence_references=(f"semantic-ir:{assessment.semantic_ir.id}:item:{item.item_id}:disposition",),
                    facts={"superseded_obligation_ids":superseded})
                if set(superseded) == set(item.supersedes):
                    ledger.transition(obligation,observation=proof)
                else:
                    ledger.transition(obligation,state=ObligationState.BLOCKED_WITH_EVIDENCE,
                        blocker_reference=f"semantic-ir:{assessment.semantic_ir.id}:item:{item.item_id}:owner-cancellation-not-acknowledged")
            uow.commit()
        answers = []
        # Semantic dependencies determine dispatch, not clause/keyword ordering.
        pending = [item for item in executable_semantic_actions(assessment.semantic_ir)
            if O(item.action.operation) in repository_ops]
        while pending:
            with self.database.unit_of_work() as uow:
                obligations = IntentRealizationStore(uow.session).obligations(turn.id)
            by_id = {o.id: o for o in obligations}
            current = next((item for item in pending if all(
                by_id[dep].state in TERMINAL_OBLIGATION_STATES
                for dep in next(o for o in obligations if o.semantic_item_id == item.item_id).depends_on)), None)
            if current is None:
                break
            pending.remove(current)
            obligation = next(o for o in obligations if o.semantic_item_id == current.item_id)
            if obligation.state in TERMINAL_OBLIGATION_STATES:
                continue
            if any(by_id[dep].state is not ObligationState.SATISFIED for dep in obligation.depends_on):
                self._close_owner_obligation(obligation, None,
                    blocker=f"obligation:{obligation.id}:dependency-not-satisfied")
                answers.append("前置操作尚未满足执行条件，后续操作没有执行。")
                continue
            with self.database.unit_of_work() as uow:
                running = IntentRealizationStore(uow.session).transition(obligation, state=ObligationState.RUNNING)
                uow.commit()
            item_ir = assessment.semantic_ir.model_copy(update={"items": (current,)})
            owner_assessment = assessment.model_copy(update={"semantic_ir": item_ir,
                "action_candidates": legacy_action_projection(item_ir)})
            projection = self.get_shared_understanding(turn.interaction_id)
            answer = None
            if (O(current.action.operation) in {O.CREATE_AND_SWITCH_BRANCH, O.CREATE_BRANCH, O.SWITCH_BRANCH, O.ACQUIRE_REPOSITORY}
                    and projection.governed_work_id is not None):
                if self._governed_branch_handler is not None:
                    answer = self._governed_branch_handler(turn.interaction_id, owner_assessment, record)
            elif self._repository_action_handler is not None:
                answer = self._repository_action_handler(turn.interaction_id, owner_assessment, record)
            observed = self._repository_effect(turn.interaction_id)
            if observed is not None and observed.facts.get("condition") == "RUNNING":
                observed = observed.model_copy(update={"facts": {**observed.facts, "owner_running": True}})
                with self.database.unit_of_work() as uow:
                    IntentRealizationStore(uow.session).transition(running,
                        state=ObligationState.RUNNING, running_evidence=observed)
                    uow.commit()
                continue
            value = self._close_owner_obligation(running, observed,
                blocker=f"interaction-assessment:{assessment.id}:repository-owner-not-realized",
                refresh=lambda: self._repository_effect(turn.interaction_id))
            if value.state is ObligationState.SATISFIED:
                if O(current.action.operation) is O.QUERY_CURRENT_BRANCH:
                    answer = _repository_branch_status_answer("", self.get_shared_understanding(turn.interaction_id))
                answers.append(answer or _repository_branch_status_answer("", self.get_shared_understanding(turn.interaction_id)))
            else:
                answers.append("所请求的仓库操作尚未完成；实际仓库状态没有满足这项请求，未安排无证据的后台重试。")
        return "\n".join(answer for answer in answers if answer) or None

    def _dispatch_registered_obligations(self, turn, assessment, record):
        answers = []
        with self.database.unit_of_work() as uow:
            obligations = IntentRealizationStore(uow.session).obligations(turn.id)
        by_id = {o.id: o for o in obligations}
        for item in executable_semantic_actions(assessment.semantic_ir):
            obligation = next(o for o in obligations if o.semantic_item_id == item.item_id)
            handler = self._operational_owner_handlers.get(obligation.operation)
            if handler is None or obligation.state in TERMINAL_OBLIGATION_STATES:
                continue
            if any(by_id[dep].state is not ObligationState.SATISFIED for dep in obligation.depends_on):
                continue
            if obligation.state is ObligationState.PENDING:
                with self.database.unit_of_work() as uow:
                    obligation = IntentRealizationStore(uow.session).transition(obligation, state=ObligationState.RUNNING)
                    uow.commit()
            observation = handler(assessment.interaction_id, item, record.source)
            if observation.facts.get("owner_running") is True:
                # Owner has actually materialized a durable pending operation.
                # A running owner cannot be changed into a terminal narrative.
                with self.database.unit_of_work() as uow:
                    ledger = IntentRealizationStore(uow.session)
                    latest = next(value for value in ledger.obligations(turn.id) if value.id == obligation.id)
                    ledger.transition(latest, state=ObligationState.RUNNING, running_evidence=observation)
                    uow.commit()
                continue
            value = self._close_owner_obligation(obligation, observation)
            answers.append("请求的操作已完成，实际效果已核验。" if value.state is ObligationState.SATISFIED
                else "请求的操作没有完成；已保留实际执行条件或失败证据。")
        return "\n".join(answers) or None

    def _settle_turn_obligations(self, turn_id, assessment, *, research_result=None):
        projection = self.get_shared_understanding(assessment.interaction_id)
        with self.database.unit_of_work() as uow:
            obligations = IntentRealizationStore(uow.session).obligations(turn_id)
        for obligation in obligations:
            work_question = any(effect.predicate is EffectPredicate.WORK_QUESTION_RESOLVED
                for effect in obligation.expected_effects)
            if (obligation.state in TERMINAL_OBLIGATION_STATES or obligation.plane is ObligationPlane.INTERACTION
                    or obligation.operation in self._operational_owner_handlers or (
                        not work_question and
                        obligation.state is ObligationState.RUNNING and obligation.observed_effect is not None
                        and obligation.observed_effect.facts.get("owner_running"))):
                continue
            observed = None
            if work_question and projection.governed_revision is not None:
                target_step_id = obligation.expected_effects[0].target
                with self.database.unit_of_work() as uow:
                    product = ProductStore(uow.session)
                    steering = SteeringStore(uow.session)
                    admission = latest_assessment_revision(projection.governed_revision,
                        product.work_reality_revision)
                    plan = steering.plan_for_work(projection.governed_work_id)
                    active_plan = None if plan is None else steering.active_revision(plan.id)
                    current_step = None if active_plan is None else next((step
                        for step in steering.steps(active_plan.id)
                        if step.state.value == "CURRENT"), None)
                if admission is not None and admission.source_assessment_id == assessment.id:
                    retired = active_plan is not None and (
                        active_plan.id != assessment.basis_steering_plan_revision_id
                        or current_step is None or str(current_step.id) != target_step_id)
                    observed = ObservedEffect(owner="work-steering-question",
                        evidence_references=(f"work-reality-revision:{admission.id}",
                            f"steering-step:{target_step_id}"),
                        facts={"work_id": str(projection.governed_work_id),
                            "work_revision_id": str(projection.governed_revision.id),
                            "question_step_id": target_step_id,
                            "question_retired": retired,
                            "constraints": list(projection.governed_revision.constraints),
                            "owner_running": not retired})
                    if not retired:
                        if obligation.state is ObligationState.PENDING:
                            with self.database.unit_of_work() as uow:
                                IntentRealizationStore(uow.session).transition(
                                    obligation, state=ObligationState.RUNNING,
                                    running_evidence=observed)
                                uow.commit()
                        continue
            elif obligation.plane is ObligationPlane.WORK and projection.governed_revision is not None:
                with self.database.unit_of_work() as uow:
                    admission = latest_assessment_revision(projection.governed_revision,
                        ProductStore(uow.session).work_reality_revision)
                if admission is not None and admission.source_assessment_id == assessment.id:
                    observed = ObservedEffect(owner="work-admission",
                        evidence_references=tuple(dict.fromkeys((f"work-reality-revision:{admission.id}",
                            f"work-reality-revision:{projection.governed_revision.id}"))),
                        facts={"work_id":str(projection.governed_work_id),
                            "work_revision_id":str(projection.governed_revision.id),
                            "admitted_work_revision_id":str(admission.id),"assessment_id":str(assessment.id)})
            elif obligation.operation and obligation.operation.value in {"SEARCH_GITHUB", "SEARCH_WEB", "FETCH_PUBLIC_RESOURCE"} and research_result is not None:
                item = next(item for item in assessment.semantic_ir.items if item.item_id == obligation.semantic_item_id)
                args = item.action.arguments
                query = args.get("query") or args.get("url")
                source_type = "WEB" if obligation.operation.value == "SEARCH_WEB" else "GITHUB"
                if obligation.operation.value == "FETCH_PUBLIC_RESOURCE" and query:
                    from urllib.parse import urlsplit
                    source_type = "GITHUB" if urlsplit(query.value).hostname == "github.com" else "WEB"
                matching = [e for e in research_result.evidence if e.source_type == source_type
                    and (query is None or e.query == query.value or e.url == query.value)]
                observed = ObservedEffect(owner="external-research",
                    evidence_references=(f"task-contract:{research_result.task_contract_id}",),
                    facts={"search_state": "COMPLETED" if matching else "BLOCKED",
                        "evidence_ids": [e.evidence_id for e in matching],
                        "queries": list(dict.fromkeys(value for e in matching for value in (e.query,e.url))),
                        "search_operations": [obligation.operation.value] if matching else [],
                        "failure_categories": list(research_result.metrics.failure_categories),
                        "qualification_status": "BLOCKED_EXTERNAL" if source_type == "WEB" and
                            "CREDENTIAL_REQUIRED" in research_result.metrics.failure_categories else None})
            blocker_event = None
            if observed is None:
                blocker_event = self._record_response_event(turn_id, WicResponseEventType.RESPONSE_REFINEMENT,
                    basis_fingerprint=assessment.basis_fingerprint,
                    metadata={"component": "irk/owner-dispatch", "signal": "ACTION_TERMINAL_BLOCKER",
                        "obligation_id": str(obligation.id), "operation": None if obligation.operation is None else obligation.operation.value,
                        "work_present": projection.governed_work_id is not None,
                        "reason": "Existing owner eligibility or required effect was not realized",
                        "authority_expanded": False, "work_converged": False}, only_while_processing=True)
            self._close_owner_obligation(obligation, observed,
                blocker=f"interaction-response-event:{blocker_event.id}" if blocker_event is not None else None)

    def _process_turn(self, turn_id: UUID) -> None:
        now = datetime.now(UTC)
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            turn = store.turn(turn_id, for_update=True)
            if turn is None or turn.status in {
                InteractionTurnStatus.COMPLETED,
                InteractionTurnStatus.FAILED,
            }:
                uow.rollback()
                return
            request_record = store.record(turn.request_record_id)
            if request_record is None:
                raise InteractionRecordNotFound(
                    f"Interaction record not found: {turn.request_record_id}"
                )
            store.update_turn(
                turn_id,
                status=InteractionTurnStatus.PROCESSING,
                updated_at=now,
                started_at=turn.started_at or now,
            )
            store.update_turn_messages_status(
                turn_id,
                status=InteractionTurnStatus.PROCESSING,
                updated_at=now,
            )
            IntentRealizationStore(uow.session).begin_compilation(turn_id)
            uow.commit()
        self._mark_turn_timing(turn_id, "processing_started")
        recovery_events = tuple(event for event in self.response_events(turn_id)
            if event.event_type is WicResponseEventType.TURN_RECOVERY_STARTED)
        if recovery_events and recovery_events[-1].metadata.get("automatic"):
            sleep(min(2, int(recovery_events[-1].metadata.get("backoff_seconds", 1))))
        try:
            controlled = turn.wic_mode is WicRuntimeMode.WIC_VNEXT_CONTROLLED
            with self.database.unit_of_work() as uow:
                restored_assessment_id = IntentRealizationStore(uow.session).assessment_id(turn_id)
                restored_assessment = (None if restored_assessment_id is None else
                    InteractionStore(uow.session).assessment(restored_assessment_id))
            assessment = restored_assessment or self._assess_current(
                turn.interaction_id,
                on_response_delta=lambda _delta: None,
                on_pipeline_stage=lambda stage: self._mark_turn_timing(turn_id, stage),
                on_basis_ready=None,
                policy_governed=controlled,
            )
            independent_action_answer = self._dispatch_repository_obligations(turn, assessment, request_record)
            branch_action_answer = None
            if (self._governed_work_handler is not None
                    and (assessment.semantic_ir.current_production
                        or assessment.candidate_change is not None)):
                branch_action_answer = self._governed_work_handler(turn.interaction_id, assessment, request_record)
            admission_prepared = self._prepare_production_admission_if_ready(
                turn.interaction_id, assessment, request_record)
            if admission_prepared:
                self._execute_prepared_production_admission(turn.interaction_id, assessment, request_record)
            realization: GovernedResponseRealization | None = None
            reconciliation: ResponseReconciliation | None = None
            delta_count = 0
            interaction_strategy: dict[str, object] | None = None
            pipeline_evidence = getattr(self.capability, "last_pipeline_evidence", None)
            if is_dataclass(pipeline_evidence):
                pipeline_evidence = asdict(pipeline_evidence)
            elif hasattr(pipeline_evidence, "model_dump"):
                pipeline_evidence = pipeline_evidence.model_dump(mode="json")
            elif pipeline_evidence is not None and not isinstance(
                pipeline_evidence, dict
            ):
                pipeline_evidence = {"type": type(pipeline_evidence).__name__}
            refinement_observation = assessment.refinement_observation
            response_content = self._human_facing_response(
                assessment.natural_response
            )
            research_result = None
            if self.external_research is not None:
                requests = self.external_research.requests_for_turn(
                    request_record.content, response_content,
                    semantic_ir=assessment.semantic_ir,
                )
                if requests:
                    search_progress_published = False
                    def record_search_event(name: str, details: dict) -> None:
                        nonlocal search_progress_published
                        self._record_response_event(
                            turn_id, WicResponseEventType(name),
                            basis_fingerprint=assessment.basis_fingerprint,
                            metadata=details,
                            only_while_processing=True,
                        )
                        if (name == "SEARCH_STARTED" and not controlled
                                and not search_progress_published):
                            self._publish_turn_response_delta(
                                turn_id, "正在检索公开来源并核查结果…"
                            )
                            search_progress_published = True
                    research_result = self.external_research.run(
                        turn_id=turn_id,
                        interaction_id=turn.interaction_id,
                        work_id=self.get_shared_understanding(turn.interaction_id).governed_work_id,
                        user_id=request_record.source,
                        text=request_record.content,
                        requests=requests,
                        on_event=record_search_event,
                        steering_step_id=assessment.basis_steering_step_id,
                        repository_source=_research_repository_source(assessment),
                    )
                    response_content = research_result.answer
            registered_answer = self._dispatch_registered_obligations(turn, assessment, request_record)
            independent_action_answer = "\n".join(answer for answer in (independent_action_answer, registered_answer) if answer) or None
            status_answers = {}
            status_fact_coverage = {}
            self._settle_turn_obligations(turn_id, assessment, research_result=research_result)
            status_items = tuple(item for item in assessment.semantic_ir.items
                if item.kind is SemanticKind.STATUS_QUERY
                and item.subject in {"WORK_CURRENT", "WORK_HISTORY", "WORK_DIAGNOSTIC"})
            if status_items:
                status_basis = self._basis(turn.interaction_id)
                if status_basis.active_work_context is not None:
                    for item in status_items:
                        status_ir = assessment.semantic_ir.model_copy(update={"items": (item,)})
                        status_answers[item.item_id] = self._work_reality_status_candidate(
                            status_basis, semantic_ir=status_ir).natural_response
                        status_fact_coverage[item.item_id] = (
                            f"work-reality-revision:{status_basis.active_work_context.work_revision.id}",)
            status_basis = self._basis(turn.interaction_id)
            for item in assessment.semantic_ir.items:
                if item.kind is not SemanticKind.STATUS_QUERY or item.item_id in status_answers:
                    continue
                grounded = _grounded_status_facts(item, status_basis.observed_reality)
                if grounded is not None:
                    status_answers[item.item_id], status_fact_coverage[item.item_id] = grounded
            named_branch_answers = {}
            named_branch_questions = tuple(item for item in assessment.semantic_ir.items
                if item.kind is SemanticKind.QUESTION and item.subject
                and item.subject.startswith("branch:"))
            repository_observation = (self._repository_effect(turn.interaction_id)
                if named_branch_questions else None)
            for item in named_branch_questions:
                grounded = _grounded_named_branch_question(
                    item, repository_observation, request_record.id)
                if grounded is not None:
                    named_branch_answers[item.item_id] = grounded[0]
                    status_fact_coverage[item.item_id] = grounded[1]
            ledger_projection = self.realization_projection(turn_id)
            if (branch_action_answer is None and assessment.semantic_ir.items
                    and any(item.kind is SemanticKind.CONSTRAINT for item in assessment.semantic_ir.items)
                    and all(item.kind in {SemanticKind.CONSTRAINT, SemanticKind.FACT} for item in assessment.semantic_ir.items)
                    and not any(item.requires_human for item in assessment.semantic_ir.items)
                    and not any(question.requires_human for question in assessment.semantic_ir.questions)
                    and all(item["plane"] == "INTERACTION" and item["state"] == "SATISFIED"
                        for item in ledger_projection["obligations"])):
                # A constraint-only Turn owes a recorded boundary, not an
                # invented retrospective description of earlier execution.
                independent_action_answer = "已记录当前约束：" + "；".join(
                    item.statement for item in assessment.semantic_ir.items if item.kind is SemanticKind.CONSTRAINT)
            work_effects = [item for item in ledger_projection["obligations"] if item["plane"] == "WORK"]
            if (registered_answer is None and work_effects
                    and any(item["state"] == "SATISFIED" for item in work_effects)):
                # Preparatory owner wording was captured before Work admission.
                # Realize the combined current outcome from the final owner basis,
                # rather than publishing that earlier snapshot as final truth.
                final_basis = self._basis(turn.interaction_id)
                if final_basis.active_work_context is not None:
                    actual = self.get_shared_understanding(turn.interaction_id)
                    independent_action_answer = "\n".join(filter(None,(
                        _repository_branch_status_answer("",actual),
                        f"当前目标已准入生产 Work：{final_basis.active_work_context.work_revision.desired_outcome}",
                        self._work_reality_status_candidate(final_basis).natural_response)))
            running_obligations = [item for item in ledger_projection["obligations"]
                if item["state"] in {"PENDING", "RUNNING"} and item["plane"] != "INTERACTION"]
            if running_obligations and (datetime.now(UTC) - (turn.started_at or now)).total_seconds() >= 300:
                budget_event = self._record_response_event(turn_id, WicResponseEventType.RESPONSE_REFINEMENT,
                    basis_fingerprint=assessment.basis_fingerprint, metadata={"component": "irk/owner-dispatch",
                        "signal": "TURN_NON_CONVERGING", "time_budget_seconds": 300,
                        "recovery_scope": "TURN", "work_converged": False}, only_while_processing=True)
                for payload in running_obligations:
                    from spg.domain.intent_realization import RealizationRefinement, RealizationScope, RealizationSignal
                    expired = TurnObligation.model_validate(payload)
                    with self.database.unit_of_work() as uow:
                        ledger = IntentRealizationStore(uow.session)
                        history = [r for r in ledger.refinements(turn_id) if r.obligation_id == expired.id]
                        if not history:
                            ledger.record_refinement(RealizationRefinement(id=uuid4(),turn_id=turn_id,
                                obligation_id=expired.id,scope=RealizationScope.ACTION if expired.plane is ObligationPlane.ACTION else RealizationScope.WORK,
                                signal=RealizationSignal.TURN_NON_CONVERGING,attempt=1,attempt_budget=1,
                                evidence_references=(f"interaction-response-event:{budget_event.id}",)))
                        uow.commit()
                    self._close_owner_obligation(TurnObligation.model_validate(payload), None,
                        blocker=f"interaction-response-event:{budget_event.id}")
                ledger_projection = self.realization_projection(turn_id)
                running_obligations = []
            if running_obligations:
                def continue_owner_observation():
                    sleep(1)
                    self._process_turn(turn_id)
                self._turn_executor.submit(continue_owner_observation)
                return
            blocked = [item for item in ledger_projection["obligations"]
                if item["state"] in {"BLOCKED_WITH_EVIDENCE", "REQUIRES_HUMAN"}]
            if blocked:
                # Independently satisfied owner effects remain true while each
                # unsatisfied current clause stays visible. No parent success is
                # inferred from a local recovery, and no generic cause is invented.
                by_item = {item.item_id: item for item in assessment.semantic_ir.items}
                boundaries = []
                for obligation in blocked:
                    item = by_item[obligation["semantic_item_id"]]
                    meaning = item.statement
                    disposition = "需要确认" if obligation["state"] == "REQUIRES_HUMAN" else "已阻塞并保留证据"
                    boundaries.append(f"尚未完成：{meaning}（{disposition}）。")
                independent_action_answer = "\n".join(filter(None, (
                    independent_action_answer, *boundaries)))
            if blocked and any(item["state"] == "REQUIRES_HUMAN" for item in blocked):
                question = assessment.progressive_semantics.selected_question if assessment.progressive_semantics else None
                if question and independent_action_answer:
                    independent_action_answer += "\n" + question
            if controlled and research_result is None:
                (
                    response_content,
                    realization,
                    reconciliation,
                    delta_count,
                    interaction_strategy,
                ) = self._realize_controlled_response(
                    turn_id,
                    assessment,
                    latest_human_input=request_record.content,
                    observed_action_answer=independent_action_answer or branch_action_answer,
                )
            if branch_action_answer is not None and research_result is None:
                response_content = branch_action_answer
            if independent_action_answer is not None and research_result is None:
                response_content = independent_action_answer
            answer_items = tuple(item for item in assessment.semantic_ir.items
                if item.kind in {SemanticKind.QUESTION, SemanticKind.ANALYSIS} and item.answer)
            direct_answer_coverage = set()
            if independent_action_answer is not None or research_result is not None:
                response_content = "\n".join(dict.fromkeys((response_content,
                    *(item.answer for item in answer_items))))
                direct_answer_coverage.update(item.item_id for item in answer_items)
            if status_answers:
                response_content = "\n".join(dict.fromkeys((response_content, *status_answers.values())))
            if named_branch_answers:
                # The exact owner branch list supersedes an earlier model
                # sentence about existence. Its receipt, not prose, closes the
                # question obligation.
                response_content = "\n".join(filter(None, (
                    independent_action_answer or branch_action_answer,
                    *named_branch_answers.values(),
                    *(answer for item_id, answer in status_answers.items()
                        if item_id not in named_branch_answers),
                    *(item.answer for item in answer_items
                        if item.item_id not in named_branch_answers))))
            final_response_basis = self._basis(turn.interaction_id)
            if (final_response_basis.active_work_context is not None
                    and final_response_basis.active_work_context != status_basis.active_work_context):
                # The realizer may have taken longer than a concurrent owner
                # reconciliation. Discard its earlier Work-state prose and
                # render from the newly observed owner revision.
                current_work = self.get_shared_understanding(turn.interaction_id)
                response_content = "\n".join(filter(None, (
                    _repository_branch_status_answer("", current_work),
                    self._work_reality_status_candidate(final_response_basis).natural_response,
                    *(item.answer for item in answer_items),
                )))
                for item in status_items:
                    status_fact_coverage[item.item_id] = (
                        f"work-reality-revision:{final_response_basis.active_work_context.work_revision.id}",)
                realization = None
                reconciliation = None
                self._record_response_event(turn_id, WicResponseEventType.RESPONSE_REFINEMENT,
                    basis_fingerprint=final_response_basis.basis_fingerprint,
                    metadata={"component": "irk/response-freshness",
                        "signal": "RESPONSE_BASIS_REFRESHED",
                        "previous_basis_fingerprint": status_basis.basis_fingerprint,
                        "work_revision_id": str(final_response_basis.active_work_context.work_revision.id)},
                    only_while_processing=True)
            self._mark_turn_timing(turn_id, "final_persistence_started")
            completed_at = datetime.now(UTC)
            with self.database.unit_of_work() as uow:
                store = InteractionStore(uow.session)
                current = store.turn(turn_id, for_update=True)
                if current is None:
                    raise InteractionRecordNotFound(
                        f"Interaction Turn not found: {turn_id}"
                    )
                if store.message_for_turn(turn_id, InteractionActor.WATT) is None:
                    interaction = store.interaction(turn.interaction_id)
                    design_refs = (
                        ()
                        if interaction is None
                        or interaction.selected_design_schema_identity is None
                        else (
                            "DESIGN_SCHEMA:"
                            f"{interaction.selected_design_schema_identity}@"
                            f"{interaction.selected_design_schema_version}",
                        )
                    )
                    if controlled:
                        store.insert_response_event({
                            "id": uuid4(), "interaction_id": turn.interaction_id,
                            "turn_id": turn_id, "response_id": turn_id,
                            "sequence": store.next_response_event_sequence(turn_id),
                            "event_type": WicResponseEventType.FINAL_RESPONSE.value,
                            "content": response_content,
                            "basis_fingerprint": assessment.basis_fingerprint,
                            "reconciliation": None if reconciliation is None else reconciliation.value,
                            "event_metadata": {
                                "trust_stage": ResponseTrustStage.FINAL.value,
                                "conversation_truth_pending": True,
                                "delta_count": delta_count,
                                "realizer_provider": None if realization is None else realization.provider_identity,
                                "realizer_model": None if realization is None else realization.model_identity,
                                "realizer_request_id": None if realization is None else realization.request_id,
                                "realizer_usage": None if realization is None else realization.usage,
                                "realizer_timing": None if realization is None else realization.timing,
                                "semantic_provider_evidence": pipeline_evidence,
                                "refinement_observation": refinement_observation,
                                "interaction_strategy": interaction_strategy,
                                "external_research": None if research_result is None else {
                                    "task_contract_id": str(research_result.task_contract_id),
                                    "metrics": research_result.metrics.model_dump(mode="json"),
                                    "evidence_ids": [item.evidence_id for item in research_result.evidence],
                                },
                            },
                            "created_at": completed_at,
                        })
                    self._reconcile_turn_response(turn_id, response_content)
                    store.insert_message(
                        {
                            "id": uuid4(),
                            "interaction_id": turn.interaction_id,
                            "turn_id": turn_id,
                            "sequence": store.next_message_sequence(turn.interaction_id),
                            "actor": InteractionActor.WATT.value,
                            "content": response_content,
                            "processing_status": InteractionTurnStatus.COMPLETED.value,
                            "interaction_record_id": None,
                            "interpretation_assessment_id": assessment.id,
                            "design_result_references": list(design_refs),
                            "governance_event_references": list(
                                (*assessment.supporting_references,
                                 *((item.evidence_id for item in research_result.evidence)
                                   if research_result is not None else ()))
                            ),
                            "supporting_references": list(
                                (*assessment.supporting_references,
                                 *((item.evidence_id for item in research_result.evidence)
                                   if research_result is not None else ()))
                            ),
                            "created_at": completed_at,
                            "updated_at": completed_at,
                        }
                    )
                ledger = IntentRealizationStore(uow.session)
                for obligation in ledger.obligations(turn_id):
                    if obligation.plane is ObligationPlane.INTERACTION and obligation.state not in TERMINAL_OBLIGATION_STATES:
                        item = next(item for item in assessment.semantic_ir.items
                            if item.item_id == obligation.semantic_item_id)
                        mixed = bool(assessment.semantic_ir.operational_requests or assessment.semantic_ir.current_production)
                        question_observed = bool(status_fact_coverage.get(item.item_id)) or (
                            item.item_id in direct_answer_coverage) or (
                            item.kind is not SemanticKind.STATUS_QUERY and not mixed
                            and bool(response_content.strip()))
                        if question_observed:
                            ledger.transition(obligation, observation=ObservedEffect(owner="interaction-response",
                                evidence_references=(f"interaction-turn:{turn_id}:final-response",
                                    *status_fact_coverage.get(item.item_id, ())),
                                facts={"answer_governed": True, "semantic_item_id": item.item_id,
                                    "covered_fact_ids": status_fact_coverage.get(item.item_id, ()),
                                    "direct_semantic_answer": item.item_id in direct_answer_coverage}))
                        else:
                            ledger.transition(obligation, state=ObligationState.BLOCKED_WITH_EVIDENCE,
                                blocker_reference=f"interaction-turn:{turn_id}:question-not-realized:{item.item_id}")
                ledger.validate_completion(turn_id)
                store.update_turn(
                    turn_id,
                    status=InteractionTurnStatus.COMPLETED,
                    updated_at=completed_at,
                    assessment_id=assessment.id,
                    completed_at=completed_at,
                )
                store.update_turn_messages_status(
                    turn_id,
                    status=InteractionTurnStatus.COMPLETED,
                    updated_at=completed_at,
                )
                if controlled:
                    store.insert_response_event({
                        "id": uuid4(), "interaction_id": turn.interaction_id,
                        "turn_id": turn_id, "response_id": turn_id,
                        "sequence": store.next_response_event_sequence(turn_id),
                        "event_type": WicResponseEventType.TURN_COMPLETED.value,
                        "content": None, "basis_fingerprint": assessment.basis_fingerprint,
                        "reconciliation": None, "event_metadata": {
                            "automatic_recovery_attempts": sum(
                                event.metadata.get("automatic") is True for event in recovery_events),
                            "recovery_scope": "WIC_TURN_ONLY",
                            "work_converged": False,
                        },
                        "created_at": completed_at,
                    })
                uow.commit()
            self._mark_turn_timing(turn_id, "persistence_completed")
            self._mark_turn_timing(turn_id, "completed")
        except Exception as error:  # persisted failure is the product-facing truth
            failed_at = datetime.now(UTC)
            failure = _classify_turn_failure(error, failed_at)
            automatic_recovery = False
            with self.database.unit_of_work() as uow:
                store = InteractionStore(uow.session)
                events = store.response_events(turn_id)
                recoveries = sum(event.event_type is WicResponseEventType.TURN_RECOVERY_STARTED
                    for event in events)
                records = store.records(turn.interaction_id)
                automatic_recovery = bool(
                    turn.wic_mode is WicRuntimeMode.WIC_VNEXT_CONTROLLED
                    and (isinstance(error, (_AssessmentBasisStale,
                        StructuredResponseSchemaViolation))
                        or (isinstance(error, ModelProviderError) and error.retryable
                            and error.kind in {ModelFailureKind.INCOMPLETE_RESPONSE,
                                ModelFailureKind.TIMEOUT_OR_NETWORK,
                                ModelFailureKind.CAPACITY_OR_RATE_LIMIT}))
                    and recoveries < 2 and records
                    and records[-1].id == turn.request_record_id
                    and store.message_for_turn(turn_id, InteractionActor.WATT) is None)
                if turn.wic_mode is WicRuntimeMode.WIC_VNEXT_CONTROLLED:
                    failure.metadata.update(automatic_recovery_pending=automatic_recovery,
                        automatic_attempt_budget=3, model_usage_unknown=(
                            error.usage_unknown if isinstance(error, ModelProviderError) else None))
                IntentRealizationStore(uow.session).compilation_failed(turn_id,
                    code=failure.code, evidence={"turn_id": str(turn_id),
                        "failure_message": failure.message,
                        "automatic_recovery_pending": automatic_recovery})
                store.update_turn(
                    turn_id,
                    status=InteractionTurnStatus.FAILED,
                    updated_at=failed_at,
                    failure_code=failure.code,
                    failure_message=failure.message,
                    refinement_observation=failure.metadata.get("refinement_observation"),
                    completed_at=failed_at,
                )
                store.update_turn_messages_status(
                    turn_id,
                    status=InteractionTurnStatus.FAILED,
                    updated_at=failed_at,
                )
                if turn.wic_mode is not WicRuntimeMode.LEGACY_WIC:
                    store.insert_response_event({
                        "id": uuid4(), "interaction_id": turn.interaction_id,
                        "turn_id": turn_id, "response_id": turn_id,
                        "sequence": store.next_response_event_sequence(turn_id),
                        "event_type": WicResponseEventType.TURN_FAILED.value,
                        "content": None, "basis_fingerprint": None,
                        "reconciliation": None,
                        "event_metadata": failure.metadata,
                        "created_at": failed_at,
                    })
                if automatic_recovery:
                    # Failure and recovery are one durable transition. Readers
                    # see RECEIVED while the historical failed event is retained.
                    store.reset_turn_for_retry(turn_id, updated_at=failed_at)
                    store.update_turn_messages_status(turn_id,
                        status=InteractionTurnStatus.RECEIVED, updated_at=failed_at)
                    store.insert_response_event({
                        "id": uuid4(), "interaction_id": turn.interaction_id,
                        "turn_id": turn_id, "response_id": turn_id,
                        "sequence": store.next_response_event_sequence(turn_id),
                        "event_type": WicResponseEventType.TURN_RECOVERY_STARTED.value,
                        "content": None, "basis_fingerprint": None, "reconciliation": None,
                        "event_metadata": {"attempt": recoveries + 1,
                            "previous_failure_class": failure.code, "human_input_reused": True,
                            "automatic": True, "backoff_seconds": recoveries + 1,
                            "attempt_budget": 3, "recovery_scope": "WIC_TURN_ONLY"},
                        "created_at": failed_at})
                uow.commit()
            self._mark_turn_timing(turn_id, "failed")
            if automatic_recovery:
                self._schedule_preserved_turn(turn_id)

    def assess_current(self, interaction_id: UUID) -> InteractionAssessment:
        return self._assess_current(
            interaction_id,
            on_response_delta=None,
            policy_governed=self.runtime_mode is WicRuntimeMode.WIC_VNEXT_CONTROLLED,
        )

    def _assess_current(
        self,
        interaction_id: UUID,
        *,
        on_response_delta: Callable[[str], None] | None,
        on_pipeline_stage: Callable[[str], None] | None = None,
        on_basis_ready: Callable[[InteractionInterpretationInput], None] | None = None,
        policy_governed: bool = False,
    ) -> InteractionAssessment:
        if on_pipeline_stage is not None:
            on_pipeline_stage("reality_load_started")
        basis = self._basis(interaction_id)
        if on_pipeline_stage is not None:
            on_pipeline_stage("reality_load_completed")
            on_pipeline_stage("basis_prepared")
        if on_basis_ready is not None:
            on_basis_ready(basis)
        with self.database.unit_of_work() as uow:
            existing = InteractionStore(uow.session).assessment_for_basis(
                interaction_id, basis.basis_fingerprint
            )
        if existing is not None:
            if on_pipeline_stage is not None:
                on_pipeline_stage("assessment_cache_hit")
            return existing
        streaming_interpret = getattr(self.capability, "interpret_stream", None)
        observed_interpret = getattr(self.capability, "interpret_stream_observed", None)
        controlled_observed_interpret = getattr(
            self.capability, "interpret_controlled_stream_observed", None
        )
        if on_pipeline_stage is not None:
            on_pipeline_stage("provider_started")
        if (
            policy_governed
            and on_response_delta is not None
            and on_pipeline_stage is not None
            and callable(controlled_observed_interpret)
        ):
            candidate = controlled_observed_interpret(
                basis,
                on_response_delta=on_response_delta,
                on_pipeline_stage=on_pipeline_stage,
            )
        elif (
            on_response_delta is not None
            and on_pipeline_stage is not None
            and callable(observed_interpret)
        ):
            candidate = observed_interpret(
                basis,
                on_response_delta=on_response_delta,
                on_pipeline_stage=on_pipeline_stage,
            )
        elif on_response_delta is not None and callable(streaming_interpret):
            candidate = streaming_interpret(basis, on_response_delta=on_response_delta)
        else:
            candidate = self.capability.interpret(basis)
        if on_pipeline_stage is not None:
            on_pipeline_stage("provider_returned")
        with self.database.unit_of_work() as uow:
            turn = InteractionStore(uow.session).unfinished_turn(interaction_id)
        if turn is not None and candidate.semantic_intent is not None:
            self._record_response_event(turn.id, WicResponseEventType.RESPONSE_REFINEMENT,
                basis_fingerprint=basis.basis_fingerprint,
                metadata={"component": "irk/semantic-compilation", "stage": "CANDIDATE_BEFORE_BINDING",
                    "semantic_candidate": candidate.semantic_intent.model_dump(mode="json"),
                    "compiler_reference": candidate.provider_identity, "work_converged": False},
                only_while_processing=True)
        return self.admit_candidate(
            interaction_id,
            basis_fingerprint=basis.basis_fingerprint,
            candidate=candidate,
            refinement_observation=_pipeline_refinement_observation(
                getattr(self.capability, "last_pipeline_evidence", None)
            ),
            on_pipeline_stage=on_pipeline_stage,
            policy_governed=policy_governed,
        )

    @staticmethod
    def _human_facing_response(natural_response: str) -> str:
        """Keep Provider-authored collaboration prose separate from metadata views."""

        return natural_response.strip()

    def admit_candidate(
        self,
        interaction_id: UUID,
        *,
        basis_fingerprint: str,
        candidate: InteractionAssessmentCandidate,
        refinement_observation: dict[str, object] | None = None,
        on_pipeline_stage: Callable[[str], None] | None = None,
        policy_governed: bool = False,
    ) -> InteractionAssessment:
        if on_pipeline_stage is not None:
            on_pipeline_stage("admission_started")
        now = datetime.now(UTC)
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            interaction = store.interaction(interaction_id, for_update=True)
            if interaction is None:
                raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
            records = store.records(interaction_id)
            if not records:
                raise InteractionInvariantViolation("Interaction has no assessment basis")
            active_context = self._active_work_context(uow.session, interaction)
            current_basis = interaction_basis_fingerprint(
                interaction,
                records,
                active_context,
            )
            if current_basis != basis_fingerprint:
                raise _AssessmentBasisStale(
                    "Interaction assessment basis is stale and cannot become current"
                )
            existing = store.assessment_for_basis(interaction_id, current_basis)
            if existing is not None:
                if on_pipeline_stage is not None:
                    on_pipeline_stage("assessment_cache_hit")
                return existing
            record_ids = {record.id for record in records}
            if any(
                source_id not in record_ids
                for meaning in candidate.meanings
                for source_id in meaning.source_record_ids
            ):
                raise InteractionInvariantViolation(
                    "Interpretation meaning references a record outside its basis"
                )
            latest_human_record = next(
                record
                for record in reversed(records)
                if record.actor is InteractionActor.HUMAN
            )
            latest_human_input = latest_human_record.content
            prior_assessment = store.latest_assessment(interaction_id)
            semantic_history = tuple(assessment.semantic_ir for assessment in
                store.assessments(interaction_id) if assessment.semantic_ir is not None)[-8:]
            semantic_basis = InteractionInterpretationInput(interaction=interaction,
                records=records, prior_assessment=prior_assessment,
                governed_semantic_history=semantic_history,
                active_work_context=active_context, basis_fingerprint=current_basis,
                observed_reality=(*self._semantic_owner_observations(interaction_id),
                    *(observation for provider in self._intent_observation_providers for observation in provider(interaction_id))))
            semantic_ir = IntentRealizationKernel().govern(candidate, semantic_basis)
            candidate = project_interaction_candidate(candidate, semantic_ir)
            if active_context is not None and any(item.kind is SemanticKind.STATUS_QUERY
                    and item.subject in {"WORK_CURRENT", "WORK_HISTORY", "WORK_DIAGNOSTIC"}
                    for item in semantic_ir.items):
                observed_status = self._work_reality_status_candidate(semantic_basis,
                    semantic_ir=semantic_ir)
                candidate = candidate.model_copy(update={"natural_response": observed_status.natural_response,
                    "response_intent": observed_status.response_intent,
                    "turn_intent": ConversationTurnIntent.DIRECT_QUESTION,
                    "focus_classification": WorkFocusClassification.SIDE_QUESTION,
                    "impact_disposition": WorkImpactDisposition.NO_GOVERNED_CHANGE})
            if (active_context is not None and not semantic_ir.legacy_typed_projection
                    and not semantic_ir.current_production
                    and not any(item.kind is SemanticKind.CORRECTION for item in semantic_ir.items)):
                # Operational/query/advisory turns cannot silently rewrite the
                # existing Work's long-lived goal through parallel provider fields.
                revision = active_context.work_revision
                candidate = candidate.model_copy(update={"interpreted_motive": revision.motive,
                    "desired_outcome": revision.desired_outcome, "current_requests": revision.requests,
                    "candidate_context": tuple(dict.fromkeys((*revision.context_facts,*candidate.candidate_context))),
                    "candidate_constraints": tuple(dict.fromkeys((*revision.constraints,*candidate.candidate_constraints)))})
                if _is_candidate_or_delivery_lifecycle_turn(semantic_ir):
                    # Candidate acceptance and delivery authority belong to their
                    # lifecycle owners. Coalesced provider fields cannot turn them
                    # into a new Work Reality revision and hide Candidate attention.
                    candidate = candidate.model_copy(update={
                        "candidate_context": revision.context_facts,
                        "candidate_constraints": revision.constraints,
                    })
            if active_context is not None and not semantic_ir.current_production and any(
                    item.kind in {SemanticKind.STATUS_QUERY, SemanticKind.QUESTION, SemanticKind.ANALYSIS}
                    for item in semantic_ir.items):
                candidate = candidate.model_copy(update={
                    "focus_classification": WorkFocusClassification.SIDE_QUESTION,
                    "impact_disposition": WorkImpactDisposition.NO_GOVERNED_CHANGE,
                })
            prior_facts = (
                active_context.work_revision.engineering_semantic_facts
                if active_context is not None
                else (
                    ()
                    if prior_assessment is None
                    else prior_assessment.engineering_semantic_facts
                )
            )
            if active_context is not None:
                candidate = self._canonicalize_explicit_branch_facts(
                    candidate,
                    latest_human_record,
                )
            engineering_semantic_facts = bind_engineering_semantic_facts(
                basis_fingerprint=current_basis,
                records=records,
                extractions=candidate.neutral_semantic_extractions,
                candidates=candidate.semantic_fact_candidates,
                prior_facts=prior_facts, semantic_ir=semantic_ir,
            )
            semantic_ir = semantic_ir.model_copy(update={
                "engineering_fact_ids": tuple(fact.id for fact in engineering_semantic_facts)})
            focus, impact, candidate_change = self._normalize_active_candidate(
                candidate,
                active_context,
                (active_context.work_revision.engineering_semantic_facts
                    if active_context is not None
                    and _is_candidate_or_delivery_lifecycle_turn(semantic_ir)
                    else engineering_semantic_facts),
                latest_human_input=latest_human_input,
                latest_human_record_id=latest_human_record.id,
                prior_production_references=tuple(
                    f"{prior.id}:{item.item_id}"
                    for prior in semantic_history for item in prior.items
                    if item.production is not None and item.production.current),
            )
            scope_question_step_id = (
                active_context.current_steering_step_id
                if active_context is not None
                and active_context.pending_human_question
                and candidate_change is not None
                and "constraints" in candidate_change.changed_fields
                and any(item.kind is SemanticKind.CONSTRAINT for item in semantic_ir.items)
                and (any(fact.relation is SemanticRelation.SCOPE
                    and latest_human_record.id in fact.provenance.source_record_ids
                    for fact in current_semantic_facts(engineering_semantic_facts))
                    or self._constraint_refers_to_current_production(
                        semantic_ir, latest_human_record.id,
                        tuple(f"{prior.id}:{item.item_id}"
                            for prior in semantic_history for item in prior.items
                            if item.production is not None and item.production.current)))
                else None)
            if scope_question_step_id is not None:
                semantic_ir = semantic_ir.model_copy(update={
                    "work_question_step_id": scope_question_step_id})
            progressive_semantics = build_progressive_semantics(
                candidate=candidate,
                records=records,
                basis_fingerprint=current_basis,
                prior_assessment=prior_assessment,
                active_context=active_context,
                focus=focus,
                impact=impact,
                semantic_ir=semantic_ir,
            )
            if policy_governed and candidate.provider_identity != "watt-native:work-reality-query":
                candidate = candidate.model_copy(
                    update={
                        "natural_response": policy_governed_response(
                            candidate,
                            progressive_semantics,
                            latest_human_input=latest_human_input,
                            active_context=active_context,
                        )
                    }
                )
            record_references = self._normalize_supporting_references(
                tuple(
                    reference
                    for record in records
                    for reference in record.supporting_references
                )
            )
            candidate_references = self._normalize_supporting_references(
                candidate.supporting_references
            )
            if not set(candidate_references).issubset(record_references):
                raise InteractionInvariantViolation(
                    "Interpretation cannot invent supporting Reality references"
                )
            supporting_references = tuple(
                dict.fromkeys((*record_references, *candidate_references))
            )
            readiness = self._evaluate_readiness(
                candidate,
                current_basis,
                governance_candidate=progressive_semantics.governance_candidate,
                progressive_semantics=progressive_semantics,
            )
            if on_pipeline_stage is not None:
                on_pipeline_stage("candidate_validated")
            if (
                interaction.current_work_id is None
                and candidate.design_intent_frame is not None
            ):
                schema, selection_rationale = match_design_schema_frame(
                    candidate.design_intent_frame
                )
                if schema is None:
                    store.clear_design_schema(interaction_id, updated_at=now)
                else:
                    store.select_design_schema(
                        interaction_id,
                        identity=schema.identity,
                        version=schema.version,
                        rationale=selection_rationale,
                        updated_at=now,
                    )
            assessment_id = uuid4()
            store.insert_assessment(
                {
                    "id": assessment_id,
                    "interaction_id": interaction_id,
                    "basis_fingerprint": current_basis,
                    "basis_last_sequence": records[-1].sequence,
                    "interpreted_motive": candidate.interpreted_motive,
                    "desired_outcome": candidate.desired_outcome,
                    "design_intent_frame": (
                        None
                        if candidate.design_intent_frame is None
                        else candidate.design_intent_frame.model_dump(mode="json")
                    ),
                    "candidate_context": list(candidate.candidate_context),
                    "candidate_constraints": list(candidate.candidate_constraints),
                    "current_requests": list(candidate.current_requests),
                    "unresolved_material_questions": list(
                        candidate.unresolved_material_questions
                    ),
                    "action_candidates": (None if candidate.action_candidates is None else
                        [item.model_dump(mode="json") for item in candidate.action_candidates]),
                    "semantic_ir": semantic_ir.model_dump(mode="json"),
                    "neutral_semantic_extractions": [
                        item.model_dump(mode="json")
                        for item in candidate.neutral_semantic_extractions
                    ],
                    "engineering_semantic_facts": [
                        item.model_dump(mode="json")
                        for item in engineering_semantic_facts
                    ],
                    "meanings": [
                        meaning.model_dump(mode="json") for meaning in candidate.meanings
                    ],
                    "focus_classification": None if focus is None else focus.value,
                    "impact_disposition": None if impact is None else impact.value,
                    "candidate_change": (
                        None
                        if candidate_change is None
                        else candidate_change.model_dump(mode="json")
                    ),
                    "basis_work_revision_id": (
                        None
                        if active_context is None
                        else active_context.work_revision.id
                    ),
                    "basis_steering_plan_revision_id": (
                        None
                        if active_context is None
                        else active_context.steering_plan_revision_id
                    ),
                    "basis_steering_step_id": (
                        None
                        if active_context is None
                        else active_context.current_steering_step_id
                    ),
                    "basis_active_runtime_binding_id": (
                        None
                        if active_context is None
                        else active_context.active_production_binding_id
                    ),
                    "supporting_references": list(supporting_references),
                    "refinement_observation": refinement_observation,
                    "natural_response": candidate.natural_response,
                    "readiness": readiness.model_dump(mode="json"),
                    "progressive_semantics": progressive_semantics.model_dump(mode="json"),
                    "provider_identity": candidate.provider_identity,
                    "model_identity": candidate.model_identity,
                    "schema_version": ASSESSMENT_SCHEMA_VERSION,
                    "created_at": now,
                }
            )
            current_turn = store.unfinished_turn(interaction_id)
            if current_turn is not None:
                if current_turn.request_record_id != semantic_ir.source_record_id:
                    raise InteractionInvariantViolation("IRK basis must belong to the current Turn")
                ledger = IntentRealizationStore(uow.session)
                ledger.initialize(current_turn.id, assessment_id, semantic_ir,
                    work_question_step_id=scope_question_step_id)
                if refinement_observation and refinement_observation.get("converged"):
                    from spg.domain.intent_realization import RealizationRefinement, RealizationScope, RealizationSignal
                    signal = RealizationSignal(refinement_observation.get("signal_kind", "SCHEMA_INVALID"))
                    first_id = uuid4()
                    references = (f"interaction-record:{latest_human_record.id}",
                        f"interaction-assessment:{assessment_id}")
                    ledger.record_refinement(RealizationRefinement(id=first_id, turn_id=current_turn.id,
                        scope=RealizationScope.TURN, signal=signal, attempt=1, attempt_budget=2,
                        evidence_references=references))
                    ledger.record_refinement(RealizationRefinement(id=uuid4(), parent_id=first_id,
                        turn_id=current_turn.id, scope=RealizationScope.TURN, signal=signal,
                        attempt=2, attempt_budget=2, evidence_references=references, local_recovered=True))
            if (
                active_context is not None
                and impact is WorkImpactDisposition.NEW_WORK_RECOMMENDED
            ):
                source_record = next(
                    record
                    for record in reversed(records)
                    if record.actor is InteractionActor.HUMAN
                )
                store.insert_work_transition(
                    {
                        "id": uuid5(
                            NAMESPACE_URL,
                            f"watt:wic-work-transition:{assessment_id}",
                        ),
                        "interaction_id": interaction.id,
                        "source_record_id": source_record.id,
                        "source_assessment_id": assessment_id,
                        "originating_work_id": active_context.work_revision.work_id,
                        "target_work_id": None,
                        "reason": candidate.natural_response,
                        "focus_classification": focus.value,
                        "impact_disposition": impact.value,
                        "choice": WorkTransitionChoice.PENDING_HUMAN.value,
                        "decided_by": None,
                        "decision_rationale": None,
                        "decided_at": None,
                        "created_at": now,
                    }
                )
            if policy_governed:
                turn = store.unfinished_turn(interaction_id)
                if turn is not None:
                    # Match the asynchronous Fast Reception event writer lock.
                    turn = store.turn(turn.id, for_update=True)
                    assert turn is not None
                    assessment = store.assessment(assessment_id)
                    assert assessment is not None
                    contract = build_response_contract(
                        assessment, interpretation=candidate.response_intent,
                        source_records=records,
                        previous_contract=store.latest_response_contract(
                            interaction_id, completed_only=True,
                        ),
                    )
                    store.insert_response_event({
                        "id": uuid4(), "interaction_id": interaction_id,
                        "turn_id": turn.id, "response_id": turn.id,
                        "sequence": store.next_response_event_sequence(turn.id),
                        "event_type": WicResponseEventType.RESPONSE_CONTRACT_READY.value,
                        "content": None, "basis_fingerprint": current_basis,
                        "reconciliation": None,
                        "event_metadata": {"response_contract": contract.model_dump(mode="json")},
                        "created_at": now,
                    })
            uow.commit()
        if on_pipeline_stage is not None:
            on_pipeline_stage("assessment_persisted")
        return self.get_assessment(assessment_id)

    def decide_work_transition(
        self,
        interaction_id: UUID,
        *,
        transition_id: UUID,
        expected_originating_work_id: UUID,
        choice: WorkTransitionChoice,
        authority_identity: str,
        rationale: str | None = None,
    ) -> SharedUnderstanding:
        if choice is WorkTransitionChoice.PENDING_HUMAN:
            raise InteractionInvariantViolation(
                "Human transition decision cannot remain pending"
            )
        identity = authority_identity.strip()
        if not identity:
            raise InteractionInvariantViolation("Human authority identity is required")
        now = datetime.now(UTC)
        new_work_id: UUID | None = None
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            interaction = store.interaction(interaction_id, for_update=True)
            transition = store.work_transition(transition_id, for_update=True)
            if interaction is None:
                raise InteractionRecordNotFound(
                    f"Interaction not found: {interaction_id}"
                )
            if interaction.condition is not InteractionCondition.OPEN:
                raise InteractionInvariantViolation(
                    "Archived Interaction cannot change Work focus"
                )
            if (
                transition is None
                or transition.interaction_id != interaction_id
                or transition.originating_work_id != expected_originating_work_id
            ):
                raise InteractionRecordNotFound(
                    f"Work transition not found: {transition_id}"
                )
            if transition.choice is not WorkTransitionChoice.PENDING_HUMAN:
                if transition.choice is choice:
                    uow.rollback()
                    return self.get_shared_understanding(interaction_id)
                raise InteractionInvariantViolation(
                    "Work transition already has a different Human choice"
                )
            if interaction.current_work_id != transition.originating_work_id:
                raise InteractionInvariantViolation(
                    "Work transition is stale against current Interaction focus"
                )
            decision_rationale = (
                rationale.strip()
                if rationale is not None and rationale.strip()
                else f"Human selected {choice.value} for the Work transition."
            )
            if choice is WorkTransitionChoice.START_NEW_WORK:
                new_work_id = uuid4()
                self._insert_pre_work(
                    ProductStore(uow.session),
                    work_id=new_work_id,
                    timestamp=now,
                )
                store.replace_current_work(
                    interaction_id,
                    expected_work_id=transition.originating_work_id,
                    new_work_id=new_work_id,
                    updated_by=identity,
                    updated_at=now,
                )
            else:
                store.touch_interaction(
                    interaction_id,
                    updated_by=identity,
                    updated_at=now,
                )
            store.decide_transition(
                transition.id,
                choice=choice,
                decided_by=identity,
                decision_rationale=decision_rationale,
                decided_at=now,
            )
            if new_work_id is not None:
                store.bind_transition_target(
                    transition.id,
                    target_work_id=new_work_id,
                )
            uow.commit()
        return self.get_shared_understanding(interaction_id)

    def get_assessment(self, assessment_id: UUID) -> InteractionAssessment:
        # Assessment ids are intentionally resolved through their owning Interaction;
        # this method is internal and keeps the store surface small.
        for projection in self.list_interactions():
            for assessment in self.assessment_history(projection.interaction.id):
                if assessment.id == assessment_id:
                    return assessment
        raise InteractionRecordNotFound(f"Interaction assessment not found: {assessment_id}")

    def assessment_history(self, interaction_id: UUID) -> tuple[InteractionAssessment, ...]:
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            if store.interaction(interaction_id) is None:
                raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
            return store.assessments(interaction_id)

    def get_shared_understanding(self, interaction_id: UUID) -> SharedUnderstanding:
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            product = ProductStore(uow.session)
            runtime = RuntimeStore(uow.session)
            interaction = store.interaction(interaction_id)
            if interaction is None:
                raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
            records = store.records(interaction_id)
            messages = store.messages(interaction_id)
            turns = store.turns(interaction_id)
            latest = store.latest_assessment(interaction_id)
            assessments = store.assessments(interaction_id)
            current_work = (
                None
                if interaction.current_work_id is None
                else product.work(interaction.current_work_id)
            )
            resource = None if interaction.current_work_id is None else product.resource_for_work(interaction.current_work_id)
            governed_revision = (
                None
                if interaction.current_work_id is None
                else product.current_work_reality_revision(interaction.current_work_id)
            )
            active_context = self._active_work_context(uow.session, interaction)
            admitted_from_latest = (
                None
                if latest is None
                else product.work_reality_revision_for_assessment(latest.id)
            )
            evolution_decisions = (
                []
                if latest is None
                else runtime.governance_for_subject(
                    f"interaction-assessment:{latest.id}"
                )
            )
            transitions = store.transitions(interaction_id)
            latest_transition = transitions[-1] if transitions else None
        current_basis = (
            interaction_basis_fingerprint(interaction, records, active_context)
            if records
            else None
        )
        # A historical assessment remains evidence but is not projected as the
        # current understanding after a newer record arrives.
        assessment_current = bool(
            latest is not None and latest.basis_fingerprint == current_basis
        )
        if latest is not None and latest.basis_last_sequence != records[-1].sequence:
                latest = None
                assessment_current = False
                admitted_from_latest = None
                evolution_decisions = []
        admission_status = self._revision_admission_status(
            latest,
            admitted_from_latest is not None,
            tuple(record.decision_type for record in evolution_decisions),
        )
        latest_human_input = next(
            (
                record.content
                for record in reversed(records)
                if record.actor is InteractionActor.HUMAN
            ),
            "",
        )
        current_production_evidence = production_evidence(None if latest is None else latest.semantic_ir)
        established_production_evidence = next((production_evidence(item.semantic_ir)
            for item in reversed(assessments) if item.semantic_ir and item.semantic_ir.current_production),
            current_production_evidence)
        production_evidence_value = (current_production_evidence if current_production_evidence.production_request
            else established_production_evidence if governed_revision is not None else current_production_evidence)
        production_admission_state = None
        repository_acquisition_state = None
        production_next_step = None
        persisted_repository_source = None
        if production_evidence_value.production_request:
            with self._turn_lock:
                admission_progress = self._production_admission_progress.get(
                    interaction_id
                )
                reality_provider = self._production_admission_reality_provider
            persisted_reality = (
                None
                if reality_provider is None
                else reality_provider(
                    interaction_id,
                    interaction.current_work_id if governed_revision is not None else None,
                )
            )
            if persisted_reality is not None:
                (
                    production_admission_state,
                    repository_acquisition_state,
                    production_next_step,
                    persisted_repository_source,
                ) = persisted_reality
                # Work Reality was read before the owner projection. A concurrent
                # binding may settle between those reads; do not combine its new
                # READY status with the earlier unbound revision in one DTO.
                if (repository_acquisition_state is RepositoryAcquisitionState.READY
                        and (governed_revision is None or governed_revision.repository_identity is None)):
                    repository_acquisition_state = RepositoryAcquisitionState.RUNNING
                    production_next_step = "Refresh the exact bound Work Reality."
            elif admission_progress is not None:
                (
                    production_admission_state,
                    repository_acquisition_state,
                    production_next_step,
                ) = admission_progress
            elif governed_revision is not None:
                production_admission_state = (
                    ProductionAdmissionExecutionState.WORK_CREATED
                )
                if governed_revision.repository_identity is not None:
                    repository_acquisition_state = (
                        RepositoryAcquisitionState.READY
                    )
                    production_next_step = (
                        "Continue Steering against the acquired repository Reality."
                    )
                elif production_evidence_value.repository_source:
                    repository_acquisition_state = (
                        RepositoryAcquisitionState.WAITING_FOR_AUTHORIZATION
                    )
                    production_next_step = (
                        "Authorize read access to the referenced repository; delivery "
                        "authority remains separate."
                    )
                else:
                    repository_acquisition_state = (
                        RepositoryAcquisitionState.WAITING_FOR_REPOSITORY_SOURCE
                    )
                    production_next_step = (
                        "Provide or bind the referenced repository source."
                    )
            else:
                production_admission_state = (
                    ProductionAdmissionExecutionState.READY_FOR_ADMISSION
                )
                repository_acquisition_state = (
                    RepositoryAcquisitionState.NOT_STARTED
                    if production_evidence_value.repository_source
                    else RepositoryAcquisitionState.WAITING_FOR_REPOSITORY_SOURCE
                    if production_evidence_value.repository_relevant
                    else None
                )
                production_next_step = "Execute governed Work admission."
        independent_observation = (
            self._repository_observation_provider(interaction_id)
            if self._repository_observation_provider is not None else None
        )
        if independent_observation is not None and governed_revision is None:
            repository_acquisition_state = (RepositoryAcquisitionState.FAILED_RETRYABLE
                if independent_observation['condition'] == 'BLOCKED'
                else RepositoryAcquisitionState(independent_observation['condition']))
            persisted_repository_source = independent_observation.get('source')
            production_next_step = (
                "Repository Reality is ready; production Work remains unadmitted."
                if independent_observation.get('condition') == 'READY'
                else independent_observation.get('human_message')
            )
        work_focus_history: list[UUID] = []
        for work_id in (
            *(record.work_focus_id for record in records),
            *(
                identity
                for transition in transitions
                for identity in (
                    transition.originating_work_id,
                    transition.target_work_id,
                )
            ),
            interaction.current_work_id,
        ):
            if work_id is not None and work_id not in work_focus_history:
                work_focus_history.append(work_id)
        satisfaction_state = (
            WorkSatisfactionState.NO_FOCUSED_WORK
            if active_context is None
            else active_context.satisfaction_state
        )
        return SharedUnderstanding(
            interaction=interaction,
            records=records,
            conversation_messages=messages,
            turns=turns,
            latest_assessment=latest,
            latest_assessment_current=assessment_current,
            human_said=tuple(
                item.content for item in records if item.actor is InteractionActor.HUMAN
            ),
            interpreted_motive=None if latest is None else latest.interpreted_motive,
            desired_outcome=None if latest is None else latest.desired_outcome,
            design_intent_frame=(
                None if latest is None else latest.design_intent_frame
            ),
            candidate_context=() if latest is None else latest.candidate_context,
            candidate_constraints=() if latest is None else latest.candidate_constraints,
            current_requests=() if latest is None else latest.current_requests,
            unresolved_material_questions=(
                () if latest is None else latest.unresolved_material_questions
            ),
            readiness=None if latest is None else latest.readiness,
            candidate_engineering_resource_id=(
                None if resource is None else resource.id
            ),
            candidate_repository_identity=(
                None if resource is None else resource.repository_identity
            ),
            candidate_repository_ref=(
                None if resource is None else resource.authoritative_ref
            ),
            candidate_scope_summary=(
                None
                if resource is None
                else (
                    "Long-lived Work authority envelope for "
                    f"{resource.repository_identity} at {resource.authoritative_ref}"
                )
            ),
            governed_work_id=(
                interaction.current_work_id if governed_revision is not None else None
            ),
            governed_revision=governed_revision,
            current_work_focus=(
                None
                if governed_revision is None
                else (
                    f"{governed_revision.motive} → {governed_revision.desired_outcome}"
                )
            ),
            focus_classification=(
                None if latest is None else latest.focus_classification
            ),
            impact_disposition=(
                None if latest is None else latest.impact_disposition
            ),
            candidate_change=(None if latest is None else latest.candidate_change),
            work_revision_admission_status=admission_status,
            active_cycle_work_revision_id=(
                None
                if active_context is None
                else active_context.active_cycle_work_revision_id
            ),
            active_cycle_impact_disposition=(
                None
                if latest is None or latest.basis_active_runtime_binding_id is None
                else latest.impact_disposition
            ),
            work_satisfaction_state=satisfaction_state,
            interaction_relationship_state=interaction.condition,
            work_focus_history=tuple(work_focus_history),
            latest_work_transition=latest_transition,
            new_work_formation_pending=bool(
                current_work is not None
                and current_work.condition is WorkCondition.PRE_WORK
            ),
            production_request_detected=production_evidence_value.production_request,
            repository_source=(
                persisted_repository_source or production_evidence_value.repository_source
            ),
            production_admission_state=production_admission_state,
            repository_acquisition_state=repository_acquisition_state,
            repository_observation=(
                {key: value for key, value in independent_observation.items()
                    if key not in {'request', 'technical_evidence'}}
                if independent_observation is not None else None
            ),
            production_next_step=production_next_step,
            selected_design_schema_identity=(
                interaction.selected_design_schema_identity
            ),
            selected_design_schema_version=(
                interaction.selected_design_schema_version
            ),
            design_schema_selection_rationale=(
                interaction.design_schema_selection_rationale
            ),
            **self._interaction_design_guidance(interaction),
        )

    @staticmethod
    def _interaction_design_guidance(interaction: Interaction) -> dict[str, str | None]:
        if interaction.selected_design_schema_identity is None:
            return {
                "design_stage": None,
                "design_next_focus": None,
                "design_focus_rationale": None,
                "design_facilitation_strategy": None,
                "design_progress_narrative": None,
            }
        schema = design_schema_by_identity(
            interaction.selected_design_schema_identity,
            interaction.selected_design_schema_version,
        )
        focus = schema.issues[0]
        return {
            "design_stage": focus.title,
            "design_next_focus": focus.objective,
            "design_focus_rationale": focus.why_it_matters,
            "design_facilitation_strategy": "CLARIFY",
            "design_progress_narrative": (
                f"Selected {schema.title} v{schema.version}. Current stage: "
                f"{focus.title}. 0 of {len(schema.issues)} design areas are resolved. "
                f"Next, {focus.objective.lower()}"
            ),
        }

    def pending_assessment_interactions(self) -> tuple[UUID, ...]:
        return tuple(
            projection.interaction.id
            for projection in self.list_interactions()
            if projection.records and projection.latest_assessment is None
        )

    def recover_pending_assessments(self) -> tuple[InteractionAssessment, ...]:
        return tuple(
            self.assess_current(interaction_id)
            for interaction_id in self.pending_assessment_interactions()
        )

    def _basis(self, interaction_id: UUID) -> InteractionInterpretationInput:
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            interaction = store.interaction(interaction_id)
            if interaction is None:
                raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
            records = store.records(interaction_id)
            # Presentation context does not alter the governed source fingerprint.
            messages = tuple(
                ConversationContextMessage(actor=message.actor.value, content=message.content)
                for message in store.messages(interaction_id, limit=8)
                if message.actor is InteractionActor.HUMAN
                or message.processing_status is InteractionTurnStatus.COMPLETED
            )
            prior = store.latest_assessment(interaction_id)
            semantic_history = tuple(assessment.semantic_ir for assessment in
                store.assessments(interaction_id) if assessment.semantic_ir is not None)[-8:]
            previous_contract = store.latest_response_contract(interaction_id, completed_only=True)
            active_context = self._active_work_context(uow.session, interaction)
        if not records:
            raise InteractionInvariantViolation("Interaction has no assessment basis")
        fingerprint = interaction_basis_fingerprint(
            interaction,
            records,
            active_context,
        )
        if prior is not None and prior.basis_fingerprint == fingerprint:
            prior = None
        return InteractionInterpretationInput(
            interaction=interaction,
            records=records,
            prior_assessment=prior,
            governed_semantic_history=semantic_history,
            active_work_context=active_context,
            basis_fingerprint=fingerprint,
            recent_conversation_messages=messages,
            previous_response_contract=previous_contract,
            observed_reality=(*self._semantic_owner_observations(interaction_id),
                *(observation for provider in self._intent_observation_providers for observation in provider(interaction_id))),
        )

    @staticmethod
    def _active_work_context(session, interaction: Interaction) -> ActiveWorkInterpretationContext | None:
        if interaction.current_work_id is None:
            return None
        product = ProductStore(session)
        work = product.work(interaction.current_work_id)
        if work is None:
            raise InteractionInvariantViolation("Focused Work does not exist")
        if work.condition is WorkCondition.PRE_WORK:
            return None
        runtime = RuntimeStore(session)
        revision = product.current_work_reality_revision(interaction.current_work_id)
        scope = product.scope_for_work(interaction.current_work_id)
        if revision is None or scope is None:
            raise InteractionInvariantViolation(
                "Focused Work lacks exact Work Reality Revision or Engineering Scope"
            )
        steering = SteeringStore(session)
        plan = steering.plan_for_work(interaction.current_work_id)
        active_revision = None if plan is None else steering.active_revision(plan.id)
        current_step = None
        if active_revision is not None:
            current_step = next(
                (
                    step
                    for step in steering.steps(active_revision.id)
                    if step.state.value == "CURRENT"
                ),
                None,
            )
        binding = product.runtime_binding(interaction.current_work_id)
        active_binding = (
            binding
            if binding is not None
            and binding.condition is ProductionCycleBindingCondition.ADMITTED
            else None
        )
        binding_summary = (
            None if binding is None else product.runtime_summary(binding)
        )
        latest_decision = (
            None
            if active_revision is None
            else steering.latest_decision(active_revision.id)
        )
        currently_satisfied = bool(
            current_step is not None
            and current_step.type is SteeringStepType.COMPLETE
            and latest_decision is not None
            and latest_decision.steering_outcome is SteeringOutcome.COMPLETE
            and binding is not None
            and binding.work_reality_revision_id == revision.id
            and binding_summary is not None
            and binding_summary.runtime_commit_id is not None
            and binding_summary.completion_outcome == "PRODUCED"
            and binding_summary.verification_results
            and all(
                result == "PASS"
                for result in binding_summary.verification_results
            )
            and binding_summary.integration_state == "CONVERGED"
            and any(
                reference.kind is RealityReferenceKind.RUNTIME_COMMIT
                and reference.identity == binding_summary.runtime_commit_id
                for reference in latest_decision.reality_refs
            )
        )
        references = [
            f"WORK_REALITY_REVISION:{revision.id}",
            f"ENGINEERING_SCOPE:{scope.id}",
        ]
        if active_revision is not None:
            references.append(f"STEERING_PLAN_REVISION:{active_revision.id}")
        if current_step is not None:
            references.append(f"STEERING_STEP:{current_step.id}")
        if active_binding is not None:
            references.append(f"PRODUCTION_CYCLE:{active_binding.id}")
            summary = product.runtime_summary(active_binding)
            for kind, identity in (
                ("COMPLETION", summary.completion_id),
                ("RUNTIME_COMMIT", summary.runtime_commit_id),
            ):
                if identity is not None:
                    references.append(f"{kind}:{identity}")
            if summary.proposed_snapshot_id is not None:
                references.extend(
                    f"VERIFICATION:{record.id}"
                    for record in runtime.verification_records_for_snapshot(
                        summary.proposed_snapshot_id
                    )
                )
        elif binding is not None and binding_summary is not None:
            references.append(f"PRODUCTION_CYCLE:{binding.id}")
            for kind, identity in (
                ("COMPLETION", binding_summary.completion_id),
                ("RUNTIME_COMMIT", binding_summary.runtime_commit_id),
            ):
                if identity is not None:
                    references.append(f"{kind}:{identity}")
            if binding_summary.proposed_snapshot_id is not None:
                references.extend(
                    f"VERIFICATION:{record.id}"
                    for record in runtime.verification_records_for_snapshot(
                        binding_summary.proposed_snapshot_id
                    )
                )
        return ActiveWorkInterpretationContext(
            work_revision=revision,
            engineering_scope_fingerprint=scope.fingerprint,
            steering_plan_revision_id=(
                None if active_revision is None else active_revision.id
            ),
            steering_plan_revision_number=(
                None if active_revision is None else active_revision.revision_number
            ),
            current_steering_step_id=(
                None if current_step is None else current_step.id
            ),
            current_steering_step_type=(
                None if current_step is None else current_step.type.value
            ),
            pending_human_question=(latest_decision.reason if latest_decision is not None
                and latest_decision.human_required and current_step is not None
                and latest_decision.current_step_id == current_step.id
                and current_step.type in {SteeringStepType.DESIGN, SteeringStepType.REFINE}
                else None),
            active_production_binding_id=(
                None if active_binding is None else active_binding.id
            ),
            active_cycle_work_revision_id=(
                None
                if active_binding is None
                else active_binding.work_reality_revision_id
            ),
            active_cycle_number=(
                None if active_binding is None else active_binding.cycle_number
            ),
            relevant_reality_references=tuple(references),
            satisfaction_state=(
                WorkSatisfactionState.CURRENTLY_SATISFIED
                if currently_satisfied
                else WorkSatisfactionState.IN_PROGRESS
            ),
        )

    @staticmethod
    def _with_design_intent_frame(
        candidate: InteractionAssessmentCandidate,
        *,
        prior_assessment: InteractionAssessment | None,
        latest_human_input: str,
    ) -> InteractionAssessmentCandidate:
        frame = candidate.design_intent_frame
        if (
            frame is None
            and prior_assessment is not None
            and (
                candidate.interpreted_motive is None
                or candidate.interpreted_motive == prior_assessment.interpreted_motive
            )
        ):
            frame = prior_assessment.design_intent_frame
        if frame is None and candidate.semantic_intent is None and candidate.interpreted_motive:
            frame = frame_design_intent_text(
                candidate.interpreted_motive or latest_human_input,
                desired_outcome=candidate.desired_outcome,
            )
        if frame is None:
            return candidate
        questions = candidate.unresolved_material_questions
        if frame.object_type is DesignObjectType.UNKNOWN:
            questions = tuple(dict.fromkeys((*questions, *frame.ambiguities)))
        return candidate.model_copy(
            update={
                "design_intent_frame": frame,
                "unresolved_material_questions": questions,
            }
        )

    @staticmethod
    def _normalize_active_candidate(
        candidate: InteractionAssessmentCandidate,
        active: ActiveWorkInterpretationContext | None,
        engineering_semantic_facts: tuple[EngineeringSemanticFact, ...] = (),
        *,
        latest_human_input: str | None = None,
        latest_human_record_id: UUID | None = None,
        prior_production_references: tuple[str, ...] = (),
    ) -> tuple[
        WorkFocusClassification | None,
        WorkImpactDisposition | None,
        WorkEvolutionCandidateChange | None,
    ]:
        if active is None:
            return None, None, None
        if candidate.turn_intent is ConversationTurnIntent.DISAGREEMENT:
            # An objection requests assessment of a judgment. It cannot become a
            # Work change because a provider mislabeled its expression CORRECT.
            return WorkFocusClassification.SIDE_QUESTION, WorkImpactDisposition.NO_GOVERNED_CHANGE, None
        focus = candidate.focus_classification or WorkFocusClassification.ON_TOPIC
        if focus in {
            WorkFocusClassification.MATERIAL_BRANCH,
            WorkFocusClassification.UNRELATED_NEW_DEMAND,
        }:
            return focus, WorkImpactDisposition.NEW_WORK_RECOMMENDED, None
        # Response posture describes how Watt should speak, not whether the
        # Human has changed the Work. A provider can choose DESIGN while also
        # recognizing an exact, explicit request to modify the current Work.
        # Require a new request grounded in the latest Human record so an
        # advisory discussion cannot silently become governed change. The
        # provider may preserve the wording or paraphrase it.
        new_requests = tuple(
            request for request in candidate.current_requests
            if request not in active.work_revision.requests
        )
        latest_request_meaning = any(
            meaning.kind in {
                InterpretationMeaningKind.REQUEST,
                InterpretationMeaningKind.OBJECTIVE_OR_SCOPE_CHANGE,
            }
            and (
                latest_human_record_id is None
                or latest_human_record_id in meaning.source_record_ids
            )
            for meaning in candidate.meanings
        )
        explicit_current_work_change = bool(candidate.semantic_intent and any(
            item.production is not None and item.production.current and (latest_human_record_id is None or any(
                source.source_record_id == latest_human_record_id for source in item.provenance))
            for item in candidate.semantic_intent.items))
        decision_input = bool(new_requests and candidate.turn_intent is ConversationTurnIntent.HUMAN_DECISION
            and any(meaning.kind is InterpretationMeaningKind.DECISION_INPUT
                and latest_human_record_id in meaning.source_record_ids
                for meaning in candidate.meanings))
        typed_scope_answer = bool(candidate.semantic_intent
            and candidate.semantic_intent.items
            and all(item.kind in {SemanticKind.CONSTRAINT, SemanticKind.FACT}
                for item in candidate.semantic_intent.items)
            and any(item.kind is SemanticKind.CONSTRAINT and any(
                source.source_record_id == latest_human_record_id
                for source in item.provenance)
                for item in candidate.semantic_intent.items)
            and (any(fact.relation is SemanticRelation.SCOPE
                and latest_human_record_id in fact.provenance.source_record_ids
                for fact in current_semantic_facts(engineering_semantic_facts))
                or WorkInteractionService._constraint_refers_to_current_production(
                    candidate.semantic_intent, latest_human_record_id,
                    prior_production_references))
            and candidate.candidate_constraints != active.work_revision.constraints
            and not candidate.unresolved_material_questions)
        governed_question_answer = bool(
            getattr(active, "pending_human_question", None)
            and latest_human_input and (decision_input or typed_scope_answer)
            and not any(item.kind in {SemanticKind.QUESTION, SemanticKind.STATUS_QUERY}
                for item in (candidate.semantic_intent.items if candidate.semantic_intent else ()))
        )
        explicit_current_work_change = explicit_current_work_change or governed_question_answer
        if candidate.response_intent is not None and candidate.response_intent.interaction_mode in {
            InteractionMode.EXPLORE, InteractionMode.ANALYZE, InteractionMode.DESIGN,
            InteractionMode.DECIDE, InteractionMode.ANSWER, InteractionMode.STATUS,
        } and not explicit_current_work_change:
            return WorkFocusClassification.SIDE_QUESTION, WorkImpactDisposition.NO_GOVERNED_CHANGE, None
        if focus in {
            WorkFocusClassification.RELEVANT_EXPLORATION,
            WorkFocusClassification.SIDE_QUESTION,
        } and not explicit_current_work_change:
            return focus, WorkImpactDisposition.NO_GOVERNED_CHANGE, None
        if explicit_current_work_change:
            focus = WorkFocusClassification.ON_TOPIC

        current = active.work_revision
        goals = tuple(item.production for item in candidate.semantic_intent.items
            if item.production and item.production.current) if candidate.semantic_intent else ()
        bounded_continuation = bool(goals) and all(goal.bounded_change and not goal.systemic_design for goal in goals)
        correction = bool(candidate.semantic_intent and any(item.kind is SemanticKind.CORRECTION for item in candidate.semantic_intent.items))
        motive = (current.motive if bounded_continuation and not correction else candidate.interpreted_motive or current.motive).strip()
        outcome = ("; ".join(dict.fromkeys((current.desired_outcome, candidate.desired_outcome)))
            if bounded_continuation and candidate.desired_outcome else candidate.desired_outcome or current.desired_outcome).strip()
        context = candidate.candidate_context or current.context_facts
        constraints = candidate.candidate_constraints or current.constraints
        requests = tuple(dict.fromkeys((*current.requests, *candidate.current_requests))) if bounded_continuation else candidate.current_requests or current.requests
        values = {
            "motive": motive,
            "desired_outcome": outcome,
            "context_facts": tuple(context),
            "constraints": tuple(constraints),
            "requests": tuple(requests),
            "semantic_facts": tuple(engineering_semantic_facts),
        }
        changed = tuple(
            name
            for name, before in (
                ("motive", current.motive),
                ("desired_outcome", current.desired_outcome),
                ("context_facts", current.context_facts),
                ("constraints", current.constraints),
                ("requests", current.requests),
                (
                    "semantic_facts",
                    getattr(current, "engineering_semantic_facts", ()),
                ),
            )
            if values[name] != before
        )
        if not changed:
            return focus, WorkImpactDisposition.NO_GOVERNED_CHANGE, None
        scope_change = "constraints" in changed or any(
            meaning.kind is InterpretationMeaningKind.OBJECTIVE_OR_SCOPE_CHANGE
            for meaning in candidate.meanings
        ) or (
            "semantic_facts" in changed
            and any(
                fact.relation is SemanticRelation.SCOPE
                for fact in current_semantic_facts(engineering_semantic_facts)
            )
        )
        impact = candidate.impact_disposition
        if impact in {
            None,
            WorkImpactDisposition.NO_GOVERNED_CHANGE,
            WorkImpactDisposition.NEW_WORK_RECOMMENDED,
        }:
            impact = (
                WorkImpactDisposition.CURRENT_RESULT_MAY_BE_INSUFFICIENT
                if (
                    active.active_production_binding_id is not None
                    or active.satisfaction_state
                    is WorkSatisfactionState.CURRENTLY_SATISFIED
                )
                else WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED
            )
        return (
            focus,
            impact,
            WorkEvolutionCandidateChange(
                changed_fields=changed,
                motive=motive,
                desired_outcome=outcome,
                context_facts=tuple(context),
                constraints=tuple(constraints),
                requests=tuple(requests),
                semantic_facts=tuple(engineering_semantic_facts),
                scope_change_required=scope_change,
            ),
        )

    @staticmethod
    def _constraint_refers_to_current_production(
        semantic_ir, latest_human_record_id: UUID | None,
        prior_production_references: tuple[str, ...],
    ) -> bool:
        if semantic_ir is None or latest_human_record_id is None:
            return False
        production_refs = set(prior_production_references)
        constraints = {item.item_id for item in semantic_ir.items
            if item.kind is SemanticKind.CONSTRAINT and any(
                source.source_record_id == latest_human_record_id
                for source in item.provenance)}
        return bool(production_refs and constraints and any(
            clause.source_record_id == latest_human_record_id
            and constraints.intersection(clause.semantic_item_ids)
            and production_refs.intersection(clause.refers_to)
            for clause in semantic_ir.clauses))

    @staticmethod
    def _normalize_supporting_references(values: tuple[str, ...]) -> tuple[str, ...]:
        allowed = {"VERIFICATION", "RUNTIME_FACT", "COMPLETION", "ENGINEERING_FINDING"}
        normalized: list[str] = []
        for raw in values:
            value = raw.strip()
            if not value:
                continue
            kind, separator, identity = value.partition(":")
            if separator != ":" or kind not in allowed:
                raise InteractionInvariantViolation(
                    "Supporting Reality reference must use an allowed typed identity"
                )
            try:
                UUID(identity)
            except ValueError as error:
                raise InteractionInvariantViolation(
                    "Supporting Reality reference identity must be a UUID"
                ) from error
            normalized.append(f"{kind}:{identity}")
        return tuple(dict.fromkeys(normalized))

    @staticmethod
    def _revision_admission_status(
        assessment: InteractionAssessment | None,
        admitted: bool,
        decision_types: tuple[str, ...],
    ) -> WorkRevisionAdmissionStatus:
        if assessment is None or assessment.basis_work_revision_id is None:
            return WorkRevisionAdmissionStatus.NOT_APPLICABLE
        if admitted:
            return WorkRevisionAdmissionStatus.ADMITTED
        if assessment.impact_disposition is WorkImpactDisposition.NEW_WORK_RECOMMENDED:
            return WorkRevisionAdmissionStatus.NEW_WORK_RECOMMENDED
        if assessment.candidate_change is None:
            return WorkRevisionAdmissionStatus.NOT_APPLICABLE
        if "REJECT_WORK_REALITY_REVISION" in decision_types:
            return WorkRevisionAdmissionStatus.REJECTED
        if "REQUEST_WORK_REALITY_REFINEMENT" in decision_types:
            return WorkRevisionAdmissionStatus.REFINEMENT_REQUESTED
        return WorkRevisionAdmissionStatus.PENDING_HUMAN

    @staticmethod
    def _evaluate_readiness(
        candidate: InteractionAssessmentCandidate,
        basis_fingerprint: str,
        *,
        governance_candidate: GovernanceCandidateKind | None = None,
        progressive_semantics: ProgressiveSemanticStructure | None = None,
    ) -> WorkAdmissionReadiness:
        if governance_candidate is GovernanceCandidateKind.CONVERSATION_ONLY:
            return WorkAdmissionReadiness(
                status=WorkAdmissionReadinessStatus.NOT_READY,
                profile=READINESS_PROFILE,
                profile_version=READINESS_PROFILE_VERSION,
                satisfied_requirements=(),
                missing_information=("WORK_MOTIVE",),
                unresolved_material_questions=(),
                reasons=(
                    "This Turn is an informational conversation and does not establish a Work motive.",
                ),
                basis_fingerprint=basis_fingerprint,
            )
        missing: list[str] = []
        satisfied: list[str] = []
        if candidate.interpreted_motive and candidate.interpreted_motive.strip():
            satisfied.append("MOTIVE")
        else:
            missing.append("MOTIVE")
        if candidate.desired_outcome and candidate.desired_outcome.strip():
            satisfied.append("DESIRED_OUTCOME")
        else:
            missing.append("DESIRED_OUTCOME")
        questions = tuple(
            value.strip()
            for value in candidate.unresolved_material_questions
            if value.strip()
        )

        if progressive_semantics is not None:
            # Admission concerns the next governed step, not every detail of the
            # eventual artifact. Keep deferred questions in the assessment and
            # progressive evidence; only current-step blockers prevent admission.
            blocking = {
                evaluation.question for evaluation in progressive_semantics.questions
                if evaluation.blocks_next_governed_step
            }
            questions = tuple(dict.fromkeys((
                *(question for question in questions if question in blocking),
                *(evaluation.question for evaluation in progressive_semantics.questions
                  if evaluation.blocks_next_governed_step and evaluation.question not in questions),
            )))
        ready = not missing and not questions
        reasons = (
            ("Motive and desired outcome are clear enough to form governed Work.",)
            if ready
            else ("Material Work-admission information remains unresolved.",)
        )
        return WorkAdmissionReadiness(
            status=(
                WorkAdmissionReadinessStatus.READY
                if ready
                else WorkAdmissionReadinessStatus.NOT_READY
            ),
            profile=READINESS_PROFILE,
            profile_version=READINESS_PROFILE_VERSION,
            satisfied_requirements=tuple(satisfied),
            missing_information=tuple(missing),
            unresolved_material_questions=questions,
            reasons=reasons,
            basis_fingerprint=basis_fingerprint,
        )

    @staticmethod
    def _canonicalize_explicit_branch_facts(
        candidate: InteractionAssessmentCandidate,
        latest: InteractionRecord,
    ) -> InteractionAssessmentCandidate:
        """Normalize Provider branch vocabulary at binding, never at execution."""

        normalized: list[EngineeringSemanticFactCandidate] = []
        explicit_branch = False
        from spg.domain.interaction_actions import CanonicalOperation, ActionSpeechAct
        targets = {action.target_branch for action in (candidate.action_candidates or ())
            if action.operation is CanonicalOperation.CREATE_AND_SWITCH_BRANCH
            and action.speech_act is ActionSpeechAct.EXPLICIT_REQUEST
            and action.confidence >= .8 and action.source_record_id == latest.id}
        for fact in candidate.semantic_fact_candidates:
            if (
                fact.subject in BRANCH_EXTRACTION_SUBJECTS
                and isinstance(fact.value, str)
                and latest.id in fact.source_record_ids
                and fact.value in targets
            ):
                normalized.append(fact.model_copy(update={
                    "subject": "repository.branch_name",
                    "relation": SemanticRelation.REFERENCE,
                    "qualifiers": {"state": "to_be_created"},
                    "authority": SemanticFactAuthority.HUMAN_EXPLICIT,
                    "epistemic_status": SemanticEpistemicStatus.CONFIRMED,
                    "source_record_ids": (latest.id,),
                    "source_text": latest.content,
                    "role_origin": SemanticRoleOrigin.EXPLICIT,
                }))
                explicit_branch = True
            else:
                normalized.append(fact)
        for target in targets:
            if not any(fact.subject == "repository.branch_name" and fact.value == target
                       for fact in normalized):
                normalized.append(EngineeringSemanticFactCandidate(
                    candidate_id="canonical-branch-target", subject="repository.branch_name",
                    relation=SemanticRelation.REFERENCE, value=target,
                    qualifiers={"state": "to_be_created"},
                    authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                    epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                    source_record_ids=(latest.id,), source_text=latest.content,
                    role_origin=SemanticRoleOrigin.EXPLICIT))
            explicit_branch = True
        if explicit_branch and not any(
            fact.subject == "repository.branch_action"
            and fact.value == "创建新分支"
            and fact.authority is SemanticFactAuthority.HUMAN_EXPLICIT
            for fact in normalized
        ):
            normalized.append(EngineeringSemanticFactCandidate(
                candidate_id="human-new-branch-action",
                subject="repository.branch_action",
                relation=SemanticRelation.EQUALITY,
                value="创建新分支",
                authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                source_record_ids=(latest.id,),
                source_text=latest.content,
                role_origin=SemanticRoleOrigin.EXPLICIT,
            ))
        return candidate.model_copy(update={"semantic_fact_candidates": tuple(normalized)})

    @staticmethod
    def _explicit_branch_candidate(
        basis: InteractionInterpretationInput, branch_name: str,
    ) -> InteractionAssessmentCandidate:
        active = basis.active_work_context
        assert active is not None
        revision = active.work_revision
        latest = basis.records[-1]
        return InteractionAssessmentCandidate(
            turn_intent=ConversationTurnIntent.ACTION_REQUEST,
            interpreted_motive=revision.motive,
            desired_outcome=revision.desired_outcome,
            candidate_context=revision.context_facts,
            candidate_constraints=revision.constraints,
            current_requests=tuple(dict.fromkeys((
                *revision.requests, latest.content,
            ))),
            semantic_fact_candidates=(EngineeringSemanticFactCandidate(
                candidate_id="human-new-branch-command",
                subject="repository.branch_name",
                relation=SemanticRelation.REFERENCE,
                value=branch_name,
                qualifiers={"state": "to_be_created"},
                authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                source_record_ids=(latest.id,),
                source_text=latest.content,
                role_origin=SemanticRoleOrigin.EXPLICIT,
            ), EngineeringSemanticFactCandidate(
                candidate_id="human-new-branch-action",
                subject="repository.branch_action",
                relation=SemanticRelation.EQUALITY,
                value="创建新分支",
                authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                source_record_ids=(latest.id,),
                source_text=latest.content,
                role_origin=SemanticRoleOrigin.EXPLICIT,
            )),
            focus_classification=WorkFocusClassification.ON_TOPIC,
            impact_disposition=WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED,
            natural_response=f"准备创建本地分支 {branch_name}。",
            provider_identity="watt-native:explicit-branch-command",
        )

    def _work_reality_status_candidate(
        self, basis: InteractionInterpretationInput, *, semantic_ir=None
    ) -> InteractionAssessmentCandidate:
        active = basis.active_work_context
        assert active is not None
        revision = active.work_revision
        with self.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            steering = SteeringStore(uow.session)
            plan = steering.plan_for_work(revision.work_id)
            plan_revision = None if plan is None else steering.active_revision(plan.id)
            current = next((step for step in steering.steps(plan_revision.id)
                            if step.state.value == "CURRENT"), None) if plan_revision else None
            binding = product.runtime_binding(revision.work_id)
            summary = None if binding is None else product.runtime_summary(binding)
            decision = None if plan_revision is None else steering.latest_decision(plan_revision.id)
            semantic_result = (
                None
                if decision is None
                else steering.latest_semantic_result_for_step(decision.current_step_id)
            )
            queue_entries = NativeExecutionStore(uow.session).list_queue(work_id=revision.work_id)
            history_query = bool(semantic_ir and any(item.subject == "WORK_HISTORY" for item in semantic_ir.items))
            commit = (RuntimeStore(uow.session).runtime_commit(summary.runtime_commit_id)
                      if history_query and summary is not None and summary.runtime_commit_id
                      else None)
            observation = (RuntimeStore(uow.session).repository_observation_by_id(summary.observation_id)
                           if history_query and summary is not None and summary.observation_id
                           else None)
        phase = {"DESIGN": "整理解决方案", "REFINE": "澄清当前步骤", "PRODUCE": "生产", "VERIFY_ACCEPT": "验证与验收", "COMPLETE": "完成"}.get(
            None if current is None else current.type.value, "等待下一步")
        if summary is not None and summary.runtime_commit_id is not None:
            conclusion = "当前 Work 已形成受信任的运行结果，正在评估后续步骤。"
            limitation = ""
        elif binding is not None:
            conclusion = "当前 Work 已进入生产周期。"
            limitation = ""
        else:
            conclusion = "当前 Work 尚未进入生产执行。"
            limitation = "重要限制：目前还没有可报告的生产或验证结果。"
        progress = (
            f"关键进展：目前处于「{phase}」；"
            f"{current.objective if current else '尚未形成当前执行步骤'}。"
        )
        if (
            summary is not None
            and summary.candidate_id is not None
            and summary.authorization_id is None
        ):
            next_step = "下一步由你审阅并授权候选结果；授权前不会集成。"
        elif (
            decision is not None
            and decision.human_required
            and current is not None
            and decision.current_step_id == current.id
        ):
            if semantic_result is not None and semantic_result.unresolved_questions:
                next_step = "下一步请在 Actions 中查看并回答当前设计问题。"
            elif decision.attention_reason is SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED:
                next_step = "下一步由你审阅当前生产提案。"
            else:
                next_step = "下一步请在 Actions 中处理当前 Human 决策。"
        else:
            next_step = (
                "当前没有需要你处理的事项；下一步由 Watt 按当前步骤继续推进。"
                if current is not None
                else "当前没有需要你处理的事项；下一步由 Watt 形成可执行步骤。"
            )
        answer = conclusion + progress + next_step + limitation
        diagnose = bool(semantic_ir and any(item.subject == "WORK_DIAGNOSTIC" for item in semantic_ir.items))
        current_queue = tuple(item for item in queue_entries
                              if binding is not None and item.pwu_id == binding.work_unit_id
                              and (summary is None or summary.attempt_id is None
                                   or item.attempt_id == summary.attempt_id))
        latest_queue = max(current_queue, key=lambda item: item.enqueued_at, default=None)
        if latest_queue is not None:
            queue_fact = {
                "QUEUED": "当前执行已进入队列。",
                "WAITING_RESOURCE": "当前执行正在等待可用资源。",
                "WAITING_HUMAN": "当前执行正在等待你的决定。",
                "ALLOCATED": "当前执行已分配资源，正在准备启动。",
                "EXECUTING": "当前执行正在进行。",
                "CHECKPOINTED": "当前执行已保存进度，正在等待继续。",
                "RETURNED_TO_QUEUE": "当前执行已返回队列，正在等待再次调度。",
                "COMPLETED": "最近一次执行已经完成。",
                "CANCELLED": "最近一次执行已经取消。",
            }.get(latest_queue.condition.value, "当前执行状态已经更新。")
            reason = latest_queue.wait_reason
            if reason:
                queue_fact += f"关键证据：系统记录的原因是“{reason}”。"
            elif diagnose:
                queue_fact += (
                    "重要限制：现有记录没有说明原因，暂时不能确定根因。"
                    "下一步由 Watt 核对调度和执行容量。"
                )
            answer = (
                f"当前结论：{queue_fact}{next_step}"
                if diagnose
                else f"当前结论：{queue_fact}{progress}{next_step}{limitation}"
            )
        elif diagnose:
            answer = (
                "当前结论：当前生产周期没有对应的执行队列记录。"
                "重要限制：现有证据不足以确认你描述的原因。"
                + next_step
            )
        if history_query:
            paths = tuple(change.repository_relative_path for change in observation.changes) if observation else (
                summary.artifact_paths if summary is not None else ())
            answer = f"当前聚焦 Work {revision.work_id} 的持久化历史："
            if paths:
                answer += "独立观察到变更文件：" + "、".join(paths) + "。"
            else:
                answer += "现有记录没有独立观察到的文件变更，不能据此声称已修改源码。"
            if summary is not None and summary.candidate_id is not None:
                answer += f"候选结果：{summary.candidate_id}；验证结果：{', '.join(summary.verification_results) or '尚无'}。"
            if commit is not None:
                answer += (f"已接受并形成本地可信提交 {commit.id}；"
                           f"源提交 {commit.expected_source_repository_revision} → {commit.repository_revision}；"
                           f"文件树 {commit.repository_tree_identity}。")
            answer += "此查询只读取历史，没有创建生产 Work；本地验收不代表已授权或执行远端交付。"
        return InteractionAssessmentCandidate(
            turn_intent=ConversationTurnIntent.DIRECT_QUESTION,
            interpreted_motive=revision.motive,
            desired_outcome=revision.desired_outcome,
            candidate_context=revision.context_facts,
            candidate_constraints=revision.constraints,
            current_requests=revision.requests,
            focus_classification=WorkFocusClassification.SIDE_QUESTION,
            impact_disposition=WorkImpactDisposition.NO_GOVERNED_CHANGE,
            natural_response=answer,
            response_intent=ResponseIntent(
                interaction_mode=InteractionMode.DIAGNOSE if diagnose else InteractionMode.STATUS,
                rationale="Watt-owned read-only Work/Runtime projection.",
                judgment_stance=JudgmentStance.FACT,
                judgment_basis=active.relevant_reality_references,
            ),
            provider_identity="watt-native:work-reality-query",
        )
