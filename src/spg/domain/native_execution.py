"""Provider-neutral Watt-native Executor v2 contracts and pure invariants."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import PurePosixPath
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def canonical_digest(value: BaseModel | dict[str, Any] | list[Any] | tuple[Any, ...]) -> str:
    """Return the version-independent digest used by native immutable contracts."""

    if isinstance(value, BaseModel):
        payload: Any = value.model_dump(mode="json", exclude_none=False)
    else:
        payload = value
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


class NativeExecutionError(RuntimeError):
    """Base error for native execution contract violations."""


class NativeExecutionConflict(NativeExecutionError):
    """A command or write conflicts with current durable Reality."""


class NativeExecutionNotFound(NativeExecutionError):
    """A required native execution record is unavailable."""


class NativeExecutionNotRunnable(NativeExecutionError):
    """The requested execution cannot currently consume capacity."""


class PWUDisposition(StrEnum):
    OPEN = "OPEN"
    SATISFIED = "SATISFIED"
    EXHAUSTED = "EXHAUSTED"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"


class PWUPhase(StrEnum):
    ADMISSION = "ADMISSION"
    READY = "READY"
    EXECUTING = "EXECUTING"
    AWAITING_RECOVERY = "AWAITING_RECOVERY"
    AWAITING_GOVERNANCE = "AWAITING_GOVERNANCE"
    VERIFYING = "VERIFYING"
    UNSATISFIED = "UNSATISFIED"


class SessionCondition(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class AttemptGrantState(StrEnum):
    GRANTED = "GRANTED"
    RELEASED = "RELEASED"
    FENCED = "FENCED"


class AttemptTerminalOutcome(StrEnum):
    RESULT_READY = "RESULT_READY"
    UNABLE_TO_COMPLETE = "UNABLE_TO_COMPLETE"
    BOUNDARY_CROSSING_REQUIRED = "BOUNDARY_CROSSING_REQUIRED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    STOPPED = "STOPPED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class ExecutionMode(StrEnum):
    QUEUED = "QUEUED"
    RECONCILING = "RECONCILING"
    RUNNING = "RUNNING"
    WAITING_RESOURCE = "WAITING_RESOURCE"
    PAUSE_REQUESTED = "PAUSE_REQUESTED"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    RESUME_REQUESTED = "RESUME_REQUESTED"
    STOP_REQUESTED = "STOP_REQUESTED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    STOPPED = "STOPPED"
    FINISHED = "FINISHED"


class StepKind(StrEnum):
    INFERENCE = "INFERENCE"
    TOOL = "TOOL"
    CHECKPOINT = "CHECKPOINT"
    RECONCILIATION = "RECONCILIATION"


class StepCondition(StrEnum):
    PREPARED = "PREPARED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


class EffectClassification(StrEnum):
    READ = "READ"
    LOCAL_MUTATION = "LOCAL_MUTATION"
    PROCESS = "PROCESS"
    NETWORK = "NETWORK"
    REPOSITORY_INTEGRATION = "REPOSITORY_INTEGRATION"


class EffectCondition(StrEnum):
    INTENDED = "INTENDED"
    STARTING = "STARTING"
    ACTIVE = "ACTIVE"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class WorkspaceCondition(StrEnum):
    ALLOCATING = "ALLOCATING"
    READY = "READY"
    SEALED = "SEALED"
    HIBERNATED = "HIBERNATED"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"
    DELETED = "DELETED"


class CheckpointCondition(StrEnum):
    PREPARING = "PREPARING"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"


class QueueCondition(StrEnum):
    QUEUED = "QUEUED"
    WAITING_RESOURCE = "WAITING_RESOURCE"
    WAITING_HUMAN = "WAITING_HUMAN"
    ALLOCATED = "ALLOCATED"
    EXECUTING = "EXECUTING"
    CHECKPOINTED = "CHECKPOINTED"
    RETURNED_TO_QUEUE = "RETURNED_TO_QUEUE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AllocationCondition(StrEnum):
    ISSUED = "ISSUED"
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class ResourceReservationCondition(StrEnum):
    RESERVED = "RESERVED"
    CONSUMED = "CONSUMED"
    RELEASED = "RELEASED"
    UNKNOWN = "UNKNOWN"


class UsageCertainty(StrEnum):
    ACTUAL = "ACTUAL"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class ControlAction(StrEnum):
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    STOP = "STOP"
    CANCEL = "CANCEL"


class ControlRequestCondition(StrEnum):
    REQUESTED = "REQUESTED"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"


class RecoveryClassification(StrEnum):
    NO_EFFECT = "NO_EFFECT"
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    LOST = "LOST"
    EFFECT_UNRESOLVED = "EFFECT_UNRESOLVED"


class RepairabilityClassification(StrEnum):
    AUTONOMOUSLY_REPAIRABLE = "AUTONOMOUSLY_REPAIRABLE"
    REPAIRABLE_WITH_SUFFICIENT_EVIDENCE = "REPAIRABLE_WITH_SUFFICIENT_EVIDENCE"
    REQUIRES_HUMAN_INPUT = "REQUIRES_HUMAN_INPUT"
    REQUIRES_HUMAN_DECISION = "REQUIRES_HUMAN_DECISION"
    UNSAFE_TO_AUTOREPAIR = "UNSAFE_TO_AUTOREPAIR"


class ObservationConfidence(StrEnum):
    OBSERVED_SUCCESS = "OBSERVED_SUCCESS"
    TRANSIENT_ANOMALY = "TRANSIENT_ANOMALY"
    CONFIRMED_FAILURE = "CONFIRMED_FAILURE"
    INCONCLUSIVE = "INCONCLUSIVE"


class NativeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _safe_relative(value: str) -> str:
    if "\\" in value:
        raise ValueError("paths must use POSIX separators")
    path = PurePosixPath(value)
    if path.is_absolute() or value in {"", "."} or ".." in path.parts:
        raise ValueError("path must be safe and repository-relative")
    return str(path)


class CapabilityGrant(NativeRecord):
    identity: str = Field(min_length=1)
    version: str = Field(min_length=1)
    scope: dict[str, Any] = Field(default_factory=dict)


class SourceMember(NativeRecord):
    mount_id: str = Field(min_length=1)
    asset_id: UUID | None = None
    repository_identity: str = Field(min_length=1)
    source_baseline_ref: str = Field(min_length=1)
    source_commit_oid: str = Field(min_length=1)
    source_tree_oid: str = Field(min_length=1)
    git_object_format: str = "sha1"
    container_path: str = Field(min_length=1)
    read_scope: tuple[str, ...] = ()
    write_scope: tuple[str, ...] = ()
    forbidden_paths: tuple[str, ...] = ()
    integration_target: str | None = None

    @field_validator("read_scope", "write_scope", "forbidden_paths")
    @classmethod
    def validate_scopes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_safe_relative(item) for item in values)

    @field_validator("container_path")
    @classmethod
    def validate_container_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts:
            raise ValueError("container_path must be an absolute normalized POSIX path")
        return str(path)


class SourceVector(NativeRecord):
    schema_version: int = Field(default=1, ge=1)
    members: tuple[SourceMember, ...] = ()
    non_repository_assets: tuple[dict[str, Any], ...] = ()
    digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_vector(self) -> "SourceVector":
        mount_ids = [item.mount_id for item in self.members]
        destinations = [item.container_path for item in self.members]
        if len(set(mount_ids)) != len(mount_ids):
            raise ValueError("source vector mount identities must be unique")
        if len(set(destinations)) != len(destinations):
            raise ValueError("source vector destinations must be unique")
        ordered = tuple(sorted(self.members, key=lambda item: item.mount_id))
        if ordered != self.members:
            raise ValueError("source vector members must be sorted by mount_id")
        expected = canonical_digest(
            {
                "schema_version": self.schema_version,
                "members": [item.model_dump(mode="json") for item in self.members],
                "non_repository_assets": list(self.non_repository_assets),
            }
        )
        if self.digest is not None and self.digest != expected:
            raise ValueError("source vector digest does not match canonical content")
        object.__setattr__(self, "digest", expected)
        return self


class WorkspaceMount(NativeRecord):
    mount_id: str = Field(min_length=1)
    host_path: str = Field(min_length=1)
    container_path: str = Field(min_length=1)
    writable: bool
    write_scope: tuple[str, ...] = ()
    forbidden_paths: tuple[str, ...] = ()

    @field_validator("write_scope", "forbidden_paths")
    @classmethod
    def validate_scopes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_safe_relative(item) for item in values)


class WorkspaceManifest(NativeRecord):
    schema_version: int = Field(default=1, ge=1)
    workspace_id: UUID
    work_id: UUID
    pwu_id: UUID
    attempt_id: UUID
    source_vector_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    host_storage_id: str = Field(min_length=1)
    environment_profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    mounts: tuple[WorkspaceMount, ...]
    generated_roots: tuple[str, ...] = ()
    service_resources: tuple[str, ...] = ()
    evidence_namespace: str = Field(min_length=1)
    retention_policy: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_mounts(self) -> "WorkspaceManifest":
        ids = [item.mount_id for item in self.mounts]
        if len(set(ids)) != len(ids):
            raise ValueError("workspace mount identities must be unique")
        if not any(item.writable for item in self.mounts):
            raise ValueError("native execution requires at least one writable mount")
        return self


class ResourceEnvelope(NativeRecord):
    schema_version: int = Field(default=1, ge=1)
    envelope_id: UUID
    policy_version: str = Field(min_length=1)
    max_inference_submissions: int = Field(default=120, ge=1)
    max_tool_effects: int = Field(default=400, ge=1)
    max_active_seconds: int = Field(default=3600, ge=1)
    max_successor_recoveries: int = Field(default=3, ge=0)
    max_parallel_workers: int = Field(default=1, ge=1)
    max_cost_units: int | None = Field(default=None, ge=0)
    provider_profile: str = Field(min_length=1)
    permitted_provider_profiles: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_provider_profiles(self) -> "ResourceEnvelope":
        profiles = self.permitted_provider_profiles or (self.provider_profile,)
        if self.provider_profile not in profiles:
            raise ValueError("active provider profile must be pre-admitted")
        if len(set(profiles)) != len(profiles):
            raise ValueError("permitted provider profiles must be unique")
        object.__setattr__(self, "permitted_provider_profiles", profiles)
        return self


class ExecutionBindingV2(NativeRecord):
    schema_version: int = Field(default=2, ge=2)
    work_id: UUID
    steering_decision_id: UUID
    pwu_id: UUID
    pwu_contract_version_id: UUID
    pwu_contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    attempt_id: UUID
    generation: int = Field(ge=1)
    session_id: UUID
    source_vector: SourceVector
    workspace: WorkspaceManifest
    context_package_ref: str = Field(min_length=1)
    materialized_input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    backend_implementation: str = Field(min_length=1)
    backend_version: str = Field(min_length=1)
    inference_profile: str = Field(min_length=1)
    capability_grants: Annotated[tuple[CapabilityGrant, ...], Field(min_length=1)]
    resource_envelope: ResourceEnvelope
    stop_conditions: tuple[str, ...] = ()
    obligation_references: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_binding(self) -> "ExecutionBindingV2":
        if self.workspace.attempt_id != self.attempt_id:
            raise ValueError("workspace must bind the exact Attempt")
        if self.workspace.pwu_id != self.pwu_id:
            raise ValueError("workspace must bind the exact PWU")
        if self.workspace.work_id != self.work_id:
            raise ValueError("workspace must bind the exact Work")
        if self.workspace.source_vector_digest != self.source_vector.digest:
            raise ValueError("workspace and binding SourceVector differ")
        capabilities = [item.identity for item in self.capability_grants]
        if len(set(capabilities)) != len(capabilities):
            raise ValueError("capability grants must be unique")
        return self


class PWUContractVersionRecord(NativeRecord):
    id: UUID
    pwu_id: UUID
    revision: int = Field(ge=1)
    objective: str = Field(min_length=1)
    contract_payload: dict[str, Any]
    contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime


class ExecutionSessionRecord(NativeRecord):
    id: UUID
    pwu_id: UUID
    condition: SessionCondition
    parent_checkpoint_id: UUID | None = None
    current_checkpoint_id: UUID | None = None
    current_working_state_version: int = Field(default=0, ge=0)
    version: int = Field(default=1, ge=1)
    created_at: datetime
    closed_at: datetime | None = None


class NativeAttemptBindingRecord(NativeRecord):
    attempt_id: UUID
    pwu_id: UUID
    session_id: UUID
    pwu_contract_version_id: UUID
    source_vector_id: UUID
    workspace_id: UUID
    resource_envelope_id: UUID
    binding: ExecutionBindingV2
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime


class NativeAttemptStateRecord(NativeRecord):
    attempt_id: UUID
    generation: int = Field(ge=1)
    grant_state: AttemptGrantState
    runtime_mode: ExecutionMode
    terminal_outcome: AttemptTerminalOutcome | None = None
    control_version: int = Field(default=0, ge=0)
    worker_epoch: int = Field(default=0, ge=0)
    current_step_sequence: int = Field(default=0, ge=0)
    current_checkpoint_id: UUID | None = None
    blocker_reasons: tuple[str, ...] = ()
    effect_uncertainty: bool = False
    version: int = Field(default=1, ge=1)
    updated_at: datetime

    @model_validator(mode="after")
    def validate_terminal_state(self) -> "NativeAttemptStateRecord":
        if self.grant_state is AttemptGrantState.GRANTED and self.terminal_outcome:
            raise ValueError("live grants cannot carry terminal outcomes")
        if self.grant_state is AttemptGrantState.FENCED and (
            self.terminal_outcome is not AttemptTerminalOutcome.UNKNOWN
        ):
            raise ValueError("fenced Attempts must carry UNKNOWN")
        return self


class ExecutionQueueEntryRecord(NativeRecord):
    id: UUID
    command_id: UUID
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    actor_identity: str = Field(min_length=1)
    work_id: UUID
    pwu_id: UUID
    attempt_id: UUID
    grant_revision: int = Field(ge=1)
    fairness_group: str = Field(min_length=1)
    condition: QueueCondition
    required_capabilities: tuple[str, ...] = ()
    required_provider_profile: str = Field(min_length=1)
    required_resource_profile: str = Field(min_length=1)
    wait_reason: str | None = None
    enqueued_at: datetime
    available_at: datetime
    resume_count: int = Field(default=0, ge=0)
    version: int = Field(default=1, ge=1)


class ExecutionAllocationRecord(NativeRecord):
    id: UUID
    queue_entry_id: UUID
    pwu_id: UUID
    attempt_id: UUID
    grant_revision: int = Field(ge=1)
    worker_id: str = Field(min_length=1)
    worker_profile: str = Field(min_length=1)
    provider_profile: str = Field(min_length=1)
    lease_epoch: int = Field(ge=1)
    lease_token_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    condition: AllocationCondition
    policy_version: str = Field(min_length=1)
    decision_reason: str = Field(min_length=1)
    issued_at: datetime
    start_deadline: datetime
    expires_at: datetime
    released_at: datetime | None = None


class WorkerLeaseRecord(NativeRecord):
    attempt_id: UUID
    allocation_id: UUID
    worker_id: str
    epoch: int = Field(ge=1)
    token_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    deadline: datetime
    heartbeat_at: datetime
    released_at: datetime | None = None


class WorkingPlan(NativeRecord):
    version: int = Field(ge=1)
    objective_reference: str = Field(min_length=1)
    hypotheses: tuple[str, ...] = ()
    chosen_approach: str = Field(min_length=1)
    approach_rationale: str = Field(min_length=1)
    completed_actions: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    obligation_ids: tuple[str, ...] = ()
    evidence_ids: tuple[UUID, ...] = ()


class ExecutionStepRecord(NativeRecord):
    id: UUID
    session_id: UUID
    attempt_id: UUID
    sequence: int = Field(ge=1)
    kind: StepKind
    condition: StepCondition
    request_payload: dict[str, Any]
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_payload: dict[str, Any] | None = None
    result_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    context_revision: int = Field(ge=0)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ExecutionEffectRecord(NativeRecord):
    id: UUID
    step_id: UUID
    proposal_index: int = Field(ge=0)
    tool_identity: str = Field(min_length=1)
    tool_version: str = Field(min_length=1)
    semantic_input: dict[str, Any]
    semantic_input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    classification: EffectClassification
    conflict_domains: tuple[str, ...] = ()
    condition: EffectCondition
    created_at: datetime


class EffectReceiptRecord(NativeRecord):
    id: UUID
    effect_id: UUID
    delivery_id: UUID
    host_identity: str = Field(min_length=1)
    host_nonce: str = Field(min_length=1)
    condition: EffectCondition
    output: dict[str, Any]
    output_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime


class CheckpointBundleRecord(NativeRecord):
    id: UUID
    schema_version: int = Field(default=1, ge=1)
    session_id: UUID
    attempt_id: UUID
    step_sequence: int = Field(ge=0)
    worker_epoch: int = Field(ge=1)
    condition: CheckpointCondition
    source_vector_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    repository_manifest: dict[str, Any]
    execution_manifest: dict[str, Any]
    semantic_manifest: dict[str, Any]
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    consistency_class: str = Field(min_length=1)
    created_at: datetime
    committed_at: datetime | None = None


class ExecutionEvidenceRecord(NativeRecord):
    id: UUID
    pwu_id: UUID
    attempt_id: UUID
    step_id: UUID | None = None
    effect_id: UUID | None = None
    evidence_type: str = Field(min_length=1)
    producer_identity: str = Field(min_length=1)
    subject_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload: dict[str, Any]
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime


class ResultReadyClaimRecord(NativeRecord):
    id: UUID
    pwu_id: UUID
    attempt_id: UUID
    checkpoint_bundle_id: UUID
    contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_vector: dict[str, Any]
    evidence_ids: tuple[UUID, ...]
    residual_obligations: tuple[str, ...]
    claimant_identity: str = Field(min_length=1)
    created_at: datetime


class ExecutionEventRecord(NativeRecord):
    id: UUID
    pwu_id: UUID
    attempt_id: UUID | None = None
    sequence: int = Field(ge=1)
    event_type: str = Field(min_length=1)
    payload: dict[str, Any]
    causation_id: UUID | None = None
    correlation_id: UUID | None = None
    created_at: datetime


class ResourceUsageEntryRecord(NativeRecord):
    id: UUID
    envelope_id: UUID
    attempt_id: UUID
    reservation_key: str = Field(min_length=1)
    resource_type: str = Field(min_length=1)
    amount: int = Field(ge=0)
    certainty: UsageCertainty
    condition: ResourceReservationCondition
    evidence: dict[str, Any]
    created_at: datetime


class ExecutionControlRequestRecord(NativeRecord):
    id: UUID
    command_id: UUID
    attempt_id: UUID
    actor_identity: str = Field(min_length=1)
    action: ControlAction
    expected_control_version: int = Field(ge=0)
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    condition: ControlRequestCondition
    reason: str = Field(min_length=1)
    created_at: datetime
    applied_at: datetime | None = None


class ExecutionRecoveryCaseRecord(NativeRecord):
    id: UUID
    pwu_id: UUID
    attempt_id: UUID
    classification: RecoveryClassification
    basis_checkpoint_id: UUID | None = None
    observed_reality: dict[str, Any]
    residual_obligations: tuple[str, ...]
    effect_uncertainty: bool
    resolution: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class BackendCapabilities(NativeRecord):
    backend_identity: str = Field(min_length=1)
    backend_version: str = Field(min_length=1)
    binding_schema_versions: tuple[int, ...]
    supports_pause: bool
    supports_native_checkpoint: bool
    supports_multi_repository: bool
    supports_observe: bool = True
    supports_control: bool = True
    max_writable_repositories: int = Field(ge=1)
    environment_profiles: tuple[str, ...]


class ExecutionHandle(NativeRecord):
    backend_identity: str
    dispatch_id: UUID
    attempt_id: UUID
    generation: int
    opaque_reference: str = Field(min_length=1)


class BackendObservation(NativeRecord):
    handle: ExecutionHandle
    runtime_mode: ExecutionMode
    terminal_outcome: AttemptTerminalOutcome | None = None
    current_checkpoint_id: UUID | None = None
    progress_summary: str | None = None
    observed_at: datetime


class BackendControlCommand(NativeRecord):
    command_id: UUID
    handle: ExecutionHandle
    action: ControlAction
    expected_control_version: int = Field(ge=0)
    actor_identity: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class BackendControlReceipt(NativeRecord):
    command_id: UUID
    accepted: bool
    condition: ControlRequestCondition
    message: str
    recorded_at: datetime


class NativeExecutionProjection(NativeRecord):
    pwu_id: UUID
    attempt_id: UUID
    session_id: UUID
    grant_state: AttemptGrantState
    runtime_mode: ExecutionMode
    queue_condition: QueueCondition | None
    queue_wait_reason: str | None
    allocation: ExecutionAllocationRecord | None
    current_checkpoint_id: UUID | None
    current_step_sequence: int
    blocker_reasons: tuple[str, ...]
    terminal_outcome: AttemptTerminalOutcome | None


class NativeExecutionAdmission(NativeRecord):
    """Immutable command that admits one existing Attempt to native execution."""

    command_id: UUID
    actor_identity: str = Field(min_length=1)
    fairness_group: str = Field(min_length=1)
    binding: ExecutionBindingV2
    contract: PWUContractVersionRecord
    materialization_path: str = Field(min_length=1)
    required_resource_profile: str = Field(min_length=1)
    available_at: datetime


class WorkerOffer(NativeRecord):
    """Ephemeral worker capacity advertised to the Capacity Scheduling Plane."""

    worker_id: str = Field(min_length=1)
    worker_profile: str = Field(min_length=1)
    provider_profiles: tuple[str, ...]
    resource_profiles: tuple[str, ...]
    capability_identities: tuple[str, ...]
    requested_attempt_id: UUID | None = None
    lease_seconds: int = Field(default=30, ge=5, le=3600)


class WorkerRegistrationRecord(NativeRecord):
    """Durable, expiring evidence that one worker owns scheduler progression."""

    worker_id: str = Field(min_length=1)
    worker_profile: str = Field(min_length=1)
    provider_profiles: tuple[str, ...]
    resource_profiles: tuple[str, ...]
    capability_identities: tuple[str, ...]
    heartbeat_at: datetime
    expires_at: datetime
    version: int = Field(default=1, ge=1)


class QueueProgressionState(StrEnum):
    SCHEDULING = "SCHEDULING"
    CAPACITY_WAIT = "CAPACITY_WAIT"
    INFRASTRUCTURE_UNAVAILABLE = "INFRASTRUCTURE_UNAVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class QueueCapacityObservation(NativeRecord):
    progression_state: QueueProgressionState
    reason: str
    scheduler_alive: bool
    compatible_worker_count: int = Field(ge=0)
    occupied_worker_count: int = Field(ge=0)
    observed_at: datetime


class ExecutionAllocationGrant(NativeRecord):
    """Allocation returned to a worker; the plaintext lease token is not persisted."""

    allocation: ExecutionAllocationRecord
    queue_entry: ExecutionQueueEntryRecord
    lease_token: str = Field(min_length=32)


class SchedulingDecision(NativeRecord):
    """Explainable pure scheduler decision used by the transactional coordinator."""

    selected_queue_entry_id: UUID | None
    selected_fairness_group: str | None
    reason: str
    considered_entry_ids: tuple[UUID, ...]


class InferenceAction(StrEnum):
    CONTINUE = "CONTINUE"
    RESULT_READY = "RESULT_READY"
    WAITING_RESOURCE = "WAITING_RESOURCE"
    UNABLE_TO_COMPLETE = "UNABLE_TO_COMPLETE"
    BOUNDARY_CROSSING_REQUIRED = "BOUNDARY_CROSSING_REQUIRED"


class InferenceDecisionRejected(RuntimeError):
    """An observed Provider response that cannot become an executable decision."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class ToolCallProposal(NativeRecord):
    proposal_index: int = Field(ge=0)
    tool_identity: str = Field(min_length=1)
    arguments: dict[str, Any]
    provider_call_id: str | None = Field(default=None, min_length=1)


