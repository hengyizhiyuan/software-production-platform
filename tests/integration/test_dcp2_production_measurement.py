from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, insert, select, update

from spg.application.measurement import (
    MeasurementSubjectNotFound,
    ProductionMeasurementService,
)
from spg.application.product_assets import ProductAssetService
from spg.domain.measurement import (
    MeasurementAvailability,
    MeasurementDerivation,
    ProductionMeasurementKind,
    ProductionMeasurementScope,
)
from spg.domain.planning import (
    OnePwuFitClassification,
    PlannedArtifactOperation,
    ProductionPlanArtifactTarget,
    ProductionPlanProposal,
    ProductionPlanStep,
)
from spg.domain.runtime import (
    ArtifactContract,
    ArtifactOperation,
    CompletionContract,
)
from spg.infrastructure.persistence import (
    Database,
    product_tables,
    runtime_tables,
)
from spg.infrastructure.persistence.product_schema import (
    engineering_resource_bindings,
    engineering_resources,
    engineering_scopes,
    product_works,
    work_runtime_bindings,
)
from spg.infrastructure.persistence.runtime_schema import (
    baseline_candidates,
    completion_evaluations,
    context_packages,
    execution_attempts,
    execution_dispatches,
    governance_records,
    human_authorizations,
    plan_revisions,
    production_admissibility_records,
    production_runs,
    production_snapshots,
    production_work_units,
    proposed_repository_snapshots,
    provider_execution_reports,
    repository_integration_effects,
    repository_observations,
    runtime_commits,
    verification_records,
)
from spg.infrastructure.persistence.steering_schema import (
    steering_decisions,
    steering_plan_revisions,
    steering_plans,
    steering_steps,
)


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALL_TABLE_NAMES = {table.name for table in (*product_tables, *runtime_tables)}


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


def test_dcp2_reconstructs_truthful_measurement_sample_without_mutation(
    postgres_database: Database,
) -> None:
    ids = _seed_measurement_reality(postgres_database)
    service = ProductionMeasurementService(postgres_database)
    before_counts = _table_counts(postgres_database)

    first = service.sample_for_work_unit(ids["work_unit"])
    second = service.sample_for_work_unit(ids["work_unit"])

    assert first == second
    assert first.task_shape.snapshot_id == second.task_shape.snapshot_id
    assert first.task_shape.basis_fingerprint == second.task_shape.basis_fingerprint
    assert first.task_shape.captured_at == ids["pwu_created_at"]
    assert first.task_shape.work_id == ids["work"]
    assert first.task_shape.production_plan_revision_id == ids["plan_revision"]
    assert first.task_shape.work_unit_id == ids["work_unit"]
    assert first.task_shape.resource_id == ids["resource"]
    assert first.task_shape.source_baseline_id == ids["baseline"]
    assert first.task_shape.repository_identity == "test://dcp2-measurement"
    assert first.task_shape.target_path_count == 1
    assert first.task_shape.create_count == 1
    assert first.task_shape.update_count == 0
    assert first.task_shape.verification_obligation_count == 1
    assert first.task_shape.ordered_planning_step_count == 2
    assert first.task_shape.context_reference_count is None
    assert first.task_shape.executor_profile_identity is None

    by_scope = {measurement.scope: measurement for measurement in first.measurements}
    machine = by_scope[ProductionMeasurementScope.AGGREGATE_PROVIDER_EXECUTION]
    assert machine.duration_microseconds == 7_000_000
    assert machine.internal_turn_count == 2
    assert machine.self_refine_occurred is True
    assert machine.attempt_id == ids["attempt"]
    assert machine.derivation is MeasurementDerivation.DERIVED_INTERVAL

    verification_total = by_scope[ProductionMeasurementScope.PWU_VERIFICATION_TOTAL]
    assert verification_total.availability is MeasurementAvailability.UNAVAILABLE
    assert verification_total.duration_microseconds is None
    assert "no authoritative aggregate" in verification_total.unavailable_reason
    verification_item = by_scope[ProductionMeasurementScope.VERIFICATION_OBLIGATION]
    assert verification_item.duration_microseconds == 2_500_000
    assert verification_item.derivation is MeasurementDerivation.OBSERVED_DURATION
    assert verification_item.observed_start_at is None
    assert verification_item.observed_end_at is None

    human = by_scope[ProductionMeasurementScope.CANDIDATE_AUTHORIZATION_WAIT]
    assert human.duration_microseconds == 30_000_000
    integration = by_scope[ProductionMeasurementScope.INTEGRATION_CONVERGENCE]
    assert integration.duration_microseconds == 4_000_000
    total = by_scope[ProductionMeasurementScope.LONG_LIVED_WORK_CYCLE]
    assert total.duration_microseconds == 100_000_000
    assert total.kind is ProductionMeasurementKind.TOTAL_STEERING_CYCLE

    assert _table_counts(postgres_database) == before_counts


