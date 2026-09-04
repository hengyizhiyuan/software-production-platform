"""Provider-neutral contracts for repository-aware Code Work refinement."""

from enum import StrEnum
from hashlib import sha256
import json
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from spg.domain.change import (
    ChangeOperation,
    CodeVerificationObligation,
    ProductionTargetKind,
    path_matches_scope,
    safe_repository_area,
    safe_repository_path,
    safe_repository_scope,
)


class ProposalTargetDisposition(StrEnum):
    REQUIRED = "REQUIRED"
    CONDITIONAL = "CONDITIONAL"


class ProposalConfidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RepositoryProposalProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_identity: str = Field(min_length=1)
    provider_version: str = Field(min_length=1)
    inspection_method: str = Field(min_length=1)


class RepositoryChangeProposalTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    operation: ChangeOperation
    disposition: ProposalTargetDisposition
    rationale: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    confidence: ProposalConfidence

    @field_validator("path")
    @classmethod
    def normalize_path(cls, value: str) -> str:
        return safe_repository_path(value)


class RepositoryChangeProposal(BaseModel):
    """Human-reviewable candidate scope; never Production Authority by itself."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: UUID
    target_kind: ProductionTargetKind = ProductionTargetKind.CODE_WORK
    engineering_resource_id: UUID
    repository_identity: str = Field(min_length=1)
    source_baseline_id: UUID
    source_ref: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    proposed_targets: tuple[RepositoryChangeProposalTarget, ...] = ()
    allowed_areas: tuple[str, ...] = ()
    forbidden_areas: tuple[str, ...] = ()
    rationale: str = Field(min_length=1)
    confidence: ProposalConfidence
    verification_obligations: tuple[CodeVerificationObligation, ...] = ()
    provenance: RepositoryProposalProvenance
    unresolved_scope_questions: tuple[str, ...] = ()

    @field_validator("allowed_areas")
    @classmethod
    def normalize_allowed_areas(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(safe_repository_area(value) for value in values))
        forbidden_fallbacks = {"src/**", "tests/**"}
        if any(value in forbidden_fallbacks for value in normalized):
            raise ValueError("Change Proposal cannot use broad source/test-root fallback")
        return normalized

    @field_validator("forbidden_areas")
    @classmethod
    def normalize_forbidden_areas(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(safe_repository_scope(value) for value in values))

    @model_validator(mode="after")
    def require_non_authoritative_proposal_shape(self) -> "RepositoryChangeProposal":
        if self.target_kind is not ProductionTargetKind.CODE_WORK:
            raise ValueError("Repository Change Proposal must target CODE_WORK")
        paths = tuple(target.path for target in self.proposed_targets)
        if len(paths) != len(set(paths)):
            raise ValueError("Repository Change Proposal paths must be unique")
        if not self.required_targets and not self.allowed_areas and not self.unresolved_scope_questions:
            raise ValueError("an empty Change Proposal must explain its unresolved scope")
        for target in self.required_targets:
            if any(path_matches_scope(target.path, area) for area in self.forbidden_areas):
                raise ValueError("required proposal target conflicts with a forbidden area")
        return self

    @property
    def required_targets(self) -> tuple[RepositoryChangeProposalTarget, ...]:
        return tuple(
            target
            for target in self.proposed_targets
            if target.disposition is ProposalTargetDisposition.REQUIRED
        )

    @property
    def conditional_targets(self) -> tuple[RepositoryChangeProposalTarget, ...]:
        return tuple(
            target
            for target in self.proposed_targets
            if target.disposition is ProposalTargetDisposition.CONDITIONAL
        )

    @property
    def proposal_fingerprint(self) -> str:
        payload = self.model_dump(mode="json")
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


class RepositoryChangeProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    work_id: UUID
    refined_code_intent: str = Field(min_length=1)
    constraints: tuple[str, ...] = ()
    engineering_resource_id: UUID
    repository_identity: str = Field(min_length=1)
    repository_location: str = Field(min_length=1)
    source_baseline_id: UUID
    source_ref: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    explicit_targets: tuple[str, ...] = ()
    explicit_allowed_areas: tuple[str, ...] = ()
    explicit_forbidden_areas: tuple[str, ...] = ()
    requested_verification: tuple[CodeVerificationObligation, ...] = ()


class RepositoryChangeProposalProvider(Protocol):
    """Replaceable read-only refinement intelligence behind a stable contract."""

    def propose(
        self,
        request: RepositoryChangeProposalRequest,
    ) -> RepositoryChangeProposal:
        ...
