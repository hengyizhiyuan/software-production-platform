from collections.abc import Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, inspect, select

from spg.application.execution import ExecutionService
from spg.application.preparation import PreparationService
from spg.application.runtime import RuntimeService
from spg.domain.execution import ArtifactChangeType, ProviderReportedOutcome
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
    RuntimeDomainError,
    RuntimeInvariantViolation,
)
from spg.infrastructure.persistence import Database, metadata
from spg.infrastructure.persistence.runtime_schema import (
    execution_dispatches,
    provider_execution_reports,
    repository_observations,
    runtime_tables,
    work_product_references,
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


@dataclass(frozen=True)
class RuntimeFacts:
    database: Database
    runtime: RuntimeService
    preparation: PreparationService
    execution: ExecutionService
    repository: Path
    baseline: object
    spine: object
    attempt: object
    workspace_root: Path


@dataclass(frozen=True)
class PreparedFacts(RuntimeFacts):
    package: object
    prepared: object


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
    (repository / "docs" / "delete-me.md").write_text(
        "delete source\n", encoding="utf-8"
    )
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    return repository


@pytest.fixture
def runtime_facts(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> RuntimeFacts:
    runtime = RuntimeService(postgres_database)
    preparation = PreparationService(postgres_database)
    execution = ExecutionService(postgres_database, preparation=preparation)
    baseline = runtime.bootstrap_trusted_baseline(
        BootstrapRequest(
            repository_path=git_repository,
            repository_identity="test://s2b-repository",
            repository_ref="refs/heads/main",
            authority_identity="architecture-lead:test",
            scope={"slice": "S2-B"},
        )
    ).snapshot
    spine = runtime.create_initial_runtime_spine(
        InitialRunRequest(
            intent_ref="intent:test:s2b-documentation",
            goal="Observe governed documentation production",
            production_horizon=ProductionHorizon.DOCUMENTATION,
            initial_work_unit_objective="Create docs/expected.md",
            completion_contract=CompletionContract(
                required_outputs=("docs/expected.md",),
                required_changes=("record S2-B evidence",),
                forbidden_changes=("authoritative repository ref",),
                verification_obligations=("later independent verification",),
            ),
        )
    )
    attempt = runtime.create_initial_attempt(spine.work_unit.id)
    return RuntimeFacts(
        database=postgres_database,
        runtime=runtime,
        preparation=preparation,
        execution=execution,
        repository=git_repository,
        baseline=baseline,
        spine=spine,
        attempt=attempt,
        workspace_root=tmp_path / "attempt-workspaces",
    )


@pytest.fixture
def prepared_facts(runtime_facts: RuntimeFacts) -> PreparedFacts:
    package = runtime_facts.preparation.assemble_context_package(
        runtime_facts.spine.work_unit.id,
        runtime_facts.repository,
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
    prepared = runtime_facts.preparation.prepare_attempt(
        runtime_facts.attempt.id,
        package.id,
        _binding(),
        runtime_facts.repository,
        runtime_facts.workspace_root,
    )
    return PreparedFacts(
        **runtime_facts.__dict__,
        package=package,
        prepared=prepared,
    )


def _binding() -> ExecutorBinding:
    return ExecutorBinding(
        binding_ref="binding:deterministic-documentation",
        capability_identity="capability:executor",
        profile_identity="profile:local-fvs",
    )


def _executor(
    *operations: DeterministicFileOperation,
    outcome: ProviderReportedOutcome = ProviderReportedOutcome.SUCCESS,
    before_mutation=None,
    after_mutation=None,
) -> DeterministicTestExecutor:
    return DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=operations,
            reported_outcome=outcome,
            summary="deterministic S2-B execution",
        ),
        before_mutation=before_mutation,
        after_mutation=after_mutation,
    )


def _operation(kind: DeterministicFileOperationType, path: str, content=None):
    return DeterministicFileOperation(
        operation=kind,
        repository_relative_path=path,
        content=content,
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


def test_s2b_migration_downgrade_and_reupgrade(postgres_database: Database) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260828_02")
    tables = set(inspect(postgres_database.engine).get_table_names())
    assert not {
        "execution_dispatches",
        "provider_execution_reports",
        "repository_observations",
        "work_product_references",
    } & tables

    command.upgrade(config, "head")
    tables = set(inspect(postgres_database.engine).get_table_names())
    assert {
        "execution_dispatches",
        "provider_execution_reports",
        "repository_observations",
        "work_product_references",
    } <= tables
    assert not {
        "verifications",
        "candidates",
        "production_issues",
        "external_effects",
        "repository_integrations",
    } & tables


def test_s2b_01_prepared_attempt_required(runtime_facts: RuntimeFacts) -> None:
    executor = _executor()
    with pytest.raises(RuntimeDomainError):
        runtime_facts.execution.dispatch_and_observe(
            runtime_facts.attempt.id,
            executor,
        )
    assert executor.dispatch_count == 0
    assert _count(runtime_facts.database, execution_dispatches) == 0


def test_s2b_02_current_generation_required(prepared_facts: PreparedFacts) -> None:
    prepared_facts.runtime.retry_attempt(prepared_facts.attempt.id)
    executor = _executor()
    with pytest.raises(RuntimeInvariantViolation, match="current Attempt"):
        prepared_facts.execution.dispatch_and_observe(
            prepared_facts.attempt.id,
            executor,
        )
    assert executor.dispatch_count == 0


def test_s2b_03_dispatch_is_durable_before_provider_work(
    prepared_facts: PreparedFacts,
) -> None:
    def assert_durable(request) -> None:
        with prepared_facts.database.unit_of_work() as unit_of_work:
            record = RuntimeStore(unit_of_work.session).execution_dispatch(
                request.dispatch_id
            )
        assert record is not None
        assert record.attempt_id == prepared_facts.attempt.id
        assert not (request.execution.workspace.workspace_path / "docs/output.md").exists()

    executor = _executor(
        _operation(
            DeterministicFileOperationType.CREATE,
            "docs/output.md",
            "created after durable dispatch\n",
        ),
        before_mutation=assert_durable,
    )
    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        executor,
    )
    assert result.dispatch.attempt_id == prepared_facts.attempt.id


def test_s2b_04_deterministic_successful_execution(
    prepared_facts: PreparedFacts,
) -> None:
    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(
            _operation(
                DeterministicFileOperationType.CREATE,
                "docs/expected.md",
                "governed output\n",
            )
        ),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert (
        prepared_facts.prepared.preparation.workspace.workspace_path
        / "docs/expected.md"
    ).read_text(encoding="utf-8") == "governed output\n"


def test_s2b_05_provider_success_has_no_completion_authority(
    prepared_facts: PreparedFacts,
) -> None:
    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(),
    )
    durable_spine = prepared_facts.runtime.inspect_run(prepared_facts.spine.run.id)
    durable_attempt = prepared_facts.runtime.get_attempt(prepared_facts.attempt.id)
    assert result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert durable_spine.work_unit.condition.value == "PROPOSED"
    assert durable_attempt.condition.value == "CREATED"


