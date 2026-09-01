"""S6-B2-A dedicated Executor boundary deterministic spike."""

from collections.abc import Iterator
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from pydantic import ValidationError
from sqlalchemy import func, inspect, select

from spg.application.execution import ExecutionService
from spg.application.materialization import ExecutionInputMaterializationService
from spg.application.preparation import PreparationService
from spg.application.runtime import RuntimeService
from spg.domain.execution import (
    ArtifactChangeType,
    ExecutorDispatchRequest,
    ProviderReportedOutcome,
)
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
)
from spg.infrastructure.executor_boundary import (
    DedicatedExecutorClient,
    DedicatedExecutorRequest,
    ExecutorTransportError,
    ExecutorWorkspacePathMapping,
    SubprocessExecutorTransport,
    execute_deterministic_request,
)
from spg.infrastructure.codex_executor_binding import (
    AUTH_READINESS,
    CODEX_BINDING,
    CODEX_REAL_BINDING,
    preflight_codex_binding,
    unsupported_provider_binding,
)
from spg.infrastructure.git_observation import GitWorkspaceObserver
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_schema import (
    baseline_candidates,
    completion_evaluations,
    provider_execution_reports,
    runtime_commits,
    runtime_tables,
    verification_records,
)
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.providers.codex_sdk_executor import CodexSdkExecutor
from spg.providers.deterministic_executor import (
    DeterministicExecutionSpecification,
    DeterministicFileOperation,
    DeterministicFileOperationType,
)


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TABLE_NAMES = {table.name for table in runtime_tables}
TARGET_PATH = "docs/executor_boundary_target.md"
BEFORE_CONTENT = "S6-B2-A marker: BEFORE\n"
AFTER_CONTENT = "S6-B2-A marker: AFTER\n"
INSTRUCTION = "Modify only the admitted S6-B2-A deterministic fixture when instructed."
UNAUTHORIZED_PROVIDER_TRANSPORT_FIELDS = frozenset(
    {
        "provider_binding",
        "codex_sdk_configuration",
        "codex_model",
        "codex_runtime",
        "thread_id",
        "turn_id",
        "turn_handle",
        "provider_credentials",
        "api_key",
        "raw_token",
        "chatgpt_auth_file",
        "provider_lifecycle",
    }
)


@dataclass(frozen=True)
class S6B2AFacts:
    database: Database
    execution: ExecutionService
    repository: Path
    attempt: object
    prepared: object
    materialized_input: object


class CapturingTransport:
    def __init__(self, delegate=None) -> None:
        self.delegate = delegate or SubprocessExecutorTransport()
        self.requests: list[DedicatedExecutorRequest] = []

    def exchange(self, request: DedicatedExecutorRequest) -> str:
        self.requests.append(request)
        return self.delegate.exchange(request)


class UnavailableTransport:
    def exchange(self, request: DedicatedExecutorRequest) -> str:
        raise ExecutorTransportError("UNAVAILABLE", "fixture boundary unavailable")


class MalformedTransport:
    def exchange(self, request: DedicatedExecutorRequest) -> str:
        return "not-json"


class MismatchedTransport:
    def __init__(self, specification) -> None:
        self.specification = specification

    def exchange(self, request: DedicatedExecutorRequest) -> str:
        response = execute_deterministic_request(request, self.specification)
        return response.model_copy(update={"dispatch_id": uuid4()}).model_dump_json()


