"""Provider-neutral transport for a dedicated local Executor process."""

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import subprocess
import sys
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from spg.domain.execution import (
    ExecutorDispatchRequest,
    ExecutorDispatchResult,
    ProviderReportedOutcome,
)
from spg.domain.materialization import MaterializedExecutionInputRecord
from spg.domain.preparation import ExecutorBinding, WorkspaceBinding
from spg.domain.runtime import RuntimeInvariantViolation
from spg.providers.deterministic_executor import (
    DeterministicExecutionSpecification,
    DeterministicFileOperationType,
)


BOUNDARY_PROTOCOL = "spg-dedicated-executor-v1"
EXECUTOR_WIRE_ENCODING = "utf-8"
EXECUTOR_WIRE_ERRORS = "strict"
MAX_PROVIDER_TIMEOUT_SECONDS = 600.0


class ExecutorWorkspacePathMapping(BaseModel):
    """Infrastructure-only mapping; canonical workspace identity stays unchanged."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_identity: str = Field(min_length=1)
    executor_workspace_path: Path


class DedicatedExecutorRequest(BaseModel):
    """Minimal transport projection; deliberately excludes repository/database facts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol: str = BOUNDARY_PROTOCOL
    dispatch_id: UUID
    attempt_id: UUID
    generation: int = Field(ge=1)
    production_run_id: UUID
    work_unit_id: UUID
    plan_revision_id: UUID
    source_baseline_id: UUID
    context_package_id: UUID
    context_package_version: int = Field(ge=1)
    completion_contract_fingerprint: str = Field(min_length=1)
    executor_binding: ExecutorBinding
    materialized_execution_input_id: UUID
    materialized_execution_input_fingerprint: str = Field(min_length=1)
    workspace_identity: str = Field(min_length=1)
    executor_workspace_path: Path
    repository_identity: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    provider_input: str = Field(min_length=1)
    request_fingerprint: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_exact_fingerprint(self) -> "DedicatedExecutorRequest":
        if self.request_fingerprint != _request_fingerprint(self):
            raise ValueError("dedicated Executor request fingerprint mismatch")
        return self


