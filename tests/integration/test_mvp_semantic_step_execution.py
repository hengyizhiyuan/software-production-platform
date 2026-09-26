from collections.abc import Iterator
import json
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
from time import monotonic, sleep

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, inspect, select, text

from spg.application.orchestration import ProductionOrchestrator
from spg.application.post_admission import WorkPostAdmissionService
from spg.application.runtime import RuntimeService
from spg.application.semantic_steps import SemanticStepApplicationService
from spg.application.steering import SteeringApplicationService
from spg.application.steering_bootstrap import SteeringBootstrapService
from spg.application.steering_decision import (
    DeterministicPlanSteeringCapability,
    SteeringDecisionApplicationService,
)
from spg.application.steering_driver import PlanSteeringDriver
from spg.application.steering_production import SteeringProductionService
from spg.application.work import WorkApplicationService
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.api.http import create_http_application
from spg.domain.change import ProductionTargetKind
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import (
    EngineeringContextReference,
    WorkMode,
    WorkStatus,
)
from spg.domain.runtime import BootstrapRequest
from spg.domain.steering import (
    SemanticProductionProposal,
    SemanticResultKind,
    SemanticStepInput,
    SemanticStepResultCandidate,
    StaleSemanticStepCandidate,
    SteeringActionType,
    SteeringAutomaticProgressionState,
    SteeringAuthorityAssessment,
    SteeringDriverStopReason,
    SteeringInvariantViolation,
    SteeringOutcome,
    SteeringStepType,
    TransitionSteeringStepRequest,
)
from spg.infrastructure.persistence import Database, product_tables, runtime_tables
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_schema import (
    production_runs,
    production_work_units,
    runtime_commits,
)
from spg.infrastructure.persistence.steering_schema import semantic_step_results
from spg.infrastructure.model_runtime import ModelFailureKind, ModelProviderError
from spg.providers.semantic_wire import SemanticStepWireContract
from spg.domain.refinement_contract import RefinementClass, RefinementSignalKind


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOGFOOD_MOTIVE = """我希望改善 Watt 在任务执行过程中的状态可观测性。
现在任务自动执行时，我很难判断系统正在做什么、做到哪一步、
是否还在正常工作，有时候甚至会以为它卡死了。
希望用户能清楚知道当前阶段、正在进行的事情、必要的进度和阻塞原因，
但这轮先满足开发阶段的必要体验，
不要做完整的 UX/UI 重构，
也不要为了展示效果引入复杂的新基础设施。"""


class _SemanticCapability:
    def __init__(
        self,
        *,
        step_type: SteeringStepType,
        provider: str = "fake:semantic-v1",
        expansion: bool = False,
        proposed_production: bool = False,
        summary: str = "A bounded semantic direction is grounded in the exact baseline.",
    ) -> None:
        self.step_type = step_type
        self.provider = provider
        self.expansion = expansion
        self.proposed_production = proposed_production
        self.summary = summary
        self.inputs: list[SemanticStepInput] = []

    def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
        self.inputs.append(input)
        assert input.step.type is self.step_type
        production = (
            SemanticProductionProposal(
                target_kind=ProductionTargetKind.CODE_WORK,
                objective="Improve bounded execution progress observability",
                code_targets=("src/spg/web/app.js",),
                forbidden_areas=("migrations/**",),
                verification_expectation="PATH_SCOPE and GIT_DIFF_CHECK",
            )
            if self.proposed_production
            else None
        )
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
            bounded_summary=self.summary,
            decisions=(
                "Expose bounded plan-stage progress using the existing web application path.",
            ),
            derived_constraints=input.constraints,
            evidence_refs=input.reality_refs,
            unresolved_questions=(
                ("Human must admit the expanded repository authority.",)
                if self.expansion
                else ()
            ),
            authority_assessment=(
                SteeringAuthorityAssessment.EXPANDS_AUTHORITY
                if self.expansion
                else SteeringAuthorityAssessment.WITHIN_AUTHORITY
            ),
            human_attention_recommendation=(
                "Keep the change inside the admitted Work scope."
                if self.expansion
                else None
            ),
            proposed_production=production,
            reasoning_provider_identity=self.provider,
            completion_claimed=not self.expansion,
        )


