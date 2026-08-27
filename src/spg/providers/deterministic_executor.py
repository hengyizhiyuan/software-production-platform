"""Deterministic provider-neutral Executor used for governed Runtime validation."""

from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from spg.domain.execution import (
    ExecutorDispatchRequest,
    ExecutorDispatchResult,
    ProviderReportedOutcome,
)
from spg.domain.runtime import RuntimeInvariantViolation


class DeterministicFileOperationType(StrEnum):
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    DELETE = "DELETE"


class DeterministicFileOperation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: DeterministicFileOperationType
    repository_relative_path: str = Field(min_length=1)
    content: str | None = None

    @field_validator("repository_relative_path")
    @classmethod
    def require_safe_relative_path(cls, value: str) -> str:
        if "\\" in value:
            raise ValueError("repository paths must use POSIX separators")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value in {"", "."}:
            raise ValueError("operation path must be repository-relative")
        return str(path)

    @model_validator(mode="after")
    def require_content_shape(self) -> "DeterministicFileOperation":
        if self.operation is DeterministicFileOperationType.DELETE:
            if self.content is not None:
                raise ValueError("DELETE cannot supply content")
        elif self.content is None:
            raise ValueError("CREATE and MODIFY require content")
        return self


class DeterministicExecutionSpecification(BaseModel):
    """Small structured control input; no natural-language execution authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operations: tuple[DeterministicFileOperation, ...] = ()
    reported_outcome: ProviderReportedOutcome
    summary: str | None = None


ExecutionProbe = Callable[[ExecutorDispatchRequest], None]


class DeterministicTestExecutor:
    """Synchronous deterministic implementation of ExecutorCapabilityContract."""

    def __init__(
        self,
        specification: DeterministicExecutionSpecification,
        *,
        before_mutation: ExecutionProbe | None = None,
        after_mutation: ExecutionProbe | None = None,
    ) -> None:
        self.specification = specification
        self.before_mutation = before_mutation
        self.after_mutation = after_mutation
        self.dispatch_count = 0

    def dispatch(self, request: ExecutorDispatchRequest) -> ExecutorDispatchResult:
        started_at = datetime.now(UTC)
        self.dispatch_count += 1
        if self.before_mutation is not None:
            self.before_mutation(request)

        workspace = request.execution.workspace.workspace_path.resolve()
        for operation in self.specification.operations:
            target = self._target(workspace, operation.repository_relative_path)
            if operation.operation is DeterministicFileOperationType.CREATE:
                if target.exists():
                    raise RuntimeInvariantViolation(
                        "deterministic CREATE target already exists: "
                        f"{operation.repository_relative_path}"
                    )
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(operation.content or "", encoding="utf-8")
            elif operation.operation is DeterministicFileOperationType.MODIFY:
                if not target.is_file():
                    raise RuntimeInvariantViolation(
                        "deterministic MODIFY target does not exist: "
                        f"{operation.repository_relative_path}"
                    )
                target.write_text(operation.content or "", encoding="utf-8")
            else:
                if not target.is_file():
                    raise RuntimeInvariantViolation(
                        "deterministic DELETE target does not exist: "
                        f"{operation.repository_relative_path}"
                    )
                target.unlink()

        if self.after_mutation is not None:
            self.after_mutation(request)
        return ExecutorDispatchResult(
            provider_reference=f"deterministic-test:{request.dispatch_id}",
            outcome=self.specification.reported_outcome,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            metadata={"operation_count": len(self.specification.operations)},
            summary=self.specification.summary,
        )

    @staticmethod
    def _target(workspace: Path, repository_relative_path: str) -> Path:
        target = workspace / repository_relative_path
        resolved_parent = target.parent.resolve()
        try:
            resolved_parent.relative_to(workspace)
        except ValueError as error:
            raise RuntimeInvariantViolation(
                "deterministic operation escapes the Attempt workspace"
            ) from error
        return target
