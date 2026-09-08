from collections.abc import Iterator
from datetime import UTC, datetime
import os
from pathlib import Path
import subprocess
from time import monotonic, sleep
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from spg.application.runtime import RuntimeService
from spg.application.semantic_steps import SemanticStepApplicationService
from spg.application.steering import SteeringApplicationService
from spg.application.steering_decision import (
    DeterministicPlanSteeringCapability,
    PlanFrameAssembler,
    SteeringDecisionApplicationService,
)
from spg.application.steering_production import SteeringProductionService
from spg.application.steering_driver import PlanSteeringDriver
from spg.application.orchestration import (
    OrchestrationStopReason,
    ProductionOrchestrator,
)
from spg.application.work import WorkApplicationService
from spg.api import create_http_application
from spg.domain.execution import ProviderReportedOutcome
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import (
    AttentionAction,
    AttentionResolutionRequest,
    AttentionKind,
    EngineeringContextReference,
    WorkRefinementRequest,
    WorkStatus,
)
from spg.domain.runtime import BootstrapRequest
from spg.domain.steering import (
    AdmitSteeringDecisionRequest,
    CreateSteeringPlanRequest,
    ElaborateSteeringStepRequest,
    NextStepCandidate,
    PlanFrame,
    PlanFrameBlocker,
    PlanFrameBlockerKind,
    RealityReference,
    RealityReferenceKind,
    ReviseSteeringPlanRequest,
    SemanticResultKind,
    SemanticStepInput,
    SemanticStepResultCandidate,
    StaleSteeringCandidate,
    SteeringActionType,
    SteeringAttentionReason,
    SteeringDriverStopReason,
    SteeringAuthorityAssessment,
    SteeringHistoryEventType,
    SteeringInvariantViolation,
    SteeringOutcome,
    SteeringPlanRevisionCondition,
    SteeringStepSpec,
    SteeringStepState,
    SteeringStepType,
    TransitionSteeringStepRequest,
)
from spg.infrastructure.persistence import Database, product_tables, runtime_tables
from spg.infrastructure.persistence.steering_store import SteeringStore
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_schema import (
    production_runs,
    production_work_units,
)
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from sqlalchemy import func, select
from spg.providers.deterministic_executor import (
    DeterministicExecutionSpecification,
    DeterministicFileOperation,
    DeterministicFileOperationType,
    DeterministicTestExecutor,
)
from spg.providers.deterministic_verifier import DeterministicVerificationProvider
from spg.domain.verification import VerificationResultValue


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALL_TABLE_NAMES = {table.name for table in (*product_tables, *runtime_tables)}
STEERING_TABLE_NAMES = {
    "steering_plans",
    "steering_plan_revisions",
    "steering_steps",
    "steering_decisions",
    "steering_history_events",
    "semantic_step_results",
}


def _migration_config(database: Database) -> Config:
    os.environ["SPG_DATABASE_URL"] = database.engine.url.render_as_string(
        hide_password=False
    )
    return Config(PROJECT_ROOT / "alembic.ini")


@pytest.fixture(autouse=True)
def clean_product_runtime_schema(postgres_database: Database) -> Iterator[None]:
    previous = os.environ.get("SPG_DATABASE_URL")
    command.upgrade(_migration_config(postgres_database), "head")
    _truncate(postgres_database)
    try:
        yield
    finally:
        command.upgrade(_migration_config(postgres_database), "head")
        _truncate(postgres_database)
        if previous is None:
            os.environ.pop("SPG_DATABASE_URL", None)
        else:
            os.environ["SPG_DATABASE_URL"] = previous


@pytest.fixture
def git_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "steering-repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "AI_context.md").write_text("governed baseline\n", encoding="utf-8")
    (repository / "docs").mkdir()
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    return repository


@pytest.fixture
def admitted_work(postgres_database: Database, git_repository: Path, tmp_path: Path):
    runtime = RuntimeService(postgres_database)
    baseline = runtime.bootstrap_trusted_baseline(
        BootstrapRequest(
            repository_path=git_repository,
            repository_identity="test://steering-repository",
            repository_ref="refs/heads/main",
            authority_identity="architecture-lead:test",
            scope={"slice": "MVP-PLAN-STEER-1C"},
        )
    ).snapshot
    works = WorkApplicationService(
        postgres_database,
        workspace_root=tmp_path / "workspaces",
    )
    works.register_engineering_resource(
        repository_identity="test://steering-repository",
        location_ref=str(git_repository),
        authoritative_ref="refs/heads/main",
        context_references=(
            EngineeringContextReference(
                semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                repository_relative_path="AI_context.md",
            ),
        ),
    )
    submitted = works.submit_work("Deliver a long-lived governed product outcome")
    draft = works.refine_work(
        submitted.work_id,
        WorkRefinementRequest(
            title="Long-lived Steering Work",
            desired_outcome="Reach the governed product outcome",
            production_objective="Establish the first bounded artifact",
            expected_artifact_path="docs/steering-result.md",
            verification_expectation="Verify the admitted artifact",
        ),
    )
    admitted = works.approve_work(
        draft.work_id,
        authority_identity="human:test",
        rationale="Admit the bounded initial Work authority",
    )
    return works, admitted, baseline


def _steps(*, coarse: bool = False) -> tuple[SteeringStepSpec, ...]:
    produce_objective = (
        "Implement the coarse product capability"
        if coarse
        else "Produce the admitted bounded capability"
    )
    return (
        SteeringStepSpec(
            type=SteeringStepType.DESIGN,
            objective="Establish the bounded design",
            completion_condition="The design direction is governed",
            state=SteeringStepState.CURRENT,
        ),
        SteeringStepSpec(
            type=SteeringStepType.PRODUCE,
            objective=produce_objective,
            completion_condition="The bounded production result is trusted",
        ),
        SteeringStepSpec(
            type=SteeringStepType.VERIFY_ACCEPT,
            objective="Evaluate the resulting Reality",
            completion_condition="Required evidence is accepted",
        ),
        SteeringStepSpec(
            type=SteeringStepType.COMPLETE,
            objective="Close the long-lived Work",
            completion_condition="The Work outcome is satisfied",
        ),
    )