class _TransientProviderFailureCapability(_SemanticCapability):
    def __init__(self, *, step_type: SteeringStepType) -> None:
        super().__init__(step_type=step_type, proposed_production=True)
        self.calls = 0

    def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
        self.calls += 1
        if self.calls == 1:
            raise ModelProviderError(
                ModelFailureKind.TIMEOUT_OR_NETWORK,
                "test Provider transport failed",
                request_sent=True,
                usage_unknown=True,
                retryable=True,
            )
        return super().execute(input)


class _RepeatedProviderFailureCapability(_SemanticCapability):
    def __init__(self) -> None:
        super().__init__(step_type=SteeringStepType.DESIGN)
        self.calls = 0

    def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
        self.calls += 1
        raise ModelProviderError(
            ModelFailureKind.TIMEOUT_OR_NETWORK,
            "controlled repeated transport failure",
            request_sent=True, usage_unknown=True, retryable=True,
        )


def _migration_config(database: Database) -> Config:
    os.environ["SPG_DATABASE_URL"] = database.engine.url.render_as_string(
        hide_password=False
    )
    return Config(PROJECT_ROOT / "alembic.ini")


@pytest.fixture(autouse=True)
def clean_schema(postgres_database: Database) -> Iterator[None]:
    previous = os.environ.get("SPG_DATABASE_URL")
    command.upgrade(_migration_config(postgres_database), "head")
    names = sorted({table.name for table in (*product_tables, *runtime_tables)})
    with postgres_database.engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {', '.join(names)} RESTART IDENTITY CASCADE"))
    try:
        yield
    finally:
        with postgres_database.engine.begin() as connection:
            connection.execute(text(f"TRUNCATE {', '.join(names)} RESTART IDENTITY CASCADE"))
        if previous is None:
            os.environ.pop("SPG_DATABASE_URL", None)
        else:
            os.environ["SPG_DATABASE_URL"] = previous


@pytest.fixture
def product(postgres_database: Database, tmp_path: Path):
    repository = tmp_path / "semantic-repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "AI_context.md").write_text("governed context\n", encoding="utf-8")
    (repository / "src" / "spg" / "web").mkdir(parents=True)
    (repository / "src" / "spg" / "web" / "app.js").write_text(
        "const status = 'ready';\n",
        encoding="utf-8",
    )
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    RuntimeService(postgres_database).bootstrap_trusted_baseline(
        BootstrapRequest(
            repository_path=repository,
            repository_identity="test://semantic-step",
            repository_ref="refs/heads/main",
            authority_identity="architecture-lead:test",
            scope={"slice": "MVP-PLAN-STEER-1I"},
        )
    )
    works = WorkApplicationService(
        postgres_database,
        workspace_root=tmp_path / "workspaces",
    )
    works.register_engineering_resource(
        repository_identity="test://semantic-step",
        location_ref=str(repository),
        authoritative_ref="refs/heads/main",
        context_references=(
            EngineeringContextReference(
                semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                repository_relative_path="AI_context.md",
            ),
        ),
    )
    return works, repository


def _admitted_plan(works: WorkApplicationService, requirement: str = DOGFOOD_MOTIVE):
    draft = works.refine_work(
        works.submit_work(
            requirement,
            mode=WorkMode.LONG_LIVED_STEERING,
        ).work_id
    )
    assert draft.production_plan is None
    admitted = works.approve_work(
        draft.work_id,
        authority_identity="human:semantic-dogfood",
    )
    plan = SteeringBootstrapService(works.database).bootstrap(admitted.work_id)
    return admitted, plan


def _runtime_counts(database: Database) -> tuple[int, int, int]:
    with database.engine.connect() as connection:
        return (
            connection.execute(select(func.count()).select_from(production_runs)).scalar_one(),
            connection.execute(
                select(func.count()).select_from(production_work_units)
            ).scalar_one(),
            connection.execute(
                select(func.count()).select_from(runtime_commits)
            ).scalar_one(),
        )


