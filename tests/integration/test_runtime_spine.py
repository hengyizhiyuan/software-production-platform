from collections.abc import Iterator
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, inspect, select

from spg.application.runtime import RuntimeService
from spg.cli import main
from spg.domain.runtime import (
    AttemptRequest,
    BootstrapAlreadyInitialized,
    BootstrapRequest,
    CompletionContract,
    InitialRunRequest,
    ProductionHorizon,
    RuntimeInvariantViolation,
)
from spg.infrastructure.persistence import (
    Database,
    OptimisticConcurrencyConflict,
)
from spg.infrastructure.persistence.runtime_schema import (
    current_trusted_baseline_pointer,
    execution_attempts,
    governance_records,
    plan_revisions,
    production_runs,
    production_snapshots,
    production_work_units,
    runtime_tables,
    transition_history,
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
    (repository / "architecture.md").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "architecture.md")
    _git(repository, "commit", "-m", "baseline")
    return repository


@pytest.fixture
def runtime(postgres_database: Database) -> RuntimeService:
    return RuntimeService(postgres_database)


@pytest.fixture
def bootstrapped_runtime(
    runtime: RuntimeService,
    git_repository: Path,
) -> tuple[RuntimeService, Path]:
    _bootstrap(runtime, git_repository)
    return runtime, git_repository


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _bootstrap(runtime: RuntimeService, repository: Path):
    return runtime.bootstrap_trusted_baseline(
        BootstrapRequest(
            repository_path=repository,
            repository_identity="test://governed-repository",
            repository_ref="refs/heads/main",
            authority_identity="architecture-lead:test",
            scope={"slice": "S1-C"},
            rationale="controlled test baseline",
        )
    )


def _run_request() -> InitialRunRequest:
    return InitialRunRequest(
        intent_ref="intent:test:documentation-001",
        goal="Update the governed architecture record",
        production_horizon=ProductionHorizon.DOCUMENTATION,
        initial_work_unit_objective="Produce the documentation update",
        completion_contract=CompletionContract(
            required_outputs=("architecture record",),
            required_changes=("record the admitted decision",),
            forbidden_changes=("production code",),
            verification_obligations=("review document diff",),
        ),
    )


def _truncate_runtime(database: Database) -> None:
    table_names = ", ".join(f'"{name}"' for name in RUNTIME_TABLE_NAMES)
    with database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {table_names} CASCADE")


def _count(database: Database, table) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table))


def _runtime_counts(database: Database) -> dict[str, int]:
    return {table.name: _count(database, table) for table in runtime_tables}


def test_rs_01_migration_upgrade_creates_exact_s1c_schema(
    postgres_database: Database,
) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "base")
    assert not (RUNTIME_TABLE_NAMES & set(inspect(postgres_database.engine).get_table_names()))

    command.upgrade(config, "head")

    table_names = set(inspect(postgres_database.engine).get_table_names())
    assert RUNTIME_TABLE_NAMES <= table_names
    assert not {
        "work_products",
        "verifications",
        "production_issues",
        "external_effects",
        "provider_registry",
    } & table_names


def test_rs_02_migration_downgrade_and_reupgrade(postgres_database: Database) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    assert RUNTIME_TABLE_NAMES <= set(
        inspect(postgres_database.engine).get_table_names()
    )


def test_rs_03_explicit_bootstrap_records_exact_revision_and_authority(
    runtime: RuntimeService,
    git_repository: Path,
) -> None:
    exact_revision = _git(git_repository, "rev-parse", "refs/heads/main^{commit}")

    result = _bootstrap(runtime, git_repository)

    assert result.snapshot.repository_revision == exact_revision
    assert result.snapshot.repository_ref == "refs/heads/main"
    assert result.snapshot.source_baseline_id is None
    assert result.pointer.snapshot_id == result.snapshot.id
    assert result.pointer.version == 0
    assert result.governance.decision_type == "BOOTSTRAP_INITIAL_BASELINE"
    assert result.governance.authority_identity == "architecture-lead:test"
    assert result.governance.subject_identity == str(result.snapshot.id)


def test_rs_04_bootstrap_is_atomic_on_injected_failure(
    runtime: RuntimeService,
    git_repository: Path,
    postgres_database: Database,
    monkeypatch,
) -> None:
    def fail_transition(*args, **kwargs) -> None:
        raise RuntimeError("injected bootstrap failure")

    monkeypatch.setattr(RuntimeStore, "insert_transition", fail_transition)
    with pytest.raises(RuntimeError, match="injected bootstrap failure"):
        _bootstrap(runtime, git_repository)

    assert _runtime_counts(postgres_database) == {
        name: 0 for name in RUNTIME_TABLE_NAMES
    }


def test_rs_05_bootstrap_is_single_initialization_and_preserves_b0(
    runtime: RuntimeService,
    git_repository: Path,
    postgres_database: Database,
) -> None:
    first = _bootstrap(runtime, git_repository)
    before = _runtime_counts(postgres_database)
    (git_repository / "later-uncommitted.md").write_text(
        "must not trigger repository observation\n",
        encoding="utf-8",
    )

    with pytest.raises(BootstrapAlreadyInitialized):
        _bootstrap(runtime, git_repository)

    assert runtime.current_baseline().id == first.snapshot.id
    assert _runtime_counts(postgres_database) == before


