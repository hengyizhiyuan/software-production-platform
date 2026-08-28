from collections.abc import Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess

from alembic import command
from alembic.config import Config
import pytest
from pydantic import ValidationError
from sqlalchemy import func, inspect, select

from spg.application.completion import CompletionService
from spg.application.execution import ExecutionService
from spg.application.preparation import (
    PreparationService,
    completion_contract_fingerprint,
)
from spg.application.runtime import RuntimeService
from spg.domain.completion import (
    CompletionEvaluationOutcome,
    CompletionObligationResultValue,
)
from spg.domain.execution import ProviderReportedOutcome
from spg.domain.preparation import (
    ContextArtifactSelection,
    ContextPackageRequest,
    ContextSemanticRole,
    ExecutorBinding,
)
from spg.domain.runtime import (
    BootstrapRequest,
    CompletionContract,
    InitialRunRequest,
    ProductionHorizon,
    RuntimeInvariantViolation,
    WorkUnitCondition,
)
from spg.infrastructure.persistence import (
    Database,
    OptimisticConcurrencyConflict,
    metadata,
    update_versioned_row,
)
from spg.infrastructure.persistence.runtime_schema import (
    completion_evaluations,
    current_trusted_baseline_pointer,
    production_admissibility_records,
    production_work_units,
    proposed_repository_snapshots,
    runtime_tables,
    transition_history,
    verification_records,
)
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.providers.deterministic_executor import (
    DeterministicExecutionSpecification,
    DeterministicFileOperation,
    DeterministicFileOperationType,
    DeterministicTestExecutor,
)


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TABLE_NAMES = {table.name for table in runtime_tables}
LATER_STAGE_TABLES = {
    "qualifications",
    "candidates",
    "authorizations",
    "repository_integrations",
    "production_issues",
    "external_effects",
}


@dataclass(frozen=True)
class CompletionFacts:
    database: Database
    runtime: RuntimeService
    preparation: PreparationService
    execution: ExecutionService
    completion: CompletionService
    repository: Path
    baseline: object
    spine: object
    attempt: object
    package: object
    prepared: object
    execution_result: object
    workspace_root: Path


def _migration_config(database: Database) -> Config:
    os.environ["SPG_DATABASE_URL"] = database.engine.url.render_as_string(
        hide_password=False
    )
    return Config(PROJECT_ROOT / "alembic.ini")


@pytest.fixture(autouse=True)
def clean_runtime_schema(postgres_database: Database) -> Iterator[None]:
    previous_database_url = os.environ.get("SPG_DATABASE_URL")
    command.upgrade(_migration_config(postgres_database), "head")
    _truncate_runtime(postgres_database)
    try:
        yield
    finally:
        command.upgrade(_migration_config(postgres_database), "head")
        _truncate_runtime(postgres_database)
        if previous_database_url is None:
            os.environ.pop("SPG_DATABASE_URL", None)
        else:
            os.environ["SPG_DATABASE_URL"] = previous_database_url


@pytest.fixture
def git_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "governed-repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "docs").mkdir()
    (repository / "AI_context.md").write_text("baseline context\n", encoding="utf-8")
    (repository / "docs" / "contract.md").write_text(
        "execution contract\n", encoding="utf-8"
    )
    (repository / "docs" / "existing.md").write_text(
        "existing version\n", encoding="utf-8"
    )
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    return repository


