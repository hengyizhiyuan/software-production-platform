"""S6-C2-R2 explicit UTF-8 Dedicated Executor transport validation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest

from spg.domain.execution import ExecutorDispatchRequest, ProviderReportedOutcome
from spg.domain.materialization import (
    MaterializedContextArtifact,
    MaterializedExecutionInputRecord,
)
from spg.domain.preparation import (
    ContextSemanticRole,
    ExecutorBinding,
    PreparedExecutionRequest,
    WorkspaceBinding,
)
from spg.infrastructure.executor_boundary import (
    EXECUTOR_WIRE_ENCODING,
    EXECUTOR_WIRE_ERRORS,
    DedicatedExecutorClient,
    DedicatedExecutorRequest,
    SubprocessExecutorTransport,
    build_executor_child_environment,
)


SUCCESS_CHILD = r"""
from datetime import UTC, datetime
from hashlib import sha256
import os
import sys

from spg.domain.execution import ProviderReportedOutcome
from spg.infrastructure.executor_boundary import (
    DedicatedExecutorRequest,
    DedicatedExecutorResponse,
)

request = DedicatedExecutorRequest.model_validate_json(sys.stdin.read())
timestamp = datetime.now(UTC)
response = DedicatedExecutorResponse(
    request_fingerprint=request.request_fingerprint,
    dispatch_id=request.dispatch_id,
    attempt_id=request.attempt_id,
    generation=request.generation,
    materialized_execution_input_id=request.materialized_execution_input_id,
    materialized_execution_input_fingerprint=(
        request.materialized_execution_input_fingerprint
    ),
    workspace_identity=request.workspace_identity,
    provider_reference="deterministic:utf8-transport-child",
    outcome=ProviderReportedOutcome.SUCCESS,
    started_at=timestamp,
    finished_at=timestamp,
    metadata={
        "诊断": "子进程响应正常",
        "structured": {"状态": "已解析", "说明": "保持原始 Unicode"},
        "provider_input_length": len(request.provider_input),
        "provider_input_sha256": sha256(
            request.provider_input.encode("utf-8")
        ).hexdigest(),
        "database_configuration_present": "SPG_DATABASE_URL" in os.environ,
        "openai_api_key_present": "OPENAI_API_KEY" in os.environ,
        "other_provider_token_present": "OTHER_PROVIDER_TOKEN" in os.environ,
        "provider_thread_started": False,
        "provider_turn_started": False,
    },
    summary="执行器响应：Unicode 往返成功",
)
print(response.model_dump_json(), flush=True)
"""


ASCII_CHILD = r"""
from datetime import UTC, datetime
import sys

from spg.domain.execution import ProviderReportedOutcome
from spg.infrastructure.executor_boundary import (
    DedicatedExecutorRequest,
    DedicatedExecutorResponse,
)

request = DedicatedExecutorRequest.model_validate_json(sys.stdin.read())
timestamp = datetime.now(UTC)
response = DedicatedExecutorResponse(
    request_fingerprint=request.request_fingerprint,
    dispatch_id=request.dispatch_id,
    attempt_id=request.attempt_id,
    generation=request.generation,
    materialized_execution_input_id=request.materialized_execution_input_id,
    materialized_execution_input_fingerprint=(
        request.materialized_execution_input_fingerprint
    ),
    workspace_identity=request.workspace_identity,
    provider_reference="deterministic:ascii-transport-child",
    outcome=ProviderReportedOutcome.SUCCESS,
    started_at=timestamp,
    finished_at=timestamp,
    metadata={"provider_thread_started": False, "provider_turn_started": False},
    summary="ASCII transport remains compatible",
)
print(response.model_dump_json(), flush=True)
"""


NON_ASCII_ERROR_CHILD = r"""
import sys

from spg.infrastructure.executor_boundary import DedicatedExecutorRequest

DedicatedExecutorRequest.model_validate_json(sys.stdin.read())
print("子进程诊断：合成错误，不启动 Provider", file=sys.stderr, flush=True)
raise SystemExit(2)
"""


INVALID_UTF8_CHILD = r"""
import sys

from spg.infrastructure.executor_boundary import DedicatedExecutorRequest