class InferenceRequest(NativeRecord):
    attempt_id: UUID
    session_id: UUID
    step_sequence: int = Field(ge=1)
    objective: str = Field(min_length=1)
    working_plan: WorkingPlan
    context_facts: tuple[dict[str, Any], ...]
    available_tools: tuple[dict[str, Any], ...]
    residual_obligations: tuple[str, ...]
    previous_results: tuple[dict[str, Any], ...] = ()


class InferenceUsage(NativeRecord):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)


class InferenceTransportObservation(NativeRecord):
    """Secret-free timing and completeness facts for one Provider response."""

    mode: str = Field(min_length=1)
    response_headers_received: bool
    response_status_code: int | None = Field(default=None, ge=100, le=599)
    headers_elapsed_ms: int | None = Field(default=None, ge=0)
    first_byte_elapsed_ms: int | None = Field(default=None, ge=0)
    elapsed_ms: int = Field(ge=0)
    received_bytes: int = Field(ge=0)
    received_events: int = Field(ge=0)
    terminal_received: bool
    syntactically_complete: bool
    failure_code: str | None = Field(default=None, min_length=1)


class InferenceProviderObservation(NativeRecord):
    provider_identity: str = Field(min_length=1)
    requested_model: str = Field(min_length=1)
    effective_model: str | None = Field(default=None, min_length=1)
    provider_request_id: str | None = Field(default=None, min_length=1)
    response_status: str = Field(min_length=1)
    usage: InferenceUsage | None = None
    transport: InferenceTransportObservation | None = None