def test_steer_truth_03_through_14_and_reconstruction(
    postgres_database: Database,
    admitted_work,
) -> None:
    _works, work, baseline = admitted_work
    service = SteeringApplicationService(postgres_database)
    work_ref = RealityReference(
        kind=RealityReferenceKind.WORK,
        identity=work.work_id,
    )
    baseline_ref = RealityReference(
        kind=RealityReferenceKind.TRUSTED_BASELINE,
        identity=baseline.id,
    )
    created = service.create_plan(
        CreateSteeringPlanRequest(
            work_id=work.work_id,
            rationale="The admitted Work requires a long-lived governed trajectory",
            reality_refs=(baseline_ref,),
            steps=_steps(coarse=True),
        )
    )
    revision_id = created.active_revision.revision.id
    design = created.current_step
    produce = created.next_step
    assert design is not None and design.type is SteeringStepType.DESIGN
    assert produce is not None and produce.type is SteeringStepType.PRODUCE
    assert [step.type for step in created.active_revision.steps] == [
        SteeringStepType.DESIGN,
        SteeringStepType.PRODUCE,
        SteeringStepType.VERIFY_ACCEPT,
        SteeringStepType.COMPLETE,
    ]

    semantic_result = _record_semantic_result(postgres_database, work.work_id)
    decision_refs = tuple(
        item.reference
        for item in PlanFrameAssembler(postgres_database)
        .assemble(work.work_id)
        .basis.resolved_reality
    )
    assert RealityReference(
        kind=RealityReferenceKind.SEMANTIC_RESULT,
        identity=semantic_result.id,
    ) in decision_refs
    fingerprint = service.decision_basis_fingerprint(
        revision_id,
        design.id,
        decision_refs,
    )
    assert fingerprint == service.decision_basis_fingerprint(
        revision_id,
        design.id,
        tuple(reversed(decision_refs)),
    )
    decision = service.admit_decision(
        AdmitSteeringDecisionRequest(
            steering_plan_revision_id=revision_id,
            current_step_id=design.id,
            next_step_type=produce.type,
            objective=produce.objective,
            reason="The governed design direction is established",
            reality_refs=decision_refs,
            human_required=False,
            completion_condition=produce.completion_condition,
            steering_outcome=SteeringOutcome.AUTO_CONTINUE,
            expected_basis_fingerprint=fingerprint,
            reasoning_provider_identity="provider-neutral:deterministic-test",
        )
    )
    transitioned = service.transition_step(
        TransitionSteeringStepRequest(
            steering_plan_revision_id=revision_id,
            current_step_id=design.id,
            next_step_id=produce.id,
            steering_decision_id=decision.id,
        )
    )
    assert transitioned.active_revision.revision.id == revision_id
    assert transitioned.active_revision.revision.revision_number == 1
    assert transitioned.current_step is not None
    assert transitioned.current_step.id == produce.id
    assert design.id in {step.id for step in transitioned.completed_steps}
    transition = transitioned.history[-1]
    assert transition.event_type is SteeringHistoryEventType.STEP_TRANSITION
    assert transition.steering_decision_id == decision.id

    elaborated = service.elaborate_step(
        ElaborateSteeringStepRequest(
            steering_plan_revision_id=revision_id,
            step_id=produce.id,
            replacements=(
                SteeringStepSpec(
                    type=SteeringStepType.PRODUCE,
                    objective="Produce capability foundation",
                    completion_condition="Foundation result is trusted",
                ),
                SteeringStepSpec(
                    type=SteeringStepType.PRODUCE,
                    objective="Produce capability integration",
                    completion_condition="Integration result is trusted",
                ),
            ),
            rationale="Near work now has two recognizable Reality changes",
            reality_refs=(work_ref,),
        )
    )
    assert elaborated.active_revision.revision.id == revision_id
    assert elaborated.current_step is not None
    children = tuple(
        step
        for step in elaborated.active_revision.steps
        if step.elaborates_step_id == produce.id
    )
    assert len(children) == 2
    assert children[0].state is SteeringStepState.CURRENT
    assert next(
        step for step in elaborated.active_revision.steps if step.id == produce.id
    ).state is SteeringStepState.SUPERSEDED
    assert elaborated.history[-1].event_type is SteeringHistoryEventType.STEP_ELABORATION

    current = elaborated.current_step
    attention_fingerprint = service.decision_basis_fingerprint(
        revision_id,
        current.id,
        (work_ref,),
    )
    attention = service.admit_decision(
        AdmitSteeringDecisionRequest(
            steering_plan_revision_id=revision_id,
            current_step_id=current.id,
            next_step_type=SteeringStepType.HUMAN_DECISION,
            objective="Obtain the material direction decision",
            reason="The material choice belongs to Human Authority",
            reality_refs=(work_ref,),
            human_required=True,
            completion_condition="A governed Human decision is recorded",
            steering_outcome=SteeringOutcome.HUMAN_ATTENTION,
            expected_basis_fingerprint=attention_fingerprint,
        )
    )
    assert attention.steering_outcome is SteeringOutcome.HUMAN_ATTENTION

    revised = service.revise_plan(
        ReviseSteeringPlanRequest(
            steering_plan_id=created.steering_plan_id,
            superseded_revision_id=revision_id,
            rationale="The exact governed baseline changes the viable path",
            reality_refs=(baseline_ref,),
            steps=_steps(),
        )
    )
    assert revised.active_revision.revision.revision_number == 2
    assert revised.active_revision.revision.supersedes_revision_id == revision_id
    assert revised.has_material_revision is True
    assert (
        revised.revision_lineage[0].revision.condition
        is SteeringPlanRevisionCondition.SUPERSEDED
    )
    assert revised.history[-1].event_type is SteeringHistoryEventType.PLAN_REVISION
    assert revised.latest_decision == attention

    with pytest.raises(SteeringInvariantViolation, match="exact active"):
        service.revise_plan(
            ReviseSteeringPlanRequest(
                steering_plan_id=created.steering_plan_id,
                superseded_revision_id=revision_id,
                rationale="Stale revision must not be admitted",
                reality_refs=(work_ref,),
                steps=_steps(),
            )
        )

    fresh_service = SteeringApplicationService(postgres_database)
    reconstructed = fresh_service.reconstruct(work.work_id)
    assert reconstructed.work_objective == "Establish the first bounded artifact"
    assert reconstructed.active_revision.revision.revision_number == 2
    assert reconstructed.current_step is not None
    assert reconstructed.current_step.type is SteeringStepType.DESIGN
    assert reconstructed.next_step is not None
    assert reconstructed.next_step.type is SteeringStepType.PRODUCE
    assert reconstructed.completed_steps
    assert reconstructed.latest_decision is not None
    assert reconstructed.latest_decision.reason == attention.reason
    assert reconstructed.latest_decision.reality_refs == (work_ref,)
    assert {event.event_type for event in reconstructed.history} == {
        SteeringHistoryEventType.STEP_TRANSITION,
        SteeringHistoryEventType.STEP_ELABORATION,
        SteeringHistoryEventType.PLAN_REVISION,
    }


def test_stale_decision_and_multiple_current_steps_are_rejected(
    postgres_database: Database,
    admitted_work,
) -> None:
    _works, work, _baseline = admitted_work
    service = SteeringApplicationService(postgres_database)
    with pytest.raises(SteeringInvariantViolation, match="at most one CURRENT"):
        service.create_plan(
            CreateSteeringPlanRequest(
                work_id=work.work_id,
                rationale="Invalid duplicated current truth",
                steps=(
                    SteeringStepSpec(
                        type=SteeringStepType.DESIGN,
                        objective="First current",
                        completion_condition="First closes",
                        state=SteeringStepState.CURRENT,
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.PRODUCE,
                        objective="Second current",
                        completion_condition="Second closes",
                        state=SteeringStepState.CURRENT,
                    ),
                ),
            )
        )

    created = service.create_plan(
        CreateSteeringPlanRequest(
            work_id=work.work_id,
            rationale="Valid current truth",
            steps=_steps(),
        )
    )
    current = created.current_step
    assert current is not None
    with pytest.raises(IntegrityError):
        with postgres_database.unit_of_work() as unit_of_work:
            SteeringStore(unit_of_work.session).insert_step(
                {
                    "id": uuid4(),
                    "steering_plan_revision_id": created.active_revision.revision.id,
                    "type": SteeringStepType.DESIGN.value,
                    "objective": "Database-rejected second current",
                    "completion_condition": "Must never be admitted",
                    "position": 99,
                    "state": SteeringStepState.CURRENT.value,
                    "elaborates_step_id": None,
                    "created_at": datetime.now(UTC),
                }
            )
            unit_of_work.commit()

    with pytest.raises(SteeringInvariantViolation, match="does not exist"):
        service.decision_basis_fingerprint(
            created.active_revision.revision.id,
            current.id,
            (
                RealityReference(
                    kind=RealityReferenceKind.TRUSTED_BASELINE,
                    identity=uuid4(),
                ),
            ),
        )

    with pytest.raises(SteeringInvariantViolation, match="basis is stale"):
        service.admit_decision(
            AdmitSteeringDecisionRequest(
                steering_plan_revision_id=created.active_revision.revision.id,
                current_step_id=current.id,
                next_step_type=SteeringStepType.PRODUCE,
                objective="Produce the admitted bounded capability",
                reason="A stale output cannot control progression",
                reality_refs=(
                    RealityReference(
                        kind=RealityReferenceKind.WORK,
                        identity=work.work_id,
                    ),
                ),
                human_required=False,
                completion_condition="The bounded production result is trusted",
                steering_outcome=SteeringOutcome.AUTO_CONTINUE,
                expected_basis_fingerprint="0" * 64,
            )
        )