def test_s2b_06_observation_is_independent_from_provider_prose(
    prepared_facts: PreparedFacts,
) -> None:
    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(
            _operation(
                DeterministicFileOperationType.MODIFY,
                "docs/existing.md",
                "independently visible\n",
            )
        ),
    )
    assert result.provider_report.metadata == {"operation_count": 1}
    assert [change.repository_relative_path for change in result.observation.changes] == [
        "docs/existing.md"
    ]


def test_s2b_07_added_artifact_has_exact_observed_fingerprint(
    prepared_facts: PreparedFacts,
) -> None:
    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(
            _operation(
                DeterministicFileOperationType.CREATE,
                "docs/added.md",
                "added\n",
            )
        ),
    )
    change = result.observation.changes[0]
    assert change.change_type is ArtifactChangeType.ADDED
    assert change.source_fingerprint is None
    assert change.observed_fingerprint == _git(
        prepared_facts.prepared.preparation.workspace.workspace_path,
        "hash-object",
        "--",
        "docs/added.md",
    )


def test_s2b_08_modified_artifact_compares_exact_source_baseline(
    prepared_facts: PreparedFacts,
) -> None:
    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(
            _operation(
                DeterministicFileOperationType.MODIFY,
                "docs/existing.md",
                "modified\n",
            )
        ),
    )
    change = result.observation.changes[0]
    assert change.change_type is ArtifactChangeType.MODIFIED
    assert change.source_fingerprint == _git(
        prepared_facts.repository,
        "rev-parse",
        f"{prepared_facts.baseline.repository_revision}:docs/existing.md",
    )
    assert change.observed_fingerprint != change.source_fingerprint


