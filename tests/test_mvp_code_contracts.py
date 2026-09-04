from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError
import pytest

from spg.application.planning import ProductionPlanningService
from spg.domain.change import (
    ChangeOperation,
    ChangeTargetShape,
    CodeChangeContract,
    CodeChangeTarget,
    CodeVerificationKind,
    CodeVerificationObligation,
    ProductionTargetKind,
)
from spg.domain.planning import (
    OnePwuFitClassification,
    ProductionPlanProposal,
    ProductionPlanStep,
    ProductionPlanningRequest,
)
from spg.domain.runtime import CompletionContract
from spg.infrastructure.configured_executor import render_governed_instruction
from spg.providers.rule_based_planner import RuleBasedProductionPlanner


def _contract(
    *,
    exact_paths: tuple[str, ...] = ("src/spg/example.py", "tests/test_example.py"),
    allowed_areas: tuple[str, ...] = (),
) -> CodeChangeContract:
    return CodeChangeContract(
        target_shape=(
            ChangeTargetShape.EXACT_AND_BOUNDED
            if exact_paths and allowed_areas
            else ChangeTargetShape.EXACT_TARGET_SET
            if exact_paths
            else ChangeTargetShape.BOUNDED_REPOSITORY_AREAS
        ),
        engineering_resource_id=uuid4(),
        repository_identity="test://code-contract",
        source_baseline_id=uuid4(),
        source_revision="a" * 40,
        desired_outcome="Change one bounded Python behavior and its test",
        constraints=("Do not change public API shape.",),
        exact_targets=tuple(
            CodeChangeTarget(path=path, operation=ChangeOperation.UPDATE)
            for path in exact_paths
        ),
        allowed_areas=allowed_areas,
        forbidden_areas=(".github/**",),
        verification_obligations=(
            CodeVerificationObligation(kind=CodeVerificationKind.PATH_SCOPE),
            CodeVerificationObligation(kind=CodeVerificationKind.GIT_DIFF_CHECK),
            CodeVerificationObligation(kind=CodeVerificationKind.PYTHON_COMPILE),
            CodeVerificationObligation(
                kind=CodeVerificationKind.PYTEST_TARGET,
                target="tests/test_example.py",
            ),
            CodeVerificationObligation(
                kind=CodeVerificationKind.IMPORT_CHECK,
                target="spg.example",
            ),
        ),
    )


def _request(contract: CodeChangeContract) -> ProductionPlanningRequest:
    return ProductionPlanningRequest(
        work_id=uuid4(),
        target_kind=ProductionTargetKind.CODE_WORK,
        admitted_requirement="Modify src/spg/example.py and tests/test_example.py",
        desired_outcome=contract.desired_outcome,
        production_objective=contract.desired_outcome,
        change_contract=contract,
        constraints=contract.constraints,
        verification_expectation="Run admitted typed checks",
        engineering_scope_summary="One repository",
        engineering_resource_id=contract.engineering_resource_id,
        repository_identity=contract.repository_identity,
        source_baseline_id=contract.source_baseline_id,
        source_revision=contract.source_revision,
    )


def test_code_02_03_04_exact_and_bounded_change_contract_is_typed() -> None:
    contract = _contract(allowed_areas=("src/spg/api/**",))

    assert contract.target_kind is ProductionTargetKind.CODE_WORK
    assert contract.target_shape is ChangeTargetShape.EXACT_AND_BOUNDED
    assert contract.allows_path("src/spg/example.py")
    assert contract.allows_path("src/spg/api/routes.py")
    assert not contract.allows_path("README.md")
    assert not contract.allows_path(".github/workflows/ci.yml")


@pytest.mark.parametrize(
    "unsafe",
    (
        "C:/outside.py",
        "/outside.py",
        "../outside.py",
        ".git/config",
        "**/*",
        "src/**/anything.py",
    ),
)
def test_code_05_06_unsafe_or_repository_wide_exact_paths_are_rejected(
    unsafe: str,
) -> None:
    with pytest.raises(ValidationError):
        CodeChangeTarget(path=unsafe, operation=ChangeOperation.UPDATE)


