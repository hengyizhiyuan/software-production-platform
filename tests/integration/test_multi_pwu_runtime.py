"""Persisted multi-PWU plan facts and exact initial readiness."""

import os
import subprocess
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest

from spg.application.runtime import RuntimeService
from spg.application.preparation import PreparationService
from spg.application.execution import ExecutionService
from spg.application.completion import CompletionService
from spg.application.verification import VerificationService
from spg.application.governance import CandidateGovernanceService
from spg.application.integration import RepositoryIntegrationService
from spg.application.runtime_commit import RuntimeCommitService
from spg.domain.preparation import ContextArtifactSelection, ContextPackageRequest, ContextSemanticRole, ExecutorBinding
from spg.domain.execution import ProviderReportedOutcome
from spg.domain.verification import VerificationResultValue
from spg.domain.governance import CandidateAuthorizationScope, CandidateSealRequest, HumanAuthorizationRequest
from spg.domain.integration import RepositoryIntegrationRequest
from spg.domain.runtime_commit import RuntimeCommitRequest
from spg.domain.planning import (
    OnePwuFitClassification, PlannedArtifactOperation, ProductionNodeKind,
    ProductionPlanArtifactTarget, ProductionPlanGraph, ProductionPlanNode,
    ProductionPlanningRequest,
)
from spg.domain.runtime import BootstrapRequest, CompletionContract, InitialRunRequest, ProductionHorizon, RuntimeInvariantViolation
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence import runtime_tables
from spg.providers.rule_based_planner import RuleBasedProductionPlanner
from spg.providers.deterministic_executor import DeterministicExecutionSpecification, DeterministicFileOperation, DeterministicFileOperationType, DeterministicTestExecutor
from spg.providers.deterministic_verifier import DeterministicVerificationProvider


pytestmark = pytest.mark.postgresql


@pytest.fixture(autouse=True)
def isolate_multi_pwu_facts(postgres_database, monkeypatch):
    monkeypatch.setenv("SPG_DATABASE_URL", os.environ["SPG_TEST_DATABASE_URL"])
    command.upgrade(Config(Path(__file__).resolve().parents[2] / "alembic.ini"), "head")
    names = ", ".join(f'"{table.name}"' for table in runtime_tables)
    with postgres_database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {names} CASCADE")
    try:
        yield
    finally:
        with postgres_database.engine.begin() as connection:
            connection.exec_driver_sql(f"TRUNCATE TABLE {names} CASCADE")


def _git(path: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True).stdout.strip()


def test_multi_pwu_plan_persists_three_units_and_blocks_join_before_parents(postgres_database, tmp_path, monkeypatch):
    monkeypatch.setenv("SPG_DATABASE_URL", os.environ["SPG_TEST_DATABASE_URL"])
    command.upgrade(Config(Path(__file__).resolve().parents[2] / "alembic.ini"), "head")
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "README.md").write_text("initial\n")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "initial")
    runtime = RuntimeService(postgres_database)
    identity = f"test://multi-pwu/{uuid4()}"
    baseline = runtime.bootstrap_trusted_baseline(BootstrapRequest(
        repository_path=repository, repository_identity=identity,
        repository_ref="refs/heads/main", authority_identity="human:test",
    )).snapshot
    targets = tuple(ProductionPlanArtifactTarget(path=f"docs/{stem}.md", operation=PlannedArtifactOperation.CREATE)
                    for stem in ("auth", "billing"))
    plan = RuleBasedProductionPlanner().propose(ProductionPlanningRequest(
        work_id=uuid4(), admitted_requirement="Implement independent auth and billing guides",
        desired_outcome="Both guides exist", production_objective="Produce two guides",
        artifact_targets=targets, verification_expectation="Verify both guides",
        engineering_scope_summary="one repository", engineering_resource_id=uuid4(),
        repository_identity=identity, source_baseline_id=baseline.id,
        source_revision=baseline.repository_revision,
    ))
    assert plan.graph is not None
    spine = runtime.create_initial_runtime_spine(InitialRunRequest(
        intent_ref="work:multi", goal="Both guides exist",
        production_horizon=ProductionHorizon.DOCUMENTATION,
        initial_work_unit_objective="Produce two guides",
        completion_contract=CompletionContract(
            required_outputs=tuple(item.path for item in targets),
            required_changes=tuple(item.path for item in targets),
            verification_obligations=("Verify both guides",),
            production_plan=plan,
        ),
    ))
    with postgres_database.unit_of_work() as uow:
        store = RuntimeStore(uow.session)
        units = store.work_units_for_plan(spine.plan_revision.id)
        join = store.work_unit_for_node(spine.plan_revision.id, "pwu:join")
    assert len(units) == 3
    assert {unit.source_baseline_id for unit in units if unit.node_id != "pwu:join"} == {baseline.id}
    assert join is not None and join.source_baseline_id is None
    assert spine.run.integrated_baseline_id == baseline.id
    with pytest.raises(RuntimeInvariantViolation, match="unresolved"):
        runtime.create_initial_attempt(join.id)
    assert runtime.create_initial_attempt(spine.work_unit.id).source_baseline_id == baseline.id
    with pytest.raises(RuntimeError, match="Cannot downgrade versioned multi-PWU"):
        command.downgrade(Config(Path(__file__).resolve().parents[2] / "alembic.ini"), "20260925_49")
    with postgres_database.engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "20260926_57"