def test_s2b_09_deleted_artifact_preserves_prior_identity(
    prepared_facts: PreparedFacts,
) -> None:
    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(
            _operation(
                DeterministicFileOperationType.DELETE,
                "docs/delete-me.md",
            )
        ),
    )
    change = result.observation.changes[0]
    assert change.change_type is ArtifactChangeType.DELETED
    assert change.source_fingerprint is not None
    assert change.observed_fingerprint is None
    assert result.work_products[0].change_type is ArtifactChangeType.DELETED


def test_s2b_10_execution_and_observation_protect_authoritative_ref(
    prepared_facts: PreparedFacts,
) -> None:
    before = _git(prepared_facts.repository, "rev-parse", "refs/heads/main")
    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(
            _operation(
                DeterministicFileOperationType.CREATE,
                "docs/output.md",
                "isolated\n",
            )
        ),
    )
    after = _git(prepared_facts.repository, "rev-parse", "refs/heads/main")
    assert after == before
    assert result.dispatch.authoritative_ref_revision == before
    assert result.observation.authoritative_ref_revision == before


def test_s2b_11_work_product_reference_preserves_exact_lineage(
    prepared_facts: PreparedFacts,
) -> None:
    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(
            _operation(
                DeterministicFileOperationType.CREATE,
                "docs/lineage.md",
                "lineage\n",
            )
        ),
    )
    reference = result.work_products[0]
    assert reference.production_run_id == prepared_facts.spine.run.id
    assert reference.work_unit_id == prepared_facts.spine.work_unit.id
    assert reference.plan_revision_id == prepared_facts.spine.plan_revision.id
    assert reference.attempt_id == prepared_facts.attempt.id
    assert reference.generation == prepared_facts.attempt.generation
    assert reference.source_baseline_id == prepared_facts.baseline.id
    assert reference.repository_observation_id == result.observation.id
    assert reference.artifact_path == "docs/lineage.md"
    assert reference.observed_fingerprint == result.observation.changes[0].observed_fingerprint


def test_s2b_12_false_success_is_factual_without_completion_judgment(
    prepared_facts: PreparedFacts,
) -> None:
    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(
            _operation(
                DeterministicFileOperationType.CREATE,
                "docs/partial.md",
                "not the required artifact\n",
            )
        ),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert [item.artifact_path for item in result.work_products] == ["docs/partial.md"]
    assert not (
        prepared_facts.prepared.preparation.workspace.workspace_path
        / "docs/expected.md"
    ).exists()
    assert prepared_facts.runtime.inspect_run(
        prepared_facts.spine.run.id
    ).work_unit.condition.value == "PROPOSED"


def test_s2b_13_provider_failure_preserves_real_artifact_changes(
    prepared_facts: PreparedFacts,
) -> None:
    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(
            _operation(
                DeterministicFileOperationType.CREATE,
                "docs/failed-provider-output.md",
                "real output despite claim\n",
            ),
            outcome=ProviderReportedOutcome.FAILURE,
        ),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.FAILURE
    assert [item.artifact_path for item in result.work_products] == [
        "docs/failed-provider-output.md"
    ]