def _build(
    database: Database,
    repository: Path,
    tmp_path: Path,
    contract: CompletionContract,
    *,
    operations: tuple[DeterministicFileOperation, ...] = (),
    outcome: ProviderReportedOutcome = ProviderReportedOutcome.SUCCESS,
) -> CompletionFacts:
    runtime = RuntimeService(database)
    preparation = PreparationService(database)
    execution = ExecutionService(database, preparation=preparation)
    completion = CompletionService(database, observer=execution.observer)
    baseline = runtime.bootstrap_trusted_baseline(
        BootstrapRequest(
            repository_path=repository,
            repository_identity="test://s3a-repository",
            repository_ref="refs/heads/main",
            authority_identity="architecture-lead:test",
            scope={"slice": "S3-A"},
        )
    ).snapshot
    spine = runtime.create_initial_runtime_spine(
        InitialRunRequest(
            intent_ref="intent:test:s3a-documentation",
            goal="Evaluate governed documentation production",
            production_horizon=ProductionHorizon.DOCUMENTATION,
            initial_work_unit_objective="Produce the exact contracted output",
            completion_contract=contract,
        )
    )
    attempt = runtime.create_initial_attempt(spine.work_unit.id)
    package = preparation.assemble_context_package(
        spine.work_unit.id,
        repository,
        ContextPackageRequest(
            artifacts=(
                ContextArtifactSelection(
                    semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                    repository_relative_path="AI_context.md",
                ),
                ContextArtifactSelection(
                    semantic_role=ContextSemanticRole.EXECUTION_CONTRACT,
                    repository_relative_path="docs/contract.md",
                ),
            )
        ),
    )
    workspace_root = tmp_path / "attempt-workspaces"
    prepared = preparation.prepare_attempt(
        attempt.id,
        package.id,
        _binding(),
        repository,
        workspace_root,
    )
    executor = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=operations,
            reported_outcome=outcome,
            summary="deterministic S3-A execution",
        )
    )
    execution_result = execution.dispatch_and_observe(attempt.id, executor)
    return CompletionFacts(
        database=database,
        runtime=runtime,
        preparation=preparation,
        execution=execution,
        completion=completion,
        repository=repository,
        baseline=baseline,
        spine=spine,
        attempt=attempt,
        package=package,
        prepared=prepared,
        execution_result=execution_result,
        workspace_root=workspace_root,
    )


def _create(path: str, content: str) -> DeterministicFileOperation:
    return DeterministicFileOperation(
        operation=DeterministicFileOperationType.CREATE,
        repository_relative_path=path,
        content=content,
    )


def _modify(path: str, content: str) -> DeterministicFileOperation:
    return DeterministicFileOperation(
        operation=DeterministicFileOperationType.MODIFY,
        repository_relative_path=path,
        content=content,
    )


def _binding() -> ExecutorBinding:
    return ExecutorBinding(
        binding_ref="binding:deterministic-documentation",
        capability_identity="capability:executor",
        profile_identity="profile:local-fvs",
    )


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _truncate_runtime(database: Database) -> None:
    table_names = ", ".join(f'"{name}"' for name in RUNTIME_TABLE_NAMES)
    with database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {table_names} CASCADE")


def _count(database: Database, table) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table))


def test_s3a_migration_downgrade_and_reupgrade(
    postgres_database: Database,
) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260828_03")
    tables = set(inspect(postgres_database.engine).get_table_names())
    assert "completion_evaluations" not in tables

    command.upgrade(config, "head")
    tables = set(inspect(postgres_database.engine).get_table_names())
    assert "completion_evaluations" in tables
    assert not LATER_STAGE_TABLES & tables


def test_s3a_01_exact_completion_basis(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    contract = CompletionContract(
        required_outputs=("docs/result.md",),
        required_changes=("docs/result.md",),
    )
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        contract,
        operations=(_create("docs/result.md", "result\n"),),
    )

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )
    evaluation = result.evaluation

    assert evaluation.production_run_id == facts.spine.run.id
    assert evaluation.work_unit_id == facts.spine.work_unit.id
    assert evaluation.plan_revision_id == facts.spine.plan_revision.id
    assert evaluation.source_baseline_id == facts.baseline.id
    assert evaluation.attempt_id == facts.attempt.id
    assert evaluation.generation == facts.attempt.generation
    assert evaluation.completion_contract_fingerprint == (
        completion_contract_fingerprint(contract)
    )
    assert evaluation.repository_observation_id == facts.execution_result.observation.id
    assert evaluation.repository_observation_fingerprint == (
        facts.execution_result.observation.observation_fingerprint
    )
    assert [item.reference_id for item in evaluation.work_product_lineage] == [
        facts.execution_result.work_products[0].id
    ]
    assert len(evaluation.basis_fingerprint) == 64


def test_s3a_02_required_artifact_pass(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(required_outputs=("docs/result.md",)),
        operations=(_create("docs/result.md", "produced\n"),),
    )

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert result.evaluation.outcome is CompletionEvaluationOutcome.PRODUCED
    assert result.work_unit.condition is WorkUnitCondition.PRODUCED


def test_s3a_03_missing_required_artifact(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(required_outputs=("docs/result.md",)),
    )

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert facts.execution_result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert result.evaluation.outcome is CompletionEvaluationOutcome.NOT_PRODUCED
    assert result.work_unit.condition is WorkUnitCondition.PROPOSED


