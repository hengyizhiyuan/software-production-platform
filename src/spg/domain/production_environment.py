"""Production Environment Foundation v1 immutable contracts.

Work remains the authority-bearing production entity. These records describe
where and under what conditions admitted work happens; they do not grant Work,
Executor, Verification, Assurance, or Delivery authority.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


GIT_OBJECT_PATTERN = r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$"


class ProductionEnvironmentContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def canonical_digest(value: BaseModel | dict[str, Any] | list[Any]) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value


def safe_workspace_path(value: str) -> str:
    if "\\" in value:
        raise ValueError("workspace paths must use POSIX separators")
    path = PurePosixPath(value)
    if not path.is_absolute() or len(path.parts) < 3 or path.parts[1] != "workspace":
        raise ValueError("workspace path must be below /workspace")
    if ".." in path.parts:
        raise ValueError("workspace path must not traverse parents")
    return str(path)


def safe_repository_path(value: str) -> str:
    if "\\" in value:
        raise ValueError("repository paths must use POSIX separators")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value in {"", "."}:
        raise ValueError("repository path must be safe and relative")
    if ".git" in path.parts:
        raise ValueError("repository path cannot address Git internals")
    return str(path)


class EnvironmentLifecycleState(StrEnum):
    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"
    DESTROYED = "DESTROYED"


class EnvironmentRuntimeState(StrEnum):
    NOT_PROVISIONED = "NOT_PROVISIONED"
    PREPARING = "PREPARING"
    READY = "READY"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class PreviewRuntimeStatus(StrEnum):
    CREATED = "CREATED"
    STARTING = "STARTING"
    READY = "READY"
    NOT_READY = "NOT_READY"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class DeliveryIntentKind(StrEnum):
    BRANCH_CREATION = "BRANCH_CREATION"
    COMMIT = "COMMIT"
    PULL_REQUEST_PREPARATION = "PULL_REQUEST_PREPARATION"


class ProductionDeliveryState(StrEnum):
    READY_FOR_HUMAN_ACCEPTANCE = "READY_FOR_HUMAN_ACCEPTANCE"
    ACCEPTED = "ACCEPTED"
    AUTHORIZED_FOR_DELIVERY = "AUTHORIZED_FOR_DELIVERY"


class HumanDeliveryAction(StrEnum):
    ACCEPT = "ACCEPT"
    AUTHORIZE_DELIVERY = "AUTHORIZE_DELIVERY"


class DeliveryAuthorityKind(StrEnum):
    HUMAN_EXPLICIT = "HUMAN_EXPLICIT"


class ResourceKind(StrEnum):
    WORK = "WORK"
    ENVIRONMENT = "ENVIRONMENT"
    WORKSPACE = "WORKSPACE"
    ARTIFACT = "ARTIFACT"
    EVIDENCE = "EVIDENCE"
    DELIVERY = "DELIVERY"


class ReferenceRelationship(StrEnum):
    BINDS = "BINDS"
    CONTAINS = "CONTAINS"
    PRODUCES = "PRODUCES"
    SUPPORTS = "SUPPORTS"
    DELIVERS = "DELIVERS"


class VerificationOutcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class ProductionChangeType(StrEnum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"


class RepositoryBranchSelection(StrEnum):
    HUMAN_REQUESTED = "HUMAN_REQUESTED"
    REPOSITORY_DEFAULT = "REPOSITORY_DEFAULT"


class RepositoryAcquisitionPolicyV1(ProductionEnvironmentContract):
    branch_selection: RepositoryBranchSelection
    ref_scope: str = Field(default="SINGLE_BRANCH", pattern=r"^SINGLE_BRANCH$")
    history: str = Field(default="FULL_HISTORY", pattern=r"^FULL_HISTORY$")


class RepositoryAssetBinding(ProductionEnvironmentContract):
    asset_id: UUID
    repository_identity: str = Field(min_length=1)
    source: str = Field(min_length=1)
    branch: str | None = Field(default=None, min_length=1)
    default_branch: str = Field(min_length=1)
    requested_branch: str | None = Field(default=None, min_length=1)
    source_revision: str = Field(pattern=GIT_OBJECT_PATTERN)
    source_tree_identity: str = Field(pattern=GIT_OBJECT_PATTERN)
    acquisition_policy: RepositoryAcquisitionPolicyV1
    mount_path: str
    writable: bool
    provenance_reference: str = Field(min_length=1)

    _safe_mount = field_validator("mount_path")(safe_workspace_path)

    @model_validator(mode="after")
    def validate_acquisition_selection(self) -> "RepositoryAssetBinding":
        if self.branch is None:
            raise ValueError("Workspace repository requires a selected branch")
        human_selected = (
            self.acquisition_policy.branch_selection
            is RepositoryBranchSelection.HUMAN_REQUESTED
        )
        if human_selected != (self.requested_branch is not None):
            raise ValueError("requested branch and acquisition selection differ")
        if self.requested_branch is not None and self.branch != self.requested_branch:
            raise ValueError("Workspace did not select the Human-requested branch")
        if self.requested_branch is None and self.branch != self.default_branch:
            raise ValueError("Workspace did not select Repository Reality default branch")
        return self


class EnvironmentConfiguration(ProductionEnvironmentContract):
    provider_profile: str = Field(min_length=1)
    dependency_profile_reference: str | None = Field(default=None, min_length=1)
    toolchain_references: tuple[str, ...] = ()
    lifecycle_policy_references: tuple[str, ...] = ()


class RuntimeConfiguration(ProductionEnvironmentContract):
    runtime_profile: str = Field(min_length=1)
    preview_enabled: bool = True
    network_policy_reference: str | None = Field(default=None, min_length=1)
    resource_policy_reference: str | None = Field(default=None, min_length=1)


class ProductionWorkspaceV1(ProductionEnvironmentContract):
    schema_version: int = Field(default=1, ge=1, le=1)
    id: UUID
    work_id: UUID
    repository_assets: tuple[RepositoryAssetBinding, ...] = Field(min_length=1)
    environment_configuration: EnvironmentConfiguration
    runtime_configuration: RuntimeConfiguration
    generated_roots: tuple[str, ...] = ()
    created_at: datetime

    _created_timezone = field_validator("created_at")(require_timezone)
    _safe_generated = field_validator("generated_roots")(
        lambda values: tuple(safe_workspace_path(value) for value in values)
    )

    @model_validator(mode="after")
    def validate_repository_vector(self) -> "ProductionWorkspaceV1":
        identities = [item.repository_identity for item in self.repository_assets]
        mounts = [item.mount_path for item in self.repository_assets]
        asset_ids = [item.asset_id for item in self.repository_assets]
        if len(set(identities)) != len(identities):
            raise ValueError("repository identities must be unique in a Workspace")
        if len(set(mounts)) != len(mounts):
            raise ValueError("repository mount paths must be unique in a Workspace")
        if len(set(asset_ids)) != len(asset_ids):
            raise ValueError("repository asset bindings must be unique")
        return self


class ProductionEnvironmentV1(ProductionEnvironmentContract):
    schema_version: int = Field(default=1, ge=1, le=1)
    id: UUID
    work_id: UUID
    workspace_id: UUID
    lifecycle_state: EnvironmentLifecycleState
    runtime_state: EnvironmentRuntimeState
    provider_reference: str | None = Field(default=None, min_length=1)
    artifact_references: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()
    created_at: datetime
    updated_at: datetime
    version: int = Field(default=1, ge=1)

    _created_timezone = field_validator("created_at")(require_timezone)
    _updated_timezone = field_validator("updated_at")(require_timezone)

    @model_validator(mode="after")
    def validate_environment_state(self) -> "ProductionEnvironmentV1":
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")
        if self.lifecycle_state is EnvironmentLifecycleState.ACTIVE:
            if self.runtime_state is not EnvironmentRuntimeState.READY:
                raise ValueError("ACTIVE environment requires READY runtime state")
            if self.provider_reference is None:
                raise ValueError("ACTIVE environment requires a provider reference")
        if self.lifecycle_state is EnvironmentLifecycleState.DESTROYED and (
            self.runtime_state not in {
                EnvironmentRuntimeState.NOT_PROVISIONED,
                EnvironmentRuntimeState.STOPPED,
            }
        ):
            raise ValueError("DESTROYED environment cannot retain a live runtime")
        return self


class LifecycleDecisionContext(ProductionEnvironmentContract):
    idle_seconds: int | None = Field(default=None, ge=0)
    work_state: str = Field(min_length=1)
    human_review_pending: bool = False
    reachable_reference_count: int = Field(default=0, ge=0)
    organization_policy_reference: str | None = Field(default=None, min_length=1)
    cost_policy_reference: str | None = Field(default=None, min_length=1)
    cleanup_authorized: bool = False


class LifecycleTransitionRecord(ProductionEnvironmentContract):
    id: UUID
    environment_id: UUID
    from_state: EnvironmentLifecycleState
    to_state: EnvironmentLifecycleState
    actor_reference: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    policy_reference: str = Field(min_length=1)
    decided_at: datetime

    _decided_timezone = field_validator("decided_at")(require_timezone)


class PreviewRuntimeV1(ProductionEnvironmentContract):
    schema_version: int = Field(default=1, ge=1, le=1)
    id: UUID
    environment_id: UUID
    workspace_id: UUID
    environment_lifecycle_state: EnvironmentLifecycleState
    status: PreviewRuntimeStatus
    preview_reference: str = Field(min_length=1)
    endpoint: str | None = Field(default=None, min_length=1)
    artifact_references: tuple[str, ...] = Field(min_length=1)
    created_at: datetime
    updated_at: datetime

    _created_timezone = field_validator("created_at")(require_timezone)
    _updated_timezone = field_validator("updated_at")(require_timezone)

    @model_validator(mode="after")
    def validate_preview_readiness(self) -> "PreviewRuntimeV1":
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")
        if self.status is PreviewRuntimeStatus.READY:
            if self.environment_lifecycle_state is not EnvironmentLifecycleState.ACTIVE:
                raise ValueError("READY Preview requires an ACTIVE environment")
            if self.endpoint is None:
                raise ValueError("READY Preview requires an endpoint")
        return self


class GitContinuityV1(ProductionEnvironmentContract):
    schema_version: int = Field(default=1, ge=1, le=1)
    repository_identity: str = Field(min_length=1)
    source: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    base_commit: str = Field(pattern=GIT_OBJECT_PATTERN)
    current_commit: str = Field(pattern=GIT_OBJECT_PATTERN)
    current_tree_identity: str = Field(pattern=GIT_OBJECT_PATTERN)
    ancestry: tuple[str, ...] = Field(min_length=1)
    diff_reference: str = Field(min_length=1)
    observed_at: datetime

    _observed_timezone = field_validator("observed_at")(require_timezone)

    @model_validator(mode="after")
    def validate_ancestry(self) -> "GitContinuityV1":
        if self.ancestry[0] != self.base_commit:
            raise ValueError("Git ancestry must begin at the exact base commit")
        if self.ancestry[-1] != self.current_commit:
            raise ValueError("Git ancestry must end at the current commit")
        if len(set(self.ancestry)) != len(self.ancestry):
            raise ValueError("Git ancestry cannot contain duplicate commits")
        return self


class DeliveryIntentV1(ProductionEnvironmentContract):
    schema_version: int = Field(default=1, ge=1, le=1)
    id: UUID
    work_id: UUID
    environment_id: UUID
    repository_identity: str = Field(min_length=1)
    kinds: tuple[DeliveryIntentKind, ...] = Field(min_length=1)
    target_branch: str = Field(min_length=1)
    commit: str = Field(pattern=GIT_OBJECT_PATTERN)
    pull_request_reference: str | None = Field(default=None, min_length=1)
    state: ProductionDeliveryState = ProductionDeliveryState.READY_FOR_HUMAN_ACCEPTANCE
    created_at: datetime
    updated_at: datetime
    version: int = Field(default=1, ge=1)

    _created_timezone = field_validator("created_at")(require_timezone)
    _updated_timezone = field_validator("updated_at")(require_timezone)

    @model_validator(mode="after")
    def validate_intent(self) -> "DeliveryIntentV1":
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")
        if len(set(self.kinds)) != len(self.kinds):
            raise ValueError("delivery intent kinds must be unique")
        if (
            DeliveryIntentKind.PULL_REQUEST_PREPARATION in self.kinds
            and DeliveryIntentKind.BRANCH_CREATION not in self.kinds
        ):
            raise ValueError("pull-request preparation requires branch creation intent")
        return self


class HumanDeliveryDecision(ProductionEnvironmentContract):
    id: UUID
    delivery_intent_id: UUID
    action: HumanDeliveryAction
    authority_kind: DeliveryAuthorityKind = DeliveryAuthorityKind.HUMAN_EXPLICIT
    authority_identity: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    decided_at: datetime

    _decided_timezone = field_validator("decided_at")(require_timezone)


class ResourceReferenceV1(ProductionEnvironmentContract):
    schema_version: int = Field(default=1, ge=1, le=1)
    id: UUID
    source_kind: ResourceKind
    source_reference: str = Field(min_length=1)
    target_kind: ResourceKind
    target_reference: str = Field(min_length=1)
    relationship: ReferenceRelationship
    created_at: datetime

    _created_timezone = field_validator("created_at")(require_timezone)

    @model_validator(mode="after")
    def reject_self_reference(self) -> "ResourceReferenceV1":
        if (
            self.source_kind is self.target_kind
            and self.source_reference == self.target_reference
        ):
            raise ValueError("resource references cannot point to themselves")
        return self


class RepositoryRevisionReference(ProductionEnvironmentContract):
    repository_identity: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    before_revision: str = Field(pattern=GIT_OBJECT_PATTERN)
    after_revision: str = Field(pattern=GIT_OBJECT_PATTERN)
    diff_reference: str = Field(min_length=1)


class ProductionChangeReference(ProductionEnvironmentContract):
    repository_identity: str = Field(min_length=1)
    path: str
    change_type: ProductionChangeType
    artifact_reference: str | None = Field(default=None, min_length=1)

    _safe_path = field_validator("path")(safe_repository_path)


class VerificationResultReference(ProductionEnvironmentContract):
    reference: str = Field(min_length=1)
    outcome: VerificationOutcome


class DeliveryResultReference(ProductionEnvironmentContract):
    reference: str = Field(min_length=1)
    state: ProductionDeliveryState


class ProductionRecordV1(ProductionEnvironmentContract):
    schema_version: int = Field(default=1, ge=1, le=1)
    id: UUID
    work_reference: str = Field(min_length=1)
    task_contract_reference: str = Field(min_length=1)
    repository_revisions: tuple[RepositoryRevisionReference, ...] = Field(min_length=1)
    environment_reference: str = Field(min_length=1)
    changes: tuple[ProductionChangeReference, ...] = Field(min_length=1)
    verification_results: tuple[VerificationResultReference, ...] = Field(min_length=1)
    delivery_result: DeliveryResultReference
    created_at: datetime
    content_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    _created_timezone = field_validator("created_at")(require_timezone)

    @model_validator(mode="after")
    def bind_content_digest(self) -> "ProductionRecordV1":
        repository_identities = [item.repository_identity for item in self.repository_revisions]
        if len(set(repository_identities)) != len(repository_identities):
            raise ValueError("Production Record repository revisions must be unique")
        known = set(repository_identities)
        if any(change.repository_identity not in known for change in self.changes):
            raise ValueError("every change must reference a recorded repository revision")
        payload = self.model_dump(mode="json", exclude={"content_digest"})
        expected = canonical_digest(payload)
        if self.content_digest is not None and self.content_digest != expected:
            raise ValueError("Production Record digest does not match its content")
        object.__setattr__(self, "content_digest", expected)
        return self


class GitOperationProductionRecordV1(ProductionEnvironmentContract):
    """Immutable Production Record for a verified Git-only PWU (no fake delivery)."""

    schema_version: int = Field(default=1, ge=1, le=1)
    id: UUID
    work_id: UUID
    task_contract_id: UUID
    pwu_id: UUID
    attempt_id: UUID
    environment_id: UUID
    checkpoint_id: UUID
    capability_id: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    repository_identity: str = Field(min_length=1)
    source_revision: str = Field(pattern=GIT_OBJECT_PATTERN)
    resulting_branch: str = Field(min_length=1)
    resulting_revision: str = Field(pattern=GIT_OBJECT_PATTERN)
    verification_reference: str = Field(min_length=1)
    created_at: datetime
    content_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    _created_timezone = field_validator("created_at")(require_timezone)

    @model_validator(mode="after")
    def bind_content_digest(self) -> "GitOperationProductionRecordV1":
        expected = canonical_digest(self.model_dump(mode="json", exclude={"content_digest"}))
        if self.content_digest is not None and self.content_digest != expected:
            raise ValueError("Git Production Record digest does not match its content")
        object.__setattr__(self, "content_digest", expected)
        return self


class ProviderEnvironmentHandle(ProductionEnvironmentContract):
    provider_identity: str = Field(min_length=1)
    environment_id: UUID
    opaque_reference: str = Field(min_length=1)


class PreparedRepositoryMount(ProductionEnvironmentContract):
    repository_identity: str = Field(min_length=1)
    host_path: Path
    container_path: str
    source_revision: str = Field(pattern=GIT_OBJECT_PATTERN)
    writable: bool

    _safe_container_path = field_validator("container_path")(safe_workspace_path)


class PreparedWorkspaceV1(ProductionEnvironmentContract):
    schema_version: int = Field(default=1, ge=1, le=1)
    workspace_id: UUID
    root_path: Path
    repository_mounts: tuple[PreparedRepositoryMount, ...] = Field(min_length=1)
    prepared_at: datetime

    _prepared_timezone = field_validator("prepared_at")(require_timezone)

    @model_validator(mode="after")
    def validate_mounts(self) -> "PreparedWorkspaceV1":
        identities = [item.repository_identity for item in self.repository_mounts]
        container_paths = [item.container_path for item in self.repository_mounts]
        if len(set(identities)) != len(identities):
            raise ValueError("prepared repository identities must be unique")
        if len(set(container_paths)) != len(container_paths):
            raise ValueError("prepared container paths must be unique")
        root = self.root_path.resolve()
        for mount in self.repository_mounts:
            host_path = mount.host_path.resolve()
            if root not in host_path.parents:
                raise ValueError("prepared repository mount escapes Workspace root")
        return self


class EnvironmentProvisionRequest(ProductionEnvironmentContract):
    environment: ProductionEnvironmentV1
    workspace: ProductionWorkspaceV1
    prepared_workspace: PreparedWorkspaceV1
    image_reference: str = Field(min_length=1)

    @model_validator(mode="after")
    def bind_environment_workspace(self) -> "EnvironmentProvisionRequest":
        if self.environment.workspace_id != self.workspace.id:
            raise ValueError("environment and workspace identities differ")
        if self.environment.work_id != self.workspace.work_id:
            raise ValueError("environment and workspace Work bindings differ")
        if self.prepared_workspace.workspace_id != self.workspace.id:
            raise ValueError("prepared Workspace and Workspace identities differ")
        expected = {
            (item.repository_identity, item.mount_path)
            for item in self.workspace.repository_assets
        }
        actual = {
            (item.repository_identity, item.container_path)
            for item in self.prepared_workspace.repository_mounts
        }
        if expected != actual:
            raise ValueError("prepared Workspace repository vector differs")
        return self


class EnvironmentCommand(ProductionEnvironmentContract):
    argv: tuple[str, ...] = Field(min_length=1)
    working_directory: str

    _safe_working_directory = field_validator("working_directory")(safe_workspace_path)

    @field_validator("argv")
    @classmethod
    def nonblank_arguments(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value for value in values):
            raise ValueError("command arguments cannot be blank")
        return values


class EnvironmentCommandResult(ProductionEnvironmentContract):
    command: EnvironmentCommand
    exit_code: int
    stdout_reference: str | None = Field(default=None, min_length=1)
    stderr_reference: str | None = Field(default=None, min_length=1)


class EnvironmentCommandObservation(ProductionEnvironmentContract):
    """Bounded Provider observation returned to the existing Native Executor."""

    result: EnvironmentCommandResult
    stdout: str
    stderr: str
    stdout_truncated: bool = False
    stderr_truncated: bool = False


class CollectedEnvironmentOutput(ProductionEnvironmentContract):
    path: str
    artifact_reference: str = Field(min_length=1)
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)

    _safe_path = field_validator("path")(safe_workspace_path)


class NativeExecutionEnvironmentBindingV1(ProductionEnvironmentContract):
    """Durable WHERE binding for one existing Work/PWU/Native Attempt."""

    schema_version: int = Field(default=1, ge=1, le=1)
    work_id: UUID
    pwu_id: UUID
    attempt_id: UUID
    task_contract_reference: str = Field(min_length=1)
    workspace: ProductionWorkspaceV1
    prepared_workspace: PreparedWorkspaceV1
    environment: ProductionEnvironmentV1
    provider_handle: ProviderEnvironmentHandle
    created_at: datetime

    _created_timezone = field_validator("created_at")(require_timezone)

    @model_validator(mode="after")
    def validate_native_lineage(self) -> "NativeExecutionEnvironmentBindingV1":
        if self.workspace.work_id != self.work_id:
            raise ValueError("Production Workspace belongs to another Work")
        if self.environment.work_id != self.work_id:
            raise ValueError("Production Environment belongs to another Work")
        if self.environment.workspace_id != self.workspace.id:
            raise ValueError("Production Environment and Workspace differ")
        if self.prepared_workspace.workspace_id != self.workspace.id:
            raise ValueError("prepared and governed Workspaces differ")
        if self.provider_handle.environment_id != self.environment.id:
            raise ValueError("Provider handle belongs to another Environment")
        return self


class ProductionEnvironmentProvider(Protocol):
    """Provider-neutral boundary; business logic never depends on Docker."""

    def create_workspace_environment(
        self, request: EnvironmentProvisionRequest
    ) -> ProviderEnvironmentHandle: ...

    def prepare_dependencies(
        self,
        handle: ProviderEnvironmentHandle,
        commands: tuple[EnvironmentCommand, ...],
    ) -> tuple[EnvironmentCommandResult, ...]: ...

    def execute_commands(
        self,
        handle: ProviderEnvironmentHandle,
        commands: tuple[EnvironmentCommand, ...],
    ) -> tuple[EnvironmentCommandResult, ...]: ...

    def execute_observed(
        self,
        handle: ProviderEnvironmentHandle,
        command: EnvironmentCommand,
    ) -> EnvironmentCommandObservation: ...

    def collect_outputs(
        self,
        handle: ProviderEnvironmentHandle,
        paths: tuple[str, ...],
    ) -> tuple[CollectedEnvironmentOutput, ...]: ...

    def cleanup(self, handle: ProviderEnvironmentHandle) -> None: ...


class ProductionEnvironmentError(RuntimeError):
    """Base error for Production Environment invariant violations."""


class LifecycleTransitionRejected(ProductionEnvironmentError):
    pass


class DeliveryAuthorizationRejected(ProductionEnvironmentError):
    pass


class EnvironmentProviderError(ProductionEnvironmentError):
    pass