def test_dcp2_snapshot_stays_stable_after_execution_state_changes(
    postgres_database: Database,
) -> None:
    ids = _seed_measurement_reality(postgres_database)
    service = ProductionMeasurementService(postgres_database)
    before = service.task_shape_snapshot(ids["work_unit"])

    with postgres_database.engine.begin() as connection:
        connection.execute(
            update(production_work_units)
            .where(production_work_units.c.id == ids["work_unit"])
            .values(condition="SATISFIED", version=9, current_execution_generation=4)
        )

    after = service.task_shape_snapshot(ids["work_unit"])
    assert after == before


def test_dcp2_query_failure_cannot_create_authority_or_integration(
    postgres_database: Database,
) -> None:
    _seed_measurement_reality(postgres_database)
    service = ProductionMeasurementService(postgres_database)
    before_authorizations = _count(postgres_database, human_authorizations)
    before_effects = _count(postgres_database, repository_integration_effects)

    with pytest.raises(MeasurementSubjectNotFound):
        service.machine_execution_measurement(uuid4())

    assert _count(postgres_database, human_authorizations) == before_authorizations
    assert _count(postgres_database, repository_integration_effects) == before_effects


def test_p1_q2_parallel_fan_in_economics_and_candidate_lineage(
    postgres_database: Database,
) -> None:
    ids = _seed_measurement_reality(postgres_database)
    b, join, b_attempt, join_attempt, b_dispatch, join_dispatch = (uuid4() for _ in range(6))
    start = datetime(2026, 9, 6, 9, 0, tzinfo=UTC)
    graph = {"planning_rationale": "Parallel implementation followed by an explicit join",
             "nodes": [
        {"node_id": name, "kind": kind, "objective": name,
         "dependency_ids": dependencies, "responsibility_boundary": name,
         "acceptance_criteria": ["verified"]}
        for name, kind, dependencies in (("A", "PWU", []), ("B", "PWU", []),
                                         ("J", "JOIN", ["A", "B"]))
    ]}
    with postgres_database.engine.begin() as connection:
        contract = connection.execute(select(production_work_units.c.completion_contract).where(
            production_work_units.c.id == ids["work_unit"])).scalar_one()
        dispatch = connection.execute(select(execution_dispatches).where(
            execution_dispatches.c.id == ids["dispatch"])).mappings().one()
        connection.execute(update(plan_revisions).where(plan_revisions.c.id == ids["plan_revision"])
                           .values(graph=graph))
        connection.execute(update(production_work_units).where(
            production_work_units.c.id == ids["work_unit"]).values(node_id="A"))
        connection.execute(update(provider_execution_reports).where(
            provider_execution_reports.c.id == ids["report"]).values(
                started_at=start, finished_at=start + timedelta(seconds=60),
                metadata={"token_usage": {"input_tokens": 5, "output_tokens": 5,
                                          "total_tokens": 10}}))
        for unit_id, attempt_id, dispatch_id, node_id, offset, duration in (
            (b, b_attempt, b_dispatch, "B", 0, 60),
            (join, join_attempt, join_dispatch, "J", 60, 40),
        ):
            connection.execute(insert(production_work_units).values(
                id=unit_id, production_run_id=ids["run"],
                plan_revision_id=ids["plan_revision"], source_baseline_id=ids["baseline"],
                node_id=node_id, objective=node_id, completion_contract=contract,
                condition="SATISFIED", version=1, current_execution_generation=1,
                created_at=start + timedelta(seconds=offset)))
            connection.execute(insert(execution_attempts).values(
                id=attempt_id, work_unit_id=unit_id, generation=1,
                plan_revision_id=ids["plan_revision"], source_baseline_id=ids["baseline"],
                condition="CREATED", created_at=start + timedelta(seconds=offset)))
            connection.execute(insert(execution_dispatches).values(
                id=dispatch_id, attempt_id=attempt_id, generation=1,
                context_package_id=ids["context"], source_baseline_id=ids["baseline"],
                executor_binding=dispatch["executor_binding"],
                workspace_identity=f"workspace:{node_id}", workspace_path=f"/tmp/{node_id}",
                repository_identity=dispatch["repository_identity"],
                repository_path=dispatch["repository_path"],
                source_revision=dispatch["source_revision"],
                authoritative_ref_revision=dispatch["authoritative_ref_revision"],
                dispatched_at=start + timedelta(seconds=offset)))
            connection.execute(insert(provider_execution_reports).values(
                id=uuid4(), dispatch_id=dispatch_id, attempt_id=attempt_id, generation=1,
                executor_binding=dispatch["executor_binding"],
                provider_reference="provider:test:dcp2", outcome="SUCCESS",
                started_at=start + timedelta(seconds=offset),
                finished_at=start + timedelta(seconds=offset + duration),
                metadata={"token_usage": {"input_tokens": 10, "output_tokens": 10,
                                          "total_tokens": 20}},
                recorded_at=start + timedelta(seconds=offset + duration)))
        connection.execute(update(baseline_candidates).where(
            baseline_candidates.c.id == ids["candidate"]).values(
                satisfied_work_unit_ids=[str(ids["work_unit"]), str(b), str(join)]))
    measurement = ProductionMeasurementService(postgres_database)
    assert measurement.task_shape_snapshot(b).work_unit_id == b
    assert measurement.human_wait_measurement(ids["candidate"]).work_unit_id is None
    facts = measurement.graph_economics(ids["work"])
    assert facts["pwu_count"] == 3
    assert facts["join_count"] == 1
    assert facts["execution_seconds"] == 160
    assert facts["wall_elapsed_seconds"] == 100
    assert facts["critical_path_seconds"] == 100
    assert facts["parallelism_effect_seconds"] == 60
    assert facts["token_usage"]["total_tokens"] == 50
    assert facts["observed_provider_spend"]["status"] == "UNREPORTED"
    assert facts["observed_provider_spend"]["amount"] is None
    # A failed B attempt followed by one recovered generation must remain
    # attributable to B, including the extra runtime and partial cost.
    recovered_attempt, recovered_dispatch = uuid4(), uuid4()
    with postgres_database.engine.begin() as connection:
        connection.execute(update(provider_execution_reports).where(
            provider_execution_reports.c.attempt_id == b_attempt).values(outcome="FAILED"))
        connection.execute(update(provider_execution_reports).where(
            provider_execution_reports.c.attempt_id == join_attempt).values(
                started_at=start + timedelta(seconds=90),
                finished_at=start + timedelta(seconds=130)))
        connection.execute(update(production_work_units).where(
            production_work_units.c.id == b).values(current_execution_generation=2))
        connection.execute(insert(execution_attempts).values(
            id=recovered_attempt, work_unit_id=b, generation=2,
            plan_revision_id=ids["plan_revision"], source_baseline_id=ids["baseline"],
            condition="CREATED", retry_of=b_attempt,
            created_at=start + timedelta(seconds=60)))
        connection.execute(insert(execution_dispatches).values(
            id=recovered_dispatch, attempt_id=recovered_attempt, generation=2,
            context_package_id=ids["context"], source_baseline_id=ids["baseline"],
            executor_binding=dispatch["executor_binding"],
            workspace_identity="workspace:B:recovery", workspace_path="/tmp/B-recovery",
            repository_identity=dispatch["repository_identity"],
            repository_path=dispatch["repository_path"],
            source_revision=dispatch["source_revision"],
            authoritative_ref_revision=dispatch["authoritative_ref_revision"],
            dispatched_at=start + timedelta(seconds=60)))
        connection.execute(insert(provider_execution_reports).values(
            id=uuid4(), dispatch_id=recovered_dispatch, attempt_id=recovered_attempt,
            generation=2, executor_binding=dispatch["executor_binding"],
            provider_reference="provider:test:dcp2", outcome="SUCCESS",
            started_at=start + timedelta(seconds=60),
            finished_at=start + timedelta(seconds=90),
            metadata={"token_usage": {"input_tokens": 3, "output_tokens": 3,
                                      "total_tokens": 6},
                      "provider_spend": {"amount": 0.5, "currency": "USD"}},
            recorded_at=start + timedelta(seconds=90)))
    recovered = measurement.graph_economics(ids["work"])
    assert recovered["pwu_count"] == 3
    assert recovered["retried_pwu_count"] == 1
    assert recovered["execution_seconds"] == 190
    assert recovered["wall_elapsed_seconds"] == 130
    assert recovered["critical_path_seconds"] == 130
    assert recovered["token_usage"]["total_tokens"] == 56
    assert recovered["observed_provider_spend"]["status"] == "PARTIAL"
    assert recovered["observed_provider_spend"]["by_currency"] == {"USD": 0.5}
    assert recovered["observed_provider_spend"]["unreported_attempt_count"] == 3


