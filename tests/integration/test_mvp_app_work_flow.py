from collections.abc import Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, inspect, select

from spg.application.runtime import RuntimeService
from spg.application.materialization import ExecutionInputMaterializationService
from spg.application.work import WorkApplicationService
from spg.domain.execution import ProviderReportedOutcome
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import (
    AttentionAction,
    AttentionKind,
    AttentionResolutionRequest,
    EngineeringContextReference,
    EngineeringScopeCondition,
    ProductInvariantViolation,
    ResourceBindingCondition,
    WorkCondition,
    WorkRefinementRequest,
    WorkStatus,
)
from spg.domain.runtime import BootstrapRequest
from spg.domain.verification import VerificationResultValue
from spg.infrastructure.persistence import Database, product_tables, runtime_tables
from spg.infrastructure.persistence.product_schema import product_works
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.runtime_schema import (
    completion_evaluations,
    execution_attempts,
    governance_records,
    production_runs,
    plan_revisions,
    production_work_units,
    provider_execution_reports,
    repository_observations,
)
from spg.providers.deterministic_executor import (
    DeterministicExecutionSpecification,
    DeterministicFileOperation,
    DeterministicFileOperationType,
    DeterministicTestExecutor,
)
from spg.providers.deterministic_verifier import DeterministicVerificationProvider
from spg.infrastructure.configured_executor import render_governed_instruction
from spg.providers.repository_markdown_verifier import RepositoryArtifactVerifier
from spg.providers.contract_verifier import ContractDrivenRepositoryVerifier


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_TABLE_NAMES = {table.name for table in product_tables}
ALL_TABLE_NAMES = {table.name for table in (*product_tables, *runtime_tables)}


@dataclass(frozen=True)
class AppFacts:
    database: Database
    repository: Path
    workspace_root: Path
    service: WorkApplicationService
    resource: object


def _migration_config(database: Database) -> Config:
    os.environ["SPG_DATABASE_URL"] = database.engine.url.render_as_string(
        hide_password=False
    )
    return Config(PROJECT_ROOT / "alembic.ini")


@pytest.fixture(autouse=True)
def clean_product_runtime_schema(postgres_database: Database) -> Iterator[None]:
    previous = os.environ.get("SPG_DATABASE_URL")
    command.upgrade(_migration_config(postgres_database), "head")
    _truncate(postgres_database)
    try:
        yield
    finally:
        command.upgrade(_migration_config(postgres_database), "head")
        _truncate(postgres_database)
        if previous is None:
            os.environ.pop("SPG_DATABASE_URL", None)
        else:
            os.environ["SPG_DATABASE_URL"] = previous


@pytest.fixture
def git_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "governed-repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "docs").mkdir()
    (repository / "docs" / "architecture").mkdir()
    (repository / "AI_context.md").write_text("baseline context\n", encoding="utf-8")
    (repository / "docs" / "contract.md").write_text(
        "governed execution contract\n",
        encoding="utf-8",
    )
    (repository / "docs" / "architecture" / "architecture-principles.md").write_text(
        "accepted architecture principles\n",
        encoding="utf-8",
    )
    (repository / "src").mkdir()
    (repository / "tests").mkdir()
    (repository / "src" / "spg_example.py").write_text(
        'def value() -> str:\n    return "old"\n',
        encoding="utf-8",
    )
    (repository / "tests" / "test_spg_example.py").write_text(
        'from spg_example import value\n\n\ndef test_value() -> None:\n    assert value() == "old"\n',
        encoding="utf-8",
    )
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    return repository


@pytest.fixture
def app_facts(
    postgres_database: Database,
    git_repository: Path,
    tmp_path: Path,
) -> AppFacts:
    RuntimeService(postgres_database).bootstrap_trusted_baseline(
        BootstrapRequest(
            repository_path=git_repository,
            repository_identity="test://mvp-app-repository",
            repository_ref="refs/heads/main",
            authority_identity="architecture-lead:test",
            scope={"slice": "MVP-APP-1"},
        )
    )
    service = WorkApplicationService(
        postgres_database,
        workspace_root=tmp_path / "attempt-workspaces",
    )
    resource = service.register_engineering_resource(
        repository_identity="test://mvp-app-repository",
        location_ref=str(git_repository),
        authoritative_ref="refs/heads/main",
        context_references=(
            EngineeringContextReference(
                semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                repository_relative_path="AI_context.md",
            ),
            EngineeringContextReference(
                semantic_role=ContextSemanticRole.EXECUTION_CONTRACT,
                repository_relative_path="docs/contract.md",
            ),
        ),
    )
    return AppFacts(
        database=postgres_database,
        repository=git_repository,
        workspace_root=tmp_path / "attempt-workspaces",
        service=service,
        resource=resource,
    )


