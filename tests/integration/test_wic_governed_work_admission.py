from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
import subprocess
from uuid import UUID

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, inspect, select, text

from spg.api import create_http_application
from spg.application.interaction import WorkInteractionService
from spg.application.runtime import RuntimeService
from spg.application.steering_bootstrap import SteeringBootstrapService
from spg.application.work import WorkApplicationService
from spg.domain.interaction import (
    InteractionAssessmentCandidate,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    WorkAdmissionReadinessStatus,
)
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import EngineeringContextReference, WorkMode, WorkStatus
from spg.domain.runtime import BootstrapRequest
from spg.domain.runtime_activation import RuntimeActivationProjection, RuntimeActivationState
from spg.domain.steering import RealityReferenceKind, SteeringStepType
from spg.infrastructure.persistence import Database, product_tables, runtime_tables
from spg.infrastructure.persistence.product_schema import (
    engineering_resource_bindings,
    engineering_scopes,
    interaction_records,
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
    production_admissibility_records,
    production_runs,
    production_work_units,
    proposed_repository_snapshots,
    provider_execution_reports,
    repository_integration_effects,
    repository_observations,
    runtime_commits,
)
from spg.infrastructure.persistence.steering_schema import steering_plans


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
        raise AssertionError("projection is not needed by this test")

    def shutdown(self) -> None:
        return None


class _NoopOrchestrator:
    def schedule(self, _work_id: UUID) -> bool:
        raise AssertionError("WIC long-lived admission must not schedule ORCH")

    def resume_safely_eligible_works(self) -> tuple[()]:
        return ()

    def shutdown(self) -> None:
        return None


class _RuntimeActivation:
    def project(self) -> RuntimeActivationProjection:
        return RuntimeActivationProjection(
            state=RuntimeActivationState.ACTIVE_AT_TRUSTED_BASELINE,
            active_application_revision="test",
            current_trusted_baseline_revision="test",
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
            repository_identity="test://wic-admission",
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
        repository_identity="test://wic-admission",
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


def _admit(work: WorkApplicationService, ready):
    return work.admit_interaction_work(
        ready.interaction.id,
        assessment_id=ready.latest_assessment.id,
        basis_fingerprint=ready.latest_assessment.basis_fingerprint,
        authority_identity="human:governor",
        rationale="Admit the reviewed Shared Understanding.",
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
    assert revision.schema_version == "wic-work-reality-v1"
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
    for table in PRODUCTION_TABLES:
        assert _count(postgres_database, table) == 0, table.name

    reconstructed = SteeringBootstrapService(postgres_database).bootstrap(
        admitted.work_id
    )
    assert reconstructed.steering_plan_id == plan.steering_plan_id
    assert _count(postgres_database, steering_plans) == 1


def test_admission_api_requires_human_action_and_preserves_same_interaction(
    postgres_database: Database,
    services,
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
            runtime_activation=_RuntimeActivation(),
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
        assert _count(postgres_database, product_works) == 1
        assert _count(postgres_database, steering_plans) == 1
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
        "schema_version",
    } <= columns


def _git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *args),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