def test_rs_06_baseline_is_not_a_dynamic_git_head_alias(
    runtime: RuntimeService,
    git_repository: Path,
) -> None:
    baseline = _bootstrap(runtime, git_repository).snapshot
    (git_repository / "architecture.md").write_text("advanced\n", encoding="utf-8")
    _git(git_repository, "add", "architecture.md")
    _git(git_repository, "commit", "-m", "advance head")
    advanced_head = _git(git_repository, "rev-parse", "HEAD")

    current = runtime.current_baseline()

    assert advanced_head != baseline.repository_revision
    assert current.id == baseline.id
    assert current.repository_revision == baseline.repository_revision


def test_rs_07_run_binds_intent_baseline_and_documentation_horizon(
    bootstrapped_runtime: tuple[RuntimeService, Path],
) -> None:
    runtime, _ = bootstrapped_runtime
    baseline = runtime.current_baseline()

    spine = runtime.create_initial_runtime_spine(_run_request())

    assert spine.run.intent_ref == "intent:test:documentation-001"
    assert spine.run.source_baseline_id == baseline.id
    assert spine.run.production_horizon is ProductionHorizon.DOCUMENTATION
    assert spine.run.condition.value == "OPEN"
    assert spine.run.version == 1


def test_rs_08_initial_plan_is_revision_one_and_schema_enforces_uniqueness(
    bootstrapped_runtime: tuple[RuntimeService, Path],
    postgres_database: Database,
) -> None:
    runtime, _ = bootstrapped_runtime
    spine = runtime.create_initial_runtime_spine(_run_request())

    assert spine.plan_revision.revision_number == 1
    assert spine.plan_revision.production_run_id == spine.run.id
    assert spine.plan_revision.source_baseline_id == spine.run.source_baseline_id
    assert spine.run.current_plan_revision_id == spine.plan_revision.id
    constraints = inspect(postgres_database.engine).get_unique_constraints(
        "plan_revisions"
    )
    indexes = inspect(postgres_database.engine).get_indexes("plan_revisions")
    assert any(
        set(item["column_names"]) == {"production_run_id", "revision_number"}
        for item in constraints
    )
    assert any(
        item["name"] == "uq_plan_revisions_one_active_per_run"
        and item["unique"]
        for item in indexes
    )


def test_rs_09_pwu_binds_spine_and_durable_completion_contract(
    bootstrapped_runtime: tuple[RuntimeService, Path],
) -> None:
    runtime, _ = bootstrapped_runtime
    spine = runtime.create_initial_runtime_spine(_run_request())
    inspected = runtime.inspect_run(spine.run.id)

    assert inspected.work_unit.production_run_id == spine.run.id
    assert inspected.work_unit.plan_revision_id == spine.plan_revision.id
    assert inspected.work_unit.source_baseline_id == spine.run.source_baseline_id
    assert inspected.work_unit.condition.value == "PROPOSED"
    assert inspected.work_unit.current_execution_generation == 0
    assert inspected.work_unit.completion_contract.required_outputs == (
        "architecture record",
    )


def test_rs_10_documentation_runtime_spine_has_no_code_artifact_dependency(
    bootstrapped_runtime: tuple[RuntimeService, Path],
) -> None:
    runtime, _ = bootstrapped_runtime
    spine = runtime.create_initial_runtime_spine(_run_request())

    assert spine.run.production_horizon.value == "DOCUMENTATION"
    assert spine.work_unit.objective == "Produce the documentation update"
    assert "code" not in type(spine.work_unit).model_fields


def test_rs_11_initial_run_construction_is_atomic_and_preserves_prior_history(
    bootstrapped_runtime: tuple[RuntimeService, Path],
    postgres_database: Database,
    monkeypatch,
) -> None:
    runtime, _ = bootstrapped_runtime
    before = _runtime_counts(postgres_database)
    original = RuntimeStore.insert_transition
    calls = 0

    def fail_second_transition(self, values) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected run construction failure")
        original(self, values)

    monkeypatch.setattr(RuntimeStore, "insert_transition", fail_second_transition)
    with pytest.raises(RuntimeError, match="injected run construction failure"):
        runtime.create_initial_runtime_spine(_run_request())

    assert _runtime_counts(postgres_database) == before
    assert _count(postgres_database, production_snapshots) == 1
    assert _count(postgres_database, transition_history) == 1


def test_rs_12_attempt_has_independent_identity_and_exact_bindings(
    bootstrapped_runtime: tuple[RuntimeService, Path],
) -> None:
    runtime, _ = bootstrapped_runtime
    spine = runtime.create_initial_runtime_spine(_run_request())

    attempt = runtime.create_initial_attempt(
        spine.work_unit.id,
        AttemptRequest(
            context_ref="context:test:1",
            provider_ref="executor-profile:test",
            workspace_ref="workspace:test",
        ),
    )

    assert attempt.id not in {spine.run.id, spine.plan_revision.id, spine.work_unit.id}
    assert attempt.work_unit_id == spine.work_unit.id
    assert attempt.plan_revision_id == spine.plan_revision.id
    assert attempt.source_baseline_id == spine.run.source_baseline_id
    assert attempt.generation == 1
    assert attempt.condition.value == "CREATED"