def test_sem_01_03_04_05_06_08_09_10_12_14_15_real_product_path(
    postgres_database: Database,
    product,
) -> None:
    works, repository = product
    admitted, plan = _admitted_plan(works)
    assert plan.current_step is not None
    assert plan.current_step.type is SteeringStepType.DESIGN
    capability = _SemanticCapability(
        step_type=SteeringStepType.DESIGN,
        proposed_production=True,
    )
    orchestrator = ProductionOrchestrator(works)
    driver = PlanSteeringDriver(
        postgres_database,
        works,
        orchestrator,
        semantic_capability=capability,
        max_automatic_transitions=1,
    )
    post_admission = WorkPostAdmissionService(
        works,
        SteeringBootstrapService(postgres_database),
        driver,
        orchestrator,
    )
    try:
        post_admission.activate(admitted.work_id)
        assert driver.wait_until_idle(admitted.work_id, 5)
        outcome = driver.last_outcome(admitted.work_id)
        assert outcome is not None
        assert outcome.last_action is SteeringActionType.SEMANTIC_RESULT_ADMISSION
        assert outcome.stop_reason is SteeringDriverStopReason.TRANSITION_BOUND
        reconstructed = SteeringApplicationService(postgres_database).reconstruct(
            admitted.work_id
        )
        assert reconstructed.current_step is not None
        assert reconstructed.current_step.type is SteeringStepType.DESIGN
        assert len(reconstructed.semantic_results) == 1
        result = reconstructed.semantic_results[0]
        assert result.step_id == reconstructed.current_step.id
        assert result.completion_satisfied is True
        assert result.reasoning_provider_identity == "fake:semantic-v1"
        assert result.proposed_production is not None
        assert result.evidence_refs
        assert capability.inputs[0].source_tree == _git(
            repository, "rev-parse", "HEAD^{tree}"
        )
        assert capability.inputs[0].context_materials[0].repository_relative_path == (
            "AI_context.md"
        )
        instruction = SemanticStepWireContract._instruction(capability.inputs[0])
        assert "Do not invoke shell, filesystem, or repository tools" in instruction
        assert "repository_tree_paths and context_materials" in instruction
        assert "missing full contents alone is not a Human decision" in instruction
        assert _runtime_counts(postgres_database) == (0, 0, 0)
        assert _git(repository, "status", "--porcelain") == ""

        projection = works.get_work(admitted.work_id)
        assert projection.production_plan is not None
        assert projection.production_plan.fit_classification.value == "ONE_PWU_FIT"
        assert projection.change_proposal is not None
        assert projection.change_proposal.required_targets[0].path == (
            "src/spg/web/app.js"
        )

        second = driver.iterate(admitted.work_id)
        assert second.action is SteeringActionType.STEP_TRANSITION
        reconstructed = SteeringApplicationService(postgres_database).reconstruct(
            admitted.work_id
        )
        assert reconstructed.current_step is not None
        assert reconstructed.current_step.type is SteeringStepType.PRODUCE
        assert reconstructed.latest_decision is not None
        assert any(
            reference.kind.value == "SEMANTIC_RESULT"
            and reference.identity == result.id
            for reference in reconstructed.latest_decision.reality_refs
        )
        assert _runtime_counts(postgres_database) == (0, 0, 0)

        production = SteeringProductionService(postgres_database)
        production_request = production.materialize_request(admitted.work_id)
        production_admission = production.admit_cycle(production_request)
        assert production_admission.binding is not None
        assert _runtime_counts(postgres_database) == (1, 1, 0)
    finally:
        driver.shutdown()
        orchestrator.shutdown()


def test_sem_01_06_design_cannot_transition_without_governed_result(
    postgres_database: Database,
    product,
) -> None:
    works, _repository = product
    admitted, plan = _admitted_plan(works)
    current = plan.current_step
    next_step = plan.next_step
    assert current is not None and next_step is not None
    frame, candidate = SteeringDecisionApplicationService(
        postgres_database,
        DeterministicPlanSteeringCapability(),
    ).evaluate(admitted.work_id)
    decision = SteeringDecisionApplicationService(
        postgres_database,
        DeterministicPlanSteeringCapability(),
    ).admit(admitted.work_id, candidate)
    with pytest.raises(
        SteeringInvariantViolation,
        match="without exact governed result evidence",
    ):
        SteeringApplicationService(postgres_database).transition_step(
            TransitionSteeringStepRequest(
                steering_plan_revision_id=frame.reconstruction.active_revision.revision.id,
                current_step_id=current.id,
                next_step_id=next_step.id,
                steering_decision_id=decision.id,
            )
        )
    assert SteeringApplicationService(postgres_database).reconstruct(
        admitted.work_id
    ).current_step.id == current.id