class ClaimingTransport:
    def __init__(self, specification) -> None:
        self.specification = specification

    def exchange(self, request: DedicatedExecutorRequest) -> str:
        response = execute_deterministic_request(request, self.specification)
        return response.model_copy(
            update={"metadata": {"provider_claimed_paths": ["fabricated.py"]}}
        ).model_dump_json()


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
def s6b2a_facts(postgres_database: Database, tmp_path: Path) -> S6B2AFacts:
    repository = tmp_path / "authoritative-repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "docs").mkdir()
    (repository / "AI_context.md").write_text(
        "S6-B2-A admitted project context\n", encoding="utf-8"
    )
    (repository / "docs" / "contract.md").write_text(
        "The dedicated Executor receives only explicit execution facts.\n",
        encoding="utf-8",
    )
    (repository / TARGET_PATH).write_text(BEFORE_CONTENT, encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "S6-B2-A deterministic baseline")

    runtime = RuntimeService(postgres_database)
    preparation = PreparationService(postgres_database)
    execution = ExecutionService(postgres_database, preparation=preparation)
    materialization = ExecutionInputMaterializationService(
        postgres_database,
        preparation=preparation,
    )
    runtime.bootstrap_trusted_baseline(
        BootstrapRequest(
            repository_path=repository,
            repository_identity="test://s6b2a-executor-boundary",
            repository_ref="refs/heads/main",
            authority_identity="architecture-lead:s6b2a",
            scope={"slice": "S6-B2-A"},
        )
    )
    spine = runtime.create_initial_runtime_spine(
        InitialRunRequest(
            intent_ref="intent:s6b2a-deterministic-boundary",
            goal="Prove the dedicated deterministic Executor process boundary",
            production_horizon=ProductionHorizon.DOCUMENTATION,
            initial_work_unit_objective=f"Modify only {TARGET_PATH}",
            completion_contract=CompletionContract(
                required_outputs=(TARGET_PATH,),
                required_changes=("replace the fixture marker when requested",),
                forbidden_changes=("authoritative repository mutation",),
                verification_obligations=("independent Git observation",),
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
            binding_ref="binding:dedicated-executor-boundary",
            capability_identity="capability:executor",
            profile_identity="profile:local-dedicated-process",
        ),
        repository,
        tmp_path / "attempt-workspaces",
    )
    materialized_input = materialization.materialize(attempt.id, INSTRUCTION)
    return S6B2AFacts(
        database=postgres_database,
        execution=execution,
        repository=repository,
        attempt=attempt,
        prepared=prepared,
        materialized_input=materialized_input,
    )


def _specification(
    outcome: ProviderReportedOutcome,
    *,
    mutate: bool = False,
    path: str = TARGET_PATH,
) -> DeterministicExecutionSpecification:
    operations = ()
    if mutate:
        operations = (
            DeterministicFileOperation(
                operation=DeterministicFileOperationType.MODIFY,
                repository_relative_path=path,
                content=AFTER_CONTENT,
            ),
        )
    return DeterministicExecutionSpecification(
        operations=operations,
        reported_outcome=outcome,
        summary=f"fixture Provider outcome {outcome.value}",
    )


def _client(
    facts: S6B2AFacts,
    outcome: ProviderReportedOutcome,
    *,
    mutate: bool = False,
    path: str = TARGET_PATH,
    transport=None,
    workspace_path_mapper=None,
) -> DedicatedExecutorClient:
    specification = _specification(outcome, mutate=mutate, path=path)
    selected_transport = transport or SubprocessExecutorTransport(
        deterministic_specification=specification
    )
    return DedicatedExecutorClient(
        facts.materialized_input,
        transport=selected_transport,
        workspace_path_mapper=workspace_path_mapper,
    )


def _request(facts: S6B2AFacts) -> ExecutorDispatchRequest:
    return ExecutorDispatchRequest(
        dispatch_id=uuid4(),
        execution=facts.prepared.execution_request,
    )


def _assert_provider_neutral_transport_request(
    request: DedicatedExecutorRequest,
) -> dict[str, object]:
    """Validate transport structure without interpreting admitted string values."""

    payload = json.loads(request.model_dump_json())
    assert set(payload) == set(DedicatedExecutorRequest.model_fields)
    assert set(payload).isdisjoint(UNAUTHORIZED_PROVIDER_TRANSPORT_FIELDS)
    assert set(payload["executor_binding"]) == set(ExecutorBinding.model_fields)
    assert set(payload["executor_binding"]).isdisjoint(
        UNAUTHORIZED_PROVIDER_TRANSPORT_FIELDS
    )
    assert DedicatedExecutorRequest.model_validate(payload) == request
    return payload


def _assert_unauthorized_transport_field_rejected(
    request: DedicatedExecutorRequest,
    field_name: str,
) -> None:
    payload = request.model_dump(mode="json")
    payload[field_name] = "unauthorized-fixture-value"
    with pytest.raises(ValidationError) as captured:
        DedicatedExecutorRequest.model_validate(payload)
    assert any(
        error["type"] == "extra_forbidden"
        and tuple(error["loc"]) == (field_name,)
        for error in captured.value.errors()
    )


def _count(database: Database, table) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table))


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _create_directory_alias(alias: Path, target: Path) -> None:
    """Create a directory alias without requiring Windows symlink privilege."""

    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(alias), str(target)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError("Windows directory junction creation failed")
        return
    alias.symlink_to(target, target_is_directory=True)


def _truncate_runtime(database: Database) -> None:
    table_names = ", ".join(f'"{name}"' for name in RUNTIME_TABLE_NAMES)
    with database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {table_names} CASCADE")


def test_b2a_01_exact_governed_dispatch_crosses_process_boundary(
    s6b2a_facts: S6B2AFacts,
) -> None:
    transport = CapturingTransport(
        SubprocessExecutorTransport(
            deterministic_specification=_specification(
                ProviderReportedOutcome.SUCCESS,
                mutate=True,
            )
        )
    )
    result = s6b2a_facts.execution.dispatch_and_observe(
        s6b2a_facts.attempt.id,
        _client(
            s6b2a_facts,
            ProviderReportedOutcome.SUCCESS,
            mutate=True,
            transport=transport,
        ),
    )
    assert len(transport.requests) == 1
    assert result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert result.provider_report.metadata["executor_transport_status"] == "COMPLETED"
    assert result.provider_report.metadata["dispatch_id"] == str(result.dispatch.id)
    assert result.observation.changes[0].change_type is ArtifactChangeType.MODIFIED


def test_b2a_02_materialized_input_identity_and_fingerprint_cross_exactly(
    s6b2a_facts: S6B2AFacts,
) -> None:
    result = _client(
        s6b2a_facts,
        ProviderReportedOutcome.SUCCESS,
    ).dispatch(_request(s6b2a_facts))
    assert result.metadata["materialized_execution_input_id"] == str(
        s6b2a_facts.materialized_input.id
    )
    assert result.metadata["materialized_execution_input_fingerprint"] == (
        s6b2a_facts.materialized_input.input_fingerprint
    )


