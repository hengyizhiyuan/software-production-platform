"""Official Python Codex SDK implementation of the Executor capability."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import Any, Protocol

from openai_codex import ApprovalMode, Codex, Sandbox

from spg.domain.execution import (
    ExecutorDispatchRequest,
    ExecutorDispatchResult,
    ProviderReportedOutcome,
)
from spg.domain.preparation import PreparedExecutionRequest, WorkspaceBinding
from spg.domain.runtime import RuntimeInvariantViolation
from spg.infrastructure.git_workspace import GitAttemptWorkspace


CodexFactory = Callable[[], AbstractContextManager[Any]]
WorkspaceValidator = Callable[[WorkspaceBinding], None]
INTERRUPT_GRACE_SECONDS = 5.0


class MaterializedExecutorInput(Protocol):
    id: object
    attempt_id: object
    generation: int
    input_fingerprint: str
    prepared_execution_request: PreparedExecutionRequest

    def provider_input(self) -> str: ...


@dataclass(frozen=True)
class _TerminalWait:
    result: Any | None = None
    timed_out: bool = False
    timeout_at: datetime | None = None
    interrupt_requested: bool = False
    interrupt_error_type: str | None = None
    post_timeout_error_type: str | None = None


class CodexSdkExecutor:
    """Synchronous host-local SDK adapter for one exact materialized input."""

    def __init__(
        self,
        materialized_input: MaterializedExecutorInput,
        *,
        codex_factory: CodexFactory | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        sandbox: Sandbox = Sandbox.workspace_write,
        workspace_validator: WorkspaceValidator | None = None,
    ) -> None:
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive when provided")
        self.materialized_input = materialized_input
        self.codex_factory = codex_factory or Codex
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.sandbox = sandbox
        self.workspace_validator = workspace_validator or _validate_host_workspace

    def preflight(self, request: ExecutorDispatchRequest) -> dict[str, Any]:
        """Validate exact adapter binding without constructing Codex or starting a Turn."""

        self._validate_dispatch(request)
        return self._metadata(request, thread_id=None, turn_id=None) | {
            "provider_turn_started": False,
            "preflight_only": True,
        }

    def dispatch(self, request: ExecutorDispatchRequest) -> ExecutorDispatchResult:
        started_at = datetime.now(UTC)
        self._validate_dispatch(request)
        workspace = request.execution.workspace.workspace_path.resolve()
        thread_id: str | None = None
        turn_id: str | None = None
        provider_reference = f"codex-sdk:dispatch:{request.dispatch_id}"
        metadata = self._metadata(request, thread_id=thread_id, turn_id=turn_id)

        try:
            with self.codex_factory() as codex:
                thread = codex.thread_start(
                    approval_mode=ApprovalMode.deny_all,
                    cwd=str(workspace),
                    ephemeral=True,
                    model=self.model,
                    sandbox=self.sandbox,
                )
                thread_id = str(thread.id)
                provider_reference = f"codex-sdk:thread:{thread_id}"
                turn = thread.turn(
                    self.materialized_input.provider_input(),
                    approval_mode=ApprovalMode.deny_all,
                    cwd=str(workspace),
                    model=self.model,
                    sandbox=self.sandbox,
                )
                turn_id = str(turn.id)
                provider_reference = f"codex-sdk:thread:{thread_id}:turn:{turn_id}"
                metadata = self._metadata(
                    request,
                    thread_id=thread_id,
                    turn_id=turn_id,
                )
                terminal = _wait_for_terminal(turn, self.timeout_seconds)
                if terminal.timed_out:
                    metadata.update(
                        {
                            "terminal_result_within_timeout": False,
                            "timeout_seconds": self.timeout_seconds,
                            "timeout_at": terminal.timeout_at.isoformat()
                            if terminal.timeout_at is not None
                            else None,
                            "interrupt_requested": terminal.interrupt_requested,
                            "interrupt_error_type": terminal.interrupt_error_type,
                            "post_timeout_error_type": (
                                terminal.post_timeout_error_type
                            ),
                            "post_timeout_status": _enum_value(
                                terminal.result.status
                            )
                            if terminal.result is not None
                            else None,
                            "post_timeout_started_at": getattr(
                                terminal.result,
                                "started_at",
                                None,
                            ),
                            "post_timeout_completed_at": getattr(
                                terminal.result,
                                "completed_at",
                                None,
                            ),
                            "post_timeout_duration_ms": getattr(
                                terminal.result,
                                "duration_ms",
                                None,
                            ),
                        }
                    )
                    return ExecutorDispatchResult(
                        provider_reference=provider_reference,
                        outcome=ProviderReportedOutcome.UNKNOWN,
                        started_at=started_at,
                        finished_at=datetime.now(UTC),
                        metadata=metadata,
                        summary=(
                            "Codex turn exceeded the bounded terminal wait; "
                            "Provider outcome remains UNKNOWN"
                        ),
                    )

                result = terminal.result
                if result is None:
                    raise RuntimeError("Codex terminal wait returned no result")
                status = _enum_value(result.status)
                result_turn_id = str(result.id)
                identity_matches = result_turn_id == turn_id
                outcome = (
                    _map_outcome(status)
                    if identity_matches
                    else ProviderReportedOutcome.UNKNOWN
                )
                metadata.update(
                    {
                        "terminal_result_within_timeout": True,
                        "turn_status": status,
                        "terminal_turn_id": result_turn_id,
                        "terminal_identity_matches": identity_matches,
                        "turn_error_present": result.error is not None,
                        "sdk_started_at": result.started_at,
                        "sdk_completed_at": result.completed_at,
                        "sdk_duration_ms": result.duration_ms,
                    }
                )
        except RuntimeInvariantViolation:
            raise
        except Exception as error:
            metadata = self._metadata(
                request,
                thread_id=thread_id,
                turn_id=turn_id,
            ) | {
                "terminal_result_within_timeout": False,
                "exception_type": type(error).__name__,
            }
            return ExecutorDispatchResult(
                provider_reference=provider_reference,
                outcome=ProviderReportedOutcome.UNKNOWN,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                metadata=metadata,
                summary=str(error),
            )

        return ExecutorDispatchResult(
            provider_reference=provider_reference,
            outcome=outcome,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            metadata=metadata,
            summary=result.final_response,
        )

    def _metadata(
        self,
        request: ExecutorDispatchRequest,
        *,
        thread_id: str | None,
        turn_id: str | None,
    ) -> dict[str, Any]:
        if thread_id is not None and turn_id is not None:
            identity_state = "COMPLETE"
        elif thread_id is not None:
            identity_state = "PARTIAL"
        else:
            identity_state = "MISSING"
        metadata: dict[str, Any] = {
            "adapter": "CodexSdkExecutor",
            "sdk_version": version("openai-codex"),
            "runtime_version": version("openai-codex-cli-bin"),
            "model": self.model or "sdk-default",
            "sandbox": self.sandbox.value,
            "approval_mode": ApprovalMode.deny_all.value,
            "dispatch_id": str(request.dispatch_id),
            "input_id": str(self.materialized_input.id),
            "input_fingerprint": self.materialized_input.input_fingerprint,
            "workspace_identity": request.execution.workspace.workspace_identity,
            "provider_identity_state": identity_state,
        }
        if thread_id is not None:
            metadata["thread_id"] = thread_id
        if turn_id is not None:
            metadata["turn_id"] = turn_id
        return metadata

    def _validate_dispatch(self, request: ExecutorDispatchRequest) -> None:
        execution = request.execution
        materialized = self.materialized_input
        if materialized.prepared_execution_request != execution:
            raise RuntimeInvariantViolation(
                "materialized input does not bind the exact dispatch request"
            )
        if (
            materialized.attempt_id != execution.attempt_id
            or materialized.generation != execution.generation
            or execution.workspace.workspace_identity
            != f"attempt-worktree:{execution.attempt_id}"
        ):
            raise RuntimeInvariantViolation(
                "Codex dispatch does not bind the exact Attempt/generation workspace"
            )

        self.workspace_validator(execution.workspace)


def _validate_host_workspace(workspace_binding: WorkspaceBinding) -> None:
    workspace = workspace_binding.workspace_path.resolve()
    repository = workspace_binding.repository_path.resolve()
    if not workspace.is_dir():
        raise RuntimeInvariantViolation("exact Attempt workspace does not exist")
    if workspace == repository:
        raise RuntimeInvariantViolation(
            "authoritative repository cannot be used as an Attempt workspace"
        )
    GitAttemptWorkspace().validate(workspace_binding)


def _enum_value(value: object) -> str:
    candidate = getattr(value, "value", value)
    return str(candidate).lower()


def _map_outcome(status: str) -> ProviderReportedOutcome:
    if status == "completed":
        return ProviderReportedOutcome.SUCCESS
    if status == "failed":
        return ProviderReportedOutcome.FAILURE
    return ProviderReportedOutcome.UNKNOWN


def _wait_for_terminal(turn: Any, timeout_seconds: float | None) -> _TerminalWait:
    if timeout_seconds is None:
        return _TerminalWait(result=turn.run())

    completed: Queue[tuple[str, Any]] = Queue(maxsize=1)

    def consume_terminal() -> None:
        try:
            completed.put(("result", turn.run()))
        except Exception as error:  # transported back to the dispatch thread
            completed.put(("error", error))

    worker = Thread(
        target=consume_terminal,
        name="spg-codex-terminal-wait",
        daemon=True,
    )
    worker.start()
    try:
        kind, value = completed.get(timeout=timeout_seconds)
    except Empty:
        timeout_at = datetime.now(UTC)
        interrupt_error_type = None
        try:
            turn.interrupt()
        except Exception as error:
            interrupt_error_type = type(error).__name__

        try:
            post_timeout_kind, post_timeout_value = completed.get(
                timeout=INTERRUPT_GRACE_SECONDS
            )
        except Empty:
            return _TerminalWait(
                timed_out=True,
                timeout_at=timeout_at,
                interrupt_requested=True,
                interrupt_error_type=interrupt_error_type,
            )
        return _TerminalWait(
            result=post_timeout_value if post_timeout_kind == "result" else None,
            timed_out=True,
            timeout_at=timeout_at,
            interrupt_requested=True,
            interrupt_error_type=interrupt_error_type,
            post_timeout_error_type=(
                type(post_timeout_value).__name__
                if post_timeout_kind == "error"
                else None
            ),
        )

    if kind == "error":
        raise value
    return _TerminalWait(result=value)
