"""Read exact ECS dogfood lineage; optional bounded invalid-plan injection.

Run inside the normal API runtime. Never accepts a Candidate or synthesizes a
Worker result. The invalid-plan mode appends the owner's refinement evidence
and proves that failed admission creates no Run/PWU/Attempt.
"""
import argparse
import json
import subprocess
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from spg.application.multi_pwu_lineage import completed_graph
from spg.application.planning import ProductionPlanningService
from spg.application.runtime import RuntimeService
from spg.config import Settings
from spg.domain.planning import ProductionNodeKind, ProductionPlanGraph, ProductionPlanNode, ProductionPlanningRequest
from spg.domain.runtime import InitialRunRequest, ProductionHorizon, RuntimeInvariantViolation
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_schema import production_runs, production_work_units, execution_attempts
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.providers.rule_based_planner import RuleBasedProductionPlanner


def invalid_decomposition(db, work_id, contract):
    proposal = contract.production_plan
    request = ProductionPlanningRequest(
        work_id=work_id, target_kind=proposal.target_kind,
        admitted_requirement=proposal.objective, desired_outcome=proposal.desired_outcome,
        production_objective=proposal.objective, artifact_targets=proposal.artifact_targets,
        change_proposal=proposal.change_proposal, change_contract=proposal.change_contract,
        constraints=proposal.inherited_constraints, verification_expectation=proposal.verification_approach,
        engineering_scope_summary="Exact admitted dogfood repository",
        engineering_resource_id=proposal.engineering_resource_id,
        repository_identity=proposal.repository_identity, source_baseline_id=proposal.source_baseline_id,
        source_revision=proposal.source_revision,
    )
    valid = RuleBasedProductionPlanner().propose(request)
    graph = valid.graph
    if graph is None:
        paths = tuple(t.path for t in valid.change_contract.exact_targets)
        assert len(paths) == 2
        leaves = tuple(ProductionPlanNode(node_id=f"pwu:{i}", kind=ProductionNodeKind.PWU,
            objective=f"Produce {path}", writable_paths=(path,), responsibility_boundary=path,
            acceptance_criteria=(f"Qualified {path}",), verification_requirements=(request.verification_expectation,))
            for i, path in enumerate(paths, start=1))
        join = ProductionPlanNode(node_id="pwu:join", kind=ProductionNodeKind.JOIN,
            objective="Integrate the two exact outputs", writable_paths=paths,
            dependency_ids=("pwu:1", "pwu:2"), responsibility_boundary="Exact admitted outputs only",
            acceptance_criteria=("Qualified integrated result",), verification_requirements=(request.verification_expectation,))
        graph = ProductionPlanGraph(nodes=(*leaves, join), planning_rationale="Replay superseded dual-target decomposition")
    nodes = tuple(node.model_copy(update={"writable_paths": ()}) if node.node_id == "pwu:2" else node
                  for node in graph.nodes)
    invalid = valid.model_copy(update={"graph": graph.model_copy(update={"nodes": nodes})})
    intent_ref = f"qualification:invalid-plan:{work_id}"
    runs = select(production_runs.c.id).where(production_runs.c.intent_ref == intent_ref)
    units = select(production_work_units.c.id).where(production_work_units.c.production_run_id.in_(runs))
    statements = (
        select(func.count()).select_from(production_runs).where(production_runs.c.intent_ref == intent_ref),
        select(func.count()).select_from(production_work_units).where(production_work_units.c.production_run_id.in_(runs)),
        select(func.count()).select_from(execution_attempts).where(execution_attempts.c.work_unit_id.in_(units)),
    )
    def counts():
        with db.unit_of_work() as uow:
            return [uow.session.scalar(statement) for statement in statements]
    before = counts()
    try:
        RuntimeService(db).create_initial_runtime_spine(InitialRunRequest(
            source_baseline_id=valid.source_baseline_id, intent_ref=intent_ref,
            goal=valid.desired_outcome, initial_work_unit_objective=valid.objective,
            production_horizon=ProductionHorizon.CODE,
            completion_contract=contract.model_copy(update={"production_plan": invalid}),
        ))
    except RuntimeInvariantViolation as error:
        finding = str(error)
        assert "PLANNING_EMPTY_PWU" in finding
    else:
        raise AssertionError("Empty PWU was admitted")
    assert before == counts(), "Rejected planning created durable execution state"
    class FaultPlanner:
        def propose(self, request): return invalid
    corrected = ProductionPlanningService(FaultPlanner(), database=db).propose(request)
    if corrected.graph is not None:
        corrected.graph.validate_admission({p for node in graph.nodes for p in node.writable_paths})
        assert all(node.writable_paths for node in corrected.graph.nodes if node.kind is ProductionNodeKind.PWU)
    else:
        assert corrected.fit_classification.value == "ONE_PWU_FIT"
        assert len(corrected.change_contract.exact_targets) == 2
    with db.unit_of_work() as uow:
        events = NativeExecutionStore(uow.session).self_refine_events_for_operation(valid.proposal_id)
        event = next(item for item in reversed(events) if item.affected_component == "planning/production-plan")
    assert event.final_result == "LOCAL_OBLIGATION_RECOVERED"
    return {"finding": finding, "admission_counts_before_after": before,
            "refinement_event_id": str(event.id), "corrected_plan": corrected.model_dump(mode="json")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("work_id", type=UUID)
    parser.add_argument("--invalid-decomposition", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    db = Database.from_settings(Settings())
    with db.unit_of_work() as uow:
        product, runtime, native = ProductStore(uow.session), RuntimeStore(uow.session), NativeExecutionStore(uow.session)
        binding = product.runtime_binding(args.work_id)
        plan = runtime.plan_revision(binding.plan_revision_id)
        run = runtime.run(binding.production_run_id)
        units = runtime.work_units_for_plan(plan.id)
        result = {"work_id": str(args.work_id), "plan": plan.model_dump(mode="json"), "units": [],
                  "queue": [q.model_dump(mode="json") for q in native.list_queue(work_id=args.work_id)]}
        for unit in units:
            attempts = runtime.attempts_for_work_unit(unit.id)
            rows = runtime.verification_records_for_work_unit(unit.id)
            result["units"].append({"unit": unit.model_dump(mode="json"),
                "attempts": [a.model_dump(mode="json") for a in attempts],
                "verification": [v.model_dump(mode="json") for v in rows]})
        terminal_ids = {u.node_id for u in units} - {d for n in (() if plan.graph is None else plan.graph.nodes) for d in n.dependency_ids}
        terminal = next(u for u in units if u.node_id in terminal_ids)
        candidates = runtime.baseline_candidates_for_work_unit(terminal.id)
        result["candidate"] = None
        if candidates:
            candidate = candidates[-1]
            proposed = runtime.proposed_snapshot(candidate.proposed_snapshot_id)
            qualified = units
            if plan.graph is not None:
                qualified, _ = completed_graph(runtime, run, plan, proposed)
            assert set(candidate.satisfied_work_unit_ids) == {u.id for u in qualified}
            assert not runtime.human_authorizations_for_candidate(candidate.id)
            result["candidate"] = candidate.model_dump(mode="json")
            attempt = runtime.attempts_for_work_unit(terminal.id)[-1]
            workspace = runtime.attempt_preparation(attempt.id).workspace
            repo = workspace.repository_path
            changed = subprocess.check_output(["git", "-C", repo, "diff", "--name-only",
                candidate.expected_source_repository_revision, candidate.proposed_commit_identity], text=True).splitlines()
            result["changed_files"] = changed
            result["artifact_contents"] = {path: subprocess.check_output(["git", "-C", repo, "show",
                f"{candidate.proposed_commit_identity}:{path}"], text=True) for path in changed}
    if args.invalid_decomposition:
        result["invalid_decomposition"] = invalid_decomposition(db, args.work_id, terminal.completion_contract)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({"work_id": result["work_id"], "plan_id": str(plan.id),
        "unit_count": len(units), "candidate_id": None if result["candidate"] is None else result["candidate"]["id"],
        "invalid_decomposition": result.get("invalid_decomposition", {}).get("finding"), "evidence": str(target)}))
    db.dispose()


if __name__ == "__main__": main()
