"""Provider-neutral contracts for repository-aware Code Work refinement."""

from enum import StrEnum
from hashlib import sha256
import json
from typing import Literal, Protocol
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


class RepositoryTargetNecessityProof(BaseModel):
    """Read-only witness of a minimum change surface, not model authority."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str = Field(min_length=1)
    # Legacy existing-source witnesses retain their original strict contract.
    evidence_kind: Literal["EXISTING_IMPLEMENTATION", "NEW_TARGET"] = "EXISTING_IMPLEMENTATION"
    source_path: str | None = Field(default=None, min_length=1)
    repository_quote: str | None = Field(default=None, min_length=5, max_length=2000)
    source_revision: str | None = Field(default=None, pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
    source_tree: str | None = Field(default=None, pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
    human_clause: str = Field(min_length=3, max_length=2000)
    necessity: str = Field(min_length=10, max_length=2000)

    @field_validator("path", "source_path")
    @classmethod
    def normalize_witness_path(cls, value: str | None) -> str | None:
        return None if value is None else safe_repository_path(value)

    @model_validator(mode="after")
    def require_exact_evidence_basis(self) -> "RepositoryTargetNecessityProof":
        if self.evidence_kind == "NEW_TARGET":
            if (self.source_revision is None or self.source_tree is None
                    or self.source_path is not None or self.repository_quote is not None):
                raise ValueError("New target proof requires exact revision/tree and no invented existing-source witness")
        elif self.source_path is None or self.repository_quote is None:
            raise ValueError("Existing implementation proof requires an exact source path and repository quote")
        return self


def scope_target_proof_issues(proof: RepositoryTargetNecessityProof, *,
        candidate_paths: tuple[str, ...], tree_paths: tuple[str, ...],
        source_revision: str, source_tree: str,
        human_authority_text: str, observed_sources: dict[str, str],
        refined_code_intent: str | None = None) -> tuple[str, ...]:
    """Identity/provenance checks for a derived necessity judgment, not authority."""
    # Consumer proof cannot rely on a producer's previously validated instance:
    # Pydantic model_copy or a stored projection may bypass shape validation.
    try:
        proof = RepositoryTargetNecessityProof.model_validate(proof.model_dump())
    except ValueError:
        return ("Scope necessity proof evidence contract is invalid",)
    issues = []
    if proof.path not in candidate_paths:
        issues.append("Scope necessity proof is outside observed candidate Reality")
    if (proof.human_clause not in human_authority_text
            or (refined_code_intent is not None and proof.human_clause not in refined_code_intent)):
        issues.append("Scope necessity proof has no exact repository/Human witness")
    if proof.source_revision is not None and proof.source_revision != source_revision:
        issues.append("Scope necessity proof has stale source revision")
    if proof.source_tree is not None and proof.source_tree != source_tree:
        issues.append("Scope necessity proof has stale source tree")
    if proof.evidence_kind == "NEW_TARGET":
        # Use the complete exact Git tree, never absence from a sampled context.
        if (proof.path in tree_paths
                or any(proof.path.startswith(path + "/") or path.startswith(proof.path + "/")
                       for path in tree_paths)):
            issues.append("New target proof conflicts with an existing exact-tree file or directory")
    elif (proof.source_path not in tree_paths or proof.repository_quote is None
            or proof.repository_quote not in observed_sources.get(proof.source_path, "")):
        issues.append("Scope necessity proof has no exact repository/Human witness")
    return tuple(issues)


class ScopeRequirementCoverage(BaseModel):
    """How one governed requirement is discharged by the proposed scope."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    requirement: str = Field(min_length=1)
    disposition: Literal["REQUIRED_TARGET", "ALREADY_PRESENT", "DOWNSTREAM", "MISSING"]
    target_paths: tuple[str, ...] = ()
    source_path: str | None = None
    repository_quote: str | None = None
    explanation: str = Field(min_length=10)

    @field_validator("target_paths")
    @classmethod
    def normalize_target_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(safe_repository_path(path) for path in value)

    @field_validator("source_path")
    @classmethod
    def normalize_source_path(cls, value: str | None) -> str | None:
        return None if value is None else safe_repository_path(value)


class RepositoryScopeValidation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    required_targets: tuple[RepositoryTargetNecessityProof, ...]
    rejected_behaviors: tuple[str, ...]
    explanation: str = Field(min_length=10)
    requirement_coverage: tuple[ScopeRequirementCoverage, ...]
    missing_acceptance_requirements: tuple[str, ...] = ()


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
    candidate_targets: tuple[str, ...] = ()
    necessity_proofs: tuple[RepositoryTargetNecessityProof, ...] = ()
    human_authority_text: str | None = None
    governed_semantic_ir_id: UUID | None = None
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