class DedicatedExecutorResponse(BaseModel):
    """Correlated Provider fact returned by the dedicated Executor boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol: str = BOUNDARY_PROTOCOL
    request_fingerprint: str = Field(min_length=1)
    dispatch_id: UUID
    attempt_id: UUID
    generation: int = Field(ge=1)
    materialized_execution_input_id: UUID
    materialized_execution_input_fingerprint: str = Field(min_length=1)
    workspace_identity: str = Field(min_length=1)
    provider_reference: str = Field(min_length=1)
    outcome: ProviderReportedOutcome
    started_at: datetime
    finished_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None


class DedicatedExecutorPreflightResponse(BaseModel):
    """Infrastructure binding result; never a Provider execution report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol: str = BOUNDARY_PROTOCOL
    request_fingerprint: str = Field(min_length=1)
    dispatch_id: UUID
    attempt_id: UUID
    generation: int = Field(ge=1)
    materialized_execution_input_id: UUID
    materialized_execution_input_fingerprint: str = Field(min_length=1)
    workspace_identity: str = Field(min_length=1)
    binding_identity: str = Field(min_length=1)
    binding_status: str = Field(min_length=1)
    provider_outcome: ProviderReportedOutcome = ProviderReportedOutcome.UNKNOWN
    authentication_readiness: str = "REQUIRES_REAL_B2_B2_PROBE"
    provider_turn_started: bool = False
    sdk_version: str | None = None
    adapter_identity: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutorTransportError(RuntimeError):
    """Infrastructure transport failure, not a Provider result."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category


class ExecutorTransport(Protocol):
    def exchange(self, request: DedicatedExecutorRequest) -> str: ...


class SubprocessExecutorTransport:
    """One request/response exchange with an isolated local Executor process."""

    def __init__(
        self,
        *,
        command: Sequence[str] | None = None,
        timeout_seconds: float = 30.0,
        deterministic_specification: DeterministicExecutionSpecification | None = None,
        provider_binding: str | None = None,
        provider_timeout_seconds: float | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.command = tuple(command or (sys.executable, "-m", "spg.executor_service"))
        self.timeout_seconds = timeout_seconds
        self.deterministic_specification = deterministic_specification
        self.provider_binding = provider_binding
        if provider_timeout_seconds is not None and not (
            0 < provider_timeout_seconds <= MAX_PROVIDER_TIMEOUT_SECONDS
        ):
            raise ValueError("provider_timeout_seconds must be within (0, 600]")
        self.provider_timeout_seconds = provider_timeout_seconds
        if deterministic_specification is not None and provider_binding not in {
            None,
            "deterministic-fixture",
        }:
            raise ValueError(
                "deterministic specification requires deterministic-fixture binding"
            )

    def exchange(self, request: DedicatedExecutorRequest) -> str:
        environment = _minimal_executor_environment()
        if self.deterministic_specification is not None:
            environment["SPG_EXECUTOR_PROVIDER_BINDING"] = "deterministic-fixture"
            environment["SPG_EXECUTOR_DETERMINISTIC_SPEC"] = (
                self.deterministic_specification.model_dump_json()
            )
        elif self.provider_binding is not None:
            environment["SPG_EXECUTOR_PROVIDER_BINDING"] = self.provider_binding
        if self.provider_timeout_seconds is not None:
            environment["SPG_EXECUTOR_PROVIDER_TIMEOUT_SECONDS"] = str(
                self.provider_timeout_seconds
            )
        try:
            wire_request = request.model_dump_json().encode(
                EXECUTOR_WIRE_ENCODING,
                EXECUTOR_WIRE_ERRORS,
            )
        except UnicodeError as error:
            raise ExecutorTransportError(
                "PROCESS_ERROR",
                "dedicated Executor request is not valid UTF-8",
            ) from error
        try:
            result = subprocess.run(
                self.command,
                input=wire_request,
                capture_output=True,
                check=False,
                timeout=self.timeout_seconds,
                cwd=request.executor_workspace_path,
                env=environment,
            )
        except subprocess.TimeoutExpired as error:
            raise ExecutorTransportError(
                "TIMEOUT",
                "dedicated Executor transport timed out",
            ) from error
        except OSError as error:
            raise ExecutorTransportError(
                "UNAVAILABLE",
                "dedicated Executor process is unavailable",
            ) from error
        try:
            stdout = result.stdout.decode(
                EXECUTOR_WIRE_ENCODING,
                EXECUTOR_WIRE_ERRORS,
            )
            stderr = result.stderr.decode(
                EXECUTOR_WIRE_ENCODING,
                EXECUTOR_WIRE_ERRORS,
            )
        except UnicodeError as error:
            raise ExecutorTransportError(
                "MALFORMED_RESPONSE",
                "dedicated Executor transport contained invalid UTF-8",
            ) from error
        if result.returncode != 0:
            message = stderr.strip() or "dedicated Executor process failed"
            raise ExecutorTransportError("PROCESS_ERROR", message)
        return stdout


WorkspacePathMapper = Callable[[WorkspaceBinding], ExecutorWorkspacePathMapping]


class DedicatedExecutorClient:
    """Executor Capability adapter whose implementation lives across a process seam."""

    def __init__(
        self,
        materialized_input: MaterializedExecutionInputRecord,
        *,
        transport: ExecutorTransport,
        workspace_path_mapper: WorkspacePathMapper | None = None,
    ) -> None:
        self.materialized_input = materialized_input
        self.transport = transport
        self.workspace_path_mapper = workspace_path_mapper or _identity_path_mapping

    def dispatch(self, request: ExecutorDispatchRequest) -> ExecutorDispatchResult:
        started_at = datetime.now(UTC)
        boundary_request = self.prepare_transport_request(request)
        try:
            raw_response = self.transport.exchange(boundary_request)
        except ExecutorTransportError as error:
            return self._transport_unknown(
                request,
                boundary_request,
                started_at,
                category=error.category,
                detail=str(error),
            )
        except Exception as error:
            return self._transport_unknown(
                request,
                boundary_request,
                started_at,
                category="UNAVAILABLE",
                detail=type(error).__name__,
            )

        try:
            response = DedicatedExecutorResponse.model_validate_json(raw_response)
        except Exception as error:
            return self._transport_unknown(
                request,
                boundary_request,
                started_at,
                category="MALFORMED_RESPONSE",
                detail=type(error).__name__,
            )
        if not _response_matches_request(response, boundary_request):
            return self._transport_unknown(
                request,
                boundary_request,
                started_at,
                category="CORRELATION_MISMATCH",
                detail="dedicated Executor response did not match exact request identity",
            )

        metadata = {
            **response.metadata,
            **_correlation_metadata(boundary_request),
            "executor_transport_status": "COMPLETED",
            "provider_result_present": True,
        }
        return ExecutorDispatchResult(
            provider_reference=response.provider_reference,
            outcome=response.outcome,
            started_at=response.started_at,
            finished_at=response.finished_at,
            metadata=metadata,
            summary=response.summary,
        )

    def preflight_provider_binding(
        self,
        request: ExecutorDispatchRequest,
    ) -> DedicatedExecutorPreflightResponse:
        """Validate a child-side Provider binding without executing the Provider."""

        boundary_request = self.prepare_transport_request(request)
        try:
            raw_response = self.transport.exchange(boundary_request)
        except ExecutorTransportError as error:
            return _preflight_failure(
                boundary_request,
                binding_identity="transport",
                status=f"TRANSPORT_{error.category}",
                detail=str(error),
            )
        except Exception as error:
            return _preflight_failure(
                boundary_request,
                binding_identity="transport",
                status="TRANSPORT_UNAVAILABLE",
                detail=type(error).__name__,
            )
        try:
            response = DedicatedExecutorPreflightResponse.model_validate_json(raw_response)
        except Exception as error:
            return _preflight_failure(
                boundary_request,
                binding_identity="transport",
                status="MALFORMED_RESPONSE",
                detail=type(error).__name__,
            )
        if not _preflight_response_matches_request(response, boundary_request):
            return _preflight_failure(
                boundary_request,
                binding_identity=response.binding_identity,
                status="CORRELATION_MISMATCH",
                detail="preflight response did not match exact request identity",
            )
        return response

    def prepare_transport_request(
        self,
        request: ExecutorDispatchRequest,
    ) -> DedicatedExecutorRequest:
        """Create the exact provider-neutral projection for the process boundary."""
        materialized = self.materialized_input
        execution = request.execution
        if materialized.prepared_execution_request != execution:
            raise RuntimeInvariantViolation(
                "materialized input does not bind the exact Executor dispatch"
            )
        if (
            materialized.attempt_id != execution.attempt_id
            or materialized.generation != execution.generation
            or execution.workspace.workspace_identity
            != f"attempt-worktree:{execution.attempt_id}"
        ):
            raise RuntimeInvariantViolation(
                "dedicated Executor dispatch does not bind exact Attempt identity"
            )
        workspace = execution.workspace.workspace_path.resolve()
        repository = execution.workspace.repository_path.resolve()
        if not workspace.is_dir() or workspace == repository:
            raise RuntimeInvariantViolation(
                "dedicated Executor requires a distinct existing Attempt workspace"
            )
        mapping = self.workspace_path_mapper(execution.workspace)
        if mapping.workspace_identity != execution.workspace.workspace_identity:
            raise RuntimeInvariantViolation(
                "path translation changed canonical Attempt workspace identity"
            )

        basis = {
            "protocol": BOUNDARY_PROTOCOL,
            "dispatch_id": str(request.dispatch_id),
            "attempt_id": str(execution.attempt_id),
            "generation": execution.generation,
            "production_run_id": str(execution.production_run_id),
            "work_unit_id": str(execution.work_unit_id),
            "plan_revision_id": str(execution.plan_revision_id),
            "source_baseline_id": str(execution.source_baseline_id),
            "context_package_id": str(execution.context_package_id),
            "context_package_version": execution.context_package_version,
            "completion_contract_fingerprint": (
                execution.completion_contract_fingerprint
            ),
            "executor_binding": execution.executor_binding.model_dump(mode="json"),
            "materialized_execution_input_id": str(materialized.id),
            "materialized_execution_input_fingerprint": materialized.input_fingerprint,
            "workspace_identity": execution.workspace.workspace_identity,
            "executor_workspace_path": str(mapping.executor_workspace_path),
            "repository_identity": execution.workspace.repository_identity,
            "source_revision": execution.workspace.source_revision,
            "provider_input": materialized.provider_input(),
        }
        return DedicatedExecutorRequest(
            **basis,
            request_fingerprint=_fingerprint(basis),
        )

    @staticmethod
    def _transport_unknown(
        request: ExecutorDispatchRequest,
        boundary_request: DedicatedExecutorRequest,
        started_at: datetime,
        *,
        category: str,
        detail: str,
    ) -> ExecutorDispatchResult:
        return ExecutorDispatchResult(
            provider_reference=f"executor-transport:{request.dispatch_id}",
            outcome=ProviderReportedOutcome.UNKNOWN,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            metadata={
                **_correlation_metadata(boundary_request),
                "executor_transport_status": category,
                "transport_error_detail": detail,
                "provider_result_present": False,
            },
            summary=(
                "Dedicated Executor transport did not yield a correlated Provider result"
            ),
        )


def execute_deterministic_request(
    request: DedicatedExecutorRequest,
    specification: DeterministicExecutionSpecification,
) -> DedicatedExecutorResponse:
    """Dedicated-process entrypoint with no SPG persistence dependency."""

    started_at = datetime.now(UTC)
    expected_identity = f"attempt-worktree:{request.attempt_id}"
    if request.workspace_identity != expected_identity:
        raise RuntimeInvariantViolation(
            "dedicated Executor request has invalid Attempt workspace identity"
        )
    workspace = request.executor_workspace_path.resolve()
    if not workspace.is_dir():
        raise RuntimeInvariantViolation("Executor-local Attempt workspace is unavailable")

    for operation in specification.operations:
        target = _safe_operation_target(workspace, operation.repository_relative_path)
        if operation.operation is DeterministicFileOperationType.CREATE:
            if target.exists():
                raise RuntimeInvariantViolation(
                    "deterministic CREATE target already exists"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(operation.content or "", encoding="utf-8")
        elif operation.operation is DeterministicFileOperationType.MODIFY:
            if not target.is_file():
                raise RuntimeInvariantViolation(
                    "deterministic MODIFY target does not exist"
                )
            target.write_text(operation.content or "", encoding="utf-8")
        else:
            if not target.is_file():
                raise RuntimeInvariantViolation(
                    "deterministic DELETE target does not exist"
                )
            target.unlink()

    finished_at = datetime.now(UTC)
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
        provider_reference=f"deterministic-boundary:{request.dispatch_id}",
        outcome=specification.reported_outcome,
        started_at=started_at,
        finished_at=finished_at,
        metadata={
            "deterministic_operation_count": len(specification.operations),
            "executor_boundary": "DEDICATED_LOCAL_PROCESS",
            "database_configuration_present": "SPG_DATABASE_URL" in os.environ,
        },
        summary=specification.summary,
    )


def _identity_path_mapping(workspace: WorkspaceBinding) -> ExecutorWorkspacePathMapping:
    return ExecutorWorkspacePathMapping(
        workspace_identity=workspace.workspace_identity,
        executor_workspace_path=workspace.workspace_path,
    )


def _safe_operation_target(workspace: Path, relative_path: str) -> Path:
    target = workspace / relative_path
    resolved = target.resolve(strict=False)
    try:
        resolved.relative_to(workspace)
    except ValueError as error:
        raise RuntimeInvariantViolation(
            "deterministic operation escapes the Executor Attempt workspace"
        ) from error
    return resolved


def _request_fingerprint(request: DedicatedExecutorRequest) -> str:
    return _fingerprint(
        request.model_dump(mode="json", exclude={"request_fingerprint"})
    )


def _fingerprint(value: object) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return sha256(canonical).hexdigest()


def _response_matches_request(
    response: DedicatedExecutorResponse,
    request: DedicatedExecutorRequest,
) -> bool:
    return (
        response.protocol == request.protocol
        and response.request_fingerprint == request.request_fingerprint
        and response.dispatch_id == request.dispatch_id
        and response.attempt_id == request.attempt_id
        and response.generation == request.generation
        and response.materialized_execution_input_id
        == request.materialized_execution_input_id
        and response.materialized_execution_input_fingerprint
        == request.materialized_execution_input_fingerprint
        and response.workspace_identity == request.workspace_identity
    )


def _preflight_response_matches_request(
    response: DedicatedExecutorPreflightResponse,
    request: DedicatedExecutorRequest,
) -> bool:
    return (
        response.protocol == request.protocol
        and response.request_fingerprint == request.request_fingerprint
        and response.dispatch_id == request.dispatch_id
        and response.attempt_id == request.attempt_id
        and response.generation == request.generation
        and response.materialized_execution_input_id
        == request.materialized_execution_input_id
        and response.materialized_execution_input_fingerprint
        == request.materialized_execution_input_fingerprint
        and response.workspace_identity == request.workspace_identity
        and response.provider_outcome is ProviderReportedOutcome.UNKNOWN
        and response.provider_turn_started is False
    )


def _preflight_failure(
    request: DedicatedExecutorRequest,
    *,
    binding_identity: str,
    status: str,
    detail: str,
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
        metadata={"infrastructure_failure_detail": detail},
    )


def _correlation_metadata(request: DedicatedExecutorRequest) -> dict[str, object]:
    return {
        "executor_boundary_protocol": request.protocol,
        "executor_request_fingerprint": request.request_fingerprint,
        "dispatch_id": str(request.dispatch_id),
        "attempt_id": str(request.attempt_id),
        "generation": request.generation,
        "materialized_execution_input_id": str(
            request.materialized_execution_input_id
        ),
        "materialized_execution_input_fingerprint": (
            request.materialized_execution_input_fingerprint
        ),
        "workspace_identity": request.workspace_identity,
        "executor_workspace_path": str(request.executor_workspace_path),
    }


def build_executor_child_environment(
    source_environment: Mapping[str, str] | None = None,
    *,
    platform_name: str | None = None,
) -> dict[str, str]:
    """Project a narrow, cross-platform environment for the Executor child."""

    source = os.environ if source_environment is None else source_environment
    is_windows = (platform_name or os.name).casefold() in {"nt", "win32", "windows"}
    allowed = (
        (
            "USERPROFILE",
            "SYSTEMROOT",
            "PATH",
            "PYTHONPATH",
            "TEMP",
            "TMP",
            "APPDATA",
            "LOCALAPPDATA",
            "LANG",
            "LC_ALL",
        )
        if is_windows
        else (
            "HOME",
            "PATH",
            "PYTHONPATH",
            "TMPDIR",
            "LANG",
            "LC_ALL",
        )
    )
    environment: dict[str, str] = {}
    for name in allowed:
        value = _environment_value(source, name, case_insensitive=is_windows)
        if value:
            environment[name] = value

    codex_home = _resolve_codex_home(source, is_windows=is_windows)
    if codex_home is not None:
        environment["CODEX_HOME"] = codex_home
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def _minimal_executor_environment() -> dict[str, str]:
    return build_executor_child_environment()


def _resolve_codex_home(
    source: Mapping[str, str],
    *,
    is_windows: bool,
) -> str | None:
    explicit = _environment_value(
        source,
        "CODEX_HOME",
        case_insensitive=is_windows,
    )
    if explicit:
        return _require_absolute_state_root(
            explicit,
            variable_name="CODEX_HOME",
            is_windows=is_windows,
        )

    native_home_name = "USERPROFILE" if is_windows else "HOME"
    native_home = _environment_value(
        source,
        native_home_name,
        case_insensitive=is_windows,
    )
    if not native_home:
        return None
    native_root = _require_absolute_state_root(
        native_home,
        variable_name=native_home_name,
        is_windows=is_windows,
    )
    if is_windows:
        return str(PureWindowsPath(native_root) / ".codex")
    return str(PurePosixPath(native_root) / ".codex")


def _require_absolute_state_root(
    value: str,
    *,
    variable_name: str,
    is_windows: bool,
) -> str:
    path = PureWindowsPath(value) if is_windows else PurePosixPath(value)
    if not path.is_absolute():
        raise RuntimeInvariantViolation(
            f"{variable_name} must identify an absolute Executor state root"
        )
    return str(path)


def _environment_value(
    source: Mapping[str, str],
    name: str,
    *,
    case_insensitive: bool,
) -> str | None:
    if not case_insensitive:
        return source.get(name)
    exact = source.get(name)
    if exact is not None:
        return exact
    expected = name.casefold()
    for candidate, value in source.items():
        if candidate.casefold() == expected:
            return value
    return None
