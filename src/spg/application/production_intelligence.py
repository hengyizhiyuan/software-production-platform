"""Application services for bounded production-intelligence foundations."""

from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
import json
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field

from spg.domain.engineering_semantics import (
    SemanticFactAuthority,
    SemanticFactReference,
    semantic_fact_statement,
)
from spg.domain.design_intent import DesignObjectType
from spg.domain.production_intelligence import (
    CognitiveContextItem,
    CognitiveContextPackage,
    ContextBudget,
    ContextCandidate,
    ContextSource,
    DecisionTrace,
    DecisionTraceStatus,
    EngineeringActivity,
    EngineeringPattern,
    EvidenceCategory,
    EvidenceExpectation,
    EvidenceReference,
    PatternActivationMetadata,
    PatternDimension,
    PatternEvidenceDirection,
    PatternOption,
    ReasoningSummary,
    SoftwareProductionSop,
    SopActivityGuidance,
    SopCheckpoint,
    SystemCapabilityReality,
    TaskContextReference,
    TaskContract,
)
from spg.domain.response_contract import InformationBudget, InteractionMode, ResponseContract


class ContextAssemblyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    basis_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    purpose: str = Field(min_length=1)
    activity: EngineeringActivity
    candidates: tuple[ContextCandidate, ...]
    semantic_facts: tuple[SemanticFactReference, ...] = ()
    budget: ContextBudget = ContextBudget()


class TaskContractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    activity: EngineeringActivity = EngineeringActivity.FEATURE_DELIVERY
    objective: str = Field(min_length=1)
    scope: tuple[str, ...] = Field(min_length=1)
    constraints: tuple[str, ...] = ()
    acceptance_meaning: tuple[str, ...] = Field(min_length=1)
    out_of_scope: tuple[str, ...] = Field(min_length=1)
    authority_lineage: tuple[str, ...] = Field(min_length=1)
    work_reality_references: tuple[str, ...] = Field(min_length=1)
    ecf_references: tuple[str, ...] = Field(min_length=1)
    semantic_facts: tuple[SemanticFactReference, ...] = ()
    decision_reference: str


class EngineeringPatternCatalog:
    """Small replaceable catalog selected by structured applicability metadata."""

    def __init__(self, patterns: tuple[EngineeringPattern, ...]) -> None:
        identities = tuple((item.pattern_id, item.version) for item in patterns)
        if len(identities) != len(set(identities)):
            raise ValueError("Engineering Pattern identities must be unique")
        self.patterns = patterns

    def select(
        self,
        activity: EngineeringActivity,
        semantic_facts: tuple[SemanticFactReference, ...],
        *,
        limit: int = 3,
    ) -> tuple[EngineeringPattern, ...]:
        relations = {fact.relation for fact in semantic_facts}
        subjects = tuple(fact.subject for fact in semantic_facts)
        selected: list[EngineeringPattern] = []
        for pattern in self.patterns:
            activation = pattern.activation
            if activity not in activation.activities:
                continue
            if activation.requires_semantic_truth and not semantic_facts:
                continue
            if activation.semantic_relations and not relations.intersection(
                activation.semantic_relations
            ):
                continue
            if activation.subject_prefixes and not any(
                subject.startswith(prefix)
                for prefix in activation.subject_prefixes
                for subject in subjects
            ):
                continue
            selected.append(pattern)
            if len(selected) == limit:
                break
        return tuple(selected)


class SoftwareProductionSopCatalog:
    def __init__(self, sops: tuple[SoftwareProductionSop, ...]) -> None:
        self.sops = sops

    def guidance_for(
        self, activity: EngineeringActivity
    ) -> tuple[SoftwareProductionSop, SopActivityGuidance] | None:
        for sop in self.sops:
            for guidance in sop.activities:
                if guidance.activity is activity:
                    return sop, guidance
        return None


