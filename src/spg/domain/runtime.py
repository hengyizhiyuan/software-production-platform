"""S1-C domain contracts independent from SQLAlchemy persistence details."""

from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SnapshotCondition(StrEnum):
    TRUSTED = "TRUSTED"


class RunCondition(StrEnum):
    OPEN = "OPEN"
    SUPERSEDED = "SUPERSEDED"


class PlanCondition(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


class WorkUnitCondition(StrEnum):
    PROPOSED = "PROPOSED"
    PRODUCED = "PRODUCED"
    SATISFIED = "SATISFIED"
    SUPERSEDED = "SUPERSEDED"


class AttemptCondition(StrEnum):
    CREATED = "CREATED"


class ProductionHorizon(StrEnum):
    DOCUMENTATION = "DOCUMENTATION"


class ArtifactOperation(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"


class ArtifactContract(BaseModel):
    """Exact Human-admitted artifact authority for one initial PWU."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    engineering_resource_id: UUID
    repository_identity: str = Field(min_length=1)
    source_baseline_id: UUID
    source_revision: str = Field(min_length=1)
    artifact_path: str = Field(min_length=1)
    operation: ArtifactOperation
    constraints: tuple[str, ...] = ()
    expected_outcome: str = Field(min_length=1)
    verification_obligation: str = Field(min_length=1)

    @field_validator("artifact_path")
    @classmethod
    def require_safe_repository_path(cls, value: str) -> str:
        if "\\" in value:
            raise ValueError("artifact path must use POSIX separators")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value in {"", "."}:
            raise ValueError("artifact path must be repository-relative")
        if ".git" in path.parts:
            raise ValueError("artifact path cannot address Git internals")
        return str(path)


class CompletionContract(BaseModel):
    """Durable obligations established before any execution attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    required_outputs: tuple[str, ...] = ()
    required_changes: tuple[str, ...] = ()
    required_markers: tuple[str, ...] = ()
    forbidden_changes: tuple[str, ...] = ()
    verification_obligations: tuple[str, ...] = ()
    blocking_conditions: tuple[str, ...] = ()
    artifact_contract: ArtifactContract | None = None

    @model_validator(mode="after")
    def require_at_least_one_obligation(self) -> "CompletionContract":
        if not any(
            (
                self.required_outputs,
                self.required_changes,
                self.required_markers,
                self.forbidden_changes,
                self.verification_obligations,
                self.blocking_conditions,
                self.artifact_contract,
            )
        ):
            raise ValueError("Completion Contract must declare at least one obligation")
        return self

    @property
    def requires_observed_production_result(self) -> bool:
        """Whether NONE Reality cannot satisfy the production obligations."""

        return bool(
            self.required_outputs
            or self.required_changes
            or self.required_markers
        )


class BootstrapRequest(BaseModel):
    """Explicit governed input for initial Trusted Baseline admission."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_path: Path
    repository_identity: str = Field(min_length=1)
    repository_ref: str = Field(min_length=1)
    authority_identity: str = Field(min_length=1)
    scope: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None


class InitialRunRequest(BaseModel):
    """Already-admitted structured input for deterministic initial planning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    intent_ref: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    production_horizon: ProductionHorizon
    initial_work_unit_objective: str = Field(min_length=1)
    completion_contract: CompletionContract


class AttemptRequest(BaseModel):
    """Optional non-authoritative preparation references for Attempt identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    context_ref: str | None = None
    provider_ref: str | None = None
    workspace_ref: str | None = None


class RuntimeDomainError(RuntimeError):
    """Base class for rejected governed Runtime operations."""


class RuntimeNotBootstrapped(RuntimeDomainError):
    pass


class BootstrapAlreadyInitialized(RuntimeDomainError):
    pass


class RuntimeRecordNotFound(RuntimeDomainError):
    pass


class RuntimeInvariantViolation(RuntimeDomainError):
    pass


class RepositoryRealityError(RuntimeDomainError):
    pass


class RepositoryReality(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_identity: str
    repository_ref: str
    exact_revision: str


class SnapshotRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    condition: SnapshotCondition
    repository_identity: str
    repository_ref: str
    repository_revision: str
    source_baseline_id: UUID | None
    created_at: datetime


class BaselinePointerRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: UUID
    version: int
    updated_at: datetime


class GovernanceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    decision_type: str
    authority_identity: str
    subject_type: str
    subject_identity: str
    scope: dict[str, Any]
    rationale: str | None
    created_at: datetime


class ProductionRunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    intent_ref: str
    goal: str
    production_horizon: ProductionHorizon
    source_baseline_id: UUID
    current_plan_revision_id: UUID
    condition: RunCondition
    version: int
    created_at: datetime


class PlanRevisionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    production_run_id: UUID
    revision_number: int
    source_baseline_id: UUID
    condition: PlanCondition
    version: int
    created_at: datetime


class WorkUnitRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    production_run_id: UUID
    plan_revision_id: UUID
    source_baseline_id: UUID
    objective: str
    completion_contract: CompletionContract
    condition: WorkUnitCondition
    version: int
    current_execution_generation: int
    created_at: datetime


class ExecutionAttemptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    work_unit_id: UUID
    generation: int
    plan_revision_id: UUID
    source_baseline_id: UUID
    context_ref: str | None
    provider_ref: str | None
    workspace_ref: str | None
    condition: AttemptCondition
    retry_of: UUID | None
    created_at: datetime


class TransitionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    entity_type: str
    entity_identity: str
    from_condition: str | None
    to_condition: str
    reason: str
    actor_identity: str
    correlation_identity: str | None
    created_at: datetime


class BootstrapResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot: SnapshotRecord
    pointer: BaselinePointerRecord
    governance: GovernanceRecord


class InitialRuntimeSpine(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run: ProductionRunRecord
    plan_revision: PlanRevisionRecord
    work_unit: WorkUnitRecord
