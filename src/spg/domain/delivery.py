"""Work-owned delivery intent and explicit Human product acceptance.

These records do not admit production, advance SPG, or satisfy Work Reality.
"""
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DeliveryTargetKind(StrEnum):
    SOFTWARE_ARTIFACT = "SOFTWARE_ARTIFACT"
    CLI_TOOL = "CLI_TOOL"
    WEB_APPLICATION = "WEB_APPLICATION"
    MOBILE_APPLICATION = "MOBILE_APPLICATION"
    MINI_PROGRAM = "MINI_PROGRAM"
    API_SERVICE = "API_SERVICE"
    BACKEND_SERVICE = "BACKEND_SERVICE"
    LIBRARY = "LIBRARY"
    AUTOMATION_TOOL = "AUTOMATION_TOOL"
    DOCUMENT_PACKAGE = "DOCUMENT_PACKAGE"
    OTHER_SOFTWARE_ARTIFACT = "OTHER_SOFTWARE_ARTIFACT"


class SoftwareRuntimeRecipe(BaseModel):
    """Typed adapter selection; never an arbitrary shell command."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    adapter: Literal["STATIC_WEB", "FULL_APPLICATION_RUNTIME"]
    entrypoint: str | None = "index.html"

    @model_validator(mode="after")
    def supported_runtime(self):
        from spg.domain.change import safe_repository_path
        if self.adapter == "FULL_APPLICATION_RUNTIME":
            if self.entrypoint is not None:
                raise ValueError("Full application runtime has no static entrypoint")
        elif (self.entrypoint is None
                or safe_repository_path(self.entrypoint) != self.entrypoint
                or not self.entrypoint.endswith(".html")):
            raise ValueError("Static Web entrypoint must be an exact HTML repository path")
        return self


class SoftwareDeliveryDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    form: DeliveryTargetKind
    runtime_recipe: SoftwareRuntimeRecipe
    repository_ref: str
    source_revision: str
    commit_message: str
    changed_files: tuple[dict[str, str], ...]
    verification: tuple[dict, ...]
    reproduction: tuple[str, ...]


class DeliveryTargetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: DeliveryTargetKind
    title: str = Field(min_length=1, max_length=255)
    acceptance_criteria: tuple[str, ...] = Field(min_length=1, max_length=20)
    authority_identity: str = Field(min_length=1, max_length=255)
    software_form: DeliveryTargetKind | None = None
    runtime_recipe: SoftwareRuntimeRecipe | None = None

    @model_validator(mode="after")
    def delivery_adapter_contract(self):
        if self.kind is DeliveryTargetKind.SOFTWARE_ARTIFACT:
            if self.software_form is not DeliveryTargetKind.WEB_APPLICATION or self.runtime_recipe is None:
                raise ValueError("Software delivery requires WEB_APPLICATION and a supported runtime recipe")
        elif self.software_form is not None or self.runtime_recipe is not None:
            raise ValueError("Software configuration belongs to SOFTWARE_ARTIFACT")
        return self

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
    software: SoftwareDeliveryDetails | None = None
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
