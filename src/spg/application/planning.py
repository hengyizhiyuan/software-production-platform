"""Authority-safe application boundary for Production Planner Lite."""

from uuid import NAMESPACE_URL, uuid5

from spg.domain.planning import (
    OnePwuFitClassification,
    ProductionPlanProposal,
    ProductionPlanStep,
    ProductionPlanner,
    ProductionPlanningRequest,
)


class ProductionPlanningService:
    """Accept planning intelligence only when it stays inside governed Work facts."""

    def __init__(self, planner: ProductionPlanner) -> None:
        self.planner = planner

    def propose(self, request: ProductionPlanningRequest) -> ProductionPlanProposal:
        proposal = self.planner.propose(request)
        violations = self._authority_violations(request, proposal)
        if not violations:
            return proposal
        return ProductionPlanProposal(
            proposal_id=uuid5(
                NAMESPACE_URL,
                f"spg:planning-authority-refinement:{request.work_id}:{'|'.join(violations)}",
            ),
            objective=request.production_objective,
            desired_outcome=request.desired_outcome,
            ordered_steps=(
                ProductionPlanStep(
                    position=1,
                    instruction="Resolve the proposed Production Plan authority expansion.",
                ),
            ),
            artifact_targets=request.artifact_targets,
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
        if proposal.artifact_targets != request.artifact_targets:
            violations.append("Planner introduced or changed an unauthorized artifact target.")
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
        return tuple(violations)