class InferenceResponse(NativeRecord):
    action: InferenceAction
    summary: str = Field(min_length=1)
    working_plan: WorkingPlan
    tool_calls: tuple[ToolCallProposal, ...] = ()
    result_claim: dict[str, Any] | None = None
    residual_obligations: tuple[str, ...] = ()
    provider_observation: InferenceProviderObservation | None = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> "InferenceResponse":
        if self.action is InferenceAction.CONTINUE and not self.tool_calls:
            raise ValueError("CONTINUE requires at least one tool call")
        if self.action is InferenceAction.RESULT_READY and self.result_claim is None:
            raise ValueError("RESULT_READY requires a result claim")
        if self.action is not InferenceAction.CONTINUE and self.tool_calls:
            raise ValueError("terminal or waiting inference action cannot propose tools")
        return self


class ToolExecutionRequest(NativeRecord):
    delivery_id: UUID
    attempt_id: UUID
    worker_epoch: int = Field(ge=1)
    step_id: UUID
    proposal: ToolCallProposal
    capability_grants: tuple[CapabilityGrant, ...]
    workspace: WorkspaceManifest


class ToolExecutionResult(NativeRecord):
    delivery_id: UUID
    tool_identity: str
    condition: EffectCondition
    output: dict[str, Any]
    output_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence: tuple[dict[str, Any], ...] = ()


