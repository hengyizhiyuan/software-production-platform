"""Authority-safe application boundary for Production Planner Lite."""

from uuid import NAMESPACE_URL, uuid5

from spg.domain.planning import (
    OnePwuFitClassification,
    ProductionPlanProposal,
    ProductionPlanStep,
    ProductionPlanner,
    ProductionPlanningRequest,
    ProductionNodeKind,
)


class ProductionPlanningService:
    """Accept planning intelligence only when it stays inside governed Work facts."""

    def __init__(self, planner: ProductionPlanner, *, database=None) -> None:
        self.planner = planner
        self.database = database

    def propose(self, request: ProductionPlanningRequest) -> ProductionPlanProposal:
        proposal = self.planner.propose(request)
        violations = self._authority_violations(request, proposal)
        if not violations:
            return proposal
        from spg.providers.rule_based_planner import RuleBasedProductionPlanner
        # Regenerate from admitted facts, not by deleting failed validations or
        # accepting an expanded model scope. Genuine unresolved facts remain so.
        revised = RuleBasedProductionPlanner().propose(request)
        remaining = self._authority_violations(request, revised)
        if self.database is not None:
            from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
            from spg.domain.refinement_contract import RefinementSignalKind
            with self.database.unit_of_work() as uow:
                NativeExecutionStore(uow.session).record_bounded_refinement(
                    work_id=request.work_id, operation_id=proposal.proposal_id,
                    component="planning/production-plan", signal_kind=RefinementSignalKind.CONTRACT_MISMATCH,
                    signature_basis="|".join(violations),
                    evidence_references=(f"production-plan:{proposal.proposal_id}",),
                    converged=not remaining and revised.fit_classification in {
                        OnePwuFitClassification.ONE_PWU_FIT, OnePwuFitClassification.MULTI_PWU_FIT},
                    attempt_count=2, diagnostic_evidence={"initial_violations": list(violations),
                        "remaining_violations": list(remaining), "authority_expanded": False})
                uow.commit()
        if not remaining:
            return revised
        violations = remaining
        return ProductionPlanProposal(
            proposal_id=uuid5(
                NAMESPACE_URL,
                f"spg:planning-authority-refinement:{request.work_id}:{'|'.join(violations)}",
            ),
            target_kind=request.target_kind,
            objective=request.production_objective,
            desired_outcome=request.desired_outcome,
            ordered_steps=(
                ProductionPlanStep(
                    position=1,
                    instruction="Resolve the proposed Production Plan authority expansion.",
                ),
            ),
            artifact_targets=request.artifact_targets,
            change_proposal=request.change_proposal,
            change_contract=request.change_contract,
            inherited_constraints=request.constraints,
            verification_approach=request.verification_expectation,
            assumptions=(),
            unresolved_questions=tuple(violations),
            fit_classification=OnePwuFitClassification.NEEDS_REFINEMENT,
            engineering_resource_id=request.engineering_resource_id,
            repository_identity=request.repository_identity,
            source_baseline_id=request.source_baseline_id,
            source_revision=request.source_revision,
        )

    @staticmethod
    def _authority_violations(
        request: ProductionPlanningRequest,
        proposal: ProductionPlanProposal,
    ) -> tuple[str, ...]:
        violations: list[str] = []
        if proposal.objective != request.production_objective:
            violations.append("Planner changed the admitted production objective.")
        if proposal.desired_outcome != request.desired_outcome:
            violations.append("Planner changed the admitted desired outcome.")
        if proposal.target_kind is not request.target_kind:
            violations.append("Planner changed the admitted target kind.")
        if proposal.artifact_targets != request.artifact_targets:
            violations.append("Planner introduced or changed an unauthorized artifact target.")
        if proposal.change_proposal != request.change_proposal:
            violations.append("Planner introduced or widened an unauthorized Change Proposal.")
        if proposal.change_contract != request.change_contract:
            violations.append("Planner introduced or widened an unauthorized code change boundary.")
        if proposal.inherited_constraints != request.constraints:
            violations.append("Planner changed the admitted Work constraints.")
        if proposal.verification_approach != request.verification_expectation:
            violations.append("Planner changed the admitted verification expectation.")
        if (
            proposal.engineering_resource_id != request.engineering_resource_id
            or proposal.repository_identity != request.repository_identity
        ):
            violations.append("Planner widened the admitted Engineering Resource or Scope.")
        if (
            proposal.source_baseline_id != request.source_baseline_id
            or proposal.source_revision != request.source_revision
        ):
            violations.append("Planner changed the exact Source Baseline.")
        if request.available_capabilities is not None and proposal.graph is None:
            required = {"filesystem.read", "filesystem.write"}
            if request.change_contract is not None and any(
                item.kind.value in {"PYTEST_TARGET", "NODE_TEST_TARGET"}
                for item in request.change_contract.verification_obligations
            ):
                required.add("test.run")
            unavailable = required - set(request.available_capabilities)
            if unavailable:
                violations.append("PWU_REQUIRED_CAPABILITY_UNAVAILABLE_AT_ADMISSION: "
                    + ", ".join(sorted(unavailable)))
        if proposal.graph is not None:
            paths = set(target.path for target in request.artifact_targets)
            if request.change_contract is not None:
                paths.update(target.path for target in request.change_contract.exact_targets)
            if request.change_proposal is not None:
                paths.update(target.path for target in request.change_proposal.required_targets)
            units = tuple(node for node in proposal.graph.nodes
                if node.kind is not ProductionNodeKind.GROUP)
            if sum(node.kind is ProductionNodeKind.PWU for node in units) > len(paths):
                violations.append("PWU_COUNT_EXCEEDS_PROVEN_CHANGE_SURFACES")
            for node in units:
                if set(node.writable_paths) - paths:
                    violations.append("Planner introduced an unproven PWU write surface.")
                if request.available_capabilities is not None:
                    unavailable = set(node.required_capabilities) - set(request.available_capabilities)
                    if unavailable:
                        violations.append("PWU_REQUIRED_CAPABILITY_UNAVAILABLE_AT_ADMISSION: "
                            + ", ".join(sorted(unavailable)))
        return tuple(violations)
