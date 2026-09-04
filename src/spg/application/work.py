"""Goal-centric MVP application flow composed over governed Runtime services."""

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.completion import CompletionService
from spg.application.execution import ExecutionService
from spg.application.governance import CandidateGovernanceService
from spg.application.integration import RepositoryIntegrationService
from spg.application.planning import ProductionPlanningService
from spg.application.preparation import PreparationService
from spg.application.runtime import RuntimeService
from spg.application.runtime_commit import RuntimeCommitService
from spg.application.verification import VerificationService
from spg.application.refinement import RepositoryChangeProposalService
from spg.domain.change import (
    ChangeOperation,
    ChangeTargetShape,
    CodeChangeContract,
    CodeChangeTarget,
    CodeVerificationKind,
    CodeVerificationObligation,
    ProductionTargetKind,
)
from spg.domain.executor import ExecutorCapabilityContract
from spg.domain.governance import (
    CandidateAuthorizationScope,
    CandidateSealRequest,
    HumanAuthorizationRequest,
)
from spg.domain.integration import RepositoryIntegrationRequest
from spg.domain.preparation import (
    ContextArtifactSelection,
    ContextPackageRequest,
    ExecutorBinding,
)
from spg.domain.planning import (
    OnePwuFitClassification,
    PlannedArtifactOperation,
    ProductionPlanArtifactTarget,
    ProductionPlanProposal,
    ProductionPlanner,
    ProductionPlanningRequest,
)
from spg.domain.refinement import (
    RepositoryChangeProposal,
    RepositoryChangeProposalProvider,
    RepositoryChangeProposalRequest,
)
from spg.domain.product import (
    ArtifactTargetConfidence,
    ArtifactTargetOperation,
    ArtifactTargetProposal,
    AttentionAction,
    AttentionItem,
    AttentionKind,
    AttentionResolutionRequest,
    EngineeringContextReference,
    EngineeringResourceKind,
    EngineeringResourceRecord,
    EngineeringScopeCondition,
    GoalCondition,
    GoalProjection,
    GoalRecord,
    ProductInvariantViolation,
    ProductRecordNotFound,
    ResourceBindingCondition,
    RuntimeFactSummary,
    WorkCondition,
    WorkProjection,
    WorkRecord,
    WorkRefinementRequest,
    WorkResultProjection,
    WorkStatus,
)
from spg.domain.runtime import (
    ArtifactContract,
    ArtifactOperation,
    CompletionContract,
    InitialRunRequest,
    ProductionHorizon,
)
from spg.domain.runtime_commit import RuntimeCommitRequest
from spg.domain.verification import (
    ProductionAdmissibilityOutcome,
    VerificationResultValue,
)
from spg.domain.verifier import VerificationCapabilityContract
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.providers.rule_based_planner import RuleBasedProductionPlanner
from spg.providers.repository_change_proposal import (
    RepositoryAwareChangeProposalProvider,
)


WORK_ACTOR = "spg-product:work-application"
DEFAULT_BINDING = ExecutorBinding(
    binding_ref="binding:configured-mvp-executor",
    capability_identity="capability:executor",
    profile_identity="profile:local-mvp",
)


