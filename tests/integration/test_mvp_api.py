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
from spg.application.bootstrap import bootstrap
from spg.application.runtime import RuntimeService
from spg.application.work import WorkApplicationService
from spg.config import Settings
from spg.domain.execution import ProviderReportedOutcome
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import EngineeringContextReference
from spg.domain.runtime import BootstrapRequest
from spg.domain.verification import VerificationResultValue
from spg.infrastructure.persistence import Database, product_tables, runtime_tables
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_schema import (
    completion_evaluations,
    execution_attempts,
    execution_dispatches,
    provider_execution_reports,
    repository_observations,
)
from spg.providers.deterministic_executor import (
    DeterministicExecutionSpecification,
    DeterministicFileOperation,
    DeterministicFileOperationType,
    DeterministicTestExecutor,
)
from spg.providers.deterministic_verifier import DeterministicVerificationProvider


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALL_TABLE_NAMES = {table.name for table in (*product_tables, *runtime_tables)}


@dataclass(frozen=True)
class ApiFacts:
    database: Database
    repository: Path
    workspace_root: Path
    service: WorkApplicationService
    client: TestClient


class _ManualOnlyOrchestrator:
    """Keep pre-ORCH API cases explicitly on the admitted fallback path."""

    def resume_safely_eligible_works(self) -> tuple[()]:
        return ()

    def schedule(self, _work_id: UUID) -> bool:
        return False

    def shutdown(self) -> None:
        return None


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
    repository = tmp_path / "governed-api-repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG API Test")
    _git(repository, "config", "user.email", "spg-api-test@example.invalid")
    (repository / "docs").mkdir()
    (repository / "AI_context.md").write_text("baseline context\n", encoding="utf-8")
    (repository / "docs" / "contract.md").write_text(
        "governed HTTP execution contract\n",
        encoding="utf-8",
    )
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    return repository


@pytest.fixture
def api_facts(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> Iterator[ApiFacts]:
    RuntimeService(postgres_database).bootstrap_trusted_baseline(
        BootstrapRequest(
            repository_path=git_repository,
            repository_identity="test://mvp-api-repository",
            repository_ref="refs/heads/main",
            authority_identity="architecture-lead:api-test",
            scope={"slice": "MVP-API-1"},
        )
    )
    workspace_root = tmp_path / "api-attempt-workspaces"
    service = WorkApplicationService(
        postgres_database,
        workspace_root=workspace_root,
    )
    service.register_engineering_resource(
        repository_identity="test://mvp-api-repository",
        location_ref=str(git_repository),
        authoritative_ref="refs/heads/main",
        context_references=(
            EngineeringContextReference(
                semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                repository_relative_path="AI_context.md",
            ),
            EngineeringContextReference(
                semantic_role=ContextSemanticRole.EXECUTION_CONTRACT,
                repository_relative_path="docs/contract.md",
            ),
        ),
    )
    client = TestClient(
        create_http_application(
            database=postgres_database,
            work_service=service,
            orchestrator=_ManualOnlyOrchestrator(),
        ),
        raise_server_exceptions=False,
    )
    with client:
        yield ApiFacts(
            database=postgres_database,
            repository=git_repository,
            workspace_root=workspace_root,
            service=service,
            client=client,
        )


def _submit_and_refine(
    client: TestClient,
    *,
    requirement: str = "Create the governed API product result",
    goal_id: str | None = None,
) -> dict:
    payload: dict[str, object] = {
        "requirement": requirement,
        "tags": ["api", "mvp"],
    }
    if goal_id is not None:
        payload["goal_id"] = goal_id
    submitted = client.post("/api/works", json=payload)
    assert submitted.status_code == 201
    work_id = submitted.json()["work_id"]
    refined = client.post(
        f"/api/works/{work_id}/refine",
        json={"expected_artifact_path": f"docs/api-work-{work_id}.md"},
    )
    assert refined.status_code == 200
    return refined.json()


def _service_with_deterministic_capabilities(
    facts: ApiFacts,
    work_id: UUID,
    *,
    produce_change: bool,
) -> tuple[WorkApplicationService, DeterministicTestExecutor]:
    with facts.database.unit_of_work() as unit_of_work:
        record = ProductStore(unit_of_work.session).work(work_id)
    assert record is not None
    assert record.expected_artifact_path is not None
    assert record.verification_expectation is not None
    operations = (
        (
            DeterministicFileOperation(
                operation=DeterministicFileOperationType.CREATE,
                repository_relative_path=record.expected_artifact_path,
                content="governed HTTP product result\n",
            ),
        )
        if produce_change
        else ()
    )
    executor = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=operations,
            reported_outcome=ProviderReportedOutcome.SUCCESS,
            summary="deterministic MVP-API-1 execution",
        )
    )
    verifier = DeterministicVerificationProvider(
        {record.verification_expectation: VerificationResultValue.PASS}
    )
    return (
        WorkApplicationService(
            facts.database,
            workspace_root=facts.workspace_root,
            executor=executor,
            verifier=verifier,
        ),
        executor,
    )