def test_b2a_03_workspace_identity_survives_path_translation(
    s6b2a_facts: S6B2AFacts,
    tmp_path: Path,
) -> None:
    translated = tmp_path / "executor-mounted-workspace"
    _create_directory_alias(
        translated,
        s6b2a_facts.prepared.execution_request.workspace.workspace_path,
    )

    def mapper(workspace):
        return ExecutorWorkspacePathMapping(
            workspace_identity=workspace.workspace_identity,
            executor_workspace_path=translated,
        )

    result = _client(
        s6b2a_facts,
        ProviderReportedOutcome.SUCCESS,
        workspace_path_mapper=mapper,
    ).dispatch(_request(s6b2a_facts))
    assert result.metadata["workspace_identity"] == (
        s6b2a_facts.prepared.execution_request.workspace.workspace_identity
    )
    assert result.metadata["executor_workspace_path"] == str(translated)


def test_b2a_04_authoritative_repository_is_not_a_writable_executor_target(
    s6b2a_facts: S6B2AFacts,
) -> None:
    authoritative = s6b2a_facts.repository / "AI_context.md"
    before = authoritative.read_text(encoding="utf-8")
    escape = s6b2a_facts.prepared.execution_request.workspace.workspace_path / "escape"
    _create_directory_alias(escape, s6b2a_facts.repository)
    result = _client(
        s6b2a_facts,
        ProviderReportedOutcome.SUCCESS,
        mutate=True,
        path="escape/AI_context.md",
    ).dispatch(_request(s6b2a_facts))
    assert result.outcome is ProviderReportedOutcome.UNKNOWN
    assert result.metadata["executor_transport_status"] == "PROCESS_ERROR"
    assert authoritative.read_text(encoding="utf-8") == before


def test_b2a_05_exact_attempt_workspace_is_writable(
    s6b2a_facts: S6B2AFacts,
) -> None:
    result = _client(
        s6b2a_facts,
        ProviderReportedOutcome.SUCCESS,
        mutate=True,
    ).dispatch(_request(s6b2a_facts))
    target = s6b2a_facts.prepared.execution_request.workspace.workspace_path / TARGET_PATH
    assert result.outcome is ProviderReportedOutcome.SUCCESS
    assert target.read_text(encoding="utf-8") == AFTER_CONTENT


