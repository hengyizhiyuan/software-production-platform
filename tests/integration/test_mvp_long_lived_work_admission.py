from collections.abc import Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from spg.api import create_http_application
from spg.application.post_admission import WorkPostAdmissionService
from spg.application.runtime import RuntimeService
from spg.application.steering_bootstrap import SteeringBootstrapService
from spg.application.steering_driver import PlanSteeringDriver
from spg.application.steering_production import SteeringProductionService
from spg.application.work import WorkApplicationService
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import (
    AttentionKind,
    EngineeringContextReference,
    ProductInvariantViolation,
    WorkMode,
    WorkRefinementRequest,
    WorkStatus,
)
from spg.domain.runtime import BootstrapRequest
from spg.domain.steering import SteeringOutcome, SteeringStepType
from spg.infrastructure.persistence import (
    Database,
    product_tables,
    runtime_tables,
    steering_tables,
)
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_schema import (
    production_runs,
    production_work_units,
    provider_execution_reports,
)
from spg.infrastructure.persistence.steering_schema import (
    steering_decisions,
    steering_plan_revisions,
    steering_plans,
    steering_steps,
)


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALL_TABLE_NAMES = {
    table.name for table in (*product_tables, *runtime_tables, *steering_tables)
}

DOGFOOD_MOTIVE = """我希望改善 Watt 在任务执行过程中的状态可观测性。
现在任务自动执行时，我很难判断系统正在做什么、做到哪一步、
是否还在正常工作，有时候甚至会以为它卡死了。
希望用户能清楚知道当前阶段、正在进行的事情、必要的进度和阻塞原因，
但这轮先满足开发阶段的必要体验，
不要做完整的 UX/UI 重构，
也不要为了展示效果引入复杂的新基础设施。"""


@dataclass(frozen=True)
class AdmissionFacts:
    database: Database
    service: WorkApplicationService


class _RecordingOrchestrator:
    def __init__(self) -> None:
        self.scheduled_work_ids: list[UUID] = []
        self._active_work_ids: set[UUID] = set()

    def resume_safely_eligible_works(self) -> tuple[()]:
        return ()

    def schedule(self, work_id: UUID) -> bool:
        if work_id in self._active_work_ids:
            return False
        self._active_work_ids.add(work_id)
        self.scheduled_work_ids.append(work_id)
        return True

    def is_active(self, work_id: UUID) -> bool:
        return work_id in self._active_work_ids

    def last_outcome(self, _work_id: UUID):
        return None

    def add_outcome_listener(self, _listener) -> None:
        return None

    def shutdown(self) -> None:
        self._active_work_ids.clear()


class _RecordingSteeringDriver(PlanSteeringDriver):
    def __init__(
        self,
        database: Database,
        work_service: WorkApplicationService,
        production_orchestrator: _RecordingOrchestrator,
    ) -> None:
        super().__init__(database, work_service, production_orchestrator)
        self.scheduled_work_ids: list[UUID] = []

    def schedule(self, work_id: UUID) -> bool:
        with self._condition:
            if work_id in self._active_work_ids:
                return False
            self._active_work_ids.add(work_id)
            self.scheduled_work_ids.append(work_id)
        return True

    def shutdown(self, timeout: float = 2.0) -> None:
        del timeout
        with self._condition:
            self._active_work_ids.clear()
            self._pending_work_ids.clear()


class _FailingSteeringBootstrap:
    def bootstrap(self, _work_id: UUID):
        raise ProductInvariantViolation("deterministic Steering bootstrap failure")


class _UnavailableSteeringDriver:
    def __init__(self) -> None:
        self.scheduled_work_ids: list[UUID] = []

    def schedule(self, work_id: UUID) -> bool:
        self.scheduled_work_ids.append(work_id)
        return False

    def is_active(self, _work_id: UUID) -> bool:
        return False