def test_sem_02_06_13_refine_requires_governed_result(
    postgres_database: Database,
    product,
) -> None:
    works, _repository = product
    admitted, plan = _admitted_plan(
        works,
        "Explore and clarify the bounded status feedback direction for Watt",
    )
    assert plan.current_step is not None
    assert plan.current_step.type is SteeringStepType.REFINE
    orchestrator = ProductionOrchestrator(works)
    unavailable = PlanSteeringDriver(postgres_database, works, orchestrator)
    try:
        no_progress = unavailable.iterate(admitted.work_id)
        assert (
            no_progress.stop_reason
            is SteeringDriverStopReason.CAPABILITY_UNAVAILABLE
        )
        assert not SteeringApplicationService(postgres_database).reconstruct(
            admitted.work_id
        ).semantic_results
    finally:
        unavailable.shutdown()

    capability = _SemanticCapability(step_type=SteeringStepType.REFINE)
    driver = PlanSteeringDriver(
        postgres_database,
        works,
        orchestrator,
        semantic_capability=capability,
    )
    try:
        admitted_result = driver.iterate(admitted.work_id)
        assert admitted_result.action is SteeringActionType.SEMANTIC_RESULT_ADMISSION
        assert _runtime_counts(postgres_database) == (0, 0, 0)
        transitioned = driver.iterate(admitted.work_id)
        assert transitioned.action is SteeringActionType.STEP_TRANSITION
        reconstructed = SteeringApplicationService(postgres_database).reconstruct(
            admitted.work_id
        )
        assert reconstructed.current_step is not None
        assert reconstructed.current_step.type is SteeringStepType.DESIGN
    finally:
        driver.shutdown()
        orchestrator.shutdown()


def test_retryable_semantic_provider_failure_waits_and_resumes_automatically(
    postgres_database: Database,
    product,
) -> None:
    works, _repository = product
    admitted, plan = _admitted_plan(works)
    assert plan.current_step is not None
    capability = _TransientProviderFailureCapability(
        step_type=SteeringStepType.DESIGN
    )
    orchestrator = ProductionOrchestrator(works)
    driver = PlanSteeringDriver(
        postgres_database,
        works,
        orchestrator,
        semantic_capability=capability,
        max_automatic_transitions=1,
        provider_retry_base_delay_seconds=0.2,
        provider_retry_max_delay_seconds=0.2,
    )
    try:
        assert driver.schedule(admitted.work_id) is True
        deadline = monotonic() + 3
        waiting = None
        while monotonic() < deadline:
            waiting = driver.project(admitted.work_id)
            if (
                waiting.automatic_progression_state
                is SteeringAutomaticProgressionState.WAITING_RESOURCE
            ):
                break
            sleep(0.01)
        assert waiting is not None
        assert (
            waiting.automatic_progression_state
            is SteeringAutomaticProgressionState.WAITING_RESOURCE
        )
        assert waiting.last_stop_reason is SteeringDriverStopReason.CAPABILITY_UNAVAILABLE

        while monotonic() < deadline:
            if (
                capability.calls == 2
                and SteeringApplicationService(postgres_database)
                .reconstruct(admitted.work_id)
                .semantic_results
            ):
                break
            sleep(0.01)
        assert capability.calls == 2
        assert driver.wait_until_idle(admitted.work_id, 2)
        with postgres_database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            recovery = store.list_self_refine_events(
                work_id=admitted.work_id, component="steering/provider",
            )
            assert len(recovery) == 1
            assert recovery[0].final_result == "RECOVERED"
            assert recovery[0].work_resume_result == "RESUMED"
            assert [action.outcome for action in store.self_refine_actions(recovery[0].id)] == [
                "RETRY_SCHEDULED", "RECOVERED",
            ]
        result = driver.last_outcome(admitted.work_id)
        assert result is not None
        assert result.last_action is SteeringActionType.SEMANTIC_RESULT_ADMISSION
        assert result.stop_reason is SteeringDriverStopReason.TRANSITION_BOUND

        reconstructed = SteeringApplicationService(postgres_database).reconstruct(
            admitted.work_id
        )
        assert len(reconstructed.semantic_results) == 1
        semantic_result = reconstructed.semantic_results[0]
        assert semantic_result.completion_satisfied is True
        assert semantic_result.proposed_production is not None
        assert reconstructed.current_step is not None
        assert reconstructed.current_step.type is SteeringStepType.DESIGN

        assert driver.schedule(admitted.work_id) is True
        assert driver.wait_until_idle(admitted.work_id, 2)
        transitioned = driver.last_outcome(admitted.work_id)
        assert transitioned is not None
        assert transitioned.last_action is SteeringActionType.STEP_TRANSITION
        assert transitioned.stop_reason is SteeringDriverStopReason.TRANSITION_BOUND

        advanced = SteeringApplicationService(postgres_database).reconstruct(
            admitted.work_id
        )
        assert advanced.current_step is not None
        assert advanced.current_step.type is SteeringStepType.PRODUCE
        assert len(advanced.semantic_results) == 1
        assert capability.calls == 2
    finally:
        driver.shutdown()
        orchestrator.shutdown()


