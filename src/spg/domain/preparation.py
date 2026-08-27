"""S2-A execution-facing context and Attempt preparation contracts."""

from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContextSemanticRole(StrEnum):
    """Small FVS manifest vocabulary, not a general context taxonomy."""

    PROJECT_CONTEXT = "PROJECT_CONTEXT"
    ARCHITECTURE_CONTRACT = "ARCHITECTURE_CONTRACT"
    EXECUTION_CONTRACT = "EXECUTION_CONTRACT"
    CONSTRAINT = "CONSTRAINT"
    DECISION = "DECISION"


class ContextArtifactSelection(BaseModel):
    """One admitted repository artifact selected for exact-revision context."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    semantic_role: ContextSemanticRole
    repository_relative_path: str = Field(min_length=1)

    @field_validator("repository_relative_path")
    @classmethod
    def require_safe_repository_relative_path(cls, value: str) -> str:
        if "\\" in value:
            raise ValueError("repository paths must use POSIX separators")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value in {".", ""}:
            raise ValueError("context artifact path must be repository-relative")
        return str(path)


class ContextPackageRequest(BaseModel):
    """Explicit admitted artifact selection; raw conversation is not accepted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifacts: Annotated[tuple[ContextArtifactSelection, ...], Field(min_length=1)]


class ContextArtifactManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    semantic_role: ContextSemanticRole
    repository_relative_path: str
    source_revision: str
    blob_fingerprint: str


class ContextPackageManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifacts: tuple[ContextArtifactManifestEntry, ...]


class ContextPackageRecord(BaseModel):
    """Immutable local FVS projection of an execution Context Package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    version: int
    production_run_id: UUID
    work_unit_id: UUID
    plan_revision_id: UUID
    source_baseline_id: UUID
    manifest: ContextPackageManifest
    content_fingerprint: str
    completion_contract_fingerprint: str
    created_at: datetime


class ExecutorBinding(BaseModel):
    """Provider-neutral capability/profile binding resolved outside SPG domain logic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    binding_ref: str = Field(min_length=1)
    capability_identity: str = Field(min_length=1)
    profile_identity: str = Field(min_length=1)


class WorkspaceBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_identity: str = Field(min_length=1)
    workspace_path: Path
    repository_identity: str = Field(min_length=1)
    repository_path: Path
    source_revision: str = Field(min_length=1)


class AttemptPreparationRecord(BaseModel):
    """Durable readiness binding without inventing an Attempt lifecycle state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: UUID
    context_package_id: UUID
    executor_binding: ExecutorBinding
    workspace: WorkspaceBinding
    prepared_at: datetime


class PreparedExecutionRequest(BaseModel):
    """Provider-neutral exact input that a later S2-B dispatcher may consume."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: UUID
    generation: int
    production_run_id: UUID
    work_unit_id: UUID
    plan_revision_id: UUID
    source_baseline_id: UUID
    context_package_id: UUID
    context_package_version: int
    completion_contract_fingerprint: str
    executor_binding: ExecutorBinding
    workspace: WorkspaceBinding


class AttemptPreparationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    context_package: ContextPackageRecord
    preparation: AttemptPreparationRecord
    execution_request: PreparedExecutionRequest
