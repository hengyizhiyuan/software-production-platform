from uuid import uuid4

from spg.application.planning import ProductionPlanningService
from spg.domain.planning import (
    OnePwuFitClassification,
    PlannedArtifactOperation,
    ProductionPlanArtifactTarget,
    ProductionPlanProposal,
    ProductionPlanStep,
    ProductionPlanningRequest,
)
from spg.domain.runtime import CompletionContract
from spg.infrastructure.configured_executor import render_governed_instruction
from spg.providers.rule_based_planner import RuleBasedProductionPlanner


def _request(
    requirement: str,
    *,
    refinement_reasons: tuple[str, ...] = (),
    artifact_targets: tuple[ProductionPlanArtifactTarget, ...] | None = None,
):
    return ProductionPlanningRequest(
        work_id=uuid4(),
        admitted_requirement=requirement,
        desired_outcome="Produce the admitted change",
        production_objective="Produce the admitted change",
        artifact_targets=artifact_targets
        or (
            ProductionPlanArtifactTarget(
                path="docs/architecture/change.md",
                operation=PlannedArtifactOperation.CREATE,
            ),
        ),
        constraints=("Do not change production code.",),
        verification_expectation="Verify the exact artifact content.",
        engineering_scope_summary="One governed repository",
        engineering_resource_id=uuid4(),
        repository_identity="test://planner",
        source_baseline_id=uuid4(),
        source_revision="a" * 40,
        context_references=("AI_context.md",),
        refinement_reasons=refinement_reasons,
    )


def test_atomic_documentation_work_forms_short_ordered_single_pwu_plan() -> None:
    plan = RuleBasedProductionPlanner().propose(
        _request("Create one architecture documentation artifact")
    )

    assert plan.fit_classification is OnePwuFitClassification.ONE_PWU_FIT
    assert tuple(step.position for step in plan.ordered_steps) == tuple(
        range(1, len(plan.ordered_steps) + 1)
    )
    assert 2 <= len(plan.ordered_steps) <= 4


def test_api_tests_and_documentation_are_logical_steps_not_pwus() -> None:
    targets = tuple(
        ProductionPlanArtifactTarget(
            path=path,
            operation=PlannedArtifactOperation.CREATE,
        )
        for path in ("src/api.py", "tests/test_api.py", "docs/api.md")
    )
    plan = RuleBasedProductionPlanner().propose(
        _request(
            "Add an API endpoint, affected tests, and documentation",
            artifact_targets=targets,
        )
    )

    assert plan.fit_classification is OnePwuFitClassification.ONE_PWU_FIT
    assert len(plan.ordered_steps) >= 4
    assert plan.artifact_targets == targets
    assert "work_unit" not in ProductionPlanStep.model_fields
    assert "pwu" not in ProductionPlanProposal.model_fields


def test_ambiguous_work_requires_refinement() -> None:
    plan = RuleBasedProductionPlanner().propose(
        _request(
            "Make it better",
            refinement_reasons=("The requested outcome is ambiguous.",),
        )
    )

    assert plan.fit_classification is OnePwuFitClassification.NEEDS_REFINEMENT
    assert plan.unresolved_questions == ("The requested outcome is ambiguous.",)


def test_independently_governed_sequence_requires_deferred_multi_pwu() -> None:
    plan = RuleBasedProductionPlanner().propose(
        _request(
            "Use independently governed sequential production with a successor baseline"
        )
    )

    assert plan.fit_classification is OnePwuFitClassification.MULTI_PWU_REQUIRED


class ScopeExpandingPlanner:
    def propose(self, request: ProductionPlanningRequest) -> ProductionPlanProposal:
        return ProductionPlanProposal(
            proposal_id=uuid4(),
            objective=request.production_objective,
            desired_outcome=request.desired_outcome,
            ordered_steps=(ProductionPlanStep(position=1, instruction="Expand scope."),),
            artifact_targets=(
                ProductionPlanArtifactTarget(
                    path="src/unauthorized.py",
                    operation=PlannedArtifactOperation.CREATE,
                ),
            ),
            inherited_constraints=request.constraints,
            verification_approach=request.verification_expectation,
            assumptions=(),
            unresolved_questions=(),
            fit_classification=OnePwuFitClassification.ONE_PWU_FIT,
            engineering_resource_id=request.engineering_resource_id,
            repository_identity=request.repository_identity,
            source_baseline_id=request.source_baseline_id,
            source_revision=request.source_revision,
        )


def test_planner_scope_expansion_is_replaced_by_truthful_refinement_plan() -> None:
    request = _request("Create one bounded document")
    plan = ProductionPlanningService(ScopeExpandingPlanner()).propose(request)

    assert plan.fit_classification is OnePwuFitClassification.NEEDS_REFINEMENT
    assert plan.artifact_targets == request.artifact_targets
    assert "unauthorized artifact target" in plan.unresolved_questions[0]


def test_mei_instruction_contains_admitted_plan_without_provider_types() -> None:
    plan = RuleBasedProductionPlanner().propose(
        _request("Create one architecture documentation artifact")
    )
    contract = CompletionContract(
        required_outputs=("docs/architecture/change.md",),
        required_changes=("docs/architecture/change.md",),
        verification_obligations=(plan.verification_approach,),
        production_plan=plan,
    )

    instruction = render_governed_instruction(plan.objective, contract)

    assert plan.desired_outcome in instruction
    assert all(step.instruction in instruction for step in plan.ordered_steps)
    assert plan.verification_approach in instruction
    assert "Codex" not in ProductionPlanningRequest.__module__