def test_serial_baseline_progression_and_replan_preserve_completed_history(postgres_database, tmp_path):
    """MPWU-Q1/Q9/Q11: A is verified before B starts; B/C can be revised."""

    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "README.md").write_text("initial\n")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "initial")
    runtime = RuntimeService(postgres_database)
    identity = f"test://serial/{uuid4()}"
    baseline = runtime.bootstrap_trusted_baseline(BootstrapRequest(
        repository_path=repository, repository_identity=identity,
        repository_ref="refs/heads/main", authority_identity="human:test",
    )).snapshot
    targets = tuple(ProductionPlanArtifactTarget(
        path=f"docs/{name}.md", operation=PlannedArtifactOperation.CREATE,
    ) for name in ("alpha", "beta", "gamma"))

    def plan_for(paths, objective):
        return RuleBasedProductionPlanner().propose(ProductionPlanningRequest(
            work_id=uuid4(), admitted_requirement="shared interface requires serial baseline progression",
            desired_outcome="three related guides", production_objective=objective,
            artifact_targets=paths, verification_expectation="Verify guides",
            engineering_scope_summary="one repository", engineering_resource_id=uuid4(),
            repository_identity=identity, source_baseline_id=baseline.id,
            source_revision=baseline.repository_revision,
        ))

    plan = plan_for(targets, "Produce three related guides")
    assert plan.graph is not None
    contract = CompletionContract(
        required_outputs=tuple(item.path for item in targets),
        required_changes=tuple(item.path for item in targets),
        verification_obligations=("Verify guides",), production_plan=plan,
    )
    spine = runtime.create_initial_runtime_spine(InitialRunRequest(
        intent_ref="work:serial", goal="three related guides",
        production_horizon=ProductionHorizon.DOCUMENTATION,
        initial_work_unit_objective="Produce three related guides",
        completion_contract=contract,
    ))
    with postgres_database.unit_of_work() as uow:
        store = RuntimeStore(uow.session)
        second = store.work_unit_for_node(spine.plan_revision.id, "pwu:2")
        third = store.work_unit_for_node(spine.plan_revision.id, "pwu:3")
    assert second.source_baseline_id is None and third.source_baseline_id is None
    with pytest.raises(RuntimeInvariantViolation, match="unresolved"):
        runtime.create_initial_attempt(second.id)

    preparation = PreparationService(postgres_database)
    execution = ExecutionService(postgres_database, preparation=preparation)
    completion = CompletionService(postgres_database, observer=execution.observer)
    verification = VerificationService(postgres_database, observer=execution.observer)
    attempt = runtime.create_initial_attempt(spine.work_unit.id)
    package = preparation.assemble_context_package(
        spine.work_unit.id, repository, ContextPackageRequest(artifacts=(
            ContextArtifactSelection(
                semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                repository_relative_path="README.md",
            ),
        )),
    )
    preparation.prepare_attempt(attempt.id, package.id, ExecutorBinding(
        binding_ref="binding:serial", capability_identity="capability:executor",
        profile_identity="profile:local-fvs",
    ), repository, tmp_path / "attempt-workspaces")
    dispatched = execution.dispatch_and_observe(attempt.id, DeterministicTestExecutor(
        DeterministicExecutionSpecification(operations=(DeterministicFileOperation(
            operation=DeterministicFileOperationType.CREATE,
            repository_relative_path="docs/alpha.md", content="alpha\n",
        ),), reported_outcome=ProviderReportedOutcome.SUCCESS),
    ))
    evaluated = completion.evaluate_observation(dispatched.observation.id)
    proposed = verification.create_proposed_snapshot(evaluated.evaluation.id)
    verification.verify_obligation(proposed.id, "Verify guides", DeterministicVerificationProvider(
        {"Verify guides": VerificationResultValue.PASS},
    ))
    verification.evaluate_admissibility(proposed.id)
    output = runtime.publish_verified_pwu_output(spine.work_unit.id, proposed.id)
    with postgres_database.unit_of_work() as uow:
        store = RuntimeStore(uow.session)
        second = store.work_unit_for_node(spine.plan_revision.id, "pwu:2")
        third = store.work_unit_for_node(spine.plan_revision.id, "pwu:3")
        run = store.run(spine.run.id)
    assert run.integrated_baseline_id == output.id
    assert second.source_baseline_id == output.id
    assert third.source_baseline_id is None
    revised = plan_for(targets[1:], "Revise the remaining two guides")
    new_spine = runtime.revise_production_plan(spine.run.id, contract.model_copy(update={
        "production_plan": revised,
    }), reason="observed design Reality changed")
    assert new_spine.plan_revision.revision_number == 2
    assert new_spine.plan_revision.supersedes_plan_revision_id == spine.plan_revision.id
    assert new_spine.plan_revision.graph.starting_baseline_id == output.id
    assert new_spine.work_unit.source_baseline_id == output.id
    assert runtime.create_initial_attempt(new_spine.work_unit.id).source_baseline_id == output.id
    with postgres_database.unit_of_work() as uow:
        store = RuntimeStore(uow.session)
        previous_a = store.work_unit(spine.work_unit.id)
        previous_b = store.work_unit(second.id)
        previous_c = store.work_unit(third.id)
        previous_plan = store.plan_revision(spine.plan_revision.id)
    assert previous_a.verified_output_baseline_id == output.id
    assert previous_b.condition.value == previous_c.condition.value == "SUPERSEDED"
    assert previous_plan.condition.value == "SUPERSEDED"


