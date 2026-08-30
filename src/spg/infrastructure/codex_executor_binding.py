"""Child-side Codex adapter binding for preflight and governed execution."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
import subprocess
from typing import Any

from spg.domain.execution import (
    ExecutorDispatchRequest,
    ExecutorDispatchResult,
    ProviderReportedOutcome,
)
from spg.domain.preparation import PreparedExecutionRequest, WorkspaceBinding
from spg.domain.runtime import RuntimeInvariantViolation
from spg.infrastructure.executor_boundary import (
    DedicatedExecutorPreflightResponse,
    DedicatedExecutorRequest,
    DedicatedExecutorResponse,
)


CODEX_BINDING = "codex-sdk-preflight"
CODEX_REAL_BINDING = "codex-sdk-real"
AUTH_READINESS = "REQUIRES_REAL_B2_B2_PROBE"
REAL_PROVIDER_TIMEOUT_SECONDS = 120.0
HIDDEN_REPOSITORY_PATH = Path("/__spg_authoritative_repository_not_exposed__")
REQUIRED_RUNTIME_PREREQUISITES = ("HOME", "PATH")


@dataclass(frozen=True)
class TransportMaterializedExecutionInput:
    """Exact child-side input binding reconstructed without repository authority."""

    id: object
    attempt_id: object
    generation: int
    input_fingerprint: str
    prepared_execution_request: PreparedExecutionRequest
    provider_input_content: str

    def provider_input(self) -> str:
        return self.provider_input_content


SdkVersionResolver = Callable[[], str]
AdapterFactory = Callable[..., Any]


def preflight_codex_binding(
    request: DedicatedExecutorRequest,
    *,
    environment: Mapping[str, str],
    sdk_version_resolver: SdkVersionResolver | None = None,
    adapter_factory: AdapterFactory | None = None,
) -> DedicatedExecutorPreflightResponse:
    """Bind and validate the existing adapter while guaranteeing zero Turns."""

    missing = tuple(
        prerequisite
        for prerequisite in REQUIRED_RUNTIME_PREREQUISITES
        if not environment.get(prerequisite)
    )
    if missing:
        return _response(
            request,
            status="MISSING_RUNTIME_PREREQUISITE",
            metadata={"missing_runtime_prerequisites": list(missing)},
        )

    resolver = sdk_version_resolver or (lambda: version("openai-codex"))
    try:
        sdk_version = resolver()
    except Exception as error:
        return _response(
            request,
            status="SDK_UNAVAILABLE",
            metadata={"failure_type": type(error).__name__},
        )

    selected_adapter_factory = adapter_factory
    if selected_adapter_factory is None:
        try:
            from spg.providers.codex_sdk_executor import CodexSdkExecutor
        except Exception as error:
            return _response(
                request,
                status="SDK_UNAVAILABLE",
                sdk_version=sdk_version,
                metadata={"failure_type": type(error).__name__},
            )
        selected_adapter_factory = CodexSdkExecutor

    dispatch, materialized = _translated_binding(request)
    try:
        adapter = selected_adapter_factory(
            materialized,
            workspace_validator=_validate_translated_workspace,
        )
        adapter_metadata = adapter.preflight(dispatch)
    except Exception as error:
        return _response(
            request,
            status="ADAPTER_INITIALIZATION_FAILED",
            sdk_version=sdk_version,
            metadata={"failure_type": type(error).__name__},
        )

    return _response(
        request,
        status="READY_FOR_REAL_PROBE_AUTH_UNPROVEN",
        sdk_version=sdk_version,
        adapter_identity=(
            "spg.providers.codex_sdk_executor.CodexSdkExecutor"
        ),
        metadata={
            **adapter_metadata,
            "environment_policy": "NARROW_ALLOWLIST",
            "permitted_environment_classes": [
                "home-directory-location",
                "executable-search-path",
                "locale",
                "temporary-directory",
                "python-module-path",
            ],
            "spg_database_configuration_present": (
                "SPG_DATABASE_URL" in environment
            ),
            "authentication_secret_inspected": False,
        },
    )


def execute_codex_binding(
    request: DedicatedExecutorRequest,
    *,
    environment: Mapping[str, str],
    adapter_factory: AdapterFactory | None = None,
    timeout_seconds: float = REAL_PROVIDER_TIMEOUT_SECONDS,
) -> DedicatedExecutorResponse:
    """Run one exact materialized input through the existing Codex adapter."""

    started_at = datetime.now(UTC)
    missing = tuple(
        prerequisite
        for prerequisite in REQUIRED_RUNTIME_PREREQUISITES
        if not environment.get(prerequisite)
    )
    if missing:
        return _execution_response(
            request,
            ExecutorDispatchResult(
                provider_reference=f"codex-sdk:dispatch:{request.dispatch_id}",
                outcome=ProviderReportedOutcome.UNKNOWN,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                metadata={
                    "provider_turn_started": False,
                    "provider_identity_state": "MISSING",
                    "binding_failure": "MISSING_RUNTIME_PREREQUISITE",
                    "missing_runtime_prerequisites": list(missing),
                },
                summary="Codex binding runtime prerequisites are unavailable",
            ),
            environment=environment,
        )

    selected_adapter_factory = adapter_factory
    if selected_adapter_factory is None:
        from spg.providers.codex_sdk_executor import CodexSdkExecutor

        selected_adapter_factory = CodexSdkExecutor

    dispatch, materialized = _translated_binding(request)
    try:
        adapter = selected_adapter_factory(
            materialized,
            timeout_seconds=timeout_seconds,
            workspace_validator=_validate_translated_workspace,
        )
        result = adapter.dispatch(dispatch)
    except Exception as error:
        result = ExecutorDispatchResult(
            provider_reference=f"codex-sdk:dispatch:{request.dispatch_id}",
            outcome=ProviderReportedOutcome.UNKNOWN,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            metadata={
                "provider_turn_started": False,
                "provider_identity_state": "MISSING",
                "binding_failure": "ADAPTER_INITIALIZATION_FAILED",
                "exception_type": type(error).__name__,
            },
            summary="Codex adapter initialization or dispatch failed",
        )
    return _execution_response(request, result, environment=environment)


def unsupported_provider_binding(
    request: DedicatedExecutorRequest,
    binding_identity: str,
) -> DedicatedExecutorPreflightResponse:
    return _response(
        request,
        status="UNSUPPORTED_PROVIDER_BINDING",
        binding_identity=binding_identity,
    )


def _translated_binding(
    request: DedicatedExecutorRequest,
) -> tuple[ExecutorDispatchRequest, TransportMaterializedExecutionInput]:
    workspace = WorkspaceBinding(
        workspace_identity=request.workspace_identity,
        workspace_path=request.executor_workspace_path,
        repository_identity=request.repository_identity,
        repository_path=HIDDEN_REPOSITORY_PATH,
        source_revision=request.source_revision,
    )
    execution = PreparedExecutionRequest(
        attempt_id=request.attempt_id,
        generation=request.generation,
        production_run_id=request.production_run_id,
        work_unit_id=request.work_unit_id,
        plan_revision_id=request.plan_revision_id,
        source_baseline_id=request.source_baseline_id,
        context_package_id=request.context_package_id,
        context_package_version=request.context_package_version,
        completion_contract_fingerprint=request.completion_contract_fingerprint,
        executor_binding=request.executor_binding,
        workspace=workspace,
    )
    materialized = TransportMaterializedExecutionInput(
        id=request.materialized_execution_input_id,
        attempt_id=request.attempt_id,
        generation=request.generation,
        input_fingerprint=request.materialized_execution_input_fingerprint,
        prepared_execution_request=execution,
        provider_input_content=request.provider_input,
    )
    return (
        ExecutorDispatchRequest(
            dispatch_id=request.dispatch_id,
            execution=execution,
        ),
        materialized,
    )


def _validate_translated_workspace(workspace: WorkspaceBinding) -> None:
    expected_identity = f"attempt-worktree:{workspace.workspace_identity.split(':')[-1]}"
    if workspace.workspace_identity != expected_identity:
        raise RuntimeInvariantViolation("translated workspace identity is invalid")
    physical = workspace.workspace_path.resolve()
    if not physical.is_dir():
        raise RuntimeInvariantViolation("translated Attempt workspace is unavailable")
    result = subprocess.run(
        ["git", "-C", str(physical), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or result.stdout.strip() != workspace.source_revision:
        raise RuntimeInvariantViolation(
            "translated Attempt workspace does not match Source Baseline"
        )


def _response(
    request: DedicatedExecutorRequest,
    *,
    status: str,
    binding_identity: str = CODEX_BINDING,
    sdk_version: str | None = None,
    adapter_identity: str | None = None,
    metadata: dict[str, object] | None = None,
) -> DedicatedExecutorPreflightResponse:
    return DedicatedExecutorPreflightResponse(
        request_fingerprint=request.request_fingerprint,
        dispatch_id=request.dispatch_id,
        attempt_id=request.attempt_id,
        generation=request.generation,
        materialized_execution_input_id=request.materialized_execution_input_id,
        materialized_execution_input_fingerprint=(
            request.materialized_execution_input_fingerprint
        ),
        workspace_identity=request.workspace_identity,
        binding_identity=binding_identity,
        binding_status=status,
        authentication_readiness=AUTH_READINESS,
        provider_turn_started=False,
        sdk_version=sdk_version,
        adapter_identity=adapter_identity,
        metadata=metadata or {},
    )


def _execution_response(
    request: DedicatedExecutorRequest,
    result: ExecutorDispatchResult,
    *,
    environment: Mapping[str, str],
) -> DedicatedExecutorResponse:
    metadata = {
        **result.metadata,
        "executor_boundary": "DEDICATED_LOCAL_PROCESS",
        "provider_binding_selected_in_child": True,
        "child_provider_binding": CODEX_REAL_BINDING,
        "spg_database_configuration_present": "SPG_DATABASE_URL" in environment,
        "authentication_secret_inspected": False,
    }
    provider_turn_started = bool(metadata.get("turn_id"))
    metadata["provider_turn_started"] = provider_turn_started
    metadata["authenticated_provider_execution"] = (
        "PROVEN" if provider_turn_started else "NOT_PROVEN"
    )
    return DedicatedExecutorResponse(
        request_fingerprint=request.request_fingerprint,
        dispatch_id=request.dispatch_id,
        attempt_id=request.attempt_id,
        generation=request.generation,
        materialized_execution_input_id=request.materialized_execution_input_id,
        materialized_execution_input_fingerprint=(
            request.materialized_execution_input_fingerprint
        ),
        workspace_identity=request.workspace_identity,
        provider_reference=result.provider_reference,
        outcome=result.outcome,
        started_at=result.started_at,
        finished_at=result.finished_at,
        metadata=metadata,
        summary=result.summary,
    )