class WorkApplicationService:
    """Public Python product API; Runtime services retain transition authority."""

    def __init__(
        self,
        database: Database,
        *,
        workspace_root: Path | None = None,
        executor: ExecutorCapabilityContract | None = None,
        verifier: VerificationCapabilityContract | None = None,
        planner: ProductionPlanner | None = None,
        change_proposal_provider: RepositoryChangeProposalProvider | None = None,
        executor_binding: ExecutorBinding = DEFAULT_BINDING,
    ) -> None:
        self.database = database
        self.workspace_root = (workspace_root or Path(".spg/workspaces")).resolve()
        self.executor = executor
        self.verifier = verifier
        self.planning = ProductionPlanningService(
            planner or RuleBasedProductionPlanner()
        )
        self.change_proposals = RepositoryChangeProposalService(
            change_proposal_provider or RepositoryAwareChangeProposalProvider()
        )
        self.executor_binding = executor_binding
        self.runtime = RuntimeService(database)
        self.preparation = PreparationService(database)
        self.execution = ExecutionService(database, preparation=self.preparation)
        self.completion = CompletionService(database, observer=self.execution.observer)
        self.verification = VerificationService(
            database,
            observer=self.execution.observer,
        )
        self.governance = CandidateGovernanceService(database)
        self.integration = RepositoryIntegrationService(database)
        self.runtime_commit = RuntimeCommitService(database)

    def create_goal(self, title: str, description: str | None = None) -> GoalRecord:
        title = title.strip()
        if not title:
            raise ProductInvariantViolation("Goal title is required")
        goal_id = uuid4()
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            store.insert_goal(
                {
                    "id": goal_id,
                    "title": title,
                    "description": description,
                    "condition": GoalCondition.ACTIVE.value,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )
            result = store.goal(goal_id)
            unit_of_work.commit()
        if result is None:
            raise ProductInvariantViolation("Goal was not constructed")
        return result

    def get_goal(self, goal_id: UUID) -> GoalRecord:
        with self.database.unit_of_work() as unit_of_work:
            goal = ProductStore(unit_of_work.session).goal(goal_id)
        if goal is None:
            raise ProductRecordNotFound(f"Goal not found: {goal_id}")
        return goal

    def list_goals(self) -> tuple[GoalRecord, ...]:
        with self.database.unit_of_work() as unit_of_work:
            return ProductStore(unit_of_work.session).list_goals()

    def register_engineering_resource(
        self,
        *,
        repository_identity: str,
        location_ref: str,
        authoritative_ref: str,
        context_references: tuple[EngineeringContextReference, ...],
        is_default: bool = True,
    ) -> EngineeringResourceRecord:
        if not repository_identity.strip() or not location_ref.strip():
            raise ProductInvariantViolation("Engineering Resource identity/location required")
        if not context_references:
            raise ProductInvariantViolation(
                "MVP repository resource requires at least one Context reference"
            )
        resource_id = uuid4()
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            store.insert_resource(
                {
                    "id": resource_id,
                    "kind": EngineeringResourceKind.REPOSITORY.value,
                    "repository_identity": repository_identity,
                    "location_ref": location_ref,
                    "authoritative_ref": authoritative_ref,
                    "context_references": [
                        item.model_dump(mode="json") for item in context_references
                    ],
                    "is_default": is_default,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )
            result = store.resource(resource_id)
            unit_of_work.commit()
        if result is None:
            raise ProductInvariantViolation("Engineering Resource was not constructed")
        return result

    def submit_work(
        self,
        raw_user_requirement: str,
        *,
        goal_id: UUID | None = None,
        tags: tuple[str, ...] = (),
    ) -> WorkProjection:
        if not raw_user_requirement.strip():
            raise ProductInvariantViolation("Work requirement is required")
        timestamp = datetime.now(UTC)
        work_id = uuid4()
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            if goal_id is not None and store.goal(goal_id) is None:
                raise ProductRecordNotFound(f"Goal not found: {goal_id}")
            normalized_tags = tuple(
                sorted({item.strip() for item in tags if item.strip()})
            )
            store.insert_work(
                {
                    "id": work_id,
                    "goal_id": goal_id,
                    "raw_user_requirement": raw_user_requirement,
                    "refined_title": None,
                    "desired_outcome": None,
                    "constraints": [],
                    "tags": list(normalized_tags),
                    "condition": WorkCondition.DRAFT.value,
                    "scope_summary": None,
                    "production_objective": None,
                    "expected_artifact_path": None,
                    "artifact_operation": None,
                    "artifact_placement_rationale": None,
                    "artifact_target_confidence": None,
                    "artifact_source_baseline_id": None,
                    "artifact_source_revision": None,
                    "verification_expectation": None,
                    "code_change_proposal": None,
                    "production_plan_proposal": None,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )
            unit_of_work.commit()
        return self.get_work(work_id)

    def refine_work(
        self,
        work_id: UUID,
        request: WorkRefinementRequest | None = None,
    ) -> WorkProjection:
        request = request or WorkRefinementRequest()
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            work = self._required_work(store, work_id)
            if work.condition not in {
                WorkCondition.DRAFT,
                WorkCondition.NEEDS_REFINEMENT,
                WorkCondition.AWAITING_APPROVAL,
            }:
                raise ProductInvariantViolation("Only a draft Work may be refined")
            resource = store.default_resource()
            if resource is None:
                raise ProductInvariantViolation(
                    "A configured default Engineering Resource is required"
                )
            title = request.title or self._default_title(work.raw_user_requirement)
            desired_outcome = request.desired_outcome or work.raw_user_requirement.strip()
            scope_summary = (
                request.scope_summary
                or f"Change {resource.repository_identity} at {resource.authoritative_ref}"
            )
            objective = request.production_objective or desired_outcome
            baseline = self.runtime.current_baseline()
            if baseline.repository_identity != resource.repository_identity:
                raise ProductInvariantViolation(
                    "Engineering Resource does not match current governed Baseline"
                )
            constraints = self._merge_constraints(
                work.constraints,
                request.constraints,
                self._extract_constraints(work.raw_user_requirement),
            )
            code_work = self._is_code_work(work.raw_user_requirement, request)
            existing_proposal = work.code_change_proposal
            change_proposal = (
                self._repository_change_proposal(
                    work_id=work.id,
                    raw=work.raw_user_requirement,
                    request=request,
                    existing=existing_proposal,
                    resource=resource,
                    baseline_id=baseline.id,
                    source_ref=baseline.repository_ref,
                    source_revision=baseline.repository_revision,
                    desired_outcome=desired_outcome,
                    constraints=constraints,
                )
                if code_work
                else None
            )
            proposal = (
                None
                if code_work
                else self._artifact_target_proposal(
                    raw=work.raw_user_requirement,
                    explicit_path=request.expected_artifact_path,
                    resource=resource,
                    baseline_id=baseline.id,
                    source_revision=baseline.repository_revision,
                )
            )
            verification = (
                request.verification_expectation
                or (
                    self._proposal_verification_summary(change_proposal)
                    if change_proposal is not None
                    else "Verify the requested outcome against independent repository Reality"
                )
            )
            refinement_reasons: list[str] = []
            if self._is_too_broad(work.raw_user_requirement):
                refinement_reasons.append(
                    "The admitted Work is too broad for a trustworthy single-PWU plan."
                )
            if code_work and (
                change_proposal is None
                or (
                    not change_proposal.required_targets
                    and not change_proposal.allowed_areas
                )
            ):
                refinement_reasons.append(
                    "A safely bounded exact target set or repository area is required for code production."
                )
            if code_work and change_proposal is not None:
                refinement_reasons.extend(
                    change_proposal.unresolved_scope_questions
                )
            elif not code_work and proposal is None:
                refinement_reasons.append(
                    "An exact authorized artifact target is required before production."
                )
            plan = self.planning.propose(
                ProductionPlanningRequest(
                    work_id=work.id,
                    target_kind=(
                        ProductionTargetKind.CODE_WORK
                        if code_work
                        else ProductionTargetKind.DOCUMENTATION_WORK
                    ),
                    admitted_requirement=work.raw_user_requirement,
                    desired_outcome=desired_outcome,
                    production_objective=objective,
                    artifact_targets=(
                        ()
                        if proposal is None
                        else (
                            ProductionPlanArtifactTarget(
                                path=proposal.path,
                                operation=PlannedArtifactOperation(
                                    proposal.operation.value
                                ),
                            ),
                        )
                    ),
                    change_proposal=change_proposal,
                    change_contract=None,
                    constraints=constraints,
                    verification_expectation=verification,
                    engineering_scope_summary=scope_summary,
                    engineering_resource_id=resource.id,
                    repository_identity=resource.repository_identity,
                    source_baseline_id=baseline.id,
                    source_revision=baseline.repository_revision,
                    context_references=tuple(
                        item.repository_relative_path
                        for item in resource.context_references
                    ),
                    refinement_reasons=tuple(refinement_reasons),
                )
            )
            condition = (
                WorkCondition.AWAITING_APPROVAL
                if plan.fit_classification
                is OnePwuFitClassification.ONE_PWU_FIT
                else WorkCondition.NEEDS_REFINEMENT
            )
            scope_id = uuid4()
            timestamp = datetime.now(UTC)
            fingerprint = self._fingerprint(
                {
                    "work_id": str(work.id),
                    "summary": scope_summary,
                    "resource_ids": [str(resource.id)],
                }
            )
            store.replace_scope(
                scope_values={
                    "id": scope_id,
                    "work_id": work.id,
                    "summary": scope_summary,
                    "fingerprint": fingerprint,
                    "condition": EngineeringScopeCondition.PROPOSED.value,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                },
                binding_values=(
                    {
                        "id": uuid4(),
                        "engineering_scope_id": scope_id,
                        "resource_id": resource.id,
                        "condition": ResourceBindingCondition.PROPOSED.value,
                        "created_at": timestamp,
                    },
                ),
            )
            store.update_work(
                work.id,
                {
                    "refined_title": title,
                    "desired_outcome": desired_outcome,
                    "constraints": list(constraints),
                    "condition": condition.value,
                    "scope_summary": scope_summary,
                    "production_objective": objective,
                    "expected_artifact_path": (
                        None if proposal is None else proposal.path
                    ),
                    "artifact_operation": (
                        None if proposal is None else proposal.operation.value
                    ),
                    "artifact_placement_rationale": (
                        None if proposal is None else proposal.placement_rationale
                    ),
                    "artifact_target_confidence": (
                        None if proposal is None else proposal.confidence.value
                    ),
                    "artifact_source_baseline_id": (
                        None if proposal is None else proposal.source_baseline_id
                    ),
                    "artifact_source_revision": (
                        None if proposal is None else proposal.source_revision
                    ),
                    "verification_expectation": verification,
                    "code_change_proposal": (
                        None
                        if change_proposal is None
                        else change_proposal.model_dump(mode="json")
                    ),
                    "production_plan_proposal": plan.model_dump(mode="json"),
                    "updated_at": timestamp,
                },
            )
            unit_of_work.commit()
        return self.get_work(work_id)

    create_work_draft = refine_work

    def update_work_tags(
        self,
        work_id: UUID,
        tags: tuple[str, ...],
    ) -> WorkProjection:
        normalized = tuple(sorted({item.strip() for item in tags if item.strip()}))
        if len(normalized) > 20:
            raise ProductInvariantViolation("MVP Work supports at most 20 tags")
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            self._required_work(store, work_id)
            store.update_work(
                work_id,
                {"tags": list(normalized), "updated_at": datetime.now(UTC)},
            )
            unit_of_work.commit()
        return self.get_work(work_id)

    def approve_work(
        self,
        work_id: UUID,
        *,
        authority_identity: str,
        rationale: str | None = None,
    ) -> WorkProjection:
        if not authority_identity.strip():
            raise ProductInvariantViolation("Human authority identity is required")
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            work = self._required_work(store, work_id)
            existing = store.runtime_binding(work_id)
            if existing is not None:
                return self._projection(store, work)
            if work.condition is not WorkCondition.AWAITING_APPROVAL:
                raise ProductInvariantViolation(
                    "Work must await Human approval before Runtime admission"
                )
            scope = store.scope_for_work(work_id)
            if scope is None:
                raise ProductInvariantViolation("Work has no Engineering Scope")
            active = tuple(
                item
                for item in scope.bindings
                if item.condition is ResourceBindingCondition.PROPOSED
            )
            self._require_mvp_scope(active)
            resource = store.resource(active[0].resource_id)
            if resource is None:
                raise ProductInvariantViolation("Scope Resource is missing")
            plan = self._required_production_plan(work)
            artifact = self._artifact_target(work)
            change_proposal = work.code_change_proposal
            change_contract = plan.change_contract

        baseline = self.runtime.current_baseline()
        if (
            baseline.repository_identity != resource.repository_identity
            or baseline.repository_ref != resource.authoritative_ref
        ):
            raise ProductInvariantViolation(
                "Engineering Resource does not match current governed Baseline"
            )
        if plan.fit_classification is not OnePwuFitClassification.ONE_PWU_FIT:
            raise ProductInvariantViolation(
                "Work Production Plan is not fit for the single-PWU MVP"
            )
        if sum(
            (
                artifact is not None,
                change_proposal is not None,
                change_contract is not None,
            )
        ) != 1:
            raise ProductInvariantViolation(
                "Work must contain exactly one documentation target, Code Proposal, or legacy Code Contract"
            )
        expected_plan_targets = ()
        if artifact is not None:
            if (
                artifact.source_baseline_id != baseline.id
                or artifact.source_revision != baseline.repository_revision
            ):
                raise ProductInvariantViolation(
                    "Artifact Target Proposal is stale against the current Source Baseline"
                )
            expected_plan_targets = (
                ProductionPlanArtifactTarget(
                    path=artifact.path,
                    operation=PlannedArtifactOperation(artifact.operation.value),
                ),
            )
        if change_proposal is not None:
            if (
                plan.change_proposal != change_proposal
                or change_proposal.engineering_resource_id != resource.id
                or change_proposal.repository_identity != resource.repository_identity
                or change_proposal.source_baseline_id != baseline.id
                or change_proposal.source_ref != baseline.repository_ref
                or change_proposal.source_revision != baseline.repository_revision
            ):
                raise ProductInvariantViolation(
                    "Code Change Proposal is stale against the current Source Baseline"
                )
            change_contract = self._admit_change_contract(
                change_proposal,
                desired_outcome=(
                    work.desired_outcome or work.raw_user_requirement.strip()
                ),
                constraints=work.constraints,
            )
            plan = self.planning.propose(
                ProductionPlanningRequest(
                    work_id=work.id,
                    target_kind=ProductionTargetKind.CODE_WORK,
                    admitted_requirement=work.raw_user_requirement,
                    desired_outcome=(
                        work.desired_outcome or work.raw_user_requirement.strip()
                    ),
                    production_objective=(
                        work.production_objective or work.desired_outcome or ""
                    ),
                    change_contract=change_contract,
                    constraints=work.constraints,
                    verification_expectation=work.verification_expectation or "",
                    engineering_scope_summary=scope.summary,
                    engineering_resource_id=resource.id,
                    repository_identity=resource.repository_identity,
                    source_baseline_id=baseline.id,
                    source_revision=baseline.repository_revision,
                    context_references=tuple(
                        item.repository_relative_path
                        for item in resource.context_references
                    ),
                )
            )
            if plan.fit_classification is not OnePwuFitClassification.ONE_PWU_FIT:
                raise ProductInvariantViolation(
                    "Admitted Code Change Contract did not produce a one-PWU Plan"
                )
        if change_contract is not None and (
            change_contract.engineering_resource_id != resource.id
            or change_contract.repository_identity != resource.repository_identity
            or change_contract.source_baseline_id != baseline.id
            or change_contract.source_revision != baseline.repository_revision
            or change_contract.desired_outcome
            != (work.desired_outcome or work.raw_user_requirement.strip())
            or change_contract.constraints != work.constraints
        ):
            raise ProductInvariantViolation(
                "Code Change Contract no longer matches the admitted Work authority envelope"
            )
        if (
            plan.desired_outcome
            != (work.desired_outcome or work.raw_user_requirement.strip())
            or plan.objective
            != (work.production_objective or work.desired_outcome or "")
            or plan.target_kind
            is not (
                ProductionTargetKind.CODE_WORK
                if change_contract is not None
                else ProductionTargetKind.DOCUMENTATION_WORK
            )
            or plan.artifact_targets != expected_plan_targets
            or plan.change_contract != change_contract
            or plan.inherited_constraints != work.constraints
            or plan.verification_approach
            != (work.verification_expectation or "")
            or plan.engineering_resource_id != resource.id
            or plan.repository_identity != resource.repository_identity
            or plan.source_baseline_id != baseline.id
            or plan.source_revision != baseline.repository_revision
        ):
            raise ProductInvariantViolation(
                "Production Plan no longer matches the admitted Work authority envelope"
            )
        if artifact is not None:
            verification_obligation = (
                work.verification_expectation
                or "Verify the admitted artifact against independent repository Reality"
            )
            artifact_contract = ArtifactContract(
                engineering_resource_id=resource.id,
                repository_identity=resource.repository_identity,
                source_baseline_id=baseline.id,
                source_revision=baseline.repository_revision,
                artifact_path=artifact.path,
                operation=ArtifactOperation(artifact.operation.value),
                constraints=work.constraints,
                expected_outcome=work.desired_outcome or work.raw_user_requirement.strip(),
                verification_obligation=verification_obligation,
            )
            objective = self._artifact_objective(artifact_contract)
            horizon = ProductionHorizon.DOCUMENTATION
            completion_contract = CompletionContract(
                required_outputs=(artifact.path,),
                required_changes=(artifact.path,),
                verification_obligations=(verification_obligation,),
                artifact_contract=artifact_contract,
                production_plan=plan,
            )
        else:
            assert change_contract is not None
            objective = self._code_change_objective(change_contract)
            horizon = ProductionHorizon.CODE
            exact_paths = tuple(target.path for target in change_contract.exact_targets)
            completion_contract = CompletionContract(
                required_outputs=exact_paths,
                required_changes=exact_paths,
                verification_obligations=change_contract.verification_identities,
                change_contract=change_contract,
                production_plan=plan,
            )
        spine = self.runtime.create_initial_runtime_spine(
            InitialRunRequest(
                intent_ref=f"work:{work.id}",
                goal=work.desired_outcome or work.refined_title or "Governed Work",
                production_horizon=horizon,
                initial_work_unit_objective=objective,
                completion_contract=completion_contract,
            )
        )
        timestamp = datetime.now(UTC)
        governance_id = uuid5(
            NAMESPACE_URL,
            f"spg:work-admission:{work.id}:{scope.fingerprint}:{authority_identity}",
        )
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            current = self._required_work(product, work_id)
            if product.runtime_binding(work_id) is not None:
                unit_of_work.rollback()
                return self.get_work(work_id)
            runtime.insert_governance(
                {
                    "id": governance_id,
                    "decision_type": "ADMIT_WORK_DRAFT",
                    "authority_identity": authority_identity,
                    "subject_type": "PRODUCT_WORK",
                    "subject_identity": str(work.id),
                    "scope": {
                        "engineering_scope_id": str(scope.id),
                        "scope_fingerprint": scope.fingerprint,
                        "resource_id": str(resource.id),
                        "production_run_id": str(spine.run.id),
                        "work_unit_id": str(spine.work_unit.id),
                        "production_plan_proposal_id": str(plan.proposal_id),
                        "production_plan_fingerprint": self._fingerprint(
                            plan.model_dump(mode="json")
                        ),
                        "production_plan_fit": plan.fit_classification.value,
                        "source_change_proposal_id": (
                            None
                            if change_proposal is None
                            else str(change_proposal.proposal_id)
                        ),
                        "source_change_proposal_fingerprint": (
                            None
                            if change_proposal is None
                            else change_proposal.proposal_fingerprint
                        ),
                    },
                    "rationale": rationale,
                    "created_at": timestamp,
                }
            )
            product.insert_runtime_binding(
                {
                    "work_id": current.id,
                    "engineering_scope_id": scope.id,
                    "resource_id": resource.id,
                    "production_run_id": spine.run.id,
                    "plan_revision_id": spine.plan_revision.id,
                    "work_unit_id": spine.work_unit.id,
                    "governance_record_id": governance_id,
                    "admitted_by": authority_identity,
                    "created_at": timestamp,
                }
            )
            product.set_scope_condition(
                scope.id,
                EngineeringScopeCondition.ADMITTED,
                updated_at=timestamp,
            )
            product.update_work(
                current.id,
                {
                    "condition": WorkCondition.READY.value,
                    "production_plan_proposal": plan.model_dump(mode="json"),
                    "updated_at": timestamp,
                },
            )
            unit_of_work.commit()
        return self.get_work(work_id)

    approve_work_draft = approve_work

    def reject_work_draft(
        self,
        work_id: UUID,
        *,
        authority_identity: str,
    ) -> WorkProjection:
        return self._record_draft_decision(
            work_id,
            authority_identity=authority_identity,
            decision_type="REJECT_WORK_DRAFT",
            condition=WorkCondition.REJECTED,
        )

    def request_work_refinement(
        self,
        work_id: UUID,
        *,
        authority_identity: str,
    ) -> WorkProjection:
        return self._record_draft_decision(
            work_id,
            authority_identity=authority_identity,
            decision_type="REQUEST_WORK_REFINEMENT",
            condition=WorkCondition.NEEDS_REFINEMENT,
        )

    reject_work = reject_work_draft
    request_refinement = request_work_refinement

    def get_work(self, work_id: UUID) -> WorkProjection:
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            work = self._required_work(store, work_id)
            return self._projection(store, work)

    def orchestration_reality_fingerprint(self, work_id: UUID) -> str:
        """Fingerprint persisted facts used only to detect actual step progress."""

        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            work = self._required_work(product, work_id)
            binding = product.runtime_binding(work_id)
            if binding is None:
                facts = RuntimeFactSummary()
            else:
                facts = product.runtime_summary(binding)
                preparation = (
                    None
                    if facts.attempt_id is None
                    else runtime.attempt_preparation(facts.attempt_id)
                )
                preparation_identity = (
                    None if preparation is None else str(preparation.attempt_id)
                )
            if binding is None:
                preparation_identity = None
        return self._fingerprint(
            {
                "work_condition": work.condition.value,
                "runtime_facts": facts.model_dump(mode="json"),
                "attempt_preparation_identity": preparation_identity,
            }
        )

    def list_works(self, goal_id: UUID | None = None) -> tuple[WorkProjection, ...]:
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            return tuple(
                self._projection(store, work)
                for work in store.list_works(goal_id=goal_id)
            )

    def get_goal_projection(self, goal_id: UUID) -> GoalProjection:
        goal = self.get_goal(goal_id)
        works = self.list_works(goal_id=goal_id)
        counts: dict[WorkStatus, int] = {}
        for work in works:
            counts[work.status] = counts.get(work.status, 0) + 1
        return GoalProjection(
            goal=goal,
            work_count=len(works),
            works_by_status=counts,
            recent_works=works[:10],
            needs_attention_count=sum(
                item.status in {WorkStatus.NEEDS_ATTENTION, WorkStatus.AWAITING_APPROVAL}
                for item in works
            ),
        )

    def advance_work(self, work_id: UUID) -> WorkProjection:
        """Perform at most one currently legal governed production action."""

        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime_store = RuntimeStore(unit_of_work.session)
            work = self._required_work(product, work_id)
            binding = product.runtime_binding(work_id)
            if binding is None:
                return self._projection(product, work)
            resource = product.resource(binding.resource_id)
            if resource is None:
                raise ProductInvariantViolation("Bound Engineering Resource is missing")
            summary = product.runtime_summary(binding)
            work_unit = runtime_store.work_unit(binding.work_unit_id)
            if work_unit is None:
                raise ProductInvariantViolation("Bound governed PWU is missing")

        if summary.runtime_commit_id is not None:
            return self.get_work(work_id)
        if summary.attempt_id is None:
            self.runtime.create_initial_attempt(binding.work_unit_id)
            return self.get_work(work_id)

        with self.database.unit_of_work() as unit_of_work:
            runtime_store = RuntimeStore(unit_of_work.session)
            package = runtime_store.latest_context_package(binding.work_unit_id)
            preparation = runtime_store.attempt_preparation(summary.attempt_id)
        if preparation is None:
            repository_path = Path(resource.location_ref).resolve()
            if package is None:
                package = self.preparation.assemble_context_package(
                    binding.work_unit_id,
                    repository_path,
                    ContextPackageRequest(
                        artifacts=tuple(
                            ContextArtifactSelection(
                                semantic_role=item.semantic_role,
                                repository_relative_path=item.repository_relative_path,
                            )
                            for item in resource.context_references
                        )
                    ),
                )
            self.preparation.prepare_attempt(
                summary.attempt_id,
                package.id,
                self.executor_binding,
                repository_path,
                self.workspace_root,
            )
            return self.get_work(work_id)

        if summary.dispatch_id is None:
            if self.executor is None:
                return self.get_work(work_id)
            self.execution.dispatch_and_observe(summary.attempt_id, self.executor)
            return self.get_work(work_id)

        if summary.observation_id is None:
            return self.get_work(work_id)
        if summary.completion_id is None:
            if (
                work_unit.completion_contract.requires_observed_production_result
                and not summary.artifact_paths
            ):
                return self.get_work(work_id)
            self.completion.evaluate_observation(summary.observation_id)
            return self.get_work(work_id)
        if summary.completion_outcome != "PRODUCED":
            return self.get_work(work_id)

        if summary.proposed_snapshot_id is None:
            self.verification.create_proposed_snapshot(summary.completion_id)
            return self.get_work(work_id)

        required = work_unit.completion_contract.verification_obligations
        verified = set(summary.verification_obligations)
        missing = next((item for item in required if item not in verified), None)
        if missing is not None:
            if self.verifier is None:
                return self.get_work(work_id)
            self.verification.verify_obligation(
                summary.proposed_snapshot_id,
                missing,
                self.verifier,
            )
            return self.get_work(work_id)

        if summary.admissibility_id is None:
            self.verification.evaluate_admissibility(summary.proposed_snapshot_id)
            return self.get_work(work_id)
        if summary.admissibility_outcome != ProductionAdmissibilityOutcome.ADMISSIBLE.value:
            return self.get_work(work_id)

        if summary.candidate_id is None:
            with self.database.unit_of_work() as unit_of_work:
                current = RuntimeStore(unit_of_work.session).work_unit(
                    binding.work_unit_id
                )
            if current is None:
                raise ProductInvariantViolation("Governed PWU disappeared")
            self.governance.seal_candidate(
                CandidateSealRequest(
                    proposed_snapshot_id=summary.proposed_snapshot_id,
                    production_admissibility_id=summary.admissibility_id,
                    expected_work_unit_version=current.version,
                )
            )
            return self.get_work(work_id)

        if summary.authorization_id is None:
            return self.get_work(work_id)
        if summary.integration_effect_id is None:
            self.integration.integrate_repository_candidate(
                RepositoryIntegrationRequest(
                    candidate_id=summary.candidate_id,
                    candidate_fingerprint=summary.candidate_fingerprint or "",
                    human_authorization_id=summary.authorization_id,
                )
            )
            return self.get_work(work_id)
        if summary.integration_state != "CONVERGED":
            return self.get_work(work_id)

        self.runtime_commit.commit_runtime_candidate(
            RuntimeCommitRequest(
                candidate_id=summary.candidate_id,
                candidate_fingerprint=summary.candidate_fingerprint or "",
                human_authorization_id=summary.authorization_id,
                repository_integration_effect_id=summary.integration_effect_id,
            )
        )
        return self.get_work(work_id)

    def list_attention(
        self,
        *,
        work_id: UUID | None = None,
    ) -> tuple[AttentionItem, ...]:
        projections = (
            (self.get_work(work_id),)
            if work_id is not None
            else self.list_works()
        )
        items: list[AttentionItem] = []
        for projection in projections:
            if projection.status is WorkStatus.NEEDS_REFINEMENT:
                questions = (
                    ()
                    if projection.production_plan is None
                    else projection.production_plan.unresolved_questions
                )
                items.append(
                    AttentionItem(
                        id=uuid5(
                            NAMESPACE_URL,
                            f"spg:work-refinement-attention:{projection.work_id}",
                        ),
                        work_id=projection.work_id,
                        kind=AttentionKind.WORK_REFINEMENT_REQUIRED,
                        decision="Refine this Work before production admission.",
                        reason=(
                            " ".join(questions)
                            or "The current Work cannot form a trustworthy single-PWU plan."
                        ),
                        available_actions=(),
                        recommended_action=None,
                        governed_subject_ref=f"work:{projection.work_id}",
                    )
                )
                continue
            if projection.status is WorkStatus.AWAITING_APPROVAL:
                items.append(
                    AttentionItem(
                        id=uuid5(
                            NAMESPACE_URL,
                            f"spg:work-draft-attention:{projection.work_id}",
                        ),
                        work_id=projection.work_id,
                        kind=AttentionKind.WORK_DRAFT_APPROVAL,
                        decision="Admit this governed Work draft?",
                        reason="Draft generation does not create execution authority.",
                        available_actions=(
                            AttentionAction.APPROVE,
                            AttentionAction.REJECT,
                            AttentionAction.REQUEST_REFINEMENT,
                        ),
                        recommended_action=AttentionAction.APPROVE,
                        governed_subject_ref=f"work:{projection.work_id}",
                    )
                )
                continue
            with self.database.unit_of_work() as unit_of_work:
                store = ProductStore(unit_of_work.session)
                binding = store.runtime_binding(projection.work_id)
                summary = (
                    RuntimeFactSummary()
                    if binding is None
                    else store.runtime_summary(binding)
                )
            if summary.candidate_id is not None and summary.authorization_id is None:
                items.append(
                    AttentionItem(
                        id=uuid5(
                            NAMESPACE_URL,
                            f"spg:candidate-attention:{summary.candidate_id}",
                        ),
                        work_id=projection.work_id,
                        kind=AttentionKind.CANDIDATE_AUTHORIZATION,
                        decision="Authorize exact sealed Candidate integration?",
                        reason="Repository integration requires exact Human Authority.",
                        available_actions=(AttentionAction.AUTHORIZE,),
                        recommended_action=None,
                        governed_subject_ref=f"baseline-candidate:{summary.candidate_id}",
                    )
                )
            elif projection.status is WorkStatus.BLOCKED:
                items.append(
                    AttentionItem(
                        id=uuid5(
                            NAMESPACE_URL,
                            f"spg:blocked-work-attention:{projection.work_id}",
                        ),
                        work_id=projection.work_id,
                        kind=AttentionKind.PRODUCTION_BLOCKED,
                        decision="Review the truthful production blocker.",
                        reason=projection.what_happens_next,
                        available_actions=(),
                        recommended_action=None,
                        governed_subject_ref=f"work:{projection.work_id}",
                    )
                )
        return tuple(items)

    def resolve_attention(
        self,
        attention_id: UUID,
        request: AttentionResolutionRequest,
    ) -> WorkProjection:
        attention = next(
            (item for item in self.list_attention() if item.id == attention_id),
            None,
        )
        if attention is None:
            raise ProductRecordNotFound(f"Attention not found: {attention_id}")
        if request.action not in attention.available_actions:
            raise ProductInvariantViolation("Requested Attention action is not allowed")
        if attention.kind is AttentionKind.WORK_DRAFT_APPROVAL:
            if request.action is AttentionAction.APPROVE:
                return self.approve_work(
                    attention.work_id,
                    authority_identity=request.authority_identity,
                    rationale=request.rationale,
                )
            if request.action is AttentionAction.REJECT:
                return self.reject_work_draft(
                    attention.work_id,
                    authority_identity=request.authority_identity,
                )
            return self.request_work_refinement(
                attention.work_id,
                authority_identity=request.authority_identity,
            )

        if attention.kind is AttentionKind.CANDIDATE_AUTHORIZATION:
            with self.database.unit_of_work() as unit_of_work:
                product = ProductStore(unit_of_work.session)
                binding = product.runtime_binding(attention.work_id)
                if binding is None:
                    raise ProductInvariantViolation("Attention has no Runtime lineage")
                summary = product.runtime_summary(binding)
            if summary.candidate_id is None:
                raise ProductInvariantViolation("Candidate Attention lost its subject")
            candidate = self.governance.candidate(summary.candidate_id)
            self.governance.authorize_candidate(
                HumanAuthorizationRequest(
                    authority_identity=request.authority_identity,
                    candidate_id=candidate.id,
                    candidate_fingerprint=candidate.fingerprint,
                    scope=CandidateAuthorizationScope(
                        repository_identity=candidate.repository_identity,
                        target_authoritative_ref=candidate.target_authoritative_ref,
                        expected_source_repository_revision=(
                            candidate.expected_source_repository_revision
                        ),
                        proposed_repository_revision=candidate.proposed_commit_identity,
                    ),
                    rationale=request.rationale,
                )
            )
            return self.get_work(attention.work_id)
        raise ProductInvariantViolation("Blocked Reality cannot be overridden")

    def get_work_result(self, work_id: UUID) -> WorkResultProjection:
        projection = self.get_work(work_id)
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            binding = store.runtime_binding(work_id)
            summary = RuntimeFactSummary() if binding is None else store.runtime_summary(binding)
        verification = tuple(
            f"{obligation}: {result}"
            for obligation, result in zip(
                summary.verification_obligations,
                summary.verification_results,
                strict=False,
            )
        )
        repository_state = None
        if summary.runtime_commit_id is not None:
            repository_state = "TRUSTED_BASELINE_ADVANCED"
        elif summary.integration_state is not None:
            repository_state = f"REPOSITORY_INTEGRATION_{summary.integration_state}"
        elif summary.candidate_id is not None:
            repository_state = "SEALED_CANDIDATE"
        blocker = None
        if projection.status is not WorkStatus.COMPLETED:
            blocker = projection.what_happens_next
        return WorkResultProjection(
            work_id=work_id,
            status=projection.status,
            desired_outcome=projection.desired_outcome,
            produced_artifacts=summary.artifact_paths,
            verification_summary=verification,
            repository_state=repository_state,
            trusted_result=summary.runtime_commit_id is not None,
            remaining_blocker_or_risk=blocker,
            human_attention_required=projection.human_attention_required,
        )

    def _projection(
        self,
        store: ProductStore,
        work: WorkRecord,
    ) -> WorkProjection:
        scope = store.scope_for_work(work.id)
        binding = store.runtime_binding(work.id)
        summary = RuntimeFactSummary() if binding is None else store.runtime_summary(binding)
        status, step, event, next_action = self._projection_state(work, summary)
        result_summary = None
        if summary.runtime_commit_id is not None:
            result_summary = "Trusted Runtime Commit recorded"
        elif summary.artifact_paths:
            result_summary = (
                f"{len(summary.artifact_paths)} independently observed artifact change(s)"
            )
        return WorkProjection(
            work_id=work.id,
            goal_id=work.goal_id,
            raw_user_requirement=work.raw_user_requirement,
            title=work.refined_title,
            desired_outcome=work.desired_outcome,
            constraints=work.constraints,
            target_kind=(
                ProductionTargetKind.DOCUMENTATION_WORK
                if work.production_plan is None
                else work.production_plan.target_kind
            ),
            artifact_target=self._artifact_target(work),
            change_proposal=work.code_change_proposal,
            change_contract=(
                None
                if work.production_plan is None
                else work.production_plan.change_contract
            ),
            production_plan=work.production_plan,
            tags=work.tags,
            engineering_scope=scope,
            status=status,
            current_production_step=step,
            most_recent_meaningful_event=summary.latest_event or event,
            what_happens_next=next_action,
            human_attention_required=status
            in {
                WorkStatus.NEEDS_REFINEMENT,
                WorkStatus.AWAITING_APPROVAL,
                WorkStatus.NEEDS_ATTENTION,
                WorkStatus.BLOCKED,
            },
            result_summary=result_summary,
        )

    def _projection_state(
        self,
        work: WorkRecord,
        facts: RuntimeFactSummary,
    ) -> tuple[WorkStatus, str, str, str]:
        if work.condition is WorkCondition.DRAFT:
            return WorkStatus.DRAFT, "WORK_INTAKE", "WORK_SUBMITTED", "Refine Work draft"
        if work.condition is WorkCondition.NEEDS_REFINEMENT:
            if (
                work.production_plan is not None
                and work.production_plan.fit_classification
                is OnePwuFitClassification.MULTI_PWU_REQUIRED
            ):
                return (
                    WorkStatus.NEEDS_REFINEMENT,
                    "PRODUCTION_PLANNING",
                    "MULTI_PWU_REQUIRED",
                    "Narrow the Work to one governed PWU; multi-PWU production is deferred",
                )
            return (
                WorkStatus.NEEDS_REFINEMENT,
                "PRODUCTION_PLANNING",
                "PLAN_REFINEMENT_REQUIRED",
                "Narrow or clarify the Work",
            )
        if work.condition is WorkCondition.AWAITING_APPROVAL:
            return (
                WorkStatus.AWAITING_APPROVAL,
                "HUMAN_ADMISSION",
                "WORK_DRAFTED",
                "Human must approve, reject, or request refinement",
            )
        if work.condition is WorkCondition.REJECTED:
            return WorkStatus.BLOCKED, "WORK_REJECTED", "WORK_REJECTED", "No execution is authorized"
        if facts.runtime_commit_id is not None:
            return WorkStatus.COMPLETED, "RUNTIME_COMMIT", "TRUSTED_BASELINE_ADVANCED", "Work is complete"
        if (
            facts.dispatch_id is not None
            and facts.provider_outcome == "UNKNOWN"
            and facts.observation_id is not None
            and not facts.artifact_paths
            and facts.completion_id is None
            and facts.completion_requires_production_result
        ):
            return (
                WorkStatus.BLOCKED,
                "EXECUTION_STOPPED",
                "PROVIDER_OUTCOME_UNKNOWN_PRODUCTION_NONE",
                "Execution stopped before Provider completion. Architecture/Operator review required.",
            )
        if (
            facts.dispatch_id is not None
            and facts.provider_outcome is not None
            and facts.observation_id is not None
            and not facts.artifact_paths
            and facts.completion_id is None
            and facts.completion_requires_production_result
        ):
            return (
                WorkStatus.BLOCKED,
                "EXECUTION_STOPPED",
                "REQUIRED_PRODUCTION_RESULT_ABSENT",
                "Execution completed without the required production result. "
                "Architecture/Operator review required.",
            )
        if facts.completion_outcome == "NOT_PRODUCED":
            return WorkStatus.BLOCKED, "COMPLETION", "OUTPUT_NOT_PRODUCED", "Review Completion failures"
        if (
            facts.admissibility_outcome is not None
            and facts.admissibility_outcome
            != ProductionAdmissibilityOutcome.ADMISSIBLE.value
        ):
            return WorkStatus.BLOCKED, "VERIFICATION", "NOT_ADMISSIBLE", "Review Verification evidence"
        if facts.candidate_id is not None and facts.authorization_id is None:
            return (
                WorkStatus.NEEDS_ATTENTION,
                "CANDIDATE_AUTHORITY",
                "CANDIDATE_SEALED",
                "Human must authorize the exact Candidate",
            )
        if facts.attempt_id is not None and facts.dispatch_id is None and self.executor is None:
            return (
                WorkStatus.NEEDS_ATTENTION,
                "EXECUTOR_BINDING",
                "ATTEMPT_READY",
                "Configure an Executor capability",
            )
        if (
            facts.proposed_snapshot_id is not None
            and not facts.verification_obligations
            and self.verifier is None
        ):
            return (
                WorkStatus.NEEDS_ATTENTION,
                "VERIFICATION_PROVIDER",
                "SNAPSHOT_PROPOSED",
                "Configure a Verification capability",
            )
        if facts.attempt_id is None:
            return WorkStatus.READY, "PWU_READY", "WORK_ADMITTED", "Create initial Attempt"
        return WorkStatus.RUNNING, self._runtime_step(facts), facts.latest_event or "RUNTIME_ACTIVE", self._next_runtime_action(facts)

    @staticmethod
    def _runtime_step(facts: RuntimeFactSummary) -> str:
        if facts.integration_effect_id is not None:
            return "REPOSITORY_INTEGRATION"
        if facts.authorization_id is not None:
            return "AUTHORIZED_CANDIDATE"
        if facts.candidate_id is not None:
            return "CANDIDATE_GOVERNANCE"
        if facts.admissibility_id is not None:
            return "PRODUCTION_ADMISSIBILITY"
        if facts.proposed_snapshot_id is not None:
            return "VERIFICATION"
        if facts.completion_id is not None:
            return "COMPLETION"
        if facts.observation_id is not None:
            return "PRODUCTION_OBSERVATION"
        if facts.dispatch_id is not None:
            return "EXECUTION"
        return "ATTEMPT_PREPARATION"

    @staticmethod
    def _next_runtime_action(facts: RuntimeFactSummary) -> str:
        if facts.integration_effect_id is not None:
            return "Commit converged repository Reality to Runtime"
        if facts.authorization_id is not None:
            return "Integrate authorized Candidate"
        if facts.admissibility_id is not None:
            return "Seal eligible Candidate"
        if facts.proposed_snapshot_id is not None:
            return "Complete Verification and admissibility"
        if facts.completion_id is not None:
            return "Create proposed repository snapshot"
        if facts.observation_id is not None:
            return "Evaluate Completion"
        if facts.dispatch_id is not None:
            return "Observe production Reality"
        return "Prepare or dispatch current Attempt"

    def _record_draft_decision(
        self,
        work_id: UUID,
        *,
        authority_identity: str,
        decision_type: str,
        condition: WorkCondition,
    ) -> WorkProjection:
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            work = self._required_work(product, work_id)
            if product.runtime_binding(work_id) is not None:
                raise ProductInvariantViolation(
                    "Admitted Work cannot be rewritten as a draft decision"
                )
            if work.condition not in {
                WorkCondition.DRAFT,
                WorkCondition.NEEDS_REFINEMENT,
                WorkCondition.AWAITING_APPROVAL,
            }:
                raise ProductInvariantViolation("Work is not in draft governance")
            governance_id = uuid5(
                NAMESPACE_URL,
                f"spg:{decision_type}:{work.id}:{authority_identity}",
            )
            runtime.insert_governance(
                {
                    "id": governance_id,
                    "decision_type": decision_type,
                    "authority_identity": authority_identity,
                    "subject_type": "PRODUCT_WORK",
                    "subject_identity": str(work.id),
                    "scope": {},
                    "rationale": None,
                    "created_at": timestamp,
                }
            )
            product.update_work(
                work.id,
                {"condition": condition.value, "updated_at": timestamp},
            )
            unit_of_work.commit()
        return self.get_work(work_id)

    @staticmethod
    def _required_work(store: ProductStore, work_id: UUID) -> WorkRecord:
        work = store.work(work_id)
        if work is None:
            raise ProductRecordNotFound(f"Work not found: {work_id}")
        return work

    @staticmethod
    def _require_mvp_scope(bindings) -> None:
        if len(bindings) != 1:
            raise ProductInvariantViolation(
                "MVP execution requires exactly one active Engineering Resource binding"
            )

    @staticmethod
    def _default_title(raw: str) -> str:
        first = next((line.strip() for line in raw.splitlines() if line.strip()), "")
        return first[:120] or "Untitled Work"

    @classmethod
    def _is_code_work(
        cls,
        raw: str,
        request: WorkRefinementRequest,
    ) -> bool:
        if any(
            value is not None
            for value in (
                request.code_exact_targets,
                request.code_allowed_areas,
                request.code_forbidden_areas,
                request.code_verification_obligations,
            )
        ):
            return True
        paths = cls._explicit_repository_paths(raw)
        if any(
            path.startswith(("src/", "tests/")) or path.endswith(".py")
            for path in paths
        ) or cls._explicit_repository_areas(raw):
            return True
        normalized = " ".join(raw.casefold().split())
        markers = (
            "source code",
            "python code",
            "code change",
            "modify code",
            "update code",
            "frontend",
            "javascript",
            "fix the bug",
            "unit test",
            "代码",
            "前端",
            "源文件",
            "修复 bug",
            "单元测试",
        )
        return any(marker in normalized for marker in markers)

    def _repository_change_proposal(
        self,
        *,
        work_id: UUID,
        raw: str,
        request: WorkRefinementRequest,
        existing: RepositoryChangeProposal | None,
        resource: EngineeringResourceRecord,
        baseline_id: UUID,
        source_ref: str,
        source_revision: str,
        desired_outcome: str,
        constraints: tuple[str, ...],
    ) -> RepositoryChangeProposal:
        exact_paths = (
            request.code_exact_targets
            if request.code_exact_targets is not None
            else self._explicit_repository_paths(raw)
            or (
                tuple(target.path for target in existing.required_targets)
                if existing is not None
                else ()
            )
        )
        allowed_areas = (
            request.code_allowed_areas
            if request.code_allowed_areas is not None
            else existing.allowed_areas
            if existing is not None
            else self._explicit_repository_areas(raw)
        )
        forbidden_areas = (
            request.code_forbidden_areas
            if request.code_forbidden_areas is not None
            else existing.forbidden_areas
            if existing is not None
            else ()
        )
        existing_targets = (
            tuple(target.path for target in existing.required_targets)
            if existing is not None
            else ()
        )
        scope_unchanged = (
            existing is not None
            and tuple(exact_paths) == existing_targets
            and tuple(allowed_areas) == existing.allowed_areas
        )
        requested_verification = (
            request.code_verification_obligations
            if request.code_verification_obligations is not None
            else existing.verification_obligations
            if scope_unchanged
            else ()
        )
        try:
            return self.change_proposals.propose(
                RepositoryChangeProposalRequest(
                    work_id=work_id,
                    refined_code_intent=desired_outcome,
                    constraints=constraints,
                    engineering_resource_id=resource.id,
                    repository_identity=resource.repository_identity,
                    repository_location=resource.location_ref,
                    source_baseline_id=baseline_id,
                    source_ref=source_ref,
                    source_revision=source_revision,
                    explicit_targets=tuple(exact_paths),
                    explicit_allowed_areas=tuple(allowed_areas),
                    explicit_forbidden_areas=tuple(forbidden_areas),
                    requested_verification=requested_verification,
                )
            )
        except ValueError as error:
            raise ProductInvariantViolation(f"Invalid Code Change Proposal: {error}") from error

    @staticmethod
    def _admit_change_contract(
        proposal: RepositoryChangeProposal,
        *,
        desired_outcome: str,
        constraints: tuple[str, ...],
    ) -> CodeChangeContract:
        if proposal.unresolved_scope_questions:
            raise ProductInvariantViolation(
                "Change Proposal still requires refinement before Human admission"
            )
        targets = tuple(
            CodeChangeTarget(path=target.path, operation=target.operation)
            for target in proposal.required_targets
        )
        shape = (
            ChangeTargetShape.EXACT_AND_BOUNDED
            if targets and proposal.allowed_areas
            else ChangeTargetShape.EXACT_TARGET_SET
            if targets
            else ChangeTargetShape.BOUNDED_REPOSITORY_AREAS
        )
        return CodeChangeContract(
            target_shape=shape,
            engineering_resource_id=proposal.engineering_resource_id,
            repository_identity=proposal.repository_identity,
            source_baseline_id=proposal.source_baseline_id,
            source_revision=proposal.source_revision,
            desired_outcome=desired_outcome,
            constraints=constraints,
            exact_targets=targets,
            allowed_areas=proposal.allowed_areas,
            forbidden_areas=proposal.forbidden_areas,
            verification_obligations=proposal.verification_obligations,
            source_proposal_id=proposal.proposal_id,
            source_proposal_fingerprint=proposal.proposal_fingerprint,
        )

    @staticmethod
    def _explicit_repository_areas(raw: str) -> tuple[str, ...]:
        matches = re.findall(
            r"(?<![\w./*-])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*/\*\*)(?![\w/*-])",
            raw,
        )
        return tuple(dict.fromkeys(matches))

    @staticmethod
    def _explicit_repository_paths(raw: str) -> tuple[str, ...]:
        nested = re.findall(
            r"(?<![\w./-])((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+)(?![\w./*-])",
            raw,
        )
        roots = re.findall(
            r"(?<![\w./-])([A-Za-z0-9_-]+\.(?:py|toml|json|ya?ml))(?![\w./-])",
            raw,
            flags=re.IGNORECASE,
        )
        return tuple(
            dict.fromkeys(
                path.rstrip(".,:;。；")
                for path in (*nested, *roots)
                if "*" not in path
                and not (
                    path.startswith("docs/") and path.casefold().endswith(".md")
                )
            )
        )

    @classmethod
    def _default_code_verification_obligations(
        cls,
        exact_paths: tuple[str, ...],
        allowed_areas: tuple[str, ...],
    ) -> tuple[CodeVerificationObligation, ...]:
        obligations: list[CodeVerificationObligation] = [
            CodeVerificationObligation(kind=CodeVerificationKind.PATH_SCOPE),
            CodeVerificationObligation(kind=CodeVerificationKind.GIT_DIFF_CHECK),
        ]
        if any(path.endswith(".py") for path in exact_paths) or any(
            area.startswith(("src/", "tests/")) for area in allowed_areas
        ):
            obligations.append(
                CodeVerificationObligation(kind=CodeVerificationKind.PYTHON_COMPILE)
            )
        for path in exact_paths:
            if path.startswith("tests/") and path.endswith(".py"):
                obligations.append(
                    CodeVerificationObligation(
                        kind=CodeVerificationKind.PYTEST_TARGET,
                        target=path,
                    )
                )
            module = cls._python_module_for_path(path)
            if module is not None:
                obligations.append(
                    CodeVerificationObligation(
                        kind=CodeVerificationKind.IMPORT_CHECK,
                        target=module,
                    )
                )
        for area in allowed_areas:
            prefix = area[:-3].rstrip("/")
            if prefix.startswith("tests/"):
                obligations.append(
                    CodeVerificationObligation(
                        kind=CodeVerificationKind.PYTEST_TARGET,
                        target=prefix,
                    )
                )
        return tuple({item.identity: item for item in obligations}.values())

    @staticmethod
    def _python_module_for_path(path: str) -> str | None:
        if not path.startswith("src/") or not path.endswith(".py"):
            return None
        stem = path[4:-3].replace("/", ".")
        if stem.endswith(".__init__"):
            stem = stem[: -len(".__init__")]
        return stem or None

    @staticmethod
    def _code_verification_summary(contract: CodeChangeContract | None) -> str:
        if contract is None:
            return "Define a bounded Code Change Contract before Verification"
        return "Run admitted typed checks: " + ", ".join(
            contract.verification_identities
        )

    @staticmethod
    def _proposal_verification_summary(
        proposal: RepositoryChangeProposal | None,
    ) -> str:
        if proposal is None:
            return "Define a bounded Code Change Proposal before Verification"
        return "Proposed typed checks: " + ", ".join(
            item.identity for item in proposal.verification_obligations
        )

    @staticmethod
    def _code_change_objective(contract: CodeChangeContract) -> str:
        exact = "\n".join(
            f"- {target.operation.value} {target.path}"
            for target in contract.exact_targets
        )
        areas = "\n".join(f"- {area}" for area in contract.allowed_areas)
        return (
            f"Produce the admitted code change.\n"
            f"Desired outcome: {contract.desired_outcome}\n"
            f"Exact targets:\n{exact or '- None.'}\n"
            f"Bounded areas:\n{areas or '- None.'}"
        )

    @staticmethod
    def _is_too_broad(raw: str) -> bool:
        normalized = " ".join(raw.lower().split())
        broad_markers = (
            "entire platform",
            "complete platform",
            "all systems",
            "everything",
            "multiple repositories",
            "rewrite the whole",
        )
        return len(normalized) > 600 or any(item in normalized for item in broad_markers)

    @staticmethod
    def _artifact_target(work: WorkRecord) -> ArtifactTargetProposal | None:
        values = (
            work.expected_artifact_path,
            work.artifact_operation,
            work.artifact_placement_rationale,
            work.artifact_target_confidence,
            work.artifact_source_baseline_id,
            work.artifact_source_revision,
        )
        if any(item is None for item in values):
            return None
        return ArtifactTargetProposal(
            path=work.expected_artifact_path or "",
            operation=work.artifact_operation or ArtifactTargetOperation.CREATE,
            placement_rationale=work.artifact_placement_rationale or "",
            confidence=(
                work.artifact_target_confidence or ArtifactTargetConfidence.LOW
            ),
            source_baseline_id=work.artifact_source_baseline_id,
            source_revision=work.artifact_source_revision or "",
        )

    @classmethod
    def _required_artifact_target(cls, work: WorkRecord) -> ArtifactTargetProposal:
        target = cls._artifact_target(work)
        if target is None:
            raise ProductInvariantViolation(
                "Work requires an exact Human-visible Artifact Target before approval"
            )
        return target

    @staticmethod
    def _required_production_plan(work: WorkRecord) -> ProductionPlanProposal:
        if work.production_plan is None:
            raise ProductInvariantViolation(
                "Work requires a Human-visible Production Plan before approval"
            )
        return work.production_plan

    @classmethod
    def _artifact_target_proposal(
        cls,
        *,
        raw: str,
        explicit_path: str | None,
        resource: EngineeringResourceRecord,
        baseline_id: UUID,
        source_revision: str,
    ) -> ArtifactTargetProposal | None:
        repository = Path(resource.location_ref).resolve()
        paths = cls._baseline_paths(repository, source_revision)
        path: str | None = None
        rationale: str | None = None
        confidence = ArtifactTargetConfidence.LOW
        if explicit_path is not None:
            path = cls._validate_artifact_path(explicit_path)
            rationale = "Human-selected repository-relative documentation target."
            confidence = ArtifactTargetConfidence.HIGH
        else:
            match = re.search(
                r"(?<![\w.-])((?:docs/)[A-Za-z0-9_./-]+\.md)(?![\w.-])",
                raw,
                flags=re.IGNORECASE,
            )
            if match:
                path = cls._validate_artifact_path(match.group(1))
                rationale = "The requirement names this exact documentation path."
                confidence = ArtifactTargetConfidence.HIGH
            else:
                normalized = " ".join(raw.casefold().split())
                if "production orchestration lite" in normalized:
                    path = "docs/architecture/production-orchestration-lite.md"
                    rationale = (
                        "Architecture terminology and the baseline documentation tree "
                        "place this product/architecture document under docs/architecture/."
                    )
                    confidence = ArtifactTargetConfidence.HIGH
                else:
                    folder = cls._documentation_folder(normalized, paths)
                    slug = cls._document_slug(raw)
                    if folder is not None and slug:
                        path = f"{folder}/{slug}.md"
                        rationale = (
                            f"The exact Source Baseline contains {folder}/ and the "
                            "requirement category maps to that documentation area."
                        )
                        confidence = ArtifactTargetConfidence.MEDIUM
        if path is None:
            return None
        operation = (
            ArtifactTargetOperation.UPDATE
            if path in paths
            else ArtifactTargetOperation.CREATE
        )
        return ArtifactTargetProposal(
            path=path,
            operation=operation,
            placement_rationale=rationale or "Repository-aware documentation placement.",
            confidence=confidence,
            source_baseline_id=baseline_id,
            source_revision=source_revision,
        )

    @staticmethod
    def _baseline_paths(repository: Path, source_revision: str) -> frozenset[str]:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "ls-tree",
                "-r",
                "--name-only",
                source_revision,
                "--",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise ProductInvariantViolation(
                "Exact Source Baseline repository structure is unavailable"
            )
        return frozenset(result.stdout.splitlines())

    @staticmethod
    def _documentation_folder(normalized: str, paths: frozenset[str]) -> str | None:
        directories = {
            str(PurePosixPath(path).parent)
            for path in paths
            if path.startswith("docs/")
        }
        categories = (
            ("docs/roadmap", ("roadmap", "migration plan", "delivery plan")),
            ("docs/evidence", ("evidence", "finding", "benchmark", "test report")),
            (
                "docs/architecture",
                ("architecture", "principle", "production orchestration", "product"),
            ),
        )
        for folder, markers in categories:
            if folder in directories and any(marker in normalized for marker in markers):
                return folder
        if "docs" in directories and any(
            marker in normalized
            for marker in ("document", "documentation", "markdown", "work result", "product result")
        ):
            return "docs"
        return None

    @staticmethod
    def _document_slug(raw: str) -> str | None:
        first = next((line.strip() for line in raw.splitlines() if line.strip()), "")
        words = re.findall(r"[a-z0-9]+", first.casefold())
        ignored = {
            "a", "an", "the", "create", "add", "write", "produce", "update",
            "document", "documentation", "markdown", "governed", "admitted",
        }
        selected = [word for word in words if word not in ignored][:8]
        return "-".join(selected) or None

    @staticmethod
    def _validate_artifact_path(raw_path: str) -> str:
        value = raw_path.strip()
        if "\\" in value:
            raise ProductInvariantViolation("Artifact Target must use POSIX separators")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value in {"", "."}:
            raise ProductInvariantViolation(
                "Artifact Target must be a safe repository-relative path"
            )
        if any(part.startswith(".") for part in path.parts):
            raise ProductInvariantViolation(
                "Artifact Target cannot address hidden or Git-internal paths"
            )
        if not value.startswith("docs/") or path.suffix.casefold() != ".md":
            raise ProductInvariantViolation(
                "MVP documentation Artifact Target must be a Markdown path under docs/"
            )
        return str(path)

    @staticmethod
    def _extract_constraints(raw: str) -> tuple[str, ...]:
        normalized = " ".join(raw.casefold().split())
        constraints: list[str] = []
        if "do not expand" in normalized and any(
            marker in normalized for marker in ("invent", "introduce", "new capabilities")
        ):
            constraints.append(
                "Do not expand or invent capabilities beyond the already accepted design."
            )
        marker = re.compile(
            r"\b(do not|must not|only|must|keep|without|do not expand|do not introduce)\b",
            flags=re.IGNORECASE,
        )
        chinese_markers = (
            "不要",
            "不得",
            "不应",
            "禁止",
            "必须",
            "只能",
            "仅限",
        )
        fragments = tuple(
            " ".join(fragment.split()).strip(" -:")
            for fragment in re.split(r"[\n.;。；]+", raw)
        )
        has_explicit_chinese_instruction = any(
            any(chinese_marker in fragment for chinese_marker in chinese_markers)
            for fragment in fragments
        )
        for candidate in fragments:
            chinese_instruction = any(
                chinese_marker in candidate for chinese_marker in chinese_markers
            )
            bounded_reuse = (
                "尽量复用" in candidate and has_explicit_chinese_instruction
            )
            if candidate and (
                marker.search(candidate) or chinese_instruction or bounded_reuse
            ):
                constraints.append(candidate)
        return tuple(dict.fromkeys(constraints))

    @staticmethod
    def _merge_constraints(*groups: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                item.strip()
                for group in groups
                for item in group
                if item.strip()
            )
        )

    @staticmethod
    def _artifact_objective(contract: ArtifactContract) -> str:
        constraint_text = "\n".join(f"- {item}" for item in contract.constraints)
        return (
            f"{contract.operation.value} the exact artifact {contract.artifact_path}.\n"
            f"Intended outcome: {contract.expected_outcome}\n"
            f"Constraints:\n{constraint_text or '- None beyond the admitted contract.'}"
        )

    @staticmethod
    def _fingerprint(value: object) -> str:
        canonical = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        return sha256(canonical).hexdigest()