def test_s2b_14_unrelated_success_preserves_only_observed_change(
    prepared_facts: PreparedFacts,
) -> None:
    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(
            _operation(
                DeterministicFileOperationType.CREATE,
                "scratch.tmp",
                "unrelated\n",
            )
        ),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert [item.artifact_path for item in result.work_products] == ["scratch.tmp"]
    assert prepared_facts.runtime.get_attempt(
        prepared_facts.attempt.id
    ).condition.value == "CREATED"


def test_s2b_15_no_change_is_a_durable_observation(
    prepared_facts: PreparedFacts,
) -> None:
    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert result.observation.changes == ()
    assert result.work_products == ()
    assert _count(prepared_facts.database, repository_observations) == 1


def test_s2b_16_duplicate_normal_dispatch_is_rejected(
    prepared_facts: PreparedFacts,
) -> None:
    first_executor = _executor()
    prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        first_executor,
    )
    second_executor = _executor()
    with pytest.raises(RuntimeInvariantViolation, match="dispatch fact"):
        prepared_facts.execution.dispatch_and_observe(
            prepared_facts.attempt.id,
            second_executor,
        )
    assert first_executor.dispatch_count == 1
    assert second_executor.dispatch_count == 0
    assert _count(prepared_facts.database, execution_dispatches) == 1


def test_s2b_17_stale_post_execution_facts_remain_history(
    prepared_facts: PreparedFacts,
) -> None:
    later_attempt = {}

    def make_stale(_request) -> None:
        later_attempt["record"] = prepared_facts.runtime.retry_attempt(
            prepared_facts.attempt.id
        )

    result = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(
            _operation(
                DeterministicFileOperationType.CREATE,
                "docs/late.md",
                "historical output\n",
            ),
            after_mutation=make_stale,
        ),
    )
    assert prepared_facts.runtime.attempt_is_current(prepared_facts.attempt.id) is False
    assert prepared_facts.runtime.attempt_is_current(later_attempt["record"].id) is True
    assert result.provider_report.attempt_id == prepared_facts.attempt.id
    assert result.observation.attempt_id == prepared_facts.attempt.id
    assert result.work_products[0].attempt_id == prepared_facts.attempt.id
    assert prepared_facts.runtime.inspect_run(
        prepared_facts.spine.run.id
    ).work_unit.condition.value == "PROPOSED"


def test_s2b_18_execution_has_no_completion_or_later_stage_path(
    prepared_facts: PreparedFacts,
) -> None:
    prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(
            _operation(
                DeterministicFileOperationType.CREATE,
                "docs/expected.md",
                "exists but is not evaluated\n",
            )
        ),
    )
    assert prepared_facts.runtime.inspect_run(
        prepared_facts.spine.run.id
    ).work_unit.condition.value == "PROPOSED"
    assert prepared_facts.runtime.get_attempt(
        prepared_facts.attempt.id
    ).condition.value == "CREATED"
    assert not {
        "verifications",
        "candidates",
        "production_issues",
        "repository_integrations",
        "runtime_commits",
    } & set(metadata.tables)


def test_s2b_19_observation_idempotency_is_deterministic(
    prepared_facts: PreparedFacts,
) -> None:
    first = prepared_facts.execution.dispatch_and_observe(
        prepared_facts.attempt.id,
        _executor(
            _operation(
                DeterministicFileOperationType.CREATE,
                "docs/idempotent.md",
                "stable\n",
            )
        ),
    )
    repeated_observation, repeated_products = prepared_facts.execution.observe_dispatch(
        first.dispatch.id
    )
    assert repeated_observation.id == first.observation.id
    assert repeated_observation.observation_fingerprint == (
        first.observation.observation_fingerprint
    )
    assert repeated_products == first.work_products
    assert _count(prepared_facts.database, repository_observations) == 1
    assert _count(prepared_facts.database, work_product_references) == 1
    assert _count(prepared_facts.database, provider_execution_reports) == 1