@pytest.mark.parametrize("area", ("**/*", "./**", ".git/**", "src/spg"))
def test_code_05_06_unbounded_or_unsafe_areas_are_rejected(area: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        _contract(exact_paths=(), allowed_areas=(area,))


def test_code_09_10_11_plan_and_mei_preserve_one_pwu_change_authority() -> None:
    contract = _contract()
    plan = RuleBasedProductionPlanner().propose(_request(contract))
    completion = CompletionContract(
        required_outputs=tuple(target.path for target in contract.exact_targets),
        required_changes=tuple(target.path for target in contract.exact_targets),
        verification_obligations=contract.verification_identities,
        change_contract=contract,
        production_plan=plan,
    )

    assert plan.target_kind is ProductionTargetKind.CODE_WORK
    assert plan.fit_classification is OnePwuFitClassification.ONE_PWU_FIT
    assert plan.change_contract == contract
    assert "pwu" not in ProductionPlanStep.model_fields
    instruction = render_governed_instruction(plan.objective, completion)
    assert all(target.path in instruction for target in contract.exact_targets)
    assert all(item.identity in instruction for item in contract.verification_obligations)
    assert "Never widen the Change Contract yourself" in instruction
    assert "repository root" not in instruction


class _WideningPlanner:
    def propose(self, request: ProductionPlanningRequest) -> ProductionPlanProposal:
        admitted = request.change_contract
        assert admitted is not None
        widened = admitted.model_copy(
            update={
                "exact_targets": (
                    *admitted.exact_targets,
                    CodeChangeTarget(
                        path="README.md",
                        operation=ChangeOperation.UPDATE,
                    ),
                )
            }
        )
        return ProductionPlanProposal(
            proposal_id=uuid4(),
            target_kind=request.target_kind,
            objective=request.production_objective,
            desired_outcome=request.desired_outcome,
            ordered_steps=(ProductionPlanStep(position=1, instruction="Widen."),),
            change_contract=widened,
            inherited_constraints=request.constraints,
            verification_approach=request.verification_expectation,
            fit_classification=OnePwuFitClassification.ONE_PWU_FIT,
            engineering_resource_id=request.engineering_resource_id,
            repository_identity=request.repository_identity,
            source_baseline_id=request.source_baseline_id,
            source_revision=request.source_revision,
        )


def test_code_12_planner_cannot_widen_the_admitted_contract() -> None:
    contract = _contract()
    proposal = ProductionPlanningService(_WideningPlanner()).propose(_request(contract))

    assert proposal.fit_classification is OnePwuFitClassification.NEEDS_REFINEMENT
    assert proposal.change_contract == contract
    assert "widened" in proposal.unresolved_questions[0]


def test_code_15_16_17_18_verification_is_typed_and_contract_owned() -> None:
    contract = _contract()

    assert contract.verification_identities == (
        "PATH_SCOPE",
        "GIT_DIFF_CHECK",
        "PYTHON_COMPILE",
        "PYTEST_TARGET:tests/test_example.py",
        "IMPORT_CHECK:spg.example",
    )
    assert not any("shell" in identity.casefold() for identity in contract.verification_identities)
    with pytest.raises(ValidationError):
        CodeVerificationObligation(
            kind=CodeVerificationKind.PYTEST_TARGET,
            target="tests/../outside.py",
        )


def test_code_01_07_code_intent_is_not_a_documentation_fallback() -> None:
    from spg.application.work import WorkApplicationService
    from spg.domain.product import WorkRefinementRequest

    assert WorkApplicationService._is_code_work(
        "Modify source code without a resolved target",
        WorkRefinementRequest(),
    )
    assert not WorkApplicationService._explicit_repository_paths(
        "Modify source code without a resolved target"
    )
    assert WorkApplicationService._explicit_repository_paths(
        "Modify src/spg/example.py and tests/test_example.py"
    ) == ("src/spg/example.py", "tests/test_example.py")


def test_code_contract_module_remains_provider_neutral() -> None:
    source = Path("src/spg/domain/change.py").read_text(encoding="utf-8")
    assert "Codex" not in source
    assert "subprocess" not in source