def _migration_config(database: Database) -> Config:
    os.environ["SPG_DATABASE_URL"] = database.engine.url.render_as_string(
        hide_password=False
    )
    return Config(PROJECT_ROOT / "alembic.ini")


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
def admission_facts(
    postgres_database: Database,
    tmp_path: Path,
) -> AdmissionFacts:
    repository = tmp_path / "long-lived-work-repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "AI_context.md").write_text("governed context\n", encoding="utf-8")
    (repository / "docs").mkdir()
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
            repository_identity="test://long-lived-work",
            repository_ref="refs/heads/main",
            authority_identity="architecture-lead:test",
            scope={"slice": "MVP-PLAN-STEER-1G"},
        )
    )
    service = WorkApplicationService(
        postgres_database,
        workspace_root=tmp_path / "workspaces",
    )
    service.register_engineering_resource(
        repository_identity="test://long-lived-work",
        location_ref=str(repository),
        authoritative_ref="refs/heads/main",
        context_references=(
            EngineeringContextReference(
                semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                repository_relative_path="AI_context.md",
            ),
        ),
    )
    return AdmissionFacts(postgres_database, service)


def _long_lived_draft(facts: AdmissionFacts, requirement: str = DOGFOOD_MOTIVE):
    submitted = facts.service.submit_work(
        requirement,
        mode=WorkMode.LONG_LIVED_STEERING,
    )
    return facts.service.refine_work(submitted.work_id)


def _counts(database: Database) -> tuple[int, int, int]:
    with database.engine.connect() as connection:
        return (
            connection.execute(select(func.count()).select_from(production_runs)).scalar_one(),
            connection.execute(
                select(func.count()).select_from(production_work_units)
            ).scalar_one(),
            connection.execute(
                select(func.count()).select_from(provider_execution_reports)
            ).scalar_one(),
        )


def _steering_counts(database: Database) -> tuple[int, int, int, int, int]:
    with database.engine.connect() as connection:
        return (
            connection.execute(select(func.count()).select_from(steering_plans)).scalar_one(),
            connection.execute(
                select(func.count()).select_from(steering_plan_revisions)
            ).scalar_one(),
            connection.execute(select(func.count()).select_from(steering_steps)).scalar_one(),
            connection.execute(
                select(func.count())
                .select_from(steering_steps)
                .where(steering_steps.c.state == "CURRENT")
            ).scalar_one(),
            connection.execute(
                select(func.count()).select_from(steering_decisions)
            ).scalar_one(),
        )


def test_steer_admit_01_02_03_04_06_08_12_15_dogfood_envelope_admission(
    admission_facts: AdmissionFacts,
) -> None:
    draft = _long_lived_draft(admission_facts)

    assert draft.mode is WorkMode.LONG_LIVED_STEERING
    assert draft.status is WorkStatus.AWAITING_APPROVAL
    assert draft.artifact_target is None
    assert draft.change_proposal is None
    assert draft.production_plan is None
    assert all(
        "exact authorized artifact target" not in item.reason.casefold()
        for item in admission_facts.service.list_attention(work_id=draft.work_id)
    )

    admitted = admission_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:dogfood",
        rationale="Admit the Motive, constraints, Resource, and bounded Work envelope",
    )
    assert admitted.status is WorkStatus.READY
    assert admitted.most_recent_meaningful_event == "STEERING_BOOTSTRAP_PENDING"
    assert admitted.what_happens_next == "Create the initial governed Steering Plan"
    assert admitted.engineering_scope is not None
    assert admitted.engineering_scope.condition.value == "ADMITTED"
    assert _counts(admission_facts.database) == (0, 0, 0)
    with admission_facts.database.unit_of_work() as unit_of_work:
        assert ProductStore(unit_of_work.session).runtime_binding(draft.work_id) is None

    plan = SteeringBootstrapService(admission_facts.database).bootstrap(draft.work_id)
    assert plan.current_step is not None
    assert plan.current_step.type is SteeringStepType.DESIGN
    assert _counts(admission_facts.database) == (0, 0, 0)
    projection = admission_facts.service.get_work(draft.work_id)
    assert projection.steering_enabled is True
    assert projection.current_steering_step_type == "DESIGN"
    assert projection.what_happens_next == "Steering evaluates the current governed Plan Step"


