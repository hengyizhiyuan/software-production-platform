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
from spg.providers.codex_semantic import CodexSdkSemanticStepCapability


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
        super().__init__(step_type=step_type)
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
        instruction = CodexSdkSemanticStepCapability._instruction(capability.inputs[0])
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
        result = driver.last_outcome(admitted.work_id)
        assert result is not None
        assert result.last_action is SteeringActionType.SEMANTIC_RESULT_ADMISSION
        assert result.stop_reason is SteeringDriverStopReason.TRANSITION_BOUND
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


class _FakeSemanticTurn:
    id = "turn-semantic-test"

    def __init__(self, response: str) -> None:
        self.response = response

    def run(self):
        return SimpleNamespace(
            id=self.id,
            status=SimpleNamespace(value="completed"),
            error=None,
            final_response=self.response,
        )


class _FakeSemanticThread:
    id = "thread-semantic-test"

    def __init__(self, owner: "_FakeSemanticCodex") -> None:
        self.owner = owner

    def turn(self, instruction: str, **kwargs):
        self.owner.instruction = instruction
        self.owner.turn_kwargs = kwargs
        return _FakeSemanticTurn(self.owner.response)


class _FakeSemanticCodex:
    def __init__(self, response: str) -> None:
        self.response = response
        self.thread_kwargs = None
        self.turn_kwargs = None
        self.instruction = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def thread_start(self, **kwargs):
        self.thread_kwargs = kwargs
        return _FakeSemanticThread(self)


def test_sem_03_real_adapter_is_structured_read_only_and_provider_neutral(
    postgres_database: Database,
    product,
) -> None:
    works, _repository = product
    admitted, _plan = _admitted_plan(works)
    semantic_input = SemanticStepApplicationService(
        postgres_database,
        None,
    ).assemble_input(admitted.work_id)
    fake = _FakeSemanticCodex(
        json.dumps(
            {
                "bounded_summary": (
                    "Use the existing status projection to expose bounded progress."
                ),
                "decisions": ["Reuse the current Work and Steering projections."],
                "derived_constraints": list(semantic_input.constraints),
                "proposed_production": None,
                "disposition": {
                    "state": "RESOLVED",
                    "authority_assessment": "WITHIN_AUTHORITY",
                    "unresolved_questions": [],
                    "human_attention_recommendation": None,
                    "completion_claimed": True,
                },
            }
        )
    )
    candidate = CodexSdkSemanticStepCapability(
        codex_factory=lambda: fake,
    ).execute(semantic_input)

    assert candidate.work_id == semantic_input.work_id
    assert candidate.step_id == semantic_input.step.id
    assert candidate.basis_fingerprint == semantic_input.basis_fingerprint
    assert candidate.evidence_refs == semantic_input.reality_refs
    assert candidate.reasoning_provider_identity == (
        "codex-sdk:thread:thread-semantic-test:turn:turn-semantic-test"
    )
    assert fake.thread_kwargs["approval_mode"].value == "deny_all"
    assert fake.thread_kwargs["sandbox"].value == "read-only"
    assert fake.turn_kwargs["sandbox"].value == "read-only"
    assert fake.turn_kwargs["output_schema"] == (
        CodexSdkSemanticStepCapability.output_schema()
    )
    schema = fake.turn_kwargs["output_schema"]
    assert schema["$defs"]["ProductionTargetKind"]["enum"] == [
        "DOCUMENTATION_WORK",
        "CODE_WORK",
    ]
    assert schema["$defs"]["_SemanticProviderProductionProposal"]["properties"][
        "target_kind"
    ] == {"$ref": "#/$defs/ProductionTargetKind"}
    assert schema["$defs"]["_SemanticProviderProductionProposal"]["properties"][
        "artifact_targets"
    ]["items"] == {"$ref": "#/$defs/ProductionPlanArtifactTarget"}
    assert schema["$defs"]["_SemanticProviderProductionProposal"]["properties"][
        "allowed_areas"
    ]["items"]["pattern"] == r"^[^/]+/[^/]+(?:/[^/]+)*/\*\*$"
    assert "Return JSON only" in fake.instruction
    assert "target_kind must be exactly DOCUMENTATION_WORK or CODE_WORK" in (
        fake.instruction
    )
    assert "ending with /**" in fake.instruction
    assert str(semantic_input.repository_location) not in fake.instruction

    admitted_result = SemanticStepApplicationService(
        postgres_database,
        None,
    ).admit(semantic_input, candidate)
    assert admitted_result.step_id == semantic_input.step.id
    assert admitted_result.basis_fingerprint == semantic_input.basis_fingerprint
    assert admitted_result.completion_satisfied is True
    assert admitted_result.reasoning_provider_identity == (
        "codex-sdk:thread:thread-semantic-test:turn:turn-semantic-test"
    )
    assert _runtime_counts(postgres_database) == (0, 0, 0)