def test_steer_truth_15_16_legacy_work_remains_one_cycle_compatible(
    postgres_database: Database,
    admitted_work,
) -> None:
    works, work, _baseline = admitted_work

    projection = works.get_work(work.work_id)
    assert projection.production_plan is not None
    with postgres_database.unit_of_work() as unit_of_work:
        assert SteeringStore(unit_of_work.session).plan_for_work(work.work_id) is None


def _create_steering_plan(
    database: Database,
    work_id,
    *,
    steps: tuple[SteeringStepSpec, ...] | None = None,
):
    return SteeringApplicationService(database).create_plan(
        CreateSteeringPlanRequest(
            work_id=work_id,
            rationale="The admitted Work requires governed long-lived Steering",
            steps=steps or _steps(),
        )
    )


class _WordingCapability:
    def __init__(self, *, reason: str, provider: str) -> None:
        self.reason = reason
        self.provider = provider

    def evaluate(self, plan_frame: PlanFrame) -> NextStepCandidate:
        candidate = DeterministicPlanSteeringCapability().evaluate(plan_frame)
        return candidate.model_copy(
            update={
                "reason": self.reason,
                "reasoning_provider_identity": self.provider,
            }
        )


class _TestSemanticCapability:
    def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
        return SemanticStepResultCandidate(
            work_id=input.work_id,
            steering_plan_revision_id=input.steering_plan_revision_id,
            step_id=input.step.id,
            step_type=input.step.type,
            basis_fingerprint=input.basis_fingerprint,
            result_kind=(
                SemanticResultKind.DESIGN_DIRECTION
                if input.step.type is SteeringStepType.DESIGN
                else SemanticResultKind.WORK_REFINEMENT
            ),
            bounded_summary=(
                "The deterministic test records a bounded governed semantic direction."
            ),
            decisions=("Retain the already admitted bounded test direction.",),
            derived_constraints=input.constraints,
            evidence_refs=input.reality_refs,
            authority_assessment=SteeringAuthorityAssessment.WITHIN_AUTHORITY,
            reasoning_provider_identity="fake:semantic-step",
            completion_claimed=True,
        )


def _record_semantic_result(database: Database, work_id):
    return SemanticStepApplicationService(
        database,
        _TestSemanticCapability(),
    ).execute(work_id)


def test_steer_dec_01_through_09_plan_frame_candidate_and_admission(
    postgres_database: Database,
    admitted_work,
) -> None:
    _works, work, baseline = admitted_work
    created = _create_steering_plan(postgres_database, work.work_id)
    first_service = SteeringDecisionApplicationService(
        postgres_database,
        _WordingCapability(
            reason="Persisted governed facts support the next ordered Step",
            provider="fake:one",
        ),
    )
    frame, first = first_service.evaluate(work.work_id)
    second_service = SteeringDecisionApplicationService(
        postgres_database,
        _WordingCapability(
            reason="The current Reality admits the known bounded direction",
            provider="fake:two",
        ),
    )
    second_frame, second = second_service.evaluate(work.work_id)

    assert frame.basis.fingerprint == second_frame.basis.fingerprint
    assert frame.basis.canonical_representation == second_frame.basis.canonical_representation
    assert first.type is SteeringStepType.PRODUCE
    assert first.proposed_outcome is SteeringOutcome.AUTO_CONTINUE
    assert first.human_required is False
    assert first.material_direction_fingerprint == second.material_direction_fingerprint
    assert first.reason != second.reason
    assert first.reasoning_provider_identity != second.reasoning_provider_identity
    assert {item.reference.kind for item in frame.basis.resolved_reality} >= {
        RealityReferenceKind.WORK,
        RealityReferenceKind.GOVERNANCE_DECISION,
        RealityReferenceKind.TRUSTED_BASELINE,
    }
    assert frame.trusted_baseline_ref is not None
    assert frame.trusted_baseline_ref.identity == baseline.id
    assert frame.engineering_scope_fingerprint is not None
    assert created.active_revision.revision.id == frame.reconstruction.active_revision.revision.id

    with pytest.raises(SteeringInvariantViolation, match="Reality-grounded rationale"):
        second_service.admit(
            work.work_id,
            second.model_copy(update={"reason": "The model thinks this is better"}),
        )
    decision = second_service.admit(work.work_id, second)
    assert decision.steering_outcome is SteeringOutcome.AUTO_CONTINUE
    assert decision.reason == second.reason
    assert decision.basis_fingerprint == frame.basis.fingerprint
    fresh = SteeringApplicationService(postgres_database).reconstruct(work.work_id)
    assert fresh.latest_decision == decision
    assert fresh.current_step == frame.reconstruction.current_step


def test_steer_dec_07_stale_candidate_after_material_revision_is_rejected(
    postgres_database: Database,
    admitted_work,
) -> None:
    _works, work, _baseline = admitted_work
    created = _create_steering_plan(postgres_database, work.work_id)
    decision_service = SteeringDecisionApplicationService(
        postgres_database,
        DeterministicPlanSteeringCapability(),
    )
    _frame, candidate = decision_service.evaluate(work.work_id)
    SteeringApplicationService(postgres_database).revise_plan(
        ReviseSteeringPlanRequest(
            steering_plan_id=created.steering_plan_id,
            superseded_revision_id=created.active_revision.revision.id,
            rationale="New governed Reality materially changes the admitted Plan",
            reality_refs=(
                RealityReference(
                    kind=RealityReferenceKind.WORK,
                    identity=work.work_id,
                ),
            ),
            steps=_steps(),
        )
    )
    with pytest.raises(StaleSteeringCandidate, match="STALE_STEERING_CANDIDATE"):
        decision_service.admit(work.work_id, candidate)


@pytest.mark.parametrize("attention_reason", tuple(SteeringAttentionReason))
def test_steer_dec_10_through_14_human_attention_is_typed_and_projected(
    postgres_database: Database,
    admitted_work,
    attention_reason: SteeringAttentionReason,
) -> None:
    works, work, _baseline = admitted_work
    _create_steering_plan(postgres_database, work.work_id)
    frame = PlanFrameAssembler(postgres_database).assemble(work.work_id)
    refs = tuple(item.reference for item in frame.basis.resolved_reality)
    expanding = (
        attention_reason is SteeringAttentionReason.SCOPE_OR_AUTHORITY_EXPANSION
    )
    candidate = NextStepCandidate(
        type=SteeringStepType.HUMAN_DECISION,
        objective=f"Resolve {attention_reason.value}",
        reason="Current governed Reality leaves a material Human-owned decision",
        reality_refs=refs,
        human_required=True,
        completion_condition="Human Authority records the material direction",
        proposed_outcome=SteeringOutcome.HUMAN_ATTENTION,
        basis_fingerprint=frame.basis.fingerprint,
        authority_assessment=(
            SteeringAuthorityAssessment.EXPANDS_AUTHORITY
            if expanding
            else SteeringAuthorityAssessment.UNCERTAIN
        ),
        proposed_engineering_scope_fingerprint=(
            "f" * 64 if expanding else frame.engineering_scope_fingerprint
        ),
        attention_reason=attention_reason,
        recommendation="Choose the bounded option that preserves admitted authority",
        alternatives=("Narrow the direction", "Revise authority explicitly"),
        trade_offs=("Scope versus delivery cost",),
        expected_impact="The decision controls subsequent Steering",
        reasoning_provider_identity="fake:semantic-steering",
    )
    decision = SteeringDecisionApplicationService(
        postgres_database,
        DeterministicPlanSteeringCapability(),
    ).admit(work.work_id, candidate)
    assert decision.attention_reason is attention_reason
    assert decision.authority_assessment is candidate.authority_assessment

    attention = works.list_attention(work_id=work.work_id)
    assert len(attention) == 1
    assert attention[0].kind is (
        AttentionKind.PRODUCTION_PROPOSAL_REVIEW
        if attention_reason
        is SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED
        else AttentionKind.STEERING_DECISION_REQUIRED
    )
    assert attention[0].steering_reason is attention_reason
    assert attention[0].decision == candidate.objective
    assert attention[0].recommendation == candidate.recommendation
    assert attention[0].expected_impact == candidate.expected_impact
    assert attention[0].governed_subject_ref == f"steering-decision:{decision.id}"
    assert attention[0].kind is not AttentionKind.CANDIDATE_AUTHORIZATION