def _draft(
    facts: AppFacts,
    *,
    requirement: str = "Create the admitted MVP Work result",
    goal_id=None,
    tags: tuple[str, ...] = ("mvp",),
):
    submitted = facts.service.submit_work(
        requirement,
        goal_id=goal_id,
        tags=tags,
    )
    return facts.service.refine_work(submitted.work_id)


INTAKE_SAME_INTENT = """Create a formal Production Orchestration Lite product/architecture document
in an appropriate location in the existing documentation system.
Cover Human-in-the-loop != Human-as-the-loop, automatic progression boundaries,
Human Attention responsibility, MVP vs future evolution, and reuse accepted design.
Do not expand or invent new capabilities beyond the already accepted design."""


def test_intake_same_intent_target_propagates_from_approval_through_verification(
    app_facts: AppFacts,
) -> None:
    submitted = app_facts.service.submit_work(INTAKE_SAME_INTENT)
    draft = app_facts.service.refine_work(submitted.work_id)
    assert draft.artifact_target is not None
    assert draft.production_plan is not None
    assert draft.production_plan.fit_classification.value == "ONE_PWU_FIT"
    target = "docs/architecture/production-orchestration-lite.md"
    assert draft.artifact_target.path == target
    assert draft.artifact_target.operation.value == "CREATE"
    assert draft.constraints
    assert "docs/work-" not in draft.artifact_target.path

    approved = app_facts.service.approve_work(
        draft.work_id,
        authority_identity="architecture-lead:intake-test",
    )
    assert approved.status is WorkStatus.READY
    binding = _runtime_binding(app_facts, draft.work_id)
    assert binding is not None
    with app_facts.database.unit_of_work() as unit_of_work:
        work_unit = RuntimeStore(unit_of_work.session).work_unit(binding.work_unit_id)
    assert work_unit is not None
    contract = work_unit.completion_contract
    assert contract.artifact_contract is not None
    assert contract.production_plan == draft.production_plan
    assert contract.artifact_contract.artifact_path == target
    assert contract.required_outputs == (target,)
    assert contract.required_changes == (target,)
    assert target in work_unit.objective
    assert all(item in contract.artifact_contract.constraints for item in draft.constraints)

    app_facts.service.advance_work(draft.work_id)
    app_facts.service.advance_work(draft.work_id)
    with app_facts.database.unit_of_work() as unit_of_work:
        summary = ProductStore(unit_of_work.session).runtime_summary(binding)
    assert summary.attempt_id is not None
    instruction = render_governed_instruction(work_unit.objective, contract)
    materialized = ExecutionInputMaterializationService(app_facts.database).materialize(
        summary.attempt_id,
        instruction,
    )
    assert target in materialized.instruction_content
    assert "Operation: CREATE" in materialized.instruction_content
    assert "Ordered Plan steps:" in materialized.instruction_content
    assert all(
        step.instruction in materialized.instruction_content
        for step in draft.production_plan.ordered_steps
    )

    executor = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=(
                DeterministicFileOperation(
                    operation=DeterministicFileOperationType.CREATE,
                    repository_relative_path=target,
                    content="# Production Orchestration Lite\n\nGoverned result.\n",
                ),
            ),
            reported_outcome=ProviderReportedOutcome.SUCCESS,
        )
    )
    service = WorkApplicationService(
        app_facts.database,
        workspace_root=app_facts.workspace_root,
        executor=executor,
        verifier=RepositoryArtifactVerifier(app_facts.database),
    )
    for _ in range(10):
        result = service.advance_work(draft.work_id)
        if result.status in {WorkStatus.NEEDS_ATTENTION, WorkStatus.BLOCKED}:
            break
    assert result.status is WorkStatus.NEEDS_ATTENTION
    with app_facts.database.unit_of_work() as unit_of_work:
        final = ProductStore(unit_of_work.session).runtime_summary(binding)
    assert final.artifact_paths == (target,)
    assert final.verification_obligations == contract.verification_obligations
    assert final.verification_results == (VerificationResultValue.PASS.value,)