class ContextOrchestrator:
    """Select what is needed now while preserving every source boundary."""

    _source_order = {
        ContextSource.SEMANTIC_TRUTH: 0,
        ContextSource.RESPONSE_CONTRACT: 1,
        ContextSource.SYSTEM_CAPABILITY_REALITY: 2,
        ContextSource.WORK_REALITY: 3,
        ContextSource.ECF_REALITY: 4,
        ContextSource.DECISION_MEMORY: 5,
        ContextSource.GUARDIAN_EVIDENCE: 6,
        ContextSource.SOP: 7,
        ContextSource.DOMAIN_PATTERN: 8,
    }

    def __init__(
        self,
        patterns: EngineeringPatternCatalog,
        sops: SoftwareProductionSopCatalog,
    ) -> None:
        self.patterns = patterns
        self.sops = sops

    def assemble(self, request: ContextAssemblyRequest) -> CognitiveContextPackage:
        candidates = list(request.candidates)
        selected_patterns = self.patterns.select(
            request.activity, request.semantic_facts
        )
        for pattern in selected_patterns:
            candidates.append(self._pattern_candidate(pattern))

        sop_selection = self.sops.guidance_for(request.activity)
        sop_reference = None
        if sop_selection is not None:
            sop, guidance = sop_selection
            sop_reference = f"sop:{sop.sop_id}:{sop.version}:{guidance.activity.value}"
            candidates.append(self._sop_candidate(sop, guidance, sop_reference))

        ordered = sorted(
            candidates,
            key=lambda item: (
                not item.required,
                -item.priority,
                self._source_order[item.source],
                item.candidate_id,
            ),
        )
        selected: list[CognitiveContextItem] = []
        source_counts: dict[ContextSource, int] = {}
        used_characters = 0
        for candidate in ordered:
            over_source = (
                source_counts.get(candidate.source, 0)
                >= request.budget.max_items_per_source
            )
            over_items = len(selected) >= request.budget.max_items
            over_characters = (
                used_characters + len(candidate.content)
                > request.budget.max_characters
            )
            if over_source or over_items or over_characters:
                if candidate.required:
                    raise ValueError(
                        "Required governed context does not fit the selected Context Budget"
                    )
                continue
            selected.append(
                CognitiveContextItem(
                    item_id=candidate.candidate_id,
                    source=candidate.source,
                    content=candidate.content,
                    source_reference=candidate.source_reference,
                    authority=candidate.authority,
                    provenance=candidate.provenance,
                    priority=candidate.priority,
                    authoritative=candidate.authoritative,
                )
            )
            source_counts[candidate.source] = source_counts.get(candidate.source, 0) + 1
            used_characters += len(candidate.content)

        return CognitiveContextPackage(
            basis_fingerprint=request.basis_fingerprint,
            purpose=request.purpose,
            activity=request.activity,
            budget=request.budget,
            items=tuple(selected),
            omitted_candidate_count=len(candidates) - len(selected),
            selected_pattern_ids=tuple(
                f"{item.pattern_id}:{item.version}" for item in selected_patterns
            ),
            sop_reference=sop_reference,
        )

    @staticmethod
    def _pattern_candidate(pattern: EngineeringPattern) -> ContextCandidate:
        dimensions = "; ".join(
            f"{dimension.consideration}: "
            + ", ".join(option.description for option in dimension.options)
            for dimension in pattern.dimensions
        )
        return ContextCandidate(
            candidate_id=f"pattern:{pattern.pattern_id}:{pattern.version}",
            source=ContextSource.DOMAIN_PATTERN,
            content=f"{pattern.decision_space}. Consider {dimensions}",
            source_reference=f"pattern:{pattern.pattern_id}:{pattern.version}",
            authority=pattern.authority,
            provenance=pattern.provenance_references,
            priority=45,
        )

    @staticmethod
    def _sop_candidate(
        sop: SoftwareProductionSop,
        guidance: SopActivityGuidance,
        reference: str,
    ) -> ContextCandidate:
        expectations = "; ".join(
            expectation.statement
            for checkpoint in guidance.checkpoints
            for expectation in checkpoint.evidence_expectations
        )
        return ContextCandidate(
            candidate_id=reference,
            source=ContextSource.SOP,
            content=(
                f"{guidance.applicability}. Evidence expected: {expectations}. "
                "These checkpoints do not grant authority or require approval."
            ),
            source_reference=reference,
            authority=sop.authority,
            provenance=(f"sop:{sop.sop_id}:{sop.version}",),
            priority=55,
        )


