"""Explicit repository intake and Work-owned scope admission contracts."""
from enum import StrEnum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RepositoryAcquisitionFailureCategory(StrEnum):
    AUTH_REQUIRED = "AUTH_REQUIRED"
    REPOSITORY_NOT_FOUND = "REPOSITORY_NOT_FOUND"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    INVALID_BRANCH = "INVALID_BRANCH"
    FILESYSTEM_FAILURE = "FILESYSTEM_FAILURE"
    ACQUISITION_FAILED_RETRYABLE = "ACQUISITION_FAILED_RETRYABLE"
    ACQUISITION_FAILED_TERMINAL = "ACQUISITION_FAILED_TERMINAL"


class RepositoryAcquisitionFailure(RuntimeError):
    """Typed Production Environment failure safe for governed persistence."""

    def __init__(
        self,
        category: RepositoryAcquisitionFailureCategory,
        human_message: str,
        *,
        technical_evidence: dict[str, object],
        retryable: bool,
    ) -> None:
        super().__init__(human_message)
        self.category = category
        self.human_message = human_message
        self.technical_evidence = technical_evidence
        self.retryable = retryable

class RepositoryIntakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    request_id: UUID
    source: str | None = Field(default=None, max_length=2000)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    authority_identity: str = Field(min_length=1, max_length=255)
    interaction_id: UUID | None = None
    work_id: UUID | None = None
    attempt_number: int = Field(default=1, ge=1)
    previous_attempt_id: UUID | None = None
    operation_kind: str = "ACQUIRE"
    base_resource_id: UUID | None = None
    target_branch: str | None = None

    @model_validator(mode="after")
    def valid_operation(self):
        if self.operation_kind == "ACQUIRE":
            if self.base_resource_id is not None or self.target_branch is not None:
                raise ValueError("Acquisition cannot contain branch creation fields")
        elif self.operation_kind == "CREATE_BRANCH":
            if (
                self.work_id is None
                or self.base_resource_id is None
                or self.target_branch is None
                or self.source is None
            ):
                raise ValueError("Branch creation requires Work, base Resource, source, and branch")
        else:
            raise ValueError("Unknown repository operation")
        return self

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