def test_steer_dec_09_bounded_defect_does_not_ask_human_to_continue(
    postgres_database: Database,
    admitted_work,
) -> None:
    _works, work, _baseline = admitted_work
    _create_steering_plan(postgres_database, work.work_id)
    frame = PlanFrameAssembler(postgres_database).assemble(work.work_id)
    work_ref = next(
        item.reference
        for item in frame.basis.resolved_reality
        if item.reference.kind is RealityReferenceKind.WORK
    )
    blocked_frame = frame.model_copy(
        update={
            "open_blocking_reality": (
                PlanFrameBlocker(
                    kind=PlanFrameBlockerKind.VERIFICATION_NOT_PASSING,
                    reason="A bounded verification defect remains",
                    reality_refs=(work_ref,),
                ),
            )
        }
    )
    candidate = DeterministicPlanSteeringCapability().evaluate(blocked_frame)
    assert candidate.proposed_outcome is SteeringOutcome.AUTO_CONTINUE
    assert candidate.human_required is False
    assert candidate.type is blocked_frame.reconstruction.current_step.type


def test_steer_dec_15_complete_decision_uses_persisted_evidence_without_closing_work(
    postgres_database: Database,
    admitted_work,
) -> None:
    works, work, _baseline = admitted_work
    target = "docs/steering-result.md"
    executor = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=(
                DeterministicFileOperation(
                    operation=DeterministicFileOperationType.CREATE,
                    repository_relative_path=target,
                    content="# Trusted Steering result\n",
                ),
            ),
            reported_outcome=ProviderReportedOutcome.SUCCESS,
            summary="provider-free deterministic Steering fixture",
        )
    )
    production = WorkApplicationService(
        postgres_database,
        workspace_root=works.workspace_root,
        executor=executor,
        verifier=DeterministicVerificationProvider(
            {"Verify the admitted artifact": VerificationResultValue.PASS}
        ),
    )
    for _ in range(12):
        projected = production.advance_work(work.work_id)
        if projected.status is WorkStatus.NEEDS_ATTENTION:
            break
    assert projected.status is WorkStatus.NEEDS_ATTENTION

    _create_steering_plan(
        postgres_database,
        work.work_id,
        steps=(
            SteeringStepSpec(
                type=SteeringStepType.VERIFY_ACCEPT,
                objective="Accept the persisted verification result",
                completion_condition="Completion and Verification Reality pass",
                state=SteeringStepState.CURRENT,
            ),
            SteeringStepSpec(
                type=SteeringStepType.COMPLETE,
                objective="Recognize the long-lived outcome as complete",
                completion_condition="Persisted evidence proves the Work outcome",
            ),
        ),
    )
    service = SteeringDecisionApplicationService(
        postgres_database,
        DeterministicPlanSteeringCapability(),
    )
    frame, candidate = service.evaluate(work.work_id)
    assert frame.completion_evidence_sufficient is True
    assert {item.kind for item in frame.runtime_reality_refs} >= {
        RealityReferenceKind.COMPLETION,
        RealityReferenceKind.VERIFICATION,
    }
    assert candidate.proposed_outcome is SteeringOutcome.COMPLETE
    before_decision = production.get_work(work.work_id)
    decision = service.admit(work.work_id, candidate)
    assert decision.steering_outcome is SteeringOutcome.COMPLETE
    assert production.get_work(work.work_id).status is before_decision.status
    assert SteeringApplicationService(postgres_database).reconstruct(
        work.work_id
    ).latest_decision == decision


def test_steering_decision_migration_downgrade_and_reupgrade(
    postgres_database: Database,
) -> None:
    config = _migration_config(postgres_database)
    columns = {
        item["name"]
        for item in inspect(postgres_database.engine).get_columns("steering_decisions")
    }
    assert "attention_reason" in columns
    assert "authority_assessment" in columns

    command.downgrade(config, "20260905_18")
    downgraded = {
        item["name"]
        for item in inspect(postgres_database.engine).get_columns("steering_decisions")
    }
    assert "attention_reason" not in downgraded
    assert "authority_assessment" not in downgraded

    command.upgrade(config, "head")
    upgraded = {
        item["name"]
        for item in inspect(postgres_database.engine).get_columns("steering_decisions")
    }
    assert "attention_reason" in upgraded
    assert "authority_assessment" in upgraded


def _transition_to_next_step(database: Database, work_id):
    reconstruction = SteeringApplicationService(database).reconstruct(work_id)
    if (
        reconstruction.current_step is not None
        and reconstruction.current_step.type
        in {SteeringStepType.DESIGN, SteeringStepType.REFINE}
        and not any(
            result.step_id == reconstruction.current_step.id
            for result in reconstruction.semantic_results
        )
    ):
        _record_semantic_result(database, work_id)
    decision_service = SteeringDecisionApplicationService(
        database,
        DeterministicPlanSteeringCapability(),
    )
    frame, candidate = decision_service.evaluate(work_id)
    decision = decision_service.admit(work_id, candidate)
    next_step = frame.reconstruction.next_step
    assert next_step is not None
    return SteeringApplicationService(database).transition_step(
        TransitionSteeringStepRequest(
            steering_plan_revision_id=frame.reconstruction.active_revision.revision.id,
            current_step_id=frame.reconstruction.current_step.id,
            next_step_id=next_step.id,
            steering_decision_id=decision.id,
        )
    )


def _trusted_cycle(
    database: Database,
    works: WorkApplicationService,
    work_id,
) -> None:
    orchestrator = ProductionOrchestrator(works)
    first = orchestrator.orchestrate(work_id)
    assert first.work_status is WorkStatus.NEEDS_ATTENTION
    attention = works.list_attention(work_id=work_id)
    assert len(attention) == 1
    assert attention[0].kind is AttentionKind.CANDIDATE_AUTHORIZATION
    works.resolve_attention(
        attention[0].id,
        AttentionResolutionRequest(
            action=AttentionAction.AUTHORIZE,
            authority_identity="human:exact-cycle-candidate",
        ),
    )
    second = orchestrator.orchestrate(work_id)
    assert second.stop_reason is OrchestrationStopReason.PRODUCTION_CYCLE_TRUSTED
    with database.unit_of_work() as unit_of_work:
        binding = WorkApplicationService._runtime_binding_for_current_context(
            ProductStore(unit_of_work.session), work_id
        )
        assert binding is not None
        assert ProductStore(unit_of_work.session).runtime_summary(
            binding
        ).runtime_commit_id is not None


def _wait_for(assertion, *, timeout: float = 30.0) -> None:
    deadline = monotonic() + timeout
    last_error = None
    while monotonic() < deadline:
        try:
            assertion()
            return
        except AssertionError as error:
            last_error = error
            sleep(0.02)
    if last_error is not None:
        raise last_error
    raise AssertionError("Timed out waiting for deterministic Steering Reality")


def _authorize_current_candidate(
    works: WorkApplicationService,
    work_id,
) -> None:
    attention = works.list_attention(work_id=work_id)
    assert len(attention) == 1
    assert attention[0].kind is AttentionKind.CANDIDATE_AUTHORIZATION
    works.resolve_attention(
        attention[0].id,
        AttentionResolutionRequest(
            action=AttentionAction.AUTHORIZE,
            authority_identity="human:steering-driver-candidate",
        ),
    )


