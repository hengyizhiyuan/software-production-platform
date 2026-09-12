"""Exact multi-repository CandidateVector and aggregate trust contracts."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from spg.domain.native_execution import canonical_digest


class VectorCondition(StrEnum):
    SEALED = "SEALED"
    AUTHORIZED = "AUTHORIZED"
    PARTIAL = "PARTIAL"
    CONVERGED = "CONVERGED"
    COMMITTED = "COMMITTED"


class VectorTargetCondition(StrEnum):
    PREPARED = "PREPARED"
    CONVERGED = "CONVERGED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class CandidateVectorTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mount_id: str = Field(min_length=1)
    repository_identity: str = Field(min_length=1)
    repository_path: str = Field(min_length=1)
    target_authoritative_ref: str = Field(min_length=1)
    expected_source_revision: str = Field(min_length=1)
    proposed_revision: str = Field(min_length=1)
    proposed_tree_identity: str = Field(min_length=1)
    verification_obligations: tuple[str, ...] = Field(min_length=1)
    verification_evidence_ids: tuple[UUID, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_verification_basis(self) -> "CandidateVectorTarget":
        if len(set(self.verification_obligations)) != len(self.verification_obligations):
            raise ValueError("verification obligations must be unique")
        if len(set(self.verification_evidence_ids)) != len(self.verification_evidence_ids):
            raise ValueError("verification evidence IDs must be unique")
        return self


class CandidateVectorSealRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pwu_id: UUID
    source_vector_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    checkpoint_id: UUID
    targets: tuple[CandidateVectorTarget, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_targets(self) -> "CandidateVectorSealRequest":
        mount_ids = tuple(item.mount_id for item in self.targets)
        identities = tuple(
            (item.repository_identity, item.target_authoritative_ref)
            for item in self.targets
        )
        if mount_ids != tuple(sorted(mount_ids)) or len(set(mount_ids)) != len(mount_ids):
            raise ValueError("CandidateVector targets must have unique sorted mount IDs")
        if len(set(identities)) != len(identities):
            raise ValueError("CandidateVector repository targets must be unique")
        return self

    @property
    def digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


class CandidateVectorRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    pwu_id: UUID
    source_vector_digest: str
    checkpoint_id: UUID
    manifest_digest: str
    condition: VectorCondition
    created_at: datetime
    updated_at: datetime
    version: int = Field(ge=1)


class CandidateVectorAuthorizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    vector_id: UUID
    manifest_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_identity: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class CandidateVectorAuthorizationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    vector_id: UUID
    manifest_digest: str
    authority_identity: str
    rationale: str
    authorized_at: datetime


class CandidateVectorTargetRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    vector_id: UUID
    target: CandidateVectorTarget
    condition: VectorTargetCondition
    observed_revision: str | None = None
    operation_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    prepared_at: datetime
    settled_at: datetime | None = None
    version: int = Field(ge=1)


class CandidateVectorProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    vector: CandidateVectorRecord
    authorization: CandidateVectorAuthorizationRecord | None
    targets: tuple[CandidateVectorTargetRecord, ...]
    aggregate_commit_id: UUID | None = None


class NativeAggregateRuntimeCommitRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    vector_id: UUID
    manifest_digest: str
    authorization_id: UUID
    trusted_vector_digest: str
    committed_at: datetime


class NativeVectorVerificationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    pwu_id: UUID
    mount_id: str = Field(min_length=1)
    proposed_revision: str = Field(min_length=1)
    proposed_tree_identity: str = Field(min_length=1)
    obligation: str = Field(min_length=1)
    provider_identity: str = Field(min_length=1)
    result: str = Field(pattern=r"^(PASS|FAIL|UNKNOWN)$")
    evidence: dict[str, object]
    created_at: datetime