class TaskContractBuilder:
    """Project governed Work/Steering facts into an explicit PWU obligation."""

    def __init__(self, orchestrator: ContextOrchestrator) -> None:
        self.orchestrator = orchestrator

    def build(self, request: TaskContractRequest) -> TaskContract:
        basis = _fingerprint(request.model_dump(mode="json"))
        candidates = [
            ContextCandidate(
                candidate_id=f"work-reality:{index}",
                source=ContextSource.WORK_REALITY,
                content=reference,
                source_reference=reference,
                authority="WORK_REALITY",
                provenance=(reference,),
                priority=90,
                authoritative=True,
                required=True,
            )
            for index, reference in enumerate(request.work_reality_references, start=1)
        ]
        candidates.extend(
            ContextCandidate(
                candidate_id=f"ecf-reality:{index}",
                source=ContextSource.ECF_REALITY,
                content=reference,
                source_reference=reference,
                authority="SOURCE_REALITY",
                provenance=(reference,),
                priority=80,
                authoritative=True,
                required=True,
            )
            for index, reference in enumerate(request.ecf_references, start=1)
        )
        candidates.extend(
            ContextCandidate(
                candidate_id=f"semantic-fact:{fact.fact_id}",
                source=ContextSource.SEMANTIC_TRUTH,
                content=semantic_fact_statement(fact),
                source_reference=f"semantic-fact:{fact.fact_id}",
                authority=fact.authority.value,
                provenance=(
                    f"work-reality-revision:{fact.source_work_revision_id}",
                ),
                priority=100,
                authoritative=True,
                required=True,
            )
            for fact in request.semantic_facts
        )
        candidates.append(
            ContextCandidate(
                candidate_id="decision-current",
                source=ContextSource.DECISION_MEMORY,
                content=request.decision_reference,
                source_reference=request.decision_reference,
                authority="STEERING_OR_WORK_ADMISSION",
                provenance=(request.decision_reference,),
                priority=85,
                authoritative=True,
                required=True,
            )
        )
        package = self.orchestrator.assemble(
            ContextAssemblyRequest(
                basis_fingerprint=basis,
                purpose="Bounded PWU Task Contract",
                activity=request.activity,
                candidates=tuple(candidates),
                semantic_facts=request.semantic_facts,
                budget=ContextBudget(
                    max_items=24,
                    max_characters=12000,
                    max_items_per_source=12,
                ),
            )
        )

        evidence = tuple(self._semantic_evidence(fact) for fact in request.semantic_facts)
        evidence += (
            EvidenceReference(
                category=EvidenceCategory.ENGINEERING,
                source_reference=request.ecf_references[-1],
                subject_reference="task-scope",
                basis_reference=request.ecf_references[-1],
                assertion="The task is bound to the admitted engineering source basis.",
                authority_domain="ECF/SOURCE_REALITY",
            ),
        )
        sop_expectations = self._sop_expectations(request.activity)
        assurance_expectations = tuple(
            EvidenceExpectation(
                expectation_id=f"task-acceptance-{index}",
                category=EvidenceCategory.ASSURANCE,
                statement=statement,
                owner_boundary="Guardian/Verification owns the assurance result.",
            )
            for index, statement in enumerate(request.acceptance_meaning, start=1)
        )
        decision_id = uuid5(NAMESPACE_URL, f"watt:decision-trace:{basis}")
        task_contract_id = uuid5(NAMESPACE_URL, f"watt:task-contract:{basis}")
        decision = DecisionTrace(
            decision_id=decision_id,
            context_reference=request.decision_reference,
            considered_options=(
                "Execute within the admitted scope and governed meaning",
                "Return to Steering or Human authority before widening the boundary",
            ),
            selected_direction=f"Execute the bounded task: {request.objective}",
            rationale=(
                "The selected direction preserves current Work Reality, semantic facts, "
                "source baseline, and independent verification obligations."
            ),
            authority_reference=request.authority_lineage[-1],
            evidence_references=evidence,
            status=DecisionTraceStatus.ADMITTED,
        )
        factors = (
            "Current governed objective and scope",
            "Current Semantic Truth without reinterpretation",
            "Exact engineering source basis",
            "Independent evidence required for acceptance",
            *(f"Pattern guidance {item}" for item in package.selected_pattern_ids),
        )
        return TaskContract(
            task_contract_id=task_contract_id,
            activity=request.activity,
            objective=request.objective,
            relevant_context=tuple(
                TaskContextReference(
                    source=item.source,
                    reference=item.source_reference,
                    authority=item.authority,
                )
                for item in package.items
            ),
            scope=request.scope,
            constraints=request.constraints,
            acceptance_meaning=request.acceptance_meaning,
            evidence_requirements=tuple((*sop_expectations, *assurance_expectations)),
            out_of_scope=request.out_of_scope,
            authority_lineage=request.authority_lineage,
            semantic_fact_references=request.semantic_facts,
            sop_reference=package.sop_reference,
            reasoning_summary=ReasoningSummary(
                summary=(
                    "Use the admitted task boundary and source Reality, preserve governed "
                    "meaning, and require independent evidence before acceptance."
                ),
                considered_factors=factors,
            ),
            decision_trace=decision,
            evidence_lineage=evidence,
        )

    def _sop_expectations(
        self, activity: EngineeringActivity
    ) -> tuple[EvidenceExpectation, ...]:
        selection = self.orchestrator.sops.guidance_for(activity)
        if selection is None:
            return ()
        _, guidance = selection
        return tuple(
            expectation
            for checkpoint in guidance.checkpoints
            for expectation in checkpoint.evidence_expectations
        )

    @staticmethod
    def _semantic_evidence(fact: SemanticFactReference) -> EvidenceReference:
        category = (
            EvidenceCategory.HUMAN
            if fact.authority is SemanticFactAuthority.HUMAN_EXPLICIT
            else EvidenceCategory.ENGINEERING
        )
        return EvidenceReference(
            category=category,
            source_reference=f"work-reality-revision:{fact.source_work_revision_id}",
            subject_reference=f"semantic-fact:{fact.fact_id}",
            basis_reference=f"semantic-fact:{fact.fact_id}",
            assertion=semantic_fact_statement(fact),
            authority_domain="ENGINEERING_SEMANTIC_TRUTH",
        )