@pytest.mark.parametrize(
    ("requirement", "expected"),
    (
        (
            "Explore and clarify the bounded status feedback direction for Watt",
            SteeringStepType.REFINE,
        ),
        (
            "A material product direction requires human decision before implementation",
            SteeringStepType.HUMAN_DECISION,
        ),
    ),
)
def test_steer_admit_05_provider_neutral_initial_semantic_steps(
    admission_facts: AdmissionFacts,
    requirement: str,
    expected: SteeringStepType,
) -> None:
    draft = _long_lived_draft(admission_facts, requirement)
    admission_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:initial-plan",
    )
    plan = SteeringBootstrapService(admission_facts.database).bootstrap(draft.work_id)
    assert plan.current_step is not None
    assert plan.current_step.type is expected
    assert _counts(admission_facts.database) == (0, 0, 0)


def test_steer_admit_07_produce_forms_plan_1b_contract_and_one_cycle(
    admission_facts: AdmissionFacts,
) -> None:
    submitted = admission_facts.service.submit_work(
        "Produce the bounded progress status change in docs/progress-status.md",
        mode=WorkMode.LONG_LIVED_STEERING,
    )
    draft = admission_facts.service.refine_work(submitted.work_id)
    assert draft.production_plan is not None
    assert draft.production_plan.fit_classification.value == "ONE_PWU_FIT"
    admission_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:bounded-production",
    )
    assert _counts(admission_facts.database) == (0, 0, 0)
    plan = SteeringBootstrapService(admission_facts.database).bootstrap(draft.work_id)
    assert plan.current_step is not None
    assert plan.current_step.type is SteeringStepType.PRODUCE

    production = SteeringProductionService(admission_facts.database)
    request = production.materialize_request(draft.work_id)
    admission = production.admit_cycle(request)
    assert admission.binding is not None
    assert admission.attention_decision_id is None
    assert _counts(admission_facts.database) == (1, 1, 0)


def test_steer_admit_05_07_bounded_contract_forms_only_at_produce(
    admission_facts: AdmissionFacts,
) -> None:
    submitted = admission_facts.service.submit_work(
        "Improve the bounded execution-status feedback",
        mode=WorkMode.LONG_LIVED_STEERING,
    )
    draft = admission_facts.service.refine_work(
        submitted.work_id,
        WorkRefinementRequest(code_allowed_areas=("src/spg/web/**",)),
    )
    assert draft.artifact_target is None
    assert draft.change_proposal is not None
    assert draft.change_proposal.required_targets == ()
    assert draft.change_contract is None

    admission_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:bounded-area",
    )
    assert _counts(admission_facts.database) == (0, 0, 0)
    plan = SteeringBootstrapService(admission_facts.database).bootstrap(draft.work_id)
    assert plan.current_step is not None
    assert plan.current_step.type is SteeringStepType.PRODUCE

    production = SteeringProductionService(admission_facts.database)
    request = production.materialize_request(draft.work_id)
    assert request.artifact_targets == ()
    assert request.change_contract is not None
    assert request.change_contract.exact_targets == ()
    assert request.change_contract.allowed_areas == ("src/spg/web/**",)
    admission = production.admit_cycle(request)
    assert admission.binding is not None
    assert admission.attention_decision_id is None
    assert _counts(admission_facts.database) == (1, 1, 0)


def test_steer_admit_09_10_authority_expansion_stops_before_runtime(
    admission_facts: AdmissionFacts,
) -> None:
    submitted = admission_facts.service.submit_work(
        "Produce docs/admitted-boundary.md",
        mode=WorkMode.LONG_LIVED_STEERING,
    )
    draft = admission_facts.service.refine_work(submitted.work_id)
    admission_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:bounded-production",
    )
    SteeringBootstrapService(admission_facts.database).bootstrap(draft.work_id)
    production = SteeringProductionService(admission_facts.database)
    expected = production.materialize_request(draft.work_id)
    expanded = expected.model_copy(update={"repository_identity": "other://repository"})

    admission = production.admit_cycle(expanded)
    assert admission.binding is None
    assert admission.attention_decision_id is not None
    assert _counts(admission_facts.database) == (0, 0, 0)
    attention = admission_facts.service.list_attention(work_id=draft.work_id)
    assert len(attention) == 1
    assert attention[0].kind is AttentionKind.STEERING_DECISION_REQUIRED
    assert attention[0].steering_reason.value == "SCOPE_OR_AUTHORITY_EXPANSION"