def test_steer_spg_01_through_16_two_independent_cycles_and_completion(
    postgres_database: Database,
    admitted_work,
) -> None:
    original_works, work, baseline_zero = admitted_work
    created = _create_steering_plan(
        postgres_database,
        work.work_id,
        steps=(
            SteeringStepSpec(
                type=SteeringStepType.DESIGN,
                objective="Establish the bounded design",
                completion_condition="The bounded design is governed",
                state=SteeringStepState.CURRENT,
            ),
            SteeringStepSpec(
                type=SteeringStepType.PRODUCE,
                objective="Produce bounded result A",
                completion_condition="Production result A is trusted",
            ),
            SteeringStepSpec(
                type=SteeringStepType.PRODUCE,
                objective="Produce bounded result B",
                completion_condition="Production result B is trusted",
            ),
            SteeringStepSpec(
                type=SteeringStepType.COMPLETE,
                objective="Recognize the long-lived outcome",
                completion_condition="Both bounded results are trusted",
            ),
        ),
    )
    first_produce = _transition_to_next_step(
        postgres_database, work.work_id
    ).current_step
    assert first_produce is not None
    bridge = SteeringProductionService(postgres_database)
    request_a = bridge.materialize_request(work.work_id)
    cycle_a = bridge.admit_cycle(request_a).binding
    assert cycle_a is not None
    assert cycle_a.cycle_number == 1
    assert cycle_a.steering_step_id == first_produce.id

    works_a = WorkApplicationService(
        postgres_database,
        workspace_root=original_works.workspace_root,
        executor=DeterministicTestExecutor(
            DeterministicExecutionSpecification(
                operations=(
                    DeterministicFileOperation(
                        operation=DeterministicFileOperationType.CREATE,
                        repository_relative_path="docs/steering-result.md",
                        content="# Cycle A\n",
                    ),
                ),
                reported_outcome=ProviderReportedOutcome.SUCCESS,
                summary="deterministic cycle A",
            )
        ),
        verifier=DeterministicVerificationProvider(
            {"Verify the admitted artifact": VerificationResultValue.PASS}
        ),
    )
    _trusted_cycle(postgres_database, works_a, work.work_id)
    baseline_one = RuntimeService(postgres_database).current_baseline()
    assert baseline_one.id != baseline_zero.id
    assert works_a.get_work(work.work_id).status is not WorkStatus.COMPLETED

    second_produce = _transition_to_next_step(
        postgres_database, work.work_id
    ).current_step
    assert second_produce is not None
    request_b = bridge.materialize_request(work.work_id)
    assert request_b.artifact_targets[0].operation.value == "UPDATE"
    cycle_b = bridge.admit_cycle(request_b).binding
    assert cycle_b is not None
    assert cycle_b.cycle_number == 2
    assert cycle_b.production_run_id != cycle_a.production_run_id
    assert cycle_b.plan_revision_id != cycle_a.plan_revision_id
    assert cycle_b.work_unit_id != cycle_a.work_unit_id
    with postgres_database.unit_of_work() as unit_of_work:
        runtime = RuntimeStore(unit_of_work.session)
        assert runtime.run(cycle_a.production_run_id).source_baseline_id == baseline_zero.id
        assert runtime.run(cycle_b.production_run_id).source_baseline_id == baseline_one.id

    works_b = WorkApplicationService(
        postgres_database,
        workspace_root=original_works.workspace_root,
        executor=DeterministicTestExecutor(
            DeterministicExecutionSpecification(
                operations=(
                    DeterministicFileOperation(
                        operation=DeterministicFileOperationType.MODIFY,
                        repository_relative_path="docs/steering-result.md",
                        content="# Cycle B\n",
                    ),
                ),
                reported_outcome=ProviderReportedOutcome.SUCCESS,
                summary="deterministic cycle B",
            )
        ),
        verifier=DeterministicVerificationProvider(
            {"Verify the admitted artifact": VerificationResultValue.PASS}
        ),
    )
    _trusted_cycle(postgres_database, works_b, work.work_id)
    baseline_two = RuntimeService(postgres_database).current_baseline()
    assert baseline_two.id not in {baseline_zero.id, baseline_one.id}
    before_complete = works_b.get_work(work.work_id)
    assert before_complete.status is not WorkStatus.COMPLETED
    assert before_complete.current_production_cycle_number == 2
    completed = _transition_to_next_step(postgres_database, work.work_id)
    assert completed.current_step is not None
    assert completed.current_step.type is SteeringStepType.COMPLETE
    projected = works_b.get_work(work.work_id)
    assert projected.status is WorkStatus.COMPLETED
    assert projected.work_complete is True
    assert projected.steering_enabled is True
    assert projected.latest_trusted_runtime_commit_id is not None
    with postgres_database.unit_of_work() as unit_of_work:
        bindings = ProductStore(unit_of_work.session).runtime_bindings(work.work_id)
        assert len(bindings) == 2
        assert all(
            unit_of_work.session.scalar(
                select(func.count())
                .select_from(production_work_units)
                .where(
                    production_work_units.c.production_run_id
                    == binding.production_run_id
                )
            )
            == 1
            for binding in bindings
        )


def test_steer_spg_authority_expansion_stops_before_runtime_creation(
    postgres_database: Database,
    admitted_work,
) -> None:
    _works, work, _baseline = admitted_work
    _create_steering_plan(postgres_database, work.work_id)
    _transition_to_next_step(postgres_database, work.work_id)
    bridge = SteeringProductionService(postgres_database)
    request = bridge.materialize_request(work.work_id)
    with postgres_database.unit_of_work() as unit_of_work:
        before = unit_of_work.session.scalar(select(func.count()).select_from(production_runs))
    expanded = request.model_copy(
        update={
            "artifact_targets": (
                request.artifact_targets[0].model_copy(
                    update={"path": "docs/outside-authority.md"}
                ),
            )
        }
    )
    stopped = bridge.admit_cycle(expanded)
    assert stopped.binding is None
    assert stopped.attention_decision_id is not None
    with postgres_database.unit_of_work() as unit_of_work:
        after = unit_of_work.session.scalar(select(func.count()).select_from(production_runs))
        assert after == before
        assert ProductStore(unit_of_work.session).runtime_binding_for_step(
            request.steering_step_id
        ) is None
    attention = _works.list_attention(work_id=work.work_id)
    assert attention[0].steering_reason is SteeringAttentionReason.SCOPE_OR_AUTHORITY_EXPANSION