def activity_for_response_contract(contract: ResponseContract) -> EngineeringActivity:
    return {
        InteractionMode.EXPLORE: EngineeringActivity.DISCOVERY,
        InteractionMode.ANALYZE: EngineeringActivity.DISCOVERY,
        InteractionMode.DESIGN: EngineeringActivity.ARCHITECTURE_DECISION,
        InteractionMode.DECIDE: EngineeringActivity.ARCHITECTURE_DECISION,
        InteractionMode.ANSWER: EngineeringActivity.DISCOVERY,
        InteractionMode.DIAGNOSE: EngineeringActivity.INVESTIGATION,
        InteractionMode.EXECUTE: EngineeringActivity.FEATURE_DELIVERY,
        InteractionMode.CORRECT: EngineeringActivity.DISCOVERY,
        InteractionMode.STATUS: EngineeringActivity.INVESTIGATION,
    }[contract.interaction_mode]


def budget_for_response_contract(contract: ResponseContract) -> ContextBudget:
    return {
        InformationBudget.MINIMAL_ACKNOWLEDGEMENT: ContextBudget(
            max_items=6, max_characters=2000, max_items_per_source=3
        ),
        InformationBudget.MINIMUM_SUFFICIENT: ContextBudget(
            max_items=8, max_characters=3000, max_items_per_source=4
        ),
        InformationBudget.CONCISE_REALITY: ContextBudget(
            max_items=8, max_characters=3500, max_items_per_source=4
        ),
        InformationBudget.CORRECTION_AND_CONTINUE: ContextBudget(
            max_items=10, max_characters=4000, max_items_per_source=5
        ),
        InformationBudget.FOCUSED_DIAGNOSIS: ContextBudget(
            max_items=12, max_characters=6000, max_items_per_source=5
        ),
        InformationBudget.DECISIVE_FACTORS: ContextBudget(
            max_items=12, max_characters=6500, max_items_per_source=5
        ),
        InformationBudget.REASONED_TRADEOFFS: ContextBudget(
            max_items=16, max_characters=9000, max_items_per_source=6
        ),
        InformationBudget.RELEVANT_DIVERGENCE: ContextBudget(
            max_items=18, max_characters=10000, max_items_per_source=7
        ),
    }[contract.information_budget]