def test_dogfood_7_coherent_wire_result_closes_design_and_admits_produce(
    postgres_database: Database,
    product,
) -> None:
    works, repository = product
    admitted, plan = _admitted_plan(works)
    assert plan.current_step is not None
    assert plan.current_step.type is SteeringStepType.DESIGN
    fake = _FakeSemanticCodex(
        json.dumps(
            {
                "bounded_summary": (
                    "Expose bounded execution progress through the existing web path."
                ),
                "decisions": [
                    "Reuse the current Work projection and existing application UI."
                ],
                "derived_constraints": list(admitted.constraints),
                "proposed_production": {
                    "target_kind": "CODE_WORK",
                    "objective": "Expose bounded execution progress observability",
                    "artifact_targets": [],
                    "code_targets": ["src/spg/web/app.js"],
                    "allowed_areas": [],
                    "forbidden_areas": [],
                    "verification_expectation": "PATH_SCOPE and GIT_DIFF_CHECK",
                },
                "disposition": {
                    "state": "RESOLVED",
                    "authority_assessment": "WITHIN_AUTHORITY",
                    "unresolved_questions": [],
                    "human_attention_recommendation": None,
                    "completion_claimed": True,
                },
            }
        )
    )
    orchestrator = ProductionOrchestrator(works)
    driver = PlanSteeringDriver(
        postgres_database,
        works,
        orchestrator,
        semantic_capability=CodexSdkSemanticStepCapability(
            codex_factory=lambda: fake,
        ),
    )
    try:
        admitted_result = driver.iterate(admitted.work_id)
        assert admitted_result.action is SteeringActionType.SEMANTIC_RESULT_ADMISSION
        reconstructed = SteeringApplicationService(postgres_database).reconstruct(
            admitted.work_id
        )
        assert len(reconstructed.semantic_results) == 1
        assert reconstructed.semantic_results[0].completion_satisfied is True
        assert _runtime_counts(postgres_database) == (0, 0, 0)
        assert _git(repository, "status", "--porcelain") == ""

        transitioned = driver.iterate(admitted.work_id)
        assert transitioned.action is SteeringActionType.STEP_TRANSITION
        reconstructed = SteeringApplicationService(postgres_database).reconstruct(
            admitted.work_id
        )
        assert reconstructed.current_step is not None
        assert reconstructed.current_step.type is SteeringStepType.PRODUCE
        assert _runtime_counts(postgres_database) == (0, 0, 0)

        production = SteeringProductionService(postgres_database)
        production_request = production.materialize_request(admitted.work_id)
        production_admission = production.admit_cycle(production_request)
        assert production_admission.binding is not None
        assert _runtime_counts(postgres_database) == (1, 1, 0)
        assert _git(repository, "status", "--porcelain") == ""
    finally:
        driver.shutdown()
        orchestrator.shutdown()