def _client_for_service(facts: ApiFacts, service: WorkApplicationService) -> TestClient:
    return TestClient(
        create_http_application(
            database=facts.database,
            work_service=service,
            orchestrator=_ManualOnlyOrchestrator(),
        ),
        raise_server_exceptions=False,
    )


def test_api_01_health_boots_without_provider_and_api_18_is_safe(
    api_facts: ApiFacts,
) -> None:
    response = api_facts.client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "service": "available",
        "database": "available",
        "application_initialized": True,
    }
    serialized = response.text.lower()
    assert "database_url" not in serialized
    assert "password" not in serialized
    assert "credential" not in serialized

    configured = create_http_application(
        bootstrap(
            Settings(
                database_url=api_facts.database.engine.url.render_as_string(
                    hide_password=False
                ),
                repository_path=api_facts.repository,
                workspace_root=api_facts.workspace_root,
            )
        )
    )
    with TestClient(configured, raise_server_exceptions=False) as client:
        assert client.get("/health").json()["application_initialized"] is True
    configured.state.database.dispose()


def test_api_02_goal_create_list_and_summary_get(api_facts: ApiFacts) -> None:
    created = api_facts.client.post(
        "/api/goals",
        json={"title": "MVP", "description": "Usable governed product"},
    )
    assert created.status_code == 201
    goal_id = created.json()["goal_id"]
    listed = api_facts.client.get("/api/goals")
    assert listed.status_code == 200
    assert [item["goal_id"] for item in listed.json()] == [goal_id]
    summary = api_facts.client.get(f"/api/goals/{goal_id}")
    assert summary.status_code == 200
    assert summary.json()["goal"]["title"] == "MVP"
    assert summary.json()["work_count"] == 0