@lru_cache(maxsize=1)
def default_system_capability_reality() -> SystemCapabilityReality:
    """Repository-owned self-capability truth, not marketing or personality."""

    return SystemCapabilityReality(
        version="1",
        capabilities=(
            "Understand Human goals, constraints, corrections, and governed meaning.",
            "Reason about software products, architecture, engineering trade-offs, and repositories.",
            "Create and modify software artifacts through governed production work.",
            "Execute bounded engineering tasks and manage their production workflow.",
            "Verify produced results and consume attributable Guardian assurance evidence.",
            "Preserve Work Reality, engineering facts, decisions, and evidence lineage.",
        ),
        production_object_types=(
            DesignObjectType.PRODUCT_SYSTEM,
            DesignObjectType.FEATURE,
        ),
        boundaries=(
            "External account, platform-submission, deployment, or publication actions require actual integration and authority.",
            "Watt must not claim an external or production effect without attributable runtime evidence.",
            "Capability guidance cannot admit Work, override Human authority, or replace Human Acceptance.",
        ),
        provenance=(
            "docs/architecture/watt-ai-native-software-production-architecture.md",
            "docs/architecture/wic-context-orchestration.md",
        ),
    )


def system_capability_context_candidate(*, required: bool = False) -> ContextCandidate:
    reality = default_system_capability_reality()
    return ContextCandidate(
        candidate_id=f"system-capability-reality:{reality.version}",
        source=ContextSource.SYSTEM_CAPABILITY_REALITY,
        content=(
            f"Identity: {reality.identity}; type: AI-native software production system. "
            "Capabilities: " + " ".join(reality.capabilities) + " Boundaries: "
            + " ".join(reality.boundaries)
        ),
        source_reference=f"system-capability-reality:{reality.version}",
        authority=reality.authority,
        provenance=reality.provenance,
        priority=92,
        authoritative=True,
        required=required,
    )


def is_system_capability_question(value: str) -> bool:
    normalized = " ".join(value.casefold().split())
    return any(
        signal in normalized
        for signal in (
            "你是谁",
            "你是什么",
            "你能做什么",
            "你会做什么",
            "你的能力",
            "who are you",
            "what are you",
            "what can you do",
            "your capabilities",
        )
    )


@lru_cache(maxsize=1)
def default_context_orchestrator() -> ContextOrchestrator:
    return ContextOrchestrator(
        EngineeringPatternCatalog(_default_patterns()),
        SoftwareProductionSopCatalog((_default_sop(),)),
    )


@lru_cache(maxsize=1)
def default_task_contract_builder() -> TaskContractBuilder:
    return TaskContractBuilder(default_context_orchestrator())