def test_plan_approval_creates_exactly_one_plan_revision_and_one_pwu(
    app_facts: AppFacts,
) -> None:
    draft = _draft(
        app_facts,
        requirement="Add an API endpoint, affected tests, and documentation at docs/api-plan.md",
    )
    assert draft.production_plan is not None
    # Only the exact documentation target is admitted here. The Planner must not
    # invent source/test steps from descriptive prose without a Code Contract.
    assert len(draft.production_plan.ordered_steps) >= 3

    app_facts.service.approve_work(
        draft.work_id,
        authority_identity="architecture-lead:plan-1b",
    )
    binding = _runtime_binding(app_facts, draft.work_id)
    assert binding is not None
    with app_facts.database.unit_of_work() as unit_of_work:
        plan_count = unit_of_work.session.scalar(
            select(func.count()).select_from(plan_revisions)
        )
        work_unit_count = unit_of_work.session.scalar(
            select(func.count()).select_from(production_work_units)
        )
        work_unit = RuntimeStore(unit_of_work.session).work_unit(binding.work_unit_id)

    assert plan_count == 1
    assert work_unit_count == 1
    assert work_unit is not None
    assert work_unit.completion_contract.production_plan == draft.production_plan


@pytest.mark.parametrize(
    ("requirement", "expected_fit"),
    (
        ("Rewrite the whole entire platform and all systems", "NEEDS_REFINEMENT"),
        (
            "Use independently governed sequential production with a successor baseline",
            "MULTI_PWU_REQUIRED",
        ),
    ),
)
def test_non_single_pwu_fit_creates_no_executable_runtime(
    app_facts: AppFacts,
    requirement: str,
    expected_fit: str,
) -> None:
    draft = _draft(app_facts, requirement=requirement)

    assert draft.status is WorkStatus.NEEDS_REFINEMENT
    assert draft.production_plan is not None
    assert draft.production_plan.fit_classification.value == expected_fit
    assert draft.human_attention_required
    assert _runtime_binding(app_facts, draft.work_id) is None
    with pytest.raises(ProductInvariantViolation):
        app_facts.service.approve_work(
            draft.work_id,
            authority_identity="architecture-lead:plan-1b",
        )


def test_intake_human_override_replaces_proposal_before_approval(
    app_facts: AppFacts,
) -> None:
    submitted = app_facts.service.submit_work(INTAKE_SAME_INTENT)
    proposed = app_facts.service.refine_work(submitted.work_id)
    assert proposed.artifact_target is not None
    target_a = proposed.artifact_target.path
    target_b = "docs/architecture/human-approved-orchestration.md"

    overridden = app_facts.service.refine_work(
        submitted.work_id,
        WorkRefinementRequest(expected_artifact_path=target_b),
    )
    assert overridden.artifact_target is not None
    assert overridden.artifact_target.path == target_b
    app_facts.service.approve_work(
        submitted.work_id,
        authority_identity="architecture-lead:override-test",
    )
    binding = _runtime_binding(app_facts, submitted.work_id)
    assert binding is not None
    with app_facts.database.unit_of_work() as unit_of_work:
        work_unit = RuntimeStore(unit_of_work.session).work_unit(binding.work_unit_id)
    assert work_unit is not None
    serialized = work_unit.model_dump_json()
    assert target_b in serialized
    assert target_a not in serialized


def _work_record(facts: AppFacts, work_id):
    with facts.database.unit_of_work() as unit_of_work:
        record = ProductStore(unit_of_work.session).work(work_id)
    assert record is not None
    return record


def _runtime_binding(facts: AppFacts, work_id):
    with facts.database.unit_of_work() as unit_of_work:
        binding = ProductStore(unit_of_work.session).runtime_binding(work_id)
    return binding


def _service_with_deterministic_capabilities(facts: AppFacts, work_id):
    record = _work_record(facts, work_id)
    assert record.expected_artifact_path is not None
    assert record.verification_expectation is not None
    executor = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=(
                DeterministicFileOperation(
                    operation=DeterministicFileOperationType.CREATE,
                    repository_relative_path=record.expected_artifact_path,
                    content="governed MVP product result\n",
                ),
            ),
            reported_outcome=ProviderReportedOutcome.SUCCESS,
            summary="deterministic MVP-APP-1 execution",
        )
    )
    verifier = DeterministicVerificationProvider(
        {record.verification_expectation: VerificationResultValue.PASS}
    )
    return (
        WorkApplicationService(
            facts.database,
            workspace_root=facts.workspace_root,
            executor=executor,
            verifier=verifier,
        ),
        executor,
    )


def _advance_to_candidate_attention(facts: AppFacts, work_id):
    service, executor = _service_with_deterministic_capabilities(facts, work_id)
    for _ in range(12):
        projection = service.advance_work(work_id)
        attention = service.list_attention(work_id=work_id)
        if attention and attention[0].kind is AttentionKind.CANDIDATE_AUTHORIZATION:
            return service, executor, projection, attention[0]
    raise AssertionError("candidate Attention was not reached")