def test_api_03_04_05_06_20_work_submission_projection_and_filters(
    api_facts: ApiFacts,
) -> None:
    goal = api_facts.client.post("/api/goals", json={"title": "MVP"}).json()
    first = api_facts.client.post(
        "/api/works",
        json={"requirement": "First independent Work", "tags": ["z", "api", "api"]},
    )
    second = api_facts.client.post(
        "/api/works",
        json={
            "requirement": "Second Goal Work",
            "goal_id": goal["goal_id"],
            "tags": ["goal"],
        },
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["goal_id"] is None
    assert first.json()["raw_user_requirement"] == "First independent Work"
    assert first.json()["constraints"] == []
    assert first.json()["tags"] == ["api", "z"]
    assert second.json()["goal_id"] == goal["goal_id"]
    forbidden = {
        "production_run_id",
        "plan_revision_id",
        "work_unit_id",
        "attempt_id",
        "provider_outcome",
        "database_url",
    }
    assert forbidden.isdisjoint(first.json())
    filtered = api_facts.client.get(
        "/api/works",
        params={"goal_id": goal["goal_id"], "status": "DRAFT"},
    )
    assert [item["work_id"] for item in filtered.json()] == [second.json()["work_id"]]
    assert api_facts.client.get(
        f"/api/works/{first.json()['work_id']}"
    ).json()["work_id"] == first.json()["work_id"]


def test_api_07_08_09_refinement_and_governed_admission(
    api_facts: ApiFacts,
) -> None:
    submitted = api_facts.client.post(
        "/api/works",
        json={"requirement": "Admit this Work"},
    ).json()
    early = api_facts.client.post(
        f"/api/works/{submitted['work_id']}/approve",
        json={"authority_identity": "human:api"},
    )
    assert early.status_code == 409
    assert early.json()["code"] == "HUMAN_APPROVAL_REQUIRED"

    refined = api_facts.client.post(
        f"/api/works/{submitted['work_id']}/refine",
        json={
            "title": "Governed API Work",
            "constraints": ["bounded"],
            "expected_artifact_path": "docs/governed-api-work.md",
        },
    )
    assert refined.status_code == 200
    assert refined.json()["status"] == "AWAITING_APPROVAL"
    assert refined.json()["raw_user_requirement"] == "Admit this Work"
    assert refined.json()["constraints"] == ["bounded"]
    assert len(refined.json()["engineering_scope"]["resources"]) == 1
    plan = refined.json()["production_plan"]
    assert plan["fit_classification"] == "ONE_PWU_FIT"
    assert plan["objective"] == refined.json()["desired_outcome"]
    assert [step["position"] for step in plan["ordered_steps"]] == list(
        range(1, len(plan["ordered_steps"]) + 1)
    )
    assert plan["artifact_targets"] == ["CREATE docs/governed-api-work.md"]
    assert plan["inherited_constraints"] == ["bounded"]
    assert plan["verification_approach"]
    approved = api_facts.client.post(
        f"/api/works/{submitted['work_id']}/approve",
        json={
            "authority_identity": "human:api",
            "rationale": "admit exact HTTP draft",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "READY"
    with api_facts.database.unit_of_work() as unit_of_work:
        binding = ProductStore(unit_of_work.session).runtime_binding(
            UUID(submitted["work_id"])
        )
    assert binding is not None


def test_code_draft_contract_is_visible_adjustable_and_admitted_over_http(
    api_facts: ApiFacts,
) -> None:
    submitted = api_facts.client.post(
        "/api/works",
        json={"requirement": "Modify Python source code and its unit test"},
    ).json()
    unresolved = api_facts.client.post(
        f"/api/works/{submitted['work_id']}/refine",
        json={},
    )
    assert unresolved.status_code == 200
    assert unresolved.json()["target_kind"] == "CODE_WORK"
    assert unresolved.json()["status"] == "NEEDS_REFINEMENT"
    assert unresolved.json()["artifact_target"] is None
    assert unresolved.json()["change_proposal"] is not None
    assert unresolved.json()["change_contract"] is None

    refined = api_facts.client.post(
        f"/api/works/{submitted['work_id']}/refine",
        json={
            "code_exact_targets": [
                "src/spg/example.py",
                "tests/test_example.py",
            ],
            "code_forbidden_areas": [".github/**"],
            "code_verification_obligations": [
                {"kind": "PATH_SCOPE"},
                {"kind": "GIT_DIFF_CHECK"},
                {"kind": "PYTHON_COMPILE"},
                {"kind": "PYTEST_TARGET", "target": "tests/test_example.py"},
                {"kind": "IMPORT_CHECK", "target": "spg.example"},
            ],
        },
    )
    assert refined.status_code == 200
    payload = refined.json()
    assert payload["status"] == "AWAITING_APPROVAL"
    assert payload["target_kind"] == "CODE_WORK"
    assert payload["artifact_target"] is None
    assert payload["production_plan"]["target_kind"] == "CODE_WORK"
    assert payload["change_contract"] is None
    assert payload["change_proposal"]["target_kind"] == "CODE_WORK"
    assert [item["path"] for item in payload["change_proposal"]["proposed_targets"]] == [
        "src/spg/example.py",
        "tests/test_example.py",
    ]
    assert payload["change_proposal"]["forbidden_areas"] == [".github/**"]
    assert payload["change_proposal"]["provenance"]["provider_identity"].startswith(
        "provider:repository-aware-change-proposal"
    )

    approved = api_facts.client.post(
        f"/api/works/{submitted['work_id']}/approve",
        json={"authority_identity": "human:code-api"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "READY"
    admitted = approved.json()["change_contract"]
    assert admitted["target_shape"] == "EXACT_TARGET_SET"
    assert admitted["source_proposal_id"] == payload["change_proposal"]["proposal_id"]
    assert (
        admitted["source_proposal_fingerprint"]
        == payload["change_proposal"]["proposal_fingerprint"]
    )


def test_intake_multilingual_constraint_persists_and_projects(
    api_facts: ApiFacts,
) -> None:
    requirement = (
        "把我们刚刚确立的 Production Orchestration Lite 设计原则整理成一份正式的"
        "产品/架构说明文档，放到现有文档体系中合适的位置。"
        "重点说明 Human-in-the-loop 不等于 Human-as-the-loop、Watt 的自动推进边界、"
        "Human Attention 的职责，以及 MVP 当前方案和未来演进方向的区别。"
        "尽量复用现有已经确定的设计，不要发散新的能力。"
    )
    expected = ["尽量复用现有已经确定的设计，不要发散新的能力"]
    submitted = api_facts.client.post(
        "/api/works",
        json={"requirement": requirement},
    )
    assert submitted.status_code == 201
    work_id = submitted.json()["work_id"]

    refined = api_facts.client.post(
        f"/api/works/{work_id}/refine",
        json={},
    )
    assert refined.status_code == 200
    assert refined.json()["status"] == "AWAITING_APPROVAL"
    assert refined.json()["constraints"] == expected

    with api_facts.database.unit_of_work() as unit_of_work:
        persisted = ProductStore(unit_of_work.session).work(UUID(work_id))
    assert persisted is not None
    assert persisted.constraints == tuple(expected)

    projected = api_facts.client.get(f"/api/works/{work_id}")
    assert projected.status_code == 200
    assert projected.json()["constraints"] == expected


def test_needs_refinement_reject_and_request_refinement_routes(
    api_facts: ApiFacts,
) -> None:
    broad = _submit_and_refine(
        api_facts.client,
        requirement="Rewrite the whole entire platform and all systems",
    )
    assert broad["status"] == "NEEDS_REFINEMENT"
    blocked_approval = api_facts.client.post(
        f"/api/works/{broad['work_id']}/approve",
        json={"authority_identity": "human:api"},
    )
    assert blocked_approval.status_code == 409
    assert blocked_approval.json()["code"] == "NEEDS_REFINEMENT"

    rejectable = _submit_and_refine(api_facts.client)
    rejected = api_facts.client.post(
        f"/api/works/{rejectable['work_id']}/reject",
        json={"authority_identity": "human:api"},
    )
    assert rejected.json()["status"] == "BLOCKED"
    refinable = _submit_and_refine(api_facts.client, requirement="Refine this request")
    requested = api_facts.client.post(
        f"/api/works/{refinable['work_id']}/request-refinement",
        json={"authority_identity": "human:api"},
    )
    assert requested.json()["status"] == "NEEDS_REFINEMENT"


def test_api_10_11_12_15_19_bounded_advance_and_truthful_observation(
    api_facts: ApiFacts,
) -> None:
    work = _submit_and_refine(api_facts.client, requirement="Observe no production change")
    api_facts.client.post(
        f"/api/works/{work['work_id']}/approve",
        json={"authority_identity": "human:api"},
    )
    service, executor = _service_with_deterministic_capabilities(
        api_facts,
        UUID(work["work_id"]),
        produce_change=False,
    )
    with _client_for_service(api_facts, service) as client:
        first = client.post(f"/api/works/{work['work_id']}/advance")
        assert first.status_code == 200
        with api_facts.database.engine.connect() as connection:
            assert connection.scalar(select(func.count()).select_from(execution_attempts)) == 1
            assert connection.scalar(select(func.count()).select_from(execution_dispatches)) == 0
        client.post(f"/api/works/{work['work_id']}/advance")
        blocked = client.post(f"/api/works/{work['work_id']}/advance")
        assert blocked.json()["status"] == "BLOCKED"
        assert blocked.json()["status"] != "COMPLETED"
        with api_facts.database.engine.connect() as connection:
            assert connection.scalar(select(func.count()).select_from(provider_execution_reports)) == 1
            assert connection.scalar(select(func.count()).select_from(repository_observations)) == 1
            assert connection.scalar(select(func.count()).select_from(completion_evaluations)) == 0
        repeated = client.post(f"/api/works/{work['work_id']}/advance")
        assert repeated.json()["status"] == "BLOCKED"
    assert executor.dispatch_count == 1


def test_api_13_14_16_deterministic_http_flow_attention_and_result(
    api_facts: ApiFacts,
) -> None:
    goal = api_facts.client.post("/api/goals", json={"title": "MVP"}).json()
    work = _submit_and_refine(api_facts.client, goal_id=goal["goal_id"])
    service, executor = _service_with_deterministic_capabilities(
        api_facts,
        UUID(work["work_id"]),
        produce_change=True,
    )
    with _client_for_service(api_facts, service) as client:
        approved = client.post(
            f"/api/works/{work['work_id']}/approve",
            json={"authority_identity": "human:api"},
        )
        assert approved.json()["status"] == "READY"
        candidate_attention = None
        for _ in range(12):
            client.post(f"/api/works/{work['work_id']}/advance")
            attention = client.get(
                "/api/attention",
                params={"work_id": work["work_id"]},
            ).json()
            if attention and attention[0]["kind"] == "CANDIDATE_AUTHORIZATION":
                candidate_attention = attention[0]
                break
        assert candidate_attention is not None
        assert candidate_attention["available_actions"] == ["AUTHORIZE"]
        resolved = client.post(
            f"/api/attention/{candidate_attention['attention_id']}/resolve",
            json={
                "action": "AUTHORIZE",
                "authority_identity": "human:api",
                "rationale": "authorize exact Candidate",
            },
        )
        assert resolved.status_code == 200
        projection = resolved.json()
        for _ in range(4):
            projection = client.post(
                f"/api/works/{work['work_id']}/advance"
            ).json()
            if projection["status"] == "COMPLETED":
                break
        assert projection["status"] == "COMPLETED"
        result = client.get(f"/api/works/{work['work_id']}/result")
        assert result.status_code == 200
        assert result.json()["trusted_result"] is True
        assert result.json()["produced_artifacts"]
        assert result.json()["verification_summary"]
        serialized = result.text.lower()
        assert "database_url" not in serialized
        assert "api_key" not in serialized
    assert executor.dispatch_count == 1


def test_orch_01_02_05_08_through_15_deterministic_automatic_flow(
    api_facts: ApiFacts,
) -> None:
    goal = api_facts.client.post("/api/goals", json={"title": "MVP ORCH"}).json()
    work = _submit_and_refine(api_facts.client, goal_id=goal["goal_id"])
    work_id = UUID(work["work_id"])
    service, executor = _service_with_deterministic_capabilities(
        api_facts,
        work_id,
        produce_change=True,
    )
    application = create_http_application(
        database=api_facts.database,
        work_service=service,
    )
    manual_advance_calls = 0

    @application.middleware("http")
    async def count_manual_advance(request, call_next):
        nonlocal manual_advance_calls
        if request.url.path == f"/api/works/{work_id}/advance":
            manual_advance_calls += 1
        return await call_next(request)

    with TestClient(application, raise_server_exceptions=False) as client:
        approved = client.post(
            f"/api/works/{work_id}/approve",
            json={"authority_identity": "human:orch"},
        )
        assert approved.status_code == 200
        # The Human request returns the persisted admission snapshot; Provider
        # duration belongs to the in-process orchestration thread.
        assert approved.json()["status"] == "READY"

        orchestrator = application.state.production_orchestrator
        assert orchestrator.wait_until_idle(work_id, 60)
        candidate_work = client.get(f"/api/works/{work_id}").json()
        assert candidate_work["status"] == "NEEDS_ATTENTION"
        attention = client.get(
            "/api/attention",
            params={"work_id": str(work_id)},
        ).json()
        assert len(attention) == 1
        assert attention[0]["kind"] == "CANDIDATE_AUTHORIZATION"
        assert attention[0]["available_actions"] == ["AUTHORIZE"]
        with api_facts.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            binding = store.runtime_binding(work_id)
            assert binding is not None
            before_authority = store.runtime_summary(binding)
        assert before_authority.candidate_id is not None
        assert before_authority.authorization_id is None

        authorized = client.post(
            f"/api/attention/{attention[0]['attention_id']}/resolve",
            json={
                "action": "AUTHORIZE",
                "authority_identity": "human:orch",
                "rationale": "authorize the exact sealed Candidate",
            },
        )
        assert authorized.status_code == 200
        assert authorized.json()["status"] == "RUNNING"
        assert orchestrator.wait_until_idle(work_id, 60)

        completed = client.get(f"/api/works/{work_id}").json()
        result = client.get(f"/api/works/{work_id}/result").json()
        assert completed["status"] == "COMPLETED"
        assert result["trusted_result"] is True
        assert result["produced_artifacts"]
        assert result["verification_summary"]

    assert manual_advance_calls == 0
    assert executor.dispatch_count == 1


def test_api_17_unknown_resources_and_invalid_request_are_stable(
    api_facts: ApiFacts,
) -> None:
    missing = uuid4()
    for path in (
        f"/api/goals/{missing}",
        f"/api/works/{missing}",
        f"/api/works/{missing}/result",
    ):
        response = api_facts.client.get(path)
        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"
    attention = api_facts.client.post(
        f"/api/attention/{missing}/resolve",
        json={"action": "APPROVE", "authority_identity": "human:api"},
    )
    assert attention.status_code == 404
    assert attention.json()["code"] == "NOT_FOUND"
    invalid = api_facts.client.post("/api/works", json={"requirement": ""})
    assert invalid.status_code == 422
    assert invalid.json() == {
        "code": "INVALID_REQUEST",
        "message": "Request validation failed",
    }


def test_work_result_before_execution_does_not_invent_evidence(
    api_facts: ApiFacts,
) -> None:
    work = api_facts.client.post(
        "/api/works",
        json={"requirement": "No execution yet"},
    ).json()
    result = api_facts.client.get(f"/api/works/{work['work_id']}/result")
    assert result.status_code == 200
    assert result.json()["produced_artifacts"] == []
    assert result.json()["verification_summary"] == []
    assert result.json()["repository_state"] is None
    assert result.json()["trusted_result"] is False
    activation = result.json()["runtime_activation"]
    assert activation["state"] == "ACTIVATION_BLOCKED"
    assert activation["active_application_revision"] is None
    assert activation["current_trusted_baseline_revision"] == _git(
        api_facts.repository,
        "rev-parse",
        "HEAD",
    )


def test_ui_functional_public_http_smoke_without_provider(api_facts: ApiFacts) -> None:
    client = api_facts.client
    assert client.get("/app").status_code == 200
    for asset in ("styles.css", "state.js", "app.js"):
        assert client.get(f"/assets/{asset}").status_code == 200

    goal = client.post("/api/goals", json={"title": "MVP"})
    assert goal.status_code == 201
    goal_id = goal.json()["goal_id"]

    first = client.post(
        "/api/works",
        json={
            "requirement": "Deliver the first bounded UI smoke Work",
            "goal_id": goal_id,
            "tags": ["mvp", "ui"],
        },
    )
    assert first.status_code == 201
    first_id = first.json()["work_id"]
    refined = client.post(
        f"/api/works/{first_id}/refine",
        json={"expected_artifact_path": "docs/ui-smoke-work.md"},
    )
    assert refined.status_code == 200
    assert refined.json()["status"] == "AWAITING_APPROVAL"
    attention = client.get("/api/attention", params={"work_id": first_id})
    assert attention.status_code == 200
    assert attention.json()[0]["available_actions"] == [
        "APPROVE",
        "REJECT",
        "REQUEST_REFINEMENT",
    ]
    approved = client.post(
        f"/api/attention/{attention.json()[0]['attention_id']}/resolve",
        json={
            "action": "APPROVE",
            "authority_identity": "human:ui-smoke",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "READY"

    advanced = client.post(f"/api/works/{first_id}/advance")
    assert advanced.status_code == 200
    assert advanced.json()["status"] == "NEEDS_ATTENTION"
    assert client.get("/api/attention", params={"work_id": first_id}).status_code == 200
    assert client.get(f"/api/works/{first_id}/result").status_code == 200

    second = client.post(
        "/api/works",
        json={"requirement": "Keep a second independent Work accessible"},
    )
    assert second.status_code == 201
    assert second.json()["goal_id"] is None
    assert client.get(f"/api/works/{first_id}").status_code == 200
    assert client.get(f"/api/works/{second.json()['work_id']}").status_code == 200


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
