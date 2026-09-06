"""Official Python Codex SDK implementation of the Executor capability."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from importlib.metadata import version
import json
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from time import monotonic
from typing import Any, Protocol

from openai_codex import ApprovalMode, Codex, Sandbox
from pydantic import BaseModel, ConfigDict, Field

from spg.domain.execution import (
    ExecutorDispatchRequest,
    ExecutorDispatchResult,
    ExecutorReturnControl,
    ProviderReportedOutcome,
)
from spg.domain.preparation import PreparedExecutionRequest, WorkspaceBinding
from spg.domain.runtime import RuntimeInvariantViolation
from spg.infrastructure.git_workspace import GitAttemptWorkspace


CodexFactory = Callable[[], AbstractContextManager[Any]]
WorkspaceValidator = Callable[[WorkspaceBinding], None]
ContinuationValidator = Callable[[ExecutorDispatchRequest], None]
INTERRUPT_GRACE_SECONDS = 5.0


class _InternalTurnAction(StrEnum):
    CONTINUE = "CONTINUE"
    RESULT_READY = "RESULT_READY"
    UNABLE_TO_COMPLETE = "UNABLE_TO_COMPLETE"
    BOUNDARY_CROSSING_REQUIRED = "BOUNDARY_CROSSING_REQUIRED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    EXECUTION_CONTINUITY_LOST = "EXECUTION_CONTINUITY_LOST"


class _InternalTurnClaim(BaseModel):
    """Non-authoritative control claim returned by one internal Provider Turn."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: _InternalTurnAction
    activity_summary: str = Field(min_length=1)


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
        max_internal_turns: int = 3,
        sandbox: Sandbox = Sandbox.workspace_write,
        workspace_validator: WorkspaceValidator | None = None,
        continuation_validator: ContinuationValidator | None = None,
    ) -> None:
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive when provided")
        if max_internal_turns < 1:
            raise ValueError("max_internal_turns must be positive")
        self.materialized_input = materialized_input
        self.codex_factory = codex_factory or Codex
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_internal_turns = max_internal_turns
        self.sandbox = sandbox
        self.workspace_validator = workspace_validator or _validate_host_workspace
        self.continuation_validator = (
            continuation_validator or _validate_host_continuation
        )

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
        internal_turn_count = 0
        turn_ids: list[str] = []
        activity_summaries: list[str] = []
        provider_reference = f"codex-sdk:dispatch:{request.dispatch_id}"
        metadata = self._metadata(request, thread_id=thread_id, turn_id=turn_id)
        deadline = (
            monotonic() + self.timeout_seconds
            if self.timeout_seconds is not None
            else None
        )

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
                for turn_number in range(1, self.max_internal_turns + 1):
                    remaining = _remaining_time(deadline)
                    if remaining is not None and remaining <= 0:
                        return self._aggregate_result(
                            request,
                            provider_reference=provider_reference,
                            started_at=started_at,
                            metadata=metadata,
                            internal_turn_count=internal_turn_count,
                            turn_ids=turn_ids,
                            activity_summaries=activity_summaries,
                            return_control=ExecutorReturnControl.BUDGET_EXHAUSTED,
                            summary="Executor total Provider time budget was exhausted",
                            stop_reason="TIME_BUDGET_EXHAUSTED",
                        )
                    input_content = (
                        self.materialized_input.provider_input()
                        if turn_number == 1
                        else _continuation_instruction(activity_summaries[-1])
                    )
                    turn = thread.turn(
                        input_content,
                        approval_mode=ApprovalMode.deny_all,
                        cwd=str(workspace),
                        model=self.model,
                        output_schema=self.turn_output_schema(),
                        sandbox=self.sandbox,
                    )
                    internal_turn_count = turn_number
                    turn_id = str(turn.id)
                    turn_ids.append(turn_id)
                    provider_reference = (
                        f"codex-sdk:thread:{thread_id}:turn:{turn_id}"
                    )
                    metadata = self._metadata(
                        request,
                        thread_id=thread_id,
                        turn_id=turn_id,
                    )
                    terminal = _wait_for_terminal(turn, remaining)
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
                                    terminal.result, "started_at", None
                                ),
                                "post_timeout_completed_at": getattr(
                                    terminal.result, "completed_at", None
                                ),
                                "post_timeout_duration_ms": getattr(
                                    terminal.result, "duration_ms", None
                                ),
                            }
                        )
                        return self._aggregate_result(
                            request,
                            provider_reference=provider_reference,
                            started_at=started_at,
                            metadata=metadata,
                            internal_turn_count=internal_turn_count,
                            turn_ids=turn_ids,
                            activity_summaries=activity_summaries,
                            return_control=ExecutorReturnControl.BUDGET_EXHAUSTED,
                            summary=(
                                "Codex Turn exceeded the bounded total Provider time"
                            ),
                            stop_reason="TIME_BUDGET_EXHAUSTED",
                        )

                    result = terminal.result
                    if result is None:
                        raise RuntimeError("Codex terminal wait returned no result")
                    status = _enum_value(result.status)
                    result_turn_id = str(result.id)
                    identity_matches = result_turn_id == turn_id
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
                    if not identity_matches:
                        return self._aggregate_result(
                            request,
                            provider_reference=provider_reference,
                            started_at=started_at,
                            metadata=metadata,
                            internal_turn_count=internal_turn_count,
                            turn_ids=turn_ids,
                            activity_summaries=activity_summaries,
                            return_control=(
                                ExecutorReturnControl.EXECUTION_CONTINUITY_LOST
                            ),
                            summary="Provider terminal Turn identity changed",
                            stop_reason="TURN_IDENTITY_MISMATCH",
                        )
                    if status != "completed" or result.error is not None:
                        return_control = (
                            ExecutorReturnControl.UNABLE_TO_COMPLETE
                            if status == "failed"
                            else ExecutorReturnControl.EXECUTION_CONTINUITY_LOST
                        )
                        return self._aggregate_result(
                            request,
                            provider_reference=provider_reference,
                            started_at=started_at,
                            metadata=metadata,
                            internal_turn_count=internal_turn_count,
                            turn_ids=turn_ids,
                            activity_summaries=activity_summaries,
                            return_control=return_control,
                            summary=str(result.final_response or status),
                            stop_reason=f"PROVIDER_TURN_{status.upper()}",
                        )

                    try:
                        claim = _parse_turn_claim(result.final_response)
                    except ValueError:
                        return self._aggregate_result(
                            request,
                            provider_reference=provider_reference,
                            started_at=started_at,
                            metadata=metadata,
                            internal_turn_count=internal_turn_count,
                            turn_ids=turn_ids,
                            activity_summaries=activity_summaries,
                            return_control=ExecutorReturnControl.UNABLE_TO_COMPLETE,
                            summary="Provider returned an invalid Executor control claim",
                            stop_reason="INVALID_TURN_CONTROL_CLAIM",
                        )
                    if claim is None:
                        return self._aggregate_result(
                            request,
                            provider_reference=provider_reference,
                            started_at=started_at,
                            metadata=metadata,
                            internal_turn_count=internal_turn_count,
                            turn_ids=turn_ids,
                            activity_summaries=activity_summaries,
                            return_control=ExecutorReturnControl.RESULT_READY,
                            summary=result.final_response,
                            stop_reason="LEGACY_ONE_TURN_RESULT",
                        )

                    activity = claim.activity_summary.strip()
                    if claim.action is not _InternalTurnAction.CONTINUE:
                        return self._aggregate_result(
                            request,
                            provider_reference=provider_reference,
                            started_at=started_at,
                            metadata=metadata,
                            internal_turn_count=internal_turn_count,
                            turn_ids=turn_ids,
                            activity_summaries=activity_summaries + [activity],
                            return_control=ExecutorReturnControl(claim.action.value),
                            summary=activity,
                            stop_reason=f"EXECUTOR_{claim.action.value}",
                        )

                    if activity_summaries and activity == activity_summaries[-1]:
                        return self._aggregate_result(
                            request,
                            provider_reference=provider_reference,
                            started_at=started_at,
                            metadata=metadata,
                            internal_turn_count=internal_turn_count,
                            turn_ids=turn_ids,
                            activity_summaries=activity_summaries + [activity],
                            return_control=ExecutorReturnControl.BUDGET_EXHAUSTED,
                            summary="Executor repeated the same continuation without progress",
                            stop_reason="REPEATED_NO_PROGRESS",
                        )
                    activity_summaries.append(activity)
                    if turn_number >= self.max_internal_turns:
                        return self._aggregate_result(
                            request,
                            provider_reference=provider_reference,
                            started_at=started_at,
                            metadata=metadata,
                            internal_turn_count=internal_turn_count,
                            turn_ids=turn_ids,
                            activity_summaries=activity_summaries,
                            return_control=ExecutorReturnControl.BUDGET_EXHAUSTED,
                            summary="Executor maximum internal Turn budget was exhausted",
                            stop_reason="MAX_INTERNAL_TURNS_EXHAUSTED",
                        )
                    try:
                        self._validate_continuation(request)
                    except Exception as error:
                        return self._aggregate_result(
                            request,
                            provider_reference=provider_reference,
                            started_at=started_at,
                            metadata=metadata,
                            internal_turn_count=internal_turn_count,
                            turn_ids=turn_ids,
                            activity_summaries=activity_summaries,
                            return_control=(
                                ExecutorReturnControl.EXECUTION_CONTINUITY_LOST
                            ),
                            summary="Executor continuation basis is no longer trustworthy",
                            stop_reason=f"CONTINUITY_{type(error).__name__}",
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
                return_control=ExecutorReturnControl.EXECUTION_CONTINUITY_LOST,
            )

        raise RuntimeError("bounded Executor loop ended without a return-control claim")

    @staticmethod
    def turn_output_schema() -> dict[str, Any]:
        """Strict non-authoritative control shape for one internal Turn."""

        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [item.value for item in _InternalTurnAction],
                    "description": (
                        "Use CONTINUE only when another bounded Turn is needed. Use "
                        "RESULT_READY when the best candidate result is ready for "
                        "independent SPG observation. Stop on inability, boundary "
                        "crossing, budget exhaustion, or continuity loss."
                    ),
                },
                "activity_summary": {
                    "type": "string",
                    "minLength": 1,
                    "description": (
                        "Safe bounded summary of progress or the exact stop reason; "
                        "this is operational metadata, not Authority or Verification."
                    ),
                },
            },
            "required": ["action", "activity_summary"],
        }

    def _aggregate_result(
        self,
        request: ExecutorDispatchRequest,
        *,
        provider_reference: str,
        started_at: datetime,
        metadata: dict[str, Any],
        internal_turn_count: int,
        turn_ids: list[str],
        activity_summaries: list[str],
        return_control: ExecutorReturnControl,
        summary: str | None,
        stop_reason: str,
    ) -> ExecutorDispatchResult:
        outcome = _provider_outcome(return_control)
        aggregate_metadata = {
            **metadata,
            "internal_turn_count": internal_turn_count,
            "self_refine_occurred": internal_turn_count > 1,
            "terminal_executor_outcome": return_control.value,
            "executor_stop_reason": stop_reason,
            "configured_max_internal_turns": self.max_internal_turns,
            "configured_total_time_budget_seconds": self.timeout_seconds,
            "internal_turn_ids": turn_ids,
            "internal_activity_summaries": activity_summaries,
            "executor_active": False,
            "current_activity": summary,
            "self_refining": internal_turn_count > 1,
        }
        return ExecutorDispatchResult(
            provider_reference=provider_reference,
            outcome=outcome,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            metadata=aggregate_metadata,
            summary=summary,
            return_control=return_control,
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
        self._validate_dispatch_identity(request)
        self.workspace_validator(request.execution.workspace)

    def _validate_continuation(self, request: ExecutorDispatchRequest) -> None:
        self._validate_dispatch_identity(request)
        self.continuation_validator(request)

    def _validate_dispatch_identity(self, request: ExecutorDispatchRequest) -> None:
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


def _validate_host_continuation(request: ExecutorDispatchRequest) -> None:
    """Require the same exact worktree/HEAD basis while allowing produced changes."""

    GitAttemptWorkspace().validate_basis(request.execution.workspace)


def _remaining_time(deadline: float | None) -> float | None:
    return None if deadline is None else max(deadline - monotonic(), 0.0)


def _continuation_instruction(previous_activity: str) -> str:
    return (
        "Continue the same exact admitted Executor Attempt. Keep the original "
        "objective, Source Basis, Authority, Scope, constraints, Completion "
        "Contract, sandbox, and STOP conditions unchanged. Diagnose, repair, and "
        "revalidate only inside that envelope. Stop before any boundary crossing. "
        "Return the required structured control claim for this Turn.\n\n"
        f"Previous bounded activity summary:\n{previous_activity}"
    )


def _parse_turn_claim(raw: str) -> _InternalTurnClaim | None:
    value = raw.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    if not value.startswith("{"):
        return None
    try:
        return _InternalTurnClaim.model_validate(json.loads(value))
    except (TypeError, ValueError) as error:
        raise ValueError("invalid Executor Turn control claim") from error


def _provider_outcome(
    return_control: ExecutorReturnControl,
) -> ProviderReportedOutcome:
    if return_control is ExecutorReturnControl.RESULT_READY:
        return ProviderReportedOutcome.SUCCESS
    if return_control is ExecutorReturnControl.UNABLE_TO_COMPLETE:
        return ProviderReportedOutcome.FAILURE
    return ProviderReportedOutcome.UNKNOWN


def _enum_value(value: object) -> str:
    candidate = getattr(value, "value", value)
    return str(candidate).lower()


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