def test_three_serial_pwus_inherit_exact_verified_predecessor_baselines(postgres_database, tmp_path):
    """MPWU-Q1: B0 -> A -> B -> C is one executable lineage."""

    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "README.md").write_text("initial\n")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "initial")
    runtime = RuntimeService(postgres_database)
    identity = f"test://serial-chain/{uuid4()}"
    baseline = runtime.bootstrap_trusted_baseline(BootstrapRequest(
        repository_path=repository, repository_identity=identity,
        repository_ref="refs/heads/main", authority_identity="human:test",
    )).snapshot
    paths = ("docs/alpha.md", "docs/beta.md", "docs/gamma.md")
    plan = RuleBasedProductionPlanner().propose(ProductionPlanningRequest(
        work_id=uuid4(), admitted_requirement="shared interface serial work",
        desired_outcome="all three guides", production_objective="Produce three guides",
        artifact_targets=tuple(ProductionPlanArtifactTarget(
            path=path, operation=PlannedArtifactOperation.CREATE,
        ) for path in paths),
        verification_expectation="Verify guides", engineering_scope_summary="one repository",
        engineering_resource_id=uuid4(), repository_identity=identity,
        source_baseline_id=baseline.id, source_revision=baseline.repository_revision,
    ))
    spine = runtime.create_initial_runtime_spine(InitialRunRequest(
        intent_ref="work:serial-chain", goal="all three guides",
        production_horizon=ProductionHorizon.DOCUMENTATION,
        initial_work_unit_objective="Produce three guides",
        completion_contract=CompletionContract(
            required_outputs=paths, required_changes=paths,
            verification_obligations=("Verify guides",), production_plan=plan,
        ),
    ))
    preparation = PreparationService(postgres_database)
    execution = ExecutionService(postgres_database, preparation=preparation)
    completion = CompletionService(postgres_database, observer=execution.observer)
    verification = VerificationService(postgres_database, observer=execution.observer)
    predecessor = baseline
    for index, path in enumerate(paths, start=1):
        with postgres_database.unit_of_work() as uow:
            store = RuntimeStore(uow.session)
            unit = store.work_unit_for_node(spine.plan_revision.id, f"pwu:{index}")
            run = store.run(spine.run.id)
        assert unit.source_baseline_id == predecessor.id
        assert run.integrated_baseline_id == predecessor.id
        attempt = runtime.create_initial_attempt(unit.id)
        package = preparation.assemble_context_package(
            unit.id, repository, ContextPackageRequest(artifacts=(ContextArtifactSelection(
                semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                repository_relative_path="README.md",
            ),)),
        )
        preparation.prepare_attempt(attempt.id, package.id, ExecutorBinding(
            binding_ref="binding:serial-chain", capability_identity="capability:executor",
            profile_identity="profile:local-fvs",
        ), repository, tmp_path / "attempt-workspaces")
        dispatched = execution.dispatch_and_observe(attempt.id, DeterministicTestExecutor(
            DeterministicExecutionSpecification(operations=(DeterministicFileOperation(
                operation=DeterministicFileOperationType.CREATE,
                repository_relative_path=path, content=f"guide {index}\n",
            ),), reported_outcome=ProviderReportedOutcome.SUCCESS),
        ))
        evaluated = completion.evaluate_observation(dispatched.observation.id)
        proposed = verification.create_proposed_snapshot(evaluated.evaluation.id)
        verification.verify_obligation(proposed.id, "Verify guides", DeterministicVerificationProvider(
            {"Verify guides": VerificationResultValue.PASS},
        ))
        verification.evaluate_admissibility(proposed.id)
        predecessor = runtime.publish_verified_pwu_output(unit.id, proposed.id)
        assert runtime.publish_verified_pwu_output(unit.id, proposed.id).id == predecessor.id
    with postgres_database.unit_of_work() as uow:
        run = RuntimeStore(uow.session).run(spine.run.id)
    assert run.integrated_baseline_id == predecessor.id
    for path in paths:
        assert _git(repository, "show", f"{predecessor.repository_revision}:{path}").startswith("guide")


