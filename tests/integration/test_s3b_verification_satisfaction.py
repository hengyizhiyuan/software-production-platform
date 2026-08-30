from collections.abc import Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, inspect, select

from spg.application.completion import CompletionService
from spg.application.execution import ExecutionService
from spg.application.preparation import PreparationService
from spg.application.runtime import RuntimeService
from spg.application.verification import VerificationService
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
    RuntimeNotBootstrapped,
    WorkUnitCondition,
)
from spg.domain.verification import (
    ProductionAdmissibilityOutcome,
    VerificationResultValue,
)
from spg.infrastructure.persistence import (
    Database,
    OptimisticConcurrencyConflict,
    metadata,
    update_versioned_row,
)
from spg.infrastructure.persistence.runtime_schema import (
    baseline_candidates,
    current_trusted_baseline_pointer,
    human_authorizations,
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
from spg.providers.deterministic_verifier import DeterministicVerificationProvider


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TABLE_NAMES = {table.name for table in runtime_tables}
OBLIGATION_A = "document structure check"
OBLIGATION_B = "architecture marker check"


@dataclass(frozen=True)
class VerificationFacts:
    database: Database
    runtime: RuntimeService
    verification: VerificationService
    repository: Path
    baseline: object
    spine: object
    attempt: object
    execution_result: object
    completion_result: object


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
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    return repository


def _build(
    database: Database,
    repository: Path,
    tmp_path: Path,
    *,
    obligations: tuple[str, ...] = (OBLIGATION_A,),
    operations: tuple[DeterministicFileOperation, ...] | None = None,
    provider_outcome: ProviderReportedOutcome = ProviderReportedOutcome.SUCCESS,
    label: str = "primary",
) -> VerificationFacts:
    runtime = RuntimeService(database)
    preparation = PreparationService(database)
    execution = ExecutionService(database, preparation=preparation)
    completion = CompletionService(database, observer=execution.observer)
    verification = VerificationService(database, observer=execution.observer)
    try:
        baseline = runtime.current_baseline()
    except RuntimeNotBootstrapped:
        baseline = runtime.bootstrap_trusted_baseline(
            BootstrapRequest(
                repository_path=repository,
                repository_identity="test://s3b-repository",
                repository_ref="refs/heads/main",
                authority_identity="architecture-lead:test",
                scope={"slice": "S3-B"},
            )
        ).snapshot
    contract = CompletionContract(
        required_outputs=(f"docs/{label}.md",),
        required_changes=(f"docs/{label}.md",),
        verification_obligations=obligations,
    )
    spine = runtime.create_initial_runtime_spine(
        InitialRunRequest(
            intent_ref=f"intent:test:s3b:{label}",
            goal="Verify governed documentation production",
            production_horizon=ProductionHorizon.DOCUMENTATION,
            initial_work_unit_objective=f"Produce and verify {label}",
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
    preparation.prepare_attempt(
        attempt.id,
        package.id,
        ExecutorBinding(
            binding_ref="binding:deterministic-documentation",
            capability_identity="capability:executor",
            profile_identity="profile:local-fvs",
        ),
        repository,
        tmp_path / "attempt-workspaces",
    )
    if operations is None:
        operations = (_create(f"docs/{label}.md", f"{label} output\n"),)
    executor = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=operations,
            reported_outcome=provider_outcome,
            summary="deterministic S3-B execution",
        )
    )
    execution_result = execution.dispatch_and_observe(attempt.id, executor)
    completion_result = completion.evaluate_observation(execution_result.observation.id)
    return VerificationFacts(
        database=database,
        runtime=runtime,
        verification=verification,
        repository=repository,
        baseline=baseline,
        spine=spine,
        attempt=attempt,
        execution_result=execution_result,
        completion_result=completion_result,
    )


def _create(path: str, content: str) -> DeterministicFileOperation:
    return DeterministicFileOperation(
        operation=DeterministicFileOperationType.CREATE,
        repository_relative_path=path,
        content=content,
    )


def _provider(
    outcomes: dict[str, VerificationResultValue],
    *,
    version: str = "v1",
) -> DeterministicVerificationProvider:
    return DeterministicVerificationProvider(outcomes, provider_version=version)


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


def _snapshot(facts: VerificationFacts):
    return facts.verification.create_proposed_snapshot(facts.completion_result.evaluation.id)


def _verify_pass(facts: VerificationFacts, snapshot, obligation: str = OBLIGATION_A):
    return facts.verification.verify_obligation(
        snapshot.id,
        obligation,
        _provider({obligation: VerificationResultValue.PASS}),
    )


def test_s3b_migration_downgrade_and_reupgrade(postgres_database: Database) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260828_04")
    tables = set(inspect(postgres_database.engine).get_table_names())
    assert not {
        "proposed_repository_snapshots",
        "verification_records",
        "production_admissibility_records",
    } & tables
    command.upgrade(config, "head")
    assert {
        "proposed_repository_snapshots",
        "verification_records",
        "production_admissibility_records",
    } <= set(inspect(postgres_database.engine).get_table_names())


def test_s3b_01_produced_required(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        operations=(),
    )
    assert facts.completion_result.work_unit.condition is WorkUnitCondition.PROPOSED
    with pytest.raises(RuntimeInvariantViolation, match="exact Produced lineage|PRODUCED"):
        facts.verification.create_proposed_snapshot(
            facts.completion_result.evaluation.id
        )


def test_s3b_02_exact_proposed_snapshot(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    snapshot = _snapshot(facts)
    change = facts.execution_result.observation.changes[0]
    assert snapshot.completion_evaluation_id == facts.completion_result.evaluation.id
    assert snapshot.repository_observation_id == facts.execution_result.observation.id
    assert _git(git_repository, "rev-parse", f"{snapshot.proposed_commit_identity}^{{tree}}") == snapshot.tree_identity
    assert _git(git_repository, "rev-parse", f"{snapshot.proposed_commit_identity}:{change.repository_relative_path}") == change.observed_fingerprint


def test_s3b_03_snapshot_does_not_advance_ref(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = _git(git_repository, "rev-parse", "refs/heads/main")
    snapshot = _snapshot(facts)
    after = _git(git_repository, "rev-parse", "refs/heads/main")
    assert before == after == snapshot.authoritative_ref_revision
    assert snapshot.proposed_commit_identity != after


def test_s3b_04_workspace_drift_rejects_snapshot(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    workspace = facts.execution_result.dispatch.workspace.workspace_path
    (workspace / "docs" / "primary.md").write_text("drifted\n", encoding="utf-8")
    with pytest.raises(RuntimeInvariantViolation, match="workspace changed"):
        _snapshot(facts)
    assert _count(postgres_database, proposed_repository_snapshots) == 0


def test_s3b_05_snapshot_immutability(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    first = _snapshot(facts)
    second = _snapshot(facts)
    assert first == second
    assert _count(postgres_database, proposed_repository_snapshots) == 1


def test_s3b_06_verification_exact_subject(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    snapshot = _snapshot(facts)
    record = _verify_pass(facts, snapshot)
    assert record.proposed_snapshot_id == snapshot.id
    assert record.proposed_commit_identity == snapshot.proposed_commit_identity
    assert record.tree_identity == snapshot.tree_identity
    assert record.completion_evaluation_id == facts.completion_result.evaluation.id
    assert record.evidence.subject_commit_identity == snapshot.proposed_commit_identity


def test_s3b_07_deterministic_verification_pass(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    record = _verify_pass(facts, _snapshot(facts))
    assert record.result is VerificationResultValue.PASS
    assert record.evidence.observed == "PASS"
    assert _count(postgres_database, verification_records) == 1


def test_s3b_08_deterministic_verification_fail(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    snapshot = _snapshot(facts)
    record = facts.verification.verify_obligation(
        snapshot.id,
        OBLIGATION_A,
        _provider({OBLIGATION_A: VerificationResultValue.FAIL}),
    )
    result = facts.verification.evaluate_admissibility(snapshot.id)
    assert record.result is VerificationResultValue.FAIL
    assert result.admissibility.outcome is ProductionAdmissibilityOutcome.NOT_ADMISSIBLE
    assert result.work_unit.condition is WorkUnitCondition.PRODUCED


def test_s3b_09_verification_unknown(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    snapshot = _snapshot(facts)
    record = facts.verification.verify_obligation(
        snapshot.id,
        OBLIGATION_A,
        _provider({}),
    )
    result = facts.verification.evaluate_admissibility(snapshot.id)
    assert record.result is VerificationResultValue.UNKNOWN
    assert result.admissibility.outcome is ProductionAdmissibilityOutcome.NOT_ADMISSIBLE


def test_s3b_10_missing_verification_blocks_satisfaction(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.verification.evaluate_admissibility(_snapshot(facts).id)
    assert result.admissibility.outcome is ProductionAdmissibilityOutcome.NOT_ADMISSIBLE
    assert result.admissibility.obligation_results[0].verification_record_id is None
    assert result.work_unit.condition is WorkUnitCondition.PRODUCED


def test_s3b_11_result_and_applicability_are_separate(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    first = _build(postgres_database, git_repository, tmp_path, label="first")
    first_snapshot = _snapshot(first)
    record = _verify_pass(first, first_snapshot)
    second = _build(postgres_database, git_repository, tmp_path, label="second")
    second_snapshot = _snapshot(second)
    assessment = second.verification.assess_applicability(record.id, second_snapshot.id)
    with second.database.unit_of_work() as unit_of_work:
        historical = RuntimeStore(unit_of_work.session).verification_record(record.id)
    assert historical is not None
    assert historical.result is VerificationResultValue.PASS
    assert assessment.applicable is False
    assert assessment.reasons


def test_s3b_12_old_snapshot_pass_cannot_satisfy_new_snapshot(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    first = _build(postgres_database, git_repository, tmp_path, label="old")
    _verify_pass(first, _snapshot(first))
    second = _build(postgres_database, git_repository, tmp_path, label="new")
    result = second.verification.evaluate_admissibility(_snapshot(second).id)
    assert result.admissibility.outcome is ProductionAdmissibilityOutcome.NOT_ADMISSIBLE
    assert result.work_unit.condition is WorkUnitCondition.PRODUCED


def test_s3b_13_wrong_plan_or_baseline_evidence_rejected(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    first = _build(postgres_database, git_repository, tmp_path, label="plan-one")
    record = _verify_pass(first, _snapshot(first))
    second = _build(postgres_database, git_repository, tmp_path, label="plan-two")
    assessment = second.verification.assess_applicability(record.id, _snapshot(second).id)
    assert assessment.applicable is False
    assert "Plan Revision changed" in assessment.reasons


def test_s3b_14_all_required_verifications_are_required(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        obligations=(OBLIGATION_A, OBLIGATION_B),
    )
    snapshot = _snapshot(facts)
    _verify_pass(facts, snapshot, OBLIGATION_A)
    result = facts.verification.evaluate_admissibility(snapshot.id)
    assert result.admissibility.outcome is ProductionAdmissibilityOutcome.NOT_ADMISSIBLE
    assert [item.admissible for item in result.admissibility.obligation_results] == [True, False]


def test_s3b_15_produced_and_all_pass_becomes_satisfied(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(
        postgres_database,
        git_repository,
        tmp_path,
        obligations=(OBLIGATION_A, OBLIGATION_B),
    )
    snapshot = _snapshot(facts)
    provider = _provider(
        {
            OBLIGATION_A: VerificationResultValue.PASS,
            OBLIGATION_B: VerificationResultValue.PASS,
        }
    )
    facts.verification.verify_obligation(snapshot.id, OBLIGATION_A, provider)
    facts.verification.verify_obligation(snapshot.id, OBLIGATION_B, provider)
    result = facts.verification.evaluate_admissibility(snapshot.id)
    assert result.admissibility.outcome is ProductionAdmissibilityOutcome.ADMISSIBLE
    assert result.work_unit.condition is WorkUnitCondition.SATISFIED


def test_s3b_16_produced_does_not_imply_satisfied(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    _snapshot(facts)
    assert facts.runtime.inspect_run(facts.spine.run.id).work_unit.condition is WorkUnitCondition.PRODUCED
    assert _count(postgres_database, production_admissibility_records) == 0


def test_s3b_17_executor_provider_success_has_no_satisfaction_authority(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    result = facts.verification.evaluate_admissibility(_snapshot(facts).id)
    assert facts.execution_result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert result.work_unit.condition is WorkUnitCondition.PRODUCED
    assert result.admissibility.outcome is ProductionAdmissibilityOutcome.NOT_ADMISSIBLE


def test_s3b_18_satisfaction_atomicity(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    snapshot = _snapshot(facts)
    _verify_pass(facts, snapshot)

    def fail_satisfaction(self, work_unit_id, expected_version):
        raise RuntimeError("injected Satisfaction failure")

    monkeypatch.setattr(RuntimeStore, "mark_work_unit_satisfied", fail_satisfaction)
    with pytest.raises(RuntimeError, match="injected Satisfaction failure"):
        facts.verification.evaluate_admissibility(snapshot.id)
    assert _count(postgres_database, production_admissibility_records) == 0
    assert facts.runtime.inspect_run(facts.spine.run.id).work_unit.condition is WorkUnitCondition.PRODUCED
    with facts.database.engine.connect() as connection:
        count = connection.scalar(
            select(func.count()).select_from(transition_history).where(
                transition_history.c.reason == "VERIFICATION_EVIDENCE_ADMISSIBILITY_EVALUATED"
            )
        )
    assert count == 0


def test_s3b_19_satisfaction_optimistic_concurrency(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    snapshot = _snapshot(facts)
    _verify_pass(facts, snapshot)
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
        facts.verification.evaluate_admissibility(
            snapshot.id,
            expected_work_unit_version=current.version,
        )
    assert _count(postgres_database, production_admissibility_records) == 0
    assert facts.runtime.inspect_run(facts.spine.run.id).work_unit.condition is WorkUnitCondition.PRODUCED


def test_s3b_20_stale_production_lineage_cannot_satisfy(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    facts.runtime.retry_attempt(facts.attempt.id)
    with pytest.raises(RuntimeInvariantViolation, match="stale production lineage"):
        _snapshot(facts)
    assert facts.runtime.attempt_is_current(facts.attempt.id) is False
    assert facts.runtime.inspect_run(facts.spine.run.id).work_unit.condition is WorkUnitCondition.PRODUCED


def test_s3b_21_satisfaction_creates_no_candidate(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    snapshot = _snapshot(facts)
    _verify_pass(facts, snapshot)
    result = facts.verification.evaluate_admissibility(snapshot.id)
    assert result.work_unit.condition is WorkUnitCondition.SATISFIED
    assert _count(postgres_database, baseline_candidates) == 0
    assert _count(postgres_database, human_authorizations) == 0
    assert not {"candidates", "candidate_authorizations"} & set(
        inspect(postgres_database.engine).get_table_names()
    )


def test_s3b_22_no_repository_integration_or_ref_movement(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before_ref = _git(git_repository, "rev-parse", "refs/heads/main")
    before_baseline = facts.runtime.current_baseline()
    snapshot = _snapshot(facts)
    _verify_pass(facts, snapshot)
    facts.verification.evaluate_admissibility(snapshot.id)
    assert _git(git_repository, "rev-parse", "refs/heads/main") == before_ref
    assert facts.runtime.current_baseline() == before_baseline
    assert "repository_integrations" not in inspect(postgres_database.engine).get_table_names()


def test_s3b_23_documentation_horizon_can_be_satisfied(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path, label="decision")
    snapshot = _snapshot(facts)
    _verify_pass(facts, snapshot)
    result = facts.verification.evaluate_admissibility(snapshot.id)
    assert facts.spine.run.production_horizon is ProductionHorizon.DOCUMENTATION
    assert result.work_unit.condition is WorkUnitCondition.SATISFIED
    assert not snapshot.proposed_commit_identity.endswith((".py", ".js", ".ts"))


def test_s3b_24_verification_provider_remains_replaceable(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    snapshot = _snapshot(facts)
    provider = DeterministicVerificationProvider(
        {OBLIGATION_A: VerificationResultValue.PASS},
        provider_identity="provider:alternate-assurance",
        provider_version="2026.08",
    )
    record = facts.verification.verify_obligation(snapshot.id, OBLIGATION_A, provider)
    assert record.provider == provider.binding
    assert "guardian_findings" not in inspect(postgres_database.engine).get_table_names()


def test_s3b_25_no_trust_score(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    record = _verify_pass(facts, _snapshot(facts))
    assert record.evidence.metadata["score"] is None
    assert "trust_score" not in type(record).model_fields
    assert "trust_scores" not in inspect(postgres_database.engine).get_table_names()


def test_s3b_26_verification_idempotency_and_history(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    snapshot = _snapshot(facts)
    first = _verify_pass(facts, snapshot)
    repeated = _verify_pass(facts, snapshot)
    rerun = facts.verification.verify_obligation(
        snapshot.id,
        OBLIGATION_A,
        _provider({OBLIGATION_A: VerificationResultValue.PASS}, version="v2"),
    )
    assert first == repeated
    assert rerun.id != first.id
    assert _count(postgres_database, verification_records) == 2
    with facts.database.unit_of_work() as unit_of_work:
        historical = RuntimeStore(unit_of_work.session).verification_record(first.id)
    assert historical == first


def test_s3b_27_existing_regression_contracts_remain(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    facts = _build(postgres_database, git_repository, tmp_path)
    before = facts.runtime.current_baseline()
    snapshot = _snapshot(facts)
    _verify_pass(facts, snapshot)
    result = facts.verification.evaluate_admissibility(snapshot.id)
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
    assert result.work_unit.condition is WorkUnitCondition.SATISFIED
    assert facts.runtime.current_baseline() == before
    with postgres_database.engine.connect() as connection:
        assert connection.scalar(
            select(func.count()).select_from(current_trusted_baseline_pointer)
        ) == 1