def _default_patterns() -> tuple[EngineeringPattern, ...]:
    all_activities = tuple(EngineeringActivity)
    return (
        EngineeringPattern(
            pattern_id="governed-meaning-preservation",
            version="1",
            title="Governed Meaning Preservation",
            decision_space=(
                "Keep product meaning distinct from implementation representation"
            ),
            activation=PatternActivationMetadata(
                activities=all_activities,
                requires_semantic_truth=True,
            ),
            dimensions=(
                PatternDimension(
                    key="meaning-to-implementation",
                    consideration=(
                        "How will the implementation satisfy governed product meaning "
                        "without substituting a convenient structural interpretation?"
                    ),
                    options=(
                        PatternOption(
                            key="direct-projection",
                            description="Project governed facts directly into the contract",
                            benefits=("Strong lineage",),
                            costs_and_risks=("Requires explicit fact references",),
                        ),
                        PatternOption(
                            key="derived-representation",
                            description=(
                                "Use a derived implementation shape while verifying the "
                                "original product semantics"
                            ),
                            benefits=("Implementation flexibility",),
                            costs_and_risks=("Needs semantic verification",),
                        ),
                    ),
                ),
            ),
            evidence_direction=(
                PatternEvidenceDirection(
                    statement="Trace each material implementation obligation to current facts.",
                    provenance_reference="architecture:engineering-semantic-truth",
                ),
            ),
            provenance_references=(
                "docs/architecture/engineering-semantic-truth.md",
                "docs/architecture/wic-software-domain-grounding.md",
            ),
        ),
        EngineeringPattern(
            pattern_id="bounded-change-and-evidence",
            version="1",
            title="Bounded Change and Evidence",
            decision_space="Balance delivery scope with attributable verification evidence",
            activation=PatternActivationMetadata(
                activities=(
                    EngineeringActivity.FEATURE_DELIVERY,
                    EngineeringActivity.BUG_RESOLUTION,
                    EngineeringActivity.REFACTORING,
                    EngineeringActivity.MIGRATION,
                    EngineeringActivity.OPTIMIZATION,
                    EngineeringActivity.RELEASE,
                ),
            ),
            dimensions=(
                PatternDimension(
                    key="change-boundary",
                    consideration="What is the narrowest sufficient authorized change?",
                    options=(
                        PatternOption(
                            key="exact-targets",
                            description="Use exact artifact targets where known",
                            benefits=("High auditability",),
                            costs_and_risks=("May require re-steering if incomplete",),
                        ),
                        PatternOption(
                            key="bounded-area",
                            description="Use a bounded area when exact targets are not known",
                            benefits=("Allows local engineering judgment",),
                            costs_and_risks=("Wider review surface",),
                        ),
                    ),
                ),
            ),
            evidence_direction=(
                PatternEvidenceDirection(
                    statement="Bind evidence to exact source and produced subjects.",
                    provenance_reference="architecture:watt-decision-evidence",
                ),
            ),
            provenance_references=(
                "docs/architecture/watt-ai-native-software-production-architecture.md",
                "docs/architecture/watt-decision-evidence-architecture.md",
            ),
        ),
    )


def _default_sop() -> SoftwareProductionSop:
    activities: list[SopActivityGuidance] = []
    for activity in EngineeringActivity:
        activity_name = activity.value.replace("_", " ").title()
        activities.append(
            SopActivityGuidance(
                activity=activity,
                applicability=f"Use for governed {activity_name} engineering activity",
                checkpoints=(
                    SopCheckpoint(
                        checkpoint_id=f"{activity.value.lower().replace('_', '-')}-basis",
                        purpose="Confirm the current source and authority basis is attributable",
                        evidence_expectations=(
                            EvidenceExpectation(
                                expectation_id=(
                                    f"{activity.value.lower().replace('_', '-')}-basis-evidence"
                                ),
                                category=EvidenceCategory.ENGINEERING,
                                statement=(
                                    "Current Work, source, scope, and decision lineage are "
                                    "identifiable before acting."
                                ),
                                owner_boundary="Work/ECF/Steering retain their own authority.",
                            ),
                        ),
                    ),
                    SopCheckpoint(
                        checkpoint_id=f"{activity.value.lower().replace('_', '-')}-outcome",
                        purpose="Require attributable evidence for the claimed outcome",
                        evidence_expectations=(
                            EvidenceExpectation(
                                expectation_id=(
                                    f"{activity.value.lower().replace('_', '-')}-outcome-evidence"
                                ),
                                category=EvidenceCategory.ASSURANCE,
                                statement=(
                                    "Outcome claims are evaluated against the admitted "
                                    "acceptance meaning and exact produced subject."
                                ),
                                owner_boundary="Guardian/Verification owns assurance results.",
                            ),
                        ),
                    ),
                ),
            )
        )
    return SoftwareProductionSop(
        sop_id="watt-software-production",
        version="1",
        title="Watt Software Production SOP Foundation",
        activities=tuple(activities),
    )


def _fingerprint(value: object) -> str:
    canonical = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return sha256(canonical).hexdigest()
