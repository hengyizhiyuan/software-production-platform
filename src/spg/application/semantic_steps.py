"""Governed provider-neutral execution for bounded semantic Steering Steps."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from time import monotonic
from uuid import UUID, uuid4

from pydantic import ValidationError

from spg.application.planning import ProductionPlanningService
from spg.application.assets import RepositoryAssetService
from spg.application.guided_design import GuidedDesignApplicationService
from spg.application.intent_realization import current_dependent_analysis_requests
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
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.persistence.interaction_store import InteractionStore
from spg.domain.refinement_contract import RefinementSignalKind
from spg.application.work import WorkApplicationService
from spg.providers.repository_change_proposal import (
    RepositoryAwareChangeProposalProvider,
)
from spg.providers.rule_based_planner import RuleBasedProductionPlanner


def bind_exact_human_document_identifiers(
    objective: str, verification: str, human_request: str,
) -> tuple[str, str]:
    """Carry literal Human document identifiers into the admitted Work contract."""
    wording = human_request.casefold()
    if not ("identifier" in wording and ("literal" in wording or "exact" in wording)):
        return objective, verification
    markers = tuple(dict.fromkeys(re.findall(
        r"(?<![0-9a-fA-F])(?:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|"
        r"[0-9a-fA-F]{40})(?![0-9a-fA-F])", human_request)))
    if not markers:
        return objective, verification
    objective += " Exact Human-supplied lineage identifiers: " + "; ".join(markers) + "."
    verification += (" Verify that all exact lineage identifiers in the admitted "
                     "Work objective appear verbatim in the document.")
    return objective, verification


MAX_TREE_PATHS = 1_000
MAX_CONTEXT_FILES = 24
MAX_CONTEXT_CHARS_PER_FILE = 8_000
MAX_CONTEXT_CHARS_TOTAL = 64_000
REFINABLE_ADMISSION_FEEDBACK = (
    "ATTENTION_NOT_QUALIFIED",
    "Semantic result references Reality outside its governed input",
    "An intermediate guided design issue cannot form production",
    "Implementation-readiness design requires a reviewable production proposal",
    "DESIGN cannot close toward PRODUCE without a current production proposal",
    "Approved intermediate design cannot replace the remaining code implementation",
    "Implementation cannot be proposed before a design artifact is produced",
    "Semantic production proposal does not satisfy PLAN-1B ONE_PWU_FIT",
    "Semantic production proposal has no executable PWU boundary",
    "Task Contract candidate failed validation",
)


def _semantic_feedback(value: str) -> str:
    """Retain the exact bounded feedback sent to repair, excluding secrets."""
    from spg.providers.verification_receipts import _safe_value
    return _safe_value(value)[:2000]


def _semantic_failure(error: Exception | None) -> dict[str, object] | None:
    """Classify owner failure without serializing arbitrary exception prose."""
    if error is None:
        return None
    from spg.providers.fulfillment_candidate import provider_failure_observation
    provider = provider_failure_observation(error)
    result = {"error_type": type(error).__name__, "code": "SEMANTIC_REFINEMENT_FAILED"}
    if provider is not None:
        result.update(code="SEMANTIC_PROVIDER_FAILURE", provider=provider)
        return result
    validation = error if isinstance(error, ValidationError) else error.__cause__
    if isinstance(validation, ValidationError):
        result.update(code="SEMANTIC_CANDIDATE_SCHEMA_REJECTED", field_issues=[{
            "location": _semantic_feedback(".".join(str(part) for part in issue["loc"])),
            "type": _semantic_feedback(issue["type"]),
        } for issue in validation.errors(include_input=False, include_context=False)[:32]])
        return result
    if isinstance(error, StaleSemanticStepCandidate):
        result["code"] = "SEMANTIC_BASIS_CHANGED"
        return result
    if isinstance(error, (SteeringInvariantViolation, ValueError)):
        result["code"] = "SEMANTIC_ADMISSION_REJECTED" if isinstance(error, SteeringInvariantViolation) else "SEMANTIC_CANDIDATE_VALUE_REJECTED"
        text = str(error)
        machine = re.match(r"([A-Z][A-Z0-9_]{1,79})(?::|$)", text)
        if machine is not None:
            result["validator_code"] = _semantic_feedback(machine.group(1))
            result["safe_reason"] = _semantic_feedback(text)
        elif text.startswith(REFINABLE_ADMISSION_FEEDBACK):
            result["safe_reason"] = _semantic_feedback(text)
    return result


def _semantic_candidate_identity(candidate: SemanticStepResultCandidate | None):
    if candidate is None:
        return None
    payload = candidate.model_dump(mode="json")
    return {"candidate_fingerprint": sha256(json.dumps(payload, sort_keys=True,
        ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "work_id": str(candidate.work_id), "steering_plan_revision_id": str(candidate.steering_plan_revision_id),
        "step_id": str(candidate.step_id), "step_type": candidate.step_type.value,
        "basis_fingerprint": candidate.basis_fingerprint}


def _semantic_failure_message(error: Exception) -> str:
    diagnosis = _semantic_failure(error)
    return str(diagnosis.get("safe_reason") or diagnosis["code"])


class SemanticStepRefinementExhausted(SteeringInvariantViolation):
    """Same-basis owner validation exhausted its admissible correction budget."""


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
        self.planning = ProductionPlanningService(RuleBasedProductionPlanner(), database=database)
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
            semantic_ir = None
            intent_revision = work_revision
            seen_intent_revisions = set()
            while intent_revision is not None and intent_revision.id not in seen_intent_revisions:
                seen_intent_revisions.add(intent_revision.id)
                source_assessment = (InteractionStore(unit_of_work.session).assessment(intent_revision.source_assessment_id)
                    if intent_revision.source_assessment_id else None)
                if source_assessment is not None and source_assessment.semantic_ir is not None:
                    if semantic_ir is None or source_assessment.semantic_ir.current_production:
                        semantic_ir = source_assessment.semantic_ir
                    if semantic_ir.current_production:
                        break
                intent_revision = product.work_reality_revision(intent_revision.previous_revision_id) if intent_revision.previous_revision_id else None
            human_records = () if work_revision is None else tuple(
                record.content for identity in work_revision.source_record_ids
                if (record := InteractionStore(unit_of_work.session).record(identity)) is not None
                and record.actor.value == "HUMAN")
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
            configured_paths = tuple(item.repository_relative_path for item in resource.context_references)
            # Small repositories fit the existing bounded observation budget.
            # Inspect their implementation before requesting diagnostics from Human.
            observed_paths = tuple(path for path in paths if Path(path).suffix in {
                ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".sql", ".json", ".toml",
            } or Path(path).name in {"Dockerfile", "Makefile"})
            explicit_paths = () if semantic_ir is None else tuple(
                arg.value for goal in semantic_ir.current_production for arg in goal.target_paths)
            materials = self._context_materials(repository, baseline.repository_revision,
                self._observation_paths(configured_paths, observed_paths, explicit_paths))
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
            and design_context is not None
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
            dependent_analysis_requests=(
                current_dependent_analysis_requests(semantic_ir)
                if work_revision is not None and semantic_ir is not None
                and source_assessment is not None
                and work_revision.source_assessment_id == source_assessment.id
                else ()
            ),
            human_explicit_requests=human_records or (work.raw_user_requirement,),
            governed_semantic_ir_id=None if semantic_ir is None or semantic_ir.legacy_typed_projection else semantic_ir.id,
            governed_semantic_ir=None if semantic_ir is None else semantic_ir.model_dump(mode="json"),
            canonical_explicit_targets=() if semantic_ir is None else tuple(arg.value for goal in semantic_ir.current_production for arg in goal.target_paths),
            canonical_allowed_areas=() if semantic_ir is None else tuple(arg.value for goal in semantic_ir.current_production for arg in goal.allowed_areas),
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
        started = monotonic()
        candidate = None
        try:
            candidate = self.capability.execute(semantic_input)
        except SteeringInvariantViolation as error:
            # A provider's malformed typed candidate is a same-basis
            # stochastic defect. The strict parser remains fail-closed; the
            # existing Semantic owner gets one bounded correction opportunity.
            refine = getattr(self.capability, "refine", None)
            if not isinstance(error.__cause__, ValueError) or not callable(refine):
                raise
            feedback = "Semantic provider candidate failed strict schema or repository path validation: " + str(error)
            if isinstance(error.__cause__, ValidationError):
                issues = error.__cause__.errors(include_input=False, include_context=False)
                feedback += "; " + "; ".join(
                    f"{'.'.join(str(part) for part in issue['loc'])}: {issue['type']}"
                    for issue in issues
                )
            feedback = _semantic_feedback(feedback)
            first_usage = getattr(self.capability, "last_usage", None)
            first_observations = tuple(getattr(self.capability, "last_semantic_observations", ()))
            revised = None
            stage = "REVISED_PROVIDER_CANDIDATE"
            try:
                revised = refine(semantic_input, validation_feedback=feedback)
                stage = "REVISED_ADMISSION"
                admitted = self.admit(semantic_input, revised)
            except Exception as second_error:
                self._record_semantic_refinement(semantic_input, feedback, started,
                    first_usage, converged=False, second_error=second_error,
                    first_error=error, first_stage="INITIAL_PROVIDER_VALIDATION", second_stage=stage,
                    first_observations=first_observations, first_candidate=None, second_candidate=revised)
                raise SemanticStepRefinementExhausted(_semantic_failure_message(second_error)) from second_error
            self._record_semantic_refinement(semantic_input, feedback, started,
                first_usage, converged=True, first_error=error,
                first_stage="INITIAL_PROVIDER_VALIDATION", second_stage="ADMITTED",
                first_observations=first_observations, first_candidate=None, second_candidate=revised)
            return admitted
        try:
            return self.admit(semantic_input, candidate)
        except (SteeringInvariantViolation, ValueError) as error:
            first_error = error
            if isinstance(error, ValueError):
                error = SteeringInvariantViolation(f"Task Contract candidate failed validation: {error}")
            if isinstance(error, StaleSemanticStepCandidate) or not str(error).startswith(
                REFINABLE_ADMISSION_FEEDBACK
            ):
                raise
            refine = getattr(self.capability, "refine", None)
            if not callable(refine):
                raise
            feedback = _semantic_feedback(str(error))
            first_usage = getattr(self.capability, "last_usage", None)
            first_observations = tuple(getattr(self.capability, "last_semantic_observations", ()))
            revised = None
            stage = "REVISED_PROVIDER_CANDIDATE"
            try:
                revised = refine(semantic_input, validation_feedback=feedback)
                stage = "REVISED_ADMISSION"
                admitted = self.admit(semantic_input, revised)
            except Exception as second_error:
                self._record_semantic_refinement(
                    semantic_input, feedback, started, first_usage,
                    converged=False, second_error=second_error,
                    superseded=isinstance(second_error, StaleSemanticStepCandidate),
                    first_error=first_error, first_stage="INITIAL_ADMISSION", second_stage=stage,
                    first_observations=first_observations, first_candidate=candidate, second_candidate=revised,
                )
                if isinstance(second_error, StaleSemanticStepCandidate):
                    raise
                if isinstance(second_error, (SteeringInvariantViolation, ValueError)):
                    raise SemanticStepRefinementExhausted(_semantic_failure_message(second_error)) from second_error
                raise
            self._record_semantic_refinement(
                semantic_input, feedback, started, first_usage,
                converged=True, first_error=first_error, first_stage="INITIAL_ADMISSION", second_stage="ADMITTED",
                first_observations=first_observations, first_candidate=candidate, second_candidate=revised,
            )
            return admitted

    def _record_semantic_refinement(
        self, semantic_input: SemanticStepInput, feedback: str,
        started: float, first_usage: object, *, converged: bool,
        second_error: Exception | None = None,
        superseded: bool = False,
        first_error: Exception | None = None, first_stage: str = "INITIAL_ADMISSION",
        second_stage: str = "REVISED_ADMISSION", first_observations: tuple = (),
        first_candidate: SemanticStepResultCandidate | None = None,
        second_candidate: SemanticStepResultCandidate | None = None,
    ) -> None:
        from spg.providers.verification_receipts import _safe_value
        second_usage = getattr(self.capability, "last_usage", None)
        usages = ((first_usage,) if second_usage is first_usage else (first_usage, second_usage))
        usage_known = bool(usages) and all(isinstance(usage, dict) and not usage.get("unknown", False)
            and type(usage.get("total_tokens")) is int and usage["total_tokens"] >= 0 for usage in usages)
        for error in (first_error, second_error):
            provider_failure = (_semantic_failure(error) or {}).get("provider")
            if provider_failure is not None:
                failure_usage = provider_failure.get("usage")
                # Only an observed complete total can keep the failed call's
                # aggregate known. Legacy failures still expose no such total.
                if not isinstance(failure_usage, dict) or failure_usage.get("unknown", True) or (
                    type(failure_usage.get("total_tokens")) is not int or failure_usage["total_tokens"] < 0
                ):
                    usage_known = False
        total_tokens = sum(usage["total_tokens"] for usage in usages) if usage_known else None
        first_identity, second_identity = map(_semantic_candidate_identity, (first_candidate, second_candidate))
        second_observations = tuple(getattr(self.capability, "last_semantic_observations", ()))
        # Providers without the optional observation contract contribute no
        # invented request, response, token or transport counts.
        if second_observations is first_observations:
            second_observations = ()
        diagnostics = _safe_value({
            "schema": "semantic-step-refinement-diagnostic-v1",
            "work_id": str(semantic_input.work_id), "step_id": str(semantic_input.step.id),
            "steering_plan_revision_id": str(semantic_input.steering_plan_revision_id),
            "basis_fingerprint": semantic_input.basis_fingerprint,
            "first_validation_feedback": feedback,
            "first_failure": _semantic_failure(first_error),
            "second_error_type": None if second_error is None else type(second_error).__name__,
            "second_failure": _semantic_failure(second_error),
            "failure_stage": None if converged else second_stage,
            "candidate_lineage": [
                {"attempt": 1, "candidate": first_identity, "parent_candidate_fingerprint": None,
                 "stage": first_stage, "provider_observations": list(first_observations)},
                {"attempt": 2, "candidate": second_identity,
                 "parent_candidate_fingerprint": None if first_identity is None else first_identity["candidate_fingerprint"],
                 "stage": second_stage, "provider_observations": list(second_observations)},
            ],
            "budget": {"candidate_attempt_count": 2, "candidate_attempt_limit": 2,
                "feedback_attempt_count": 1, "feedback_attempt_limit": 1,
                "observation_is_authority": False},
        })
        with self.database.unit_of_work() as uow:
            NativeExecutionStore(uow.session).record_bounded_refinement(
                work_id=semantic_input.work_id,
                operation_id=semantic_input.step.id,
                component="steering/semantic-step",
                signal_kind=(
                    RefinementSignalKind.REALITY_MISMATCH
                    if superseded else RefinementSignalKind.CONTRACT_MISMATCH
                ),
                signature_basis=feedback,
                evidence_references=(f"steering-step:{semantic_input.step.id}",),
                converged=converged, attempt_count=2,
                elapsed_seconds=int(monotonic() - started),
                model_token_usage={"total_tokens": total_tokens, "unknown": not usage_known},
                diagnostic_evidence=diagnostics,
                superseded=superseded,
            )
            uow.commit()

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
        if candidate.unresolved_questions:
            from spg.application.human_attention import require_human_decision
            from spg.domain.intent_realization import GovernedSemanticIR
            require_human_decision(candidate.human_decision_need, evidence=fresh.reality_refs,
                semantic_ir=(None if fresh.governed_semantic_ir is None else
                             GovernedSemanticIR.model_validate(fresh.governed_semantic_ir)))
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
            inserted = store.insert_semantic_result(
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
                    "human_decision_need": (None if candidate.human_decision_need is None else candidate.human_decision_need.model_dump(mode="json")),
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
            if not inserted:
                # A concurrent run settled this same Step/basis while this
                # candidate was being prepared. It owns the single semantic
                # result and its Work update; this run must not apply a second
                # production proposal.
                existing = store.latest_semantic_result_for_step(fresh.step.id)
                if existing is None or existing.basis_fingerprint != fresh.basis_fingerprint:
                    raise StaleSemanticStepCandidate(
                        "Concurrent semantic result did not match the current Step basis")
                return existing
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
        validate_scope = getattr(getattr(self, "capability", None), "validate_production_scope", None)
        scope_validation = (validate_scope(semantic_input, proposal)
            if callable(validate_scope) and (proposal.target_kind is ProductionTargetKind.CODE_WORK
                or not semantic_input.required_intermediate_artifacts) else None)
        if scope_validation is not None and scope_validation.missing_acceptance_requirements:
            raise ValueError("INTENT_COMPLETENESS_MISMATCH: " + "; ".join(
                scope_validation.missing_acceptance_requirements))
        if proposal.target_kind is ProductionTargetKind.CODE_WORK:
            # Provider-selected code_targets are hypotheses, not Human scope.
            # Only paths stated by Human may enter the explicit-target channel,
            # including explicitly requested new files. Otherwise let read-only
            # repository discovery select the minimum required implementation.
            human_text = "\n".join(semantic_input.human_explicit_requests)
            if semantic_input.governed_semantic_ir_id is not None:
                human_targets = semantic_input.canonical_explicit_targets
                human_areas = semantic_input.canonical_allowed_areas
            else:
                # Historical/manual typed admission does not have an IRK Turn.
                human_targets = tuple(WorkApplicationService._explicit_repository_paths(human_text))
                human_areas = WorkApplicationService._explicit_repository_areas(human_text)
            change_proposal = self.change_proposals.propose(
                RepositoryChangeProposalRequest(
                    work_id=semantic_input.work_id,
                    refined_code_intent="\n".join(
                        (semantic_input.desired_outcome, *semantic_input.work_requests, *semantic_input.constraints)
                    ),
                    constraints=semantic_input.constraints,
                    engineering_resource_id=semantic_input.engineering_resource_id,
                    repository_identity=semantic_input.repository_identity,
                    repository_location=semantic_input.repository_location,
                    source_baseline_id=semantic_input.source_baseline_id,
                    source_ref=semantic_input.repository_ref,
                    source_revision=semantic_input.source_revision,
                    explicit_targets=human_targets,
                    candidate_targets=proposal.code_targets,
                    necessity_proofs=(() if scope_validation is None else scope_validation.required_targets),
                    human_authority_text="\n".join(semantic_input.human_explicit_requests),
                    governed_semantic_ir_id=semantic_input.governed_semantic_ir_id,
                    explicit_allowed_areas=human_areas,
                    explicit_forbidden_areas=proposal.forbidden_areas,
                )
            )
            if scope_validation is not None and (
                scope_validation.rejected_behaviors
                or set(proposal.code_targets) != {target.path for target in change_proposal.required_targets}
            ):
                with self.database.unit_of_work() as uow:
                    NativeExecutionStore(uow.session).record_bounded_refinement(
                        work_id=semantic_input.work_id, operation_id=semantic_input.step.id,
                        component="semantic/scope", signal_kind=RefinementSignalKind.CANDIDATE_INCONSISTENT,
                        signature_basis="PROVIDER_CANDIDATE_PROMOTED_TO_REQUIRED_SCOPE",
                        evidence_references=(f"source-baseline:{semantic_input.source_baseline_id}",),
                        converged=bool(change_proposal.required_targets), attempt_count=2,
                        model_token_usage=getattr(self.capability, "last_usage", None),
                        diagnostic_evidence={"signal": "SCOPE_INFLATION",
                            "candidate_paths": list(proposal.code_targets),
                            "required_paths": [target.path for target in change_proposal.required_targets],
                            "rejected_behaviors": list(scope_validation.rejected_behaviors),
                            "authority_expanded": False})
                    uow.commit()
        # Semantic provider prose is advisory. It may suggest useful implementation
        # details, but cannot add a route, page, or other product behavior to the
        # governed objective or verification contract without Human authority.
        production_objective = (
            semantic_input.desired_outcome
            if proposal.target_kind is ProductionTargetKind.CODE_WORK
            else proposal.objective
        )
        verification_expectation = (
            "Verify the admitted desired outcome against the exact Candidate, "
            "run repository-appropriate checks, and provide a real preview "
            "when requested; do not add unrequested functionality or deliver "
            "without Human authorization."
            if proposal.target_kind is ProductionTargetKind.CODE_WORK
            else proposal.verification_expectation
        )
        if (proposal.target_kind is ProductionTargetKind.DOCUMENTATION_WORK
                and semantic_input.human_explicit_requests):
            production_objective, verification_expectation = (
                bind_exact_human_document_identifiers(
                    production_objective, verification_expectation,
                    semantic_input.human_explicit_requests[-1],
                )
            )
        plan = self.planning.propose(
            ProductionPlanningRequest(
                work_id=semantic_input.work_id,
                target_kind=proposal.target_kind,
                admitted_requirement=semantic_input.desired_outcome,
                desired_outcome=semantic_input.desired_outcome,
                production_objective=production_objective,
                artifact_targets=proposal.artifact_targets,
                change_proposal=change_proposal,
                constraints=semantic_input.constraints,
                verification_expectation=verification_expectation,
                engineering_scope_summary=semantic_input.engineering_scope_summary,
                engineering_resource_id=semantic_input.engineering_resource_id,
                repository_identity=semantic_input.repository_identity,
                source_baseline_id=semantic_input.source_baseline_id,
                source_revision=semantic_input.source_revision,
                context_references=tuple(
                    item.repository_relative_path
                    for item in semantic_input.context_materials
                ),
                available_capabilities=semantic_input.available_executable_capabilities or None,
                refinement_reasons=(change_proposal.unresolved_scope_questions
                    if change_proposal is not None else ()),
            )
        )
        if plan.fit_classification not in {OnePwuFitClassification.ONE_PWU_FIT, OnePwuFitClassification.MULTI_PWU_FIT}:
            raise SteeringInvariantViolation(
                "Semantic production proposal has no executable PWU boundary: "
                + "; ".join(plan.unresolved_questions)
            )
        return plan, change_proposal

    @classmethod
    def _observation_paths(cls, configured, observed, explicit=()):
        """Sample actual implementation structure; never select Human intent.

        Large repositories must not lose every implementation observation just
        because their inventory exceeds the read budget. Markup entry points and
        adjacent assets are read-only evidence, not required change targets.
        """
        implementation = tuple(path for path in observed if not path.startswith(
            ("tests/", "test/", "docs/", "benchmarks/", "node_modules/")))
        markup = tuple(path for path in implementation if Path(path).suffix == ".html")
        adjacent = tuple(path for path in implementation if Path(path).suffix in {
            ".js", ".ts", ".tsx", ".jsx", ".css"} and Path(path).parent in {
                Path(entry).parent for entry in markup})
        return tuple(dict.fromkeys((*explicit, *configured, *markup, *adjacent, *implementation)))[:MAX_CONTEXT_FILES]

    @classmethod
    def _context_materials(
        cls,
        repository: Path,
        revision: str,
        paths: tuple[str, ...],
    ) -> tuple[SemanticContextMaterial, ...]:
        results: list[SemanticContextMaterial] = []
        total = 0
        selected = tuple(dict.fromkeys(paths))[:MAX_CONTEXT_FILES]
        for index, path in enumerate(selected):
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
            allowance = max(1, remaining // (len(selected) - index))
            content = completed.stdout[: min(MAX_CONTEXT_CHARS_PER_FILE, allowance)]
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