def test_b2a_06_success_does_not_imply_observed_work(
    s6b2a_facts: S6B2AFacts,
) -> None:
    result = s6b2a_facts.execution.dispatch_and_observe(
        s6b2a_facts.attempt.id,
        _client(s6b2a_facts, ProviderReportedOutcome.SUCCESS),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert result.observation.changes == ()
    assert result.work_products == ()


def test_b2a_07_unknown_can_coexist_with_modified_work(
    s6b2a_facts: S6B2AFacts,
) -> None:
    result = s6b2a_facts.execution.dispatch_and_observe(
        s6b2a_facts.attempt.id,
        _client(
            s6b2a_facts,
            ProviderReportedOutcome.UNKNOWN,
            mutate=True,
        ),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.UNKNOWN
    assert [change.repository_relative_path for change in result.observation.changes] == [
        TARGET_PATH
    ]
    assert [reference.artifact_path for reference in result.work_products] == [TARGET_PATH]


def test_b2a_08_transport_failure_remains_distinct_from_provider_outcome(
    s6b2a_facts: S6B2AFacts,
) -> None:
    result = _client(
        s6b2a_facts,
        ProviderReportedOutcome.SUCCESS,
        transport=UnavailableTransport(),
    ).dispatch(_request(s6b2a_facts))
    assert result.outcome is ProviderReportedOutcome.UNKNOWN
    assert result.metadata["executor_transport_status"] == "UNAVAILABLE"
    assert result.metadata["provider_result_present"] is False


def test_b2a_09_malformed_response_is_conservative_unknown(
    s6b2a_facts: S6B2AFacts,
) -> None:
    result = _client(
        s6b2a_facts,
        ProviderReportedOutcome.SUCCESS,
        transport=MalformedTransport(),
    ).dispatch(_request(s6b2a_facts))
    assert result.outcome is ProviderReportedOutcome.UNKNOWN
    assert result.metadata["executor_transport_status"] == "MALFORMED_RESPONSE"
    assert result.metadata["provider_result_present"] is False


def test_b2a_10_executor_receives_explicit_input_without_database_discovery(
    s6b2a_facts: S6B2AFacts,
) -> None:
    transport = CapturingTransport(
        SubprocessExecutorTransport(
            deterministic_specification=_specification(
                ProviderReportedOutcome.SUCCESS
            )
        )
    )
    result = _client(
        s6b2a_facts,
        ProviderReportedOutcome.SUCCESS,
        transport=transport,
    ).dispatch(_request(s6b2a_facts))
    payload = transport.requests[0].model_dump_json()
    assert INSTRUCTION in transport.requests[0].provider_input
    assert "database_url" not in payload.lower()
    assert "repository_path" not in payload
    assert "specification" not in payload
    assert "reported_outcome" not in payload
    assert result.metadata["database_configuration_present"] is False


def test_b2a_11_provider_credentials_do_not_enter_spg_persistence(
    s6b2a_facts: S6B2AFacts,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "fixture-provider-secret-never-persist"
    monkeypatch.setenv("B2A_FAKE_PROVIDER_SECRET", secret)
    result = s6b2a_facts.execution.dispatch_and_observe(
        s6b2a_facts.attempt.id,
        _client(
            s6b2a_facts,
            ProviderReportedOutcome.SUCCESS,
            transport=SubprocessExecutorTransport(
                deterministic_specification=_specification(
                    ProviderReportedOutcome.SUCCESS
                ),
            ),
        ),
    )
    assert secret not in json.dumps(
        result.provider_report.model_dump(mode="json"), sort_keys=True
    )
    columns = {
        column["name"]
        for column in inspect(s6b2a_facts.database.engine).get_columns(
            "provider_execution_reports"
        )
    }
    assert not ({"credential", "secret", "token", "auth"} & columns)


def test_b2a_12_independent_observation_overrules_provider_artifact_claims(
    s6b2a_facts: S6B2AFacts,
) -> None:
    failure = _client(
        s6b2a_facts,
        ProviderReportedOutcome.FAILURE,
    ).dispatch(_request(s6b2a_facts))
    unknown = _client(
        s6b2a_facts,
        ProviderReportedOutcome.UNKNOWN,
    ).dispatch(_request(s6b2a_facts))
    assert failure.outcome is ProviderReportedOutcome.FAILURE
    assert unknown.outcome is ProviderReportedOutcome.UNKNOWN

    result = s6b2a_facts.execution.dispatch_and_observe(
        s6b2a_facts.attempt.id,
        _client(
            s6b2a_facts,
            ProviderReportedOutcome.SUCCESS,
            transport=ClaimingTransport(
                _specification(ProviderReportedOutcome.SUCCESS)
            ),
        ),
    )
    assert result.provider_report.metadata["provider_claimed_paths"] == [
        "fabricated.py"
    ]
    assert result.observation.changes == ()
    assert result.work_products == ()


def test_b2a_13_path_translation_never_replaces_canonical_domain_path(
    s6b2a_facts: S6B2AFacts,
    tmp_path: Path,
) -> None:
    canonical = s6b2a_facts.prepared.execution_request.workspace
    translated = tmp_path / "container-workspace"
    _create_directory_alias(translated, canonical.workspace_path)

    def mapper(workspace):
        return ExecutorWorkspacePathMapping(
            workspace_identity=workspace.workspace_identity,
            executor_workspace_path=translated,
        )

    _client(
        s6b2a_facts,
        ProviderReportedOutcome.SUCCESS,
        workspace_path_mapper=mapper,
    ).dispatch(_request(s6b2a_facts))
    assert s6b2a_facts.prepared.execution_request.workspace == canonical
    assert canonical.workspace_path != translated


def test_b2a_14_response_correlation_must_match_exact_dispatch_and_input(
    s6b2a_facts: S6B2AFacts,
) -> None:
    result = _client(
        s6b2a_facts,
        ProviderReportedOutcome.SUCCESS,
        transport=MismatchedTransport(
            _specification(ProviderReportedOutcome.SUCCESS)
        ),
    ).dispatch(_request(s6b2a_facts))
    assert result.outcome is ProviderReportedOutcome.UNKNOWN
    assert result.metadata["executor_transport_status"] == "CORRELATION_MISMATCH"
    assert result.metadata["provider_result_present"] is False


def test_b2a_15_executor_boundary_introduces_no_completion_authority(
    s6b2a_facts: S6B2AFacts,
) -> None:
    result = s6b2a_facts.execution.dispatch_and_observe(
        s6b2a_facts.attempt.id,
        _client(
            s6b2a_facts,
            ProviderReportedOutcome.SUCCESS,
            mutate=True,
        ),
    )
    assert result.work_products
    assert _count(s6b2a_facts.database, completion_evaluations) == 0
    assert _count(s6b2a_facts.database, verification_records) == 0
    assert _count(s6b2a_facts.database, baseline_candidates) == 0
    assert _count(s6b2a_facts.database, runtime_commits) == 0


def _codex_preflight_client(
    facts: S6B2AFacts,
    *,
    transport=None,
    workspace_path_mapper=None,
) -> DedicatedExecutorClient:
    return DedicatedExecutorClient(
        facts.materialized_input,
        transport=transport
        or SubprocessExecutorTransport(provider_binding=CODEX_BINDING),
        workspace_path_mapper=workspace_path_mapper,
    )


def test_b2b1_01_codex_binding_is_selected_inside_dedicated_executor(
    s6b2a_facts: S6B2AFacts,
) -> None:
    response = _codex_preflight_client(s6b2a_facts).preflight_provider_binding(
        _request(s6b2a_facts)
    )
    assert response.binding_identity == CODEX_BINDING
    assert response.binding_status == "READY_FOR_REAL_PROBE_AUTH_UNPROVEN"
    assert response.adapter_identity == (
        "spg.providers.codex_sdk_executor.CodexSdkExecutor"
    )
    assert response.provider_turn_started is False


def test_b2b1_02_spg_transport_remains_provider_neutral(
    s6b2a_facts: S6B2AFacts,
) -> None:
    transport = CapturingTransport(
        SubprocessExecutorTransport(provider_binding=CODEX_BINDING)
    )
    _codex_preflight_client(
        s6b2a_facts,
        transport=transport,
    ).preflight_provider_binding(_request(s6b2a_facts))
    payload = transport.requests[0].model_dump_json().lower()
    assert "codex" not in payload
    assert "provider_binding" not in payload
    assert "specification" not in payload
    assert "reported_outcome" not in payload


def test_b2b1_03_exact_materialized_input_correlation_survives_boundary(
    s6b2a_facts: S6B2AFacts,
) -> None:
    response = _codex_preflight_client(s6b2a_facts).preflight_provider_binding(
        _request(s6b2a_facts)
    )
    assert response.materialized_execution_input_id == (
        s6b2a_facts.materialized_input.id
    )
    assert response.materialized_execution_input_fingerprint == (
        s6b2a_facts.materialized_input.input_fingerprint
    )


def test_b2b1_04_exact_workspace_identity_survives_boundary(
    s6b2a_facts: S6B2AFacts,
) -> None:
    response = _codex_preflight_client(s6b2a_facts).preflight_provider_binding(
        _request(s6b2a_facts)
    )
    assert response.workspace_identity == (
        s6b2a_facts.prepared.execution_request.workspace.workspace_identity
    )


def test_b2b1_05_workspace_translation_is_infrastructure_only(
    s6b2a_facts: S6B2AFacts,
    tmp_path: Path,
) -> None:
    canonical = s6b2a_facts.prepared.execution_request.workspace
    translated = tmp_path / "codex-executor-workspace"
    _create_directory_alias(translated, canonical.workspace_path)

    def mapper(workspace):
        return ExecutorWorkspacePathMapping(
            workspace_identity=workspace.workspace_identity,
            executor_workspace_path=translated,
        )

    response = _codex_preflight_client(
        s6b2a_facts,
        workspace_path_mapper=mapper,
    ).preflight_provider_binding(_request(s6b2a_facts))
    assert response.binding_status == "READY_FOR_REAL_PROBE_AUTH_UNPROVEN"
    assert s6b2a_facts.prepared.execution_request.workspace == canonical
    assert canonical.workspace_path != translated


def test_b2b1_06_transport_payload_contains_no_credential_field(
    s6b2a_facts: S6B2AFacts,
) -> None:
    client = _codex_preflight_client(s6b2a_facts)
    payload = client.prepare_transport_request(_request(s6b2a_facts)).model_dump_json()
    lowered = payload.lower()
    assert all(
        forbidden not in lowered
        for forbidden in ("credential", "secret", "token", "api_key", "auth_path")
    )


def test_b2b1_07_provider_credentials_are_not_persisted(
    s6b2a_facts: S6B2AFacts,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "b2b1-parent-secret-not-admitted"
    monkeypatch.setenv("B2B1_UNRELATED_PROVIDER_SECRET", secret)
    response = _codex_preflight_client(s6b2a_facts).preflight_provider_binding(
        _request(s6b2a_facts)
    )
    assert secret not in response.model_dump_json()
    assert _count(s6b2a_facts.database, provider_execution_reports) == 0
    columns = {
        column["name"]
        for column in inspect(s6b2a_facts.database.engine).get_columns(
            "provider_execution_reports"
        )
    }
    assert not ({"credential", "secret", "token", "api_key"} & columns)


def test_b2b1_08_child_environment_excludes_spg_database_configuration(
    s6b2a_facts: S6B2AFacts,
) -> None:
    response = _codex_preflight_client(s6b2a_facts).preflight_provider_binding(
        _request(s6b2a_facts)
    )
    assert response.metadata["spg_database_configuration_present"] is False


def test_b2b1_09_child_environment_excludes_unrelated_credentials(
    s6b2a_facts: S6B2AFacts,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "b2b1-unrelated-secret-value"
    monkeypatch.setenv("B2B1_UNRELATED_CREDENTIAL", secret)
    response = _codex_preflight_client(s6b2a_facts).preflight_provider_binding(
        _request(s6b2a_facts)
    )
    assert response.binding_status == "READY_FOR_REAL_PROBE_AUTH_UNPROVEN"
    assert secret not in response.model_dump_json()
    assert response.metadata["authentication_secret_inspected"] is False


def test_b2b1_10_non_secret_runtime_prerequisites_are_narrowly_admitted(
    s6b2a_facts: S6B2AFacts,
) -> None:
    response = _codex_preflight_client(s6b2a_facts).preflight_provider_binding(
        _request(s6b2a_facts)
    )
    assert response.metadata["environment_policy"] == "NARROW_ALLOWLIST"
    assert set(response.metadata["permitted_environment_classes"]) == {
        "home-directory-location",
        "executable-search-path",
        "locale",
        "temporary-directory",
        "python-module-path",
    }


def test_b2b1_11_sdk_unavailable_maps_conservatively(
    s6b2a_facts: S6B2AFacts,
) -> None:
    client = _codex_preflight_client(s6b2a_facts)
    boundary_request = client.prepare_transport_request(_request(s6b2a_facts))

    def unavailable() -> str:
        raise ModuleNotFoundError("fixture SDK unavailable")

    response = preflight_codex_binding(
        boundary_request,
        environment={"CODEX_HOME": "/fixture/.codex", "PATH": "/usr/bin"},
        sdk_version_resolver=unavailable,
    )
    assert response.binding_status == "SDK_UNAVAILABLE"
    assert response.provider_outcome is ProviderReportedOutcome.UNKNOWN
    assert response.provider_turn_started is False


def test_b2b1_12_binding_failures_are_conservative_and_distinct(
    s6b2a_facts: S6B2AFacts,
) -> None:
    client = _codex_preflight_client(s6b2a_facts)
    boundary_request = client.prepare_transport_request(_request(s6b2a_facts))

    def initialization_failure(*_args, **_kwargs):
        raise RuntimeError("fixture adapter initialization failure")

    initialization = preflight_codex_binding(
        boundary_request,
        environment={"CODEX_HOME": "/fixture/.codex", "PATH": "/usr/bin"},
        sdk_version_resolver=lambda: "0.147.0",
        adapter_factory=initialization_failure,
    )
    missing = preflight_codex_binding(
        boundary_request,
        environment={"PATH": "/usr/bin"},
        sdk_version_resolver=lambda: "0.147.0",
    )
    unsupported = unsupported_provider_binding(boundary_request, "fixture-unknown")
    assert initialization.binding_status == "ADAPTER_INITIALIZATION_FAILED"
    assert missing.binding_status == "MISSING_RUNTIME_PREREQUISITE"
    assert unsupported.binding_status == "UNSUPPORTED_PROVIDER_BINDING"
    assert {
        initialization.provider_outcome,
        missing.provider_outcome,
        unsupported.provider_outcome,
    } == {ProviderReportedOutcome.UNKNOWN}


def test_b2b1_13_preflight_never_constructs_codex_or_starts_turn(
    s6b2a_facts: S6B2AFacts,
) -> None:
    client = _codex_preflight_client(s6b2a_facts)
    boundary_request = client.prepare_transport_request(_request(s6b2a_facts))
    codex_factory_calls = 0

    def forbidden_codex_factory():
        nonlocal codex_factory_calls
        codex_factory_calls += 1
        raise AssertionError("preflight must not construct Codex")

    def adapter_factory(materialized, *, workspace_validator):
        return CodexSdkExecutor(
            materialized,
            codex_factory=forbidden_codex_factory,
            workspace_validator=workspace_validator,
        )

    response = preflight_codex_binding(
        boundary_request,
        environment={"CODEX_HOME": "/fixture/.codex", "PATH": "/usr/bin"},
        sdk_version_resolver=lambda: "0.147.0",
        adapter_factory=adapter_factory,
    )
    assert response.binding_status == "READY_FOR_REAL_PROBE_AUTH_UNPROVEN"
    assert response.provider_turn_started is False
    assert codex_factory_calls == 0


def test_b2b1_14_preflight_introduces_no_completion_authority(
    s6b2a_facts: S6B2AFacts,
) -> None:
    response = _codex_preflight_client(s6b2a_facts).preflight_provider_binding(
        _request(s6b2a_facts)
    )
    assert response.provider_outcome is ProviderReportedOutcome.UNKNOWN
    assert _count(s6b2a_facts.database, provider_execution_reports) == 0
    assert _count(s6b2a_facts.database, completion_evaluations) == 0
    assert _count(s6b2a_facts.database, verification_records) == 0
    assert _count(s6b2a_facts.database, baseline_candidates) == 0


def test_b2b1_15_independent_spg_observation_remains_unchanged(
    s6b2a_facts: S6B2AFacts,
) -> None:
    _codex_preflight_client(s6b2a_facts).preflight_provider_binding(
        _request(s6b2a_facts)
    )
    workspace = s6b2a_facts.prepared.execution_request.workspace
    expected_ref = _git(s6b2a_facts.repository, "rev-parse", "refs/heads/main")
    reality = GitWorkspaceObserver().observe(
        workspace,
        repository_ref="refs/heads/main",
        expected_authoritative_ref_revision=expected_ref,
    )
    assert reality.changes == ()
    assert AUTH_READINESS == "REQUIRES EXECUTION-TIME PROOF"


def _persisted_provider_report(database: Database, attempt_id):
    with database.unit_of_work() as unit_of_work:
        store = RuntimeStore(unit_of_work.session)
        dispatch = store.execution_dispatch_for_attempt(attempt_id)
        if dispatch is None:
            return None
        return store.provider_execution_report(dispatch.id)


def _b2b2_provider_evidence(report) -> dict[str, object]:
    metadata = report.metadata
    return {
        "attempt_id": str(report.attempt_id),
        "generation": report.generation,
        "dispatch_id": str(report.dispatch_id),
        "materialized_execution_input_id": metadata.get(
            "materialized_execution_input_id"
        ),
        "materialized_execution_input_fingerprint": metadata.get(
            "materialized_execution_input_fingerprint"
        ),
        "request_fingerprint": metadata.get("executor_request_fingerprint"),
        "workspace_identity": metadata.get("workspace_identity"),
        "executor_workspace_path": metadata.get("executor_workspace_path"),
        "provider_reference": report.provider_reference,
        "provider_outcome": report.outcome.value,
        "provider_turn_started": metadata.get("provider_turn_started", False),
        "authenticated_provider_execution": metadata.get(
            "authenticated_provider_execution", "NOT_PROVEN"
        ),
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
        "timeout_at": metadata.get("timeout_at"),
        "interrupt_requested": metadata.get("interrupt_requested", False),
        "exception_type": metadata.get("exception_type"),
        "transport_status": metadata.get("executor_transport_status"),
        "provider_result_present": metadata.get("provider_result_present"),
        "executor_boundary": metadata.get("executor_boundary"),
    }


def _emit_b2b2_evidence(label: str, evidence: dict[str, object]) -> None:
    print(label + "=" + json.dumps(evidence, sort_keys=True), flush=True)


def _b2b2_production_evidence(
    facts: S6B2AFacts,
    *,
    authoritative_ref_before: str,
    authoritative_status_before: str,
    result=None,
) -> dict[str, object]:
    workspace = facts.prepared.execution_request.workspace.workspace_path
    target = workspace / TARGET_PATH
    return {
        "authoritative_ref_before": authoritative_ref_before,
        "authoritative_ref_after": _git(
            facts.repository, "rev-parse", "refs/heads/main"
        ),
        "authoritative_status_before": authoritative_status_before,
        "authoritative_status_after": _git(
            facts.repository, "status", "--porcelain"
        ),
        "workspace_head": _git(workspace, "rev-parse", "HEAD"),
        "workspace_status": _git(workspace, "status", "--porcelain"),
        "workspace_identity": (
            facts.prepared.execution_request.workspace.workspace_identity
        ),
        "workspace_path": str(workspace),
        "target_path": TARGET_PATH,
        "target_content": target.read_text(encoding="utf-8"),
        "target_blob_fingerprint": _git(workspace, "hash-object", "--", TARGET_PATH),
        "changed_paths": (
            [change.repository_relative_path for change in result.observation.changes]
            if result is not None
            else None
        ),
        "work_products": (
            [item.artifact_path for item in result.work_products]
            if result is not None
            else None
        ),
    }


@pytest.mark.real_codex
def test_b2b2_single_real_codex_through_dedicated_executor_boundary(
    s6b2a_facts: S6B2AFacts,
) -> None:
    if os.environ.get("SPG_RUN_REAL_CODEX_B2B2") != "1":
        pytest.skip("single S6-B2-B2 real probe requires explicit authorization")
    assert not os.environ.get("OPENAI_API_KEY")
    assert not os.environ.get("CODEX_API_KEY")

    authoritative_ref_before = _git(
        s6b2a_facts.repository, "rev-parse", "refs/heads/main"
    )
    authoritative_status_before = _git(
        s6b2a_facts.repository, "status", "--porcelain"
    )
    transport = CapturingTransport(
        SubprocessExecutorTransport(
            provider_binding=CODEX_REAL_BINDING,
            timeout_seconds=140,
        )
    )
    client = DedicatedExecutorClient(
        s6b2a_facts.materialized_input,
        transport=transport,
    )
    try:
        result = s6b2a_facts.execution.dispatch_and_observe(
            s6b2a_facts.attempt.id,
            client,
        )
    except Exception as error:
        report = _persisted_provider_report(
            s6b2a_facts.database, s6b2a_facts.attempt.id
        )
        if report is not None:
            _emit_b2b2_evidence(
                "S6B2B2_PROVIDER_EVIDENCE", _b2b2_provider_evidence(report)
            )
        evidence = _b2b2_production_evidence(
            s6b2a_facts,
            authoritative_ref_before=authoritative_ref_before,
            authoritative_status_before=authoritative_status_before,
        ) | {
            "observation_error_type": type(error).__name__,
            "observation_error": str(error),
        }
        _emit_b2b2_evidence("S6B2B2_PRODUCTION_EVIDENCE", evidence)
        raise

    assert len(transport.requests) == 1
    request = transport.requests[0]
    _emit_b2b2_evidence(
        "S6B2B2_PROVIDER_EVIDENCE",
        _b2b2_provider_evidence(result.provider_report),
    )
    production_evidence = _b2b2_production_evidence(
        s6b2a_facts,
        authoritative_ref_before=authoritative_ref_before,
        authoritative_status_before=authoritative_status_before,
        result=result,
    )
    _emit_b2b2_evidence("S6B2B2_PRODUCTION_EVIDENCE", production_evidence)

    _assert_provider_neutral_transport_request(request)
    assert request.attempt_id == s6b2a_facts.attempt.id
    assert request.generation == s6b2a_facts.attempt.generation
    assert request.materialized_execution_input_id == s6b2a_facts.materialized_input.id
    assert request.materialized_execution_input_fingerprint == (
        s6b2a_facts.materialized_input.input_fingerprint
    )
    assert production_evidence["authoritative_ref_after"] == authoritative_ref_before
    assert (
        production_evidence["authoritative_status_after"]
        == authoritative_status_before
    )
    unexpected_paths = sorted(
        set(production_evidence["changed_paths"] or ()) - {TARGET_PATH}
    )
    assert not unexpected_paths, f"unexpected workspace paths: {unexpected_paths}"
    assert _count(s6b2a_facts.database, completion_evaluations) == 0
    assert _count(s6b2a_facts.database, verification_records) == 0
    assert _count(s6b2a_facts.database, baseline_candidates) == 0
    assert _count(s6b2a_facts.database, runtime_commits) == 0


def test_b2close_01_transport_provider_neutrality_is_structural(
    s6b2a_facts: S6B2AFacts,
) -> None:
    request = _codex_preflight_client(
        s6b2a_facts
    ).prepare_transport_request(_request(s6b2a_facts))
    payload = _assert_provider_neutral_transport_request(request)
    assert "provider_binding" not in payload
    assert "thread_id" not in payload
    assert "turn_id" not in payload


def test_b2close_02_codex_named_filesystem_path_is_not_provider_leakage(
    s6b2a_facts: S6B2AFacts,
    tmp_path: Path,
) -> None:
    translated = tmp_path / "codex-named-executor-workspace"
    _create_directory_alias(
        translated,
        s6b2a_facts.prepared.execution_request.workspace.workspace_path,
    )

    def mapper(workspace):
        return ExecutorWorkspacePathMapping(
            workspace_identity=workspace.workspace_identity,
            executor_workspace_path=translated,
        )

    request = _codex_preflight_client(
        s6b2a_facts,
        workspace_path_mapper=mapper,
    ).prepare_transport_request(_request(s6b2a_facts))
    assert "codex" in str(request.executor_workspace_path).lower()
    _assert_provider_neutral_transport_request(request)


def test_b2close_03_codex_named_fixture_is_not_provider_leakage(
    s6b2a_facts: S6B2AFacts,
) -> None:
    request = _codex_preflight_client(
        s6b2a_facts
    ).prepare_transport_request(_request(s6b2a_facts))
    assert "codex" in str(request.executor_workspace_path).lower()
    _assert_provider_neutral_transport_request(request)


def test_b2close_04_provider_specific_transport_fields_are_rejected(
    s6b2a_facts: S6B2AFacts,
) -> None:
    request = _codex_preflight_client(
        s6b2a_facts
    ).prepare_transport_request(_request(s6b2a_facts))
    for field_name in (
        "codex_sdk_configuration",
        "codex_model",
        "codex_runtime",
        "thread_id",
        "turn_id",
        "turn_handle",
        "provider_lifecycle",
    ):
        _assert_unauthorized_transport_field_rejected(request, field_name)


def test_b2close_05_credential_like_provider_fields_are_rejected(
    s6b2a_facts: S6B2AFacts,
) -> None:
    request = _codex_preflight_client(
        s6b2a_facts
    ).prepare_transport_request(_request(s6b2a_facts))
    for field_name in (
        "provider_credentials",
        "api_key",
        "raw_token",
        "chatgpt_auth_file",
    ):
        _assert_unauthorized_transport_field_rejected(request, field_name)


def test_b2close_06_provider_binding_remains_child_side_only(
    s6b2a_facts: S6B2AFacts,
) -> None:
    transport = SubprocessExecutorTransport(provider_binding=CODEX_REAL_BINDING)
    request = DedicatedExecutorClient(
        s6b2a_facts.materialized_input,
        transport=transport,
    ).prepare_transport_request(_request(s6b2a_facts))
    payload = _assert_provider_neutral_transport_request(request)
    assert transport.provider_binding == CODEX_REAL_BINDING
    assert "provider_binding" not in payload


def test_b2close_07_success_and_observed_none_remain_valid(
    s6b2a_facts: S6B2AFacts,
) -> None:
    result = s6b2a_facts.execution.dispatch_and_observe(
        s6b2a_facts.attempt.id,
        _client(s6b2a_facts, ProviderReportedOutcome.SUCCESS),
    )
    assert result.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    assert result.observation.changes == ()
    assert result.work_products == ()
    workspace = s6b2a_facts.prepared.execution_request.workspace.workspace_path
    assert (workspace / TARGET_PATH).read_text(encoding="utf-8") == BEFORE_CONTENT


def test_b2close_08_provider_success_grants_no_completion_authority(
    s6b2a_facts: S6B2AFacts,
) -> None:
    result = s6b2a_facts.execution.dispatch_and_observe(
        s6b2a_facts.attempt.id,
        _client(s6b2a_facts, ProviderReportedOutcome.SUCCESS),
    )
    inspected = RuntimeService(s6b2a_facts.database).inspect_run(
        s6b2a_facts.prepared.execution_request.production_run_id
    )
    assert inspected.work_unit.condition.value == "PROPOSED"
    assert _count(s6b2a_facts.database, completion_evaluations) == 0
    assert _count(s6b2a_facts.database, verification_records) == 0
    assert _count(s6b2a_facts.database, baseline_candidates) == 0
    assert _count(s6b2a_facts.database, runtime_commits) == 0
