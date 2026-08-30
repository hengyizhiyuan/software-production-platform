"""S3-C immutable Candidate sealing and exact Human Authorization contracts."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CandidateCondition(StrEnum):
    """The only admitted S3-C Candidate lifecycle state."""

    SEALED = "SEALED"


class CandidateAuthorizationAction(StrEnum):
    """Permission recorded for a later slice; S3-C never executes it."""

    REPOSITORY_INTEGRATION = "REPOSITORY_INTEGRATION"


class CandidateSealRequest(BaseModel):
    """Explicit exact basis requested for Candidate sealing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposed_snapshot_id: UUID
    production_admissibility_id: UUID
    expected_work_unit_version: int = Field(ge=0)


class BaselineCandidateRecord(BaseModel):
    """Immutable proposal that exact satisfied production may later be integrated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    condition: CandidateCondition
    production_run_id: UUID
    plan_revision_id: UUID
    source_baseline_id: UUID
    repository_identity: str
    target_authoritative_ref: str
    expected_source_repository_revision: str
    proposed_snapshot_id: UUID
    proposed_commit_identity: str
    proposed_tree_identity: str
    satisfied_work_unit_ids: tuple[UUID, ...]
    completion_evaluation_ids: tuple[UUID, ...]
    work_product_reference_ids: tuple[UUID, ...]
    verification_record_ids: tuple[UUID, ...]
    production_admissibility_id: UUID
    production_admissibility_basis_fingerprint: str
    fingerprint: str
    sealed_at: datetime


class CandidateAuthorizationScope(BaseModel):
    """Exact permission that a later S4 operation may consume."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: CandidateAuthorizationAction = (
        CandidateAuthorizationAction.REPOSITORY_INTEGRATION
    )
    repository_identity: str = Field(min_length=1)
    target_authoritative_ref: str = Field(min_length=1)
    expected_source_repository_revision: str = Field(min_length=1)
    proposed_repository_revision: str = Field(min_length=1)


class HumanAuthorizationRequest(BaseModel):
    """No-latest contract: both exact Candidate identity and fingerprint are required."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authority_identity: str = Field(min_length=1)
    candidate_id: UUID
    candidate_fingerprint: str = Field(min_length=64, max_length=64)
    scope: CandidateAuthorizationScope
    rationale: str | None = None


class HumanAuthorizationRecord(BaseModel):
    """Append-only permission record for one exact sealed Candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    authority_identity: str
    candidate_id: UUID
    candidate_fingerprint: str
    scope: CandidateAuthorizationScope
    source_baseline_id: UUID
    repository_identity: str
    target_authoritative_ref: str
    expected_source_repository_revision: str
    proposed_repository_revision: str
    rationale: str | None
    governance_record_id: UUID
    basis_fingerprint: str
    authorized_at: datetime
