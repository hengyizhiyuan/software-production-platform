"""Explicit repository intake and Work-owned scope admission contracts."""
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

class RepositoryIntakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    request_id: UUID
    source: str | None = Field(default=None, max_length=2000)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    authority_identity: str = Field(min_length=1, max_length=255)

    @field_validator("title", "description", "authority_identity")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("A nonblank value is required")
        return value.strip()

class AssetScopeAdmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    resource_id: UUID
    expected_work_revision_id: UUID
    observation_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_identity: str = Field(min_length=1, max_length=255)
    rationale: str = Field(min_length=1, max_length=4000)

    @field_validator("authority_identity", "rationale")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Human asset admission requires a nonblank decision")
        return value.strip()
