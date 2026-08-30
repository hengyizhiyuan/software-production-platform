"""S6-B1 deterministic contracts plus one explicitly gated real SDK probe."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
from threading import Event
from types import SimpleNamespace

from alembic import command
from alembic.config import Config
from openai_codex import ApprovalMode, Codex, Sandbox
import pytest
from sqlalchemy import func, inspect, select

from spg.application.execution import ExecutionService
from spg.application.materialization import ExecutionInputMaterializationService
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
    RuntimeInvariantViolation,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.runtime_schema import (
    baseline_candidates,
    completion_evaluations,
    materialized_execution_inputs,
    production_admissibility_records,
    runtime_tables,
    runtime_commits,
    verification_records,
)
from spg.providers.codex_sdk_executor import CodexSdkExecutor
from spg.providers.deterministic_executor import (
    DeterministicExecutionSpecification,
    DeterministicTestExecutor,
)


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TABLE_NAMES = {table.name for table in runtime_tables}
TARGET_PATH = "docs/codex_real_execution_probe.md"
BEFORE_CONTENT = "S6-B1 marker: BEFORE\n"
AFTER_CONTENT = "S6-B1 marker: AFTER\n"
INSTRUCTION = (
    "Change exactly the specified marker in "
    "docs/codex_real_execution_probe.md from 'S6-B1 marker: BEFORE' to "
    "'S6-B1 marker: AFTER'. Do not modify any other file. Do not commit. "
    "Do not push. Stop after making the requested file change."
)


@dataclass(frozen=True)
class S6B1Facts:
    database: Database
    runtime: RuntimeService
    preparation: PreparationService
    materialization: ExecutionInputMaterializationService
    execution: ExecutionService
    repository: Path
    baseline: object
    spine: object
    attempt: object
    prepared: object
    materialized_input: object


class FakeStatus:
    def __init__(self, value: str) -> None:
        self.value = value


class FakeTurnHandle:
    id = "turn-s6b1-test"

    def __init__(self, owner, status: str, mutation=None) -> None:
        self.owner = owner
        self.status = status
        self.mutation = mutation

    def run(self):
        if self.mutation is not None:
            self.mutation(Path(self.owner.run_kwargs["cwd"]))
        if self.owner.block_until_interrupt:
            self.owner.run_started.set()
            self.owner.interrupted.wait()
        return SimpleNamespace(
            id=self.owner.terminal_turn_id,
            status=FakeStatus(self.status),
            error=None,
            started_at=1_800_000_000,
            completed_at=1_800_000_001,
            duration_ms=1_000,
            final_response="provider claims the requested change is complete",
        )

    def interrupt(self):
        self.owner.interrupt_count += 1
        self.owner.interrupted.set()
        return SimpleNamespace()


class FakeThread:
    id = "thread-s6b1-test"

    def __init__(self, owner, status: str, mutation=None) -> None:
        self.owner = owner
        self.status = status
        self.mutation = mutation

    def turn(self, input_content: str, **kwargs):
        if self.owner.turn_start_error is not None:
            raise self.owner.turn_start_error
        self.owner.run_input = input_content
        self.owner.run_kwargs = kwargs
        return FakeTurnHandle(self.owner, self.status, self.mutation)


class FakeCodex:
    def __init__(
        self,
        *,
        status: str = "completed",
        mutation=None,
        block_until_interrupt: bool = False,
        start_error: Exception | None = None,
        turn_start_error: Exception | None = None,
        terminal_turn_id: str = "turn-s6b1-test",
    ) -> None:
        self.status = status
        self.mutation = mutation
        self.block_until_interrupt = block_until_interrupt
        self.start_error = start_error
        self.turn_start_error = turn_start_error
        self.terminal_turn_id = terminal_turn_id
        self.thread_start_kwargs = None
        self.run_kwargs = None
        self.run_input = None
        self.resume_count = 0
        self.interrupt_count = 0
        self.run_started = Event()
        self.interrupted = Event()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def thread_start(self, **kwargs):
        if self.start_error is not None:
            raise self.start_error
        self.thread_start_kwargs = kwargs
        return FakeThread(self, self.status, self.mutation)

    def thread_resume(self, *_args, **_kwargs):
        self.resume_count += 1
        raise AssertionError("S6-B1 must not resume a Provider thread")


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
def s6b1_facts(postgres_database: Database, tmp_path: Path) -> S6B1Facts:
    repository = tmp_path / "authoritative-repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "docs").mkdir()
    (repository / "AI_context.md").write_text(
        "S6-B1 admitted project context\n", encoding="utf-8"
    )
    (repository / "docs" / "contract.md").write_text(
        "Only the declared probe file may change.\n", encoding="utf-8"
    )
    (repository / TARGET_PATH).write_text(BEFORE_CONTENT, encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "S6-B1 probe baseline")

    runtime = RuntimeService(postgres_database)
    preparation = PreparationService(postgres_database)
    execution = ExecutionService(postgres_database, preparation=preparation)
    materialization = ExecutionInputMaterializationService(
        postgres_database,
        preparation=preparation,
    )
    baseline = runtime.bootstrap_trusted_baseline(
        BootstrapRequest(
            repository_path=repository,
            repository_identity="test://s6b1-real-codex",
            repository_ref="refs/heads/main",
            authority_identity="architecture-lead:s6b1",
            scope={"slice": "S6-B1"},
        )
    ).snapshot
    spine = runtime.create_initial_runtime_spine(
        InitialRunRequest(
            intent_ref="intent:s6b1-real-codex-probe",
            goal="Prove one bounded real Codex documentation mutation",
            production_horizon=ProductionHorizon.DOCUMENTATION,
            initial_work_unit_objective=f"Modify only {TARGET_PATH}",
            completion_contract=CompletionContract(
                required_outputs=(TARGET_PATH,),
                required_changes=("replace BEFORE marker with AFTER marker",),
                forbidden_changes=("any other repository path",),
                verification_obligations=("independent repository observation",),
            ),
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
    prepared = preparation.prepare_attempt(
        attempt.id,
        package.id,
        ExecutorBinding(
            binding_ref="binding:codex-sdk-host-spike",
            capability_identity="capability:executor",
            profile_identity="profile:local-fvs-host-spike",
        ),
        repository,
        tmp_path / "attempt-workspaces",
    )
    materialized_input = materialization.materialize(attempt.id, INSTRUCTION)
    return S6B1Facts(
        database=postgres_database,
        runtime=runtime,
        preparation=preparation,
        materialization=materialization,
        execution=execution,
        repository=repository,
        baseline=baseline,
        spine=spine,
        attempt=attempt,
        prepared=prepared,
        materialized_input=materialized_input,
    )


def _adapter(
    facts: S6B1Facts,
    fake: FakeCodex,
    *,
    timeout_seconds: float | None = None,
) -> CodexSdkExecutor:
    return CodexSdkExecutor(
        facts.materialized_input,
        codex_factory=lambda: fake,
        timeout_seconds=timeout_seconds,
    )


def _count(database: Database, table) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table))


def _persisted_provider_report(database: Database, attempt_id):
    with database.unit_of_work() as unit_of_work:
        store = RuntimeStore(unit_of_work.session)
        dispatch = store.execution_dispatch_for_attempt(attempt_id)
        if dispatch is None:
            return None
        return store.provider_execution_report(dispatch.id)


def _provider_evidence(report) -> dict[str, object]:
    metadata = report.metadata
    return {
        "dispatch_id": str(report.dispatch_id),
        "materialized_execution_input_id": metadata.get("input_id"),
        "materialized_execution_input_fingerprint": metadata.get(
            "input_fingerprint"
        ),
        "workspace_identity": metadata.get("workspace_identity"),
        "provider_reference": report.provider_reference,
        "provider_outcome": report.outcome.value,
        "provider_identity_state": metadata.get("provider_identity_state"),
        "thread_id": metadata.get("thread_id"),
        "turn_id": metadata.get("turn_id"),
        "started_at": report.started_at.isoformat(),
        "finished_at": report.finished_at.isoformat(),
        "recorded_at": report.recorded_at.isoformat(),
        "terminal_result_within_timeout": metadata.get(
            "terminal_result_within_timeout"
        ),
        "turn_status": metadata.get("turn_status"),
        "terminal_turn_id": metadata.get("terminal_turn_id"),
        "terminal_identity_matches": metadata.get("terminal_identity_matches"),
        "sdk_started_at": metadata.get("sdk_started_at"),
        "sdk_completed_at": metadata.get("sdk_completed_at"),
        "sdk_duration_ms": metadata.get("sdk_duration_ms"),
        "timeout_at": metadata.get("timeout_at"),
        "interrupt_requested": metadata.get("interrupt_requested", False),
        "post_timeout_status": metadata.get("post_timeout_status"),
        "exception_type": metadata.get("exception_type"),
    }


def _emit_probe_evidence(label: str, evidence: dict[str, object]) -> None:
    print(label + "=" + json.dumps(evidence, sort_keys=True), flush=True)


def _assert_probe_correlation(result, materialized_input) -> None:
    metadata = result.provider_report.metadata
    assert metadata["dispatch_id"] == str(result.dispatch.id)
    assert metadata["input_id"] == str(materialized_input.id)
    assert metadata["input_fingerprint"] == materialized_input.input_fingerprint
    assert metadata["workspace_identity"] == result.dispatch.workspace.workspace_identity
    assert metadata["provider_identity_state"] == "COMPLETE"
    assert metadata["thread_id"]
    assert metadata["turn_id"]


def _assert_safe_production_observation(
    result,
    *,
    authoritative_ref_before: str,
    authoritative_ref_after: str,
    authoritative_status_before: str,
    authoritative_status_after: str,
) -> None:
    assert (
        authoritative_ref_after == authoritative_ref_before
    ), "authoritative repository ref changed"
    assert (
        authoritative_status_after == authoritative_status_before
    ), "authoritative repository working tree changed"
    changed_paths = [
        change.repository_relative_path for change in result.observation.changes
    ]
    unexpected_paths = sorted(set(changed_paths) - {TARGET_PATH})
    assert not unexpected_paths, f"unexpected workspace paths: {unexpected_paths}"
    if changed_paths:
        assert changed_paths == [TARGET_PATH]
        assert result.observation.changes[0].change_type is ArtifactChangeType.MODIFIED
        assert [reference.artifact_path for reference in result.work_products] == [
            TARGET_PATH
        ]
    else:
        assert result.work_products == ()


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _truncate_runtime(database: Database) -> None:
    table_names = ", ".join(f'"{name}"' for name in RUNTIME_TABLE_NAMES)
    with database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {table_names} CASCADE")


def test_s6b1_migration_downgrade_and_reupgrade(postgres_database: Database) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260829_11")
    assert "materialized_execution_inputs" not in inspect(
        postgres_database.engine
    ).get_table_names()
    command.upgrade(config, "head")
    assert "materialized_execution_inputs" in inspect(
        postgres_database.engine
    ).get_table_names()


def test_s6b1_01_materialized_input_binds_exact_prepared_request(
    s6b1_facts: S6B1Facts,
) -> None:
    materialized = s6b1_facts.materialized_input
    assert materialized.prepared_execution_request == s6b1_facts.prepared.execution_request
    assert materialized.attempt_id == s6b1_facts.attempt.id
    assert materialized.generation == s6b1_facts.attempt.generation


def test_s6b1_02_materialized_input_fingerprint_is_stable(
    s6b1_facts: S6B1Facts,
) -> None:
    repeated = s6b1_facts.materialization.materialize(
        s6b1_facts.attempt.id,
        INSTRUCTION,
    )
    assert repeated == s6b1_facts.materialized_input
    assert len(repeated.input_fingerprint) == 64
    assert _count(s6b1_facts.database, materialized_execution_inputs) == 1


def test_s6b1_03_provider_cannot_select_arbitrary_workspace(
    s6b1_facts: S6B1Facts,
) -> None:
    fake = FakeCodex()
    _adapter(s6b1_facts, fake).dispatch(
        SimpleNamespace(
            dispatch_id=s6b1_facts.attempt.id,
            execution=s6b1_facts.prepared.execution_request,
        )
    )
    expected = str(
        s6b1_facts.prepared.execution_request.workspace.workspace_path.resolve()
    )
    assert fake.thread_start_kwargs["cwd"] == expected
    assert fake.run_kwargs["cwd"] == expected


def test_s6b1_04_exact_attempt_generation_workspace_required(
    s6b1_facts: S6B1Facts,
) -> None:
    execution = s6b1_facts.prepared.execution_request
    wrong_workspace = execution.workspace.model_copy(
        update={"workspace_identity": "attempt-worktree:wrong"}
    )
    wrong_execution = execution.model_copy(update={"workspace": wrong_workspace})
    wrong_input = s6b1_facts.materialized_input.model_copy(
        update={"prepared_execution_request": wrong_execution}
    )
    with pytest.raises(RuntimeInvariantViolation, match="Attempt/generation"):
        CodexSdkExecutor(wrong_input, codex_factory=lambda: FakeCodex()).dispatch(
            SimpleNamespace(dispatch_id=s6b1_facts.attempt.id, execution=wrong_execution)
        )


def test_s6b1_05_authoritative_repository_rejected_as_workspace(
    s6b1_facts: S6B1Facts,
) -> None:
    execution = s6b1_facts.prepared.execution_request
    bad_workspace = execution.workspace.model_copy(
        update={"workspace_path": execution.workspace.repository_path}
    )
    bad_execution = execution.model_copy(update={"workspace": bad_workspace})
    bad_input = s6b1_facts.materialized_input.model_copy(
        update={"prepared_execution_request": bad_execution}
    )
    with pytest.raises(RuntimeInvariantViolation, match="authoritative repository"):
        CodexSdkExecutor(bad_input, codex_factory=lambda: FakeCodex()).dispatch(
            SimpleNamespace(dispatch_id=s6b1_facts.attempt.id, execution=bad_execution)
        )


def test_s6b1_06_codex_adapter_conforms_to_executor_contract(
    s6b1_facts: S6B1Facts,
) -> None:
    assert callable(_adapter(s6b1_facts, FakeCodex()).dispatch)


def test_s6b1_07_provider_success_remains_only_claim(
    s6b1_facts: S6B1Facts,
) -> None:
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex()),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert s6b1_facts.runtime.inspect_run(
        s6b1_facts.spine.run.id
    ).work_unit.condition.value == "PROPOSED"
    assert s6b1_facts.runtime.get_attempt(
        s6b1_facts.attempt.id
    ).condition.value == "CREATED"


def test_s6b1_08_provider_failure_maps_conservatively(
    s6b1_facts: S6B1Facts,
) -> None:
    result = _adapter(s6b1_facts, FakeCodex(status="failed")).dispatch(
        SimpleNamespace(
            dispatch_id=s6b1_facts.attempt.id,
            execution=s6b1_facts.prepared.execution_request,
        )
    )
    assert result.outcome is ProviderReportedOutcome.FAILURE


def test_s6b1_09_uncertain_interruption_maps_unknown(
    s6b1_facts: S6B1Facts,
) -> None:
    result = _adapter(s6b1_facts, FakeCodex(status="interrupted")).dispatch(
        SimpleNamespace(
            dispatch_id=s6b1_facts.attempt.id,
            execution=s6b1_facts.prepared.execution_request,
        )
    )
    assert result.outcome is ProviderReportedOutcome.UNKNOWN


def test_s6b1_10_provider_identity_binds_exact_dispatch(
    s6b1_facts: S6B1Facts,
) -> None:
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex()),
    )
    assert result.provider_report.dispatch_id == result.dispatch.id
    assert result.provider_report.provider_reference == (
        "codex-sdk:thread:thread-s6b1-test:turn:turn-s6b1-test"
    )
    assert result.provider_report.metadata["input_fingerprint"] == (
        s6b1_facts.materialized_input.input_fingerprint
    )


def test_s6b1_11_observation_does_not_trust_provider_response(
    s6b1_facts: S6B1Facts,
) -> None:
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex()),
    )
    assert "claims" in (result.provider_report.summary or "")
    assert result.observation.changes == ()
    assert result.work_products == ()


def test_s6b1_12_observed_work_can_disagree_with_provider_claim(
    s6b1_facts: S6B1Facts,
) -> None:
    def mutate(workspace: Path) -> None:
        (workspace / TARGET_PATH).write_text(AFTER_CONTENT, encoding="utf-8")

    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex(status="failed", mutation=mutate)),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.FAILURE
    assert [item.artifact_path for item in result.work_products] == [TARGET_PATH]


def test_s6b1_13_provider_has_no_completion_or_satisfaction_authority(
    s6b1_facts: S6B1Facts,
) -> None:
    s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex()),
    )
    assert _count(s6b1_facts.database, completion_evaluations) == 0
    assert _count(s6b1_facts.database, verification_records) == 0
    assert _count(s6b1_facts.database, production_admissibility_records) == 0


def test_s6b1_14_provider_has_no_candidate_or_baseline_authority(
    s6b1_facts: S6B1Facts,
) -> None:
    before = s6b1_facts.runtime.current_baseline()
    s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex()),
    )
    assert _count(s6b1_facts.database, baseline_candidates) == 0
    assert _count(s6b1_facts.database, runtime_commits) == 0
    assert s6b1_facts.runtime.current_baseline() == before


def test_s6b1_15_provider_does_not_lookup_execution_intent_in_database(
    s6b1_facts: S6B1Facts,
) -> None:
    fake = FakeCodex()
    adapter = _adapter(s6b1_facts, fake)
    assert not hasattr(adapter, "database")
    adapter.dispatch(
        SimpleNamespace(
            dispatch_id=s6b1_facts.attempt.id,
            execution=s6b1_facts.prepared.execution_request,
        )
    )
    assert fake.run_input == s6b1_facts.materialized_input.provider_input()


def test_s6b1_16_provider_resume_is_not_used(s6b1_facts: S6B1Facts) -> None:
    fake = FakeCodex()
    _adapter(s6b1_facts, fake).dispatch(
        SimpleNamespace(
            dispatch_id=s6b1_facts.attempt.id,
            execution=s6b1_facts.prepared.execution_request,
        )
    )
    assert fake.resume_count == 0


def test_s6b1_17_spike_never_uses_full_access_sandbox(
    s6b1_facts: S6B1Facts,
) -> None:
    fake = FakeCodex()
    _adapter(s6b1_facts, fake).dispatch(
        SimpleNamespace(
            dispatch_id=s6b1_facts.attempt.id,
            execution=s6b1_facts.prepared.execution_request,
        )
    )
    assert fake.thread_start_kwargs["sandbox"] is Sandbox.workspace_write
    assert fake.run_kwargs["sandbox"] is Sandbox.workspace_write
    assert fake.thread_start_kwargs["approval_mode"] is ApprovalMode.deny_all


def test_s6b1_18_deterministic_executor_regression_remains_valid(
    s6b1_facts: S6B1Facts,
) -> None:
    deterministic = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            reported_outcome=ProviderReportedOutcome.SUCCESS,
            summary="deterministic regression",
        )
    )
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        deterministic,
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert deterministic.dispatch_count == 1


def test_s6b1_19_documentation_horizon_pwu_remains_valid(
    s6b1_facts: S6B1Facts,
) -> None:
    inspected = s6b1_facts.runtime.inspect_run(s6b1_facts.spine.run.id)
    assert inspected.run.production_horizon is ProductionHorizon.DOCUMENTATION
    assert inspected.work_unit.objective == f"Modify only {TARGET_PATH}"


def test_s6b1_20_no_s6c_or_fvs_closure_leakage(
    s6b1_facts: S6B1Facts,
) -> None:
    _adapter(s6b1_facts, FakeCodex()).dispatch(
        SimpleNamespace(
            dispatch_id=s6b1_facts.attempt.id,
            execution=s6b1_facts.prepared.execution_request,
        )
    )
    assert _count(s6b1_facts.database, completion_evaluations) == 0
    assert _count(s6b1_facts.database, baseline_candidates) == 0
    assert _count(s6b1_facts.database, runtime_commits) == 0


def test_term_01_public_terminal_success_maps_success(
    s6b1_facts: S6B1Facts,
) -> None:
    result = _adapter(s6b1_facts, FakeCodex(status="completed")).dispatch(
        SimpleNamespace(
            dispatch_id=s6b1_facts.attempt.id,
            execution=s6b1_facts.prepared.execution_request,
        )
    )
    assert result.outcome is ProviderReportedOutcome.SUCCESS
    assert result.metadata["terminal_result_within_timeout"] is True
    assert result.metadata["turn_status"] == "completed"


def test_term_02_public_terminal_failure_maps_failure(
    s6b1_facts: S6B1Facts,
) -> None:
    result = _adapter(s6b1_facts, FakeCodex(status="failed")).dispatch(
        SimpleNamespace(
            dispatch_id=s6b1_facts.attempt.id,
            execution=s6b1_facts.prepared.execution_request,
        )
    )
    assert result.outcome is ProviderReportedOutcome.FAILURE
    assert result.metadata["turn_status"] == "failed"


def test_term_03_timeout_maps_unknown(s6b1_facts: S6B1Facts) -> None:
    fake = FakeCodex(status="interrupted", block_until_interrupt=True)
    result = _adapter(
        s6b1_facts,
        fake,
        timeout_seconds=0.01,
    ).dispatch(
        SimpleNamespace(
            dispatch_id=s6b1_facts.attempt.id,
            execution=s6b1_facts.prepared.execution_request,
        )
    )
    assert result.outcome is ProviderReportedOutcome.UNKNOWN
    assert result.metadata["terminal_result_within_timeout"] is False
    assert result.metadata["post_timeout_status"] == "interrupted"
    assert fake.interrupt_count == 1


def test_term_04_observed_change_does_not_convert_unknown_to_success(
    s6b1_facts: S6B1Facts,
) -> None:
    def mutate(workspace: Path) -> None:
        (workspace / TARGET_PATH).write_text(AFTER_CONTENT, encoding="utf-8")

    fake = FakeCodex(
        status="interrupted",
        mutation=mutate,
        block_until_interrupt=True,
    )
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, fake, timeout_seconds=0.01),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.UNKNOWN
    assert [item.artifact_path for item in result.work_products] == [TARGET_PATH]


def test_term_05_available_provider_identity_binds_exact_dispatch(
    s6b1_facts: S6B1Facts,
) -> None:
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex()),
    )
    assert result.provider_report.dispatch_id == result.dispatch.id
    assert result.provider_report.metadata["dispatch_id"] == str(result.dispatch.id)
    assert result.provider_report.metadata["provider_identity_state"] == "COMPLETE"
    assert result.provider_report.metadata["thread_id"] == "thread-s6b1-test"
    assert result.provider_report.metadata["turn_id"] == "turn-s6b1-test"


def test_term_06_missing_identity_is_represented_truthfully(
    s6b1_facts: S6B1Facts,
) -> None:
    result = _adapter(
        s6b1_facts,
        FakeCodex(start_error=RuntimeError("thread identity unavailable")),
    ).dispatch(
        SimpleNamespace(
            dispatch_id=s6b1_facts.attempt.id,
            execution=s6b1_facts.prepared.execution_request,
        )
    )
    assert result.outcome is ProviderReportedOutcome.UNKNOWN
    assert result.provider_reference == f"codex-sdk:dispatch:{s6b1_facts.attempt.id}"
    assert result.metadata["provider_identity_state"] == "MISSING"
    assert "thread_id" not in result.metadata
    assert "turn_id" not in result.metadata


def test_term_07_no_completion_authority_is_granted(
    s6b1_facts: S6B1Facts,
) -> None:
    s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex()),
    )
    assert _count(s6b1_facts.database, completion_evaluations) == 0
    assert _count(s6b1_facts.database, verification_records) == 0
    assert _count(s6b1_facts.database, production_admissibility_records) == 0


def test_term_08_no_resume_semantics_are_introduced(
    s6b1_facts: S6B1Facts,
) -> None:
    fake = FakeCodex(status="interrupted", block_until_interrupt=True)
    _adapter(s6b1_facts, fake, timeout_seconds=0.01).dispatch(
        SimpleNamespace(
            dispatch_id=s6b1_facts.attempt.id,
            execution=s6b1_facts.prepared.execution_request,
        )
    )
    assert fake.interrupt_count == 1
    assert fake.resume_count == 0


def _capture_before_downstream_failure(
    s6b1_facts: S6B1Facts,
) -> dict[str, object]:
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex(status="completed")),
    )
    evidence = _provider_evidence(result.provider_report)
    _emit_probe_evidence("S6B1_PROVIDER_EVIDENCE", evidence)
    workspace = s6b1_facts.prepared.execution_request.workspace.workspace_path
    with pytest.raises(AssertionError):
        assert (workspace / TARGET_PATH).read_text(encoding="utf-8") == AFTER_CONTENT
    return evidence


def test_evid_01_thread_identity_survives_downstream_assertion(
    s6b1_facts: S6B1Facts,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence = _capture_before_downstream_failure(s6b1_facts)
    assert evidence["thread_id"] == "thread-s6b1-test"
    assert '"thread_id": "thread-s6b1-test"' in capsys.readouterr().out


def test_evid_02_turn_identity_survives_downstream_assertion(
    s6b1_facts: S6B1Facts,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence = _capture_before_downstream_failure(s6b1_facts)
    assert evidence["turn_id"] == "turn-s6b1-test"
    assert '"turn_id": "turn-s6b1-test"' in capsys.readouterr().out


def test_evid_03_terminal_status_survives_downstream_assertion(
    s6b1_facts: S6B1Facts,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence = _capture_before_downstream_failure(s6b1_facts)
    assert evidence["turn_status"] == "completed"
    assert '"turn_status": "completed"' in capsys.readouterr().out


def test_evid_04_lifecycle_timestamps_survive_downstream_assertion(
    s6b1_facts: S6B1Facts,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence = _capture_before_downstream_failure(s6b1_facts)
    assert evidence["started_at"]
    assert evidence["finished_at"]
    assert evidence["recorded_at"]
    assert evidence["sdk_started_at"] == 1_800_000_000
    assert evidence["sdk_completed_at"] == 1_800_000_001
    output = capsys.readouterr().out
    assert '"started_at":' in output
    assert '"finished_at":' in output
    assert '"sdk_completed_at": 1800000001' in output


def test_evid_05_provider_outcome_is_independent_from_artifact_observation(
    s6b1_facts: S6B1Facts,
) -> None:
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex(status="completed")),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert result.observation.changes == ()
    assert result.work_products == ()


def test_evid_06_observation_failure_does_not_rewrite_provider_outcome(
    s6b1_facts: S6B1Facts,
) -> None:
    class FailingObserver:
        def current_ref_revision(self, *args, **kwargs):
            return s6b1_facts.execution.observer.current_ref_revision(
                *args,
                **kwargs,
            )

        def observe(self, *_args, **_kwargs):
            raise RuntimeError("injected independent observation failure")

    execution = ExecutionService(
        s6b1_facts.database,
        preparation=s6b1_facts.preparation,
        observer=FailingObserver(),
    )
    with pytest.raises(RuntimeError, match="independent observation failure"):
        execution.dispatch_and_observe(
            s6b1_facts.attempt.id,
            _adapter(s6b1_facts, FakeCodex(status="completed")),
        )

    report = _persisted_provider_report(
        s6b1_facts.database,
        s6b1_facts.attempt.id,
    )
    assert report is not None
    assert report.outcome is ProviderReportedOutcome.SUCCESS
    assert report.metadata["turn_status"] == "completed"


def test_evid_07_provider_failure_does_not_invent_artifact_reality(
    s6b1_facts: S6B1Facts,
) -> None:
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(
            s6b1_facts,
            FakeCodex(start_error=RuntimeError("provider lifecycle unavailable")),
        ),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.UNKNOWN
    assert result.provider_report.metadata["exception_type"] == "RuntimeError"
    assert result.observation.changes == ()
    assert result.work_products == ()


def test_evid_08_cleanup_occurs_after_evidence_capture(
    s6b1_facts: S6B1Facts,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex(status="completed")),
    )
    evidence = _provider_evidence(result.provider_report)
    _emit_probe_evidence("S6B1_PROVIDER_EVIDENCE", evidence)
    assert _persisted_provider_report(
        s6b1_facts.database,
        s6b1_facts.attempt.id,
    ) is not None

    _truncate_runtime(s6b1_facts.database)

    assert _persisted_provider_report(
        s6b1_facts.database,
        s6b1_facts.attempt.id,
    ) is None
    assert evidence["thread_id"] == "thread-s6b1-test"
    assert '"thread_id": "thread-s6b1-test"' in capsys.readouterr().out


def test_close_01_materialized_execution_input_id_is_exported(
    s6b1_facts: S6B1Facts,
) -> None:
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex()),
    )
    evidence = _provider_evidence(result.provider_report)
    assert evidence["materialized_execution_input_id"] == str(
        s6b1_facts.materialized_input.id
    )


def test_close_02_materialized_execution_input_fingerprint_is_exported(
    s6b1_facts: S6B1Facts,
) -> None:
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex()),
    )
    evidence = _provider_evidence(result.provider_report)
    assert evidence["materialized_execution_input_fingerprint"] == (
        s6b1_facts.materialized_input.input_fingerprint
    )


def test_close_03_unknown_and_observed_none_are_representable(
    s6b1_facts: S6B1Facts,
) -> None:
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex(status="interrupted")),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.UNKNOWN
    assert result.observation.changes == ()
    assert result.work_products == ()


def test_close_04_success_and_observed_none_remain_independent(
    s6b1_facts: S6B1Facts,
) -> None:
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex(status="completed")),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert result.observation.changes == ()
    assert result.work_products == ()


def test_close_05_unknown_and_observed_modified_remain_independent(
    s6b1_facts: S6B1Facts,
) -> None:
    def mutate(workspace: Path) -> None:
        (workspace / TARGET_PATH).write_text(AFTER_CONTENT, encoding="utf-8")

    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(
            s6b1_facts,
            FakeCodex(status="interrupted", mutation=mutate),
        ),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.UNKNOWN
    assert [change.repository_relative_path for change in result.observation.changes] == [
        TARGET_PATH
    ]


def test_close_06_probe_contract_does_not_require_preferred_mutation(
    s6b1_facts: S6B1Facts,
) -> None:
    before_ref = _git(s6b1_facts.repository, "rev-parse", "refs/heads/main")
    before_status = _git(s6b1_facts.repository, "status", "--porcelain")
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex(status="completed")),
    )
    _assert_probe_correlation(result, s6b1_facts.materialized_input)
    _assert_safe_production_observation(
        result,
        authoritative_ref_before=before_ref,
        authoritative_ref_after=_git(
            s6b1_facts.repository,
            "rev-parse",
            "refs/heads/main",
        ),
        authoritative_status_before=before_status,
        authoritative_status_after=_git(
            s6b1_facts.repository,
            "status",
            "--porcelain",
        ),
    )
    workspace = s6b1_facts.prepared.execution_request.workspace.workspace_path
    assert (workspace / TARGET_PATH).read_text(encoding="utf-8") == BEFORE_CONTENT


def test_close_07_unexpected_workspace_paths_fail_safety_validation(
    s6b1_facts: S6B1Facts,
) -> None:
    def mutate(workspace: Path) -> None:
        (workspace / "unexpected.txt").write_text("unsafe\n", encoding="utf-8")

    before_ref = _git(s6b1_facts.repository, "rev-parse", "refs/heads/main")
    before_status = _git(s6b1_facts.repository, "status", "--porcelain")
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex(mutation=mutate)),
    )
    with pytest.raises(AssertionError, match="unexpected workspace paths"):
        _assert_safe_production_observation(
            result,
            authoritative_ref_before=before_ref,
            authoritative_ref_after=before_ref,
            authoritative_status_before=before_status,
            authoritative_status_after=before_status,
        )


def test_close_08_authoritative_mutation_fails_safety_validation(
    s6b1_facts: S6B1Facts,
) -> None:
    before_ref = _git(s6b1_facts.repository, "rev-parse", "refs/heads/main")
    before_status = _git(s6b1_facts.repository, "status", "--porcelain")
    result = s6b1_facts.execution.dispatch_and_observe(
        s6b1_facts.attempt.id,
        _adapter(s6b1_facts, FakeCodex()),
    )
    with pytest.raises(
        AssertionError,
        match="authoritative repository working tree changed",
    ):
        _assert_safe_production_observation(
            result,
            authoritative_ref_before=before_ref,
            authoritative_ref_after=before_ref,
            authoritative_status_before=before_status,
            authoritative_status_after=" M unauthorized.txt",
        )


@pytest.mark.real_codex
def test_s6b1_real_codex_sdk_probe(s6b1_facts: S6B1Facts) -> None:
    if os.environ.get("SPG_RUN_REAL_CODEX") != "1":
        pytest.skip("set SPG_RUN_REAL_CODEX=1 for the one authorized SDK probe")
    assert not os.environ.get("OPENAI_API_KEY")
    assert not os.environ.get("CODEX_API_KEY")

    with Codex() as codex:
        account_response = codex.account(refresh_token=False)
        account_root = (
            account_response.account.root
            if account_response.account is not None
            else None
        )
        assert account_root is not None
        assert getattr(account_root, "type", None) == "chatgpt"
        auth_plan = str(getattr(account_root, "plan_type", "unknown"))

    authoritative_ref_before = _git(
        s6b1_facts.repository,
        "rev-parse",
        "refs/heads/main",
    )
    authoritative_status_before = _git(s6b1_facts.repository, "status", "--porcelain")
    try:
        result = s6b1_facts.execution.dispatch_and_observe(
            s6b1_facts.attempt.id,
            CodexSdkExecutor(
                s6b1_facts.materialized_input,
                timeout_seconds=120,
            ),
        )
    except Exception as error:
        persisted_report = _persisted_provider_report(
            s6b1_facts.database,
            s6b1_facts.attempt.id,
        )
        if persisted_report is not None:
            provider_evidence = _provider_evidence(persisted_report) | {
                "auth_type": "chatgpt",
                "auth_plan": auth_plan,
            }
            _emit_probe_evidence(
                "S6B1_PROVIDER_EVIDENCE",
                provider_evidence,
            )
        _emit_probe_evidence(
            "S6B1_PRODUCTION_EVIDENCE",
            {
                "observation_error_type": type(error).__name__,
                "observation_error": str(error),
            },
        )
        raise

    provider_evidence = _provider_evidence(result.provider_report) | {
        "auth_type": "chatgpt",
        "auth_plan": auth_plan,
    }
    _emit_probe_evidence("S6B1_PROVIDER_EVIDENCE", provider_evidence)

    authoritative_ref_after = _git(
        s6b1_facts.repository,
        "rev-parse",
        "refs/heads/main",
    )
    authoritative_status_after = _git(s6b1_facts.repository, "status", "--porcelain")

    workspace = s6b1_facts.prepared.execution_request.workspace.workspace_path
    workspace_content = (workspace / TARGET_PATH).read_text(encoding="utf-8")
    production_evidence = {
        "authoritative_ref_before": authoritative_ref_before,
        "authoritative_ref_after": authoritative_ref_after,
        "authoritative_status_before": authoritative_status_before,
        "authoritative_status_after": authoritative_status_after,
        "workspace_identity": result.dispatch.workspace.workspace_identity,
        "workspace_path": str(workspace),
        "target_path": TARGET_PATH,
        "target_content": workspace_content,
        "changes": [
            {
                "artifact_path": change.repository_relative_path,
                "change_type": change.change_type.value,
                "source_fingerprint": change.source_fingerprint,
                "observed_fingerprint": change.observed_fingerprint,
            }
            for change in result.observation.changes
        ],
        "work_products": [item.artifact_path for item in result.work_products],
    }
    _emit_probe_evidence("S6B1_PRODUCTION_EVIDENCE", production_evidence)

    assert result.provider_report.outcome in {
        ProviderReportedOutcome.SUCCESS,
        ProviderReportedOutcome.FAILURE,
        ProviderReportedOutcome.UNKNOWN,
    }
    _assert_probe_correlation(result, s6b1_facts.materialized_input)
    _assert_safe_production_observation(
        result,
        authoritative_ref_before=authoritative_ref_before,
        authoritative_ref_after=authoritative_ref_after,
        authoritative_status_before=authoritative_status_before,
        authoritative_status_after=authoritative_status_after,
    )
    if result.observation.changes:
        assert result.observation.changes[0].observed_fingerprint == _git(
            workspace,
            "hash-object",
            "--",
            TARGET_PATH,
        )
    assert s6b1_facts.runtime.inspect_run(
        s6b1_facts.spine.run.id
    ).work_unit.condition.value == "PROPOSED"
    assert s6b1_facts.runtime.current_baseline().id == s6b1_facts.baseline.id