def _code_executor_service(
    facts: AppFacts,
    operations: tuple[DeterministicFileOperation, ...],
) -> tuple[WorkApplicationService, DeterministicTestExecutor]:
    executor = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=operations,
            reported_outcome=ProviderReportedOutcome.SUCCESS,
            summary="deterministic bounded code execution",
        )
    )
    return (
        WorkApplicationService(
            facts.database,
            workspace_root=facts.workspace_root,
            executor=executor,
            verifier=ContractDrivenRepositoryVerifier(facts.database),
        ),
        executor,
    )


def _advance_until_governed_stop(
    service: WorkApplicationService,
    work_id,
):
    projection = service.get_work(work_id)
    for _ in range(20):
        projection = service.advance_work(work_id)
        attention = service.list_attention(work_id=work_id)
        if projection.status is WorkStatus.BLOCKED or (
            attention and attention[0].kind is AttentionKind.CANDIDATE_AUTHORIZATION
        ):
            return projection, attention
    raise AssertionError("code Work did not reach a governed stop")


def test_code_01_02_07_08_09_10_11_13_15_17_18_20_21_happy_path(
    app_facts: AppFacts,
) -> None:
    submitted = app_facts.service.submit_work(
        "Modify Python source code behavior and its unit test"
    )
    unresolved = app_facts.service.refine_work(submitted.work_id)
    assert unresolved.target_kind.value == "CODE_WORK"
    assert unresolved.status is WorkStatus.NEEDS_REFINEMENT
    assert unresolved.artifact_target is None
    assert unresolved.change_proposal is not None
    assert unresolved.change_contract is None

    draft = app_facts.service.refine_work(
        submitted.work_id,
        WorkRefinementRequest(
            code_exact_targets=(
                "src/spg_example.py",
                "tests/test_spg_example.py",
            )
        ),
    )
    assert draft.status is WorkStatus.AWAITING_APPROVAL
    assert draft.change_proposal is not None
    assert draft.change_contract is None
    assert draft.artifact_target is None
    assert draft.production_plan is not None
    assert draft.production_plan.change_proposal == draft.change_proposal
    assert tuple(
        item.identity for item in draft.change_proposal.verification_obligations
    ) == (
        "PATH_SCOPE",
        "GIT_DIFF_CHECK",
        "PYTHON_COMPILE",
        "IMPORT_CHECK:spg_example",
        "PYTEST_TARGET:tests/test_spg_example.py",
    )

    approved = app_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:code-contract",
    )
    assert approved.change_contract is not None
    assert approved.change_contract.source_proposal_id == draft.change_proposal.proposal_id
    assert (
        approved.change_contract.source_proposal_fingerprint
        == draft.change_proposal.proposal_fingerprint
    )
    binding = _runtime_binding(app_facts, draft.work_id)
    assert binding is not None
    with app_facts.database.unit_of_work() as unit_of_work:
        work_unit = RuntimeStore(unit_of_work.session).work_unit(binding.work_unit_id)
        plan_count = unit_of_work.session.scalar(
            select(func.count()).select_from(plan_revisions)
        )
        work_unit_count = unit_of_work.session.scalar(
            select(func.count()).select_from(production_work_units)
        )
    assert work_unit is not None
    assert plan_count == work_unit_count == 1
    assert work_unit.completion_contract.change_contract == approved.change_contract
    instruction = render_governed_instruction(
        work_unit.objective,
        work_unit.completion_contract,
    )
    assert "src/spg_example.py" in instruction
    assert "tests/test_spg_example.py" in instruction
    assert "Never widen the Change Contract yourself" in instruction

    service, executor = _code_executor_service(
        app_facts,
        (
            DeterministicFileOperation(
                operation=DeterministicFileOperationType.MODIFY,
                repository_relative_path="src/spg_example.py",
                content='def value() -> str:\n    return "new"\n',
            ),
            DeterministicFileOperation(
                operation=DeterministicFileOperationType.MODIFY,
                repository_relative_path="tests/test_spg_example.py",
                content=(
                    "from spg_example import value\n\n\n"
                    "def test_value() -> None:\n    assert value() == \"new\"\n"
                ),
            ),
        ),
    )
    projection, attention = _advance_until_governed_stop(service, draft.work_id)
    assert projection.status is WorkStatus.NEEDS_ATTENTION
    assert len(attention) == 1
    assert attention[0].kind is AttentionKind.CANDIDATE_AUTHORIZATION
    with app_facts.database.unit_of_work() as unit_of_work:
        summary = ProductStore(unit_of_work.session).runtime_summary(binding)
    assert summary.artifact_paths == (
        "src/spg_example.py",
        "tests/test_spg_example.py",
    )
    assert summary.completion_outcome == "PRODUCED"
    assert set(summary.verification_results) == {VerificationResultValue.PASS.value}
    assert summary.candidate_id is not None
    assert executor.dispatch_count == 1

    service.resolve_attention(
        attention[0].id,
        AttentionResolutionRequest(
            action=AttentionAction.AUTHORIZE,
            authority_identity="human:code-candidate",
            rationale="authorize exact bounded code Candidate",
        ),
    )
    for _ in range(4):
        projection = service.advance_work(draft.work_id)
        if projection.status is WorkStatus.COMPLETED:
            break
    assert projection.status is WorkStatus.COMPLETED
    assert service.get_work_result(draft.work_id).trusted_result is True
    with app_facts.database.unit_of_work() as unit_of_work:
        completed_summary = ProductStore(unit_of_work.session).runtime_summary(binding)
    assert completed_summary.authorization_id is not None
    assert completed_summary.integration_state == "CONVERGED"
    assert completed_summary.runtime_commit_id is not None
    assert 'return "new"' in _git(
        app_facts.repository,
        "show",
        "refs/heads/main:src/spg_example.py",
    )