def test_steer_spg_failed_second_cycle_stays_open_without_retry(
    postgres_database: Database,
    admitted_work,
) -> None:
    original_works, work, _baseline_zero = admitted_work
    _create_steering_plan(
        postgres_database,
        work.work_id,
        steps=(
            SteeringStepSpec(
                type=SteeringStepType.DESIGN,
                objective="Govern the bounded direction",
                completion_condition="Direction governed",
                state=SteeringStepState.CURRENT,
            ),
            SteeringStepSpec(
                type=SteeringStepType.PRODUCE,
                objective="Produce trusted result A",
                completion_condition="Result A trusted",
            ),
            SteeringStepSpec(
                type=SteeringStepType.PRODUCE,
                objective="Produce result B",
                completion_condition="Result B trusted",
            ),
            SteeringStepSpec(
                type=SteeringStepType.COMPLETE,
                objective="Complete the long-lived Work",
                completion_condition="All results trusted",
            ),
        ),
    )
    _transition_to_next_step(postgres_database, work.work_id)
    bridge = SteeringProductionService(postgres_database)
    assert bridge.admit_cycle(bridge.materialize_request(work.work_id)).binding
    passing = WorkApplicationService(
        postgres_database,
        workspace_root=original_works.workspace_root,
        executor=DeterministicTestExecutor(
            DeterministicExecutionSpecification(
                operations=(
                    DeterministicFileOperation(
                        operation=DeterministicFileOperationType.CREATE,
                        repository_relative_path="docs/steering-result.md",
                        content="# Trusted A\n",
                    ),
                ),
                reported_outcome=ProviderReportedOutcome.SUCCESS,
                summary="cycle A passes",
            )
        ),
        verifier=DeterministicVerificationProvider(
            {"Verify the admitted artifact": VerificationResultValue.PASS}
        ),
    )
    _trusted_cycle(postgres_database, passing, work.work_id)
    baseline_one = RuntimeService(postgres_database).current_baseline()
    second = _transition_to_next_step(postgres_database, work.work_id).current_step
    assert second is not None
    binding = bridge.admit_cycle(bridge.materialize_request(work.work_id)).binding
    assert binding is not None

    executor = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=(
                DeterministicFileOperation(
                    operation=DeterministicFileOperationType.MODIFY,
                    repository_relative_path="docs/steering-result.md",
                    content="# Untrusted B\n",
                ),
            ),
            reported_outcome=ProviderReportedOutcome.SUCCESS,
            summary="cycle B verification fails",
        )
    )
    failing = WorkApplicationService(
        postgres_database,
        workspace_root=original_works.workspace_root,
        executor=executor,
        verifier=DeterministicVerificationProvider(
            {"Verify the admitted artifact": VerificationResultValue.FAIL}
        ),
    )
    orchestrator = ProductionOrchestrator(failing)
    stopped = orchestrator.orchestrate(work.work_id)
    assert stopped.work_status is WorkStatus.BLOCKED
    assert RuntimeService(postgres_database).current_baseline().id == baseline_one.id
    assert executor.dispatch_count == 1
    with postgres_database.unit_of_work() as unit_of_work:
        summary = ProductStore(unit_of_work.session).runtime_summary(binding)
    assert summary.completion_outcome == "PRODUCED"
    assert summary.verification_results == (VerificationResultValue.FAIL.value,)
    assert summary.candidate_id is None
    assert summary.runtime_commit_id is None
    reconstruction = SteeringApplicationService(postgres_database).reconstruct(
        work.work_id
    )
    assert reconstruction.current_step is not None
    assert reconstruction.current_step.id == second.id
    assert reconstruction.current_step.state is SteeringStepState.CURRENT
    frame = PlanFrameAssembler(postgres_database).assemble(work.work_id)
    assert {
        blocker.kind for blocker in frame.open_blocking_reality
    } == {PlanFrameBlockerKind.VERIFICATION_NOT_PASSING}
    again = orchestrator.orchestrate(work.work_id)
    assert again.transitions_executed == 0
    assert executor.dispatch_count == 1
    driver = PlanSteeringDriver(
        postgres_database,
        failing,
        orchestrator,
    )
    driver_outcome = driver.activate(work.work_id)
    assert driver_outcome.stop_reason is SteeringDriverStopReason.BLOCKED
    assert driver_outcome.iterations_executed == 0
    assert failing.get_work(work.work_id).status is WorkStatus.BLOCKED
    assert executor.dispatch_count == 1


def test_steering_reactivates_bounded_orch_without_human_continue(
    postgres_database: Database,
    admitted_work,
) -> None:
    original_works, work, _baseline = admitted_work
    _create_steering_plan(
        postgres_database,
        work.work_id,
        steps=(
            SteeringStepSpec(
                type=SteeringStepType.PRODUCE,
                objective="Produce the admitted bounded capability",
                completion_condition="The bounded production result is trusted",
                state=SteeringStepState.CURRENT,
            ),
            SteeringStepSpec(
                type=SteeringStepType.VERIFY_ACCEPT,
                objective="Accept the persisted verification evidence",
                completion_condition="Required persisted evidence is accepted",
            ),
            SteeringStepSpec(
                type=SteeringStepType.COMPLETE,
                objective="Close the long-lived Work",
                completion_condition="The Work outcome is satisfied",
            ),
        ),
    )
    executor = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=(
                DeterministicFileOperation(
                    operation=DeterministicFileOperationType.CREATE,
                    repository_relative_path="docs/steering-result.md",
                    content="# Bounded activation result\n",
                ),
            ),
            reported_outcome=ProviderReportedOutcome.SUCCESS,
            summary="one production attempt across bounded ORCH activations",
        )
    )
    works = WorkApplicationService(
        postgres_database,
        workspace_root=original_works.workspace_root,
        executor=executor,
        verifier=DeterministicVerificationProvider(
            {"Verify the admitted artifact": VerificationResultValue.PASS}
        ),
    )
    orchestrator = ProductionOrchestrator(
        works,
        max_automatic_transitions=1,
    )
    driver = PlanSteeringDriver(postgres_database, works, orchestrator)
    try:
        started = driver.activate(work.work_id)
        assert started.stop_reason is SteeringDriverStopReason.PRODUCTION_RUNNING

        def waiting_at_candidate_authority() -> None:
            projection = works.get_work(work.work_id)
            assert projection.status is WorkStatus.NEEDS_ATTENTION
            assert len(works.list_attention(work_id=work.work_id)) == 1
            assert not orchestrator.is_active(work.work_id)
            assert not driver.is_active(work.work_id)

        _wait_for(waiting_at_candidate_authority, timeout=90)
        assert executor.dispatch_count == 1
    finally:
        driver.shutdown()
        orchestrator.shutdown()