def test_repeated_steering_provider_failure_converges_to_durable_escalation(
    postgres_database: Database, product,
) -> None:
    works, _repository = product
    admitted, _plan = _admitted_plan(works)
    capability = _RepeatedProviderFailureCapability()
    orchestrator = ProductionOrchestrator(works)
    driver = PlanSteeringDriver(
        postgres_database, works, orchestrator,
        semantic_capability=capability,
        max_automatic_transitions=1,
        provider_retry_base_delay_seconds=0.05,
        provider_retry_max_delay_seconds=0.05,
        provider_retry_same_failure_threshold=2,
    )
    try:
        assert driver.schedule(admitted.work_id)
        deadline = monotonic() + 4
        while monotonic() < deadline:
            with postgres_database.unit_of_work() as uow:
                store = NativeExecutionStore(uow.session)
                records = store.list_self_refine_events(
                    work_id=admitted.work_id, component="steering/provider",
                )
            if records and records[0].final_result == "ESCALATED":
                break
            sleep(0.02)
        assert capability.calls == 2
        assert records[0].final_result == "ESCALATED"
        with postgres_database.unit_of_work() as uow:
            assert [action.outcome for action in NativeExecutionStore(uow.session).self_refine_actions(records[0].id)] == [
                "RETRY_SCHEDULED", "ESCALATED",
            ]
        assert driver.schedule(admitted.work_id)
        assert driver.wait_until_idle(admitted.work_id, 2)
        assert capability.calls == 2
    finally:
        driver.shutdown()
        orchestrator.shutdown()


def test_sem_07_stale_semantic_candidate_is_rejected(
    postgres_database: Database,
    product,
) -> None:
    works, _repository = product
    admitted, _plan = _admitted_plan(works)
    capability = _SemanticCapability(step_type=SteeringStepType.DESIGN)
    service = SemanticStepApplicationService(postgres_database, capability)
    semantic_input = service.assemble_input(admitted.work_id)
    candidate = capability.execute(semantic_input)
    works.update_work_tags(admitted.work_id, ("basis-changed",))
    with pytest.raises(StaleSemanticStepCandidate):
        service.admit(semantic_input, candidate)
    with postgres_database.engine.connect() as connection:
        assert connection.execute(
            select(func.count()).select_from(semantic_step_results)
        ).scalar_one() == 0


def test_semantic_admission_conflict_refines_once_on_same_basis_and_records_routine(
    postgres_database: Database, product,
) -> None:
    works, _repository = product
    admitted, _plan = _admitted_plan(works)

    class RefiningCapability(_SemanticCapability):
        def __init__(self) -> None:
            super().__init__(step_type=SteeringStepType.DESIGN)
            self.feedback: str | None = None

        def refine(self, input: SemanticStepInput, *, validation_feedback: str):
            self.feedback = validation_feedback
            self.proposed_production = True
            return self.execute(input)

    capability = RefiningCapability()
    service = SemanticStepApplicationService(postgres_database, capability)
    admitted_result = service.execute(admitted.work_id)
    assert admitted_result.completion_satisfied
    assert len(capability.inputs) == 2
    assert capability.inputs[0].basis_fingerprint == capability.inputs[1].basis_fingerprint
    assert capability.feedback is not None and "production proposal" in capability.feedback
    with postgres_database.unit_of_work() as uow:
        events = NativeExecutionStore(uow.session).list_self_refine_events(
            work_id=admitted.work_id, component="steering/semantic-step",
        )
        assert len(events) == 1
        assert events[0].refinement_class is RefinementClass.ROUTINE_STOCHASTIC_REFINEMENT
        assert events[0].signal_kind is RefinementSignalKind.CONTRACT_MISMATCH
        assert events[0].final_result == "RECOVERED"
        assert events[0].budget_decision["attempt_count"] == 2


