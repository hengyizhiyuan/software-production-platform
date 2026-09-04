"""Narrow deterministic Production Planner Lite provider."""

import json

from uuid import NAMESPACE_URL, uuid5

from spg.domain.planning import (
    OnePwuFitClassification,
    ProductionPlanProposal,
    ProductionPlanStep,
    ProductionPlanningRequest,
)


class RuleBasedProductionPlanner:
    """Form one-PWU plans without model calls or independent authority."""

    _MULTI_PWU_MARKERS = (
        "independently governed sequential",
        "separate governed production units",
        "multiple executable pwus",
        "successor baseline",
        "independent baseline progression",
        "多个独立 pwu",
        "多 pwu",
        "逐个基线推进",
    )

    def propose(self, request: ProductionPlanningRequest) -> ProductionPlanProposal:
        normalized = " ".join(request.admitted_requirement.casefold().split())
        if any(marker in normalized for marker in self._MULTI_PWU_MARKERS):
            fit = OnePwuFitClassification.MULTI_PWU_REQUIRED
            unresolved = (
                "The requested independently governed sequence exceeds the current single-PWU MVP boundary.",
            )
        elif request.refinement_reasons:
            fit = OnePwuFitClassification.NEEDS_REFINEMENT
            unresolved = request.refinement_reasons
        else:
            fit = OnePwuFitClassification.ONE_PWU_FIT
            unresolved = ()

        instructions = self._steps(request, fit)
        identity = "|".join(
            (
                str(request.work_id),
                request.source_revision,
                request.production_objective,
                fit.value,
                *(target.path for target in request.artifact_targets),
                json.dumps(
                    None
                    if request.change_proposal is None
                    else request.change_proposal.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                json.dumps(
                    None
                    if request.change_contract is None
                    else request.change_contract.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                *instructions,
            )
        )
        return ProductionPlanProposal(
            proposal_id=uuid5(NAMESPACE_URL, f"spg:production-plan:{identity}"),
            target_kind=request.target_kind,
            objective=request.production_objective,
            desired_outcome=request.desired_outcome,
            ordered_steps=tuple(
                ProductionPlanStep(position=index, instruction=instruction)
                for index, instruction in enumerate(instructions, start=1)
            ),
            artifact_targets=request.artifact_targets,
            change_proposal=request.change_proposal,
            change_contract=request.change_contract,
            inherited_constraints=request.constraints,
            verification_approach=request.verification_expectation,
            assumptions=(
                "The admitted Work can be executed through one governed PWU and Attempt lineage.",
            ) if fit is OnePwuFitClassification.ONE_PWU_FIT else (),
            unresolved_questions=unresolved,
            fit_classification=fit,
            engineering_resource_id=request.engineering_resource_id,
            repository_identity=request.repository_identity,
            source_baseline_id=request.source_baseline_id,
            source_revision=request.source_revision,
        )

    @staticmethod
    def _steps(
        request: ProductionPlanningRequest,
        fit: OnePwuFitClassification,
    ) -> tuple[str, ...]:
        if fit is not OnePwuFitClassification.ONE_PWU_FIT:
            return ("Resolve the listed planning blocker before production admission.",)

        steps: list[str] = [
            "Inspect the admitted Source of Truth and existing repository conventions.",
        ]
        for target in request.artifact_targets:
            action = target.operation.value.lower()
            steps.append(
                f"{action.capitalize()} the exact authorized artifact {target.path}."
            )
        if request.change_proposal is not None:
            required = ", ".join(
                target.path for target in request.change_proposal.required_targets
            )
            if required:
                steps.append(f"Prepare the Human-proposed code targets: {required}.")
            if request.change_proposal.allowed_areas:
                areas = ", ".join(request.change_proposal.allowed_areas)
                steps.append(f"Keep any Human-admitted code changes inside: {areas}.")
        if request.change_contract is not None:
            if request.change_contract.exact_targets:
                paths = ", ".join(
                    target.path for target in request.change_contract.exact_targets
                )
                steps.append(f"Modify only the admitted exact code targets: {paths}.")
            if request.change_contract.allowed_areas:
                areas = ", ".join(request.change_contract.allowed_areas)
                steps.append(f"Keep all other code changes inside: {areas}.")
        steps.append("Run the admitted targeted verification and report the resulting evidence.")
        return tuple(dict.fromkeys(steps))
