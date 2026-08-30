"""S4-B exact Runtime Commit contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from spg.domain.runtime import BaselinePointerRecord, SnapshotRecord


class RuntimeCommitRequest(BaseModel):
    """Exact governed basis; no latest/current Candidate lookup is permitted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    candidate_fingerprint: str = Field(min_length=64, max_length=64)
    human_authorization_id: UUID
    repository_integration_effect_id: UUID


class RuntimeCommitRecord(BaseModel):
    """Immutable audit linkage for one admitted Trusted Baseline transition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    candidate_id: UUID
    candidate_fingerprint: str
    human_authorization_id: UUID
    repository_integration_effect_id: UUID
    source_baseline_id: UUID
    new_baseline_id: UUID
    production_run_id: UUID
    plan_revision_id: UUID
    repository_identity: str
    target_authoritative_ref: str
    expected_source_repository_revision: str
    repository_revision: str
    repository_tree_identity: str
    satisfied_work_unit_ids: tuple[UUID, ...]
    completion_evaluation_ids: tuple[UUID, ...]
    verification_record_ids: tuple[UUID, ...]
    production_admissibility_id: UUID
    production_admissibility_basis_fingerprint: str
    commit_fingerprint: str
    committed_at: datetime


class RuntimeCommitResult(BaseModel):
    """Authoritative local result; repository reality was observed, not mutated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime_commit: RuntimeCommitRecord
    trusted_baseline: SnapshotRecord
    current_pointer: BaselinePointerRecord
    observed_repository_revision: str
    idempotent_recognition: bool
