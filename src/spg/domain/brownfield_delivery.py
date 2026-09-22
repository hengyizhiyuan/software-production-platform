"""Contracts for one governed Brownfield Feature Delivery vertical slice."""

from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from spg.domain.production_environment import (
    CollectedEnvironmentOutput,
    DeliveryIntentV1,
    EnvironmentCommand,
    EnvironmentCommandResult,
    GIT_OBJECT_PATTERN,
    PreparedWorkspaceV1,
    PreviewRuntimeV1,
    ProductionEnvironmentContract,
    ProductionEnvironmentV1,
    ProductionRecordV1,
    ProductionWorkspaceV1,
    ProviderEnvironmentHandle,
    require_timezone,
    safe_repository_path,
    safe_workspace_path,
)


class BrownfieldFeatureDeliveryRequest(ProductionEnvironmentContract):
    work_id: UUID
    task_contract_reference: str = Field(min_length=1)
    repository_identity: str = Field(min_length=1)
    repository_source: Path
    requested_branch: str | None = Field(default=None, min_length=1)
    repository_mount_path: str = "/workspace/repository"
    target_branch: str = Field(min_length=1)
    container_image: str = Field(min_length=1)
    dependency_commands: tuple[EnvironmentCommand, ...] = ()
    implementation_commands: tuple[EnvironmentCommand, ...] = Field(min_length=1)
    verification_commands: tuple[EnvironmentCommand, ...] = Field(min_length=1)
    artifact_paths: tuple[str, ...] = Field(min_length=1)
    preview_entrypoint: str = Field(min_length=1)
    commit_message: str = Field(min_length=1)
    commit_author_name: str = Field(min_length=1)
    commit_author_email: str = Field(min_length=3)

    _safe_mount = field_validator("repository_mount_path")(safe_workspace_path)
    _safe_artifacts = field_validator("artifact_paths")(
        lambda values: tuple(safe_workspace_path(value) for value in values)
    )
    _safe_preview = field_validator("preview_entrypoint")(safe_repository_path)

    @model_validator(mode="after")
    def bind_commands_and_artifacts_to_repository(self) -> "BrownfieldFeatureDeliveryRequest":
        prefix = self.repository_mount_path.rstrip("/") + "/"
        commands = (
            *self.dependency_commands,
            *self.implementation_commands,
            *self.verification_commands,
        )
        if any(
            command.working_directory != self.repository_mount_path
            and not command.working_directory.startswith(prefix)
            for command in commands
        ):
            raise ValueError("all commands must run inside the admitted repository mount")
        if any(path != self.repository_mount_path and not path.startswith(prefix) for path in self.artifact_paths):
            raise ValueError("all artifacts must belong to the admitted repository mount")
        return self


class BrownfieldReviewSessionV1(ProductionEnvironmentContract):
    schema_version: int = Field(default=1, ge=1, le=1)
    id: UUID
    work_id: UUID
    task_contract_reference: str = Field(min_length=1)
    repository_identity: str = Field(min_length=1)
    repository_reality_reference: str = Field(min_length=1)
    source_revision: str = Field(pattern=GIT_OBJECT_PATTERN)
    candidate_revision: str = Field(pattern=GIT_OBJECT_PATTERN)
    target_branch: str = Field(min_length=1)
    workspace: ProductionWorkspaceV1
    prepared_workspace: PreparedWorkspaceV1
    environment: ProductionEnvironmentV1
    provider_handle: ProviderEnvironmentHandle
    preview: PreviewRuntimeV1
    delivery_intent: DeliveryIntentV1
    execution_results: tuple[EnvironmentCommandResult, ...]
    verification_results: tuple[EnvironmentCommandResult, ...]
    outputs: tuple[CollectedEnvironmentOutput, ...]
    created_at: datetime

    _created_timezone = field_validator("created_at")(require_timezone)

    @model_validator(mode="after")
    def validate_lineage(self) -> "BrownfieldReviewSessionV1":
        if self.workspace.work_id != self.work_id or self.environment.work_id != self.work_id:
            raise ValueError("review session Work lineage differs")
        if self.workspace.id != self.prepared_workspace.workspace_id:
            raise ValueError("review session Workspace lineage differs")
        if self.environment.workspace_id != self.workspace.id:
            raise ValueError("review session Environment lineage differs")
        if self.provider_handle.environment_id != self.environment.id:
            raise ValueError("review session Provider lineage differs")
        if self.preview.environment_id != self.environment.id:
            raise ValueError("review session Preview lineage differs")
        if self.delivery_intent.environment_id != self.environment.id:
            raise ValueError("review session Delivery lineage differs")
        if self.delivery_intent.commit != self.candidate_revision:
            raise ValueError("Delivery intent is not bound to reviewed Candidate")
        return self


class BrownfieldDeliveryCompletionV1(ProductionEnvironmentContract):
    schema_version: int = Field(default=1, ge=1, le=1)
    review_session_id: UUID
    environment: ProductionEnvironmentV1
    delivery_intent: DeliveryIntentV1
    production_record: ProductionRecordV1
    refreshed_repository_reality_reference: str = Field(min_length=1)
    change_reality_reference: str = Field(min_length=1)
    delivery_reality_reference: str = Field(min_length=1)
    guardian_intake_reference: str = Field(min_length=1)
    completed_at: datetime

    _completed_timezone = field_validator("completed_at")(require_timezone)
