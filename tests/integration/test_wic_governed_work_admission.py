from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
import os
from pathlib import Path
import subprocess
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, inspect, select, text

from spg.api import create_http_application
from spg.application.interaction import WorkInteractionService
from spg.application.runtime import RuntimeService
from spg.application.steering_decision import PlanFrameAssembler
from spg.application.steering_bootstrap import SteeringBootstrapService
from spg.application.work import WorkApplicationService
from spg.domain.interaction import (
    InteractionAssessmentCandidate,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InterpretationMeaning,
    InterpretationMeaningKind,
    WorkAdmissionReadinessStatus,
    WorkFocusClassification,
    WorkImpactDisposition,
    WorkRevisionAdmissionStatus,
)
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import (
    AttentionAction,
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
    ) -> None:
        self.focus = focus
        self.impact = impact
        self.context_fact = context_fact
        self.constraint = constraint
        self.motive = motive
        self.desired_outcome = desired_outcome
        self.meaning = meaning

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
            current_requests=revision.requests,
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


def test_wic3_active_cycle_remains_bound_to_old_revision_and_input_is_not_injected(
    postgres_database: Database,
    services,
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
            impact=WorkImpactDisposition.CURRENT_RESULT_MAY_BE_INSUFFICIENT,
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
    assert pending.active_cycle_impact_disposition is (
        WorkImpactDisposition.CURRENT_RESULT_MAY_BE_INSUFFICIENT
    )

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


def _git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *args),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