def test_code_12_13_14_19_20_unauthorized_path_fails_without_candidate(
    app_facts: AppFacts,
) -> None:
    submitted = app_facts.service.submit_work(
        "Modify only src/spg_example.py to return a new value"
    )
    draft = app_facts.service.refine_work(submitted.work_id)
    assert draft.change_proposal is not None
    assert draft.change_contract is None
    app_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:code-contract",
    )
    service, executor = _code_executor_service(
        app_facts,
        (
            DeterministicFileOperation(
                operation=DeterministicFileOperationType.MODIFY,
                repository_relative_path="src/spg_example.py",
                content='def value() -> str:\n    return "new"\n',
            ),
            DeterministicFileOperation(
                operation=DeterministicFileOperationType.CREATE,
                repository_relative_path="README.md",
                content="unauthorized\n",
            ),
        ),
    )
    projection, _ = _advance_until_governed_stop(service, draft.work_id)
    binding = _runtime_binding(app_facts, draft.work_id)
    assert binding is not None
    with app_facts.database.unit_of_work() as unit_of_work:
        summary = ProductStore(unit_of_work.session).runtime_summary(binding)
    assert projection.status is WorkStatus.BLOCKED
    assert summary.completion_outcome == "PRODUCED"
    assert summary.artifact_paths == ("README.md", "src/spg_example.py")
    results = dict(
        zip(summary.verification_obligations, summary.verification_results, strict=True)
    )
    assert results["PATH_SCOPE"] == VerificationResultValue.FAIL.value
    assert summary.candidate_id is None
    assert service.get_work_result(draft.work_id).trusted_result is False
    assert executor.dispatch_count == 1


def test_code_13_15_17_19_20_targeted_pytest_failure_prevents_candidate(
    app_facts: AppFacts,
) -> None:
    submitted = app_facts.service.submit_work(
        "Modify src/spg_example.py and tests/test_spg_example.py"
    )
    draft = app_facts.service.refine_work(submitted.work_id)
    assert draft.change_proposal is not None
    assert draft.change_contract is None
    app_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:code-contract",
    )
    service, executor = _code_executor_service(
        app_facts,
        (
            DeterministicFileOperation(
                operation=DeterministicFileOperationType.MODIFY,
                repository_relative_path="src/spg_example.py",
                content='def value() -> str:\n    return "bad"\n',
            ),
            DeterministicFileOperation(
                operation=DeterministicFileOperationType.MODIFY,
                repository_relative_path="tests/test_spg_example.py",
                content=(
                    "from spg_example import value\n\n\n"
                    "def test_value() -> None:\n    assert value() == \"expected\"\n"
                ),
            ),
        ),
    )
    projection, _ = _advance_until_governed_stop(service, draft.work_id)
    binding = _runtime_binding(app_facts, draft.work_id)
    assert binding is not None
    with app_facts.database.unit_of_work() as unit_of_work:
        summary = ProductStore(unit_of_work.session).runtime_summary(binding)
    assert projection.status is WorkStatus.BLOCKED
    assert summary.completion_outcome == "PRODUCED"
    results = dict(
        zip(summary.verification_obligations, summary.verification_results, strict=True)
    )
    assert results["PATH_SCOPE"] == VerificationResultValue.PASS.value
    assert results["GIT_DIFF_CHECK"] == VerificationResultValue.PASS.value
    assert results["PYTHON_COMPILE"] == VerificationResultValue.PASS.value
    assert results["IMPORT_CHECK:spg_example"] == VerificationResultValue.PASS.value
    assert (
        results["PYTEST_TARGET:tests/test_spg_example.py"]
        == VerificationResultValue.FAIL.value
    )
    assert summary.candidate_id is None
    assert service.get_work_result(draft.work_id).trusted_result is False
    assert executor.dispatch_count == 1