def test_s3a_04_unrelated_success(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(required_outputs=("docs/result.md",)),
        operations=(_create("unrelated.txt", "unrelated\n"),),
    )

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert [item.artifact_path for item in facts.execution_result.work_products] == [
        "unrelated.txt"
    ]
    assert result.evaluation.outcome is CompletionEvaluationOutcome.NOT_PRODUCED


def test_s3a_05_no_change_success(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(required_changes=("docs/result.md",)),
    )

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert facts.execution_result.observation.changes == ()
    assert result.evaluation.outcome is CompletionEvaluationOutcome.NOT_PRODUCED


def test_s3a_06_provider_failure_with_required_output(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(required_outputs=("docs/result.md",)),
        operations=(_create("docs/result.md", "produced despite report\n"),),
        outcome=ProviderReportedOutcome.FAILURE,
    )

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert facts.execution_result.provider_report.outcome is ProviderReportedOutcome.FAILURE
    assert result.evaluation.outcome is CompletionEvaluationOutcome.PRODUCED
    with facts.database.unit_of_work() as unit_of_work:
        report = RuntimeStore(unit_of_work.session).provider_execution_report(
            facts.execution_result.dispatch.id
        )
    assert report is not None
    assert report.outcome is ProviderReportedOutcome.FAILURE


def test_s3a_07_required_change_evaluation(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(required_changes=("docs/existing.md",)),
        operations=(_modify("docs/existing.md", "changed version\n"),),
    )

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert result.evaluation.outcome is CompletionEvaluationOutcome.PRODUCED
    assert result.evaluation.obligation_results[0].observed == "MODIFIED"


def test_s3a_08_required_marker_evaluation(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(
            required_outputs=("docs/result.md",),
            required_markers=("S3-A-COMPLETE",),
        ),
        operations=(_create("docs/result.md", "S3-A-COMPLETE\n"),),
    )

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert result.evaluation.outcome is CompletionEvaluationOutcome.PRODUCED
    assert result.evaluation.obligation_results[-1].observed == "docs/result.md"


def test_s3a_09_observation_drift_rejects_marker_evaluation(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(
            required_outputs=("docs/result.md",),
            required_markers=("ORIGINAL-MARKER",),
        ),
        operations=(_create("docs/result.md", "ORIGINAL-MARKER\n"),),
    )
    target = facts.prepared.execution_request.workspace.workspace_path / "docs/result.md"
    target.write_text("CHANGED-AFTER-OBSERVATION\n", encoding="utf-8")

    with pytest.raises(
        RuntimeInvariantViolation,
        match="changed after the bound Repository Observation",
    ):
        facts.completion.evaluate_observation(facts.execution_result.observation.id)

    assert _count(postgres_database, completion_evaluations) == 0


def test_s3a_10_forbidden_change_blocks_produced(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(
            required_outputs=("docs/result.md",),
            forbidden_changes=("src",),
        ),
        operations=(
            _create("docs/result.md", "required\n"),
            _create("src/forbidden.py", "forbidden = True\n"),
        ),
    )

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert result.evaluation.outcome is CompletionEvaluationOutcome.NOT_PRODUCED
    assert result.evaluation.obligation_results[-1].result is (
        CompletionObligationResultValue.FAIL
    )


def test_s3a_11_multiple_output_obligations_require_all(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(
            required_outputs=("docs/a.md", "docs/b.md"),
            required_changes=("docs/a.md", "docs/b.md"),
        ),
        operations=(_create("docs/a.md", "only A\n"),),
    )

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert result.evaluation.outcome is CompletionEvaluationOutcome.NOT_PRODUCED
    assert sum(
        item.result is CompletionObligationResultValue.FAIL
        for item in result.evaluation.obligation_results
    ) == 2


def test_s3a_12_verification_obligations_are_excluded(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(
            required_outputs=("docs/result.md",),
            verification_obligations=("independent review passes",),
        ),
        operations=(_create("docs/result.md", "output only\n"),),
    )

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert result.evaluation.outcome is CompletionEvaluationOutcome.PRODUCED
    assert all(
        "verification" not in item.obligation_type.value.lower()
        for item in result.evaluation.obligation_results
    )
    assert result.work_unit.condition is WorkUnitCondition.PRODUCED
    assert not LATER_STAGE_TABLES & set(inspect(postgres_database.engine).get_table_names())


