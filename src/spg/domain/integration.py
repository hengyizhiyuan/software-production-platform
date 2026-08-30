"""S4-A narrow authorized repository-integration contracts."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RepositoryEffectType(StrEnum):
    """The only external effect admitted for FVS-1 S4-A."""

    REPOSITORY_REF_ADVANCE = "REPOSITORY_REF_ADVANCE"


class RepositoryEffectState(StrEnum):
    """Minimal truthful lifecycle; PREPARED may survive an interruption."""

    PREPARED = "PREPARED"
    CONVERGED = "CONVERGED"


class RepositoryIntegrationRequest(BaseModel):
    """Exact Candidate/Authorization subject; no latest-value semantics."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    candidate_fingerprint: str = Field(min_length=64, max_length=64)
    human_authorization_id: UUID


class RepositoryIntegrationEffectRecord(BaseModel):
    """Durable intent and observed state for one exact local Git ref CAS."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    version: int
    effect_type: RepositoryEffectType
    state: RepositoryEffectState
    candidate_id: UUID
    candidate_fingerprint: str
    human_authorization_id: UUID
    repository_identity: str
    target_authoritative_ref: str
    expected_source_repository_revision: str
    proposed_repository_revision: str
    proposed_tree_identity: str
    operation_fingerprint: str
    prepared_at: datetime
    observed_repository_revision: str | None
    observed_at: datetime | None
    converged_at: datetime | None


class RepositoryIntegrationResult(BaseModel):
    """Truthful S4-A result; command outcome alone never implies convergence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    effect: RepositoryIntegrationEffectRecord
    observed_repository_revision: str
    cas_attempted: bool
    converged: bool