def test_refcode_03_04_15_16_17_human_edits_proposal_then_admits_contract(
    app_facts: AppFacts,
) -> None:
    submitted = app_facts.service.submit_work(
        "Modify Python source code behavior and its unit test"
    )
    first = app_facts.service.refine_work(
        submitted.work_id,
        WorkRefinementRequest(code_exact_targets=("src/spg_example.py",)),
    )
    assert first.change_proposal is not None
    assert first.change_contract is None
    assert _runtime_binding(app_facts, first.work_id) is None

    edited = app_facts.service.refine_work(
        first.work_id,
        WorkRefinementRequest(
            code_exact_targets=(
                "src/spg_example.py",
                "tests/test_spg_example.py",
            )
        ),
    )
    assert edited.change_proposal is not None
    assert tuple(target.path for target in edited.change_proposal.required_targets) == (
        "src/spg_example.py",
        "tests/test_spg_example.py",
    )
    assert edited.change_contract is None
    assert _runtime_binding(app_facts, edited.work_id) is None

    approved = app_facts.service.approve_work(
        edited.work_id,
        authority_identity="human:proposal-admission",
    )
    assert approved.change_contract is not None
    assert approved.change_contract.source_proposal_id == edited.change_proposal.proposal_id
    assert (
        approved.change_contract.source_proposal_fingerprint
        == edited.change_proposal.proposal_fingerprint
    )
    assert _runtime_binding(app_facts, edited.work_id) is not None


def test_refcode_14_stale_proposal_cannot_be_admitted(
    app_facts: AppFacts,
) -> None:
    submitted = app_facts.service.submit_work(
        "Modify src/spg_example.py"
    )
    draft = app_facts.service.refine_work(submitted.work_id)
    assert draft.change_proposal is not None
    assert draft.production_plan is not None
    stale = draft.change_proposal.model_copy(update={"source_revision": "f" * 40})
    stale_plan = draft.production_plan.model_copy(
        update={"change_proposal": stale}
    )
    with app_facts.database.unit_of_work() as unit_of_work:
        ProductStore(unit_of_work.session).update_work(
            draft.work_id,
            {
                "code_change_proposal": stale.model_dump(mode="json"),
                "production_plan_proposal": stale_plan.model_dump(mode="json"),
            },
        )
        unit_of_work.commit()

    with pytest.raises(ProductInvariantViolation, match="stale"):
        app_facts.service.approve_work(
            draft.work_id,
            authority_identity="human:stale-proposal",
        )
    assert _runtime_binding(app_facts, draft.work_id) is None


def test_mvp_app_migration_downgrade_and_reupgrade(
    postgres_database: Database,
) -> None:
    config = _migration_config(postgres_database)
    command.downgrade(config, "20260902_13")
    assert not (
        PRODUCT_TABLE_NAMES & set(inspect(postgres_database.engine).get_table_names())
    )
    command.upgrade(config, "head")
    assert PRODUCT_TABLE_NAMES <= set(
        inspect(postgres_database.engine).get_table_names()
    )


def test_work_01_goal_exists_independently_and_work_21_goal_projection(
    app_facts: AppFacts,
) -> None:
    goal = app_facts.service.create_goal("MVP")
    empty = app_facts.service.get_goal_projection(goal.id)
    assert empty.work_count == 0
    first = _draft(app_facts, goal_id=goal.id)
    second = app_facts.service.submit_work("A second independent Work", goal_id=goal.id)
    projection = app_facts.service.get_goal_projection(goal.id)
    assert projection.work_count == 2
    assert projection.works_by_status[WorkStatus.AWAITING_APPROVAL] == 1
    assert projection.works_by_status[WorkStatus.DRAFT] == 1
    assert {item.work_id for item in projection.recent_works} == {
        first.work_id,
        second.work_id,
    }


def test_work_02_work_without_goal_and_work_20_history_is_independent(
    app_facts: AppFacts,
) -> None:
    first_raw = "First exact source requirement\nwith original wording."
    first = app_facts.service.submit_work(first_raw)
    second = app_facts.service.submit_work("Second Work")
    assert first.goal_id is None
    assert second.goal_id is None
    assert first.work_id != second.work_id
    assert _work_record(app_facts, first.work_id).raw_user_requirement == first_raw


