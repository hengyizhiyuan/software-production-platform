from collections.abc import Iterator
import inspect as python_inspect
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from alembic import command
from alembic.config import Config
from pydantic import ValidationError
import pytest
from sqlalchemy import func, inspect, select, update

from spg.application.preparation import (
    PreparationService,
    completion_contract_fingerprint,
)
from spg.application.runtime import RuntimeService
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
    RuntimeRecordNotFound,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_schema import (
    attempt_preparations,
    context_packages,
    execution_attempts,
    runtime_tables,
)
from spg.infrastructure.persistence.runtime_store import RuntimeStore


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TABLE_NAMES = {table.name for table in runtime_tables}


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
        "execution contract v1\n",
        encoding="utf-8",
    )
    (repository / "docs" / "constraint.md").write_text(
        "do not change authoritative refs\n",
        encoding="utf-8",
    )
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    return repository


@pytest.fixture
def services(postgres_database: Database) -> tuple[RuntimeService, PreparationService]:
    return RuntimeService(postgres_database), PreparationService(postgres_database)


@pytest.fixture
def attempt_facts(
    services: tuple[RuntimeService, PreparationService],
    git_repository: Path,
):
    runtime, preparation = services
    baseline = runtime.bootstrap_trusted_baseline(
        BootstrapRequest(
            repository_path=git_repository,
            repository_identity="test://s2a-repository",
            repository_ref="refs/heads/main",
            authority_identity="architecture-lead:test",
            scope={"slice": "S2-A"},
        )
    ).snapshot
    spine = runtime.create_initial_runtime_spine(_run_request())
    attempt = runtime.create_initial_attempt(spine.work_unit.id)
    return runtime, preparation, baseline, spine, attempt


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _run_request() -> InitialRunRequest:
    return InitialRunRequest(
        intent_ref="intent:test:s2a-documentation",
        goal="Prepare a governed documentation execution",
        production_horizon=ProductionHorizon.DOCUMENTATION,
        initial_work_unit_objective="Update the governed documentation",
        completion_contract=CompletionContract(
            required_outputs=("AI_context.md",),
            required_changes=("record the admitted stage",),
            forbidden_changes=("authoritative repository ref",),
            verification_obligations=("independent diff observation",),
        ),
    )


def _context_request(*paths: tuple[ContextSemanticRole, str]) -> ContextPackageRequest:
    selected = paths or (
        (ContextSemanticRole.PROJECT_CONTEXT, "AI_context.md"),
        (ContextSemanticRole.EXECUTION_CONTRACT, "docs/contract.md"),
    )
    return ContextPackageRequest(
        artifacts=tuple(
            ContextArtifactSelection(
                semantic_role=role,
                repository_relative_path=path,
            )
            for role, path in selected
        )
    )


def _executor_binding() -> ExecutorBinding:
    return ExecutorBinding(
        binding_ref="binding:documentation-default",
        capability_identity="capability:executor",
        profile_identity="profile:local-fvs",
    )


def _package(preparation, spine, repository):
    return preparation.assemble_context_package(
        spine.work_unit.id,
        repository,
        _context_request(),
    )


def _prepare(preparation, attempt, package, repository, workspace_root):
    return preparation.prepare_attempt(
        attempt.id,
        package.id,
        _executor_binding(),
        repository,
        workspace_root,
    )


def _truncate_runtime(database: Database) -> None:
    table_names = ", ".join(f'"{name}"' for name in RUNTIME_TABLE_NAMES)
    with database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {table_names} CASCADE")


def _count(database: Database, table) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table))


def test_s2a_migration_downgrade_and_reupgrade(postgres_database: Database) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260827_01")
    tables = set(inspect(postgres_database.engine).get_table_names())
    assert "context_packages" not in tables
    assert "attempt_preparations" not in tables

    command.upgrade(config, "head")
    tables = set(inspect(postgres_database.engine).get_table_names())
    assert {"context_packages", "attempt_preparations"} <= tables
    assert not {
        "work_products",
        "verifications",
        "candidates",
        "production_issues",
        "external_effects",
        "provider_registry",
    } & tables


