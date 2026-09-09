"""Reconstructable guided design agenda integrated with existing Plan Steering."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.steering import SteeringApplicationService
from spg.domain.design_intent import DesignIntentFrame, DesignObjectType
from spg.domain.guided_design import (
    DesignAgendaRevisionCondition,
    DesignAgendaRevisionRecord,
    DesignAuthorityRelevance,
    DesignIssue,
    DesignIssueState,
    DesignOutputClass,
    DesignProcessCondition,
    DesignReadiness,
    DesignReadinessState,
    DesignFacilitationStrategy,
    DesignSchemaDefinition,
    GuidedDesignInvariantViolation,
    GuidedDesignProjection,
)
from spg.domain.product import WorkMode, WorkRecord
from spg.domain.steering import (
    RealityReference,
    RealityReferenceKind,
    ReviseSteeringPlanRequest,
    SemanticStepResultRecord,
    SteeringPlanReconstruction,
    SteeringStepSpec,
    SteeringStepState,
    SteeringStepType,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.guided_design_store import GuidedDesignStore
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.steering_store import SteeringStore


GENERAL_SCHEMA_IDENTITY = "watt:guided-design:general-product-system"
GENERAL_SCHEMA_VERSION = "0.1"
TECHNICAL_SCHEMA_IDENTITY = "watt:guided-design:technical-system"
TECHNICAL_SCHEMA_VERSION = "0.1"
EVOLUTION_SCHEMA_IDENTITY = "watt:guided-design:existing-product-evolution"
EVOLUTION_SCHEMA_VERSION = "0.1"


def general_product_system_design_issues() -> tuple[DesignIssue, ...]:
    """Small, extensible design basis; applicability is reassessed, not a waterfall."""

    return (
        DesignIssue(
            key="motive-users-problem",
            title="Motive, users, and problem",
            objective="Clarify why this product or system should exist and for whom.",
            why_it_matters="A solution direction is unsafe until the beneficiary and problem are explicit.",
            applicability="Applicable to every product or system design Work.",
            completion_condition="Governed Reality identifies the Motive, target actors, and problem boundary.",
            authority_relevance=DesignAuthorityRelevance.MATERIAL_HUMAN_DECISION,
            required_output=DesignOutputClass.SHARED_UNDERSTANDING,
        ),
        DesignIssue(
            key="outcomes-scenarios",
            title="Outcomes and key scenarios",
            objective="Establish desired user value and the key journeys that must work.",
            why_it_matters="Outcomes and scenarios make the design testable without prescribing implementation.",
            applicability="Applicable when the Work intends a user-visible or operational change.",
            prerequisite_keys=("motive-users-problem",),
            completion_condition="Governed Reality describes meaningful outcomes and representative scenarios.",
            authority_relevance=DesignAuthorityRelevance.ROUTINE,
            required_output=DesignOutputClass.GOVERNED_DESIGN_DIRECTION,
        ),
        DesignIssue(
            key="boundary-non-goals",
            title="Boundary and non-goals",
            objective="Bound the product/system responsibility and state explicit non-goals.",
            why_it_matters="A clear boundary prevents silent scope and Authority expansion.",
            applicability="Applicable before material solution or production commitments.",
            prerequisite_keys=("motive-users-problem",),
            completion_condition="Governed Reality distinguishes in-scope outcomes from explicit non-goals.",
            authority_relevance=DesignAuthorityRelevance.AUTHORITY_BOUNDARY,
            required_output=DesignOutputClass.GOVERNED_HUMAN_DECISION,
        ),
        DesignIssue(
            key="capabilities-workflow",
            title="Capabilities and lifecycle",
            objective="Shape the minimum capability model and end-to-end operating lifecycle.",
            why_it_matters="Capabilities and lifecycle connect user value to coherent system behavior.",
            applicability="Applicable after the problem and boundary are sufficiently understood.",
            prerequisite_keys=("outcomes-scenarios", "boundary-non-goals"),
            completion_condition="Governed Reality identifies the essential capabilities and lifecycle transitions.",
            authority_relevance=DesignAuthorityRelevance.ROUTINE,
            required_output=DesignOutputClass.GOVERNED_DESIGN_DIRECTION,
        ),
        DesignIssue(
            key="responsibility-information-interaction",
            title="Responsibility, information, and interaction",
            objective="Clarify Human/system responsibility, important concepts, and interaction model.",
            why_it_matters="The operating model must expose who decides and how information flows.",
            applicability="Applicable where people, automation, or durable information interact.",
            prerequisite_keys=("capabilities-workflow",),
            completion_condition="Governed Reality assigns responsibilities and describes the core information/interaction model.",
            authority_relevance=DesignAuthorityRelevance.MATERIAL_HUMAN_DECISION,
            required_output=DesignOutputClass.GOVERNED_DESIGN_DIRECTION,
        ),
        DesignIssue(
            key="architecture-risk-assumptions",
            title="Architecture implications, risks, and assumptions",
            objective="Identify architecture implications, constraints, material risks, and unresolved assumptions.",
            why_it_matters="Production must not silently depend on unexamined architectural or risk assumptions.",
            applicability="Applicable once the capability and responsibility model is coherent.",
            prerequisite_keys=("capabilities-workflow",),
            completion_condition="Critical implications, risks, and assumptions are governed or explicitly escalated.",
            authority_relevance=DesignAuthorityRelevance.MATERIAL_HUMAN_DECISION,
            required_output=DesignOutputClass.GOVERNED_DESIGN_DIRECTION,
        ),
        DesignIssue(
            key="verification-staged-readiness",
            title="Verification, staged scope, and implementation readiness",
            objective="Form a reviewable bounded next-stage production proposal and acceptance basis.",
            why_it_matters="Design readiness must become a reviewable proposal before production Authority transfers.",
            applicability="Applicable only after critical design questions are sufficiently resolved.",
            prerequisite_keys=(
                "outcomes-scenarios",
                "boundary-non-goals",
                "capabilities-workflow",
                "architecture-risk-assumptions",
            ),
            completion_condition="A governed, bounded, verifiable production proposal is available for review.",
            authority_relevance=DesignAuthorityRelevance.AUTHORITY_BOUNDARY,
            required_output=DesignOutputClass.REVIEWABLE_PRODUCTION_PROPOSAL,
        ),
    )


def technical_system_design_issues() -> tuple[DesignIssue, ...]:
    """Seed technical-system methodology without prescribing implementation."""

    stages = (
        ("requirements", "Requirements", "Establish functional and operational requirements.", (), DesignOutputClass.SHARED_UNDERSTANDING),
        ("constraints", "Constraints", "Make technical, organizational, and authority constraints explicit.", ("requirements",), DesignOutputClass.GOVERNED_HUMAN_DECISION),
        ("scale-performance", "Scale and performance", "Define relevant scale, latency, capacity, and reliability expectations.", ("requirements",), DesignOutputClass.GOVERNED_DESIGN_DIRECTION),
        ("data-model", "Data model", "Define the information semantics and ownership boundaries.", ("requirements", "constraints"), DesignOutputClass.GOVERNED_DESIGN_DIRECTION),
        ("architecture-options", "Architecture options", "Compare viable architecture shapes and their trade-offs.", ("constraints", "scale-performance", "data-model"), DesignOutputClass.GOVERNED_HUMAN_DECISION),
        ("failure-modes", "Failure modes", "Identify material failures, recovery boundaries, and operational risks.", ("architecture-options",), DesignOutputClass.GOVERNED_DESIGN_DIRECTION),
        ("verification-strategy", "Verification strategy", "Define how the intended behavior and constraints will be proven.", ("architecture-options", "failure-modes"), DesignOutputClass.GOVERNED_DESIGN_DIRECTION),
        ("implementation-readiness", "Implementation readiness", "Form a bounded, reviewable implementation proposal.", ("verification-strategy",), DesignOutputClass.REVIEWABLE_PRODUCTION_PROPOSAL),
    )
    return tuple(
        DesignIssue(
            key=key,
            title=title,
            objective=objective,
            why_it_matters=f"{title} must be explicit before downstream technical commitments are safe.",
            applicability="Applicable to technical systems, infrastructure, and architecture design.",
            prerequisite_keys=prerequisites,
            completion_condition=f"Governed Reality satisfies the {title.lower()} design basis.",
            authority_relevance=(
                DesignAuthorityRelevance.MATERIAL_HUMAN_DECISION
                if output is DesignOutputClass.GOVERNED_HUMAN_DECISION
                else DesignAuthorityRelevance.ROUTINE
            ),
            required_output=output,
        )
        for key, title, objective, prerequisites, output in stages
    )


def existing_product_evolution_design_issues() -> tuple[DesignIssue, ...]:
    """Seed methodology for governed evolution of an existing product/system."""

    stages = (
        ("current-reality", "Current Reality", "Establish the trusted current product and runtime reality.", (), DesignOutputClass.SHARED_UNDERSTANDING),
        ("user-feedback", "User feedback", "Connect observed user feedback to the current Reality.", ("current-reality",), DesignOutputClass.SHARED_UNDERSTANDING),
        ("problem-prioritization", "Problem prioritization", "Prioritize the problems worth changing and explain why.", ("user-feedback",), DesignOutputClass.GOVERNED_HUMAN_DECISION),
        ("solution-options", "Solution options", "Compare bounded ways to address the prioritized problem.", ("problem-prioritization",), DesignOutputClass.GOVERNED_DESIGN_DIRECTION),
        ("impact-assessment", "Impact assessment", "Assess product, architecture, migration, and risk impact.", ("solution-options",), DesignOutputClass.GOVERNED_DESIGN_DIRECTION),
        ("validation", "Validation", "Define evidence required to validate the proposed evolution.", ("impact-assessment",), DesignOutputClass.GOVERNED_DESIGN_DIRECTION),
        ("evolution-plan", "Evolution plan", "Form a bounded and reviewable next evolution proposal.", ("validation",), DesignOutputClass.REVIEWABLE_PRODUCTION_PROPOSAL),
    )
    return tuple(
        DesignIssue(
            key=key,
            title=title,
            objective=objective,
            why_it_matters=f"{title} prevents an existing product from evolving on unsupported assumptions.",
            applicability="Applicable to optimization or evolution of an existing product/system.",
            prerequisite_keys=prerequisites,
            completion_condition=f"Governed Reality satisfies the {title.lower()} evolution basis.",
            authority_relevance=(
                DesignAuthorityRelevance.MATERIAL_HUMAN_DECISION
                if output is DesignOutputClass.GOVERNED_HUMAN_DECISION
                else DesignAuthorityRelevance.ROUTINE
            ),
            required_output=output,
        )
        for key, title, objective, prerequisites, output in stages
    )


def design_schema_registry() -> tuple[DesignSchemaDefinition, ...]:
    """Built-in, versioned seed registry; no user workflow/schema editor is implied."""

    return (
        DesignSchemaDefinition(
            identity=GENERAL_SCHEMA_IDENTITY,
            version=GENERAL_SCHEMA_VERSION,
            title="General Product/System Design",
            applicability="New products, platforms, and internal systems.",
            issues=general_product_system_design_issues(),
        ),
        DesignSchemaDefinition(
            identity=TECHNICAL_SCHEMA_IDENTITY,
            version=TECHNICAL_SCHEMA_VERSION,
            title="Technical System Design",
            applicability="Technical systems, infrastructure, and architecture design.",
            issues=technical_system_design_issues(),
        ),
        DesignSchemaDefinition(
            identity=EVOLUTION_SCHEMA_IDENTITY,
            version=EVOLUTION_SCHEMA_VERSION,
            title="Existing Product Evolution",
            applicability="Optimization and evolution of existing products or systems.",
            issues=existing_product_evolution_design_issues(),
        ),
    )


def design_schema_by_identity(
    identity: str,
    version: str | None = None,
) -> DesignSchemaDefinition:
    for schema in design_schema_registry():
        if schema.identity == identity and (version is None or schema.version == version):
            return schema
    requested_version = version if version is not None else "(any version)"
    raise GuidedDesignInvariantViolation(
        f"Unknown built-in Design Schema: {identity} {requested_version}"
    )


def match_design_schema_text(text: str) -> tuple[DesignSchemaDefinition, str]:
    """Select a seed methodology from explicit Motive wording, conservatively."""

    normalized = " ".join(text.casefold().split())
    evolution_markers = (
        "existing product", "existing system", "current product", "current system",
        "已有", "现有", "当前产品", "当前系统",
    )
    technical_markers = (
        "technical", "architecture", "infrastructure", "database", "performance",
        "技术", "架构", "基础设施", "数据库", "性能",
    )
    registry = {item.identity: item for item in design_schema_registry()}
    if any(marker in normalized for marker in evolution_markers):
        schema = registry[EVOLUTION_SCHEMA_IDENTITY]
        reason = "The Motive explicitly concerns an existing product/system and its evolution."
    elif any(marker in normalized for marker in technical_markers):
        schema = registry[TECHNICAL_SCHEMA_IDENTITY]
        reason = "The Motive is primarily a technical-system or architecture design problem."
    else:
        schema = registry[GENERAL_SCHEMA_IDENTITY]
        reason = "The Motive appears to describe a new product, platform, or internal software system."
    return schema, reason


def match_design_schema_frame(
    frame: DesignIntentFrame,
) -> tuple[DesignSchemaDefinition | None, str]:
    """Route only an explicit framed object into an applicable seed schema."""

    registry = {item.identity: item for item in design_schema_registry()}
    # Methodology follows the design object, not technical vocabulary in its context.
    normalized = " ".join(frame.design_subject.casefold().split())
    if frame.object_type is DesignObjectType.FEATURE:
        return (
            registry[EVOLUTION_SCHEMA_IDENTITY],
            "The Design Intent Frame identifies a feature/capability evolution of an existing system.",
        )
    if frame.object_type is DesignObjectType.PRODUCT_SYSTEM:
        technical_markers = (
            "technical",
            "architecture",
            "infrastructure",
            "database",
            "performance",
            "技术",
            "架构",
            "基础设施",
            "数据库",
            "性能",
        )
        if any(marker in normalized for marker in technical_markers):
            return (
                registry[TECHNICAL_SCHEMA_IDENTITY],
                "The framed design subject is a technical system or architecture concern.",
            )
        return (
            registry[GENERAL_SCHEMA_IDENTITY],
            "The Design Intent Frame identifies a product, platform, or software system.",
        )
    return (
        None,
        "The framed object is outside the current product/system seed schemas or remains ambiguous; Guided Design selection is deferred.",
    )


def design_schema_for_work(work: WorkRecord) -> tuple[DesignSchemaDefinition, str]:
    return match_design_schema_text(
        " ".join(
            value
            for value in (work.raw_user_requirement, work.desired_outcome or "")
            if value
        )
    )


def guided_design_step_specs(
    issues: tuple[DesignIssue, ...],
) -> tuple[SteeringStepSpec, ...]:
    active = tuple(
        issue
        for issue in issues
        if issue.state in {DesignIssueState.OPEN, DesignIssueState.REOPENED}
    )
    steps = tuple(
        SteeringStepSpec(
            type=SteeringStepType.DESIGN,
            objective=issue.objective,
            completion_condition=issue.completion_condition,
            state=(
                SteeringStepState.CURRENT
                if index == 0
                else SteeringStepState.KNOWN
            ),
            design_issue_key=issue.key,
        )
        for index, issue in enumerate(active)
    )
    return (
        *steps,
        SteeringStepSpec(
            type=SteeringStepType.PRODUCE,
            objective="Produce the next exact change admitted from current design Reality",
            completion_condition="The exact bounded production cycle reaches trusted Runtime Commit",
        ),
        SteeringStepSpec(
            type=SteeringStepType.VERIFY_ACCEPT,
            objective="Assess trusted production evidence against the design and Work outcome",
            completion_condition="Governed evidence supports product acceptance or design reassessment",
        ),
        SteeringStepSpec(
            type=SteeringStepType.COMPLETE,
            objective="Complete the admitted long-lived Work",
            completion_condition="The admitted Work outcome is truthfully satisfied",
        ),
    )


class GuidedDesignApplicationService:
    """Own design-process semantics while leaving current focus to Plan Steering."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.steering = SteeringApplicationService(database)

    @staticmethod
    def eligible(work: WorkRecord) -> bool:
        return bool(
            work.mode is WorkMode.LONG_LIVED_STEERING
            and work.current_work_reality_revision_id is not None
            and work.production_plan is None
        )

    def bootstrap(
        self,
        work: WorkRecord,
        reconstruction: SteeringPlanReconstruction,
    ) -> GuidedDesignProjection | None:
        if not self.eligible(work):
            return None
        existing = self.get_optional(work.id)
        if existing is not None:
            return existing
        timestamp = datetime.now(UTC)
        process_id = uuid5(NAMESPACE_URL, f"spg:guided-design:{work.id}")
        agenda_id = uuid5(NAMESPACE_URL, f"spg:guided-design-agenda:1:{work.id}")
        work_ref = RealityReference(
            kind=RealityReferenceKind.WORK_REALITY_REVISION,
            identity=work.current_work_reality_revision_id,
        )
        plan_ref = RealityReference(
            kind=RealityReferenceKind.WORK,
            identity=work.id,
        )
        schema, selection_rationale = design_schema_for_work(work)
        steps_by_key = {
            step.design_issue_key: step.id
            for step in reconstruction.active_revision.steps
            if step.design_issue_key is not None
        }
        issues = tuple(
            issue.model_copy(update={"steering_step_id": steps_by_key.get(issue.key)})
            for issue in schema.issues
        )
        if any(issue.steering_step_id is None for issue in issues):
            raise GuidedDesignInvariantViolation(
                "Initial guided design agenda is not represented by Plan Steering Steps"
            )
        with self.database.unit_of_work() as unit_of_work:
            store = GuidedDesignStore(unit_of_work.session)
            if store.process_for_work(work.id) is not None:
                unit_of_work.rollback()
                return self.get(work.id)
            store.insert_process(
                {
                    "id": process_id,
                    "work_id": work.id,
                    "schema_identity": schema.identity,
                    "schema_version": schema.version,
                    "schema_selection_rationale": selection_rationale,
                    "objective": work.desired_outcome or work.raw_user_requirement,
                    "condition": DesignProcessCondition.ACTIVE.value,
                    "basis_work_reality_revision_id": work.current_work_reality_revision_id,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )
            store.insert_revision(
                {
                    "id": agenda_id,
                    "process_id": process_id,
                    "work_id": work.id,
                    "revision_number": 1,
                    "condition": DesignAgendaRevisionCondition.ACTIVE.value,
                    "supersedes_revision_id": None,
                    "basis_work_reality_revision_id": work.current_work_reality_revision_id,
                    "rationale": f"Initial {schema.title} basis selected. {selection_rationale}",
                    "reality_refs": [
                        item.model_dump(mode="json") for item in (work_ref, plan_ref)
                    ],
                    "issues": [item.model_dump(mode="json") for item in issues],
                    "created_at": timestamp,
                }
            )
            unit_of_work.commit()
        return self.get(work.id)

    def record_semantic_result(
        self,
        work_id: UUID,
        result: SemanticStepResultRecord,
    ) -> GuidedDesignProjection | None:
        projection = self.get_optional(work_id)
        if projection is None:
            return None
        issue = next(
            (item for item in projection.issues if item.steering_step_id == result.step_id),
            None,
        )
        if issue is None:
            raise GuidedDesignInvariantViolation(
                "Governed semantic result is not linked to the active design agenda"
            )
        satisfied = bool(
            result.completion_satisfied
            and (
                issue.required_output
                is not DesignOutputClass.REVIEWABLE_PRODUCTION_PROPOSAL
                or result.proposed_production is not None
            )
        )
        if not satisfied or (
            issue.state is DesignIssueState.SATISFIED
            and issue.admitted_semantic_result_id == result.id
        ):
            return projection
        result_ref = RealityReference(
            kind=RealityReferenceKind.SEMANTIC_RESULT,
            identity=result.id,
        )
        issues = tuple(
            item.model_copy(
                update={
                    "state": DesignIssueState.SATISFIED,
                    "admitted_semantic_result_id": result.id,
                    "reopen_rationale": None,
                    "provenance_refs": tuple(
                        dict.fromkeys((*item.provenance_refs, result_ref))
                    ),
                }
            )
            if item.key == issue.key
            else item
            for item in projection.issues
        )
        return self._append_revision(
            work_id,
            issues,
            rationale=f"Governed semantic result satisfied design issue {issue.key}.",
            reality_refs=(result_ref,),
        )

    def revise_agenda(
        self,
        work_id: UUID,
        issues: tuple[DesignIssue, ...],
        *,
        rationale: str,
        reality_refs: tuple[RealityReference, ...],
        revise_steering: bool = True,
    ) -> GuidedDesignProjection:
        current = self.get(work_id)
        candidate = DesignAgendaRevisionRecord(
            id=uuid4(),
            process_id=current.process_id,
            work_id=work_id,
            revision_number=current.agenda_revision_number + 1,
            condition=DesignAgendaRevisionCondition.ACTIVE,
            supersedes_revision_id=current.agenda_revision_id,
            basis_work_reality_revision_id=self._current_work_revision_id(work_id),
            rationale=rationale,
            reality_refs=reality_refs,
            issues=issues,
            created_at=datetime.now(UTC),
        )
        del candidate
        projection = self._append_revision(
            work_id,
            issues,
            rationale=rationale,
            reality_refs=reality_refs,
        )
        if revise_steering:
            reconstruction = self.steering.reconstruct(work_id)
            refs = tuple(
                dict.fromkeys(
                    (
                        *reality_refs,
                        RealityReference(
                            kind=RealityReferenceKind.DESIGN_AGENDA_REVISION,
                            identity=projection.agenda_revision_id,
                        ),
                    )
                )
            )
            self.steering.revise_plan(
                ReviseSteeringPlanRequest(
                    steering_plan_id=reconstruction.steering_plan_id,
                    superseded_revision_id=reconstruction.active_revision.revision.id,
                    rationale=rationale,
                    reality_refs=refs,
                    steps=guided_design_step_specs(issues),
                )
            )
            self._bind_active_steps(work_id)
            projection = self.get(work_id)
        return projection

    def skip_issue(
        self,
        work_id: UUID,
        issue_key: str,
        *,
        rationale: str,
        reality_refs: tuple[RealityReference, ...],
    ) -> GuidedDesignProjection:
        current = self.get(work_id)
        issues = tuple(
            item.model_copy(
                update={
                    "state": DesignIssueState.SKIPPED,
                    "skip_rationale": rationale,
                    "reopen_rationale": None,
                    "steering_step_id": None,
                    "provenance_refs": tuple(
                        dict.fromkeys((*item.provenance_refs, *reality_refs))
                    ),
                }
            )
            if item.key == issue_key
            else item
            for item in current.issues
        )
        if issues == current.issues:
            raise GuidedDesignInvariantViolation(f"Design issue not found: {issue_key}")
        return self.revise_agenda(
            work_id,
            issues,
            rationale=rationale,
            reality_refs=reality_refs,
        )

    def reopen_issue(
        self,
        work_id: UUID,
        issue_key: str,
        *,
        rationale: str,
        reality_refs: tuple[RealityReference, ...],
    ) -> GuidedDesignProjection:
        current = self.get(work_id)
        issues = tuple(
            item.model_copy(
                update={
                    "state": DesignIssueState.REOPENED,
                    "skip_rationale": None,
                    "reopen_rationale": rationale,
                    "steering_step_id": None,
                    "admitted_semantic_result_id": None,
                    "provenance_refs": tuple(
                        dict.fromkeys((*item.provenance_refs, *reality_refs))
                    ),
                }
            )
            if item.key == issue_key
            else item
            for item in current.issues
        )
        if issues == current.issues:
            raise GuidedDesignInvariantViolation(f"Design issue not found: {issue_key}")
        return self.revise_agenda(
            work_id,
            issues,
            rationale=rationale,
            reality_refs=reality_refs,
        )

    def semantic_context(self, work_id: UUID, step_id: UUID) -> dict[str, object] | None:
        projection = self.get_optional(work_id)
        if projection is None:
            return None
        issue = next(
            (item for item in projection.issues if item.steering_step_id == step_id),
            None,
        )
        if issue is None:
            return None
        admitted_results: list[dict[str, object]] = []
        with self.database.unit_of_work() as unit_of_work:
            steering = SteeringStore(unit_of_work.session)
            for agenda_issue in projection.issues:
                result_id = agenda_issue.admitted_semantic_result_id
                if result_id is None:
                    continue
                result = steering.semantic_result(result_id)
                if result is None:
                    raise GuidedDesignInvariantViolation(
                        "A satisfied design issue lost its governed semantic result"
                    )
                admitted_results.append(
                    {
                        "issue_key": agenda_issue.key,
                        "result_id": str(result.id),
                        "result_kind": result.result_kind.value,
                        "bounded_summary": result.bounded_summary,
                        "decisions": list(result.decisions),
                        "derived_constraints": list(result.derived_constraints),
                        "evidence_refs": [
                            reference.model_dump(mode="json")
                            for reference in result.evidence_refs
                        ],
                    }
                )
        return {
            "schema_identity": projection.schema_identity,
            "schema_version": projection.schema_version,
            "process_objective": projection.process_objective,
            "agenda_revision_id": str(projection.agenda_revision_id),
            "agenda_revision_number": projection.agenda_revision_number,
            "current_issue": issue.model_dump(mode="json"),
            "resolved_issues": [
                item.key
                for item in projection.issues
                if item.state is DesignIssueState.SATISFIED
            ],
            "admitted_results": admitted_results,
            "open_issues": [
                item.key
                for item in projection.issues
                if item.state in {DesignIssueState.OPEN, DesignIssueState.REOPENED}
            ],
            "readiness": projection.readiness.model_dump(mode="json"),
            "production_transition_issue": (
                issue.required_output
                is DesignOutputClass.REVIEWABLE_PRODUCTION_PROPOSAL
            ),
        }

    def get_optional(self, work_id: UUID) -> GuidedDesignProjection | None:
        with self.database.unit_of_work() as unit_of_work:
            store = GuidedDesignStore(unit_of_work.session)
            process = store.process_for_work(work_id)
            if process is None:
                return None
            agenda = store.active_revision(process.id)
            if agenda is None:
                raise GuidedDesignInvariantViolation(
                    "Guided design process has no active agenda revision"
                )
            steering = SteeringStore(unit_of_work.session)
            plan = steering.plan_for_work(work_id)
            current_step = None
            latest_decision = None
            if plan is not None:
                revision = steering.active_revision(plan.id)
                if revision is not None:
                    current_step = next(
                        (
                            step
                            for step in steering.steps(revision.id)
                            if step.state is SteeringStepState.CURRENT
                        ),
                        None,
                    )
                    latest_decision = steering.latest_decision(revision.id)
        current_focus = next(
            (
                issue
                for issue in agenda.issues
                if current_step is not None
                and issue.key == current_step.design_issue_key
            ),
            None,
        )
        readiness = self._readiness(agenda)
        resolved = sum(
            issue.state in {DesignIssueState.SATISFIED, DesignIssueState.SKIPPED}
            for issue in agenda.issues
        )
        completed_areas = tuple(
            issue.title
            for issue in agenda.issues
            if issue.state in {DesignIssueState.SATISFIED, DesignIssueState.SKIPPED}
        )
        unresolved_areas = tuple(
            issue.title
            for issue in agenda.issues
            if issue.state in {DesignIssueState.OPEN, DesignIssueState.REOPENED}
        )
        satisfied_keys = {
            issue.key
            for issue in agenda.issues
            if issue.state in {DesignIssueState.SATISFIED, DesignIssueState.SKIPPED}
        }
        dependency_blockers = (
            ()
            if current_focus is None
            else tuple(
                key
                for key in current_focus.prerequisite_keys
                if key not in satisfied_keys
            )
        )
        strategy, guidance = self._facilitation(current_focus, dependency_blockers)
        stage = "Production readiness" if current_focus is None else current_focus.title
        progress_narrative = (
            f"Current stage: {stage}. {resolved} of {len(agenda.issues)} design areas "
            f"are resolved; {len(unresolved_areas)} remain. "
            + (
                "The design basis is ready for a governed production proposal review."
                if readiness.state is DesignReadinessState.READY
                else (
                    f"Next focus: {current_focus.title}. {current_focus.why_it_matters}"
                    if current_focus is not None
                    else "Plan Steering has not selected a current design issue."
                )
            )
        )
        return GuidedDesignProjection(
            work_id=work_id,
            process_id=process.id,
            process_objective=process.objective,
            schema_identity=process.schema_identity,
            schema_version=process.schema_version,
            schema_selection_rationale=process.schema_selection_rationale,
            agenda_revision_id=agenda.id,
            agenda_revision_number=agenda.revision_number,
            current_focus_key=None if current_focus is None else current_focus.key,
            current_focus=current_focus,
            focus_rationale=(
                agenda.rationale
                if latest_decision is None
                else latest_decision.reason
            ),
            current_stage=stage,
            completed_areas=completed_areas,
            unresolved_areas=unresolved_areas,
            dependency_blockers=dependency_blockers,
            facilitation_strategy=strategy,
            facilitation_guidance=guidance,
            progress_narrative=progress_narrative,
            issues=agenda.issues,
            resolved_count=resolved,
            total_applicable_count=len(agenda.issues),
            readiness=readiness,
            upcoming_transition=(
                "Review the governed production proposal before production admission"
                if readiness.state is DesignReadinessState.READY
                else "Resolve the next critical design issue selected by Plan Steering"
            ),
        )

    @staticmethod
    def _facilitation(
        current_focus: DesignIssue | None,
        dependency_blockers: tuple[str, ...],
    ) -> tuple[DesignFacilitationStrategy, str]:
        if current_focus is None:
            return (
                DesignFacilitationStrategy.PROPOSE_NEXT_DESIGN_STEP,
                "Summarize the completed design basis and propose the governed production review.",
            )
        if dependency_blockers:
            return (
                DesignFacilitationStrategy.SUMMARIZE_UNDERSTANDING,
                "Reconstruct the prerequisite decisions before continuing this design issue.",
            )
        if current_focus.key in {"architecture-options", "solution-options"}:
            return (
                DesignFacilitationStrategy.PRESENT_ALTERNATIVES,
                "Present bounded alternatives and compare their material trade-offs.",
            )
        if current_focus.authority_relevance is DesignAuthorityRelevance.AUTHORITY_BOUNDARY:
            return (
                DesignFacilitationStrategy.REQUEST_HUMAN_DECISION,
                "Explain the boundary and request the Human decision needed to govern it.",
            )
        if current_focus.authority_relevance is DesignAuthorityRelevance.MATERIAL_HUMAN_DECISION:
            return (
                DesignFacilitationStrategy.EXPLAIN_TRADE_OFFS,
                "Clarify the known options and trade-offs before asking for Human judgment.",
            )
        if current_focus.required_output is DesignOutputClass.SHARED_UNDERSTANDING:
            return (
                DesignFacilitationStrategy.CLARIFY,
                "Ask only the material clarification needed to establish shared understanding.",
            )
        return (
            DesignFacilitationStrategy.SUMMARIZE_UNDERSTANDING,
            "Summarize current understanding, then propose the next bounded design move.",
        )

    def get(self, work_id: UUID) -> GuidedDesignProjection:
        projection = self.get_optional(work_id)
        if projection is None:
            raise GuidedDesignInvariantViolation(
                f"Work has no guided design process: {work_id}"
            )
        return projection

    def _append_revision(
        self,
        work_id: UUID,
        issues: tuple[DesignIssue, ...],
        *,
        rationale: str,
        reality_refs: tuple[RealityReference, ...],
    ) -> GuidedDesignProjection:
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = GuidedDesignStore(unit_of_work.session)
            process = store.process_for_work(work_id)
            if process is None:
                raise GuidedDesignInvariantViolation("Guided design process is missing")
            active = store.active_revision(process.id)
            if active is None:
                raise GuidedDesignInvariantViolation("Active design agenda is missing")
            revision_id = uuid4()
            work_revision_id = self._current_work_revision_id(
                work_id,
                session=unit_of_work.session,
            )
            store.supersede_revision(active.id)
            store.insert_revision(
                {
                    "id": revision_id,
                    "process_id": process.id,
                    "work_id": work_id,
                    "revision_number": active.revision_number + 1,
                    "condition": DesignAgendaRevisionCondition.ACTIVE.value,
                    "supersedes_revision_id": active.id,
                    "basis_work_reality_revision_id": work_revision_id,
                    "rationale": rationale,
                    "reality_refs": [
                        item.model_dump(mode="json") for item in reality_refs
                    ],
                    "issues": [item.model_dump(mode="json") for item in issues],
                    "created_at": timestamp,
                }
            )
            readiness = self._readiness_for_issues(issues)
            store.update_process(
                process.id,
                condition=(
                    DesignProcessCondition.READY
                    if readiness.state is DesignReadinessState.READY
                    else DesignProcessCondition.ACTIVE
                ),
                basis_work_reality_revision_id=work_revision_id,
                updated_at=timestamp,
            )
            unit_of_work.commit()
        return self.get(work_id)

    def _bind_active_steps(self, work_id: UUID) -> None:
        projection = self.get(work_id)
        reconstruction = self.steering.reconstruct(work_id)
        by_key = {
            step.design_issue_key: step.id
            for step in reconstruction.active_revision.steps
            if step.design_issue_key is not None
        }
        issues = tuple(
            issue.model_copy(update={"steering_step_id": by_key.get(issue.key)})
            for issue in projection.issues
        )
        self._append_revision(
            work_id,
            issues,
            rationale="Bind the revised design agenda to the exact active Plan Steering revision.",
            reality_refs=(
                RealityReference(
                    kind=RealityReferenceKind.DESIGN_AGENDA_REVISION,
                    identity=projection.agenda_revision_id,
                ),
            ),
        )

    def _current_work_revision_id(self, work_id: UUID, *, session=None) -> UUID | None:
        if session is not None:
            work = ProductStore(session).work(work_id)
            return None if work is None else work.current_work_reality_revision_id
        with self.database.unit_of_work() as unit_of_work:
            work = ProductStore(unit_of_work.session).work(work_id)
            return None if work is None else work.current_work_reality_revision_id

    @staticmethod
    def _readiness(agenda: DesignAgendaRevisionRecord) -> DesignReadiness:
        return GuidedDesignApplicationService._readiness_for_issues(
            agenda.issues,
            agenda_ref=RealityReference(
                kind=RealityReferenceKind.DESIGN_AGENDA_REVISION,
                identity=agenda.id,
            ),
        )

    @staticmethod
    def _readiness_for_issues(
        issues: tuple[DesignIssue, ...],
        agenda_ref: RealityReference | None = None,
    ) -> DesignReadiness:
        blockers = tuple(
            f"{issue.key}: {issue.completion_condition}"
            for issue in issues
            if issue.critical
            and issue.state not in {DesignIssueState.SATISFIED, DesignIssueState.SKIPPED}
        )
        refs = tuple(
            dict.fromkeys(
                (
                    *((agenda_ref,) if agenda_ref is not None else ()),
                    *(
                        reference
                        for issue in issues
                        for reference in issue.provenance_refs
                    ),
                )
            )
        )
        return DesignReadiness(
            state=(
                DesignReadinessState.READY
                if not blockers
                else DesignReadinessState.NOT_READY
            ),
            blockers=blockers,
            basis_refs=refs,
        )