class KernelCheckpoint(NativeRecord):
    schema_version: int = Field(default=1, ge=1)
    step_sequence: int = Field(ge=0)
    working_plan: WorkingPlan
    tool_results: tuple[ToolExecutionResult, ...]
    source_vector_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_claim: dict[str, Any] | None = None
    residual_obligations: tuple[str, ...] = ()


class KernelRunResult(NativeRecord):
    runtime_mode: ExecutionMode
    terminal_outcome: AttemptTerminalOutcome | None = None
    final_checkpoint_id: UUID | None
    step_count: int = Field(ge=0)
    inference_submissions: int = Field(ge=0)
    tool_effects: int = Field(ge=0)
    summary: str = Field(min_length=1)
    result_claim: dict[str, Any] | None = None
    residual_obligations: tuple[str, ...] = ()
    resource_retryable: bool = True
    failure_family: str | None = None
    observation_evidence: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_kernel_result(self) -> "KernelRunResult":
        if self.runtime_mode is ExecutionMode.FINISHED and self.terminal_outcome is None:
            raise ValueError("FINISHED kernel result requires a terminal outcome")
        if self.runtime_mode is not ExecutionMode.FINISHED and self.terminal_outcome is not None:
            raise ValueError("non-terminal kernel result cannot carry terminal outcome")
        if self.runtime_mode is not ExecutionMode.WAITING_RESOURCE and not self.resource_retryable:
            raise ValueError("resource_retryable applies only to WAITING_RESOURCE")
        return self


