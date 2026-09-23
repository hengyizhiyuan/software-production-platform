"""Executable capability facts; these grant no Work or delivery authority."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CapabilityScope(StrEnum):
    WORK = "WORK"
    USER = "USER"
    TEAM = "TEAM"
    ORGANIZATION = "ORGANIZATION"
    PLATFORM = "PLATFORM"


class ConnectorMaturity(StrEnum):
    BUILT_IN = "BUILT_IN"
    TRUSTED = "TRUSTED"
    PROVISIONAL = "PROVISIONAL"
    UNAVAILABLE = "UNAVAILABLE"


class ConnectorAvailability(StrEnum):
    AVAILABLE = "AVAILABLE"
    ADAPTER_READY = "ADAPTER_READY"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    UNAVAILABLE = "UNAVAILABLE"


class SideEffectLevel(StrEnum):
    READ = "READ"
    WORKSPACE_MUTATION = "WORKSPACE_MUTATION"
    EXTERNAL_WRITE = "EXTERNAL_WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"


class ExecutableCapability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    capability_id: str = Field(min_length=1)
    connector_id: str = Field(min_length=1)
    capability_family: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    scope: CapabilityScope
    owner_id: str = Field(min_length=1)
    maturity: ConnectorMaturity
    availability: ConnectorAvailability
    permissions_required: tuple[str, ...] = ()
    credential_requirements: tuple[str, ...] = ()
    side_effect_level: SideEffectLevel
    execution_provider: str = Field(min_length=1)
    version: str = Field(min_length=1)
    provenance: tuple[str, ...] = Field(min_length=1)
    enabled: bool = True
    secret_references: tuple[str, ...] = ()
    created_from_work: UUID | None = None
    verification_evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_evidence_for_learned_capability(self):
        if self.scope in {CapabilityScope.WORK, CapabilityScope.USER}:
            if self.created_from_work is None or not self.verification_evidence:
                raise ValueError("learned capabilities require source Work and verification evidence")
        if self.availability is ConnectorAvailability.AVAILABLE and self.execution_provider == "unbound":
            raise ValueError("an available capability requires an executable provider")
        return self


class CapabilityRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    capability_id: str = Field(min_length=1)
    work_id: UUID
    user_id: str = Field(min_length=1)
    operation_ref: str = Field(min_length=1)
    resume_point: dict[str, str] = Field(default_factory=dict)


class ConnectorResolution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement: CapabilityRequirement
    capability: ExecutableCapability | None
    executable: bool
    reason: str
    gap_id: UUID | None = None


class ConnectorCandidate(BaseModel):
    """One Work-local generic adapter proposal, not yet executable capability."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement: CapabilityRequirement
    gap_id: UUID
    execution_provider: str = Field(min_length=1)
    qualification_tool_identity: str = Field(min_length=1)
    side_effect_level: SideEffectLevel
    permissions_required: tuple[str, ...] = ()
    provenance: tuple[str, ...] = Field(min_length=1)