def test_steer_admit_11_13_legacy_path_still_precreates_one_cycle(
    admission_facts: AdmissionFacts,
) -> None:
    submitted = admission_facts.service.submit_work("Produce docs/legacy-result.md")
    assert submitted.mode is WorkMode.IMMEDIATE_PRODUCTION
    draft = admission_facts.service.refine_work(submitted.work_id)
    assert draft.status is WorkStatus.AWAITING_APPROVAL
    approved = admission_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:legacy",
    )
    assert approved.steering_enabled is False
    assert _counts(admission_facts.database) == (1, 1, 0)


def test_steer_admit_16_real_http_approval_bootstraps_plan(
    admission_facts: AdmissionFacts,
) -> None:
    orchestrator = _RecordingOrchestrator()
    driver = _RecordingSteeringDriver(
        admission_facts.database,
        admission_facts.service,
        orchestrator,
    )
    application = create_http_application(
        database=admission_facts.database,
        work_service=admission_facts.service,
        orchestrator=orchestrator,
        steering_driver=driver,
    )
    with TestClient(application, raise_server_exceptions=False) as client:
        submitted = client.post(
            "/api/works",
            json={"requirement": DOGFOOD_MOTIVE, "mode": "LONG_LIVED_STEERING"},
        )
        assert submitted.status_code == 201
        work_id = submitted.json()["work_id"]
        refined = client.post(f"/api/works/{work_id}/refine", json={})
        assert refined.status_code == 200
        assert refined.json()["status"] == "AWAITING_APPROVAL"
        approved = client.post(
            f"/api/works/{work_id}/approve",
            json={"authority_identity": "human:http"},
        )
        assert approved.status_code == 200
        assert approved.json()["steering_enabled"] is True
        assert approved.json()["current_steering_step_type"] == "DESIGN"
        steering = client.get(f"/api/works/{work_id}/steering")
        assert steering.status_code == 200
        assert steering.json()["current_step"]["type"] == "DESIGN"
        assert _counts(admission_facts.database) == (0, 0, 0)


@pytest.mark.parametrize("approval_path", ("dedicated", "attention"))
def test_steer_act_01_02_03_04_06_09_10_16_all_admission_paths_auto_activate(
    admission_facts: AdmissionFacts,
    approval_path: str,
) -> None:
    orchestrator = _RecordingOrchestrator()
    driver = _RecordingSteeringDriver(
        admission_facts.database,
        admission_facts.service,
        orchestrator,
    )
    application = create_http_application(
        database=admission_facts.database,
        work_service=admission_facts.service,
        orchestrator=orchestrator,
        steering_driver=driver,
    )

    with TestClient(application, raise_server_exceptions=False) as client:
        submitted = client.post(
            "/api/works",
            json={"requirement": DOGFOOD_MOTIVE, "mode": "LONG_LIVED_STEERING"},
        )
        assert submitted.status_code == 201
        work_id = submitted.json()["work_id"]
        refined = client.post(f"/api/works/{work_id}/refine", json={})
        assert refined.status_code == 200
        assert refined.json()["status"] == "AWAITING_APPROVAL"

        if approval_path == "dedicated":
            approved = client.post(
                f"/api/works/{work_id}/approve",
                json={"authority_identity": "human:steer-act"},
            )
        else:
            attention = client.get(
                "/api/attention", params={"work_id": work_id}
            ).json()
            approval = next(
                item for item in attention if item["kind"] == "WORK_DRAFT_APPROVAL"
            )
            approved = client.post(
                f"/api/attention/{approval['attention_id']}/resolve",
                json={
                    "action": "APPROVE",
                    "authority_identity": "human:steer-act",
                },
            )

        assert approved.status_code == 200
        projection = admission_facts.service.get_work(UUID(work_id))
        assert projection.mode is WorkMode.LONG_LIVED_STEERING
        assert projection.status is WorkStatus.READY
        assert projection.engineering_scope is not None
        assert projection.engineering_scope.condition.value == "ADMITTED"
        assert projection.steering_enabled is True
        assert projection.current_steering_step_type == "DESIGN"
        assert driver.scheduled_work_ids == [UUID(work_id)]
        assert orchestrator.scheduled_work_ids == []
        assert _steering_counts(admission_facts.database) == (1, 1, 4, 1, 0)
        assert _counts(admission_facts.database) == (0, 0, 0)
        with admission_facts.database.unit_of_work() as unit_of_work:
            assert ProductStore(unit_of_work.session).runtime_binding(UUID(work_id)) is None

        steering = client.get(f"/api/works/{work_id}/steering")
        assert steering.status_code == 200
        assert steering.json()["active_revision_number"] == 1
        assert steering.json()["current_step"]["type"] == "DESIGN"
        observed = (_steering_counts(admission_facts.database), len(driver.scheduled_work_ids))
        for _ in range(3):
            assert client.get(f"/api/works/{work_id}").status_code == 200
            assert client.get(
                "/api/attention", params={"work_id": work_id}
            ).status_code == 200
            assert client.get(f"/api/works/{work_id}/steering").status_code == 200
        assert (
            _steering_counts(admission_facts.database),
            len(driver.scheduled_work_ids),
        ) == observed


