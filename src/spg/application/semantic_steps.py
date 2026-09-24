"""Governed provider-neutral execution for bounded semantic Steering Steps."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
import subprocess
from uuid import UUID, uuid4

from spg.application.planning import ProductionPlanningService
from spg.application.assets import RepositoryAssetService
from spg.application.guided_design import GuidedDesignApplicationService
from spg.application.refinement import RepositoryChangeProposalService
from spg.application.runtime import RuntimeService
from spg.application.steering_decision import PlanFrameAssembler
from spg.domain.change import ProductionTargetKind
from spg.domain.planning import (
    OnePwuFitClassification,
    ProductionPlanArtifactTarget,
    ProductionPlanProposal,
    ProductionPlanningRequest,
)
from spg.domain.product import (
    ArtifactTargetConfidence,
    EngineeringScopeCondition,
    ProductInvariantViolation,
    WorkCondition,
)
from spg.domain.refinement import (
    RepositoryChangeProposal,
    RepositoryChangeProposalRequest,
)
from spg.domain.steering import (
    RealityReference,
    RealityReferenceKind,
    SemanticContextMaterial,
    SemanticGovernanceDecision,
    SemanticStepCapability,
    SemanticStepInput,
    SemanticStepResultCandidate,
    SemanticStepResultRecord,
    StaleSemanticStepCandidate,
    SteeringAuthorityAssessment,
    SteeringInvariantViolation,
    SteeringStepState,
    SteeringStepType,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.steering_store import SteeringStore
from spg.application.work import WorkApplicationService
from spg.providers.repository_change_proposal import (
    RepositoryAwareChangeProposalProvider,
)
from spg.providers.rule_based_planner import RuleBasedProductionPlanner


MAX_TREE_PATHS = 1_000
MAX_CONTEXT_FILES = 8
MAX_CONTEXT_CHARS_PER_FILE = 8_000
MAX_CONTEXT_CHARS_TOTAL = 24_000


class SemanticStepApplicationService:
    """Validate and admit semantic provider output as reconstructable Reality."""

    def __init__(
        self,
        database: Database,
        capability: SemanticStepCapability | None,
        *,
        work_service: WorkApplicationService | None = None,
        repository_assets: RepositoryAssetService | None = None,
    ) -> None:
        self.database = database
        self.capability = capability
        self.frames = PlanFrameAssembler(database)
        self.runtime = RuntimeService(database)
        self.planning = ProductionPlanningService(RuleBasedProductionPlanner())
        self.change_proposals = RepositoryChangeProposalService(
            RepositoryAwareChangeProposalProvider()
        )
        self.guided_design = GuidedDesignApplicationService(database)
        self.work_service = work_service
        self.repository_assets = repository_assets

    def assemble_input(self, work_id: UUID) -> SemanticStepInput:
        # A Step result is evidence for the following decision, not an input to
        # recompute that same Step. Excluding results emitted by the CURRENT
        # Step keeps its provider basis stable after the first admission.
        frame = self.frames.assemble(
            work_id,
            exclude_current_step_semantic_results=True,
        )
        step = frame.reconstruction.current_step
        if step is None or step.type not in {
            SteeringStepType.DESIGN,
            SteeringStepType.REFINE,
        }:
            raise SteeringInvariantViolation(
                "Semantic execution requires a current DESIGN or REFINE Step"
            )
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            work = product.work(work_id)
            scope = product.scope_for_work(work_id)
            if work is None or scope is None:
                raise ProductInvariantViolation("Semantic Work authority is incomplete")
            work_revision = product.current_work_reality_revision(work.id)
            if (
                work.condition is not WorkCondition.READY
                or scope.condition is not EngineeringScopeCondition.ADMITTED
            ):
                raise SteeringInvariantViolation(
                    "Semantic execution requires admitted Work and Scope Reality"
                )
            resource = product.resource_for_work(work_id)
            governance = tuple(
                SemanticGovernanceDecision(
                    id=record.id,
                    decision_type=record.decision_type,
                    authority_identity=record.authority_identity,
                    scope=record.scope,
                    rationale=record.rationale,
                )
                for record in runtime.governance_for_subject(str(work_id))
            )
        baseline = None if resource is None else self.runtime.current_baseline(
            repository_identity=resource.repository_identity, repository_ref=resource.authoritative_ref)
        repository = None if resource is None else Path(resource.location_ref).resolve()
        source_tree = None
        paths = ()
        materials = ()
        if baseline is not None:
            source_tree = self._git(repository, "rev-parse", f"{baseline.repository_revision}^{{tree}}")
            paths = tuple(self._git(repository, "ls-tree", "-r", "--name-only", baseline.repository_revision).splitlines()[:MAX_TREE_PATHS])
            materials = self._context_materials(repository, baseline.repository_revision,
                tuple(item.repository_relative_path for item in resource.context_references))
        refs = tuple(item.reference for item in frame.basis.resolved_reality)
        next_step = frame.reconstruction.next_step
        design_context = self.guided_design.semantic_context(work.id, step.id)
        guided_design = self.guided_design.get_optional(work.id)
        approved_design_artifacts = (
            self.guided_design.approved_design_artifact_references(work.id)
            if guided_design is not None else ()
        )
        required_intermediate_artifacts = (
            ("APPROVED_DESIGN_ARTIFACT",)
            if guided_design is not None
            and step.type is SteeringStepType.DESIGN
            and next_step is not None
            and next_step.type is SteeringStepType.PRODUCE
            and not approved_design_artifacts
            else ()
        )
        production_proposal_required = bool(
            step.type is SteeringStepType.DESIGN
            and next_step is not None
            and next_step.type is SteeringStepType.PRODUCE
            and (
                work.production_plan is None
                or design_context is None
                or (
                    work.production_plan.target_kind is ProductionTargetKind.DOCUMENTATION_WORK
                    and approved_design_artifacts
                )
            )
        )
        from spg.application.connectors import ConnectorResolver
        from spg.domain.connectors import ConnectorAvailability

        executable_reality = ConnectorResolver(self.database).visible_capabilities(
            work.id,
            "system" if work_revision is None else work_revision.admitted_by,
        )
        return SemanticStepInput(
            work_id=work.id,
            desired_outcome=work.desired_outcome or work.raw_user_requirement,
            constraints=work.constraints,
            work_context_facts=(
                () if work_revision is None else work_revision.context_facts
            ),
            work_requests=(
                () if work_revision is None else work_revision.requests
            ),
            steering_plan_revision_id=frame.reconstruction.active_revision.revision.id,
            step=step,
            basis_fingerprint=frame.basis.fingerprint,
            engineering_resource_id=None if resource is None else resource.id,
            engineering_scope_id=scope.id,
            engineering_scope_summary=scope.summary,
            engineering_scope_fingerprint=scope.fingerprint,
            repository_identity=None if resource is None else resource.repository_identity,
            repository_location=None if repository is None else str(repository),
            repository_ref=None if resource is None else resource.authoritative_ref,
            source_baseline_id=None if baseline is None else baseline.id,
            source_revision=None if baseline is None else baseline.repository_revision,
            source_tree=source_tree,
            reality_refs=refs,
            governance_decisions=governance,
            repository_tree_paths=paths,
            context_materials=materials,
            design_context=design_context,
            production_proposal_required=production_proposal_required,
            required_intermediate_artifacts=required_intermediate_artifacts,
            approved_artifact_references=approved_design_artifacts,
            available_executable_capabilities=tuple(
                item.capability_id for item in executable_reality
                if item.availability is ConnectorAvailability.AVAILABLE
            ),
            unavailable_executable_capabilities=tuple(
                item.capability_id for item in executable_reality
                if item.availability is not ConnectorAvailability.AVAILABLE
            ),
        )

    def execute(self, work_id: UUID) -> SemanticStepResultRecord:
        semantic_input = self.assemble_input(work_id)
        if (
            semantic_input.engineering_resource_id is None
            and semantic_input.design_context is not None
            and semantic_input.design_context.get("production_transition_issue") is True
            and self.work_service is not None
            and self.repository_assets is not None
        ):
            self.repository_assets.ensure_managed_execution_workspace(
                self.work_service,
                work_id,
            )
            semantic_input = self.assemble_input(work_id)
        existing = self.result_for_step(semantic_input.step.id)
        if (
            existing is not None
            and (
                existing.basis_fingerprint == semantic_input.basis_fingerprint
                or self._result_still_current(existing, semantic_input)
            )
        ):
            return existing
        if self.capability is None:
            raise SteeringInvariantViolation(
                "No Semantic Step capability is configured for DESIGN/REFINE"
            )
        candidate = self.capability.execute(semantic_input)
        return self.admit(semantic_input, candidate)

    @staticmethod
    def _result_still_current(
        result: SemanticStepResultRecord,
        semantic_input: SemanticStepInput,
    ) -> bool:
        durable_basis_kinds = {
            RealityReferenceKind.WORK_REALITY_REVISION,
            RealityReferenceKind.TRUSTED_BASELINE,
        }
        result_basis = {
            reference
            for reference in result.evidence_refs
            if reference.kind in durable_basis_kinds
        }
        current_basis = {
            reference
            for reference in semantic_input.reality_refs
            if reference.kind in durable_basis_kinds
        }
        return current_basis == result_basis

    def admit(
        self,
        semantic_input: SemanticStepInput,
        candidate: SemanticStepResultCandidate,
    ) -> SemanticStepResultRecord:
        fresh = self.assemble_input(semantic_input.work_id)
        if (
            fresh.steering_plan_revision_id != semantic_input.steering_plan_revision_id
            or fresh.step.id != semantic_input.step.id
            or fresh.step.state is not SteeringStepState.CURRENT
            or fresh.basis_fingerprint != semantic_input.basis_fingerprint
            or fresh.source_baseline_id != semantic_input.source_baseline_id
            or fresh.source_revision != semantic_input.source_revision
            or fresh.source_tree != semantic_input.source_tree
        ):
            raise StaleSemanticStepCandidate(
                "Semantic Step input is stale against current governed Reality"
            )
        if (
            candidate.work_id != fresh.work_id
            or candidate.steering_plan_revision_id != fresh.steering_plan_revision_id
            or candidate.step_id != fresh.step.id
            or candidate.step_type is not fresh.step.type
            or candidate.basis_fingerprint != fresh.basis_fingerprint
        ):
            raise StaleSemanticStepCandidate(
                "Semantic result candidate does not bind the exact current Step basis"
            )
        if not set(candidate.evidence_refs) <= set(fresh.reality_refs):
            raise SteeringInvariantViolation(
                "Semantic result references Reality outside its governed input"
            )
        if fresh.design_context is not None:
            production_transition_issue = bool(
                fresh.design_context.get("production_transition_issue")
            )
            if candidate.proposed_production is not None and not production_transition_issue:
                raise SteeringInvariantViolation(
                    "An intermediate guided design issue cannot form production"
                )
            if (
                candidate.completion_claimed
                and production_transition_issue
                and candidate.proposed_production is None
            ):
                raise SteeringInvariantViolation(
                    "Implementation-readiness design requires a reviewable production proposal"
                )
        if (
            fresh.production_proposal_required
            and candidate.completion_claimed
            and candidate.proposed_production is None
        ):
            raise SteeringInvariantViolation(
                "DESIGN cannot close toward PRODUCE without a current production proposal"
            )
        if (
            fresh.production_proposal_required
            and fresh.approved_artifact_references
            and candidate.proposed_production is not None
            and candidate.proposed_production.target_kind
            is ProductionTargetKind.DOCUMENTATION_WORK
        ):
            raise SteeringInvariantViolation(
                "Approved intermediate design cannot replace the remaining code implementation"
            )
        if (
            "APPROVED_DESIGN_ARTIFACT" in fresh.required_intermediate_artifacts
            and candidate.proposed_production is not None
            and candidate.proposed_production.target_kind is ProductionTargetKind.CODE_WORK
        ):
            raise SteeringInvariantViolation(
                "Implementation cannot be proposed before a design artifact is "
                "produced, reviewed, and committed to current Work Reality"
            )
        if fresh.design_context is not None and candidate.proposed_production is not None:
            with self.database.unit_of_work() as design_uow:
                design_store = SteeringStore(design_uow.session)
                records = [design_store.semantic_result(ref.identity) for ref in fresh.reality_refs
                           if ref.kind is RealityReferenceKind.SEMANTIC_RESULT]
            latest = {}
            for record in sorted((item for item in records if item is not None and item.completion_satisfied), key=lambda item: item.created_at):
                latest[record.step_id] = record
            sections = [f"Design result {item.id}: {item.bounded_summary}\n" + "\n".join(item.decisions) for item in latest.values()]
            sections.append(candidate.bounded_summary + "\n" + "\n".join(candidate.decisions))
            objective = candidate.proposed_production.objective + "\n\nDesign baseline to materialize (admitted source results):\n" + "\n\n".join(sections)
            candidate = candidate.model_copy(update={"proposed_production": candidate.proposed_production.model_copy(update={"objective": objective})})

        new_constraints = set(candidate.derived_constraints) - set(fresh.constraints)
        if new_constraints and candidate.authority_assessment is (
            SteeringAuthorityAssessment.WITHIN_AUTHORITY
        ):
            raise SteeringInvariantViolation(
                "Semantic result cannot silently add Human-approved constraints"
            )

        completion_satisfied = bool(
            candidate.completion_claimed
            and candidate.authority_assessment
            is SteeringAuthorityAssessment.WITHIN_AUTHORITY
            and not candidate.unresolved_questions
            and candidate.decisions
            and candidate.evidence_refs
        )
        production_plan: ProductionPlanProposal | None = None
        change_proposal: RepositoryChangeProposal | None = None
        if completion_satisfied and candidate.proposed_production is not None:
            production_plan, change_proposal = self._materialize_production_plan(
                fresh,
                candidate,
            )

        timestamp = datetime.now(UTC)
        result_id = uuid4()
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            store = SteeringStore(unit_of_work.session)
            step = store.step(fresh.step.id)
            revision = store.revision(fresh.steering_plan_revision_id)
            existing = store.latest_semantic_result_for_step(fresh.step.id)
            if (
                existing is not None
                and existing.basis_fingerprint == fresh.basis_fingerprint
            ):
                return existing
            if (
                step is None
                or revision is None
                or step.state is not SteeringStepState.CURRENT
                or step.steering_plan_revision_id != revision.id
            ):
                raise StaleSemanticStepCandidate(
                    "Semantic Step changed before result admission"
                )
            for reference in candidate.evidence_refs:
                if not store.reality_reference_exists(reference):
                    raise SteeringInvariantViolation(
                        "Semantic result evidence reference no longer exists"
                    )
            store.insert_semantic_result(
                {
                    "id": result_id,
                    "work_id": fresh.work_id,
                    "steering_plan_revision_id": fresh.steering_plan_revision_id,
                    "step_id": fresh.step.id,
                    "step_type": fresh.step.type.value,
                    "basis_fingerprint": fresh.basis_fingerprint,
                    "result_kind": candidate.result_kind.value,
                    "bounded_summary": candidate.bounded_summary,
                    "decisions": list(candidate.decisions),
                    "derived_constraints": list(candidate.derived_constraints),
                    "evidence_refs": [
                        item.model_dump(mode="json")
                        for item in candidate.evidence_refs
                    ],
                    "unresolved_questions": list(candidate.unresolved_questions),
                    "authority_assessment": candidate.authority_assessment.value,
                    "human_attention_recommendation": (
                        candidate.human_attention_recommendation
                    ),
                    "proposed_production": (
                        None
                        if candidate.proposed_production is None
                        else candidate.proposed_production.model_dump(mode="json")
                    ),
                    "reasoning_provider_identity": (
                        candidate.reasoning_provider_identity
                    ),
                    "completion_satisfied": completion_satisfied,
                    "material_direction_fingerprint": (
                        candidate.material_direction_fingerprint
                    ),
                    "created_at": timestamp,
                }
            )
            if production_plan is not None:
                proposal = candidate.proposed_production
                assert proposal is not None
                artifact = (
                    proposal.artifact_targets[0]
                    if proposal.target_kind is ProductionTargetKind.DOCUMENTATION_WORK
                    else None
                )
                product.update_work(
                    fresh.work_id,
                    {
                        "production_objective": proposal.objective,
                        "expected_artifact_path": (
                            None if artifact is None else artifact.path
                        ),
                        "artifact_operation": (
                            None if artifact is None else artifact.operation.value
                        ),
                        "artifact_placement_rationale": (
                            None
                            if artifact is None
                            else "Proposed by governed semantic DESIGN Reality"
                        ),
                        "artifact_target_confidence": (
                            None
                            if artifact is None
                            else ArtifactTargetConfidence.HIGH.value
                        ),
                        "artifact_source_baseline_id": (
                            None if artifact is None else fresh.source_baseline_id
                        ),
                        "artifact_source_revision": (
                            None if artifact is None else fresh.source_revision
                        ),
                        "verification_expectation": (
                            proposal.verification_expectation
                        ),
                        "code_change_proposal": (
                            None
                            if change_proposal is None
                            else change_proposal.model_dump(mode="json")
                        ),
                        "production_plan_proposal": production_plan.model_dump(
                            mode="json"
                        ),
                        "updated_at": timestamp,
                    },
                )
            unit_of_work.commit()
        result = self.result(result_id)
        if result is None:
            raise SteeringInvariantViolation("Semantic Step Result was not constructed")
        return result

    def result(self, result_id: UUID) -> SemanticStepResultRecord | None:
        with self.database.unit_of_work() as unit_of_work:
            return SteeringStore(unit_of_work.session).semantic_result(result_id)

    def result_for_step(self, step_id: UUID) -> SemanticStepResultRecord | None:
        with self.database.unit_of_work() as unit_of_work:
            return SteeringStore(unit_of_work.session).latest_semantic_result_for_step(
                step_id
            )

    def _materialize_production_plan(
        self,
        semantic_input: SemanticStepInput,
        candidate: SemanticStepResultCandidate,
    ) -> tuple[ProductionPlanProposal, RepositoryChangeProposal | None]:
        if semantic_input.engineering_resource_id is None or semantic_input.source_baseline_id is None:
            raise SteeringInvariantViolation(
                "Production requires an observed execution workspace; user repository binding is optional"
            )
        proposal = candidate.proposed_production
        assert proposal is not None
        change_proposal = None
        if proposal.target_kind is ProductionTargetKind.CODE_WORK:
            change_proposal = self.change_proposals.propose(
                RepositoryChangeProposalRequest(
                    work_id=semantic_input.work_id,
                    refined_code_intent="\n".join(
                        (candidate.bounded_summary, *candidate.decisions)
                    ),
                    constraints=semantic_input.constraints,
                    engineering_resource_id=semantic_input.engineering_resource_id,
                    repository_identity=semantic_input.repository_identity,
                    repository_location=semantic_input.repository_location,
                    source_baseline_id=semantic_input.source_baseline_id,
                    source_ref=semantic_input.repository_ref,
                    source_revision=semantic_input.source_revision,
                    explicit_targets=proposal.code_targets,
                    explicit_allowed_areas=proposal.allowed_areas,
                    explicit_forbidden_areas=proposal.forbidden_areas,
                )
            )
        plan = self.planning.propose(
            ProductionPlanningRequest(
                work_id=semantic_input.work_id,
                target_kind=proposal.target_kind,
                admitted_requirement=semantic_input.desired_outcome,
                desired_outcome=semantic_input.desired_outcome,
                production_objective=proposal.objective,
                artifact_targets=proposal.artifact_targets,
                change_proposal=change_proposal,
                constraints=semantic_input.constraints,
                verification_expectation=proposal.verification_expectation,
                engineering_scope_summary=semantic_input.engineering_scope_summary,
                engineering_resource_id=semantic_input.engineering_resource_id,
                repository_identity=semantic_input.repository_identity,
                source_baseline_id=semantic_input.source_baseline_id,
                source_revision=semantic_input.source_revision,
                context_references=tuple(
                    item.repository_relative_path
                    for item in semantic_input.context_materials
                ),
            )
        )
        if plan.fit_classification is not OnePwuFitClassification.ONE_PWU_FIT:
            raise SteeringInvariantViolation(
                "Semantic production proposal does not satisfy PLAN-1B ONE_PWU_FIT"
            )
        return plan, change_proposal

    @classmethod
    def _context_materials(
        cls,
        repository: Path,
        revision: str,
        paths: tuple[str, ...],
    ) -> tuple[SemanticContextMaterial, ...]:
        results: list[SemanticContextMaterial] = []
        total = 0
        for path in tuple(dict.fromkeys(paths))[:MAX_CONTEXT_FILES]:
            completed = subprocess.run(
                ["git", "-C", str(repository), "show", f"{revision}:{path}"],
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                continue
            remaining = MAX_CONTEXT_CHARS_TOTAL - total
            if remaining <= 0:
                break
            content = completed.stdout[: min(MAX_CONTEXT_CHARS_PER_FILE, remaining)]
            total += len(content)
            results.append(
                SemanticContextMaterial(
                    repository_relative_path=path,
                    content=content,
                    content_fingerprint=sha256(content.encode("utf-8")).hexdigest(),
                )
            )
        return tuple(results)

    @staticmethod
    def _git(repository: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(repository), *args],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise SteeringInvariantViolation(
                "Exact-baseline repository material is unavailable for semantic execution"
            )
        return completed.stdout.strip()