def test_s2a_01_context_package_uses_exact_baseline_not_advanced_head(
    attempt_facts,
    git_repository: Path,
) -> None:
    _, preparation, baseline, spine, _ = attempt_facts
    baseline_blob = _git(
        git_repository,
        "rev-parse",
        f"{baseline.repository_revision}:AI_context.md",
    )
    (git_repository / "AI_context.md").write_text("advanced context\n", encoding="utf-8")
    _git(git_repository, "add", "AI_context.md")
    _git(git_repository, "commit", "-m", "advance context")

    package = _package(preparation, spine, git_repository)

    entry = next(
        item
        for item in package.manifest.artifacts
        if item.repository_relative_path == "AI_context.md"
    )
    assert entry.source_revision == baseline.repository_revision
    assert entry.blob_fingerprint == baseline_blob
    assert _git(git_repository, "rev-parse", "HEAD") != baseline.repository_revision


def test_s2a_02_dirty_working_tree_does_not_contaminate_context(
    attempt_facts,
    git_repository: Path,
) -> None:
    _, preparation, baseline, spine, _ = attempt_facts
    exact_blob = _git(
        git_repository,
        "rev-parse",
        f"{baseline.repository_revision}:AI_context.md",
    )
    (git_repository / "AI_context.md").write_text(
        "uncommitted contamination\n",
        encoding="utf-8",
    )

    package = _package(preparation, spine, git_repository)

    context_entry = next(
        item
        for item in package.manifest.artifacts
        if item.repository_relative_path == "AI_context.md"
    )
    assert context_entry.blob_fingerprint == exact_blob
    assert "AI_context.md" in _git(git_repository, "status", "--porcelain")


def test_s2a_04_context_package_versions_are_immutable_and_idempotent(
    attempt_facts,
    git_repository: Path,
) -> None:
    _, preparation, _, spine, _ = attempt_facts
    first = preparation.assemble_context_package(
        spine.work_unit.id,
        git_repository,
        _context_request((ContextSemanticRole.PROJECT_CONTEXT, "AI_context.md")),
    )
    repeated = preparation.assemble_context_package(
        spine.work_unit.id,
        git_repository,
        _context_request((ContextSemanticRole.PROJECT_CONTEXT, "AI_context.md")),
    )
    changed = preparation.assemble_context_package(
        spine.work_unit.id,
        git_repository,
        _context_request(
            (ContextSemanticRole.PROJECT_CONTEXT, "AI_context.md"),
            (ContextSemanticRole.CONSTRAINT, "docs/constraint.md"),
        ),
    )

    assert repeated.id == first.id
    assert changed.id != first.id
    assert changed.version == first.version + 1
    assert preparation.context_package(first.id) == first