def test_s3a_13_evaluation_immutability(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(required_outputs=("docs/result.md",)),
        operations=(_create("docs/result.md", "immutable\n"),),
    )
    evaluation = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    ).evaluation

    with pytest.raises(ValidationError, match="frozen"):
        evaluation.outcome = CompletionEvaluationOutcome.NOT_PRODUCED  # type: ignore[misc]

    with facts.database.unit_of_work() as unit_of_work:
        stored = RuntimeStore(unit_of_work.session).completion_evaluation_by_basis(
            evaluation.basis_fingerprint
        )
    assert stored == evaluation
    assert not hasattr(RuntimeStore, "update_completion_evaluation")


def test_s3a_14_evaluation_idempotency(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(required_outputs=("docs/result.md",)),
        operations=(_create("docs/result.md", "idempotent\n"),),
    )

    first = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )
    second = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert second.evaluation == first.evaluation
    assert second.work_unit == first.work_unit
    assert _count(postgres_database, completion_evaluations) == 1
    with facts.database.engine.connect() as connection:
        transitions = connection.scalar(
            select(func.count())
            .select_from(transition_history)
            .where(
                transition_history.c.reason
                == "COMPLETION_OUTPUT_OBLIGATIONS_SATISFIED"
            )
        )
    assert transitions == 1


def test_s3a_15_new_observation_creates_new_evaluation(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(required_outputs=("docs/result.md",)),
        operations=(_create("unrelated.txt", "first attempt\n"),),
    )
    first = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )
    assert first.evaluation.outcome is CompletionEvaluationOutcome.NOT_PRODUCED

    retry = facts.runtime.retry_attempt(facts.attempt.id)
    prepared = facts.preparation.prepare_attempt(
        retry.id,
        facts.package.id,
        _binding(),
        facts.repository,
        facts.workspace_root,
    )
    executor = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=(_create("docs/result.md", "second attempt\n"),),
            reported_outcome=ProviderReportedOutcome.SUCCESS,
        )
    )
    second_execution = facts.execution.dispatch_and_observe(retry.id, executor)
    second = facts.completion.evaluate_observation(second_execution.observation.id)

    assert second.evaluation.outcome is CompletionEvaluationOutcome.PRODUCED
    assert second.evaluation.id != first.evaluation.id
    assert second.evaluation.repository_observation_id != (
        first.evaluation.repository_observation_id
    )
    assert prepared.execution_request.generation == 2
    with facts.database.unit_of_work() as unit_of_work:
        history = RuntimeStore(
            unit_of_work.session
        ).completion_evaluations_for_work_unit(facts.spine.work_unit.id)
    assert history == (first.evaluation, second.evaluation)


def test_s3a_16_stale_generation_cannot_produce_current_pwu(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(required_outputs=("docs/result.md",)),
        operations=(_create("docs/result.md", "stale output\n"),),
    )
    later_attempt = facts.runtime.retry_attempt(facts.attempt.id)

    with pytest.raises(RuntimeInvariantViolation, match="stale Attempt generation"):
        facts.completion.evaluate_observation(facts.execution_result.observation.id)

    assert facts.runtime.attempt_is_current(facts.attempt.id) is False
    assert facts.runtime.attempt_is_current(later_attempt.id) is True
    assert _count(postgres_database, completion_evaluations) == 0
    assert facts.runtime.inspect_run(
        facts.spine.run.id
    ).work_unit.condition is WorkUnitCondition.PROPOSED


def test_s3a_17_produced_is_not_satisfied(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(
            required_outputs=("docs/result.md",),
            verification_obligations=("review remains outstanding",),
        ),
        operations=(_create("docs/result.md", "produced only\n"),),
    )
    before_baseline = facts.runtime.current_baseline()

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert result.work_unit.condition is WorkUnitCondition.PRODUCED
    assert _count(postgres_database, proposed_repository_snapshots) == 0
    assert _count(postgres_database, verification_records) == 0
    assert _count(postgres_database, production_admissibility_records) == 0
    assert facts.runtime.current_baseline() == before_baseline
    assert not LATER_STAGE_TABLES & set(inspect(postgres_database.engine).get_table_names())