def test_steer_loop_auto_continues_two_cycles_across_restart_and_projects_api(
    postgres_database: Database,
    admitted_work,
) -> None:
    original_works, work, baseline_zero = admitted_work
    _create_steering_plan(
        postgres_database,
        work.work_id,
        steps=(
            SteeringStepSpec(
                type=SteeringStepType.DESIGN,
                objective="Govern the deterministic design Reality",
                completion_condition="The admitted design direction is recorded",
                state=SteeringStepState.CURRENT,
            ),
            SteeringStepSpec(
                type=SteeringStepType.PRODUCE,
                objective="Produce trusted result A",
                completion_condition="Production result A is trusted",
            ),
            SteeringStepSpec(
                type=SteeringStepType.PRODUCE,
                objective="Produce trusted result B",
                completion_condition="Production result B is trusted",
            ),
            SteeringStepSpec(
                type=SteeringStepType.VERIFY_ACCEPT,
                objective="Accept the persisted verification evidence",
                completion_condition="Required persisted evidence is accepted",
            ),
            SteeringStepSpec(
                type=SteeringStepType.COMPLETE,
                objective="Close the long-lived Work",
                completion_condition="Both production cycles are trusted",
            ),
        ),
    )
    executor_a = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=(
                DeterministicFileOperation(
                    operation=DeterministicFileOperationType.CREATE,
                    repository_relative_path="docs/steering-result.md",
                    content="# Trusted cycle A\n",
                ),
            ),
            reported_outcome=ProviderReportedOutcome.SUCCESS,
            summary="deterministic cycle A",
        )
    )
    works_a = WorkApplicationService(
        postgres_database,
        workspace_root=original_works.workspace_root,
        executor=executor_a,
        verifier=DeterministicVerificationProvider(
            {"Verify the admitted artifact": VerificationResultValue.PASS}
        ),
    )
    orchestrator_a = ProductionOrchestrator(works_a)
    driver_a = PlanSteeringDriver(
        postgres_database,
        works_a,
        orchestrator_a,
        capability=_WordingCapability(
            reason="Session A follows persisted governed Reality",
            provider="fake:steering-session-a",
        ),
        semantic_capability=_TestSemanticCapability(),
    )
    try:
        started = driver_a.activate(work.work_id)
        assert started.stop_reason is SteeringDriverStopReason.PRODUCTION_RUNNING
        assert started.iterations_executed == 3

        def cycle_a_waiting_for_human() -> None:
            projection = works_a.get_work(work.work_id)
            assert projection.status is WorkStatus.NEEDS_ATTENTION
            assert projection.current_production_cycle_number == 1
            assert not orchestrator_a.is_active(work.work_id)
            assert not driver_a.is_active(work.work_id)

        _wait_for(cycle_a_waiting_for_human)
        assert executor_a.dispatch_count == 1
        driver_a.shutdown()
        _authorize_current_candidate(works_a, work.work_id)
        assert orchestrator_a.schedule(work.work_id)

        def cycle_a_trusted() -> None:
            projection = works_a.get_work(work.work_id)
            assert projection.current_production_cycle_trusted is True
            assert not orchestrator_a.is_active(work.work_id)

        _wait_for(cycle_a_trusted)
        baseline_one = RuntimeService(postgres_database).current_baseline()
        assert baseline_one.id != baseline_zero.id
    finally:
        driver_a.shutdown()
        orchestrator_a.shutdown()

    executor_b = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=(
                DeterministicFileOperation(
                    operation=DeterministicFileOperationType.MODIFY,
                    repository_relative_path="docs/steering-result.md",
                    content="# Trusted cycle B\n",
                ),
            ),
            reported_outcome=ProviderReportedOutcome.SUCCESS,
            summary="deterministic cycle B after restart",
        )
    )
    works_b = WorkApplicationService(
        postgres_database,
        workspace_root=original_works.workspace_root,
        executor=executor_b,
        verifier=DeterministicVerificationProvider(
            {"Verify the admitted artifact": VerificationResultValue.PASS}
        ),
    )
    orchestrator_b = ProductionOrchestrator(works_b)
    driver_b = PlanSteeringDriver(
        postgres_database,
        works_b,
        orchestrator_b,
        capability=_WordingCapability(
            reason="Session B independently reconstructs the same material direction",
            provider="fake:steering-session-b",
        ),
    )
    try:
        assert driver_b.resume_safely_eligible_works() == (work.work_id,)

        def cycle_b_waiting_for_human() -> None:
            projection = works_b.get_work(work.work_id)
            reconstruction = SteeringApplicationService(
                postgres_database
            ).reconstruct(work.work_id)
            assert projection.status is WorkStatus.NEEDS_ATTENTION
            assert projection.current_production_cycle_number == 2
            assert reconstruction.current_step is not None
            assert reconstruction.current_step.objective == "Produce trusted result B"
            assert not orchestrator_b.is_active(work.work_id)
            assert not driver_b.is_active(work.work_id)

        _wait_for(cycle_b_waiting_for_human, timeout=90)
        assert executor_b.dispatch_count == 1
        waiting_projection = driver_b.project(work.work_id)
        assert waiting_projection.current_step is not None
        assert waiting_projection.current_step.objective == "Produce trusted result B"
        assert waiting_projection.current_production_cycle_number == 2
        assert waiting_projection.human_attention_required is True
        assert (
            waiting_projection.last_stop_reason
            is SteeringDriverStopReason.HUMAN_ATTENTION
        )
        assert waiting_projection.latest_decision is not None
        assert waiting_projection.selection_rationale == (
            "Session B independently reconstructs the same material direction"
        )
        with postgres_database.unit_of_work() as unit_of_work:
            bindings = ProductStore(unit_of_work.session).runtime_bindings(work.work_id)
            assert len(bindings) == 2
            run_a = RuntimeStore(unit_of_work.session).run(bindings[0].production_run_id)
            run_b = RuntimeStore(unit_of_work.session).run(bindings[1].production_run_id)
            assert run_a is not None and run_b is not None
            assert run_a.source_baseline_id == baseline_zero.id
            assert run_b.source_baseline_id == baseline_one.id

        _authorize_current_candidate(works_b, work.work_id)
        assert orchestrator_b.schedule(work.work_id)

        def long_lived_work_completed() -> None:
            projection = works_b.get_work(work.work_id)
            assert projection.status is WorkStatus.COMPLETED
            assert projection.work_complete is True
            assert not orchestrator_b.is_active(work.work_id)
            assert not driver_b.is_active(work.work_id)

        _wait_for(long_lived_work_completed)
        baseline_two = RuntimeService(postgres_database).current_baseline()
        assert baseline_two.id not in {baseline_zero.id, baseline_one.id}
        reconstruction = SteeringApplicationService(postgres_database).reconstruct(
            work.work_id
        )
        assert [step.type for step in reconstruction.completed_steps] == [
            SteeringStepType.DESIGN,
            SteeringStepType.PRODUCE,
            SteeringStepType.PRODUCE,
            SteeringStepType.VERIFY_ACCEPT,
        ]
        assert reconstruction.current_step is not None
        assert reconstruction.current_step.type is SteeringStepType.COMPLETE
        projection = driver_b.project(work.work_id)
        assert projection.current_step.type is SteeringStepType.COMPLETE
        assert projection.known_next_steps == ()
        assert projection.last_stop_reason is SteeringDriverStopReason.COMPLETE
        assert projection.current_production_cycle_number is None
        assert projection.current_production_cycle_trusted is False
        assert projection.human_attention_required is False

        api = create_http_application(
            database=postgres_database,
            work_service=works_b,
            orchestrator=orchestrator_b,
            steering_driver=driver_b,
        )
        response = TestClient(api).get(f"/api/works/{work.work_id}/steering")
        assert response.status_code == 200
        body = response.json()
        assert body["work_objective"] == "Establish the first bounded artifact"
        assert body["steering_enabled"] is True
        assert body["active_revision_number"] == 1
        assert body["current_step"]["type"] == "COMPLETE"
        assert body["known_next_steps"] == []
        assert body["latest_decision"]["outcome"] == "COMPLETE"
        assert body["selection_rationale"]
        assert body["automatic_progression_state"] == "STOPPED"
        assert body["last_stop_reason"] == "COMPLETE"
        assert "attempt" not in body
        assert "dispatch" not in body
    finally:
        driver_b.shutdown()
        orchestrator_b.shutdown()


def test_steer_loop_human_attention_stops_then_plan_revision_reenables(
    postgres_database: Database,
    admitted_work,
) -> None:
    works, work, _baseline = admitted_work
    created = _create_steering_plan(
        postgres_database,
        work.work_id,
        steps=(
            SteeringStepSpec(
                type=SteeringStepType.DESIGN,
                objective="Close the bounded design",
                completion_condition="Design direction is governed",
                state=SteeringStepState.CURRENT,
            ),
            SteeringStepSpec(
                type=SteeringStepType.HUMAN_DECISION,
                objective="Choose the material architecture direction",
                completion_condition="Human Authority records the direction",
            ),
            SteeringStepSpec(
                type=SteeringStepType.PRODUCE,
                objective="Produce only after the governed decision",
                completion_condition="The production result is trusted",
            ),
        ),
    )
    orchestrator = ProductionOrchestrator(works)
    driver = PlanSteeringDriver(
        postgres_database,
        works,
        orchestrator,
        semantic_capability=_TestSemanticCapability(),
    )
    try:
        stopped = driver.activate(work.work_id)
        assert stopped.stop_reason is SteeringDriverStopReason.HUMAN_ATTENTION
        assert stopped.iterations_executed == 3
        reconstruction = SteeringApplicationService(postgres_database).reconstruct(
            work.work_id
        )
        assert reconstruction.current_step is not None
        assert reconstruction.current_step.type is SteeringStepType.HUMAN_DECISION
        assert reconstruction.next_step is not None
        assert reconstruction.next_step.type is SteeringStepType.PRODUCE
        assert works.get_work(work.work_id).status is WorkStatus.NEEDS_ATTENTION
        assert driver.resume_safely_eligible_works() == ()
        with postgres_database.unit_of_work() as unit_of_work:
            bindings = ProductStore(unit_of_work.session).runtime_bindings(work.work_id)
            assert len(bindings) == 1
            assert bindings[0].steering_step_id is None
        assert orchestrator.last_outcome(work.work_id) is None

        work_ref = RealityReference(
            kind=RealityReferenceKind.WORK,
            identity=work.work_id,
        )
        revised = SteeringApplicationService(postgres_database).revise_plan(
            ReviseSteeringPlanRequest(
                steering_plan_id=created.steering_plan_id,
                superseded_revision_id=created.active_revision.revision.id,
                rationale="Human Authority resolved the material direction",
                reality_refs=(work_ref,),
                steps=(
                    SteeringStepSpec(
                        type=SteeringStepType.DESIGN,
                        objective="Record the selected bounded direction",
                        completion_condition="The Human decision is incorporated",
                        state=SteeringStepState.CURRENT,
                    ),
                    SteeringStepSpec(
                        type=SteeringStepType.PRODUCE,
                        objective="Produce the selected bounded direction",
                        completion_condition="The production result is trusted",
                    ),
                ),
            )
        )
        assert works.get_work(work.work_id).status is WorkStatus.READY
        restarted = PlanSteeringDriver(
            postgres_database,
            works,
            orchestrator,
            semantic_capability=_TestSemanticCapability(),
        )
        semantic = restarted.iterate(work.work_id)
        assert semantic.action is SteeringActionType.SEMANTIC_RESULT_ADMISSION
        resumed = restarted.iterate(work.work_id)
        assert resumed.action is SteeringActionType.STEP_TRANSITION
        assert resumed.stop_reason is None
        current = SteeringApplicationService(postgres_database).reconstruct(
            work.work_id
        ).current_step
        assert current is not None and current.type is SteeringStepType.PRODUCE
        assert revised.active_revision.revision.revision_number == 2
        restarted.shutdown()
    finally:
        driver.shutdown()
        orchestrator.shutdown()