def test_s2a_05_completion_contract_fingerprint_is_exactly_bound(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    _, preparation, _, spine, attempt = attempt_facts
    package = _package(preparation, spine, git_repository)

    result = _prepare(preparation, attempt, package, git_repository, tmp_path / "workspaces")

    expected = completion_contract_fingerprint(spine.work_unit.completion_contract)
    assert package.completion_contract_fingerprint == expected
    assert result.execution_request.completion_contract_fingerprint == expected


def test_s2a_06_preparation_persists_provider_neutral_executor_binding(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    _, preparation, _, spine, attempt = attempt_facts
    package = _package(preparation, spine, git_repository)

    result = _prepare(preparation, attempt, package, git_repository, tmp_path / "workspaces")

    assert result.preparation.executor_binding == _executor_binding()
    assert result.execution_request.executor_binding.capability_identity == (
        "capability:executor"
    )


def test_s2a_07_worktree_starts_at_exact_source_baseline(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    _, preparation, baseline, spine, attempt = attempt_facts
    (git_repository / "AI_context.md").write_text("new head\n", encoding="utf-8")
    _git(git_repository, "add", "AI_context.md")
    _git(git_repository, "commit", "-m", "advance after baseline")
    package = _package(preparation, spine, git_repository)

    result = _prepare(preparation, attempt, package, git_repository, tmp_path / "workspaces")

    workspace = result.preparation.workspace.workspace_path
    assert _git(workspace, "rev-parse", "HEAD") == baseline.repository_revision
    assert _git(git_repository, "rev-parse", "HEAD") != baseline.repository_revision


def test_s2a_08_retry_attempts_use_distinct_mutable_workspaces(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    runtime, preparation, _, spine, first_attempt = attempt_facts
    package = _package(preparation, spine, git_repository)
    first = _prepare(
        preparation,
        first_attempt,
        package,
        git_repository,
        tmp_path / "workspaces",
    )
    (first.preparation.workspace.workspace_path / "attempt-only.txt").write_text(
        "EA1 mutation\n",
        encoding="utf-8",
    )
    second_attempt = runtime.retry_attempt(first_attempt.id)

    second = _prepare(
        preparation,
        second_attempt,
        package,
        git_repository,
        tmp_path / "workspaces",
    )

    assert first.preparation.workspace.workspace_identity != (
        second.preparation.workspace.workspace_identity
    )
    assert first.preparation.workspace.workspace_path != (
        second.preparation.workspace.workspace_path
    )
    assert not (second.preparation.workspace.workspace_path / "attempt-only.txt").exists()


def test_s2a_09_worktree_preparation_and_mutation_do_not_advance_ref(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    _, preparation, _, spine, attempt = attempt_facts
    package = _package(preparation, spine, git_repository)
    before = _git(git_repository, "rev-parse", "refs/heads/main")

    result = _prepare(preparation, attempt, package, git_repository, tmp_path / "workspaces")
    (result.preparation.workspace.workspace_path / "output.md").write_text(
        "isolated mutation\n",
        encoding="utf-8",
    )

    assert _git(git_repository, "rev-parse", "refs/heads/main") == before


def test_s2a_10_duplicate_preparation_reconciles_one_binding(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
    postgres_database: Database,
) -> None:
    _, preparation, _, spine, attempt = attempt_facts
    package = _package(preparation, spine, git_repository)
    root = tmp_path / "workspaces"

    first = _prepare(preparation, attempt, package, git_repository, root)
    second = _prepare(preparation, attempt, package, git_repository, root)

    assert second.preparation == first.preparation
    assert _count(postgres_database, attempt_preparations) == 1
    assert len(_git(git_repository, "worktree", "list", "--porcelain").split("worktree ")) == 3


def test_s2a_11_prepared_request_has_all_exact_bindings(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    _, preparation, baseline, spine, attempt = attempt_facts
    package = _package(preparation, spine, git_repository)

    result = _prepare(preparation, attempt, package, git_repository, tmp_path / "workspaces")
    request = result.execution_request

    assert request.attempt_id == attempt.id
    assert request.generation == attempt.generation
    assert request.production_run_id == spine.run.id
    assert request.work_unit_id == spine.work_unit.id
    assert request.plan_revision_id == spine.plan_revision.id
    assert request.source_baseline_id == baseline.id
    assert request.context_package_id == package.id
    assert request.executor_binding == _executor_binding()
    assert request.workspace.source_revision == baseline.repository_revision
    assert preparation.is_execution_ready(attempt.id) is True
    assert spine.work_unit.condition.value == "PROPOSED"


def test_s2a_12_missing_context_rejects_without_false_readiness(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
    postgres_database: Database,
) -> None:
    _, preparation, _, _, attempt = attempt_facts
    workspace_root = tmp_path / "workspaces"

    with pytest.raises(RuntimeRecordNotFound, match="Context Package"):
        preparation.prepare_attempt(
            attempt.id,
            uuid4(),
            _executor_binding(),
            git_repository,
            workspace_root,
        )

    assert preparation.is_execution_ready(attempt.id) is False
    assert _count(postgres_database, attempt_preparations) == 0
    assert not workspace_root.exists()


def test_s2a_13_stale_generation_cannot_be_prepared(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    runtime, preparation, _, spine, first_attempt = attempt_facts
    package = _package(preparation, spine, git_repository)
    runtime.retry_attempt(first_attempt.id)

    with pytest.raises(RuntimeInvariantViolation, match="current Attempt"):
        _prepare(
            preparation,
            first_attempt,
            package,
            git_repository,
            tmp_path / "workspaces",
        )

    assert preparation.is_execution_ready(first_attempt.id) is False


def test_s2a_14_mismatched_plan_binding_is_rejected_not_rebound(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
    postgres_database: Database,
) -> None:
    runtime, preparation, _, spine, attempt = attempt_facts
    other_spine = runtime.create_initial_runtime_spine(_run_request())
    package = _package(preparation, spine, git_repository)
    with postgres_database.engine.begin() as connection:
        connection.execute(
            update(execution_attempts)
            .where(execution_attempts.c.id == attempt.id)
            .values(plan_revision_id=other_spine.plan_revision.id)
        )

    with pytest.raises(RuntimeInvariantViolation, match="Plan/Baseline"):
        _prepare(
            preparation,
            attempt,
            package,
            git_repository,
            tmp_path / "workspaces",
        )

    assert _count(postgres_database, attempt_preparations) == 0


def test_s2a_15_preparation_has_no_executor_dispatch_path(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    _, preparation, _, spine, attempt = attempt_facts
    package = _package(preparation, spine, git_repository)

    _prepare(preparation, attempt, package, git_repository, tmp_path / "workspaces")

    source = python_inspect.getsource(PreparationService)
    assert ".dispatch(" not in source
    assert not hasattr(preparation, "executor")


def test_s2a_16_workspace_before_db_failure_is_reconciled_safely(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
    postgres_database: Database,
    monkeypatch,
) -> None:
    _, preparation, _, spine, attempt = attempt_facts
    package = _package(preparation, spine, git_repository)
    root = tmp_path / "workspaces"
    original = RuntimeStore.insert_attempt_preparation

    def fail_insert(*args, **kwargs) -> None:
        raise RuntimeError("injected preparation persistence failure")

    monkeypatch.setattr(RuntimeStore, "insert_attempt_preparation", fail_insert)
    with pytest.raises(RuntimeError, match="injected preparation persistence failure"):
        _prepare(preparation, attempt, package, git_repository, root)

    workspace = root / str(attempt.id)
    assert workspace.exists()
    assert _count(postgres_database, attempt_preparations) == 0
    monkeypatch.setattr(RuntimeStore, "insert_attempt_preparation", original)

    recovered = _prepare(preparation, attempt, package, git_repository, root)

    assert recovered.preparation.workspace.workspace_path == workspace.resolve()
    assert _count(postgres_database, attempt_preparations) == 1


def test_s2a_17_preparation_history_is_durable_without_attempt_rewrite(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
    postgres_database: Database,
) -> None:
    _, preparation, _, spine, attempt = attempt_facts
    original_attempt = attempt.model_dump()
    package = _package(preparation, spine, git_repository)
    _prepare(preparation, attempt, package, git_repository, tmp_path / "workspaces")

    with postgres_database.unit_of_work() as unit_of_work:
        store = RuntimeStore(unit_of_work.session)
        history = store.transitions()
        durable_attempt = store.attempt(attempt.id)

    assert "CONTEXT_PACKAGE_ASSEMBLED" in [entry.reason for entry in history]
    assert "ATTEMPT_PREPARATION_BOUND" in [entry.reason for entry in history]
    assert durable_attempt is not None
    assert durable_attempt.model_dump() == original_attempt


def test_s2a_18_s1_spine_remains_intact_after_preparation(
    attempt_facts,
    git_repository: Path,
    tmp_path: Path,
) -> None:
    runtime, preparation, baseline, spine, attempt = attempt_facts
    package = _package(preparation, spine, git_repository)
    _prepare(preparation, attempt, package, git_repository, tmp_path / "workspaces")

    inspected = runtime.inspect_run(spine.run.id)
    durable_attempt = runtime.get_attempt(attempt.id)

    assert runtime.current_baseline().id == baseline.id
    assert inspected.run.id == spine.run.id
    assert inspected.plan_revision.id == spine.plan_revision.id
    assert inspected.work_unit.condition.value == "PROPOSED"
    assert durable_attempt.condition.value == "CREATED"