class SelfRefineEventRecord(NativeRecord):
    """Durable diagnosis for one bounded repair episode on a governed operation."""

    id: UUID
    work_id: UUID
    operation_id: UUID
    created_at: datetime
    failure_family: str
    failure_signature: str = Field(pattern=r"^[0-9a-f]{64}$")
    affected_component: str
    expected_reality: dict[str, Any]
    observed_reality: dict[str, Any]
    diagnosis_summary: str
    root_cause_classification: str
    repair_hypothesis: str
    evidence_references: tuple[str, ...]
    repairability: RepairabilityClassification = RepairabilityClassification.REPAIRABLE_WITH_SUFFICIENT_EVIDENCE
    observation_confidence: ObservationConfidence = ObservationConfidence.CONFIRMED_FAILURE
    budget_decision: dict[str, Any] = Field(default_factory=dict)
    diagnostic_evidence: dict[str, Any] = Field(default_factory=dict)
    final_result: str | None = None
    work_resume_result: str | None = None
    extra_elapsed_seconds: int | None = None
    model_token_usage: dict[str, Any] = Field(default_factory=dict)
    compute_overhead: dict[str, Any] = Field(default_factory=dict)
    known_failure_match: bool = False
    platform_improvement_candidate_ref: str | None = None
    status: str = "OPEN"
    updated_at: datetime


class SelfRefineActionRecord(NativeRecord):
    """Append-only action/observation during a Self-Refine episode."""

    id: UUID
    event_id: UUID
    sequence: int = Field(ge=1)
    created_at: datetime
    repair_action: str
    observed_reality: dict[str, Any]
    evidence_references: tuple[str, ...]
    outcome: str