def test_steer_loop_verify_accept_without_evidence_requests_product_acceptance(
    postgres_database: Database,
    admitted_work,
) -> None:
    works, work, _baseline = admitted_work
    _create_steering_plan(
        postgres_database,
        work.work_id,
        steps=(
            SteeringStepSpec(
                type=SteeringStepType.VERIFY_ACCEPT,
                objective="Accept the long-lived product outcome",
                completion_condition="Persisted evidence proves product acceptance",
                state=SteeringStepState.CURRENT,
            ),
            SteeringStepSpec(
                type=SteeringStepType.COMPLETE,
                objective="Close the long-lived Work",
                completion_condition="The long-lived outcome is accepted",
            ),
        ),
    )
    orchestrator = ProductionOrchestrator(works)
    driver = PlanSteeringDriver(postgres_database, works, orchestrator)
    try:
        outcome = driver.activate(work.work_id)
        assert outcome.stop_reason is SteeringDriverStopReason.HUMAN_ATTENTION
        reconstruction = SteeringApplicationService(postgres_database).reconstruct(
            work.work_id
        )
        assert reconstruction.current_step is not None
        assert reconstruction.current_step.type is SteeringStepType.VERIFY_ACCEPT
        assert reconstruction.latest_decision is not None
        assert (
            reconstruction.latest_decision.attention_reason
            is SteeringAttentionReason.PRODUCT_ACCEPTANCE_REQUIRED
        )
        assert works.get_work(work.work_id).status is WorkStatus.NEEDS_ATTENTION
        assert orchestrator.last_outcome(work.work_id) is None
    finally:
        driver.shutdown()
        orchestrator.shutdown()


def test_steer_loop_no_progress_and_transition_bound_are_typed(
    postgres_database: Database,
    admitted_work,
) -> None:
    works, work, _baseline = admitted_work
    _create_steering_plan(
        postgres_database,
        work.work_id,
        steps=(
            SteeringStepSpec(
                type=SteeringStepType.DESIGN,
                objective="Known but not current",
                completion_condition="A current Step must be admitted",
            ),
        ),
    )
    orchestrator = ProductionOrchestrator(works)
    no_progress_driver = PlanSteeringDriver(postgres_database, works, orchestrator)
    try:
        assert no_progress_driver.resume_safely_eligible_works() == ()
        result = no_progress_driver.iterate(work.work_id)
        assert result.stop_reason is SteeringDriverStopReason.NO_PROGRESS
        assert result.progressed is False
        assert result.before_fingerprint == result.after_fingerprint
        no_progress_driver.shutdown()
        shutdown = no_progress_driver.activate(work.work_id)
        assert shutdown.stop_reason is SteeringDriverStopReason.SHUTDOWN
        assert shutdown.iterations_executed == 0
    finally:
        no_progress_driver.shutdown()
        orchestrator.shutdown()

    revised = SteeringApplicationService(postgres_database).revise_plan(
        ReviseSteeringPlanRequest(
            steering_plan_id=SteeringApplicationService(
                postgres_database
            ).reconstruct(work.work_id).steering_plan_id,
            superseded_revision_id=SteeringApplicationService(
                postgres_database
            ).reconstruct(work.work_id).active_revision.revision.id,
            rationale="Admit a bounded executable direction",
            reality_refs=(
                RealityReference(
                    kind=RealityReferenceKind.WORK,
                    identity=work.work_id,
                ),
            ),
            steps=(
                SteeringStepSpec(
                    type=SteeringStepType.DESIGN,
                    objective="One bounded design action",
                    completion_condition="Design action is governed",
                    state=SteeringStepState.CURRENT,
                ),
                SteeringStepSpec(
                    type=SteeringStepType.PRODUCE,
                    objective="Later production must not run in this activation",
                    completion_condition="Production is trusted",
                ),
            ),
        )
    )
    bounded_orchestrator = ProductionOrchestrator(works)
    bounded = PlanSteeringDriver(
        postgres_database,
        works,
        bounded_orchestrator,
        semantic_capability=_TestSemanticCapability(),
        max_automatic_transitions=1,
    )
    try:
        outcome = bounded.activate(work.work_id)
        assert outcome.stop_reason is SteeringDriverStopReason.TRANSITION_BOUND
        assert outcome.iterations_executed == 1
        assert bounded_orchestrator.last_outcome(work.work_id) is None
        current = SteeringApplicationService(postgres_database).reconstruct(
            work.work_id
        ).current_step
        assert current is not None and current.type is SteeringStepType.DESIGN
        assert outcome.last_action is SteeringActionType.SEMANTIC_RESULT_ADMISSION
        assert revised.active_revision.revision.revision_number == 2
    finally:
        bounded.shutdown()
        bounded_orchestrator.shutdown()


def test_steering_migration_downgrade_and_reupgrade(
    postgres_database: Database,
) -> None:
    config = _migration_config(postgres_database)
    assert STEERING_TABLE_NAMES <= set(inspect(postgres_database.engine).get_table_names())

    command.downgrade(config, "20260904_17")
    assert STEERING_TABLE_NAMES.isdisjoint(
        inspect(postgres_database.engine).get_table_names()
    )

    command.upgrade(config, "head")
    assert STEERING_TABLE_NAMES <= set(inspect(postgres_database.engine).get_table_names())


def test_steering_production_cycle_migration_preserves_legacy_binding(
    postgres_database: Database,
    admitted_work,
) -> None:
    _works, work, _baseline = admitted_work
    with postgres_database.unit_of_work() as unit_of_work:
        before = ProductStore(unit_of_work.session).runtime_binding(work.work_id)
    assert before is not None
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260905_19")
    columns = {
        item["name"]
        for item in inspect(postgres_database.engine).get_columns(
            "work_runtime_bindings"
        )
    }
    assert "cycle_number" not in columns
    command.upgrade(config, "head")
    with postgres_database.unit_of_work() as unit_of_work:
        after = ProductStore(unit_of_work.session).runtime_binding(work.work_id)
    assert after is not None
    assert after.cycle_number == 1
    assert after.steering_step_id is None
    assert after.production_run_id == before.production_run_id
    assert after.plan_revision_id == before.plan_revision_id
    assert after.work_unit_id == before.work_unit_id

def _truncate(database: Database) -> None:
    names = ", ".join(f'"{name}"' for name in ALL_TABLE_NAMES)
    with database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {names} CASCADE")


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