def test_work_03_and_08_work_is_not_resource_or_project(
    app_facts: AppFacts,
) -> None:
    work = app_facts.service.submit_work("Keep Work goal-centric")
    record = _work_record(app_facts, work.work_id)
    assert record.id != app_facts.resource.id
    assert "project_id" not in record.model_fields
    assert "resource_id" not in record.model_fields


def test_work_04_raw_request_is_source_and_work_05_tags_are_mutable(
    app_facts: AppFacts,
) -> None:
    raw = "Preserve this raw request exactly.  \nDo not normalize it."
    work = app_facts.service.submit_work(raw, tags=("mvp", "docs"))
    before_baseline = RuntimeService(app_facts.database).current_baseline()
    updated = app_facts.service.update_work_tags(work.work_id, ("review", "mvp"))
    record = _work_record(app_facts, work.work_id)
    assert record.raw_user_requirement == raw
    assert updated.tags == ("mvp", "review")
    assert RuntimeService(app_facts.database).current_baseline().id == before_baseline.id
    assert _runtime_binding(app_facts, work.work_id) is None


def test_work_06_scope_binding_work_07_policy_and_work_22_structural_many(
    app_facts: AppFacts,
) -> None:
    draft = _draft(app_facts)
    second = app_facts.service.register_engineering_resource(
        repository_identity="test://secondary-repository",
        location_ref=str(app_facts.repository),
        authoritative_ref="refs/heads/main",
        context_references=(
            EngineeringContextReference(
                semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                repository_relative_path="AI_context.md",
            ),
        ),
        is_default=False,
    )
    with app_facts.database.unit_of_work() as unit_of_work:
        store = ProductStore(unit_of_work.session)
        scope = store.scope_for_work(draft.work_id)
        assert scope is not None
        timestamp = scope.updated_at
        store.replace_scope(
            scope_values={
                "id": scope.id,
                "work_id": draft.work_id,
                "summary": scope.summary,
                "fingerprint": "a" * 64,
                "condition": EngineeringScopeCondition.PROPOSED.value,
                "created_at": scope.created_at,
                "updated_at": timestamp,
            },
            binding_values=(
                {
                    "id": uuid4(),
                    "engineering_scope_id": scope.id,
                    "resource_id": app_facts.resource.id,
                    "condition": ResourceBindingCondition.PROPOSED.value,
                    "created_at": timestamp,
                },
                {
                    "id": uuid4(),
                    "engineering_scope_id": scope.id,
                    "resource_id": second.id,
                    "condition": ResourceBindingCondition.PROPOSED.value,
                    "created_at": timestamp,
                },
            ),
        )
        structural_scope = store.scope_for_work(draft.work_id)
        unit_of_work.commit()
    assert structural_scope is not None
    assert len(structural_scope.bindings) == 2
    with pytest.raises(ProductInvariantViolation, match="exactly one"):
        app_facts.service.approve_work(
            draft.work_id,
            authority_identity="human:test",
        )


def test_work_09_one_pwu_work_12_admission_and_work_23_resource_binding(
    app_facts: AppFacts,
) -> None:
    draft = _draft(app_facts)
    approved = app_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:test",
        rationale="admit exact Work draft",
    )
    binding = _runtime_binding(app_facts, draft.work_id)
    assert approved.status is WorkStatus.READY
    assert binding is not None
    assert binding.resource_id == app_facts.resource.id
    with app_facts.database.engine.connect() as connection:
        assert connection.execute(
            select(production_runs.c.id).where(
                production_runs.c.id == binding.production_run_id
            )
        ).scalar_one() == binding.production_run_id
        assert connection.execute(
            select(production_work_units.c.id).where(
                production_work_units.c.id == binding.work_unit_id
            )
        ).scalar_one() == binding.work_unit_id
        governance = connection.execute(
            select(governance_records.c.decision_type).where(
                governance_records.c.id == binding.governance_record_id
            )
        ).scalar_one()
    assert governance == "ADMIT_WORK_DRAFT"


def test_work_10_broad_work_requires_refinement(app_facts: AppFacts) -> None:
    work = app_facts.service.submit_work(
        "Rewrite the whole entire platform and all systems in multiple repositories"
    )
    refined = app_facts.service.refine_work(work.work_id)
    assert refined.status is WorkStatus.NEEDS_REFINEMENT
    assert _runtime_binding(app_facts, work.work_id) is None


def test_work_11_draft_cannot_execute_and_work_13_projection_is_not_authority(
    app_facts: AppFacts,
) -> None:
    draft = _draft(app_facts)
    before = app_facts.service.advance_work(draft.work_id)
    assert before.status is WorkStatus.AWAITING_APPROVAL
    assert _runtime_binding(app_facts, draft.work_id) is None
    with app_facts.database.engine.connect() as connection:
        assert connection.execute(select(execution_attempts.c.id)).first() is None
    assert "status" in before.model_fields
    assert "condition" not in before.model_fields