def test_steer_act_07_08_14_repeated_activation_is_idempotent_and_single_active(
    admission_facts: AdmissionFacts,
) -> None:
    draft = _long_lived_draft(admission_facts)
    admission_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:idempotency",
    )
    orchestrator = _RecordingOrchestrator()
    driver = _RecordingSteeringDriver(
        admission_facts.database,
        admission_facts.service,
        orchestrator,
    )
    coordinator = WorkPostAdmissionService(
        admission_facts.service,
        SteeringBootstrapService(admission_facts.database),
        driver,
        orchestrator,
    )

    first = coordinator.activate(draft.work_id)
    first_counts = _steering_counts(admission_facts.database)
    second = coordinator.activate(draft.work_id)

    assert first.steering_enabled is True
    assert second.steering_enabled is True
    assert first_counts == (1, 1, 4, 1, 0)
    assert _steering_counts(admission_facts.database) == first_counts
    assert driver.scheduled_work_ids == [draft.work_id]
    assert orchestrator.scheduled_work_ids == []
    assert _counts(admission_facts.database) == (0, 0, 0)


def test_steer_act_11_12_startup_repairs_interrupted_admission_once(
    admission_facts: AdmissionFacts,
) -> None:
    draft = _long_lived_draft(admission_facts)
    pending = admission_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:interrupted-admission",
    )
    assert pending.status is WorkStatus.READY
    assert pending.steering_enabled is False
    assert _steering_counts(admission_facts.database) == (0, 0, 0, 0, 0)

    first_orchestrator = _RecordingOrchestrator()
    first_driver = _RecordingSteeringDriver(
        admission_facts.database,
        admission_facts.service,
        first_orchestrator,
    )
    first_application = create_http_application(
        database=admission_facts.database,
        work_service=admission_facts.service,
        orchestrator=first_orchestrator,
        steering_driver=first_driver,
    )
    with TestClient(first_application):
        assert first_driver.scheduled_work_ids == [draft.work_id]
        assert first_orchestrator.scheduled_work_ids == []
        assert _steering_counts(admission_facts.database) == (1, 1, 4, 1, 0)
        assert _counts(admission_facts.database) == (0, 0, 0)

    second_orchestrator = _RecordingOrchestrator()
    second_driver = _RecordingSteeringDriver(
        admission_facts.database,
        admission_facts.service,
        second_orchestrator,
    )
    second_application = create_http_application(
        database=admission_facts.database,
        work_service=admission_facts.service,
        orchestrator=second_orchestrator,
        steering_driver=second_driver,
    )
    with TestClient(second_application):
        assert second_driver.scheduled_work_ids == [draft.work_id]
        assert second_orchestrator.scheduled_work_ids == []
        assert _steering_counts(admission_facts.database) == (1, 1, 4, 1, 0)
        assert _counts(admission_facts.database) == (0, 0, 0)


