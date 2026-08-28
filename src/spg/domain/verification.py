"""S3-B exact-subject Verification and production-admissibility contracts."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from spg.domain.runtime import WorkUnitRecord


class VerificationResultValue(StrEnum):
    """Assurance-owned result for one exact obligation and subject."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class ProductionAdmissibilityOutcome(StrEnum):
    """SPG decision about use of evidence in one production context."""

    ADMISSIBLE = "ADMISSIBLE"
    NOT_ADMISSIBLE = "NOT_ADMISSIBLE"


class VerificationProviderBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_identity: str = Field(min_length=1)
    provider_version: str = Field(min_length=1)


class ProposedRepositorySnapshotRecord(BaseModel):
    """Immutable non-authoritative Git subject derived from exact Produced Reality."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    production_run_id: UUID
    work_unit_id: UUID
    plan_revision_id: UUID
    source_baseline_id: UUID
    attempt_id: UUID
    generation: int
    completion_evaluation_id: UUID
    repository_observation_id: UUID
    repository_identity: str
    repository_ref: str
    authoritative_ref_revision: str
    proposed_commit_identity: str
    tree_identity: str
    basis_fingerprint: str
    created_at: datetime


class VerificationEvidence(BaseModel):
    """Lightweight provider evidence; not an Evidence Graph or Trust Score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    obligation: str
    subject_commit_identity: str
    subject_tree_identity: str
    expected: str
    observed: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerificationCapabilityRequest(BaseModel):
    """Provider-neutral request bound to an exact immutable subject."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    verification_identity: UUID
    obligation: str = Field(min_length=1)
    snapshot_id: UUID
    proposed_commit_identity: str
    tree_identity: str
    completion_evaluation_id: UUID
    plan_revision_id: UUID
    source_baseline_id: UUID


class VerificationCapabilityResult(BaseModel):
    """Assurance result returned through the replaceable capability seam."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result: VerificationResultValue
    evidence: VerificationEvidence


class VerificationRecord(BaseModel):
    """Immutable assurance result and evidence for one exact verification basis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    production_run_id: UUID
    work_unit_id: UUID
    plan_revision_id: UUID
    source_baseline_id: UUID
    completion_evaluation_id: UUID
    proposed_snapshot_id: UUID
    proposed_commit_identity: str
    tree_identity: str
    obligation: str
    obligation_fingerprint: str
    provider: VerificationProviderBinding
    result: VerificationResultValue
    evidence: VerificationEvidence
    basis_fingerprint: str
    created_at: datetime


class VerificationApplicabilityAssessment(BaseModel):
    """Relational applicability conclusion that never rewrites historical result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    verification_record_id: UUID
    proposed_snapshot_id: UUID
    applicable: bool
    reasons: tuple[str, ...]


class ProductionAdmissibilityObligation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    obligation: str
    verification_record_id: UUID | None
    result: VerificationResultValue | None
    applicable: bool
    admissible: bool
    reason: str


class ProductionAdmissibilityRecord(BaseModel):
    """SPG-owned evidence-admission fact, distinct from Assurance truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    production_run_id: UUID
    work_unit_id: UUID
    plan_revision_id: UUID
    source_baseline_id: UUID
    completion_evaluation_id: UUID
    proposed_snapshot_id: UUID
    required_obligations_fingerprint: str
    verification_record_ids: tuple[UUID, ...]
    obligation_results: tuple[ProductionAdmissibilityObligation, ...]
    basis_fingerprint: str
    outcome: ProductionAdmissibilityOutcome
    created_at: datetime


class SatisfactionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    admissibility: ProductionAdmissibilityRecord
    work_unit: WorkUnitRecord