def test_work_14_15_18_24_provider_report_is_not_completion(
    app_facts: AppFacts,
) -> None:
    draft = _draft(app_facts)
    app_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:test",
    )
    executor = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=(),
            reported_outcome=ProviderReportedOutcome.SUCCESS,
            summary="self-report success without production change",
        )
    )
    service = WorkApplicationService(
        app_facts.database,
        workspace_root=app_facts.workspace_root,
        executor=executor,
    )
    service.advance_work(draft.work_id)
    service.advance_work(draft.work_id)
    blocked = service.advance_work(draft.work_id)
    assert blocked.status is WorkStatus.BLOCKED
    assert blocked.status is not WorkStatus.COMPLETED
    repeated = service.advance_work(draft.work_id)
    assert repeated.status is WorkStatus.BLOCKED
    with app_facts.database.engine.connect() as connection:
        report = connection.execute(
            select(provider_execution_reports.c.outcome)
        ).scalar_one()
        observation = connection.execute(
            select(repository_observations.c.id)
        ).scalar_one()
        completion_count = connection.scalar(
            select(func.count()).select_from(completion_evaluations)
        )
    assert report == ProviderReportedOutcome.SUCCESS.value
    assert observation is not None
    assert completion_count == 0
    assert executor.dispatch_count == 1


def test_stopped_unknown_none_reality_projects_governed_attention(
    app_facts: AppFacts,
) -> None:
    draft = _draft(app_facts)
    app_facts.service.approve_work(
        draft.work_id,
        authority_identity="human:test",
    )
    executor = DeterministicTestExecutor(
        DeterministicExecutionSpecification(
            operations=(),
            reported_outcome=ProviderReportedOutcome.UNKNOWN,
            summary="provider stopped before completion",
        )
    )
    service = WorkApplicationService(
        app_facts.database,
        workspace_root=app_facts.workspace_root,
        executor=executor,
    )

    service.advance_work(draft.work_id)
    service.advance_work(draft.work_id)
    stopped = service.advance_work(draft.work_id)

    assert stopped.status is WorkStatus.BLOCKED
    assert stopped.current_production_step == "EXECUTION_STOPPED"
    assert stopped.human_attention_required is True
    assert "Evaluate Completion" not in stopped.what_happens_next
    attention = service.list_attention(work_id=draft.work_id)
    assert len(attention) == 1
    assert attention[0].kind is AttentionKind.PRODUCTION_BLOCKED
    assert attention[0].available_actions == ()
    assert attention[0].recommended_action is None
    assert service.get_work_result(draft.work_id).trusted_result is False
    assert executor.dispatch_count == 1


def test_work_16_attention_and_work_17_authority_delegation(
    app_facts: AppFacts,
) -> None:
    draft = _draft(app_facts)
    draft_attention = app_facts.service.list_attention(work_id=draft.work_id)
    assert draft_attention[0].kind is AttentionKind.WORK_DRAFT_APPROVAL
    app_facts.service.resolve_attention(
        draft_attention[0].id,
        AttentionResolutionRequest(
            action=AttentionAction.APPROVE,
            authority_identity="human:test",
        ),
    )
    service, _, _, candidate_attention = _advance_to_candidate_attention(
        app_facts,
        draft.work_id,
    )
    assert candidate_attention.available_actions == (AttentionAction.AUTHORIZE,)
    resolved = service.resolve_attention(
        candidate_attention.id,
        AttentionResolutionRequest(
            action=AttentionAction.AUTHORIZE,
            authority_identity="human:test",
            rationale="authorize exact Candidate",
        ),
    )
    assert resolved.status is WorkStatus.RUNNING
    for _ in range(4):
        resolved = service.advance_work(draft.work_id)
        if resolved.status is WorkStatus.COMPLETED:
            break
    assert resolved.status is WorkStatus.COMPLETED


def test_work_19_result_projection_does_not_invent_evidence(
    app_facts: AppFacts,
) -> None:
    work = app_facts.service.submit_work("No execution yet")
    result = app_facts.service.get_work_result(work.work_id)
    assert result.produced_artifacts == ()
    assert result.verification_summary == ()
    assert result.repository_state is None
    assert result.trusted_result is False


def _truncate(database: Database) -> None:
    names = ", ".join(f'"{name}"' for name in ALL_TABLE_NAMES)
    with database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {names} CASCADE")


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