def test_semantic_authority_expansion_does_not_receive_automatic_refinement(
    postgres_database: Database, product,
) -> None:
    works, _repository = product
    admitted, _plan = _admitted_plan(works)

    class AuthorityCandidate(_SemanticCapability):
        def __init__(self) -> None:
            super().__init__(step_type=SteeringStepType.DESIGN, proposed_production=True)
            self.refine_called = False

        def execute(self, input: SemanticStepInput):
            candidate = super().execute(input)
            return candidate.model_copy(update={
                "derived_constraints": (*input.constraints, "Broaden Human-approved scope"),
            })

        def refine(self, input: SemanticStepInput, *, validation_feedback: str):
            self.refine_called = True
            return super().execute(input)

    capability = AuthorityCandidate()
    with pytest.raises(SteeringInvariantViolation, match="cannot silently add"):
        SemanticStepApplicationService(postgres_database, capability).execute(admitted.work_id)
    assert not capability.refine_called


def test_semantic_nonconvergence_stops_after_one_feedback_and_retains_diagnostics(
    postgres_database: Database, product,
) -> None:
    works, _repository = product
    admitted, _plan = _admitted_plan(works)

    class UnchangedCandidate(_SemanticCapability):
        def __init__(self) -> None:
            super().__init__(step_type=SteeringStepType.DESIGN)
            self.refinements = 0

        def refine(self, input: SemanticStepInput, *, validation_feedback: str):
            self.refinements += 1
            return self.execute(input)

    capability = UnchangedCandidate()
    with pytest.raises(SteeringInvariantViolation, match="production proposal"):
        SemanticStepApplicationService(postgres_database, capability).execute(admitted.work_id)
    assert capability.refinements == 1
    with postgres_database.unit_of_work() as uow:
        events = NativeExecutionStore(uow.session).list_self_refine_events(
            work_id=admitted.work_id, component="steering/semantic-step",
        )
        assert len(events) == 1
        assert events[0].refinement_class is RefinementClass.SYSTEMIC_OR_NON_CONVERGING_INCIDENT
        assert events[0].final_result == "ESCALATED"
        assert events[0].diagnostic_evidence["basis_fingerprint"]
        assert events[0].diagnostic_evidence["second_error_type"] == "SteeringInvariantViolation"


def test_sem_13_derived_constraint_cannot_silently_expand_work_authority(
    postgres_database: Database,
    product,
) -> None:
    works, _repository = product
    admitted, _plan = _admitted_plan(
        works,
        "Explore and clarify the bounded status feedback direction for Watt",
    )
    capability = _SemanticCapability(step_type=SteeringStepType.REFINE)
    service = SemanticStepApplicationService(postgres_database, capability)
    semantic_input = service.assemble_input(admitted.work_id)
    candidate = capability.execute(semantic_input).model_copy(
        update={
            "derived_constraints": (
                *semantic_input.constraints,
                "Silently expand the Human-approved Work envelope",
            )
        }
    )

    with pytest.raises(
        SteeringInvariantViolation,
        match="cannot silently add Human-approved constraints",
    ):
        service.admit(semantic_input, candidate)


def test_sem_11_authority_expansion_stops_before_runtime(
    postgres_database: Database,
    product,
) -> None:
    works, _repository = product
    admitted, plan = _admitted_plan(works)
    assert plan.current_step is not None
    orchestrator = ProductionOrchestrator(works)
    driver = PlanSteeringDriver(
        postgres_database,
        works,
        orchestrator,
        semantic_capability=_SemanticCapability(
            step_type=SteeringStepType.DESIGN,
            expansion=True,
        ),
    )
    try:
        stopped = driver.iterate(admitted.work_id)
        assert stopped.stop_reason is SteeringDriverStopReason.HUMAN_ATTENTION
        reconstructed = SteeringApplicationService(postgres_database).reconstruct(
            admitted.work_id
        )
        assert reconstructed.current_step is not None
        assert reconstructed.current_step.type is SteeringStepType.DESIGN
        assert reconstructed.latest_decision is not None
        assert reconstructed.latest_decision.steering_outcome is (
            SteeringOutcome.HUMAN_ATTENTION
        )
        assert reconstructed.semantic_results[0].completion_satisfied is False
        assert works.get_work(admitted.work_id).status is WorkStatus.NEEDS_ATTENTION
        assert _runtime_counts(postgres_database) == (0, 0, 0)
    finally:
        driver.shutdown()
        orchestrator.shutdown()


