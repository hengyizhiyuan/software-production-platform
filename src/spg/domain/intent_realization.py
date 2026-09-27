"""Governed meaning and realization contracts; none interprets Human prose.

The compiler owns language. These immutable values bind its output to source
evidence, preserve distinct clauses and describe what an existing owner owes.
They do not grant capability, credentials, resource access or Human acceptance.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from spg.domain.interaction_actions import ActionSpeechAct, CanonicalOperation
from spg.domain.refinement_contract import RefinementSignalKind
from spg.domain.design_intent import DesignIntentFrame


class SemanticKind(StrEnum):
    OPERATIONAL_ACTION = "OPERATIONAL_ACTION"
    PRODUCTION_INTENT = "PRODUCTION_INTENT"
    QUESTION = "QUESTION"
    ANALYSIS = "ANALYSIS"
    EXPLORE = "EXPLORE"
    DESIGN = "DESIGN"
    CORRECTION = "CORRECTION"
    STATUS_QUERY = "STATUS_QUERY"
    CONSTRAINT = "CONSTRAINT"
    FACT = "FACT"


from spg.domain.semantic_provenance import (
    SemanticOrigin, SemanticProvenance, SemanticArgument, FrozenContract,
)
from spg.domain.engineering_semantics import (
    NeutralSemanticExtractionCandidate, EngineeringSemanticFactCandidate,
)


class OperationalIntent(FrozenContract):
    # Raw structured operation labels are canonicalized by IRK, never by prose.
    operation: str = Field(min_length=1, max_length=80)
    arguments: dict[str, SemanticArgument] = Field(default_factory=dict)
    speech_act: ActionSpeechAct
    conditional: bool = False
    current: bool = True
    unresolved: tuple[str, ...] = ()
    unresolved_arguments: tuple[str, ...] = ()


class ProductionIntent(FrozenContract):
    objective: str = Field(min_length=1)
    primary_change: str = Field(min_length=1)
    scope: tuple[str, ...] = Field(default=(), description="Business scope summaries, not filesystem paths or write grants")
    exclusions: tuple[str, ...] = ()
    target_paths: tuple[SemanticArgument, ...] = Field(default=(),description="Only literal Human-specified repository-relative file paths; empty when source mapping is left to the existing scope owner")
    allowed_areas: tuple[SemanticArgument, ...] = Field(default=(),description="Only literal Human-specified repository-relative filesystem patterns ending in /**; natural business areas belong in scope, never here")
    current: bool
    bounded_change: bool
    systemic_design: bool = False
    new_work: bool = False
    repository_reference: SemanticArgument | None = None
    repository_required: bool = False
    preview_required: bool = False
    acceptance_required: bool = True
    delivery_authorized: bool = False
    unresolved: tuple[str, ...] = ()
    unresolved_arguments: tuple[Literal["objective", "primary_change", "repository_reference"], ...] = ()


class SemanticItem(FrozenContract):
    item_id: str = Field(min_length=1, max_length=100)
    kind: SemanticKind
    statement: str = Field(min_length=1)
    subject: str | None = None
    answer: str | None = None
    observed_facts: dict[str, SemanticArgument] = Field(default_factory=dict)
    provenance: tuple[SemanticProvenance, ...] = Field(min_length=1)
    action: OperationalIntent | None = None
    production: ProductionIntent | None = None
    design_frame: DesignIntentFrame | None = None
    depends_on: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()
    confidence: float = Field(ge=0, le=1)
    requires_human: bool = False

    @model_validator(mode="after")
    def typed_meaning(self):
        if (self.kind is SemanticKind.OPERATIONAL_ACTION) != (self.action is not None):
            raise ValueError("SEMANTIC_TYPE_MISMATCH: operational items require only an action")
        if (self.kind is SemanticKind.PRODUCTION_INTENT) != (self.production is not None):
            raise ValueError("SEMANTIC_TYPE_MISMATCH: production items require structured production intent")
        if self.design_frame is not None and self.kind is not SemanticKind.DESIGN:
            raise ValueError("SEMANTIC_TYPE_MISMATCH: design frames belong to typed design items")
        return self


class SemanticClause(FrozenContract):
    clause_id: str = Field(min_length=1)
    source_record_id: UUID
    source_text: str = Field(min_length=1)
    semantic_item_ids: tuple[str, ...] = Field(min_length=1)


class SemanticQuestion(FrozenContract):
    question: str = Field(min_length=1)
    blocks_current_step: bool
    requires_human: bool
    safe_reversible_assumption: bool = False
    decision_value: int = Field(default=70, ge=0, le=100)
    provenance: SemanticProvenance

    @model_validator(mode="after")
    def authority_is_not_inferred(self):
        if self.requires_human and self.safe_reversible_assumption:
            raise ValueError("ACTION_SCOPE_INFLATION: Human decisions cannot be inferred reversibly")
        return self


class TurnSemanticCandidate(FrozenContract):
    items: tuple[SemanticItem, ...] = Field(min_length=1)
    clauses: tuple[SemanticClause, ...] = Field(min_length=1)
    unresolved: tuple[str, ...] = ()
    human_abstraction_level: Literal["VISION", "DOMAIN", "SOLUTION", "IMPLEMENTATION"] = "DOMAIN"
    uncertain: bool = False
    questions: tuple[SemanticQuestion, ...] = ()


class GovernedSemanticIR(TurnSemanticCandidate):
    schema_version: str = "irk-semantic-ir-v1"
    id: UUID
    interaction_id: UUID
    source_record_id: UUID
    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    engineering_fact_ids: tuple[UUID, ...] = ()
    neutral_semantic_extractions: tuple[NeutralSemanticExtractionCandidate, ...] = ()
    semantic_fact_candidates: tuple[EngineeringSemanticFactCandidate, ...] = ()
    compiler_reference: str
    legacy_typed_projection: bool = False

    @property
    def current_production(self) -> tuple[ProductionIntent, ...]:
        return tuple(i.production for i in self.items if i.production is not None and i.production.current)

    @property
    def repository_source(self) -> str | None:
        for item in self.items:
            if item.action is not None:
                arg = item.action.arguments.get("repository_source")
                if arg is not None:
                    return arg.value
            if item.production is not None and item.production.repository_reference is not None:
                return item.production.repository_reference.value
        return None

    @property
    def operational_requests(self) -> tuple[SemanticItem, ...]:
        return tuple(i for i in self.items if i.action is not None and i.action.current and i.action.speech_act in {
            ActionSpeechAct.EXPLICIT_REQUEST, ActionSpeechAct.READ_ONLY_QUERY,
        })


class ObligationPlane(StrEnum):
    ACTION = "ACTION"
    WORK = "WORK"
    INTERACTION = "INTERACTION"


class ObligationState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SATISFIED = "SATISFIED"
    BLOCKED_WITH_EVIDENCE = "BLOCKED_WITH_EVIDENCE"
    REQUIRES_HUMAN = "REQUIRES_HUMAN"
    SUPERSEDED = "SUPERSEDED"


TERMINAL_OBLIGATION_STATES = frozenset({ObligationState.SATISFIED,
    ObligationState.BLOCKED_WITH_EVIDENCE, ObligationState.REQUIRES_HUMAN,
    ObligationState.SUPERSEDED})


class EffectPredicate(StrEnum):
    OBLIGATION_SUPERSEDED = "OBLIGATION_SUPERSEDED"
    REPOSITORY_READY = "REPOSITORY_READY"
    BRANCH_EXISTS = "BRANCH_EXISTS"
    CURRENT_BRANCH = "CURRENT_BRANCH"
    REPOSITORY_INSPECTED = "REPOSITORY_INSPECTED"
    SEARCH_EVIDENCE = "SEARCH_EVIDENCE"
    PREVIEW_VERIFIED = "PREVIEW_VERIFIED"
    CANDIDATE_ACCEPTED = "CANDIDATE_ACCEPTED"
    DELIVERY_AUTHORIZED = "DELIVERY_AUTHORIZED"
    REMOTE_REF = "REMOTE_REF"
    PULL_REQUEST_OBSERVED = "PULL_REQUEST_OBSERVED"
    WORK_ADMITTED = "WORK_ADMITTED"
    QUESTION_ANSWERED = "QUESTION_ANSWERED"
    OWNER_EFFECT_OBSERVED = "OWNER_EFFECT_OBSERVED"


class ExpectedEffect(FrozenContract):
    predicate: EffectPredicate
    parameters: dict[str, str] = Field(default_factory=dict)
    target: str | None = None
    exact_revision: str | None = None


class ObservedEffect(FrozenContract):
    owner: str
    evidence_references: tuple[str, ...] = Field(min_length=1)
    facts: dict[str, Any]


class ObligationSupersession(FrozenContract):
    replacement_ir_id: UUID
    replacement_item_id: str
    prior_obligation_id: UUID
    owner_disposition: ObservedEffect


class TurnObligation(FrozenContract):
    id: UUID
    turn_id: UUID
    semantic_ir_id: UUID
    semantic_item_id: str
    plane: ObligationPlane
    operation: CanonicalOperation | None = None
    depends_on: tuple[UUID, ...] = ()
    expected_effects: tuple[ExpectedEffect, ...] = Field(min_length=1)
    state: ObligationState = ObligationState.PENDING
    observed_effect: ObservedEffect | None = None
    blocker_reference: str | None = None
    refinement_ids: tuple[UUID, ...] = ()
    supersession: ObligationSupersession | None = None
    version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def terminal_evidence(self):
        if self.state is ObligationState.SUPERSEDED and self.supersession is None:
            raise ValueError("ACTION_TERMINAL_BLOCKER: supersession requires replacement and owner disposition")
        if self.state is ObligationState.SATISFIED and self.observed_effect is None:
            raise ValueError("EXPECTED_EFFECT_NOT_REALIZED: satisfaction needs owner evidence")
        if self.state in {ObligationState.BLOCKED_WITH_EVIDENCE, ObligationState.REQUIRES_HUMAN,
                ObligationState.SUPERSEDED} and not self.blocker_reference:
            raise ValueError("ACTION_TERMINAL_BLOCKER: terminal non-success requires evidence")
        return self


class RealizationScope(StrEnum):
    TURN = "TURN"
    ACTION = "ACTION"
    WORK = "WORK"


RealizationSignal = RefinementSignalKind


class RealizationRefinement(FrozenContract):
    id: UUID
    parent_id: UUID | None = None
    turn_id: UUID
    obligation_id: UUID | None = None
    scope: RealizationScope
    signal: RealizationSignal
    attempt: int = Field(ge=1)
    attempt_budget: int = Field(ge=1)
    evidence_references: tuple[str, ...] = Field(min_length=1)
    local_recovered: bool = False
    work_converged: bool = False

    @model_validator(mode="after")
    def scope_is_not_parent_success(self):
        if self.attempt > self.attempt_budget:
            raise ValueError("TURN_NON_CONVERGING: durable scope budget exhausted")
        if self.scope is not RealizationScope.WORK and self.work_converged:
            raise ValueError("Local recovery cannot establish Work convergence")
        return self
