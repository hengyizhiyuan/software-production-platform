from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
import os
from pathlib import Path
import subprocess
from threading import RLock
import time
from types import SimpleNamespace
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, inspect, select, text

from spg.api import create_http_application
from spg.application.interaction import (
    DeterministicWorkInteractionCapability,
    WorkInteractionService,
    _repository_branch_status_answer,
)
from spg.application.guided_design import GuidedDesignApplicationService
from spg.application.assets import RepositoryAssetService, canonical_fingerprint
from spg.application.native_git_operations import NativeGitOperationRunner
from spg.application.connectors import ConnectorResolver
from spg.application.native_production_environment import NativeProductionEnvironmentRuntime
from spg.infrastructure.production_environment import ContainerProductionEnvironmentProvider, DockerCliContainerRuntime
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.persistence.steering_store import SteeringStore
from spg.application.orchestration import OrchestrationStopReason, ProductionOrchestrator
from spg.application.post_admission import WorkPostAdmissionService
from spg.application.production_admission import ProductionAdmissionTrigger
from spg.application.steering_driver import PlanSteeringDriver
from spg.application.runtime import RuntimeService
from spg.application.semantic_steps import SemanticStepApplicationService
from spg.application.steering import SteeringApplicationService
from spg.application.steering_decision import (
    DeterministicPlanSteeringCapability,
    PlanFrameAssembler,
    SteeringDecisionApplicationService,
)
from spg.application.steering_bootstrap import SteeringBootstrapService
from spg.application.steering_production import SteeringProductionService
from spg.application.work import WorkApplicationService
from spg.domain.change import ProductionTargetKind
from spg.domain.assets import (
    AssetScopeAdmissionRequest,
    RepositoryAcquisitionFailure,
    RepositoryAcquisitionFailureCategory,
    RepositoryIntakeRequest,
)
from spg.domain.conversation import ConversationTurnIntent
from spg.domain.connectors import (
    CapabilityRequirement, CapabilityScope, ConnectorAvailability,
    ConnectorMaturity, ExecutableCapability, SideEffectLevel,
)
from spg.domain.guided_design import DesignIssueState, DesignReadinessState
from spg.domain.execution import ProviderReportedOutcome
from spg.domain.engineering_semantics import (
    EngineeringSemanticFactCandidate,
    NeutralExtractionKind,
    NeutralSemanticExtractionCandidate,
    SemanticEpistemicStatus,
    SemanticFactAuthority,
    SemanticRelation,
    SemanticRoleOrigin,
    current_semantic_facts,
)
from spg.domain.interaction import (
    InteractionActor,
    InteractionAssessmentCandidate,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InteractionTurnStatus,
    InterpretationMeaning,
    InterpretationMeaningKind,
    ProductionAdmissionExecutionState,
    RepositoryAcquisitionState,
    WorkAdmissionReadinessStatus,
    WorkFocusClassification,
    WorkImpactDisposition,
    WorkRevisionAdmissionStatus,
    WorkSatisfactionState,
    WorkTransitionChoice,
)
from spg.domain.planning import (
    OnePwuFitClassification,
    PlannedArtifactOperation,
    ProductionPlanArtifactTarget,
    ProductionPlanProposal,
    ProductionPlanStep,
)
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import (
    AttentionAction,
    AttentionKind,
    AttentionResolutionRequest,
    ArtifactTargetConfidence,
    ArtifactTargetOperation,
    EngineeringContextReference,
    ProductInvariantViolation,
    ProductionCycleBindingCondition,
    WorkMode,
    WorkStatus,
)
from spg.domain.runtime import (
    BootstrapRequest,
    CompletionContract,
    InitialRunRequest,
    ProductionHorizon,
)
from spg.domain.runtime_activation import RuntimeActivationProjection, RuntimeActivationState
from spg.domain.native_execution import AttemptTerminalOutcome, QueueCondition
from spg.domain.wic_response import WicRuntimeMode
from spg.domain.steering import (
    AdmitSteeringDecisionRequest,
    CreateSteeringPlanRequest,
    RealityReference,
    RealityReferenceKind,
    SteeringOutcome,
    SteeringRecordNotFound,
    SteeringStepSpec,
    SteeringStepState,
    SteeringStepType,
    TransitionSteeringStepRequest,
    SemanticProductionProposal,
    SemanticResultKind,
    SemanticStepInput,
    SemanticStepResultCandidate,
    SteeringAuthorityAssessment,
    SteeringActionType,
)
from spg.infrastructure.persistence import Database, product_tables, runtime_tables
from spg.infrastructure.persistence.product_schema import (
    engineering_resource_bindings,
    engineering_scopes,
    interaction_records,
    interaction_work_transitions,
    product_interactions,
    product_works,
    work_runtime_bindings,
    work_reality_revisions,
)
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_schema import (
    baseline_candidates,
    completion_evaluations,
    execution_attempts,
    execution_dispatches,
    governance_records,
    human_authorizations,
    materialized_execution_inputs,
    production_admissibility_records,
    production_runs,
    production_work_units,
    proposed_repository_snapshots,
    provider_execution_reports,
    repository_integration_effects,
    repository_observations,
    runtime_commits,
)
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.steering_schema import steering_plans
from spg.infrastructure.persistence.guided_design_store import GuidedDesignStore
from spg.infrastructure.persistence.guided_design_schema import (
    guided_design_agenda_revisions,
    guided_design_processes,
)
from spg.providers.deterministic_executor import (
    DeterministicExecutionSpecification,
    DeterministicFileOperation,
    DeterministicFileOperationType,
    DeterministicTestExecutor,
)
from spg.providers.deterministic_verifier import DeterministicVerificationProvider
from spg.providers.codex_semantic import CodexSdkSemanticStepCapability
from spg.domain.verification import (
    VerificationCapabilityRequest,
    VerificationResultValue,
)


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALL_TABLE_NAMES = {table.name for table in (*product_tables, *runtime_tables)}
PRODUCTION_TABLES = (
    production_runs,
    production_work_units,
    execution_attempts,
    execution_dispatches,
    provider_execution_reports,
    repository_observations,
    proposed_repository_snapshots,
    completion_evaluations,
    production_admissibility_records,
    baseline_candidates,
    human_authorizations,
    repository_integration_effects,
    runtime_commits,
    work_runtime_bindings,
)