def test_join_conflict_requires_changed_verified_resolution_tree(postgres_database, tmp_path):
    """MPWU-Q5: a conflicted tree cannot be trusted; a resolved tree can."""

    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "README.md").write_text("initial\n")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "initial")
    runtime = RuntimeService(postgres_database)
    identity = f"test://conflict/{uuid4()}"
    baseline = runtime.bootstrap_trusted_baseline(BootstrapRequest(
        repository_path=repository, repository_identity=identity,
        repository_ref="refs/heads/main", authority_identity="human:test",
    )).snapshot
    path = "docs/shared.md"
    base_plan = RuleBasedProductionPlanner().propose(ProductionPlanningRequest(
        work_id=uuid4(), admitted_requirement="Produce shared guide",
        desired_outcome="combined guide", production_objective="Produce shared guide",
        artifact_targets=(ProductionPlanArtifactTarget(path=path, operation=PlannedArtifactOperation.CREATE),),
        verification_expectation="Verify guide", engineering_scope_summary="one repository",
        engineering_resource_id=uuid4(), repository_identity=identity,
        source_baseline_id=baseline.id, source_revision=baseline.repository_revision,
    ))
    graph = ProductionPlanGraph(nodes=tuple(
        ProductionPlanNode(
            node_id=f"pwu:{name}", kind=ProductionNodeKind.PWU,
            objective=f"Produce {name} interpretation", writable_paths=(path,),
            responsibility_boundary=f"{name} interpretation only",
            acceptance_criteria=("Verify guide",),
        ) for name in ("a", "b")
    ) + (ProductionPlanNode(
        node_id="pwu:join", kind=ProductionNodeKind.JOIN,
        objective="Resolve shared guide", dependency_ids=("pwu:a", "pwu:b"),
        writable_paths=(path,), responsibility_boundary="Integrate both interpretations",
        acceptance_criteria=("Verify guide",),
    ),), planning_rationale="Explicit overlap and bounded Join reconciliation",
    parallel_overlap_policy="EXPLICIT_JOIN_RECONCILIATION")
    plan = base_plan.model_copy(update={
        "fit_classification": OnePwuFitClassification.MULTI_PWU_FIT, "graph": graph,
    })
    spine = runtime.create_initial_runtime_spine(InitialRunRequest(
        intent_ref="work:conflict", goal="combined guide",
        production_horizon=ProductionHorizon.DOCUMENTATION,
        initial_work_unit_objective="Produce shared guide",
        completion_contract=CompletionContract(
            required_outputs=(path,), required_changes=(path,),
            verification_obligations=("Verify guide",), production_plan=plan,
        ),
    ))
    preparation = PreparationService(postgres_database)
    execution = ExecutionService(postgres_database, preparation=preparation)
    completion = CompletionService(postgres_database, observer=execution.observer)
    verification = VerificationService(postgres_database, observer=execution.observer)

    def produce(node_id, content, *, previous_attempt=None):
        with postgres_database.unit_of_work() as uow:
            unit = RuntimeStore(uow.session).work_unit_for_node(spine.plan_revision.id, node_id)
        attempt = previous_attempt or runtime.create_initial_attempt(unit.id)
        package = preparation.assemble_context_package(
            unit.id, repository, ContextPackageRequest(artifacts=(ContextArtifactSelection(
                semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                repository_relative_path="README.md",
            ),)),
        )
        preparation.prepare_attempt(attempt.id, package.id, ExecutorBinding(
            binding_ref="binding:conflict", capability_identity="capability:executor",
            profile_identity="profile:local-fvs",
        ), repository, tmp_path / "attempt-workspaces")
        if node_id == "pwu:join":
            evidence = runtime.reconcile_join_attempt(attempt.id)
            assert evidence["conflicts"]
        operations = () if content is None else (DeterministicFileOperation(
            operation=DeterministicFileOperationType.MODIFY if node_id == "pwu:join" else DeterministicFileOperationType.CREATE,
            repository_relative_path=path, content=content,
        ),)
        dispatched = execution.dispatch_and_observe(attempt.id, DeterministicTestExecutor(
            DeterministicExecutionSpecification(operations=operations, reported_outcome=ProviderReportedOutcome.SUCCESS),
        ))
        evaluated = completion.evaluate_observation(dispatched.observation.id)
        proposed = verification.create_proposed_snapshot(evaluated.evaluation.id)
        verification.verify_obligation(proposed.id, "Verify guide", DeterministicVerificationProvider(
            {"Verify guide": VerificationResultValue.PASS},
        ))
        satisfaction = verification.evaluate_admissibility(proposed.id)
        if satisfaction.admissibility.outcome.value != "ADMISSIBLE":
            return attempt, satisfaction
        return runtime.publish_verified_pwu_output(unit.id, proposed.id)

    produce("pwu:a", "first interpretation\n")
    produce("pwu:b", "second interpretation\n")
    with postgres_database.unit_of_work() as uow:
        store = RuntimeStore(uow.session)
        run = store.run(spine.run.id)
        join = store.work_unit_for_node(spine.plan_revision.id, "pwu:join")
    assert run.integrated_baseline_id == baseline.id
    assert join.source_baseline_id == baseline.id
    unresolved_attempt, refusal = produce("pwu:join", None)
    assert refusal.admissibility.outcome.value == "NOT_ADMISSIBLE"
    resumed_attempt = runtime.retry_attempt(unresolved_attempt.id)
    final = produce("pwu:join", "reconciled interpretation\n", previous_attempt=resumed_attempt)
    assert _git(repository, "show", f"{final.repository_revision}:{path}") == "reconciled interpretation"
    with postgres_database.unit_of_work() as uow:
        store = RuntimeStore(uow.session)
        join = store.work_unit_for_node(spine.plan_revision.id, "pwu:join")
    assert join.reconciliation_evidence["verification_state"] == "RESOLVED_AND_VERIFIED"
    assert join.reconciliation_evidence["resolved_tree"] != join.reconciliation_evidence["candidate_tree"]