DedicatedExecutorRequest.model_validate_json(sys.stdin.read())
sys.stdout.buffer.write(b"\xff\xfe")
sys.stdout.buffer.flush()
"""


@dataclass(frozen=True)
class Utf8TransportCase:
    client: DedicatedExecutorClient
    transport: SubprocessExecutorTransport
    dispatch: ExecutorDispatchRequest
    boundary: DedicatedExecutorRequest
    materialized: MaterializedExecutionInputRecord


def _case(
    tmp_path: Path,
    child_script: str,
    *,
    instruction: str = "生产目标：生成受治理的软件文档。",
    context: str = "约束：不得扩大范围；不得启动真实 Provider。",
) -> Utf8TransportCase:
    repository = tmp_path / "authoritative-repository"
    workspace = tmp_path / "attempt-workspace"
    repository.mkdir()
    workspace.mkdir()

    attempt_id = uuid4()
    production_run_id = uuid4()
    work_unit_id = uuid4()
    plan_revision_id = uuid4()
    source_baseline_id = uuid4()
    context_package_id = uuid4()
    materialized_id = uuid4()
    source_revision = "a" * 40
    binding = ExecutorBinding(
        binding_ref="binding:utf8-deterministic-child",
        capability_identity="capability:executor",
        profile_identity="profile:dedicated-process",
    )
    workspace_binding = WorkspaceBinding(
        workspace_identity=f"attempt-worktree:{attempt_id}",
        workspace_path=workspace,
        repository_identity="repository:utf8-fixture",
        repository_path=repository,
        source_revision=source_revision,
    )
    prepared = PreparedExecutionRequest(
        attempt_id=attempt_id,
        generation=1,
        production_run_id=production_run_id,
        work_unit_id=work_unit_id,
        plan_revision_id=plan_revision_id,
        source_baseline_id=source_baseline_id,
        context_package_id=context_package_id,
        context_package_version=1,
        completion_contract_fingerprint="completion:" + "b" * 64,
        executor_binding=binding,
        workspace=workspace_binding,
    )
    materialized = MaterializedExecutionInputRecord(
        id=materialized_id,
        attempt_id=attempt_id,
        generation=1,
        production_run_id=production_run_id,
        work_unit_id=work_unit_id,
        plan_revision_id=plan_revision_id,
        source_baseline_id=source_baseline_id,
        context_package_id=context_package_id,
        context_package_version=1,
        context_package_content_fingerprint="context:" + "c" * 64,
        completion_contract_fingerprint=prepared.completion_contract_fingerprint,
        prepared_execution_request=prepared,
        instruction_content=instruction,
        context_projection=(
            MaterializedContextArtifact(
                semantic_role=ContextSemanticRole.CONSTRAINT,
                repository_relative_path="docs/utf8-fixture.md",
                source_revision=source_revision,
                blob_fingerprint="blob:" + "d" * 64,
                content=context,
            ),
        ),
        input_fingerprint="input:" + "e" * 64,
        created_at=datetime.now(UTC),
    )
    transport = SubprocessExecutorTransport(
        command=(sys.executable, "-c", child_script),
    )
    client = DedicatedExecutorClient(materialized, transport=transport)
    dispatch = ExecutorDispatchRequest(
        dispatch_id=uuid4(),
        execution=prepared,
    )
    return Utf8TransportCase(
        client=client,
        transport=transport,
        dispatch=dispatch,
        boundary=client.prepare_transport_request(dispatch),
        materialized=materialized,
    )


def _provider_input_hash(case: Utf8TransportCase) -> str:
    return sha256(case.materialized.provider_input().encode("utf-8")).hexdigest()


def test_utf8_01_default_locale_independent_non_ascii_request_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYTHONUTF8", raising=False)
    monkeypatch.delenv("PYTHONIOENCODING", raising=False)
    case = _case(tmp_path, SUCCESS_CHILD)

    result = case.client.dispatch(case.dispatch)

    assert result.outcome is ProviderReportedOutcome.SUCCESS
    assert result.metadata["provider_input_sha256"] == _provider_input_hash(case)


def test_utf8_02_chinese_materialized_input_parses_exactly_in_child(
    tmp_path: Path,
) -> None:
    case = _case(
        tmp_path,
        SUCCESS_CHILD,
        instruction="生产目标：维护长期意图与工程边界。",
        context="约束与非目标：不得执行真实模型；不得改变生产状态。",
    )

    result = case.client.dispatch(case.dispatch)

    assert result.metadata["provider_input_length"] == len(
        case.materialized.provider_input()
    )
    assert result.metadata["provider_input_sha256"] == _provider_input_hash(case)


def test_utf8_03_large_payload_preserves_fingerprint_and_correlation(
    tmp_path: Path,
) -> None:
    context = ("工程上下文：保持目标、约束、证据与基线。\n" * 12_000)
    case = _case(tmp_path, SUCCESS_CHILD, context=context)
    assert len(case.boundary.model_dump_json()) > 200_000

    result = case.client.dispatch(case.dispatch)

    assert result.metadata["executor_request_fingerprint"] == (
        case.boundary.request_fingerprint
    )
    assert result.metadata["dispatch_id"] == str(case.dispatch.dispatch_id)
    assert result.metadata["materialized_execution_input_id"] == str(
        case.materialized.id
    )


def test_utf8_04_non_ascii_child_response_decodes_exactly(tmp_path: Path) -> None:
    case = _case(tmp_path, SUCCESS_CHILD)

    result = case.client.dispatch(case.dispatch)

    assert result.summary == "执行器响应：Unicode 往返成功"
    assert result.metadata["诊断"] == "子进程响应正常"
    assert result.metadata["structured"] == {
        "状态": "已解析",
        "说明": "保持原始 Unicode",
    }


def test_utf8_05_non_ascii_stderr_is_deterministic_and_conservative(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path, NON_ASCII_ERROR_CHILD)

    result = case.client.dispatch(case.dispatch)

    assert result.outcome is ProviderReportedOutcome.UNKNOWN
    assert result.metadata["executor_transport_status"] == "PROCESS_ERROR"
    assert "子进程诊断：合成错误，不启动 Provider" in result.metadata[
        "transport_error_detail"
    ]


def test_utf8_06_invalid_utf8_response_maps_to_conservative_transport_failure(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path, INVALID_UTF8_CHILD)

    result = case.client.dispatch(case.dispatch)

    assert result.outcome is ProviderReportedOutcome.UNKNOWN
    assert result.metadata["executor_transport_status"] == "MALFORMED_RESPONSE"
    assert result.metadata["transport_error_detail"] == (
        "dedicated Executor transport contained invalid UTF-8"
    )


def test_utf8_07_transport_failure_never_manufactures_provider_terminal_outcome(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path, INVALID_UTF8_CHILD)

    result = case.client.dispatch(case.dispatch)

    assert result.outcome not in {
        ProviderReportedOutcome.SUCCESS,
        ProviderReportedOutcome.FAILURE,
    }
    assert result.metadata["provider_result_present"] is False


def test_utf8_08_wire_encoding_is_explicit_without_parent_pythonutf8(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PYTHONUTF8", raising=False)
    observed: dict[str, object] = {}
    real_run = subprocess.run

    def capturing_run(*args, **kwargs):
        observed.update(kwargs)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", capturing_run)
    case = _case(tmp_path, SUCCESS_CHILD)

    result = case.client.dispatch(case.dispatch)

    assert result.outcome is ProviderReportedOutcome.SUCCESS
    assert isinstance(observed["input"], bytes)
    assert observed["input"].decode(
        EXECUTOR_WIRE_ENCODING,
        EXECUTOR_WIRE_ERRORS,
    ) == case.boundary.model_dump_json()
    assert EXECUTOR_WIRE_ENCODING == "utf-8"
    assert EXECUTOR_WIRE_ERRORS == "strict"


def test_utf8_09_parent_environment_is_not_persistently_mutated(
    tmp_path: Path,
) -> None:
    names = ("HOME", "USERPROFILE", "PYTHONUTF8", "PYTHONIOENCODING")
    before = {name: os.environ.get(name) for name in names}
    case = _case(tmp_path, SUCCESS_CHILD)

    case.client.dispatch(case.dispatch)

    assert {name: os.environ.get(name) for name in names} == before


def test_utf8_10_credential_and_database_filtering_remains_intact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPG_DATABASE_URL", "postgresql://secret.invalid/runtime")
    monkeypatch.setenv("OPENAI_API_KEY", "not-forwarded")
    monkeypatch.setenv("OTHER_PROVIDER_TOKEN", "not-forwarded")
    case = _case(tmp_path, SUCCESS_CHILD)

    result = case.client.dispatch(case.dispatch)

    assert result.metadata["database_configuration_present"] is False
    assert result.metadata["openai_api_key_present"] is False
    assert result.metadata["other_provider_token_present"] is False


def test_utf8_11_canonical_execution_identity_survives_protocol(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path, SUCCESS_CHILD)

    result = case.client.dispatch(case.dispatch)

    assert result.metadata["attempt_id"] == str(case.dispatch.execution.attempt_id)
    assert result.metadata["generation"] == case.dispatch.execution.generation
    assert result.metadata["workspace_identity"] == (
        case.dispatch.execution.workspace.workspace_identity
    )
    assert result.metadata["materialized_execution_input_fingerprint"] == (
        case.materialized.input_fingerprint
    )


def test_utf8_12_deterministic_transport_creates_no_provider_thread_or_turn(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path, SUCCESS_CHILD)

    result = case.client.dispatch(case.dispatch)

    assert result.metadata["provider_thread_started"] is False
    assert result.metadata["provider_turn_started"] is False
    assert "thread_id" not in result.metadata
    assert "turn_id" not in result.metadata


def test_utf8_13_existing_ascii_transport_behavior_remains_compatible(
    tmp_path: Path,
) -> None:
    case = _case(
        tmp_path,
        ASCII_CHILD,
        instruction="Produce the governed documentation artifact.",
        context="Do not expand scope or start a real Provider.",
    )

    result = case.client.dispatch(case.dispatch)

    assert result.outcome is ProviderReportedOutcome.SUCCESS
    assert result.summary == "ASCII transport remains compatible"


def test_utf8_14_posix_child_environment_remains_compatible() -> None:
    source = {
        "HOME": "/home/spg",
        "PATH": "/usr/bin",
        "PYTHONUTF8": "0",
        "SPG_DATABASE_URL": "postgresql://secret.invalid/runtime",
    }

    child = build_executor_child_environment(source, platform_name="posix")

    assert child == {
        "HOME": "/home/spg",
        "PATH": "/usr/bin",
        "CODEX_HOME": "/home/spg/.codex",
        "PYTHONIOENCODING": "utf-8",
    }
    assert EXECUTOR_WIRE_ENCODING == "utf-8"
    assert EXECUTOR_WIRE_ERRORS == "strict"
