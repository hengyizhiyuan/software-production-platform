from collections.abc import Iterator
from datetime import UTC, datetime
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from spg.application.runtime import RuntimeService
from spg.application.steering import SteeringApplicationService
from spg.application.work import WorkApplicationService
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import EngineeringContextReference, WorkRefinementRequest
from spg.domain.runtime import BootstrapRequest
from spg.domain.steering import (
    AdmitSteeringDecisionRequest,
    CreateSteeringPlanRequest,
    ElaborateSteeringStepRequest,
    RealityReference,
    RealityReferenceKind,
    ReviseSteeringPlanRequest,
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


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALL_TABLE_NAMES = {table.name for table in (*product_tables, *runtime_tables)}
STEERING_TABLE_NAMES = {
    "steering_plans",
    "steering_plan_revisions",
    "steering_steps",
    "steering_decisions",
    "steering_history_events",
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

    decision_refs = (baseline_ref, work_ref)
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
