"""S2-B governed execution, provider-report, and observation contracts."""

from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from spg.domain.preparation import ExecutorBinding, PreparedExecutionRequest, WorkspaceBinding


class ProviderReportedOutcome(StrEnum):
    """Provider-neutral execution claims, never PWU completion judgments."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    UNKNOWN = "UNKNOWN"


class ExecutorReturnControl(StrEnum):
    """Executor claim explaining why one bounded execution grant returned."""

    RESULT_READY = "RESULT_READY"
    UNABLE_TO_COMPLETE = "UNABLE_TO_COMPLETE"
    BOUNDARY_CROSSING_REQUIRED = "BOUNDARY_CROSSING_REQUIRED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    EXECUTION_CONTINUITY_LOST = "EXECUTION_CONTINUITY_LOST"


class ArtifactChangeType(StrEnum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"


class ExecutorDispatchRequest(BaseModel):
    """Runtime-issued dispatch authority plus the exact prepared request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dispatch_id: UUID
    execution: PreparedExecutionRequest


class ExecutorDispatchResult(BaseModel):
    """Untrusted provider output normalized by Runtime against dispatch facts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_reference: str = Field(min_length=1)
    outcome: ProviderReportedOutcome
    started_at: datetime
    finished_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    return_control: ExecutorReturnControl | None = None

    @model_validator(mode="after")
    def require_monotonic_timestamps(self) -> "ExecutorDispatchResult":
        if self.finished_at < self.started_at:
            raise ValueError("provider finished_at cannot precede started_at")
        if self.return_control is None:
            default = (
                ExecutorReturnControl.RESULT_READY
                if self.outcome is ProviderReportedOutcome.SUCCESS
                else ExecutorReturnControl.UNABLE_TO_COMPLETE
                if self.outcome is ProviderReportedOutcome.FAILURE
                else ExecutorReturnControl.EXECUTION_CONTINUITY_LOST
            )
            object.__setattr__(self, "return_control", default)
        return self


class ExecutionDispatchRecord(BaseModel):
    """Durable Runtime dispatch fact persisted before provider execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    attempt_id: UUID
    generation: int
    context_package_id: UUID
    source_baseline_id: UUID
    executor_binding: ExecutorBinding
    workspace: WorkspaceBinding
    authoritative_ref_revision: str = Field(min_length=1)
    dispatched_at: datetime


class ProviderExecutionReportRecord(BaseModel):
    """Immutable provider claim with Runtime-owned lineage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    dispatch_id: UUID
    attempt_id: UUID
    generation: int
    executor_binding: ExecutorBinding
    provider_reference: str
    outcome: ProviderReportedOutcome
    started_at: datetime
    finished_at: datetime
    metadata: dict[str, Any]
    summary: str | None
    recorded_at: datetime


class ObservedArtifactChange(BaseModel):
    """One factual path delta relative to the exact Attempt Source Baseline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_relative_path: str = Field(min_length=1)
    change_type: ArtifactChangeType
    source_fingerprint: str | None = None
    observed_fingerprint: str | None = None

    @field_validator("repository_relative_path")
    @classmethod
    def require_safe_relative_path(cls, value: str) -> str:
        if "\\" in value:
            raise ValueError("repository paths must use POSIX separators")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value in {"", "."}:
            raise ValueError("observed artifact path must be repository-relative")
        return str(path)

    @model_validator(mode="after")
    def require_change_fingerprint_shape(self) -> "ObservedArtifactChange":
        if self.change_type is ArtifactChangeType.ADDED:
            if self.source_fingerprint is not None or self.observed_fingerprint is None:
                raise ValueError("ADDED requires only an observed fingerprint")
        elif self.change_type is ArtifactChangeType.MODIFIED:
            if self.source_fingerprint is None or self.observed_fingerprint is None:
                raise ValueError("MODIFIED requires source and observed fingerprints")
        elif self.source_fingerprint is None or self.observed_fingerprint is not None:
            raise ValueError("DELETED requires only a source fingerprint")
        return self


class ObservedRepositoryReality(BaseModel):
    """Infrastructure observation candidate without Runtime-owned lineage IDs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_identity: str
    source_revision: str
    workspace_identity: str
    workspace_path: str
    authoritative_ref_revision: str
    observed_at: datetime
    changes: tuple[ObservedArtifactChange, ...]
    observation_fingerprint: str


class RepositoryObservationRecord(BaseModel):
    """Durable independent observation for exactly one dispatch."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    dispatch_id: UUID
    attempt_id: UUID
    generation: int
    source_baseline_id: UUID
    repository_identity: str
    source_revision: str
    workspace_identity: str
    workspace_path: str
    authoritative_ref_revision: str
    observed_at: datetime
    changes: tuple[ObservedArtifactChange, ...]
    observation_fingerprint: str


class WorkProductReferenceRecord(BaseModel):
    """Observed artifact lineage; SPG does not own the artifact content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    production_run_id: UUID
    work_unit_id: UUID
    plan_revision_id: UUID
    attempt_id: UUID
    generation: int
    source_baseline_id: UUID
    repository_observation_id: UUID
    artifact_path: str
    change_type: ArtifactChangeType
    source_fingerprint: str | None
    observed_fingerprint: str | None
    created_at: datetime


class GovernedExecutionResult(BaseModel):
    """S2-B output stops at facts and observed Work Product References."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dispatch: ExecutionDispatchRecord
    provider_report: ProviderExecutionReportRecord
    observation: RepositoryObservationRecord
    work_products: tuple[WorkProductReferenceRecord, ...]