def test_p1_q1_product_current_source_advances_from_authorized_runtime_commit(
    postgres_database: Database,
) -> None:
    ids = _seed_measurement_reality(postgres_database)
    products = ProductAssetService(postgres_database)
    product = products.create("human:owner", "Measured Finance Product")
    product_id = UUID(product["id"])
    products.bind_work(product_id, ids["work"], "human:owner")
    products.attach_asset(product_id, "human:owner", kind="REPOSITORY",
        reference="test://dcp2-measurement", resource_id=ids["resource"],
        metadata={"revision": "a" * 40, "repository_ref": "refs/heads/main"})
    new_baseline = uuid4()
    with postgres_database.engine.begin() as connection:
        connection.execute(insert(production_snapshots).values(
            id=new_baseline, condition="TRUSTED",
            repository_identity="test://dcp2-measurement",
            repository_ref="refs/heads/main", repository_revision="b" * 40,
            source_baseline_id=ids["baseline"], created_at=datetime.now(UTC)))
        connection.execute(insert(runtime_commits).values(
            id=uuid4(), candidate_id=ids["candidate"], candidate_fingerprint="c" * 64,
            human_authorization_id=ids["authorization"],
            repository_integration_effect_id=ids["effect"],
            source_baseline_id=ids["baseline"], new_baseline_id=new_baseline,
            production_run_id=ids["run"], plan_revision_id=ids["plan_revision"],
            repository_identity="test://dcp2-measurement",
            target_authoritative_ref="refs/heads/main",
            expected_source_repository_revision="a" * 40,
            repository_revision="b" * 40, repository_tree_identity="c" * 40,
            satisfied_work_unit_ids=[str(ids["work_unit"])],
            completion_evaluation_ids=[str(ids["completion"])],
            verification_record_ids=[str(ids["verification"])],
            production_admissibility_id=ids["admissibility"],
            production_admissibility_basis_fingerprint="b" * 64,
            commit_fingerprint="d" * 64, committed_at=datetime.now(UTC)))
    observed = products.get(product_id, "human:owner")
    source = observed["current_sources"][0]
    assert source["metadata"]["revision"] == "b" * 40
    assert source["metadata"]["last_work_id"] == str(ids["work"])
    assert source["metadata"]["revision_evidence_ref"].startswith("runtime-commit:")
    assert any(item["kind"] == "SOURCE_COMMITTED" for item in
               products.history(product_id, "human:owner")["timeline"])


