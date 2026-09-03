"""Goal-centric MVP application flow composed over governed Runtime services."""

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.completion import CompletionService
from spg.application.execution import ExecutionService
from spg.application.governance import CandidateGovernanceService
from spg.application.integration import RepositoryIntegrationService
from spg.application.preparation import PreparationService
from spg.application.runtime import RuntimeService
from spg.application.runtime_commit import RuntimeCommitService
from spg.application.verification import VerificationService
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
from spg.domain.product import (
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
        executor_binding: ExecutorBinding = DEFAULT_BINDING,
    ) -> None:
        self.database = database
        self.workspace_root = (workspace_root or Path(".spg/workspaces")).resolve()
        self.executor = executor
        self.verifier = verifier
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
                    "verification_expectation": None,
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
            expected_artifact_path = (
                request.expected_artifact_path
                or f"docs/work-{work.id.hex[:12]}.md"
            )
            verification = (
                request.verification_expectation
                or "Verify the requested outcome against independent repository Reality"
            )
            needs_refinement = self._is_too_broad(work.raw_user_requirement)
            condition = (
                WorkCondition.NEEDS_REFINEMENT
                if needs_refinement
                else WorkCondition.AWAITING_APPROVAL
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
                    "constraints": list(request.constraints),
                    "condition": condition.value,
                    "scope_summary": scope_summary,
                    "production_objective": objective,
                    "expected_artifact_path": expected_artifact_path,
                    "verification_expectation": verification,
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

        baseline = self.runtime.current_baseline()
        if (
            baseline.repository_identity != resource.repository_identity
            or baseline.repository_ref != resource.authoritative_ref
        ):
            raise ProductInvariantViolation(
                "Engineering Resource does not match current governed Baseline"
            )
        spine = self.runtime.create_initial_runtime_spine(
            InitialRunRequest(
                intent_ref=f"work:{work.id}",
                goal=work.desired_outcome or work.refined_title or "Governed Work",
                production_horizon=ProductionHorizon.DOCUMENTATION,
                initial_work_unit_objective=(
                    work.production_objective or work.desired_outcome or "Produce Work"
                ),
                completion_contract=CompletionContract(
                    required_outputs=(work.expected_artifact_path or "docs/work-output.md",),
                    required_changes=(work.expected_artifact_path or "docs/work-output.md",),
                    verification_obligations=(
                        work.verification_expectation
                        or "Verify independent repository Reality",
                    ),
                ),
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
                {"condition": WorkCondition.READY.value, "updated_at": timestamp},
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
            tags=work.tags,
            engineering_scope=scope,
            status=status,
            current_production_step=step,
            most_recent_meaningful_event=summary.latest_event or event,
            what_happens_next=next_action,
            human_attention_required=status
            in {WorkStatus.AWAITING_APPROVAL, WorkStatus.NEEDS_ATTENTION, WorkStatus.BLOCKED},
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
            return (
                WorkStatus.NEEDS_REFINEMENT,
                "WORK_REFINEMENT",
                "REFINEMENT_REQUIRED",
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
        ):
            return (
                WorkStatus.BLOCKED,
                "EXECUTION_STOPPED",
                "PROVIDER_OUTCOME_UNKNOWN_PRODUCTION_NONE",
                "Execution stopped before Provider completion. Architecture/Operator review required.",
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
    def _fingerprint(value: object) -> str:
        canonical = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        return sha256(canonical).hexdigest()