def test_rs_13_retry_creates_new_identity_and_generation_lineage(
    bootstrapped_runtime: tuple[RuntimeService, Path],
) -> None:
    runtime, _ = bootstrapped_runtime
    spine = runtime.create_initial_runtime_spine(_run_request())
    first = runtime.create_initial_attempt(spine.work_unit.id)

    second = runtime.retry_attempt(first.id)

    assert second.id != first.id
    assert second.generation == 2
    assert second.retry_of == first.id


def test_rs_14_retry_does_not_rewrite_historical_attempt(
    bootstrapped_runtime: tuple[RuntimeService, Path],
) -> None:
    runtime, _ = bootstrapped_runtime
    spine = runtime.create_initial_runtime_spine(_run_request())
    first = runtime.create_initial_attempt(
        spine.work_unit.id,
        AttemptRequest(provider_ref="executor-profile:original"),
    )
    original = first.model_dump()

    runtime.retry_attempt(
        first.id,
        AttemptRequest(provider_ref="executor-profile:retry"),
    )

    assert runtime.get_attempt(first.id).model_dump() == original


def test_rs_15_stale_generation_detection_and_retry_guard(
    bootstrapped_runtime: tuple[RuntimeService, Path],
) -> None:
    runtime, _ = bootstrapped_runtime
    spine = runtime.create_initial_runtime_spine(_run_request())
    first = runtime.create_initial_attempt(spine.work_unit.id)
    second = runtime.retry_attempt(first.id)

    assert runtime.attempt_is_current(first.id) is False
    assert runtime.attempt_is_current(second.id) is True
    with pytest.raises(RuntimeInvariantViolation, match="only the current Attempt"):
        runtime.retry_attempt(first.id)


def test_rs_16_transition_history_explains_material_creations(
    bootstrapped_runtime: tuple[RuntimeService, Path],
    postgres_database: Database,
) -> None:
    runtime, _ = bootstrapped_runtime
    spine = runtime.create_initial_runtime_spine(_run_request())
    first = runtime.create_initial_attempt(spine.work_unit.id)
    runtime.retry_attempt(first.id)

    with postgres_database.unit_of_work() as unit_of_work:
        history = RuntimeStore(unit_of_work.session).transitions()

    assert [entry.reason for entry in history] == [
        "BOOTSTRAP_TRUSTED_BASELINE",
        "RUN_CREATED",
        "INITIAL_PLAN_ACTIVATED",
        "WORK_UNIT_PROPOSED",
        "INITIAL_ATTEMPT_CREATED",
        "ATTEMPT_RETRY_CREATED",
    ]


def test_rs_17_baseline_pointer_has_optimistic_version_foundation(
    bootstrapped_runtime: tuple[RuntimeService, Path],
    postgres_database: Database,
) -> None:
    runtime, _ = bootstrapped_runtime
    baseline = runtime.current_baseline()

    with pytest.raises(OptimisticConcurrencyConflict):
        with postgres_database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            assert store.update_baseline_pointer(0, baseline.id) == 1
            store.update_baseline_pointer(0, baseline.id)

    with postgres_database.engine.connect() as connection:
        pointer = connection.execute(select(current_trusted_baseline_pointer)).one()
    assert pointer.snapshot_id == baseline.id
    assert pointer.version == 0


def test_s1c_cli_explicitly_bootstraps_creates_and_inspects_run(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    database_url = postgres_database.engine.url.render_as_string(hide_password=False)
    monkeypatch.setenv("SPG_DATABASE_URL", database_url)

    assert main(
        [
            "bootstrap",
            "--repository-path",
            str(git_repository),
            "--repository-identity",
            "test://cli-repository",
            "--repository-ref",
            "refs/heads/main",
            "--authority-identity",
            "architecture-lead:cli-test",
        ]
    ) == 0
    bootstrap_output = json.loads(capsys.readouterr().out)
    assert bootstrap_output["snapshot"]["repository_revision"] == _git(
        git_repository,
        "rev-parse",
        "HEAD",
    )

    assert main(["baseline", "show"]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == bootstrap_output["snapshot"]["id"]

    contract_file = tmp_path / "completion-contract.json"
    contract_file.write_text(
        json.dumps(
            {
                "required_outputs": ["documentation update"],
                "verification_obligations": ["review document diff"],
            }
        ),
        encoding="utf-8",
    )
    assert main(
        [
            "run",
            "create",
            "--intent-ref",
            "intent:test:cli",
            "--goal",
            "Update documentation",
            "--horizon",
            "DOCUMENTATION",
            "--pwu-objective",
            "Produce documentation update",
            "--completion-contract",
            str(contract_file),
        ]
    ) == 0
    run_output = json.loads(capsys.readouterr().out)

    assert main(["run", "inspect", run_output["run"]["id"]]) == 0
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["run"]["id"] == run_output["run"]["id"]