def _seed_measurement_reality(database: Database) -> dict[str, UUID | datetime]:
    start = datetime(2026, 9, 6, 9, 0, tzinfo=UTC)
    ids: dict[str, UUID | datetime] = {
        name: uuid4()
        for name in (
            "baseline",
            "resource",
            "work",
            "scope",
            "resource_binding",
            "admission",
            "run",
            "plan_revision",
            "work_unit",
            "runtime_binding",
            "attempt",
            "context",
            "dispatch",
            "report",
            "observation",
            "completion",
            "proposed_snapshot",
            "verification",
            "admissibility",
            "candidate",
            "authorization_governance",
            "authorization",
            "effect",
            "steering_plan",
            "steering_revision",
            "steering_step",
            "steering_decision",
            "production_proposal",
        )
    }
    ids["pwu_created_at"] = start + timedelta(seconds=10)
    plan = ProductionPlanProposal(
        proposal_id=ids["production_proposal"],
        objective="Create one measurement architecture note",
        desired_outcome="The note is present and verified",
        ordered_steps=(
            ProductionPlanStep(position=1, instruction="Create the exact note"),
            ProductionPlanStep(position=2, instruction="Verify the exact note"),
        ),
        artifact_targets=(
            ProductionPlanArtifactTarget(
                path="docs/architecture/measurement-note.md",
                operation=PlannedArtifactOperation.CREATE,
            ),
        ),
        verification_approach="Verify exact content",
        fit_classification=OnePwuFitClassification.ONE_PWU_FIT,
        engineering_resource_id=ids["resource"],
        repository_identity="test://dcp2-measurement",
        source_baseline_id=ids["baseline"],
        source_revision="a" * 40,
    )
    contract = CompletionContract(
        required_outputs=("docs/architecture/measurement-note.md",),
        required_changes=("docs/architecture/measurement-note.md",),
        verification_obligations=("verify exact content",),
        artifact_contract=ArtifactContract(
            engineering_resource_id=ids["resource"],
            repository_identity="test://dcp2-measurement",
            source_baseline_id=ids["baseline"],
            source_revision="a" * 40,
            artifact_path="docs/architecture/measurement-note.md",
            operation=ArtifactOperation.CREATE,
            expected_outcome="The note is present and verified",
            verification_obligation="verify exact content",
        ),
        production_plan=plan,
    )
    binding = {
        "binding_ref": "binding:test:dcp2",
        "capability_identity": "capability:executor",
        "profile_identity": "profile:test",
    }
    workspace = {
        "workspace_identity": "workspace:test:dcp2",
        "workspace_path": "/tmp/dcp2-workspace",
        "repository_identity": "test://dcp2-measurement",
        "repository_path": "/tmp/dcp2-repository",
        "source_revision": "a" * 40,
    }
    with database.engine.begin() as connection:
        connection.execute(
            insert(production_snapshots).values(
                id=ids["baseline"],
                condition="TRUSTED",
                repository_identity="test://dcp2-measurement",
                repository_ref="refs/heads/main",
                repository_revision="a" * 40,
                source_baseline_id=None,
                created_at=start,
            )
        )
        connection.execute(
            insert(engineering_resources).values(
                id=ids["resource"],
                kind="REPOSITORY",
                repository_identity="test://dcp2-measurement",
                location_ref="/tmp/dcp2-repository",
                authoritative_ref="refs/heads/main",
                context_references=[],
                is_default=True,
                created_at=start,
                updated_at=start,
            )
        )
        connection.execute(
            insert(product_works).values(
                id=ids["work"],
                goal_id=None,
                work_mode="LONG_LIVED_STEERING",
                raw_user_requirement="Measure this admitted production Work",
                refined_title="Measurement Work",
                desired_outcome="The note is present and verified",
                constraints=[],
                tags=[],
                condition="READY",
                scope_summary="docs/architecture",
                production_objective=plan.objective,
                expected_artifact_path="docs/architecture/measurement-note.md",
                artifact_operation="CREATE",
                artifact_placement_rationale="Exact admitted test target",
                artifact_target_confidence="HIGH",
                artifact_source_baseline_id=ids["baseline"],
                artifact_source_revision="a" * 40,
                verification_expectation="verify exact content",
                code_change_proposal=None,
                production_plan_proposal=plan.model_dump(mode="json"),
                created_at=start - timedelta(seconds=5),
                updated_at=start,
            )
        )
        connection.execute(
            insert(engineering_scopes).values(
                id=ids["scope"],
                work_id=ids["work"],
                summary="docs/architecture",
                fingerprint="1" * 64,
                condition="ADMITTED",
                created_at=start,
                updated_at=start,
            )
        )
        connection.execute(
            insert(engineering_resource_bindings).values(
                id=ids["resource_binding"],
                engineering_scope_id=ids["scope"],
                resource_id=ids["resource"],
                condition="ACTIVE",
                created_at=start,
            )
        )
        connection.execute(
            insert(governance_records).values(
                id=ids["admission"],
                decision_type="ADMIT_LONG_LIVED_WORK",
                authority_identity="human:test",
                subject_type="PRODUCT_WORK",
                subject_identity=str(ids["work"]),
                scope={},
                rationale="Admit bounded Work",
                created_at=start,
            )
        )
        connection.execute(
            insert(production_runs).values(
                id=ids["run"],
                intent_ref=f"work:{ids['work']}",
                goal=plan.objective,
                production_horizon="DOCUMENTATION",
                source_baseline_id=ids["baseline"],
                current_plan_revision_id=None,
                condition="OPEN",
                version=1,
                created_at=start + timedelta(seconds=10),
            )
        )
        connection.execute(
            insert(plan_revisions).values(
                id=ids["plan_revision"],
                production_run_id=ids["run"],
                revision_number=1,
                source_baseline_id=ids["baseline"],
                condition="ACTIVE",
                version=0,
                created_at=start + timedelta(seconds=10),
            )
        )
        connection.execute(
            update(production_runs)
            .where(production_runs.c.id == ids["run"])
            .values(current_plan_revision_id=ids["plan_revision"])
        )
        connection.execute(
            insert(production_work_units).values(
                id=ids["work_unit"],
                production_run_id=ids["run"],
                plan_revision_id=ids["plan_revision"],
                source_baseline_id=ids["baseline"],
                objective=plan.objective,
                completion_contract=contract.model_dump(mode="json"),
                condition="SATISFIED",
                version=3,
                current_execution_generation=1,
                created_at=ids["pwu_created_at"],
            )
        )
        connection.execute(
            insert(execution_attempts).values(
                id=ids["attempt"],
                work_unit_id=ids["work_unit"],
                generation=1,
                plan_revision_id=ids["plan_revision"],
                source_baseline_id=ids["baseline"],
                condition="CREATED",
                retry_of=None,
                created_at=start + timedelta(seconds=11),
            )
        )
        connection.execute(
            insert(context_packages).values(
                id=ids["context"],
                version=1,
                production_run_id=ids["run"],
                work_unit_id=ids["work_unit"],
                plan_revision_id=ids["plan_revision"],
                source_baseline_id=ids["baseline"],
                manifest={"artifacts": []},
                content_fingerprint="2" * 64,
                completion_contract_fingerprint="3" * 64,
                created_at=start + timedelta(seconds=12),
            )
        )
        connection.execute(
            insert(execution_dispatches).values(
                id=ids["dispatch"],
                attempt_id=ids["attempt"],
                generation=1,
                context_package_id=ids["context"],
                source_baseline_id=ids["baseline"],
                executor_binding=binding,
                authoritative_ref_revision="a" * 40,
                dispatched_at=start + timedelta(seconds=13),
                **workspace,
            )
        )
        connection.execute(
            insert(provider_execution_reports).values(
                id=ids["report"],
                dispatch_id=ids["dispatch"],
                attempt_id=ids["attempt"],
                generation=1,
                executor_binding=binding,
                provider_reference="provider:test:dcp2",
                outcome="SUCCESS",
                started_at=start + timedelta(seconds=15),
                finished_at=start + timedelta(seconds=22),
                metadata={"internal_turn_count": 2, "self_refine_occurred": True},
                summary="bounded execution complete",
                recorded_at=start + timedelta(seconds=23),
            )
        )
        connection.execute(
            insert(repository_observations).values(
                id=ids["observation"],
                dispatch_id=ids["dispatch"],
                attempt_id=ids["attempt"],
                generation=1,
                source_baseline_id=ids["baseline"],
                repository_identity="test://dcp2-measurement",
                source_revision="a" * 40,
                authoritative_ref_revision="a" * 40,
                change_manifest=[],
                observation_fingerprint="4" * 64,
                observed_at=start + timedelta(seconds=23),
                **{key: workspace[key] for key in ("workspace_identity", "workspace_path")},
            )
        )
        connection.execute(
            insert(completion_evaluations).values(
                id=ids["completion"],
                production_run_id=ids["run"],
                work_unit_id=ids["work_unit"],
                plan_revision_id=ids["plan_revision"],
                source_baseline_id=ids["baseline"],
                attempt_id=ids["attempt"],
                generation=1,
                completion_contract_fingerprint="3" * 64,
                repository_observation_id=ids["observation"],
                repository_observation_fingerprint="4" * 64,
                work_product_lineage=[],
                work_product_set_fingerprint="5" * 64,
                basis_fingerprint="6" * 64,
                outcome="PRODUCED",
                obligation_results=[],
                created_at=start + timedelta(seconds=24),
            )
        )
        connection.execute(
            insert(proposed_repository_snapshots).values(
                id=ids["proposed_snapshot"],
                production_run_id=ids["run"],
                work_unit_id=ids["work_unit"],
                plan_revision_id=ids["plan_revision"],
                source_baseline_id=ids["baseline"],
                attempt_id=ids["attempt"],
                generation=1,
                completion_evaluation_id=ids["completion"],
                repository_observation_id=ids["observation"],
                repository_identity="test://dcp2-measurement",
                repository_ref="refs/heads/main",
                authoritative_ref_revision="a" * 40,
                proposed_commit_identity="b" * 40,
                tree_identity="c" * 40,
                basis_fingerprint="7" * 64,
                created_at=start + timedelta(seconds=25),
            )
        )
        connection.execute(
            insert(verification_records).values(
                id=ids["verification"],
                production_run_id=ids["run"],
                work_unit_id=ids["work_unit"],
                plan_revision_id=ids["plan_revision"],
                source_baseline_id=ids["baseline"],
                completion_evaluation_id=ids["completion"],
                proposed_snapshot_id=ids["proposed_snapshot"],
                proposed_commit_identity="b" * 40,
                tree_identity="c" * 40,
                obligation="verify exact content",
                obligation_fingerprint="8" * 64,
                provider_binding={
                    "provider_identity": "verifier:test",
                    "provider_version": "1",
                },
                result="PASS",
                evidence={
                    "obligation": "verify exact content",
                    "subject_commit_identity": "b" * 40,
                    "subject_tree_identity": "c" * 40,
                    "expected": "PASS",
                    "observed": "PASS",
                    "metadata": {"duration_ms": 2500},
                },
                basis_fingerprint="9" * 64,
                created_at=start + timedelta(seconds=28),
            )
        )
        connection.execute(
            insert(production_admissibility_records).values(
                id=ids["admissibility"],
                production_run_id=ids["run"],
                work_unit_id=ids["work_unit"],
                plan_revision_id=ids["plan_revision"],
                source_baseline_id=ids["baseline"],
                completion_evaluation_id=ids["completion"],
                proposed_snapshot_id=ids["proposed_snapshot"],
                required_obligations_fingerprint="a" * 64,
                verification_record_ids=[str(ids["verification"])],
                obligation_results=[],
                basis_fingerprint="b" * 64,
                outcome="ADMISSIBLE",
                created_at=start + timedelta(seconds=29),
            )
        )
        connection.execute(
            insert(baseline_candidates).values(
                id=ids["candidate"],
                condition="SEALED",
                production_run_id=ids["run"],
                plan_revision_id=ids["plan_revision"],
                source_baseline_id=ids["baseline"],
                repository_identity="test://dcp2-measurement",
                target_authoritative_ref="refs/heads/main",
                expected_source_repository_revision="a" * 40,
                proposed_snapshot_id=ids["proposed_snapshot"],
                proposed_commit_identity="b" * 40,
                proposed_tree_identity="c" * 40,
                satisfied_work_unit_ids=[str(ids["work_unit"])],
                completion_evaluation_ids=[str(ids["completion"])],
                work_product_reference_ids=[],
                verification_record_ids=[str(ids["verification"])],
                production_admissibility_id=ids["admissibility"],
                production_admissibility_basis_fingerprint="b" * 64,
                fingerprint="c" * 64,
                sealed_at=start + timedelta(seconds=30),
            )
        )
        connection.execute(
            insert(governance_records).values(
                id=ids["authorization_governance"],
                decision_type="AUTHORIZE_BASELINE_CANDIDATE",
                authority_identity="human:test",
                subject_type="BASELINE_CANDIDATE",
                subject_identity=str(ids["candidate"]),
                scope={},
                rationale="Authorize exact Candidate",
                created_at=start + timedelta(seconds=60),
            )
        )
        connection.execute(
            insert(human_authorizations).values(
                id=ids["authorization"],
                authority_identity="human:test",
                candidate_id=ids["candidate"],
                candidate_fingerprint="c" * 64,
                authorization_scope={
                    "action": "REPOSITORY_INTEGRATION",
                    "repository_identity": "test://dcp2-measurement",
                    "target_authoritative_ref": "refs/heads/main",
                    "expected_source_repository_revision": "a" * 40,
                    "proposed_repository_revision": "b" * 40,
                },
                source_baseline_id=ids["baseline"],
                repository_identity="test://dcp2-measurement",
                target_authoritative_ref="refs/heads/main",
                expected_source_repository_revision="a" * 40,
                proposed_repository_revision="b" * 40,
                rationale="Authorize exact Candidate",
                governance_record_id=ids["authorization_governance"],
                basis_fingerprint="d" * 64,
                authorized_at=start + timedelta(seconds=60),
            )
        )
        connection.execute(
            insert(repository_integration_effects).values(
                id=ids["effect"],
                version=1,
                effect_type="REPOSITORY_REF_ADVANCE",
                state="CONVERGED",
                candidate_id=ids["candidate"],
                candidate_fingerprint="c" * 64,
                human_authorization_id=ids["authorization"],
                repository_identity="test://dcp2-measurement",
                target_authoritative_ref="refs/heads/main",
                expected_source_repository_revision="a" * 40,
                proposed_repository_revision="b" * 40,
                proposed_tree_identity="c" * 40,
                operation_fingerprint="e" * 64,
                prepared_at=start + timedelta(seconds=61),
                observed_repository_revision="b" * 40,
                observed_at=start + timedelta(seconds=65),
                converged_at=start + timedelta(seconds=65),
            )
        )
        connection.execute(
            insert(steering_plans).values(
                id=ids["steering_plan"],
                work_id=ids["work"],
                created_at=start,
            )
        )
        connection.execute(
            insert(steering_plan_revisions).values(
                id=ids["steering_revision"],
                steering_plan_id=ids["steering_plan"],
                work_id=ids["work"],
                revision_number=1,
                condition="ACTIVE",
                supersedes_revision_id=None,
                rationale="Admitted long-lived plan",
                reality_refs=[],
                created_at=start,
            )
        )
        connection.execute(
            insert(steering_steps).values(
                id=ids["steering_step"],
                steering_plan_revision_id=ids["steering_revision"],
                type="COMPLETE",
                objective="Recognize trusted completion",
                completion_condition="Trusted Runtime Commit exists",
                position=1,
                state="CLOSED",
                elaborates_step_id=None,
                created_at=start,
            )
        )
        connection.execute(
            insert(steering_decisions).values(
                id=ids["steering_decision"],
                steering_plan_revision_id=ids["steering_revision"],
                current_step_id=ids["steering_step"],
                next_step_type="COMPLETE",
                objective="Complete the Work",
                reason="Trusted completion Reality exists",
                reality_refs=[],
                human_required=False,
                completion_condition="Trusted completion recognized",
                steering_outcome="COMPLETE",
                basis_fingerprint="f" * 64,
                reasoning_provider_identity=None,
                attention_reason=None,
                recommendation=None,
                alternatives=[],
                trade_offs=[],
                expected_impact=None,
                authority_assessment=None,
                proposed_engineering_scope_fingerprint=None,
                created_at=start + timedelta(seconds=100),
            )
        )
        connection.execute(
            insert(work_runtime_bindings).values(
                id=ids["runtime_binding"],
                work_id=ids["work"],
                cycle_number=1,
                steering_step_id=ids["steering_step"],
                steering_decision_id=ids["steering_decision"],
                engineering_scope_id=ids["scope"],
                resource_id=ids["resource"],
                production_run_id=ids["run"],
                plan_revision_id=ids["plan_revision"],
                work_unit_id=ids["work_unit"],
                governance_record_id=ids["admission"],
                admitted_by="spg-steering-production",
                condition="TRUSTED",
                created_at=ids["pwu_created_at"],
            )
        )
    return ids


def _table_counts(database: Database) -> dict[str, int]:
    with database.engine.connect() as connection:
        return {
            table.name: connection.scalar(select(func.count()).select_from(table))
            for table in (*product_tables, *runtime_tables)
        }


def _count(database: Database, table) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table))


def _truncate(database: Database) -> None:
    names = ", ".join(f'"{name}"' for name in ALL_TABLE_NAMES)
    with database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {names} CASCADE")