class _ReadyCapability:
    def interpret(
        self, basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        return InteractionAssessmentCandidate(
            interpreted_motive="Improve Watt execution progress observability",
            desired_outcome="Developers can see the current phase, progress, and blockers.",
            candidate_context=("Automatic execution can be long-running.",),
            candidate_constraints=("Do not redesign the whole UI.",),
            current_requests=(basis.records[-1].content,),
            natural_response="The understanding is ready for Human Work admission.",
            provider_identity="test:wic-slice-2",
        )


class _CourseScheduleSemanticCapability:
    def __init__(self, *, correction: bool = False) -> None:
        self.correction = correction

    def interpret(
        self, basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        latest = basis.records[-1]
        active = basis.active_work_context
        if self.correction:
            assert active is not None
            revision = active.work_revision
            source_text = "不是，我刚才的意思改一下，要 8 列 5 行。"
            superseded_fact_ids = tuple(
                fact.id
                for fact in current_semantic_facts(
                    revision.engineering_semantic_facts
                )
            )
            return InteractionAssessmentCandidate(
                interpreted_motive=revision.motive,
                desired_outcome=revision.desired_outcome,
                candidate_context=revision.context_facts,
                candidate_constraints=revision.constraints,
                current_requests=revision.requests,
                neutral_semantic_extractions=(
                    NeutralSemanticExtractionCandidate(
                        extraction_id="dimensions-explicit",
                        kind=NeutralExtractionKind.ORDERED_VALUES,
                        values=(8, 5),
                        source_record_id=latest.id,
                        source_text=source_text,
                        explicit_roles=("columns", "rows"),
                    ),
                ),
                semantic_fact_candidates=(
                    EngineeringSemanticFactCandidate(
                        candidate_id="columns-explicit",
                        subject="layout.column",
                        relation=SemanticRelation.CARDINALITY,
                        value=8,
                        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                        source_record_ids=(latest.id,),
                        source_text=source_text,
                        source_extraction_ids=("dimensions-explicit",),
                        role_origin=SemanticRoleOrigin.EXPLICIT,
                        supersedes_fact_ids=superseded_fact_ids,
                    ),
                    EngineeringSemanticFactCandidate(
                        candidate_id="rows-explicit",
                        subject="layout.row",
                        relation=SemanticRelation.CARDINALITY,
                        value=5,
                        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                        source_record_ids=(latest.id,),
                        source_text=source_text,
                        source_extraction_ids=("dimensions-explicit",),
                        role_origin=SemanticRoleOrigin.EXPLICIT,
                    ),
                ),
                focus_classification=WorkFocusClassification.ON_TOPIC,
                impact_disposition=WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED,
                natural_response=(
                    "已将当前含义更新为 8 列 5 行；此前的 8 节课、"
                    "5 个工作日假设不再作为当前事实。"
                ),
                provider_identity="test:engineering-semantic-truth",
            )

        source_text = "8×5"
        return InteractionAssessmentCandidate(
            interpreted_motive="Build a course schedule",
            desired_outcome="Deliver a schedule whose dimensions preserve the intended meaning.",
            neutral_semantic_extractions=(
                NeutralSemanticExtractionCandidate(
                    extraction_id="dimensions-neutral",
                    kind=NeutralExtractionKind.ORDERED_VALUES,
                    values=(8, 5),
                    source_record_id=latest.id,
                    source_text=source_text,
                    explicit_roles=(None, None),
                ),
            ),
            semantic_fact_candidates=(
                EngineeringSemanticFactCandidate(
                    candidate_id="periods-inferred",
                    subject="schedule.period",
                    relation=SemanticRelation.CARDINALITY,
                    value=8,
                    authority=SemanticFactAuthority.SYSTEM_INFERRED,
                    epistemic_status=SemanticEpistemicStatus.WORKING_ASSUMPTION,
                    source_record_ids=(latest.id,),
                    source_text=source_text,
                    source_extraction_ids=("dimensions-neutral",),
                    role_origin=SemanticRoleOrigin.INFERRED,
                ),
                EngineeringSemanticFactCandidate(
                    candidate_id="weekdays-inferred",
                    subject="schedule.weekday",
                    relation=SemanticRelation.CARDINALITY,
                    value=5,
                    authority=SemanticFactAuthority.SYSTEM_INFERRED,
                    epistemic_status=SemanticEpistemicStatus.WORKING_ASSUMPTION,
                    source_record_ids=(latest.id,),
                    source_text=source_text,
                    source_extraction_ids=("dimensions-neutral",),
                    role_origin=SemanticRoleOrigin.INFERRED,
                ),
            ),
            natural_response=(
                "我会把 8×5 作为可修正的工作假设：8 节课、5 个工作日。"
            ),
            provider_identity="test:engineering-semantic-truth",
        )


class _ExplicitBranchSemanticCapability:
    def __init__(
        self, *, provider_variant: bool = False, actual_provider_fact: bool = False,
    ) -> None:
        self.provider_variant = provider_variant
        self.actual_provider_fact = actual_provider_fact

    def interpret(self, basis: InteractionInterpretationInput) -> InteractionAssessmentCandidate:
        revision = basis.active_work_context.work_revision
        latest = basis.records[-1]
        branch_name = EngineeringSemanticFactCandidate(
            candidate_id="explicit-branch-name",
            subject="repository.branch.name" if self.actual_provider_fact else "repository.branch_name",
            relation=(
                SemanticRelation.REFERENCE if self.provider_variant or self.actual_provider_fact
                else SemanticRelation.EQUALITY
            ),
            value="test",
            qualifiers=(
                {} if self.actual_provider_fact else {"branch_kind": "new"} if self.provider_variant
                else {"state": "to_be_created"}
            ),
            authority=SemanticFactAuthority.HUMAN_EXPLICIT,
            epistemic_status=SemanticEpistemicStatus.CONFIRMED,
            source_record_ids=(latest.id,),
            source_text="test" if self.provider_variant or self.actual_provider_fact else latest.content,
            role_origin=SemanticRoleOrigin.EXPLICIT,
        )
        action = EngineeringSemanticFactCandidate(
            candidate_id="explicit-branch-action",
            subject="repository.branch_action",
            relation=SemanticRelation.EQUALITY,
            value="创建新分支",
            authority=SemanticFactAuthority.HUMAN_EXPLICIT,
            epistemic_status=SemanticEpistemicStatus.CONFIRMED,
            source_record_ids=(latest.id,),
            source_text=latest.content,
            role_origin=SemanticRoleOrigin.EXPLICIT,
        )
        return InteractionAssessmentCandidate(
            interpreted_motive=revision.motive,
            desired_outcome=(
                f"{revision.desired_outcome} 创建 test 分支"
                if self.actual_provider_fact else revision.desired_outcome
            ),
            candidate_context=revision.context_facts,
            candidate_constraints=(
                (*revision.constraints, "后续开发基于 test 分支（模型推断）")
                if self.actual_provider_fact else revision.constraints
            ),
            current_requests=(*revision.requests, latest.content),
            semantic_fact_candidates=(
                (branch_name,) if self.provider_variant or self.actual_provider_fact
                else (branch_name, action)
            ),
            focus_classification=WorkFocusClassification.ON_TOPIC,
            impact_disposition=WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED,
            natural_response="已记录创建 test 分支的明确请求，等待 Work Reality 接纳。",
            provider_identity="test:explicit-branch-semantic",
        )


class _GeneralProductDesignCapability:
    def interpret(
        self, basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        motive = basis.records[0].content
        clarified_context = tuple(
            record.content for record in basis.records[1:]
        )
        return InteractionAssessmentCandidate(
            interpreted_motive=motive,
            desired_outcome=(
                "形成一个边界清楚、可验证并可分阶段进入生产的运营管理平台设计。"
            ),
            candidate_context=(
                "初始输入是高层产品 Motive，尚未形成生产合同。",
                *clarified_context,
            ),
            candidate_constraints=("在设计成熟且 Human 审阅前不得进入生产。",),
            current_requests=(motive,),
            natural_response="已形成可由 Human 治理准入的初始共同理解。",
            provider_identity="test:guided-design-wic-formation",
        )


class _NotReadyCapability:
    def interpret(
        self, _basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        return InteractionAssessmentCandidate(
            interpreted_motive="Explore progress visibility",
            unresolved_material_questions=("What exact outcome matters?",),
            natural_response="One material outcome remains unclear.",
            provider_identity="test:wic-slice-2",
        )


class _ActiveCapability:
    def __init__(
        self,
        *,
        focus: WorkFocusClassification,
        impact: WorkImpactDisposition | None = None,
        context_fact: str | None = None,
        constraint: str | None = None,
        motive: str | None = None,
        desired_outcome: str | None = None,
        meaning: InterpretationMeaningKind | None = None,
        request: str | None = None,
    ) -> None:
        self.focus = focus
        self.impact = impact
        self.context_fact = context_fact
        self.constraint = constraint
        self.motive = motive
        self.desired_outcome = desired_outcome
        self.meaning = meaning
        self.request = request

    def interpret(
        self, basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        active = basis.active_work_context
        assert active is not None
        revision = active.work_revision
        latest = basis.records[-1]
        return InteractionAssessmentCandidate(
            interpreted_motive=self.motive or revision.motive,
            desired_outcome=self.desired_outcome or revision.desired_outcome,
            candidate_context=(
                revision.context_facts
                if self.context_fact is None
                else (*revision.context_facts, self.context_fact)
            ),
            candidate_constraints=(
                revision.constraints
                if self.constraint is None
                else (*revision.constraints, self.constraint)
            ),
            current_requests=(
                revision.requests
                if self.request is None
                else (*revision.requests, self.request)
            ),
            meanings=(
                ()
                if self.meaning is None
                else (
                    InterpretationMeaning(
                        kind=self.meaning,
                        statement=latest.content,
                        source_record_ids=(latest.id,),
                        confidence=1,
                        rationale="Deterministic Slice 3 test interpretation.",
                    ),
                )
            ),
            focus_classification=self.focus,
            impact_disposition=self.impact,
            supporting_references=latest.supporting_references,
            natural_response="The input was assessed against exact active Work Reality.",
            provider_identity="test:wic-slice-3",
        )


class _InventedReferenceCapability(_ActiveCapability):
    def interpret(
        self, basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        candidate = super().interpret(basis)
        return candidate.model_copy(
            update={"supporting_references": (f"VERIFICATION:{uuid4()}",)}
        )


class _GuidedDesignSemanticCapability:
    identity = "test:guided-design-semantic"

    def __init__(self) -> None:
        self.inputs: list[SemanticStepInput] = []

    def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
        self.inputs.append(input)
        assert input.design_context is not None
        issue = input.design_context["current_issue"]
        assert isinstance(issue, dict)
        sufficiency = input.design_context["step_scoped_sufficiency"]
        assert isinstance(sufficiency, dict)
        assert sufficiency["human_attention_requires_both"] == [
            "watt_lacks_authority_to_choose",
            "choice_materially_changes_current_step",
        ]
        final = bool(input.design_context["production_transition_issue"])
        proposal = (
            SemanticProductionProposal(
                target_kind=ProductionTargetKind.DOCUMENTATION_WORK,
                objective="Record the reviewed bounded product/system design",
                artifact_targets=(
                    ProductionPlanArtifactTarget(
                        path="AI_context.md",
                        operation=PlannedArtifactOperation.UPDATE,
                    ),
                ),
                verification_expectation="Verify the exact governed design artifact",
            )
            if final
            else None
        )
        return SemanticStepResultCandidate(
            work_id=input.work_id,
            steering_plan_revision_id=input.steering_plan_revision_id,
            step_id=input.step.id,
            step_type=input.step.type,
            basis_fingerprint=input.basis_fingerprint,
            result_kind=SemanticResultKind.DESIGN_DIRECTION,
            bounded_summary=(
                f"Resolved guided design issue {issue['key']} from governed Reality."
            ),
            decisions=(f"Admit the bounded result for {issue['key']}.",),
            derived_constraints=input.constraints,
            evidence_refs=input.reality_refs,
            unresolved_questions=(),
            authority_assessment=SteeringAuthorityAssessment.WITHIN_AUTHORITY,
            proposed_production=proposal,
            reasoning_provider_identity=self.identity,
            completion_claimed=True,
        )


class _UnguidedSemanticCapability:
    identity = "test:unguided-semantic"

    def __init__(self) -> None:
        self.inputs: list[SemanticStepInput] = []

    def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
        self.inputs.append(input)
        proposal = (
            SemanticProductionProposal(
                target_kind=ProductionTargetKind.CODE_WORK,
                objective="Implement the bounded continuation for the latest Work Reality",
                code_targets=("index.html", "tests/js/test_page.cjs"),
                verification_expectation="Run the exact page test and inspect the artifact",
            )
            if input.production_proposal_required
            else None
        )
        return SemanticStepResultCandidate(
            work_id=input.work_id,
            steering_plan_revision_id=input.steering_plan_revision_id,
            step_id=input.step.id,
            step_type=input.step.type,
            basis_fingerprint=input.basis_fingerprint,
            result_kind=SemanticResultKind.DESIGN_DIRECTION,
            bounded_summary="Reassessed the latest admitted Work revision.",
            decisions=("Proceed from the current governed Work Reality.",),
            derived_constraints=input.constraints,
            evidence_refs=input.reality_refs,
            unresolved_questions=(),
            authority_assessment=SteeringAuthorityAssessment.WITHIN_AUTHORITY,
            proposed_production=proposal,
            reasoning_provider_identity=self.identity,
            completion_claimed=True,
        )


class _RecordingDriver:
    def __init__(self) -> None:
        self.scheduled: list[UUID] = []

    def schedule(self, work_id: UUID) -> bool:
        self.scheduled.append(work_id)
        return True

    def is_active(self, _work_id: UUID) -> bool:
        return False

    def resume_safely_eligible_works(self) -> tuple[()]:
        return ()

    def project(self, _work_id: UUID):
        raise SteeringRecordNotFound("test projection is intentionally absent")

    def shutdown(self) -> None:
        return None


class _NoopOrchestrator:
    def schedule(self, _work_id: UUID) -> bool:
        raise AssertionError("WIC long-lived admission must not schedule ORCH")

    def resume_safely_eligible_works(self) -> tuple[()]:
        return ()

    def shutdown(self) -> None:
        return None


class _SchedulingOrchestrator:
    def __init__(self) -> None:
        self.scheduled: list[UUID] = []

    def add_outcome_listener(self, _listener) -> None:
        return None

    def is_active(self, _work_id: UUID) -> bool:
        return False

    def schedule(self, work_id: UUID) -> bool:
        self.scheduled.append(work_id)
        return True

    def last_outcome(self, _work_id: UUID):
        return None

    def shutdown(self) -> None:
        return None


class _RuntimeActivation:
    def __init__(self, state: RuntimeActivationState = RuntimeActivationState.ACTIVE_AT_TRUSTED_BASELINE) -> None:
        self.state = state

    def project(self) -> RuntimeActivationProjection:
        return RuntimeActivationProjection(
            state=self.state,
            active_application_revision=(
                "test" if self.state is RuntimeActivationState.ACTIVE_AT_TRUSTED_BASELINE else None
            ),
            current_trusted_baseline_revision="test",
            activation_mode=(
                "HUMAN_REVIEW" if self.state is RuntimeActivationState.ACTIVE_HUMAN_REVIEW
                else "LOCAL_DOCKER_EXACT_TRUSTED_SOURCE"
            ),
            reason="test",
        )


def _migration_config(database: Database) -> Config:
    os.environ["SPG_DATABASE_URL"] = database.engine.url.render_as_string(
        hide_password=False
    )
    return Config(PROJECT_ROOT / "alembic.ini")


def _truncate(database: Database) -> None:
    names = ", ".join(f'"{name}"' for name in sorted(ALL_TABLE_NAMES))
    with database.engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture(autouse=True)
def clean_schema(postgres_database: Database) -> Iterator[None]:
    previous = os.environ.get("SPG_DATABASE_URL")
    command.upgrade(_migration_config(postgres_database), "head")
    _truncate(postgres_database)
    try:
        yield
    finally:
        _truncate(postgres_database)
        if previous is None:
            os.environ.pop("SPG_DATABASE_URL", None)
        else:
            os.environ["SPG_DATABASE_URL"] = previous


@pytest.fixture
def services(
    postgres_database: Database,
    tmp_path: Path,
) -> tuple[WorkApplicationService, WorkInteractionService]:
    return _services_for_resource(postgres_database, tmp_path, "test://wic-admission")


def _services_for_resource(
    postgres_database: Database, tmp_path: Path, identity: str,
) -> tuple[WorkApplicationService, WorkInteractionService]:
    repository = tmp_path / "wic-admission-repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "AI_context.md").write_text("governed context\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")

    RuntimeService(postgres_database).bootstrap_trusted_baseline(
        BootstrapRequest(
            repository_path=repository,
            repository_identity=identity,
            repository_ref="refs/heads/main",
            authority_identity="architecture-lead:test",
            scope={"slice": "WIC-2"},
        )
    )
    work = WorkApplicationService(
        postgres_database,
        workspace_root=tmp_path / "workspaces",
    )
    work.register_engineering_resource(
        repository_identity=identity,
        location_ref=str(repository),
        authoritative_ref="refs/heads/main",
        context_references=(
            EngineeringContextReference(
                semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                repository_relative_path="AI_context.md",
            ),
        ),
    )
    return work, WorkInteractionService(
        postgres_database,
        capability=_ReadyCapability(),
    )


def _count(database: Database, table) -> int:
    with database.engine.connect() as connection:
        return int(connection.scalar(select(func.count()).select_from(table)) or 0)


def _ready(interactions: WorkInteractionService):
    interaction = interactions.create_interaction(human_identity="human:test")
    projection = interactions.append_and_assess(
        interaction.id,
        "Please improve long-running progress feedback without redesigning the UI.",
        human_identity="human:test",
    )
    assert projection.readiness is not None
    assert projection.readiness.status is WorkAdmissionReadinessStatus.READY
    assert projection.latest_assessment is not None
    return projection


def _admit(work: WorkApplicationService, ready, *, authority_identity: str = "human:governor"):
    return work.admit_interaction_work(
        ready.interaction.id,
        assessment_id=ready.latest_assessment.id,
        basis_fingerprint=ready.latest_assessment.basis_fingerprint,
        authority_identity=authority_identity,
        rationale="Admit the reviewed Shared Understanding.",
    )


def _bind_active_cycle(
    database: Database,
    projection,
):
    scope = projection.engineering_scope
    assert scope is not None
    assert projection.current_work_reality_revision_id is not None
    spine = RuntimeService(database).create_initial_runtime_spine(
        InitialRunRequest(
            intent_ref=f"work:{projection.work_id}:wic-slice-3-test",
            goal=projection.desired_outcome or projection.raw_user_requirement,
            production_horizon=ProductionHorizon.DOCUMENTATION,
            initial_work_unit_objective="Produce bounded Slice 3 test evidence",
            completion_contract=CompletionContract(
                required_outputs=("bounded evidence",),
                verification_obligations=("inspect bounded evidence",),
            ),
        )
    )
    governance_id = uuid4()
    binding_id = uuid4()
    now = datetime.now(UTC)
    with database.unit_of_work() as unit_of_work:
        runtime = RuntimeStore(unit_of_work.session)
        product = ProductStore(unit_of_work.session)
        runtime.insert_governance(
            {
                "id": governance_id,
                "decision_type": "TEST_ADMIT_ACTIVE_PRODUCTION_CYCLE",
                "authority_identity": "human:test",
                "subject_type": "PRODUCT_WORK",
                "subject_identity": str(projection.work_id),
                "scope": {"test_only": True},
                "rationale": "Establish an immutable active-cycle test fixture.",
                "created_at": now,
            }
        )
        product.insert_runtime_binding(
            {
                "id": binding_id,
                "work_id": projection.work_id,
                "cycle_number": 1,
                "steering_step_id": None,
                "steering_decision_id": None,
                "work_reality_revision_id": projection.current_work_reality_revision_id,
                "engineering_scope_id": scope.id,
                "resource_id": scope.bindings[0].resource_id,
                "production_run_id": spine.run.id,
                "plan_revision_id": spine.plan_revision.id,
                "work_unit_id": spine.work_unit.id,
                "governance_record_id": governance_id,
                "admitted_by": "human:test",
                "condition": ProductionCycleBindingCondition.ADMITTED.value,
                "created_at": now,
            }
        )
        unit_of_work.commit()
    with database.unit_of_work() as unit_of_work:
        binding = ProductStore(unit_of_work.session).runtime_binding(projection.work_id)
    assert binding is not None
    return binding, spine


def _table_row(database: Database, table, identity: UUID) -> dict:
    with database.engine.connect() as connection:
        return dict(
            connection.execute(
                select(table).where(table.c.id == identity)
            ).mappings().one()
        )


def test_not_ready_and_stale_ready_cannot_create_work(
    postgres_database: Database,
    services,
) -> None:
    work, interactions = services
    not_ready_service = WorkInteractionService(
        postgres_database,
        capability=_NotReadyCapability(),
    )
    interaction = not_ready_service.create_interaction(human_identity="human:test")
    not_ready = not_ready_service.append_and_assess(
        interaction.id,
        "I want to explore visibility.",
        human_identity="human:test",
    )
    assert not_ready.latest_assessment is not None
    with pytest.raises(InteractionInvariantViolation, match="not READY"):
        work.admit_interaction_work(
            interaction.id,
            assessment_id=not_ready.latest_assessment.id,
            basis_fingerprint=not_ready.latest_assessment.basis_fingerprint,
            authority_identity="human:governor",
        )

    ready = _ready(interactions)
    interactions.append_human_input(
        ready.interaction.id,
        "A newer Human fact changes the exact basis.",
        human_identity="human:test",
    )
    with pytest.raises(InteractionInvariantViolation, match="stale"):
        _admit(work, ready)
    assert _count(postgres_database, product_works) == 0
    assert _count(postgres_database, work_reality_revisions) == 0


def test_reversible_detail_does_not_create_work_until_exact_human_admission(
    postgres_database: Database, services,
) -> None:
    work, _ = services

    class _CourseTableCapability:
        def interpret(self, basis: InteractionInterpretationInput) -> InteractionAssessmentCandidate:
            return InteractionAssessmentCandidate(
                turn_intent=ConversationTurnIntent.BUILD,
                interpreted_motive="制作小学五年级课程表网页",
                desired_outcome="交付带 8×5 表格和示例数据的 HTML 页面",
                candidate_context=("具体文件名尚未确定。",),
                unresolved_material_questions=("沿用哪种页面样式？",),
                natural_response="可以先按当前理解制作可逆的首版。",
                provider_identity="test:progressive-admission",
            )

    interactions = WorkInteractionService(postgres_database, capability=_CourseTableCapability())
    interaction = interactions.create_interaction(human_identity="human:test")
    candidate = interactions.append_and_assess(
        interaction.id,
        "做一个五年级课程表网页，沿用现有样式，8×5，数据自己编",
        human_identity="human:test",
    )
    assert candidate.readiness.status is WorkAdmissionReadinessStatus.READY
    assert candidate.latest_assessment.unresolved_material_questions == ("沿用哪种页面样式？",)
    assert _count(postgres_database, product_works) == 0
    with pytest.raises(ProductInvariantViolation, match="Human authority"):
        work.admit_interaction_work(
            interaction.id,
            assessment_id=candidate.latest_assessment.id,
            basis_fingerprint=candidate.latest_assessment.basis_fingerprint,
            authority_identity="",
        )
    admitted = _admit(work, candidate)
    assert admitted.raw_user_requirement == candidate.interpreted_motive
    assert admitted.desired_outcome == candidate.desired_outcome
    shared = interactions.get_shared_understanding(interaction.id)
    assert shared.governed_work_id == admitted.work_id
    assert shared.governed_revision.context_facts == ("具体文件名尚未确定。",)
    assert shared.governed_revision.source_assessment_id == candidate.latest_assessment.id


def test_exact_ready_admission_is_atomic_idempotent_and_continuous(
    postgres_database: Database,
    services,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    admitted = _admit(work, ready)

    assert admitted.mode is WorkMode.LONG_LIVED_STEERING
    assert admitted.status is WorkStatus.READY
    assert admitted.raw_user_requirement == ready.interpreted_motive
    assert admitted.desired_outcome == ready.desired_outcome
    assert admitted.constraints == ready.candidate_constraints
    assert admitted.production_plan is None
    assert admitted.artifact_target is None
    assert admitted.current_work_reality_revision_id is not None
    assert admitted.engineering_scope is not None
    assert admitted.engineering_scope.condition.value == "ADMITTED"

    shared = interactions.get_shared_understanding(ready.interaction.id)
    revision = shared.governed_revision
    assert shared.interaction.id == ready.interaction.id
    assert shared.interaction.current_work_id == admitted.work_id
    assert shared.records == ready.records
    assert revision is not None
    assert revision.revision_number == 1
    assert revision.previous_revision_id is None
    assert revision.source_interaction_id == ready.interaction.id
    assert revision.source_assessment_id == ready.latest_assessment.id
    assert revision.basis_fingerprint == ready.latest_assessment.basis_fingerprint
    assert revision.motive == ready.interpreted_motive
    assert revision.context_facts == ready.candidate_context
    assert revision.constraints == ready.candidate_constraints
    assert revision.engineering_scope_id == admitted.engineering_scope.id
    assert revision.schema_version == "wic-work-reality-v3"
    with postgres_database.unit_of_work() as unit_of_work:
        compatibility = ProductStore(unit_of_work.session).work(admitted.work_id)
    assert compatibility is not None
    assert compatibility.raw_user_requirement == revision.motive
    assert compatibility.desired_outcome == revision.desired_outcome
    assert compatibility.constraints == revision.constraints
    assert compatibility.scope_summary == admitted.engineering_scope.summary
    assert compatibility.current_work_reality_revision_id == revision.id
    assert compatibility.engineering_scope_id == revision.engineering_scope_id
    assert _count(postgres_database, governance_records) == 2

    repeated = _admit(WorkApplicationService(postgres_database), ready)
    assert repeated.work_id == admitted.work_id
    assert repeated.current_work_reality_revision_id == revision.id
    assert _count(postgres_database, product_works) == 1
    assert _count(postgres_database, work_reality_revisions) == 1
    assert _count(postgres_database, engineering_scopes) == 1
    assert _count(postgres_database, engineering_resource_bindings) == 1
    assert _count(postgres_database, product_interactions) == 1

    interactions.append_human_input(
        ready.interaction.id,
        "Continue discussing this same governed Work.",
        human_identity="human:test",
    )
    continued = interactions.get_shared_understanding(ready.interaction.id)
    assert continued.records[-1].work_focus_id == admitted.work_id
    assert continued.governed_revision == revision


def test_engineering_semantic_truth_persists_and_explicit_correction_versions_work(
    postgres_database: Database,
    tmp_path: Path,
) -> None:
    work, _ = _services_for_resource(
        postgres_database,
        tmp_path,
        "test://engineering-semantic-truth",
    )
    interactions = WorkInteractionService(
        postgres_database,
        capability=_CourseScheduleSemanticCapability(),
    )
    interaction = interactions.create_interaction(human_identity="human:test")
    ready = interactions.append_and_assess(
        interaction.id,
        "想要一个可直接打开查看的小学五年级课程表示例页面，表格尺寸为 8×5",
        human_identity="human:test",
    )
    assessment = ready.latest_assessment
    assert assessment is not None
    assert len(assessment.neutral_semantic_extractions) == 1
    assert {
        (fact.subject, fact.value, fact.authority, fact.epistemic_status)
        for fact in current_semantic_facts(assessment.engineering_semantic_facts)
    } == {
        (
            "schedule.period",
            8,
            SemanticFactAuthority.SYSTEM_INFERRED,
            SemanticEpistemicStatus.WORKING_ASSUMPTION,
        ),
        (
            "schedule.weekday",
            5,
            SemanticFactAuthority.SYSTEM_INFERRED,
            SemanticEpistemicStatus.WORKING_ASSUMPTION,
        ),
    }

    admitted = _admit(work, ready)
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)
    initial = interactions.get_shared_understanding(interaction.id).governed_revision
    assert initial is not None
    assert initial.id == admitted.current_work_reality_revision_id
    assert all(
        fact.admitted_work_revision_id == initial.id
        for fact in initial.engineering_semantic_facts
    )
    initial_current = current_semantic_facts(initial.engineering_semantic_facts)
    initial_ids = {fact.id for fact in initial_current}
    assert len(initial_ids) == 2
    assert all(
        fact.provenance.source_record_ids == (ready.records[-1].id,)
        and fact.provenance.source_text == "8×5"
        and fact.provenance.source_extraction_ids == ("dimensions-neutral",)
        and fact.provenance.role_origin is SemanticRoleOrigin.INFERRED
        for fact in initial_current
    )

    correction_service = WorkInteractionService(
        postgres_database,
        capability=_CourseScheduleSemanticCapability(correction=True),
    )
    pending = correction_service.append_and_assess(
        interaction.id,
        "不是，我刚才的意思改一下，要 8 列 5 行。",
        human_identity="human:test",
    )
    correction = pending.latest_assessment
    assert correction is not None
    assert correction.candidate_change is not None
    assert "semantic_facts" in correction.candidate_change.changed_fields
    corrected_current = current_semantic_facts(
        correction.engineering_semantic_facts
    )
    assert all(
        fact.provenance.source_record_ids == (pending.records[-1].id,)
        and fact.provenance.source_text == "不是，我刚才的意思改一下，要 8 列 5 行。"
        and fact.provenance.source_extraction_ids == ("dimensions-explicit",)
        and fact.provenance.role_origin is SemanticRoleOrigin.EXPLICIT
        for fact in corrected_current
    )
    assert {
        (fact.subject, fact.value, fact.authority, fact.epistemic_status)
        for fact in corrected_current
    } == {
        (
            "layout.column",
            8,
            SemanticFactAuthority.HUMAN_EXPLICIT,
            SemanticEpistemicStatus.CONFIRMED,
        ),
        (
            "layout.row",
            5,
            SemanticFactAuthority.HUMAN_EXPLICIT,
            SemanticEpistemicStatus.CONFIRMED,
        ),
    }
    superseded = {
        fact.id
        for fact in correction.engineering_semantic_facts
        if fact.epistemic_status is SemanticEpistemicStatus.SUPERSEDED
    }
    assert superseded == initial_ids
    assert {
        superseded_id
        for fact in corrected_current
        for superseded_id in fact.supersedes_fact_ids
    } == initial_ids

    evolved = work.decide_interaction_work_revision(
        interaction.id,
        assessment_id=correction.id,
        basis_fingerprint=correction.basis_fingerprint,
        expected_previous_revision_id=initial.id,
        action=AttentionAction.APPROVE,
        authority_identity="human:governor",
        rationale="Admit the Human's explicit dimension correction.",
    )
    assert evolved.current_work_reality_revision_id != initial.id
    with postgres_database.unit_of_work() as unit_of_work:
        history = ProductStore(unit_of_work.session).work_reality_revisions(
            admitted.work_id
        )
    assert len(history) == 2
    corrected_revision = history[-1]
    assert corrected_revision.previous_revision_id == initial.id
    admitted_current = current_semantic_facts(
        corrected_revision.engineering_semantic_facts
    )
    assert all(
        fact.admitted_work_revision_id == corrected_revision.id
        for fact in admitted_current
    )
    assert admitted_current == corrected_revision.engineering_semantic_facts[-2:]

    frame = PlanFrameAssembler(postgres_database).assemble(admitted.work_id)
    assert frame.work_reality_revision_id == corrected_revision.id
    assert {
        reference.fact_id for reference in frame.engineering_semantic_facts
    } == {
        fact.id for fact in admitted_current
    }
    assert all(
        reference.source_work_revision_id == corrected_revision.id
        for reference in frame.engineering_semantic_facts
    )

    class _SemanticProductionCapability(_GuidedDesignSemanticCapability):
        def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
            candidate = super().execute(input)
            if not input.design_context["production_transition_issue"]:
                return candidate
            return candidate.model_copy(
                update={
                        "proposed_production": SemanticProductionProposal(
                            target_kind=ProductionTargetKind.DOCUMENTATION_WORK,
                            objective="Materialize the governed course schedule design",
                            artifact_targets=(
                                ProductionPlanArtifactTarget(
                                    path="docs/course-schedule-design.md",
                                    operation=PlannedArtifactOperation.CREATE,
                                ),
                            ),
                            verification_expectation=(
                                "Verify the candidate against the governed schedule facts"
                            ),
                    )
                }
            )

    production = _SchedulingOrchestrator()
    driver = PlanSteeringDriver(
        postgres_database,
        work,
        production,
        semantic_capability=_SemanticProductionCapability(),
        max_automatic_transitions=32,
    )
    try:
        outcome = driver.activate(admitted.work_id)
    finally:
        driver.shutdown()
    if outcome.stop_reason.value == "HUMAN_ATTENTION":
        attention = work.list_attention(work_id=admitted.work_id)
        assert len(attention) == 1
        assert attention[0].kind is AttentionKind.PRODUCTION_PROPOSAL_REVIEW
        work.resolve_attention(
            attention[0].id,
            AttentionResolutionRequest(
                action=AttentionAction.APPROVE,
                authority_identity="human:governor",
                rationale="Admit the fact-bound production proposal.",
            ),
        )
        continuation = PlanSteeringDriver(
            postgres_database,
            work,
            production,
            semantic_capability=_SemanticProductionCapability(),
            max_automatic_transitions=8,
        )
        try:
            outcome = continuation.activate(admitted.work_id)
        finally:
            continuation.shutdown()
    assert outcome.stop_reason.value == "PRODUCTION_RUNNING"
    with postgres_database.unit_of_work() as unit_of_work:
        binding = ProductStore(unit_of_work.session).runtime_binding(admitted.work_id)
        assert binding is not None
        work_unit = RuntimeStore(unit_of_work.session).work_unit(binding.work_unit_id)
    assert work_unit is not None
    assert {
        reference.fact_id
        for reference in work_unit.completion_contract.semantic_fact_obligations
    } == {fact.id for fact in admitted_current}
    assert all(
        reference.source_work_revision_id == corrected_revision.id
        for reference in work_unit.completion_contract.semantic_fact_obligations
    )
    task_contract = work_unit.completion_contract.task_contract
    assert task_contract is not None
    assert task_contract.semantic_fact_references == (
        work_unit.completion_contract.semantic_fact_obligations
    )
    assert f"work-reality-revision:{corrected_revision.id}" in (
        task_contract.authority_lineage
    )
    assert any(
        item.source.value == "DOMAIN_PATTERN"
        and item.authority == "ADVISORY_ONLY"
        for item in task_contract.relevant_context
    )
    assert all(
        str(reference.fact_id)
        in {
            evidence.subject_reference.removeprefix("semantic-fact:")
            for evidence in task_contract.evidence_lineage
            if evidence.subject_reference.startswith("semantic-fact:")
        }
        for reference in work_unit.completion_contract.semantic_fact_obligations
    )
    verification_obligation = "Verify the governed course schedule semantics"
    verification = DeterministicVerificationProvider(
        {verification_obligation: VerificationResultValue.PASS}
    ).verify(
        VerificationCapabilityRequest(
            verification_identity=uuid4(),
            obligation=verification_obligation,
            semantic_fact_obligations=(
                work_unit.completion_contract.semantic_fact_obligations
            ),
            task_contract_id=task_contract.task_contract_id,
            snapshot_id=uuid4(),
            proposed_commit_identity="semantic-course-schedule-commit",
            tree_identity="semantic-course-schedule-tree",
            completion_evaluation_id=uuid4(),
            plan_revision_id=uuid4(),
            source_baseline_id=uuid4(),
        )
    )
    assert verification.evidence.metadata["semantic_fact_ids"] == [
        str(reference.fact_id)
        for reference in work_unit.completion_contract.semantic_fact_obligations
    ]


def test_admission_bootstraps_revision_bound_steering_without_production(
    postgres_database: Database,
    services,
) -> None:
    work, interactions = services
    admitted = _admit(work, _ready(interactions))
    plan = SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)

    assert plan.current_step is not None
    assert plan.current_step.type is SteeringStepType.DESIGN
    assert any(
        ref.kind is RealityReferenceKind.WORK_REALITY_REVISION
        and ref.identity == admitted.current_work_reality_revision_id
        for ref in plan.active_revision.revision.reality_refs
    )
    assert _count(postgres_database, steering_plans) == 1

    guided = GuidedDesignApplicationService(postgres_database).get(admitted.work_id)
    assert guided.schema_identity == "watt:guided-design:general-product-system"
    assert guided.current_focus_key == "motive-users-problem"
    assert guided.readiness.state is DesignReadinessState.NOT_READY
    assert len(guided.issues) == 7
    assert _count(postgres_database, guided_design_processes) == 1
    assert _count(postgres_database, guided_design_agenda_revisions) == 1
    for table in PRODUCTION_TABLES:
        assert _count(postgres_database, table) == 0, table.name

    reconstructed = SteeringBootstrapService(postgres_database).bootstrap(
        admitted.work_id
    )
    assert reconstructed.steering_plan_id == plan.steering_plan_id
    assert _count(postgres_database, steering_plans) == 1


def test_work_status_question_is_read_only_and_independent_of_provider(
    postgres_database: Database, services,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    admitted = _admit(work, ready)
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)

    class BrokenProvider:
        def interpret(self, _basis):
            raise AssertionError("Work Reality status must not call Provider")

    service = WorkInteractionService(postgres_database, capability=BrokenProvider())
    before_revision = _count(postgres_database, work_reality_revisions)
    before_runs = _count(postgres_database, production_runs)
    before_steps = SteeringApplicationService(postgres_database).reconstruct(admitted.work_id)
    service.append_human_input(
        ready.interaction.id, "目前执行到什么状态了？", human_identity="human:test",
    )
    assessment = service.assess_current(ready.interaction.id)
    assert assessment.provider_identity == "watt-native:work-reality-query"
    assert "当前 Work 尚未进入生产执行" in assessment.natural_response
    assert "下一步由 Watt 按当前步骤继续推进" in assessment.natural_response
    assert "PWU" not in assessment.natural_response
    assert "QUEUED" not in assessment.natural_response
    assert assessment.focus_classification is WorkFocusClassification.SIDE_QUESTION
    assert assessment.impact_disposition is WorkImpactDisposition.NO_GOVERNED_CHANGE
    assert _count(postgres_database, work_reality_revisions) == before_revision
    assert _count(postgres_database, production_runs) == before_runs
    assert SteeringApplicationService(postgres_database).reconstruct(admitted.work_id) == before_steps


def test_guided_design_progresses_governed_issues_and_reconstructs_after_restart(
    postgres_database: Database,
    services,
) -> None:
    work, interactions = services
    admitted = _admit(work, _ready(interactions))
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)
    capability = _GuidedDesignSemanticCapability()
    orchestrator = ProductionOrchestrator(work)
    driver = PlanSteeringDriver(
        postgres_database,
        work,
        orchestrator,
        semantic_capability=capability,
        max_automatic_transitions=4,
    )
    try:
        outcome = driver.activate(admitted.work_id)
    finally:
        orchestrator.shutdown()
        driver.shutdown()

    assert outcome.stop_reason.value == "TRANSITION_BOUND"
    design = GuidedDesignApplicationService(postgres_database).get(admitted.work_id)
    assert design.current_focus_key == "boundary-non-goals"
    assert tuple(issue.state for issue in design.issues[:2]) == (
        DesignIssueState.SATISFIED,
        DesignIssueState.SATISFIED,
    )
    assert design.agenda_revision_number == 3
    assert len(capability.inputs) == 2
    assert all(item.design_context is not None for item in capability.inputs)
    assert capability.inputs[0].work_context_facts
    assert capability.inputs[0].work_requests
    second_context = capability.inputs[1].design_context
    assert second_context is not None
    admitted_results = second_context["admitted_results"]
    assert isinstance(admitted_results, list)
    assert [item["issue_key"] for item in admitted_results] == [
        "motive-users-problem"
    ]
    assert admitted_results[0]["bounded_summary"].startswith(
        "Resolved guided design issue"
    )
    restarted = GuidedDesignApplicationService(postgres_database).get(admitted.work_id)
    assert restarted == design
    for table in PRODUCTION_TABLES:
        assert _count(postgres_database, table) == 0, table.name


def test_guided_design_materializes_design_artifact_before_human_review(
    postgres_database: Database,
    services,
) -> None:
    work, interactions = services
    admitted = _admit(work, _ready(interactions))
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)
    capability = _GuidedDesignSemanticCapability()
    orchestrator = ProductionOrchestrator(work)
    driver = PlanSteeringDriver(
        postgres_database,
        work,
        orchestrator,
        semantic_capability=capability,
        max_automatic_transitions=32,
    )
    try:
        outcome = driver.activate(admitted.work_id)
    finally:
        orchestrator.shutdown()
        driver.shutdown()

    assert outcome.stop_reason.value == "PRODUCTION_RUNNING"
    design = GuidedDesignApplicationService(postgres_database).get(admitted.work_id)
    assert design.readiness.state is DesignReadinessState.READY
    assert all(issue.state is DesignIssueState.SATISFIED for issue in design.issues)
    assert work.get_work(admitted.work_id).production_plan is not None
    projection = work.get_work(admitted.work_id)
    assert projection.production_plan is not None
    assert projection.production_plan.target_kind is (
        ProductionTargetKind.DOCUMENTATION_WORK
    )
    assert projection.production_plan.fit_classification is (
        OnePwuFitClassification.ONE_PWU_FIT
    )
    assert _count(postgres_database, production_runs) == 1
    assert _count(postgres_database, production_work_units) == 1
    with postgres_database.unit_of_work() as uow:
        product = ProductStore(uow.session)
        binding = product.runtime_binding(admitted.work_id)
        assert binding is not None
        assert product.runtime_summary(binding).extra["task_contract_mode"] == (
            "DESIGN_ARTIFACT"
        )
    restarted = WorkApplicationService(
        postgres_database,
        workspace_root=work.workspace_root,
    ).get_work(admitted.work_id)
    assert restarted.current_production_run_id == binding.production_run_id
    assert restarted.target_kind is ProductionTargetKind.DOCUMENTATION_WORK


def test_guided_design_rejects_implementation_before_design_artifact_exists(
    postgres_database: Database, tmp_path: Path,
) -> None:
    work, interactions = _services_for_resource(
        postgres_database, tmp_path, "watt://repositories/course-table-test",
    )
    admitted = _admit(work, _ready(interactions))
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)

    class ManagedCodeSemantic(_GuidedDesignSemanticCapability):
        def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
            candidate = super().execute(input)
            if not input.design_context["production_transition_issue"]:
                return candidate
            return candidate.model_copy(update={"proposed_production": SemanticProductionProposal(
                target_kind=ProductionTargetKind.CODE_WORK,
                objective="Implement and verify the admitted bounded page",
                code_targets=("index.html", "tests/js/test_page.cjs"),
                verification_expectation="Run the exact page test and inspect the artifact",
            )})

    production = _SchedulingOrchestrator()
    driver = PlanSteeringDriver(
        postgres_database, work, production,
        semantic_capability=ManagedCodeSemantic(), max_automatic_transitions=32,
    )
    try:
        outcome = driver.activate(admitted.work_id)
    finally:
        driver.shutdown()
    assert outcome.stop_reason.value == "BLOCKED"
    assert production.scheduled == []
    assert _count(postgres_database, production_runs) == 0
    assert _count(postgres_database, production_work_units) == 0


def test_approved_design_artifact_allows_bounded_implementation_contract(
    postgres_database: Database,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    approved_reference = (
        "approved-design-artifact:docs/design.md@runtime-commit:approved"
        "#human-authorization:approved"
    )
    monkeypatch.setattr(
        GuidedDesignApplicationService,
        "approved_design_artifact_references",
        lambda self, work_id: (approved_reference,),
    )
    work, interactions = _services_for_resource(
        postgres_database,
        tmp_path,
        "watt://repositories/approved-design-test",
    )
    admitted = _admit(work, _ready(interactions))
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)

    class ApprovedImplementationSemantic(_GuidedDesignSemanticCapability):
        def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
            candidate = super().execute(input)
            if not input.design_context["production_transition_issue"]:
                return candidate
            assert input.required_intermediate_artifacts == ()
            assert input.approved_artifact_references == (approved_reference,)
            return candidate.model_copy(
                update={
                    "proposed_production": SemanticProductionProposal(
                        target_kind=ProductionTargetKind.CODE_WORK,
                        objective="Implement the explicitly approved design",
                        code_targets=("index.html", "tests/js/test_page.cjs"),
                        verification_expectation="Verify the approved design implementation",
                    )
                }
            )

    production = _SchedulingOrchestrator()
    driver = PlanSteeringDriver(
        postgres_database,
        work,
        production,
        semantic_capability=ApprovedImplementationSemantic(),
        max_automatic_transitions=32,
    )
    try:
        outcome = driver.activate(admitted.work_id)
    finally:
        driver.shutdown()

    assert outcome.stop_reason.value == "PRODUCTION_RUNNING"
    assert production.scheduled == [admitted.work_id]
    with postgres_database.unit_of_work() as uow:
        product = ProductStore(uow.session)
        binding = product.runtime_binding(admitted.work_id)
        assert binding is not None
        summary = product.runtime_summary(binding)
    assert summary.extra["task_contract_mode"] == "IMPLEMENTATION"
    with postgres_database.unit_of_work() as uow:
        raw_contract = uow.session.execute(
            select(production_work_units.c.completion_contract).where(
                production_work_units.c.id == binding.work_unit_id
            )
        ).scalar_one()
    task_contract = CompletionContract.model_validate(raw_contract).task_contract
    assert task_contract is not None
    assert task_contract.required_prerequisites == ("APPROVED_DESIGN_ARTIFACT",)
    assert task_contract.prerequisite_evidence == (approved_reference,)


def test_action_eligibility_hides_implementation_approval_when_design_evidence_stales(
    postgres_database: Database,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    approved_reference = (
        "approved-design-artifact:docs/design.md@runtime-commit:approved"
        "#human-authorization:approved"
    )
    monkeypatch.setattr(
        GuidedDesignApplicationService,
        "approved_design_artifact_references",
        lambda self, work_id: (approved_reference,),
    )
    work, interactions = _services_for_resource(
        postgres_database,
        tmp_path,
        "watt://repositories/action-eligibility-test",
    )
    admitted = _admit(work, _ready(interactions))
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)

    class BroadImplementationSemantic(_GuidedDesignSemanticCapability):
        def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
            candidate = super().execute(input)
            if not input.design_context["production_transition_issue"]:
                return candidate
            return candidate.model_copy(
                update={
                    "proposed_production": SemanticProductionProposal(
                        target_kind=ProductionTargetKind.CODE_WORK,
                        objective="Review a broad implementation proposal",
                        code_targets=tuple(f"src/part_{index}.py" for index in range(5)),
                        verification_expectation="Verify the approved design implementation",
                    )
                }
            )

    driver = PlanSteeringDriver(
        postgres_database,
        work,
        _SchedulingOrchestrator(),
        semantic_capability=BroadImplementationSemantic(),
        max_automatic_transitions=32,
    )
    try:
        outcome = driver.activate(admitted.work_id)
    finally:
        driver.shutdown()
    assert outcome.stop_reason.value == "HUMAN_ATTENTION"

    monkeypatch.setattr(
        GuidedDesignApplicationService,
        "approved_design_artifact_references",
        lambda self, work_id: (),
    )
    attention = work.list_attention(work_id=admitted.work_id)
    assert len(attention) == 1
    assert attention[0].kind is AttentionKind.PRODUCTION_PROPOSAL_REVIEW
    assert attention[0].available_actions == (AttentionAction.REQUEST_REFINEMENT,)
    with pytest.raises(ProductInvariantViolation, match="not allowed"):
        work.resolve_attention(
            attention[0].id,
            AttentionResolutionRequest(
                action=AttentionAction.APPROVE,
                authority_identity="human:test",
            ),
        )


def test_repositoryless_work_still_requires_design_artifact_before_code(
    postgres_database: Database, tmp_path: Path,
) -> None:
    work, interactions = _services_for_resource(
        postgres_database, tmp_path, "test://repositoryless-work",
    )
    ready = _ready(interactions)
    admitted = work.admit_interaction_work(
        ready.interaction.id,
        assessment_id=ready.latest_assessment.id,
        basis_fingerprint=ready.latest_assessment.basis_fingerprint,
        authority_identity="human:governor",
        rationale="Admit Work without requiring a Human repository.",
        use_default_resource=False,
    )
    assets = RepositoryAssetService(
        postgres_database,
        asset_root=tmp_path / "managed-assets",
        import_root=tmp_path,
    )
    allocated = assets.ensure_managed_execution_workspace(work, admitted.work_id)
    assert allocated.engineering_scope is not None
    assert allocated.engineering_scope.bindings
    managed_repository = next((tmp_path / "managed-assets").iterdir())
    (managed_repository / "tests" / "__pycache__").mkdir(parents=True)
    (managed_repository / "tests" / "__pycache__" / "test_page.cpython-313.pyc").write_bytes(
        b"executor validation cache"
    )
    untracked = subprocess.run(
        ["git", "-C", str(managed_repository), "ls-files", "--others", "--exclude-standard"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert "tests/__pycache__/test_page.cpython-313.pyc" not in untracked

    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)

    class ManagedCodeSemantic(_GuidedDesignSemanticCapability):
        def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
            candidate = super().execute(input)
            if not input.design_context["production_transition_issue"]:
                return candidate
            return candidate.model_copy(update={"proposed_production": SemanticProductionProposal(
                target_kind=ProductionTargetKind.CODE_WORK,
                objective="Implement and verify the admitted bounded page",
                code_targets=("index.html", "tests/js/test_page.cjs"),
                verification_expectation="Run the exact page test and inspect the artifact",
            )})

    production = _SchedulingOrchestrator()
    driver = PlanSteeringDriver(
        postgres_database, work, production,
        semantic_capability=ManagedCodeSemantic(), max_automatic_transitions=32,
    )
    try:
        outcome = driver.activate(admitted.work_id)
    finally:
        driver.shutdown()

    assert outcome.stop_reason.value == "BLOCKED"
    assert production.scheduled == []
    assert _count(postgres_database, production_runs) == 0
    assert _count(postgres_database, production_work_units) == 0


def test_production_feedback_can_reopen_issue_and_revise_plan_without_rewriting_history(
    postgres_database: Database,
    services,
) -> None:
    work, interactions = services
    admitted = _admit(work, _ready(interactions))
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)
    service = GuidedDesignApplicationService(postgres_database)
    before = service.get(admitted.work_id)
    runtime_ref = RealityReference(
        kind=RealityReferenceKind.TRUSTED_BASELINE,
        identity=RuntimeService(postgres_database).current_baseline().id,
    )
    reopened = service.reopen_issue(
        admitted.work_id,
        "architecture-risk-assumptions",
        rationale="Verification evidence challenged an earlier architecture assumption.",
        reality_refs=(runtime_ref,),
    )

    assert reopened.agenda_revision_number > before.agenda_revision_number
    issue = next(
        item for item in reopened.issues if item.key == "architecture-risk-assumptions"
    )
    assert issue.state is DesignIssueState.REOPENED
    assert issue.reopen_rationale
    assert runtime_ref in issue.provenance_refs
    assert reopened.current_focus_key == "motive-users-problem"
    with postgres_database.unit_of_work() as unit_of_work:
        history = GuidedDesignStore(unit_of_work.session).revisions(reopened.process_id)
    assert history[0].condition.value == "SUPERSEDED"
    assert history[-1].condition.value == "ACTIVE"
    assert history[0].issues != ()


def test_guided_design_reexecutes_current_issue_after_governed_work_reality_changes(
    postgres_database: Database,
    services,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    admitted = _admit(work, ready)
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)
    capability = _GuidedDesignSemanticCapability()
    orchestrator = ProductionOrchestrator(work)
    driver = PlanSteeringDriver(
        postgres_database,
        work,
        orchestrator,
        semantic_capability=capability,
        max_automatic_transitions=1,
    )
    try:
        first = driver.iterate(admitted.work_id)
        assert first.action.value == "SEMANTIC_RESULT_ADMISSION"

        active = WorkInteractionService(
            postgres_database,
            capability=_ActiveCapability(
                focus=WorkFocusClassification.ON_TOPIC,
                impact=WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED,
                context_fact="Human clarified the primary operator and problem boundary.",
            ),
        )
        pending = active.append_and_assess(
            ready.interaction.id,
            "The primary operator is the team lead coordinating daily operations.",
            human_identity="human:test",
        )
        assessment = pending.latest_assessment
        assert assessment is not None
        assert assessment.basis_work_revision_id is not None
        work.decide_interaction_work_revision(
            ready.interaction.id,
            assessment_id=assessment.id,
            basis_fingerprint=assessment.basis_fingerprint,
            expected_previous_revision_id=assessment.basis_work_revision_id,
            action=AttentionAction.APPROVE,
            authority_identity="human:governor",
        )

        refreshed = driver.iterate(admitted.work_id)
        assert refreshed.action.value == "SEMANTIC_RESULT_ADMISSION"
    finally:
        orchestrator.shutdown()
        driver.shutdown()

    assert len(capability.inputs) == 2
    assert capability.inputs[0].work_context_facts != (
        capability.inputs[1].work_context_facts
    )
    reconstructed = SteeringApplicationService(postgres_database).reconstruct(
        admitted.work_id
    )
    assert len(reconstructed.semantic_results) == 2


@pytest.mark.parametrize("activation_state", (
    RuntimeActivationState.ACTIVE_AT_TRUSTED_BASELINE,
    RuntimeActivationState.ACTIVE_HUMAN_REVIEW,
))
def test_admission_api_requires_human_action_and_preserves_same_interaction(
    postgres_database: Database,
    services,
    activation_state: RuntimeActivationState,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    driver = _RecordingDriver()
    client = TestClient(
        create_http_application(
            application=object(),
            database=postgres_database,
            work_service=work,
            orchestrator=_NoopOrchestrator(),
            steering_driver=driver,
            runtime_activation=_RuntimeActivation(activation_state),
            interaction_service=interactions,
        ),
        raise_server_exceptions=False,
    )
    with client:
        before = client.get(
            f"/api/interactions/{ready.interaction.id}/shared-understanding"
        ).json()
        assert before["governed_work_id"] is None
        response = client.post(
            f"/api/interactions/{ready.interaction.id}/admit-work",
            json={
                "assessment_id": str(ready.latest_assessment.id),
                "basis_fingerprint": ready.latest_assessment.basis_fingerprint,
                "authority_identity": "human:governor",
            },
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["interaction_id"] == str(ready.interaction.id)
        assert payload["governed_work_id"] is not None
        assert payload["governed_revision"]["revision_number"] == 1
        assert payload["governed_revision"]["source_assessment_id"] == str(
            ready.latest_assessment.id
        )
        assert driver.scheduled == [UUID(payload["governed_work_id"])]
        activation = client.get("/api/runtime-activation").json()
        assert activation["state"] == activation_state.value
        if activation_state is RuntimeActivationState.ACTIVE_HUMAN_REVIEW:
            assert activation["activation_mode"] == "HUMAN_REVIEW"
            assert activation["active_application_revision"] is None
        assert _count(postgres_database, product_works) == 1
        assert _count(postgres_database, steering_plans) == 1
        work_payload = client.get(
            f"/api/works/{payload['governed_work_id']}"
        ).json()
        guided_payload = work_payload["guided_design"]
        assert guided_payload["schema_identity"] == (
            "watt:guided-design:general-product-system"
        )
        assert guided_payload["current_focus_key"] == "motive-users-problem"
        assert guided_payload["readiness"] == "NOT_READY"
        assert len(guided_payload["issues"]) == 7
        assert client.get(
            f"/api/works/{payload['governed_work_id']}/guided-design"
        ).json() == guided_payload
        for table in PRODUCTION_TABLES:
            assert _count(postgres_database, table) == 0, table.name


def test_explicit_repository_action_automatically_executes_governed_admission(
    postgres_database: Database,
    tmp_path: Path,
) -> None:
    source = "https://github.com/acme/automatic-admission"
    work, interactions = _services_for_resource(
        postgres_database,
        tmp_path,
        source,
    )
    with postgres_database.unit_of_work() as uow:
        resource = ProductStore(uow.session).default_resource()
    assert resource is not None

    class ExistingRepositoryIntake:
        def __init__(self) -> None:
            self.requests = []
            self.observations = []

        def start_intake(self, request):
            self.requests.append(request)
            observation = {
                "resource_id": str(resource.id),
                "condition": "RUNNING",
                "source": request.source,
                "interaction_id": str(request.interaction_id),
                "work_id": str(request.work_id),
                "attempt_number": request.attempt_number,
                "intake_request_id": str(request.request_id),
            }
            observation["fingerprint"] = canonical_fingerprint(observation)
            self.observations.append(observation)
            return observation

        def execute_intake(self, request_id):
            observation = {
                **self.observations[-1],
                "condition": "READY",
            }
            observation["fingerprint"] = canonical_fingerprint(
                {key: value for key, value in observation.items() if key != "fingerprint"}
            )
            self.observations[-1] = observation
            return observation

        def latest_attempt_for_work(self, work_id):
            return next(
                (
                    item
                    for item in reversed(self.observations)
                    if item["work_id"] == str(work_id)
                ),
                None,
            )

        def next_attempt_number(self, work_id):
            return len(
                [item for item in self.observations if item["work_id"] == str(work_id)]
            ) + 1

        def repository_activation_allowed(self, work_id):
            latest = self.latest_attempt_for_work(work_id)
            return latest is None or latest["condition"] == "READY"

    assets = ExistingRepositoryIntake()
    driver = _RecordingDriver()
    client = TestClient(
        create_http_application(
            application=object(),
            database=postgres_database,
            work_service=work,
            orchestrator=_NoopOrchestrator(),
            steering_driver=driver,
            runtime_activation=_RuntimeActivation(),
            interaction_service=interactions,
            repository_asset_service=assets,
        ),
        raise_server_exceptions=False,
    )
    interaction = interactions.create_interaction(
        human_identity="human:requester",
        start_work_context=True,
    )
    with client:
        submitted = client.post(
            f"/api/interactions/{interaction.id}/turns",
            json={
                "content": f"Please pull {source} and add a login feature.",
                "human_identity": "human:requester",
            },
        )
        assert submitted.status_code == 202, submitted.text
        deadline = time.monotonic() + 5
        payload = None
        while time.monotonic() < deadline:
            candidate = client.get(
                f"/api/interactions/{interaction.id}/shared-understanding"
            ).json()
            if (
                candidate.get("governed_work_id") is not None
                and candidate.get("production_admission_state") == "WORK_CREATED"
                and candidate.get("repository_acquisition_state") == "READY"
            ):
                payload = candidate
                break
            time.sleep(0.01)

    assert payload is not None, candidate
    assert payload["production_admission_state"] == "WORK_CREATED"
    assert payload["repository_acquisition_state"] == "READY"
    assert payload["governed_revision"]["repository_identity"] == source
    assert len(assets.requests) == 1
    assert assets.requests[0].authority_identity == "human:requester"
    assert driver.scheduled == [UUID(payload["governed_work_id"])]


def test_explicit_pull_recovers_admitted_work_that_has_no_prior_acquisition_attempt(
    postgres_database: Database,
    tmp_path: Path,
) -> None:
    source = "https://github.com/acme/runtime-upgrade-recovery"
    work, interactions = _services_for_resource(postgres_database, tmp_path, source)
    with postgres_database.unit_of_work() as uow:
        resource = ProductStore(uow.session).default_resource()
    assert resource is not None

    interaction = interactions.create_interaction(
        human_identity="human:requester",
        start_work_context=True,
    )
    ready = interactions.append_and_assess(
        interaction.id,
        f"Please pull {source} and add a feature.",
        human_identity="human:requester",
    )
    assert ready.latest_assessment is not None
    admitted = work.admit_interaction_work(
        interaction.id,
        engineering_resource_id=None,
        use_default_resource=False,
        assessment_id=ready.latest_assessment.id,
        basis_fingerprint=ready.latest_assessment.basis_fingerprint,
        authority_identity="human:requester",
        rationale="Simulate Work admitted before repository attempts were persisted.",
    )

    class RuntimeUpgradeRecoveryIntake:
        def __init__(self) -> None:
            self.requests = []
            self.observations = []

        def start_intake(self, request):
            self.requests.append(request)
            observation = {
                "resource_id": str(resource.id),
                "condition": "RUNNING",
                "source": request.source,
                "interaction_id": str(request.interaction_id),
                "work_id": str(request.work_id),
                "attempt_number": request.attempt_number,
                "intake_request_id": str(request.request_id),
            }
            observation["fingerprint"] = canonical_fingerprint(observation)
            self.observations.append(observation)
            return observation

        def execute_intake(self, request_id):
            observation = {**self.observations[-1], "condition": "READY"}
            observation["fingerprint"] = canonical_fingerprint(
                {key: value for key, value in observation.items() if key != "fingerprint"}
            )
            self.observations[-1] = observation
            return observation

        def latest_attempt_for_work(self, work_id):
            return next(
                (
                    item
                    for item in reversed(self.observations)
                    if item["work_id"] == str(work_id)
                ),
                None,
            )

        def next_attempt_number(self, work_id):
            return len(
                [item for item in self.observations if item["work_id"] == str(work_id)]
            ) + 1

        def repository_activation_allowed(self, work_id):
            latest = self.latest_attempt_for_work(work_id)
            return latest is not None and latest["condition"] == "READY"

    assets = RuntimeUpgradeRecoveryIntake()
    driver = _RecordingDriver()
    client = TestClient(
        create_http_application(
            application=object(),
            database=postgres_database,
            work_service=work,
            orchestrator=_NoopOrchestrator(),
            steering_driver=driver,
            runtime_activation=_RuntimeActivation(),
            interaction_service=interactions,
            repository_asset_service=assets,
        ),
        raise_server_exceptions=False,
    )

    with client:
        response = client.post(
            f"/api/interactions/{interaction.id}/turns",
            json={
                "content": "Pull the code now.",
                "human_identity": "human:requester",
            },
        )
        assert response.status_code == 202, response.text
        deadline = time.monotonic() + 5
        recovered = None
        while time.monotonic() < deadline:
            candidate = client.get(
                f"/api/interactions/{interaction.id}/shared-understanding"
            ).json()
            if (
                candidate.get("repository_acquisition_state") == "READY"
                and candidate.get("governed_revision", {}).get(
                    "repository_identity"
                )
                == source
            ):
                recovered = candidate
                break
            time.sleep(0.01)

    assert recovered is not None, candidate
    assert recovered["governed_work_id"] == str(admitted.work_id)
    assert recovered["repository_source"] == source
    assert len(assets.requests) == 1
    assert assets.requests[0].work_id == admitted.work_id
    assert assets.requests[0].source == source
    assert driver.scheduled == [admitted.work_id]


@pytest.mark.parametrize(
    "content,expected_repository_state,expected_intakes",
    (
        ("Fix this bug in my repo.", "WAITING_FOR_REPOSITORY_SOURCE", 0),
        (
            "Pull https://github.com/acme/private-repository and fix this bug.",
            "WAITING_FOR_AUTHORIZATION",
            1,
        ),
    ),
)
def test_unbound_repository_request_creates_work_without_bypassing_access(
    postgres_database: Database,
    tmp_path: Path,
    content: str,
    expected_repository_state: str,
    expected_intakes: int,
) -> None:
    work, interactions = _services_for_resource(
        postgres_database,
        tmp_path,
        "test://repository-reference-only",
    )

    class UnresolvedRepositoryIntake:
        def __init__(self) -> None:
            self.requests = []
            self.observations = []

        def start_intake(self, request):
            self.requests.append(request)
            observation = {
                "resource_id": None,
                "condition": "RUNNING",
                "source": request.source,
                "interaction_id": str(request.interaction_id),
                "work_id": str(request.work_id),
                "attempt_number": request.attempt_number,
                "intake_request_id": str(request.request_id),
            }
            self.observations.append(observation)
            return observation

        def execute_intake(self, request_id):
            observation = {
                **self.observations[-1],
                "condition": "WAITING_FOR_AUTHORIZATION",
                "failure_category": "AUTH_REQUIRED",
                "human_message": "Repository read authorization is required.",
            }
            self.observations[-1] = observation
            return observation

        def latest_attempt_for_work(self, work_id):
            return next(
                (
                    item
                    for item in reversed(self.observations)
                    if item["work_id"] == str(work_id)
                ),
                None,
            )

        def next_attempt_number(self, work_id):
            return len(
                [item for item in self.observations if item["work_id"] == str(work_id)]
            ) + 1

        def repository_activation_allowed(self, work_id):
            latest = self.latest_attempt_for_work(work_id)
            return latest is None or latest["condition"] == "READY"

    driver = _RecordingDriver()
    assets = UnresolvedRepositoryIntake()
    client = TestClient(
        create_http_application(
            application=object(),
            database=postgres_database,
            work_service=work,
            orchestrator=_NoopOrchestrator(),
            steering_driver=driver,
            runtime_activation=_RuntimeActivation(),
            interaction_service=interactions,
            repository_asset_service=assets,
        ),
        raise_server_exceptions=False,
    )
    interaction = interactions.create_interaction(
        human_identity="human:requester",
        start_work_context=True,
    )
    with client:
        response = client.post(
            f"/api/interactions/{interaction.id}/turns",
            json={
                "content": content,
                "human_identity": "human:requester",
            },
        )
        assert response.status_code == 202, response.text
        deadline = time.monotonic() + 5
        payload = None
        while time.monotonic() < deadline:
            candidate = client.get(
                f"/api/interactions/{interaction.id}/shared-understanding"
            ).json()
            if (
                candidate["governed_work_id"] is not None
                and candidate["production_admission_state"] == "WORK_CREATED"
                and candidate["repository_acquisition_state"]
                == expected_repository_state
            ):
                payload = candidate
                break
            time.sleep(0.01)

    assert payload is not None
    assert payload["production_admission_state"] == "WORK_CREATED"
    assert payload["repository_acquisition_state"] == expected_repository_state
    assert payload["governed_revision"]["repository_identity"] is None
    assert len(assets.requests) == expected_intakes
    assert driver.scheduled == []
    if expected_intakes:
        sources = client.get(
            f"/api/works/{payload['governed_work_id']}/control-room/sources"
        ).json()
        assert sources["selection"] == "ACQUISITION_STATE"
        assert sources["acquisition"]["state"] == expected_repository_state
        assert sources["acquisition"]["failure_category"] == "AUTH_REQUIRED"
        assert sources["acquisition"]["retry_available"] is True
        assert sources["acquisition"]["authorization"] == {
            "required": True,
            "integration_available": False,
            "human_action": (
                "Grant repository read access outside Watt, then retry this "
                "persisted acquisition."
            ),
        }


def test_failed_repository_acquisition_reuses_work_and_retries_with_new_attempt(
    postgres_database: Database,
    tmp_path: Path,
) -> None:
    source = "https://github.com/acme/private-repository"
    work, interactions = _services_for_resource(postgres_database, tmp_path, source)
    with postgres_database.unit_of_work() as uow:
        resource = ProductStore(uow.session).default_resource()
    assert resource is not None

    class RecoveringRepositoryAcquisition:
        def __init__(self) -> None:
            self.requests = []
            self.observations = []

        def start_intake(self, request):
            self.requests.append(request)
            observation = {
                "resource_id": None,
                "condition": "RUNNING",
                "source": request.source,
                "interaction_id": str(request.interaction_id),
                "work_id": str(request.work_id),
                "attempt_number": request.attempt_number,
                "previous_attempt_id": (
                    None
                    if request.previous_attempt_id is None
                    else str(request.previous_attempt_id)
                ),
                "intake_request_id": str(request.request_id),
            }
            self.observations.append(observation)
            return observation

        def execute_intake(self, request_id):
            current = self.observations[-1]
            if current["attempt_number"] == 1:
                observation = {
                    **current,
                    "condition": "WAITING_FOR_AUTHORIZATION",
                    "failure_category": "AUTH_REQUIRED",
                    "human_message": "Repository read authorization is required.",
                }
            else:
                observation = {
                    **current,
                    "resource_id": str(resource.id),
                    "condition": "READY",
                    "failure_category": None,
                    "human_message": "Repository is ready.",
                }
                observation["fingerprint"] = canonical_fingerprint(observation)
            self.observations[-1] = observation
            return observation

        def latest_attempt_for_work(self, work_id):
            return next(
                (
                    item
                    for item in reversed(self.observations)
                    if item["work_id"] == str(work_id)
                ),
                None,
            )

        def next_attempt_number(self, work_id):
            return len(
                [item for item in self.observations if item["work_id"] == str(work_id)]
            ) + 1

        def repository_activation_allowed(self, work_id):
            latest = self.latest_attempt_for_work(work_id)
            return latest is None or latest["condition"] == "READY"

    assets = RecoveringRepositoryAcquisition()
    driver = _RecordingDriver()
    client = TestClient(
        create_http_application(
            application=object(),
            database=postgres_database,
            work_service=work,
            orchestrator=_NoopOrchestrator(),
            steering_driver=driver,
            runtime_activation=_RuntimeActivation(),
            interaction_service=interactions,
            repository_asset_service=assets,
        ),
        raise_server_exceptions=False,
    )
    interaction = interactions.create_interaction(
        human_identity="human:requester", start_work_context=True
    )

    def submit(content: str) -> None:
        response = client.post(
            f"/api/interactions/{interaction.id}/turns",
            json={"content": content, "human_identity": "human:requester"},
        )
        assert response.status_code == 202, response.text
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            projection = client.get(
                f"/api/interactions/{interaction.id}/shared-understanding"
            ).json()
            turns = projection.get("turns", [])
            if turns and turns[-1]["status"] in {"COMPLETED", "FAILED"}:
                return
            time.sleep(0.01)
        raise AssertionError("Interaction turn did not settle")

    with client:
        submit(f"Pull {source} and add a login feature.")
        first = client.get(
            f"/api/interactions/{interaction.id}/shared-understanding"
        ).json()
        work_id = first["governed_work_id"]
        assert first["repository_acquisition_state"] == "WAITING_FOR_AUTHORIZATION"
        assert driver.scheduled == []

        submit("Is it ready?")
        status = client.get(
            f"/api/interactions/{interaction.id}/shared-understanding"
        ).json()
        assert status["governed_work_id"] == work_id
        assert status["repository_source"] == source
        assert status["repository_acquisition_state"] == "WAITING_FOR_AUTHORIZATION"
        assert len(assets.requests) == 1

        submit("Retry repository acquisition.")
        deadline = time.monotonic() + 5
        recovered = None
        while time.monotonic() < deadline:
            candidate = client.get(
                f"/api/interactions/{interaction.id}/shared-understanding"
            ).json()
            if candidate.get("repository_acquisition_state") == "READY":
                recovered = candidate
                break
            time.sleep(0.01)

    assert recovered is not None
    assert recovered["governed_work_id"] == work_id
    assert recovered["repository_acquisition_state"] == "READY"
    assert len(assets.requests) == 2
    assert assets.requests[1].attempt_number == 2
    assert assets.requests[1].previous_attempt_id == assets.requests[0].request_id
    assert driver.scheduled == [UUID(work_id)]


def test_repository_attempt_history_preserves_failure_and_new_retry_result(
    postgres_database: Database,
    tmp_path: Path,
) -> None:
    import_root = tmp_path / "imports"
    import_root.mkdir()
    source_repository = import_root / "source"
    source_repository.mkdir()
    _git(source_repository, "init", "-b", "main")
    _git(source_repository, "config", "user.name", "SPG Test")
    _git(source_repository, "config", "user.email", "spg-test@example.invalid")
    (source_repository / "README.md").write_text("# Source\n", encoding="utf-8")
    _git(source_repository, "add", ".")
    _git(source_repository, "commit", "-m", "baseline")

    class FailThenAcquire:
        def __init__(self) -> None:
            self.calls = 0

        def acquire(self, root, source, destination):
            self.calls += 1
            if self.calls == 1:
                raise RepositoryAcquisitionFailure(
                    RepositoryAcquisitionFailureCategory.AUTH_REQUIRED,
                    "Repository read authorization is required.",
                    technical_evidence={
                        "operation": "git clone --single-branch",
                        "stderr": "terminal prompts disabled",
                    },
                    retryable=True,
                )
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "clone",
                    "--single-branch",
                    "--",
                    str(source_repository),
                    str(destination),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stderr

    service = RepositoryAssetService(
        postgres_database,
        tmp_path / "assets",
        import_root,
        repository_acquirer=FailThenAcquire(),
    )
    work_id = uuid4()
    interaction_id = uuid4()
    source = "https://github.com/acme/private-repository.git"
    first_id = uuid4()
    first = service.intake(
        RepositoryIntakeRequest(
            request_id=first_id,
            source=source,
            title="Private repository",
            description="Acquire the repository baseline.",
            authority_identity="human:test",
            interaction_id=interaction_id,
            work_id=work_id,
            attempt_number=1,
        )
    )
    second = service.intake(
        RepositoryIntakeRequest(
            request_id=uuid4(),
            source=source,
            title="Private repository",
            description="Retry the repository baseline acquisition.",
            authority_identity="human:test",
            interaction_id=interaction_id,
            work_id=work_id,
            attempt_number=2,
            previous_attempt_id=first_id,
        )
    )

    history = service.attempts_for_work(work_id)
    assert first["condition"] == "WAITING_FOR_AUTHORIZATION"
    assert first["failure_category"] == "AUTH_REQUIRED"
    assert first["technical_evidence"]["stderr"] == "terminal prompts disabled"
    assert second["condition"] == "READY"
    assert second["resource_id"] is not None
    assert [item["attempt_number"] for item in history] == [1, 2]
    assert history[1]["previous_attempt_id"] == str(first_id)


def test_repository_acquisition_persists_requested_then_running_before_git_effect(
    postgres_database: Database,
    tmp_path: Path,
) -> None:
    import_root = tmp_path / "imports"
    import_root.mkdir()
    source_repository = import_root / "source"
    source_repository.mkdir()
    _git(source_repository, "init", "-b", "main")
    _git(source_repository, "config", "user.name", "SPG Test")
    _git(source_repository, "config", "user.email", "spg-test@example.invalid")
    (source_repository / "README.md").write_text("# Source\n", encoding="utf-8")
    _git(source_repository, "add", ".")
    _git(source_repository, "commit", "-m", "baseline")

    class ObservingAcquirer:
        service = None

        def __init__(self) -> None:
            self.states: list[str] = []

        def acquire(self, root, source, destination):
            assert self.service is not None
            latest = self.service.latest_attempt_for_work(work_id)
            self.states.append(latest["condition"])
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "clone",
                    "--single-branch",
                    "--",
                    str(source_repository),
                    str(destination),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stderr

    work_id = uuid4()
    acquirer = ObservingAcquirer()
    service = RepositoryAssetService(
        postgres_database,
        tmp_path / "assets",
        import_root,
        repository_acquirer=acquirer,
    )
    acquirer.service = service
    request = RepositoryIntakeRequest(
        request_id=uuid4(),
        source="https://github.com/acme/repository.git",
        title="Repository",
        description="Acquire the repository baseline.",
        authority_identity="human:test",
        interaction_id=uuid4(),
        work_id=work_id,
        attempt_number=1,
    )

    requested = service.start_intake(request)
    completed = service.execute_intake(request.request_id)

    assert requested["condition"] == "REQUESTED"
    assert acquirer.states == ["RUNNING"]
    assert completed["condition"] == "READY"
    assert service.latest_attempt_for_work(work_id)["condition"] == "READY"


def test_repository_acquisition_unexpected_effect_failure_is_terminalized(
    postgres_database: Database,
    tmp_path: Path,
) -> None:
    import_root = tmp_path / "imports"
    import_root.mkdir()

    class InvalidCheckoutAcquirer:
        def acquire(self, root, source, destination):
            destination.mkdir(parents=True)

    service = RepositoryAssetService(
        postgres_database,
        tmp_path / "assets",
        import_root,
        repository_acquirer=InvalidCheckoutAcquirer(),
    )
    request = RepositoryIntakeRequest(
        request_id=uuid4(),
        source="https://github.com/acme/repository.git",
        title="Repository",
        description="Acquire the repository baseline.",
        authority_identity="human:test",
        interaction_id=uuid4(),
        work_id=uuid4(),
        attempt_number=1,
    )

    observation = service.intake(request)

    assert observation["condition"] == "FAILED_RETRYABLE"
    assert observation["failure_category"] == "ACQUISITION_FAILED_RETRYABLE"
    assert observation["technical_evidence"]["phase"] == "REPOSITORY_ACQUISITION"
    assert observation["technical_evidence"]["error_type"] == "ProductInvariantViolation"
    assert "Traceback" not in observation["human_message"]


@pytest.mark.parametrize(
    "provider_variant,actual_provider_fact",
    ((False, False), (True, False), (False, True)),
)
def test_governed_branch_operation_preserves_main_and_binds_exact_commit(
    postgres_database: Database,
    tmp_path: Path,
    services,
    provider_variant: bool,
    actual_provider_fact: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if subprocess.run(("docker", "image", "inspect", "watt-native-executor-runtime:local"), capture_output=True).returncode:
        pytest.skip("qualified local Native Executor image is unavailable")
    work_service, interactions = services
    ready = _ready(interactions)
    branch_actor = f"human:branch-{uuid4().hex[:8]}"
    admitted = _admit(work_service, ready, authority_identity=branch_actor)
    import_root = tmp_path / "imports"
    import_root.mkdir()
    source_repository = import_root / "source"
    source_repository.mkdir()
    _git(source_repository, "init", "-b", "main")
    _git(source_repository, "config", "user.name", "SPG Test")
    _git(source_repository, "config", "user.email", "spg-test@example.invalid")
    (source_repository / "README.md").write_text("# Source\n", encoding="utf-8")
    _git(source_repository, "add", ".")
    _git(source_repository, "commit", "-m", "baseline")
    work_id = admitted.work_id
    interaction_id = uuid4()
    service = RepositoryAssetService(
        postgres_database,
        tmp_path / "assets",
        import_root,
        native_git_operations=NativeGitOperationRunner(
            postgres_database,
            production_environment=NativeProductionEnvironmentRuntime(
                store=JsonProductionEnvironmentStore(tmp_path / "native-git-pe"),
                provider=ContainerProductionEnvironmentProvider(DockerCliContainerRuntime()),
                image_reference="watt-native-executor-runtime:local",
            ),
            workspace_root=tmp_path / "native-git-workspaces",
            checkpoint_root=tmp_path.parent.parent / f"ng-{uuid4().hex[:8]}",
        ),
    )
    acquired = service.intake(
        RepositoryIntakeRequest(
            request_id=uuid4(),
            source=str(source_repository),
            title="Source repository",
            description="Acquire the baseline.",
            authority_identity="human:test",
            interaction_id=interaction_id,
            work_id=work_id,
        )
    )
    assert acquired["operation_evidence"]["capability_id"] == "git.repository.acquire"
    assert acquired["operation_evidence"]["resulting_branch"] == "refs/heads/main"
    assert acquired["operation_evidence"]["resulting_revision"] == acquired["revision"]
    assert acquired["operation_evidence"]["verified"] is True
    work_service.admit_asset_scope(
        work_id,
        AssetScopeAdmissionRequest(
            resource_id=UUID(acquired["resource_id"]),
            expected_work_revision_id=admitted.current_work_reality_revision_id,
            observation_fingerprint=acquired["fingerprint"],
            authority_identity=branch_actor,
            rationale="Bind the acquired source repository before branch work.",
        ),
        acquired,
    )
    with pytest.raises(ProductInvariantViolation, match="Human-admitted branch action"):
        service.start_intake(RepositoryIntakeRequest(
            request_id=uuid4(),
            source=str(source_repository),
            title="Unadmitted branch",
            description="Must not execute from API parameters alone.",
            authority_identity=branch_actor,
            interaction_id=interaction_id,
            work_id=work_id,
            operation_kind="CREATE_BRANCH",
            base_resource_id=UUID(acquired["resource_id"]),
            target_branch="test",
        ))
    branch_interactions = WorkInteractionService(
        postgres_database,
        capability=_ExplicitBranchSemanticCapability(
            provider_variant=provider_variant,
            actual_provider_fact=actual_provider_fact,
        ),
    )
    pending = branch_interactions.append_and_assess(
        ready.interaction.id, "切一个新分支：test", human_identity="human:test",
    )
    proposal = pending.latest_assessment
    assert proposal is not None
    with postgres_database.unit_of_work() as uow:
        base_revision = ProductStore(uow.session).current_work_reality_revision(work_id)
    assert base_revision is not None
    if actual_provider_fact:
        steering_bootstrap = SteeringBootstrapService(postgres_database)
        orchestrator = ProductionOrchestrator(work_service)
        steering_driver = PlanSteeringDriver(
            postgres_database, work_service, orchestrator, repository_assets=service,
        )
        post_admission = WorkPostAdmissionService(
            work_service, steering_bootstrap, steering_driver, orchestrator,
        )
        trigger = ProductionAdmissionTrigger(
            branch_interactions, work_service, service, post_admission,
        )
        answer = trigger.execute_explicit_branch_turn(
            ready.interaction.id, proposal, pending.records[-1],
        )
        assert answer is not None and "已从当前仓库基线创建并绑定本地分支 test" in answer, {
            key: value for key, value in service.latest_attempt_for_work(work_id).items()
            if key in {"condition", "failure_category", "human_message", "technical_evidence"}
        }
        with postgres_database.unit_of_work() as uow:
            branch_revision = ProductStore(uow.session).current_work_reality_revision(work_id)
        assert branch_revision is not None
        assert branch_revision.repository_ref == "refs/heads/test"
        assert branch_revision.source_revision == acquired["revision"]
        assert branch_revision.constraints == base_revision.constraints
        assert branch_revision.desired_outcome == base_revision.desired_outcome
        assert service.latest_attempt_for_work(work_id)["condition"] == "READY"
        return
    governed = work_service.decide_interaction_work_revision(
        ready.interaction.id,
        assessment_id=proposal.id,
        basis_fingerprint=proposal.basis_fingerprint,
        expected_previous_revision_id=base_revision.id,
        action=AttentionAction.APPROVE,
        authority_identity=branch_actor,
        rationale="Admit the explicit branch request before execution.",
    )
    with postgres_database.unit_of_work() as uow:
        branch_revision = ProductStore(uow.session).current_work_reality_revision(work_id)
    assert branch_revision is not None
    subjects = {
        fact.subject for fact in current_semantic_facts(branch_revision.engineering_semantic_facts)
    }
    assert ("repository.branch.name" if actual_provider_fact else "repository.branch_name") in subjects
    if not provider_variant and not actual_provider_fact:
        assert "repository.branch_action" in subjects
    steering_bootstrap = SteeringBootstrapService(postgres_database)
    steering_bootstrap.bootstrap(work_id)
    orchestrator = ProductionOrchestrator(work_service)
    steering_driver = PlanSteeringDriver(
        postgres_database, work_service, orchestrator, repository_assets=service,
    )
    post_admission = WorkPostAdmissionService(
        work_service, steering_bootstrap, steering_driver, orchestrator,
    )
    trigger = ProductionAdmissionTrigger(interactions, work_service, service, post_admission)
    steering_driver.configure_governed_repository_action(
        lambda selected_work, selected_interaction, authority:
            trigger.reconcile_governed_branch(
                selected_work,
                interaction_id=selected_interaction,
                authority_identity=authority,
            )
    )
    iterations = []
    if provider_variant:
        original_run = service.native_git_operations._run_admitted_branch_operation

        def interrupted_after_admission(**_kwargs):
            raise RuntimeError("Synthetic Native Git setup interruption")

        monkeypatch.setattr(
            service.native_git_operations,
            "_run_admitted_branch_operation",
            interrupted_after_admission,
        )
        for _ in range(3):
            iteration = steering_driver.iterate(work_id)
            iterations.append(iteration)
            if iteration.action is SteeringActionType.REPOSITORY_ACTION:
                break
        failed = service.latest_attempt_for_work(work_id)
        assert failed is not None and failed["condition"] == "FAILED_RETRYABLE"
        with postgres_database.unit_of_work() as uow:
            run_id = uow.session.execute(
                select(production_runs.c.id).where(
                    production_runs.c.intent_ref == f"repository-intake:{failed['intake_request_id']}"
                )
            ).scalar_one()
            unit_id = uow.session.execute(
                select(production_work_units.c.id).where(
                    production_work_units.c.production_run_id == run_id
                )
            ).scalar_one()
            failed_attempt = RuntimeStore(uow.session).attempts_for_work_unit(unit_id)[-1]
            native_store = NativeExecutionStore(uow.session)
            assert native_store.attempt_state(failed_attempt.id).terminal_outcome is AttemptTerminalOutcome.CANCELLED
            assert native_store.queue_for_attempt(failed_attempt.id).condition is QueueCondition.CANCELLED
        monkeypatch.setattr(
            service.native_git_operations,
            "_run_admitted_branch_operation",
            original_run,
        )
        retried = trigger.retry_work(work_id, authority_identity=branch_actor)
        assert retried["condition"] == "READY", retried.get("technical_evidence")
    for _ in range(3):
        iteration = steering_driver.iterate(work_id)
        iterations.append(iteration)
        if iteration.action is SteeringActionType.REPOSITORY_ACTION:
            break
    if not provider_variant:
        assert any(item.action is SteeringActionType.REPOSITORY_ACTION for item in iterations)
    branch = service.latest_attempt_for_work(work_id)
    assert branch is not None
    assert branch["condition"] == "READY", branch.get("technical_evidence")
    with postgres_database.unit_of_work() as uow:
        product = ProductStore(uow.session)
        main_resource = product.resource(UUID(acquired["resource_id"]))
        branch_resource = product.resource(UUID(branch["resource_id"]))

    assert branch["condition"] == "READY"
    assert branch["operation_kind"] == "CREATE_BRANCH"
    assert branch["target_branch"] == "test"
    assert branch["repository_ref"] == "refs/heads/test"
    assert branch["revision"] == acquired["revision"]
    assert branch["operation_evidence"]["capability_id"] == "git.branch.create"
    assert branch["operation_evidence"]["connector_id"] == "builtin:git"
    assert branch["operation_evidence"]["resulting_branch"] == "refs/heads/test"
    assert branch["operation_evidence"]["resulting_revision"] == acquired["revision"]
    assert branch["operation_evidence"]["verified"] is True
    assert branch["operation_evidence"]["native_attempt_id"]
    assert branch["operation_evidence"]["pwu_id"]
    assert branch["operation_evidence"]["checkpoint_id"]
    with postgres_database.unit_of_work() as uow:
        native_binding = NativeExecutionStore(uow.session).attempt_binding(
            UUID(branch["operation_evidence"]["native_attempt_id"])
        )
        branch_pwu = RuntimeStore(uow.session).work_unit(
            UUID(branch["operation_evidence"]["pwu_id"])
        )
        steering_plan = SteeringStore(uow.session).plan_for_work(work_id)
        active_steering = SteeringStore(uow.session).active_revision(steering_plan.id)
    assert branch_pwu is not None and branch_pwu.completion_contract.task_contract is not None
    assert native_binding.binding.steering_decision_id == active_steering.id
    assert f"steering-plan-revision:{active_steering.id}" in (
        branch_pwu.completion_contract.task_contract.authority_lineage
    )
    resolver = ConnectorResolver(postgres_database)
    checkpoint_ref = f"native-checkpoint:{branch['operation_evidence']['checkpoint_id']}"
    resolver.register_learned(ExecutableCapability(
        capability_id="git.branch.create",
        connector_id="learned:native-git",
        capability_family="git",
        operation="branch.create",
        scope=CapabilityScope.WORK,
        owner_id=str(work_id),
        maturity=ConnectorMaturity.PROVISIONAL,
        availability=ConnectorAvailability.AVAILABLE,
        permissions_required=("work.branch.create",),
        side_effect_level=SideEffectLevel.WORKSPACE_MUTATION,
        execution_provider="native-tool:git.operation",
        version=f"1-{branch['intake_request_id'][:8]}",
        provenance=("qualified-native-git-branch",),
        created_from_work=work_id,
        verification_evidence=(checkpoint_ref,),
    ))
    retained = resolver.retain_successful_work_capability_for_user(
        CapabilityRequirement(
            capability_id="git.branch.create", work_id=work_id,
            user_id=branch_actor, operation_ref="task-contract:branch-inspect",
        ),
        successful_execution_evidence=checkpoint_ref,
    )
    assert retained is not None and retained.scope is CapabilityScope.USER
    assert any(item.scope is CapabilityScope.USER for item in resolver._overlays(CapabilityRequirement(
        capability_id="git.branch.create", work_id=uuid4(),
        user_id=branch_actor, operation_ref="task-contract:branch-inspect",
    )))
    assert not resolver._overlays(CapabilityRequirement(
        capability_id="git.branch.create", work_id=uuid4(),
        user_id="human:other", operation_ref="task-contract:branch-inspect",
    ))
    record_id = UUID(branch["operation_evidence"]["production_record_id"])
    assert service.native_git_operations.production_environment.store.get_git_operation_record(record_id).resulting_branch == "test"
    repeated = service.execute_intake(UUID(branch["intake_request_id"]))
    assert repeated["operation_evidence"]["production_record_id"] == str(record_id)
    assert repeated["operation_evidence"]["native_attempt_id"] == branch["operation_evidence"]["native_attempt_id"]
    assert branch_resource.repository_identity != main_resource.repository_identity
    assert _git(Path(main_resource.location_ref), "branch", "--show-current") == "main"
    assert _git(Path(branch_resource.location_ref), "branch", "--show-current") == "test"
    assert _git(Path(branch_resource.location_ref), "remote", "get-url", "origin") == str(source_repository)
    with postgres_database.unit_of_work() as uow:
        bound_revision = ProductStore(uow.session).current_work_reality_revision(work_id)
    assert bound_revision is not None
    assert bound_revision.repository_ref == "refs/heads/test"
    assert bound_revision.source_revision == branch["revision"]
    answer = _repository_branch_status_answer(
        "当前项目在哪个分支？", interactions.get_shared_understanding(ready.interaction.id)
    )
    assert answer is not None and "test" in answer and branch["revision"] in answer
    shadow = WorkInteractionService(
        postgres_database,
        capability=_ExplicitBranchSemanticCapability(provider_variant=True),
        runtime_mode=WicRuntimeMode.WIC_VNEXT_SHADOW,
    )
    try:
        turn = shadow.submit_turn(
            ready.interaction.id,
            "已经切好了吗？当前项目分支是啥？",
            human_identity="human:test",
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            state = shadow.get_turn(turn.id)
            if state.status in {InteractionTurnStatus.COMPLETED, InteractionTurnStatus.FAILED}:
                break
            time.sleep(0.01)
        assert state.status is InteractionTurnStatus.COMPLETED, state.failure_message
        response = shadow.get_shared_understanding(ready.interaction.id).conversation_messages[-1].content
        assert "本地分支是 test" in response
        assert branch["revision"] in response
        assert "推送到远端" in response
    finally:
        shadow.shutdown()


def test_restart_resumes_persisted_repository_attempt_without_current_assessment() -> None:
    interaction_id = uuid4()
    work_id = uuid4()
    assessment = object()
    request_record = SimpleNamespace(actor=InteractionActor.HUMAN)
    projection = SimpleNamespace(
        interaction=SimpleNamespace(id=interaction_id),
        latest_assessment=assessment,
        latest_assessment_current=False,
        records=(request_record,),
        governed_work_id=work_id,
    )

    class RecoveryHarness:
        def __init__(self) -> None:
            self._turn_lock = RLock()
            self._production_admission_reality_provider = (
                lambda selected_interaction_id, selected_work_id: (
                    ProductionAdmissionExecutionState.WORK_CREATED,
                    RepositoryAcquisitionState.REQUESTED,
                    "Start the persisted repository acquisition operation.",
                    "https://github.com/acme/repository.git",
                )
            )
            self.executed: list[tuple[object, object, object]] = []

        def list_interactions(self):
            return (projection,)

        def _execute_prepared_production_admission(
            self, selected_interaction_id, selected_assessment, selected_request
        ):
            self.executed.append(
                (
                    selected_interaction_id,
                    selected_assessment,
                    selected_request,
                )
            )
            return True

    harness = RecoveryHarness()

    resumed = WorkInteractionService.resume_ready_production_admissions(harness)

    assert resumed == (interaction_id,)
    assert harness.executed == [(interaction_id, assessment, request_record)]


def test_repository_acquisition_accepts_extensionless_readme_context(
    postgres_database: Database,
    tmp_path: Path,
) -> None:
    import_root = tmp_path / "imports"
    import_root.mkdir()
    source_repository = import_root / "extensionless-readme"
    source_repository.mkdir()
    _git(source_repository, "init", "-b", "main")
    _git(source_repository, "config", "user.name", "SPG Test")
    _git(source_repository, "config", "user.email", "spg-test@example.invalid")
    (source_repository / "README").write_text("Repository overview\n", encoding="utf-8")
    _git(source_repository, "add", ".")
    _git(source_repository, "commit", "-m", "baseline")

    service = RepositoryAssetService(
        postgres_database,
        tmp_path / "assets",
        import_root,
    )
    observation = service.intake(
        RepositoryIntakeRequest(
            request_id=uuid4(),
            source=str(source_repository),
            title="Extensionless README repository",
            description="Acquire a valid repository without requiring Markdown.",
        authority_identity="human:governor",
            interaction_id=uuid4(),
            work_id=uuid4(),
            attempt_number=1,
        )
    )

    assert observation["condition"] == "READY"
    assert observation["context_path"] == "README"
    assert observation["paths"] == ["README"]


@pytest.mark.parametrize(
    "content",
    (
        "How do I add a feature to GitHub projects?",
        "I want to build something like Airbnb.",
    ),
)
def test_advisory_and_exploration_turns_do_not_auto_admit_work(
    postgres_database: Database,
    tmp_path: Path,
    content: str,
) -> None:
    work, interactions = _services_for_resource(
        postgres_database,
        tmp_path,
        "test://non-production-turn",
    )
    client = TestClient(
        create_http_application(
            application=object(),
            database=postgres_database,
            work_service=work,
            orchestrator=_NoopOrchestrator(),
            steering_driver=_RecordingDriver(),
            runtime_activation=_RuntimeActivation(),
            interaction_service=interactions,
        ),
        raise_server_exceptions=False,
    )
    interaction = interactions.create_interaction(
        human_identity="human:requester",
        start_work_context=True,
    )
    with client:
        response = client.post(
            f"/api/interactions/{interaction.id}/turns",
            json={"content": content, "human_identity": "human:requester"},
        )
        assert response.status_code == 202, response.text
        turn_id = response.json()["turn_id"]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            turn = client.get(
                f"/api/interactions/{interaction.id}/turns/{turn_id}"
            ).json()
            if turn["status"] in {"COMPLETED", "FAILED"}:
                break
            time.sleep(0.01)
        payload = client.get(
            f"/api/interactions/{interaction.id}/shared-understanding"
        ).json()

    assert turn["status"] == "COMPLETED"
    assert payload["governed_work_id"] is None


@pytest.mark.real_codex
def test_guided_design_real_provider_leads_multi_step_design_without_production(
    postgres_database: Database,
    services,
) -> None:
    if os.environ.get("SPG_RUN_REAL_GUIDED_DESIGN") != "1":
        pytest.skip(
            "set SPG_RUN_REAL_GUIDED_DESIGN=1 for the authorized Guided Design proof"
        )
    work, _interactions = services
    interactions = WorkInteractionService(
        postgres_database,
        capability=_GeneralProductDesignCapability(),
    )
    interaction = interactions.create_interaction(human_identity="human:proof")
    shared = interactions.append_and_assess(
        interaction.id,
        "我想做一个运营管理平台。",
        human_identity="human:proof",
    )
    shared = interactions.append_and_assess(
        interaction.id,
        (
            "这个平台主要服务中小团队的运营负责人和一线运营人员，解决计划、"
            "执行、结果反馈分散而难以形成闭环的问题。第一阶段希望让团队能从"
            "运营目标形成计划、跟踪执行并把结果反馈到下一轮计划；不包含完整"
            "企业 ERP、财务结算或大规模组织权限重构。"
        ),
        human_identity="human:proof",
    )
    assert shared.latest_assessment is not None
    admitted = work.admit_interaction_work(
        interaction.id,
        assessment_id=shared.latest_assessment.id,
        basis_fingerprint=shared.latest_assessment.basis_fingerprint,
        authority_identity="human:guided-design-proof",
        rationale="Admit the bounded product-design proof, not production.",
    )
    plan = SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)
    orchestrator = ProductionOrchestrator(work)
    driver = PlanSteeringDriver(
        postgres_database,
        work,
        orchestrator,
        semantic_capability=CodexSdkSemanticStepCapability(timeout_seconds=180),
        max_automatic_transitions=32,
    )
    try:
        outcome = driver.activate(admitted.work_id)
    finally:
        orchestrator.shutdown()
        driver.shutdown()

    reconstructed = SteeringApplicationService(postgres_database).reconstruct(
        admitted.work_id
    )
    guided = GuidedDesignApplicationService(postgres_database).get(admitted.work_id)
    assert reconstructed.steering_plan_id == plan.steering_plan_id
    assert len(reconstructed.semantic_results) >= 2
    assert len(
        [issue for issue in guided.issues if issue.state is DesignIssueState.SATISFIED]
    ) >= 2
    assert guided.agenda_revision_number >= 3
    assert outcome.stop_reason.value == "HUMAN_ATTENTION"
    assert guided.current_focus is not None
    attention = work.list_attention(work_id=admitted.work_id)
    assert attention
    print(
        "GUIDED_DESIGN_REAL_PROOF",
        {
            "semantic_results": len(reconstructed.semantic_results),
            "agenda_revision": guided.agenda_revision_number,
            "satisfied_issues": [
                issue.key
                for issue in guided.issues
                if issue.state is DesignIssueState.SATISFIED
            ],
            "current_focus": guided.current_focus_key,
            "readiness": guided.readiness.state.value,
            "attention_kind": attention[0].kind.value,
            "provider_threads": len(reconstructed.semantic_results),
            "provider_turns": len(reconstructed.semantic_results),
        },
    )
    for table in PRODUCTION_TABLES:
        assert _count(postgres_database, table) == 0, table.name


@pytest.mark.parametrize(
    ("focus", "impact", "status"),
    (
        (
            WorkFocusClassification.SIDE_QUESTION,
            WorkImpactDisposition.NO_GOVERNED_CHANGE,
            WorkRevisionAdmissionStatus.NOT_APPLICABLE,
        ),
        (
            WorkFocusClassification.RELEVANT_EXPLORATION,
            WorkImpactDisposition.NO_GOVERNED_CHANGE,
            WorkRevisionAdmissionStatus.NOT_APPLICABLE,
        ),
        (
            WorkFocusClassification.MATERIAL_BRANCH,
            WorkImpactDisposition.NEW_WORK_RECOMMENDED,
            WorkRevisionAdmissionStatus.NEW_WORK_RECOMMENDED,
        ),
        (
            WorkFocusClassification.UNRELATED_NEW_DEMAND,
            WorkImpactDisposition.NEW_WORK_RECOMMENDED,
            WorkRevisionAdmissionStatus.NEW_WORK_RECOMMENDED,
        ),
    ),
)
def test_wic3_focus_preservation_never_silently_mutates_work(
    postgres_database: Database,
    services,
    focus: WorkFocusClassification,
    impact: WorkImpactDisposition,
    status: WorkRevisionAdmissionStatus,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    admitted = _admit(work, ready)
    original = interactions.get_shared_understanding(ready.interaction.id).governed_revision
    assert original is not None

    active = WorkInteractionService(
        postgres_database,
        capability=_ActiveCapability(
            focus=focus,
            impact=impact,
            motive="A different objective that must not drift into current Work",
            context_fact="Candidate context that must not auto-admit",
        ),
    )
    result = active.append_and_assess(
        ready.interaction.id,
        "Can we explore an adjacent concern without changing this Work?",
        human_identity="human:test",
    )

    assert result.governed_work_id == admitted.work_id
    assert result.current_work_focus == (
        f"{original.motive} → {original.desired_outcome}"
    )
    assert result.focus_classification is focus
    assert result.impact_disposition is impact
    assert result.candidate_change is None
    assert result.work_revision_admission_status is status
    assert result.governed_revision == original
    assert _count(postgres_database, work_reality_revisions) == 1
    assert work.list_attention(work_id=admitted.work_id) == ()


@pytest.mark.parametrize(
    ("human_text", "focus", "impact", "meaning", "change_kwargs", "changed_field", "status"),
    (
        (
            "New runtime fact: the deployment region is Shanghai.",
            WorkFocusClassification.ON_TOPIC,
            WorkImpactDisposition.CURRENT_CYCLE_REMAINS_VALID,
            InterpretationMeaningKind.FACT,
            {"context_fact": "Deployment region is Shanghai."},
            "context_facts",
            WorkRevisionAdmissionStatus.PENDING_HUMAN,
        ),
        (
            "The service must keep all customer data in mainland China.",
            WorkFocusClassification.ON_TOPIC,
            WorkImpactDisposition.CURRENT_RESULT_MAY_BE_INSUFFICIENT,
            InterpretationMeaningKind.CONSTRAINT,
            {"constraint": "Customer data must remain in mainland China."},
            "constraints",
            WorkRevisionAdmissionStatus.PENDING_HUMAN,
        ),
        (
            "Correction: the target is a backend system, not a campaign.",
            WorkFocusClassification.ON_TOPIC,
            WorkImpactDisposition.CURRENT_RESULT_MAY_BE_INSUFFICIENT,
            InterpretationMeaningKind.CORRECTION,
            {"context_fact": "The target is a backend system, not a campaign."},
            "context_facts",
            WorkRevisionAdmissionStatus.PENDING_HUMAN,
        ),
        (
            "Please use an incremental migration for this local approach.",
            WorkFocusClassification.ON_TOPIC,
            WorkImpactDisposition.DEFER_TO_PRODUCTION_BOUNDARY,
            InterpretationMeaningKind.REQUEST,
            {"request": "Use an incremental migration."},
            "requests",
            WorkRevisionAdmissionStatus.PENDING_HUMAN,
        ),
        (
            "Separately, build an unrelated billing analytics product.",
            WorkFocusClassification.UNRELATED_NEW_DEMAND,
            WorkImpactDisposition.NEW_WORK_RECOMMENDED,
            InterpretationMeaningKind.NEW_WORK_CANDIDATE,
            {"motive": "Build a billing analytics product."},
            None,
            WorkRevisionAdmissionStatus.NEW_WORK_RECOMMENDED,
        ),
    ),
)
def test_q36_five_human_steering_kinds_receive_exact_durable_dispositions(
    postgres_database: Database,
    services,
    human_text: str,
    focus: WorkFocusClassification,
    impact: WorkImpactDisposition,
    meaning: InterpretationMeaningKind,
    change_kwargs: dict[str, str],
    changed_field: str | None,
    status: WorkRevisionAdmissionStatus,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    admitted = _admit(work, ready)
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)
    binding, _ = _bind_active_cycle(postgres_database, admitted)
    active = WorkInteractionService(
        postgres_database,
        capability=_ActiveCapability(
            focus=focus, impact=impact, meaning=meaning, **change_kwargs
        ),
    )

    result = active.append_and_assess(
        ready.interaction.id,
        human_text,
        human_identity="human:q36",
    )
    assessment = result.latest_assessment

    assert assessment is not None
    assert assessment.basis_active_runtime_binding_id == binding.id
    assert assessment.focus_classification is focus
    assert assessment.impact_disposition is impact
    assert result.work_revision_admission_status is status
    assert assessment.meanings[0].kind is meaning
    if changed_field is None:
        assert assessment.candidate_change is None
    else:
        assert assessment.candidate_change is not None
        assert changed_field in assessment.candidate_change.changed_fields
        if changed_field == "constraints":
            assert assessment.candidate_change.scope_change_required is True


def test_wic3_human_governed_revision_is_append_only_exact_and_idempotent(
    postgres_database: Database,
    services,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    admitted = _admit(work, ready)
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)
    old_revision = interactions.get_shared_understanding(
        ready.interaction.id
    ).governed_revision
    assert old_revision is not None
    old_snapshot = old_revision.model_dump(mode="json")
    evidence_id = uuid4()
    active = WorkInteractionService(
        postgres_database,
        capability=_ActiveCapability(
            focus=WorkFocusClassification.ON_TOPIC,
            impact=WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED,
            context_fact="Observed feedback requires history visibility.",
            constraint="Do not widen the backend Runtime boundary.",
            meaning=InterpretationMeaningKind.FEEDBACK,
        ),
    )
    pending = active.append_and_assess(
        ready.interaction.id,
        "I tested it and still cannot see the execution history.",
        human_identity="human:test",
        supporting_references=(f"VERIFICATION:{evidence_id}",),
    )
    assessment = pending.latest_assessment
    assert assessment is not None
    assert assessment.basis_work_revision_id == old_revision.id
    assert pending.focus_classification is WorkFocusClassification.ON_TOPIC
    assert pending.work_revision_admission_status is WorkRevisionAdmissionStatus.PENDING_HUMAN
    assert assessment.candidate_change is not None
    assert set(assessment.candidate_change.changed_fields) == {
        "context_facts",
        "constraints",
    }
    assert f"VERIFICATION:{evidence_id}" in assessment.supporting_references
    assert _count(postgres_database, work_reality_revisions) == 1
    for table in PRODUCTION_TABLES:
        assert _count(postgres_database, table) == 0, table.name

    attention = work.list_attention(work_id=admitted.work_id)
    assert len(attention) == 1
    assert attention[0].kind.value == "WORK_REVISION_APPROVAL"
    with pytest.raises(InteractionInvariantViolation, match="stale"):
        work.decide_interaction_work_revision(
            ready.interaction.id,
            assessment_id=assessment.id,
            basis_fingerprint=assessment.basis_fingerprint,
            expected_previous_revision_id=uuid4(),
            action=AttentionAction.APPROVE,
            authority_identity="human:governor",
        )

    evolved = work.decide_interaction_work_revision(
        ready.interaction.id,
        assessment_id=assessment.id,
        basis_fingerprint=assessment.basis_fingerprint,
        expected_previous_revision_id=old_revision.id,
        action=AttentionAction.APPROVE,
        authority_identity="human:governor",
        rationale="Admit exact tested feedback and bounded constraint.",
    )
    with postgres_database.unit_of_work() as unit_of_work:
        history = ProductStore(unit_of_work.session).work_reality_revisions(
            admitted.work_id
        )
    assert len(history) == 2
    assert history[0].model_dump(mode="json") == old_snapshot
    current = history[1]
    assert current.id == evolved.current_work_reality_revision_id
    assert current.revision_number == 2
    assert current.previous_revision_id == old_revision.id
    assert current.source_interaction_id == ready.interaction.id
    assert current.source_assessment_id == assessment.id
    assert current.source_record_ids[-1] == pending.records[-1].id
    assert current.governance_record_id is not None
    assert current.engineering_scope_id != old_revision.engineering_scope_id
    assert current.scope_basis_fingerprint != old_revision.scope_basis_fingerprint
    assert f"VERIFICATION:{evidence_id}" in current.supporting_references
    assert set(current.change_set) >= {
        "context_facts",
        "constraints",
        "impact:HUMAN_GOVERNANCE_REQUIRED",
    }

    repeated = work.decide_interaction_work_revision(
        ready.interaction.id,
        assessment_id=assessment.id,
        basis_fingerprint=assessment.basis_fingerprint,
        expected_previous_revision_id=old_revision.id,
        action=AttentionAction.APPROVE,
        authority_identity="human:governor",
    )
    assert repeated.current_work_reality_revision_id == current.id
    assert _count(postgres_database, work_reality_revisions) == 2
    with pytest.raises(ProductInvariantViolation, match="different Human decision"):
        work.decide_interaction_work_revision(
            ready.interaction.id,
            assessment_id=assessment.id,
            basis_fingerprint=assessment.basis_fingerprint,
            expected_previous_revision_id=old_revision.id,
            action=AttentionAction.REJECT,
            authority_identity="human:governor",
        )

    frame = PlanFrameAssembler(postgres_database).assemble(admitted.work_id)
    assert frame.work_reality_revision_id == current.id
    assert any(
        item.reference.kind is RealityReferenceKind.WORK_REALITY_REVISION
        and item.reference.identity == current.id
        for item in frame.basis.resolved_reality
    )


def test_wic3_stale_assessment_cannot_mutate_newer_interaction_reality(
    postgres_database: Database,
    services,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    admitted = _admit(work, ready)
    active = WorkInteractionService(
        postgres_database,
        capability=_ActiveCapability(
            focus=WorkFocusClassification.ON_TOPIC,
            context_fact="Candidate fact one.",
        ),
    )
    pending = active.append_and_assess(
        ready.interaction.id,
        "First feedback candidate.",
        human_identity="human:test",
    )
    assessment = pending.latest_assessment
    assert assessment is not None
    assert assessment.basis_work_revision_id is not None
    active.append_human_input(
        ready.interaction.id,
        "A newer Human message changes the assessment basis.",
        human_identity="human:test",
    )
    with pytest.raises(InteractionInvariantViolation, match="stale"):
        work.decide_interaction_work_revision(
            ready.interaction.id,
            assessment_id=assessment.id,
            basis_fingerprint=assessment.basis_fingerprint,
            expected_previous_revision_id=assessment.basis_work_revision_id,
            action=AttentionAction.APPROVE,
            authority_identity="human:governor",
        )
    assert _count(postgres_database, work_reality_revisions) == 1
    assert work.get_work(admitted.work_id).current_work_reality_revision_id == (
        assessment.basis_work_revision_id
    )


def test_wic3_interrupted_assessment_recovers_without_provider_invented_evidence(
    postgres_database: Database,
    services,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    admitted = _admit(work, ready)
    interactions.append_human_input(
        ready.interaction.id,
        "Record this bounded contextual clarification.",
        human_identity="human:test",
    )
    invalid = WorkInteractionService(
        postgres_database,
        capability=_InventedReferenceCapability(
            focus=WorkFocusClassification.ON_TOPIC,
            context_fact="Recovered contextual clarification.",
        ),
    )
    with pytest.raises(
        InteractionInvariantViolation,
        match="cannot invent supporting Reality references",
    ):
        invalid.assess_current(ready.interaction.id)
    assert invalid.pending_assessment_interactions() == (ready.interaction.id,)
    assert _count(postgres_database, work_reality_revisions) == 1

    recovered = WorkInteractionService(
        postgres_database,
        capability=_ActiveCapability(
            focus=WorkFocusClassification.ON_TOPIC,
            context_fact="Recovered contextual clarification.",
        ),
    )
    assessment = recovered.assess_current(ready.interaction.id)
    assert assessment.basis_work_revision_id == admitted.current_work_reality_revision_id
    assert assessment.candidate_change is not None
    assert recovered.pending_assessment_interactions() == ()


@pytest.mark.parametrize(
    "impact",
    (
        WorkImpactDisposition.CURRENT_RESULT_MAY_BE_INSUFFICIENT,
        WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED,
    ),
)
def test_wic3_active_cycle_remains_bound_to_old_revision_and_input_is_not_injected(
    postgres_database: Database,
    services,
    impact: WorkImpactDisposition,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    admitted = _admit(work, ready)
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)
    old_revision_id = admitted.current_work_reality_revision_id
    assert old_revision_id is not None
    binding, spine = _bind_active_cycle(postgres_database, admitted)
    run_before = _table_row(postgres_database, production_runs, spine.run.id)
    pwu_before = _table_row(postgres_database, production_work_units, spine.work_unit.id)

    active = WorkInteractionService(
        postgres_database,
        capability=_ActiveCapability(
            focus=WorkFocusClassification.ON_TOPIC,
            impact=impact,
            context_fact="Runtime feedback says the active result may be insufficient.",
            meaning=InterpretationMeaningKind.FEEDBACK,
        ),
    )
    pending = active.append_and_assess(
        ready.interaction.id,
        "The running result may not satisfy the newly observed behavior.",
        human_identity="human:test",
        supporting_references=(f"RUNTIME_FACT:{uuid4()}",),
    )
    assessment = pending.latest_assessment
    assert assessment is not None
    assert assessment.basis_work_revision_id == old_revision_id
    assert assessment.basis_active_runtime_binding_id == binding.id
    assert pending.active_cycle_work_revision_id == old_revision_id
    assert pending.active_cycle_impact_disposition is impact

    evolved = work.decide_interaction_work_revision(
        ready.interaction.id,
        assessment_id=assessment.id,
        basis_fingerprint=assessment.basis_fingerprint,
        expected_previous_revision_id=old_revision_id,
        action=AttentionAction.APPROVE,
        authority_identity="human:governor",
    )
    assert evolved.current_work_reality_revision_id != old_revision_id
    with postgres_database.unit_of_work() as unit_of_work:
        stored = ProductStore(unit_of_work.session).runtime_binding(admitted.work_id)
    assert stored is not None
    assert stored.id == binding.id
    assert stored.work_reality_revision_id == old_revision_id
    assert stored.engineering_scope_id == binding.engineering_scope_id
    assert stored.production_run_id == binding.production_run_id
    assert stored.plan_revision_id == binding.plan_revision_id
    assert stored.work_unit_id == binding.work_unit_id
    assert _table_row(postgres_database, production_runs, spine.run.id) == run_before
    assert _table_row(postgres_database, production_work_units, spine.work_unit.id) == pwu_before
    assert _count(postgres_database, execution_attempts) == 0
    assert _count(postgres_database, execution_dispatches) == 0
    assert _count(postgres_database, materialized_execution_inputs) == 0
    frame = PlanFrameAssembler(postgres_database).assemble(admitted.work_id)
    assert frame.completion_evidence_sufficient is False
    assert any(
        blocker.kind.value == "CURRENT_RESULT_MAY_BE_INSUFFICIENT"
        and any(
            reference.kind is RealityReferenceKind.WORK_REALITY_REVISION
            and reference.identity == evolved.current_work_reality_revision_id
            for reference in blocker.reality_refs
        )
        for blocker in frame.open_blocking_reality
    )


def test_wic3_revision_api_triggers_existing_steering_driver_only_after_approval(
    postgres_database: Database,
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    admitted = _admit(work, ready)
    SteeringBootstrapService(postgres_database).bootstrap(admitted.work_id)
    active = WorkInteractionService(
        postgres_database,
        capability=_ActiveCapability(
            focus=WorkFocusClassification.ON_TOPIC,
            impact=WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED,
            context_fact="One bounded clarification for Plan reassessment.",
        ),
    )
    pending = active.append_and_assess(
        ready.interaction.id,
        "Please incorporate this bounded clarification.",
        human_identity="human:test",
    )
    assessment = pending.latest_assessment
    assert assessment is not None
    assert assessment.basis_work_revision_id is not None
    monkeypatch.setattr(
        WorkPostAdmissionService,
        "activate",
        lambda *_args, **_kwargs: pytest.fail(
            "A Work revision must not re-enter first-admission activation"
        ),
    )
    driver = _RecordingDriver()
    client = TestClient(
        create_http_application(
            application=object(),
            database=postgres_database,
            work_service=work,
            orchestrator=_NoopOrchestrator(),
            steering_driver=driver,
            runtime_activation=_RuntimeActivation(),
            interaction_service=active,
        ),
        raise_server_exceptions=False,
    )
    with client:
        assert driver.scheduled == []
        response = client.post(
            f"/api/interactions/{ready.interaction.id}/work-revision-decisions",
            json={
                "assessment_id": str(assessment.id),
                "basis_fingerprint": assessment.basis_fingerprint,
                "expected_previous_revision_id": str(
                    assessment.basis_work_revision_id
                ),
                "action": "APPROVE",
                "authority_identity": "human:governor",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["work_revision_admission_status"] == "ADMITTED"
        assert driver.scheduled == [admitted.work_id]
        assert _count(postgres_database, work_reality_revisions) == 2
        assert _count(postgres_database, production_runs) == 0


def _transition_current_steering_step(database: Database, work_id: UUID):
    decisions = SteeringDecisionApplicationService(
        database,
        DeterministicPlanSteeringCapability(),
    )
    frame, candidate = decisions.evaluate(work_id)
    decision = decisions.admit(work_id, candidate)
    current = frame.reconstruction.current_step
    next_step = frame.reconstruction.next_step
    assert current is not None
    assert next_step is not None
    return SteeringApplicationService(database).transition_step(
        TransitionSteeringStepRequest(
            steering_plan_revision_id=(
                frame.reconstruction.active_revision.revision.id
            ),
            current_step_id=current.id,
            next_step_id=next_step.id,
            steering_decision_id=decision.id,
        )
    )


def _complete_wic_work(
    database: Database,
    original_work_service: WorkApplicationService,
    admitted,
) -> WorkApplicationService:
    scope = admitted.engineering_scope
    assert scope is not None
    baseline = RuntimeService(database).current_baseline()
    artifact = ProductionPlanArtifactTarget(
        path="docs/wic-slice-4-result.md",
        operation=PlannedArtifactOperation.CREATE,
    )
    plan = ProductionPlanProposal(
        proposal_id=uuid4(),
        target_kind=ProductionTargetKind.DOCUMENTATION_WORK,
        objective=admitted.desired_outcome or admitted.raw_user_requirement,
        desired_outcome=admitted.desired_outcome or admitted.raw_user_requirement,
        ordered_steps=(
            ProductionPlanStep(position=1, instruction="Produce the exact artifact."),
            ProductionPlanStep(position=2, instruction="Verify the exact artifact."),
        ),
        artifact_targets=(artifact,),
        inherited_constraints=admitted.constraints,
        verification_approach="Verify the admitted artifact",
        fit_classification=OnePwuFitClassification.ONE_PWU_FIT,
        engineering_resource_id=scope.bindings[0].resource_id,
        repository_identity=baseline.repository_identity,
        source_baseline_id=baseline.id,
        source_revision=baseline.repository_revision,
    )
    with database.unit_of_work() as unit_of_work:
        ProductStore(unit_of_work.session).update_work(
            admitted.work_id,
            {
                "expected_artifact_path": artifact.path,
                "artifact_operation": ArtifactTargetOperation.CREATE.value,
                "artifact_placement_rationale": (
                    "Deterministic Slice 4 completion fixture."
                ),
                "artifact_target_confidence": ArtifactTargetConfidence.HIGH.value,
                "artifact_source_baseline_id": baseline.id,
                "artifact_source_revision": baseline.repository_revision,
                "verification_expectation": "Verify the admitted artifact",
                "production_plan_proposal": plan.model_dump(mode="json"),
                "updated_at": datetime.now(UTC),
            },
        )
        unit_of_work.commit()

    SteeringApplicationService(database).create_plan(
        CreateSteeringPlanRequest(
            work_id=admitted.work_id,
            rationale="Exercise the exact Slice 4 completion lifecycle.",
            steps=(
                SteeringStepSpec(
                    type=SteeringStepType.PRODUCE,
                    objective="Produce the exact Slice 4 artifact",
                    completion_condition="The artifact reaches trusted Runtime Commit",
                    state=SteeringStepState.CURRENT,
                ),
                SteeringStepSpec(
                    type=SteeringStepType.VERIFY_ACCEPT,
                    objective="Accept the governed result",
                    completion_condition="Persisted verification evidence passes",
                ),
                SteeringStepSpec(
                    type=SteeringStepType.COMPLETE,
                    objective="Recognize current Work satisfaction",
                    completion_condition="The current Work objective is satisfied",
                ),
            ),
        )
    )
    bridge = SteeringProductionService(database)
    admission = bridge.admit_cycle(bridge.materialize_request(admitted.work_id))
    assert admission.binding is not None

    work_service = WorkApplicationService(
        database,
        workspace_root=original_work_service.workspace_root,
        executor=DeterministicTestExecutor(
            DeterministicExecutionSpecification(
                operations=(
                    DeterministicFileOperation(
                        operation=DeterministicFileOperationType.CREATE,
                        repository_relative_path=artifact.path,
                        content="# WIC Slice 4 completed result\n",
                    ),
                ),
                reported_outcome=ProviderReportedOutcome.SUCCESS,
                summary="deterministic WIC Slice 4 completion",
            )
        ),
        verifier=DeterministicVerificationProvider(
            {"Verify the admitted artifact": VerificationResultValue.PASS}
        ),
    )
    orchestrator = ProductionOrchestrator(work_service)
    first = orchestrator.orchestrate(admitted.work_id)
    assert first.work_status is WorkStatus.NEEDS_ATTENTION
    attention = work_service.list_attention(work_id=admitted.work_id)
    assert len(attention) == 1
    assert attention[0].kind is AttentionKind.CANDIDATE_AUTHORIZATION
    work_service.resolve_attention(
        attention[0].id,
        AttentionResolutionRequest(
            action=AttentionAction.AUTHORIZE,
            authority_identity="human:wic-slice-4-test",
        ),
    )
    second = orchestrator.orchestrate(admitted.work_id)
    assert second.stop_reason is OrchestrationStopReason.PRODUCTION_CYCLE_TRUSTED
    assert _transition_current_steering_step(
        database, admitted.work_id
    ).current_step.type is SteeringStepType.VERIFY_ACCEPT
    completed = _transition_current_steering_step(database, admitted.work_id)
    assert completed.current_step.type is SteeringStepType.COMPLETE
    assert work_service.get_work(admitted.work_id).status is WorkStatus.COMPLETED
    return work_service


def test_wic4_completed_work_continuation_reopens_satisfaction_without_rewriting_completion(
    postgres_database: Database,
    services,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    admitted = _admit(work, ready)
    completed_work = _complete_wic_work(postgres_database, work, admitted)
    completed_projection = completed_work.get_work(admitted.work_id)
    trusted_commit_id = completed_projection.latest_trusted_runtime_commit_id
    assert trusted_commit_id is not None

    active = WorkInteractionService(
        postgres_database,
        capability=_ActiveCapability(
            focus=WorkFocusClassification.ON_TOPIC,
            impact=WorkImpactDisposition.CURRENT_RESULT_MAY_BE_INSUFFICIENT,
            constraint="Elapsed time must be clearer in the same Work experience.",
        ),
    )
    before = active.get_shared_understanding(ready.interaction.id)
    assert before.work_satisfaction_state is WorkSatisfactionState.CURRENTLY_SATISFIED
    assert before.interaction_relationship_state.value == "OPEN"

    pending = active.append_and_assess(
        ready.interaction.id,
        "Can we also show elapsed time more clearly?",
        human_identity="human:test",
    )
    assessment = pending.latest_assessment
    old_revision = pending.governed_revision
    assert assessment is not None
    assert old_revision is not None
    assert pending.work_revision_admission_status is WorkRevisionAdmissionStatus.PENDING_HUMAN
    assert pending.work_satisfaction_state is WorkSatisfactionState.CURRENTLY_SATISFIED
    production_counts = {
        table.name: _count(postgres_database, table)
        for table in PRODUCTION_TABLES
    }

    driver = _RecordingDriver()
    client = TestClient(
        create_http_application(
            application=object(),
            database=postgres_database,
            work_service=completed_work,
            orchestrator=_NoopOrchestrator(),
            steering_driver=driver,
            runtime_activation=_RuntimeActivation(),
            interaction_service=active,
        ),
        raise_server_exceptions=False,
    )
    with client:
        response = client.post(
            f"/api/interactions/{ready.interaction.id}/work-revision-decisions",
            json={
                "assessment_id": str(assessment.id),
                "basis_fingerprint": assessment.basis_fingerprint,
                "expected_previous_revision_id": str(old_revision.id),
                "action": "APPROVE",
                "authority_identity": "human:governor",
            },
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["work_satisfaction_state"] == "IN_PROGRESS"
    assert payload["interaction_relationship_state"] == "OPEN"
    assert payload["governed_revision"]["revision_number"] == 2
    assert "satisfaction:REOPENED" in payload["governed_revision"]["change_set"]
    assert driver.scheduled == [admitted.work_id]

    evolved = completed_work.get_work(admitted.work_id)
    assert evolved.status is WorkStatus.READY
    assert evolved.work_complete is False
    assert evolved.latest_trusted_runtime_commit_id == trusted_commit_id
    assert evolved.current_production_run_id is None
    assert evolved.what_happens_next == (
        "Reassess the governed Plan against the latest Work Reality revision"
    )
    current_result = completed_work.get_work_result(admitted.work_id)
    assert current_result.produced_artifacts == ()
    assert current_result.verification_summary == ()
    assert current_result.repository_state is None
    assert current_result.trusted_result is False
    with postgres_database.unit_of_work() as unit_of_work:
        history = ProductStore(unit_of_work.session).work_reality_revisions(
            admitted.work_id
        )
    assert len(history) == 2
    assert history[0] == old_revision
    assert history[1].previous_revision_id == old_revision.id
    assert {
        table.name: _count(postgres_database, table)
        for table in PRODUCTION_TABLES
    } == production_counts
    frame = PlanFrameAssembler(postgres_database).assemble(admitted.work_id)
    assert frame.work_reality_revision_id == history[1].id
    assert frame.completion_evidence_sufficient is False
    assert any(
        blocker.kind.value == "CURRENT_RESULT_MAY_BE_INSUFFICIENT"
        for blocker in frame.open_blocking_reality
    )

    orchestrator = _SchedulingOrchestrator()
    steering_driver = PlanSteeringDriver(
        postgres_database,
        completed_work,
        orchestrator,
    )
    try:
        assert steering_driver._restart_eligible(admitted.work_id) is True
        iteration = steering_driver.iterate(admitted.work_id)
        assert iteration.action is SteeringActionType.PLAN_REVISION
        assert iteration.progressed is True
        reassessed = SteeringApplicationService(postgres_database).reconstruct(
            admitted.work_id
        )
        assert reassessed.active_revision.revision.revision_number == 2
        assert reassessed.current_step is not None
        assert reassessed.current_step.type is SteeringStepType.DESIGN
        assert [step.type for step in reassessed.known_future_steps] == [
            SteeringStepType.PRODUCE,
            SteeringStepType.VERIFY_ACCEPT,
            SteeringStepType.COMPLETE,
        ]
        assert RealityReference(
            kind=RealityReferenceKind.WORK_REALITY_REVISION,
            identity=history[1].id,
        ) in reassessed.active_revision.revision.reality_refs
        assert not PlanFrameAssembler(postgres_database).assemble(
            admitted.work_id
        ).open_blocking_reality

        capability = _UnguidedSemanticCapability()
        semantics = SemanticStepApplicationService(
            postgres_database,
            capability,
            work_service=completed_work,
        )
        first_result = semantics.execute(admitted.work_id)
        second_result = semantics.execute(admitted.work_id)
        assert second_result.id == first_result.id
        assert len(capability.inputs) == 1
        assert capability.inputs[0].production_proposal_required is True
        assert first_result.proposed_production is not None
        assert completed_work.get_work(admitted.work_id).production_plan is not None
        decision_frame = PlanFrameAssembler(postgres_database).assemble(
            admitted.work_id
        )
        assert RealityReference(
            kind=RealityReferenceKind.SEMANTIC_RESULT,
            identity=first_result.id,
        ) in tuple(
            item.reference for item in decision_frame.basis.resolved_reality
        )
        continued = steering_driver.iterate(admitted.work_id)
        assert continued.action is SteeringActionType.STEP_TRANSITION
        assert (
            SteeringApplicationService(postgres_database)
            .reconstruct(admitted.work_id)
            .current_step.type
            is SteeringStepType.PRODUCE
        )
        with postgres_database.unit_of_work() as unit_of_work:
            ProductStore(unit_of_work.session).update_work(
                admitted.work_id,
                {
                    "production_plan_proposal": None,
                    "updated_at": datetime.now(UTC),
                },
            )
            unit_of_work.commit()
        recovered = steering_driver.iterate(admitted.work_id)
        assert recovered.action is SteeringActionType.PLAN_REVISION
        recovery_plan = SteeringApplicationService(postgres_database).reconstruct(
            admitted.work_id
        )
        assert recovery_plan.active_revision.revision.revision_number == 3
        assert recovery_plan.current_step is not None
        assert recovery_plan.current_step.type is SteeringStepType.DESIGN
        recovery_input = SemanticStepApplicationService(
            postgres_database,
            _UnguidedSemanticCapability(),
            work_service=completed_work,
        ).assemble_input(admitted.work_id)
        assert recovery_input.production_proposal_required is True
    finally:
        steering_driver.shutdown()


@pytest.mark.parametrize(
    "choice",
    (
        WorkTransitionChoice.CONTINUE_CURRENT_WORK,
        WorkTransitionChoice.DISMISSED,
    ),
)
def test_wic4_non_switch_transition_choices_are_idempotent_and_preserve_work(
    postgres_database: Database,
    services,
    choice: WorkTransitionChoice,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    admitted = _admit(work, ready)
    old_revision_id = admitted.current_work_reality_revision_id
    active = WorkInteractionService(
        postgres_database,
        capability=_ActiveCapability(
            focus=WorkFocusClassification.UNRELATED_NEW_DEMAND,
            impact=WorkImpactDisposition.NEW_WORK_RECOMMENDED,
            motive="Build a materially unrelated mobile application.",
        ),
    )
    pending = active.append_and_assess(
        ready.interaction.id,
        "This is unrelated: build a new mobile application.",
        human_identity="human:test",
    )
    transition = pending.latest_work_transition
    assert transition is not None
    assert transition.choice is WorkTransitionChoice.PENDING_HUMAN
    assert _count(postgres_database, product_works) == 1
    assert _count(postgres_database, interaction_work_transitions) == 1

    client = TestClient(
        create_http_application(
            application=object(),
            database=postgres_database,
            work_service=work,
            orchestrator=_NoopOrchestrator(),
            steering_driver=_RecordingDriver(),
            runtime_activation=_RuntimeActivation(),
            interaction_service=active,
        ),
        raise_server_exceptions=False,
    )
    with client:
        response = client.post(
            f"/api/interactions/{ready.interaction.id}/work-transition-decisions",
            json={
                "transition_id": str(transition.id),
                "expected_originating_work_id": str(admitted.work_id),
                "choice": choice.value,
                "authority_identity": "human:governor",
            },
        )
    assert response.status_code == 200, response.text
    assert response.json()["latest_work_transition"]["choice"] == choice.value
    decided = active.get_shared_understanding(ready.interaction.id)
    repeated = active.decide_work_transition(
        ready.interaction.id,
        transition_id=transition.id,
        expected_originating_work_id=admitted.work_id,
        choice=choice,
        authority_identity="human:governor",
    )
    assert decided.governed_work_id == admitted.work_id
    assert repeated.latest_work_transition == decided.latest_work_transition
    assert decided.latest_work_transition.choice is choice
    assert work.get_work(admitted.work_id).current_work_reality_revision_id == (
        old_revision_id
    )
    assert _count(postgres_database, product_works) == 1
    assert _count(postgres_database, work_reality_revisions) == 1
    with pytest.raises(
        InteractionInvariantViolation,
        match="different Human choice",
    ):
        active.decide_work_transition(
            ready.interaction.id,
            transition_id=transition.id,
            expected_originating_work_id=admitted.work_id,
            choice=WorkTransitionChoice.START_NEW_WORK,
            authority_identity="human:governor",
        )


def test_wic4_new_work_transition_survives_restart_and_forms_independent_work(
    postgres_database: Database,
    services,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    old_work = _admit(work, ready)
    old_revision = interactions.get_shared_understanding(
        ready.interaction.id
    ).governed_revision
    assert old_revision is not None
    active = WorkInteractionService(
        postgres_database,
        capability=_ActiveCapability(
            focus=WorkFocusClassification.UNRELATED_NEW_DEMAND,
            impact=WorkImpactDisposition.NEW_WORK_RECOMMENDED,
            motive="Build an independent mobile application.",
        ),
    )
    pending = active.append_and_assess(
        ready.interaction.id,
        "This is a new work: build an independent mobile application.",
        human_identity="human:test",
    )
    transition = pending.latest_work_transition
    assert transition is not None
    assert transition.source_record_id == pending.records[-1].id
    assert transition.source_assessment_id == pending.latest_assessment.id
    assert transition.originating_work_id == old_work.work_id
    assert transition.focus_classification is WorkFocusClassification.UNRELATED_NEW_DEMAND
    assert transition.impact_disposition is WorkImpactDisposition.NEW_WORK_RECOMMENDED
    assert transition.choice is WorkTransitionChoice.PENDING_HUMAN
    assert _count(postgres_database, product_works) == 1
    for table in PRODUCTION_TABLES:
        assert _count(postgres_database, table) == 0, table.name
    restarted = WorkInteractionService(
        postgres_database,
        capability=_ReadyCapability(),
    )
    restored = restarted.get_shared_understanding(ready.interaction.id)
    assert restored.latest_work_transition == transition
    switched = restarted.decide_work_transition(
        ready.interaction.id,
        transition_id=transition.id,
        expected_originating_work_id=old_work.work_id,
        choice=WorkTransitionChoice.START_NEW_WORK,
        authority_identity="human:governor",
        rationale="Begin independent Work formation without inherited authority.",
    )
    assert switched.governed_work_id is None
    assert switched.governed_revision is None
    assert switched.new_work_formation_pending is True
    pre_work_id = switched.interaction.current_work_id
    assert pre_work_id is not None
    assert switched.latest_work_transition.target_work_id == pre_work_id
    assert switched.work_satisfaction_state is WorkSatisfactionState.NO_FOCUSED_WORK
    assert old_work.work_id in switched.work_focus_history
    repeated = restarted.decide_work_transition(
        ready.interaction.id,
        transition_id=transition.id,
        expected_originating_work_id=old_work.work_id,
        choice=WorkTransitionChoice.START_NEW_WORK,
        authority_identity="human:governor",
    )
    assert repeated.new_work_formation_pending is True
    assert _count(postgres_database, product_works) == 2
    assert _count(postgres_database, work_reality_revisions) == 1

    candidate = restarted.append_and_assess(
        ready.interaction.id,
        "Please build the independent mobile experience with an observable outcome.",
        human_identity="human:test",
    )
    assert candidate.governed_work_id is None
    assert candidate.readiness.status is WorkAdmissionReadinessStatus.READY
    new_work = work.admit_interaction_work(
        ready.interaction.id,
        assessment_id=candidate.latest_assessment.id,
        basis_fingerprint=candidate.latest_assessment.basis_fingerprint,
        authority_identity="human:governor",
        rationale="Independently admit the new Work formation.",
    )
    assert new_work.work_id != old_work.work_id
    assert new_work.work_id == pre_work_id
    final = restarted.get_shared_understanding(ready.interaction.id)
    assert final.governed_work_id == new_work.work_id
    assert final.latest_work_transition.target_work_id == new_work.work_id
    assert final.new_work_formation_pending is False
    assert final.work_focus_history == (old_work.work_id, new_work.work_id)
    assert _count(postgres_database, product_works) == 2
    assert _count(postgres_database, work_reality_revisions) == 2
    assert final.governed_revision.governance_record_id != (
        old_revision.governance_record_id
    )
    for table in PRODUCTION_TABLES:
        assert _count(postgres_database, table) == 0, table.name


def test_wic4_explicit_different_system_object_requires_human_new_work_decision(
    postgres_database: Database,
    services,
) -> None:
    work, interactions = services
    ready = _ready(interactions)
    admitted = _admit(work, ready)
    original_revision = work.get_work(admitted.work_id).current_work_reality_revision_id
    active = WorkInteractionService(
        postgres_database,
        capability=DeterministicWorkInteractionCapability(),
    )

    pending = active.append_and_assess(
        ready.interaction.id,
        "I want to develop a CRM system.",
        human_identity="human:test",
    )

    transition = pending.latest_work_transition
    assert transition is not None
    assert transition.originating_work_id == admitted.work_id
    assert transition.focus_classification is WorkFocusClassification.UNRELATED_NEW_DEMAND
    assert transition.impact_disposition is WorkImpactDisposition.NEW_WORK_RECOMMENDED
    assert transition.choice is WorkTransitionChoice.PENDING_HUMAN
    assert pending.governed_work_id == admitted.work_id
    assert pending.latest_assessment.candidate_change is None
    assert "This appears to be a new Work" in pending.latest_assessment.natural_response
    assert _count(postgres_database, product_works) == 1
    assert work.get_work(admitted.work_id).current_work_reality_revision_id == original_revision
    for table in PRODUCTION_TABLES:
        assert _count(postgres_database, table) == 0, table.name


def test_wic_admission_migration_downgrade_and_reupgrade(
    postgres_database: Database,
) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260907_23")
    columns = {
        item["name"]
        for item in inspect(postgres_database.engine).get_columns(
            "work_reality_revisions"
        )
    }
    assert "revision_fingerprint" not in columns
    assert "source_assessment_id" not in columns

    command.upgrade(config, "head")
    columns = {
        item["name"]
        for item in inspect(postgres_database.engine).get_columns(
            "work_reality_revisions"
        )
    }
    assert {
        "revision_fingerprint",
        "source_interaction_id",
        "source_assessment_id",
        "engineering_resource_id",
        "scope_basis_fingerprint",
        "source_baseline_id",
        "governance_record_id",
        "engineering_semantic_facts",
        "schema_version",
    } <= columns


def test_wic3_migration_round_trip_is_additive_and_reversible(
    postgres_database: Database,
) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260907_24")
    assessment_columns = {
        item["name"]
        for item in inspect(postgres_database.engine).get_columns(
            "interaction_assessments"
        )
    }
    record_columns = {
        item["name"]
        for item in inspect(postgres_database.engine).get_columns("interaction_records")
    }
    revision_columns = {
        item["name"]
        for item in inspect(postgres_database.engine).get_columns(
            "work_reality_revisions"
        )
    }
    assert "focus_classification" not in assessment_columns
    assert "supporting_references" not in record_columns
    assert "source_record_ids" not in revision_columns

    command.upgrade(config, "head")
    assessment_columns = {
        item["name"]
        for item in inspect(postgres_database.engine).get_columns(
            "interaction_assessments"
        )
    }
    assert {
        "focus_classification",
        "impact_disposition",
        "candidate_change",
        "basis_work_revision_id",
        "basis_steering_plan_revision_id",
        "basis_steering_step_id",
        "basis_active_runtime_binding_id",
        "supporting_references",
    } <= assessment_columns


def test_wic4_migration_round_trip_preserves_transition_provenance(
    postgres_database: Database,
) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260907_25")
    assert "interaction_work_transitions" not in inspect(
        postgres_database.engine
    ).get_table_names()

    command.upgrade(config, "head")
    inspector = inspect(postgres_database.engine)
    assert "interaction_work_transitions" in inspector.get_table_names()
    assert {
        "interaction_id",
        "source_record_id",
        "source_assessment_id",
        "originating_work_id",
        "target_work_id",
        "reason",
        "focus_classification",
        "impact_disposition",
        "choice",
        "decided_by",
        "decision_rationale",
        "decided_at",
    } <= {
        item["name"]
        for item in inspector.get_columns("interaction_work_transitions")
    }


def _git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *args),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
