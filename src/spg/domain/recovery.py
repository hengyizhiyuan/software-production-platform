"""S5-A immutable recovery-classification contracts."""

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from spg.domain.completion import CompletionEvaluationRecord
from spg.domain.execution import RepositoryObservationRecord
from spg.domain.integration import RepositoryIntegrationEffectRecord
from spg.domain.preparation import AttemptPreparationResult, ExecutorBinding
from spg.domain.runtime import ExecutionAttemptRecord, RuntimeInvariantViolation
from spg.domain.runtime_commit import RuntimeCommitRecord


class RecoverySubjectType(StrEnum):
    ATTEMPT = "ATTEMPT"
    REPOSITORY_INTEGRATION = "REPOSITORY_INTEGRATION"


class RecoveryClassification(StrEnum):
    COHERENT = "COHERENT"
    RECOVERABLE = "RECOVERABLE"
    UNKNOWN = "UNKNOWN"
    DIVERGED = "DIVERGED"
    STALE = "STALE"
    BLOCKED = "BLOCKED"


class RecoveryGuidance(StrEnum):
    """Advisory lowest-sufficient recovery class; never execution authority."""

    NO_ACTION = "NO_ACTION"
    REOBSERVE = "REOBSERVE"
    RESUME_EXISTING_ATTEMPT = "RESUME_EXISTING_ATTEMPT"
    RETRY_WITH_NEW_ATTEMPT = "RETRY_WITH_NEW_ATTEMPT"
    RECORD_EXTERNAL_CONVERGENCE = "RECORD_EXTERNAL_CONVERGENCE"
    RETRY_RUNTIME_COMMIT = "RETRY_RUNTIME_COMMIT"
    REPLAN_SUPERSEDE = "REPLAN_SUPERSEDE"
    ESCALATE_DIVERGENCE = "ESCALATE_DIVERGENCE"


class AttemptRecoveryAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: UUID
    expected_work_unit_id: UUID
    expected_generation: int = Field(ge=1)


class RepositoryRecoveryAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_integration_effect_id: UUID
    expected_operation_fingerprint: str = Field(min_length=64, max_length=64)


RecoveryAssessmentRequest = (
    AttemptRecoveryAssessmentRequest | RepositoryRecoveryAssessmentRequest
)


class RecoveryAssessmentRecord(BaseModel):
    """Historical evidence for one exact governed and observed recovery basis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    subject_type: RecoverySubjectType
    subject_identity: str
    governed_basis: dict[str, Any]
    observed_facts: dict[str, Any]
    differences: tuple[str, ...]
    classification: RecoveryClassification
    guidance: RecoveryGuidance
    subject_is_current: bool
    safely_recoverable: bool
    requires_human_attention: bool
    recovery_barrier: bool
    basis_fingerprint: str
    assessed_at: datetime


class RecoveryBarrierActive(RuntimeInvariantViolation):
    """Raised when a caller tries to cross an unresolved recovery barrier."""


class RecoveryActionType(StrEnum):
    """Narrow exact-subject recovery actions admitted through S5-C."""

    RECORD_EXTERNAL_CONVERGENCE = "RECORD_EXTERNAL_CONVERGENCE"
    RETRY_RUNTIME_COMMIT = "RETRY_RUNTIME_COMMIT"
    REOBSERVE_ATTEMPT_WORK = "REOBSERVE_ATTEMPT_WORK"
    RETRY_WITH_NEW_ATTEMPT = "RETRY_WITH_NEW_ATTEMPT"
    RESUME_EXISTING_ATTEMPT = "RESUME_EXISTING_ATTEMPT"


class RecoveryActionOutcome(StrEnum):
    APPLIED = "APPLIED"
    NO_ACTION = "NO_ACTION"
    SALVAGED = "SALVAGED"
    INCOMPLETE = "INCOMPLETE"
    RETRY_CREATED = "RETRY_CREATED"
    UNSUPPORTED_DEFERRED = "UNSUPPORTED_DEFERRED"


class RecoveryActionRequest(BaseModel):
    """Exact historical assessment subject; no latest-value lookup is allowed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    recovery_assessment_id: UUID
    expected_assessment_fingerprint: str = Field(min_length=64, max_length=64)


class AttemptRetryRecoveryRequest(RecoveryActionRequest):
    """Exact retry preparation inputs; no provider dispatch authority is included."""

    context_package_id: UUID
    executor_binding: ExecutorBinding
    repository_path: Path
    workspace_root: Path


class RecoveryActionRecord(BaseModel):
    """Append-only resolution evidence separate from the source assessment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    recovery_assessment_id: UUID
    assessment_basis_fingerprint: str
    action_type: RecoveryActionType
    subject_type: RecoverySubjectType
    subject_identity: str
    integration_effect_id: UUID | None
    candidate_id: UUID | None
    runtime_commit_id: UUID | None
    old_attempt_id: UUID | None
    new_attempt_id: UUID | None
    old_generation: int | None
    new_generation: int | None
    workspace_identity: str | None
    repository_observation_id: UUID | None
    completion_evaluation_id: UUID | None
    action_basis_fingerprint: str
    outcome: RecoveryActionOutcome
    observed_repository_revision: str | None
    observed_tree_identity: str | None
    resolved_at: datetime


class RecoveryReconciliationResult(BaseModel):
    """Truthful S5-B result; repository Reality was observed, never mutated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: RecoveryActionRecord
    effect: RepositoryIntegrationEffectRecord
    runtime_commit: RuntimeCommitRecord | None
    idempotent_recognition: bool


class RecoveryAssessmentStale(RuntimeInvariantViolation):
    """Raised when current Reality no longer matches the selected assessment."""


class AttemptRecoveryResult(BaseModel):
    """S5-C result that preserves normal observation/completion/Attempt facts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: RecoveryActionRecord
    original_attempt: ExecutionAttemptRecord
    retry_attempt: ExecutionAttemptRecord | None
    observation: RepositoryObservationRecord | None
    completion_evaluation: CompletionEvaluationRecord | None
    retry_preparation: AttemptPreparationResult | None
    retry_required: bool
    workspace_prepared: bool
    idempotent_recognition: bool