@pytest.mark.real_codex
def test_semantic_provider_real_end_to_end_governed_design_result(
    postgres_database: Database,
    product,
) -> None:
    if os.environ.get("SPG_RUN_REAL_SEMANTIC_CODEX") != "1":
        pytest.skip("set SPG_RUN_REAL_SEMANTIC_CODEX=1 for the authorized probe")

    works, repository = product
    admitted, plan = _admitted_plan(works)
    assert admitted.production_plan is None
    assert plan.current_step is not None
    assert plan.current_step.type is SteeringStepType.DESIGN
    assert _runtime_counts(postgres_database) == (0, 0, 0)

    class RecordingRealCapability:
        def __init__(self) -> None:
            self.delegate = CodexSdkSemanticStepCapability(timeout_seconds=600)
            self.input: SemanticStepInput | None = None
            self.candidate: SemanticStepResultCandidate | None = None

        def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
            self.input = input
            self.candidate = self.delegate.execute(input)
            return self.candidate

    capability = RecordingRealCapability()
    service = SemanticStepApplicationService(
        postgres_database,
        capability,
    )
    result = service.execute(admitted.work_id)

    candidate = capability.candidate
    semantic_input = capability.input
    assert candidate is not None
    assert semantic_input is not None
    assert candidate.completion_claimed is True
    assert candidate.authority_assessment is (
        SteeringAuthorityAssessment.WITHIN_AUTHORITY
    )
    assert not candidate.unresolved_questions
    assert result.step_id == plan.current_step.id
    assert result.result_kind is SemanticResultKind.DESIGN_DIRECTION
    assert result.completion_satisfied is True
    assert result.decisions
    assert result.evidence_refs
    assert result.reasoning_provider_identity.startswith("codex-sdk:thread:")
    reconstruction = SteeringApplicationService(postgres_database).reconstruct(
        admitted.work_id
    )
    assert reconstruction.current_step is not None
    assert reconstruction.current_step.type is SteeringStepType.DESIGN
    assert reconstruction.current_step.state.value == "CURRENT"
    assert tuple(item.id for item in reconstruction.semantic_results) == (result.id,)
    assert _runtime_counts(postgres_database) == (0, 0, 0)
    assert _git(repository, "status", "--porcelain") == ""

    orchestrator = ProductionOrchestrator(works)
    driver = PlanSteeringDriver(postgres_database, works, orchestrator)
    try:
        transitioned = driver.iterate(admitted.work_id)
        assert transitioned.action is SteeringActionType.STEP_TRANSITION
        reconstruction = SteeringApplicationService(postgres_database).reconstruct(
            admitted.work_id
        )
        assert reconstruction.current_step is not None
        assert reconstruction.current_step.type is SteeringStepType.PRODUCE
        assert reconstruction.latest_decision is not None
        assert reconstruction.latest_decision.steering_outcome is (
            SteeringOutcome.AUTO_CONTINUE
        )
        assert _runtime_counts(postgres_database) == (0, 0, 0)

        production = SteeringProductionService(postgres_database)
        production_request = production.materialize_request(admitted.work_id)
        production_admission = production.admit_cycle(production_request)
        assert production_admission.binding is not None
        assert _runtime_counts(postgres_database) == (1, 1, 0)
        assert _git(repository, "status", "--porcelain") == ""
    finally:
        driver.shutdown()
        orchestrator.shutdown()
    print(
        "REAL_SEMANTIC_EVIDENCE="
        + json.dumps(
            {
                "work_id": str(admitted.work_id),
                "step_id": str(plan.current_step.id),
                "source_revision": semantic_input.source_revision,
                "source_tree": semantic_input.source_tree,
                "basis_fingerprint": candidate.basis_fingerprint,
                "result_id": str(result.id),
                "result_kind": result.result_kind.value,
                "bounded_summary": result.bounded_summary,
                "decisions": list(result.decisions),
                "evidence_refs": [
                    item.model_dump(mode="json") for item in result.evidence_refs
                ],
                "authority_assessment": result.authority_assessment.value,
                "human_attention_recommendation": (
                    result.human_attention_recommendation
                ),
                "proposed_production": (
                    None
                    if result.proposed_production is None
                    else result.proposed_production.model_dump(mode="json")
                ),
                "completion_satisfied": result.completion_satisfied,
                "provider_identity": result.reasoning_provider_identity,
                "current_step_after_transition": (
                    reconstruction.current_step.type.value
                ),
                "runtime_counts": {
                    "runs": 1,
                    "pwus": 1,
                    "runtime_commits": 0,
                },
                "repository_clean": True,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def test_sem_03_real_adapter_rejects_unstructured_provider_prose() -> None:
    with pytest.raises(
        SteeringInvariantViolation,
        match="invalid structured result",
    ):
        CodexSdkSemanticStepCapability._parse_payload(
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
            CodexSdkSemanticStepCapability._parse_payload(
                json.dumps(common | {"proposed_production": proposed_production})
            )

    schema = CodexSdkSemanticStepCapability.output_schema()
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


def test_sem_schema_12_13_blocked_driver_is_truthful_in_work_api(
    postgres_database: Database,
    product,
) -> None:
    works, _repository = product
    admitted, plan = _admitted_plan(works)
    assert plan.current_step is not None
    invalid = {
        "bounded_summary": "Malformed Dogfood #4 provider result.",
        "decisions": ["Attempt a bounded change."],
        "derived_constraints": list(admitted.constraints),
        "proposed_production": {
            "target_kind": "BOUNDED_CODE_CHANGE",
            "objective": "Expose progress",
            "artifact_targets": [],
            "code_targets": ["src/spg/web/app.js"],
            "allowed_areas": [],
            "forbidden_areas": [],
            "verification_expectation": "Focused tests",
        },
        "disposition": {
            "state": "RESOLVED",
            "authority_assessment": "WITHIN_AUTHORITY",
            "unresolved_questions": [],
            "human_attention_recommendation": None,
            "completion_claimed": True,
        },
    }
    fake = _FakeSemanticCodex(json.dumps(invalid))
    orchestrator = ProductionOrchestrator(works)
    driver = PlanSteeringDriver(
        postgres_database,
        works,
        orchestrator,
        semantic_capability=CodexSdkSemanticStepCapability(
            codex_factory=lambda: fake,
        ),
    )
    try:
        assert driver.schedule(admitted.work_id) is True
        assert driver.wait_until_idle(admitted.work_id, 5)
        outcome = driver.last_outcome(admitted.work_id)
        assert outcome is not None
        assert outcome.stop_reason is SteeringDriverStopReason.BLOCKED
        assert not SteeringApplicationService(postgres_database).reconstruct(
            admitted.work_id
        ).semantic_results
        assert _runtime_counts(postgres_database) == (0, 0, 0)

        api = create_http_application(
            database=postgres_database,
            work_service=works,
            orchestrator=orchestrator,
            steering_driver=driver,
        )
        response = TestClient(api).get(f"/api/works/{admitted.work_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["current_steering_step_type"] == "DESIGN"
        assert body["automatic_progression_state"] == "STOPPED"
        assert body["last_stop_reason"] == "BLOCKED"
        assert body["most_recent_meaningful_event"] == "STEERING_STOPPED_BLOCKED"
        assert "stopped on a governed invariant" in body["what_happens_next"]
    finally:
        driver.shutdown()
        orchestrator.shutdown()


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