def test_s3a_18_atomic_produced_mutation(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(required_outputs=("docs/result.md",)),
        operations=(_create("docs/result.md", "atomic\n"),),
    )

    def fail_before_pwu_transition(self, work_unit_id, expected_version):
        raise RuntimeError("injected produced-transition failure")

    monkeypatch.setattr(
        RuntimeStore,
        "mark_work_unit_produced",
        fail_before_pwu_transition,
    )
    with pytest.raises(RuntimeError, match="injected produced-transition failure"):
        facts.completion.evaluate_observation(facts.execution_result.observation.id)

    assert _count(postgres_database, completion_evaluations) == 0
    assert facts.runtime.inspect_run(
        facts.spine.run.id
    ).work_unit.condition is WorkUnitCondition.PROPOSED
    with facts.database.engine.connect() as connection:
        transitions = connection.scalar(
            select(func.count())
            .select_from(transition_history)
            .where(
                transition_history.c.reason
                == "OUTPUT_OBLIGATIONS_EVALUATED"
            )
        )
    assert transitions == 0


def test_s3a_19_optimistic_concurrency(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(required_outputs=("docs/result.md",)),
        operations=(_create("docs/result.md", "concurrent\n"),),
    )
    with facts.database.unit_of_work() as unit_of_work:
        store = RuntimeStore(unit_of_work.session)
        current = store.work_unit(facts.spine.work_unit.id)
        assert current is not None
        update_versioned_row(
            unit_of_work.session,
            production_work_units,
            identity={"id": current.id},
            expected_version=current.version,
            values={"objective": current.objective},
        )
        unit_of_work.commit()

    with pytest.raises(OptimisticConcurrencyConflict):
        facts.completion.evaluate_observation(
            facts.execution_result.observation.id,
            expected_work_unit_version=current.version,
        )

    assert _count(postgres_database, completion_evaluations) == 0
    assert facts.runtime.inspect_run(
        facts.spine.run.id
    ).work_unit.condition is WorkUnitCondition.PROPOSED


def test_s3a_20_non_code_documentation_production(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(
            required_outputs=("docs/decision.md",),
            required_changes=("docs/decision.md",),
        ),
        operations=(_create("docs/decision.md", "architecture decision\n"),),
    )

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert facts.spine.run.production_horizon is ProductionHorizon.DOCUMENTATION
    assert result.evaluation.outcome is CompletionEvaluationOutcome.PRODUCED
    assert [item.artifact_path for item in result.evaluation.work_product_lineage] == [
        "docs/decision.md"
    ]
    assert all(
        not item.artifact_path.endswith((".py", ".js", ".ts"))
        for item in result.evaluation.work_product_lineage
    )


def test_s3a_21_no_guardian_or_verification_leakage(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(blocking_conditions=("output blocker remains",)),
    )

    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert result.evaluation.outcome is CompletionEvaluationOutcome.NOT_PRODUCED
    assert result.evaluation.obligation_results[0].reason == (
        "declared blocking output condition prevents Produced"
    )
    tables = set(inspect(postgres_database.engine).get_table_names())
    assert not LATER_STAGE_TABLES & tables
    assert _count(postgres_database, proposed_repository_snapshots) == 0
    assert _count(postgres_database, verification_records) == 0
    assert _count(postgres_database, production_admissibility_records) == 0
    assert not {
        "guardian_findings",
        "evidence_graph",
        "trust_scores",
    } & tables


def test_s3a_22_existing_s1_s2_regression_contracts_remain(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        CompletionContract(required_outputs=("docs/result.md",)),
        operations=(_create("docs/result.md", "regression\n"),),
    )
    result = facts.completion.evaluate_observation(
        facts.execution_result.observation.id
    )

    assert {
        "production_snapshots",
        "current_trusted_baseline_pointer",
        "production_runs",
        "plan_revisions",
        "production_work_units",
        "execution_attempts",
        "context_packages",
        "attempt_preparations",
        "execution_dispatches",
        "provider_execution_reports",
        "repository_observations",
        "work_product_references",
        "completion_evaluations",
        "proposed_repository_snapshots",
        "verification_records",
        "production_admissibility_records",
    } <= set(metadata.tables)
    assert facts.execution_result.provider_report.id is not None
    assert facts.execution_result.observation.id is not None
    assert facts.execution_result.work_products
    assert result.evaluation.outcome is CompletionEvaluationOutcome.PRODUCED
    with postgres_database.engine.connect() as connection:
        pointer_count = connection.scalar(
            select(func.count()).select_from(current_trusted_baseline_pointer)
        )
    assert pointer_count == 1