def test_sem_16_provider_wording_and_identity_do_not_define_material_direction(
    product,
) -> None:
    works, _repository = product
    admitted, _plan = _admitted_plan(works)
    service = SemanticStepApplicationService(works.database, None)
    semantic_input = service.assemble_input(admitted.work_id)
    first_capability = _SemanticCapability(
        step_type=SteeringStepType.DESIGN,
        provider="fake:one",
        summary="First provider wording for the same bounded material direction.",
    )
    second_capability = _SemanticCapability(
        step_type=SteeringStepType.DESIGN,
        provider="fake:two",
        summary="Different prose describing the same bounded material direction.",
    )
    first = first_capability.execute(semantic_input)
    second = second_capability.execute(semantic_input)
    assert first.material_direction_fingerprint == second.material_direction_fingerprint


def test_sem_03_real_adapter_rejects_unstructured_provider_prose() -> None:
    with pytest.raises(
        SteeringInvariantViolation,
        match="invalid structured result",
    ):
        SemanticStepWireContract._parse_payload(
            "A free-form design answer is not governed application Reality."
        )


def test_sem_schema_03_04_05_06_15_dogfood_4_malformed_shapes_remain_rejected(
) -> None:
    common = {
        "bounded_summary": "Bounded design proposal from current Reality.",
        "decisions": ["Reuse the existing Work and Steering projections."],
        "derived_constraints": [],
        "disposition": {
            "state": "RESOLVED",
            "authority_assessment": "WITHIN_AUTHORITY",
            "unresolved_questions": [],
            "human_attention_recommendation": None,
            "completion_claimed": True,
        },
    }
    invalid_proposals = (
        {
            "target_kind": "BOUNDED_CODE_CHANGE",
            "objective": "Expose bounded execution progress",
            "artifact_targets": [],
            "code_targets": ["src/spg/web/app.js"],
            "allowed_areas": [],
            "forbidden_areas": [],
            "verification_expectation": "Focused API and UI tests",
        },
        {
            "target_kind": "DOCUMENTATION_WORK",
            "objective": "Document bounded execution progress",
            "artifact_targets": ["path-a", "path-b"],
            "code_targets": [],
            "allowed_areas": [],
            "forbidden_areas": [],
            "verification_expectation": "Artifact path verification",
        },
        {
            "target_kind": "CODE_WORK",
            "objective": "Expose bounded execution progress",
            "artifact_targets": [],
            "code_targets": [],
            "allowed_areas": ["frontend files related to observability"],
            "forbidden_areas": [],
            "verification_expectation": "Focused API and UI tests",
        },
        {
            "target_kind": "CODE_WORK",
            "objective": "Expose bounded execution progress",
            "artifact_targets": [],
            "code_targets": [],
            "allowed_areas": ["src/**", "tests/**"],
            "forbidden_areas": [],
            "verification_expectation": "Focused API and UI tests",
        },
    )

    for proposed_production in invalid_proposals:
        with pytest.raises(
            SteeringInvariantViolation,
            match="invalid structured result",
        ):
            SemanticStepWireContract._parse_payload(
                json.dumps(common | {"proposed_production": proposed_production})
            )

    schema = SemanticStepWireContract.output_schema()
    proposal = schema["$defs"]["_SemanticProviderProductionProposal"]["properties"]
    assert "BOUNDED_CODE_CHANGE" not in schema["$defs"][
        "ProductionTargetKind"
    ]["enum"]
    assert proposal["artifact_targets"]["items"]["$ref"] == (
        "#/$defs/ProductionPlanArtifactTarget"
    )
    assert proposal["allowed_areas"]["items"]["pattern"] == (
        r"^[^/]+/[^/]+(?:/[^/]+)*/\*\*$"
    )


def test_semantic_result_migration_downgrade_and_reupgrade(
    postgres_database: Database,
) -> None:
    config = _migration_config(postgres_database)
    assert "semantic_step_results" in inspect(
        postgres_database.engine
    ).get_table_names()

    command.downgrade(config, "20260905_21")
    assert "semantic_step_results" not in inspect(
        postgres_database.engine
    ).get_table_names()

    command.upgrade(config, "head")
    assert "semantic_step_results" in inspect(
        postgres_database.engine
    ).get_table_names()


def _git(repository: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()