@pytest.mark.parametrize("first_node", ["pwu:1", "pwu:2"])
def test_real_parallel_branch_outputs_join_only_after_verification(postgres_database, tmp_path, monkeypatch, first_node):
    monkeypatch.setenv("SPG_DATABASE_URL", os.environ["SPG_TEST_DATABASE_URL"])
    command.upgrade(Config(Path(__file__).resolve().parents[2] / "alembic.ini"), "head")
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "README.md").write_text("initial\n")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "initial")
    runtime = RuntimeService(postgres_database)
    identity = f"test://multi-pwu/{uuid4()}"
    baseline = runtime.bootstrap_trusted_baseline(BootstrapRequest(
        repository_path=repository, repository_identity=identity,
        repository_ref="refs/heads/main", authority_identity="human:test",
    )).snapshot
    targets = tuple(ProductionPlanArtifactTarget(path=f"docs/{stem}.md", operation=PlannedArtifactOperation.CREATE)
                    for stem in ("auth", "billing", "final"))
    plan = RuleBasedProductionPlanner().propose(ProductionPlanningRequest(
        work_id=uuid4(), admitted_requirement="Implement independent auth and billing guides",
        desired_outcome="Both guides exist", production_objective="Produce two guides",
        artifact_targets=targets, verification_expectation="Verify both guides",
        engineering_scope_summary="one repository", engineering_resource_id=uuid4(),
        repository_identity=identity, source_baseline_id=baseline.id,
        source_revision=baseline.repository_revision,
    ))
    assert plan.graph is not None
    graph = plan.graph.model_copy(update={"nodes": tuple(
        node.model_copy(update={"dependency_ids": ("pwu:join",)})
        if node.node_id == "pwu:3" else
        node.model_copy(update={"dependency_ids": ("pwu:1", "pwu:2"),
                                "writable_paths": ("docs/auth.md", "docs/billing.md")})
        if node.node_id == "pwu:join" else node
        for node in plan.graph.nodes
    )})
    plan = plan.model_copy(update={"graph": ProductionPlanGraph.model_validate(graph.model_dump(mode="json"))})
    spine = runtime.create_initial_runtime_spine(InitialRunRequest(
        intent_ref="work:multi", goal="Both guides exist",
        production_horizon=ProductionHorizon.DOCUMENTATION,
        initial_work_unit_objective="Produce two guides",
        completion_contract=CompletionContract(
            required_outputs=tuple(item.path for item in targets),
            required_changes=tuple(item.path for item in targets),
            verification_obligations=("Verify both guides",),
            production_plan=plan,
        ),
    ))
    preparation = PreparationService(postgres_database)
    execution = ExecutionService(postgres_database, preparation=preparation)
    completion = CompletionService(postgres_database, observer=execution.observer)
    verification = VerificationService(postgres_database, observer=execution.observer)
    binding = ExecutorBinding(
        binding_ref="binding:multi-test", capability_identity="capability:executor",
        profile_identity="profile:local-fvs",
    )

    def produce(node_id: str, output_path: str | None):
        with postgres_database.unit_of_work() as uow:
            unit = RuntimeStore(uow.session).work_unit_for_node(spine.plan_revision.id, node_id)
        assert unit is not None
        attempt = runtime.create_initial_attempt(unit.id)
        package = preparation.assemble_context_package(
            unit.id, repository, ContextPackageRequest(artifacts=(
                ContextArtifactSelection(
                    semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                    repository_relative_path="README.md",
                ),
            )),
        )
        preparation.prepare_attempt(
            attempt.id, package.id, binding, repository, tmp_path / "attempt-workspaces",
        )
        if node_id == "pwu:join":
            reconciliation = runtime.reconcile_join_attempt(attempt.id)
            assert reconciliation is not None
            assert reconciliation["conflicts"] == []
        operations = () if output_path is None else (
            DeterministicFileOperation(
                operation=DeterministicFileOperationType.CREATE,
                repository_relative_path=output_path, content=f"{output_path}\n",
            ),
        )
        result = execution.dispatch_and_observe(attempt.id, DeterministicTestExecutor(
            DeterministicExecutionSpecification(
                operations=operations, reported_outcome=ProviderReportedOutcome.SUCCESS,
            ),
        ))
        evaluated = completion.evaluate_observation(result.observation.id)
        assert evaluated.evaluation.outcome.value == "PRODUCED"
        candidate = verification.create_proposed_snapshot(evaluated.evaluation.id)
        verifier = DeterministicVerificationProvider({"Verify both guides": VerificationResultValue.PASS})
        verification.verify_obligation(candidate.id, "Verify both guides", verifier)
        admissibility = verification.evaluate_admissibility(candidate.id)
        assert admissibility.admissibility.outcome.value == "ADMISSIBLE"
        output = runtime.publish_verified_pwu_output(unit.id, candidate.id)
        return output, candidate, admissibility

    first_path = "docs/auth.md" if first_node == "pwu:1" else "docs/billing.md"
    second_node = "pwu:2" if first_node == "pwu:1" else "pwu:1"
    second_path = "docs/billing.md" if first_node == "pwu:1" else "docs/auth.md"
    first, _, _ = produce(first_node, first_path)
    with postgres_database.unit_of_work() as uow:
        store = RuntimeStore(uow.session)
        run = store.run(spine.run.id)
        second_unit = store.work_unit_for_node(spine.plan_revision.id, second_node)
        join = store.work_unit_for_node(spine.plan_revision.id, "pwu:join")
    assert run.integrated_baseline_id == baseline.id
    assert second_unit.source_baseline_id == baseline.id
    assert join.source_baseline_id is None
    # Simulate service restart from persisted Plan/PWU/Attempt facts. The
    # first branch stays verified; no replay of its repository side effect.
    runtime = RuntimeService(postgres_database)
    with postgres_database.unit_of_work() as uow:
        restored = RuntimeStore(uow.session).work_unit_for_node(spine.plan_revision.id, first_node)
    assert restored.verified_output_baseline_id == first.id
    second, _, _ = produce(second_node, second_path)
    with postgres_database.unit_of_work() as uow:
        store = RuntimeStore(uow.session)
        run = store.run(spine.run.id)
        join = store.work_unit_for_node(spine.plan_revision.id, "pwu:join")
    assert run.integrated_baseline_id == baseline.id
    assert join.source_baseline_id == baseline.id
    assert set(join.parent_baseline_ids) == {first.id, second.id}
    integrated, _, _ = produce("pwu:join", None)
    with postgres_database.unit_of_work() as uow:
        store = RuntimeStore(uow.session)
        run = store.run(spine.run.id)
        successor = store.work_unit_for_node(spine.plan_revision.id, "pwu:3")
    assert run.integrated_baseline_id == integrated.id
    assert successor.source_baseline_id == integrated.id
    final, proposed, satisfaction = produce("pwu:3", "docs/final.md")
    assert final.source_baseline_id == integrated.id
    assert _git(repository, "rev-parse", "refs/heads/main") == baseline.repository_revision
    assert _git(repository, "show", f"{final.repository_revision}:docs/auth.md") == "docs/auth.md"
    assert _git(repository, "show", f"{final.repository_revision}:docs/billing.md") == "docs/billing.md"
    assert _git(repository, "show", f"{final.repository_revision}:docs/final.md") == "docs/final.md"
    governance = CandidateGovernanceService(postgres_database)
    with postgres_database.unit_of_work() as uow:
        terminal = RuntimeStore(uow.session).work_unit_for_node(spine.plan_revision.id, "pwu:3")
    candidate = governance.seal_candidate(CandidateSealRequest(
        proposed_snapshot_id=proposed.id,
        production_admissibility_id=satisfaction.admissibility.id,
        expected_work_unit_version=terminal.version,
    ))
    assert candidate.source_baseline_id == baseline.id
    assert len(candidate.satisfied_work_unit_ids) == 4
    authorization = governance.authorize_candidate(HumanAuthorizationRequest(
        authority_identity="human:test", candidate_id=candidate.id,
        candidate_fingerprint=candidate.fingerprint,
        scope=CandidateAuthorizationScope(
            repository_identity=candidate.repository_identity,
            target_authoritative_ref=candidate.target_authoritative_ref,
            expected_source_repository_revision=candidate.expected_source_repository_revision,
            proposed_repository_revision=candidate.proposed_commit_identity,
        ),
        rationale="Accept integrated graph output",
    ))
    effect = RepositoryIntegrationService(postgres_database).integrate_repository_candidate(
        RepositoryIntegrationRequest(
            candidate_id=candidate.id, candidate_fingerprint=candidate.fingerprint,
            human_authorization_id=authorization.id,
        )
    ).effect
    assert _git(repository, "rev-parse", "refs/heads/main") == final.repository_revision
    committed = RuntimeCommitService(postgres_database).commit_runtime_candidate(
        RuntimeCommitRequest(
            candidate_id=candidate.id, candidate_fingerprint=candidate.fingerprint,
            human_authorization_id=authorization.id,
            repository_integration_effect_id=effect.id,
        )
    )
    assert committed.trusted_baseline.repository_revision == final.repository_revision