def test_steer_act_13_activation_failures_never_fall_through_to_orch(
    admission_facts: AdmissionFacts,
) -> None:
    draft = _long_lived_draft(admission_facts)
    admission_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:failure-safety",
    )
    orchestrator = _RecordingOrchestrator()
    driver = _UnavailableSteeringDriver()
    failing_bootstrap = WorkPostAdmissionService(
        admission_facts.service,
        _FailingSteeringBootstrap(),  # type: ignore[arg-type]
        driver,  # type: ignore[arg-type]
        orchestrator,  # type: ignore[arg-type]
    )

    with pytest.raises(ProductInvariantViolation, match="bootstrap failure"):
        failing_bootstrap.activate(draft.work_id)
    assert orchestrator.scheduled_work_ids == []
    assert _steering_counts(admission_facts.database) == (0, 0, 0, 0, 0)
    assert _counts(admission_facts.database) == (0, 0, 0)

    unavailable_driver = WorkPostAdmissionService(
        admission_facts.service,
        SteeringBootstrapService(admission_facts.database),
        driver,  # type: ignore[arg-type]
        orchestrator,  # type: ignore[arg-type]
    )
    with pytest.raises(ProductInvariantViolation, match="scheduling is unavailable"):
        unavailable_driver.activate(draft.work_id)
    assert _steering_counts(admission_facts.database) == (1, 1, 4, 1, 0)
    assert orchestrator.scheduled_work_ids == []
    assert _counts(admission_facts.database) == (0, 0, 0)


def test_steer_act_05_15_immediate_production_still_uses_orch(
    admission_facts: AdmissionFacts,
) -> None:
    orchestrator = _RecordingOrchestrator()
    driver = _RecordingSteeringDriver(
        admission_facts.database,
        admission_facts.service,
        orchestrator,
    )
    application = create_http_application(
        database=admission_facts.database,
        work_service=admission_facts.service,
        orchestrator=orchestrator,
        steering_driver=driver,
    )
    with TestClient(application, raise_server_exceptions=False) as client:
        submitted = client.post(
            "/api/works",
            json={"requirement": "Produce docs/immediate-result.md"},
        )
        work_id = submitted.json()["work_id"]
        assert client.post(f"/api/works/{work_id}/refine", json={}).status_code == 200
        approved = client.post(
            f"/api/works/{work_id}/approve",
            json={"authority_identity": "human:immediate"},
        )

        assert approved.status_code == 200
        assert approved.json()["mode"] == "IMMEDIATE_PRODUCTION"
        assert approved.json()["steering_enabled"] is False
        assert orchestrator.scheduled_work_ids == [UUID(work_id)]
        assert driver.scheduled_work_ids == []
        assert _steering_counts(admission_facts.database) == (0, 0, 0, 0, 0)
        assert _counts(admission_facts.database) == (1, 1, 0)


def test_steer_admit_13_migration_preserves_historical_work_as_immediate(
    postgres_database: Database,
) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260905_20")
    historical_id = uuid4()
    with postgres_database.engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO product_works (
                id, goal_id, raw_user_requirement, refined_title,
                desired_outcome, constraints, tags, condition,
                created_at, updated_at
            ) VALUES (
                %(id)s, NULL, 'historical Work', NULL,
                NULL, '[]'::jsonb, '[]'::jsonb, 'DRAFT',
                now(), now()
            )
            """,
            {"id": historical_id},
        )
    command.upgrade(config, "head")
    with postgres_database.engine.connect() as connection:
        mode = connection.exec_driver_sql(
            "SELECT work_mode FROM product_works WHERE id = %(id)s",
            {"id": historical_id},
        ).scalar_one()
    assert mode == WorkMode.IMMEDIATE_PRODUCTION.value


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
