"""Durable retention, pin, hibernation, and cleanup contracts."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RetentionActionKind(StrEnum):
    HIBERNATE = "HIBERNATE"
    DELETE = "DELETE"


class RetentionActionCondition(StrEnum):
    PLANNED = "PLANNED"
    BUNDLE_VERIFIED = "BUNDLE_VERIFIED"
    PHYSICAL_COMPLETE = "PHYSICAL_COMPLETE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ResourcePinRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    resource_kind: str = Field(min_length=1)
    resource_id: str = Field(min_length=1)
    owner_kind: str = Field(min_length=1)
    owner_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    active: bool
    created_at: datetime
    released_at: datetime | None = None


class RetentionActionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    workspace_id: UUID
    action_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_kind: RetentionActionKind
    condition: RetentionActionCondition
    bundle_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    bundle_path: str | None = None
    physical_receipt: dict[str, object] | None = None
    failure: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class WorkspaceTombstoneRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: UUID
    pwu_id: UUID
    attempt_id: UUID
    manifest_digest: str
    last_bundle_digest: str | None = None
    retention_action_id: UUID
    deleted_at: datetime
