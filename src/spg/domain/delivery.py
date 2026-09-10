"""Work-owned delivery intent and explicit Human product acceptance.

These records do not admit production, advance SPG, or satisfy Work Reality.
"""
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeliveryTargetKind(StrEnum):
    WEB_APPLICATION = "WEB_APPLICATION"
    MOBILE_APPLICATION = "MOBILE_APPLICATION"
    MINI_PROGRAM = "MINI_PROGRAM"
    API_SERVICE = "API_SERVICE"
    BACKEND_SERVICE = "BACKEND_SERVICE"
    LIBRARY = "LIBRARY"
    AUTOMATION_TOOL = "AUTOMATION_TOOL"
    DOCUMENT_PACKAGE = "DOCUMENT_PACKAGE"
    OTHER_SOFTWARE_ARTIFACT = "OTHER_SOFTWARE_ARTIFACT"


class DeliveryTargetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: DeliveryTargetKind
    title: str = Field(min_length=1, max_length=255)
    acceptance_criteria: tuple[str, ...] = Field(min_length=1, max_length=20)
    authority_identity: str = Field(min_length=1, max_length=255)

    @field_validator("title", "authority_identity")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A nonblank value is required")
        return value.strip()

    @field_validator("acceptance_criteria")
    @classmethod
    def criteria_nonblank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() or len(item) > 2000 for item in values):
            raise ValueError("Each criterion must contain 1 to 2000 characters")
        return tuple(item.strip() for item in values)


class DeliveryTarget(DeliveryTargetRequest):
    id: UUID
    work_id: UUID
    created_at: datetime


class DeliveryArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    media_type: str


class DeliveryManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: UUID
    work_id: UUID
    target_id: UUID
    work_reality_revision_id: UUID | None
    runtime_binding_id: UUID
    runtime_commit_id: UUID
    repository_identity: str
    repository_revision: str
    verification_record_ids: tuple[UUID, ...]
    artifacts: tuple[DeliveryArtifact, ...] = Field(min_length=1)
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime


class HumanAcceptanceDecision(StrEnum):
    ACCEPT = "ACCEPT"
    REQUEST_CHANGES = "REQUEST_CHANGES"


class HumanAcceptanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    manifest_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: HumanAcceptanceDecision
    authority_identity: str = Field(min_length=1, max_length=255)
    rationale: str = Field(min_length=1, max_length=4000)

    @field_validator("authority_identity", "rationale")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A nonblank Human decision is required")
        return value.strip()


class HumanAcceptance(HumanAcceptanceRequest):
    id: UUID
    manifest_id: UUID
    created_at: datetime
