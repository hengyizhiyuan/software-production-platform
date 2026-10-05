"""Exact, reusable proof of a completed versioned multi-PWU production graph."""

from spg.domain.planning import ProductionNodeKind
from spg.domain.runtime import RuntimeInvariantViolation, SnapshotCondition, WorkUnitCondition
from spg.infrastructure.persistence.runtime_store import RuntimeStore


def work_consumes_revision(session, work_id, repository_identity, revision) -> bool:
    """Prove an active PWU input is derived from this Work's admitted source."""
    from spg.infrastructure.persistence.product_store import ProductStore
    product, runtime = ProductStore(session), RuntimeStore(session)
    work = product.work(work_id)
    if work is None:
        return False
    for binding in product.runtime_bindings(work_id):
        if work.current_work_reality_revision_id is not None and binding.work_reality_revision_id != work.current_work_reality_revision_id:
            continue
        run = runtime.run(binding.production_run_id)
        plan = runtime.plan_revision(binding.plan_revision_id)
        if run is None or plan is None or plan.graph is None or plan.condition.value != "ACTIVE" or run.current_plan_revision_id != plan.id:
            continue
        original = runtime.snapshot(run.source_baseline_id)
        if original is None or original.repository_identity != repository_identity:
            continue
        units = {unit.node_id: unit for unit in runtime.work_units_for_plan(plan.id)}
        for node in plan.graph.nodes:
            unit = units.get(node.node_id)
            if unit is None or unit.source_baseline_id is None:
                continue
            source = runtime.snapshot(unit.source_baseline_id)
            if source is None or source.condition is not SnapshotCondition.TRUSTED or source.repository_revision != revision:
                continue
            if source.repository_identity != repository_identity or source.repository_ref != original.repository_ref:
                continue
            cursor, seen = source, set()
            while cursor.id != original.id and cursor.id not in seen:
                seen.add(cursor.id)
                cursor = None if cursor.source_baseline_id is None else runtime.snapshot(cursor.source_baseline_id)
                if cursor is None:
                    break
            if cursor is None or cursor.id != original.id:
                continue
            parents = tuple(units.get(identity) for identity in node.dependency_ids)
            if any(parent is None or parent.condition is not WorkUnitCondition.SATISFIED or parent.verified_output_baseline_id is None for parent in parents):
                continue
            expected = tuple(parent.verified_output_baseline_id for parent in parents)
            if node.dependency_ids and unit.parent_baseline_ids != expected:
                continue
            if node.kind is ProductionNodeKind.PWU and expected and source.id != expected[0]:
                continue
            if not expected and source.id != (plan.graph.starting_baseline_id or run.source_baseline_id):
                continue
            return True
    return False


def completed_graph(store: RuntimeStore, run, plan, proposed):
    """Return all units and the terminal PWU input, or reject stale graph evidence."""

    graph = plan.graph
    if graph is None:
        raise RuntimeInvariantViolation("multi-PWU graph is missing")
    nodes = {node.node_id: node for node in graph.nodes if node.kind is not ProductionNodeKind.GROUP}
    units = {unit.node_id: unit for unit in store.work_units_for_plan(plan.id)}
    if set(units) != set(nodes):
        raise RuntimeInvariantViolation("multi-PWU graph inventory is incomplete")
    terminal_ids = set(nodes) - {dependency for node in nodes.values() for dependency in node.dependency_ids}
    if len(terminal_ids) != 1:
        raise RuntimeInvariantViolation("multi-PWU graph has no unique integration terminal")
    terminal = units[terminal_ids.pop()]
    if terminal.id != proposed.work_unit_id or run.integrated_baseline_id != terminal.verified_output_baseline_id:
        raise RuntimeInvariantViolation("final proposal is not the integrated terminal PWU")
    if graph.starting_baseline_id is not None:
        cursor = graph.starting_baseline_id
        seen = set()
        while cursor != run.source_baseline_id:
            if cursor in seen:
                raise RuntimeInvariantViolation("re-planned baseline lineage contains a cycle")
            seen.add(cursor)
            snapshot = store.snapshot(cursor)
            if snapshot is None or snapshot.source_baseline_id is None:
                raise RuntimeInvariantViolation("re-planned baseline is not derived from the Work source")
            cursor = snapshot.source_baseline_id
    for node_id, node in nodes.items():
        unit = units[node_id]
        if (
            unit.plan_revision_id != plan.id
            or unit.production_run_id != run.id
            or unit.condition is not WorkUnitCondition.SATISFIED
            or unit.source_baseline_id is None
            or unit.verified_output_baseline_id is None
        ):
            raise RuntimeInvariantViolation("multi-PWU output is incomplete or stale")
        source = store.snapshot(unit.source_baseline_id)
        output = store.snapshot(unit.verified_output_baseline_id)
        if (
            source is None or output is None
            or source.condition is not SnapshotCondition.TRUSTED
            or output.condition is not SnapshotCondition.TRUSTED
            or output.source_baseline_id != source.id
            or output.repository_identity != source.repository_identity
            or output.repository_ref != source.repository_ref
        ):
            raise RuntimeInvariantViolation("multi-PWU baseline chain is inconsistent")
        if node.dependency_ids:
            parents = tuple(units[parent].verified_output_baseline_id for parent in node.dependency_ids)
            if unit.parent_baseline_ids != parents:
                raise RuntimeInvariantViolation("multi-PWU dependency outputs changed")
            if node.kind is ProductionNodeKind.JOIN and (
                unit.reconciliation_evidence is None
                or unit.reconciliation_evidence.get("verification_state") != "RESOLVED_AND_VERIFIED"
            ):
                raise RuntimeInvariantViolation("Join lacks verified reconciliation evidence")
        elif source.id != (graph.starting_baseline_id or run.source_baseline_id):
            raise RuntimeInvariantViolation("root PWU did not start from the Work baseline")
    final_output = store.snapshot(terminal.verified_output_baseline_id)
    if (
        final_output is None
        or final_output.repository_revision != proposed.proposed_commit_identity
        or final_output.repository_tree_identity != proposed.tree_identity
        or terminal.source_baseline_id != proposed.source_baseline_id
    ):
        raise RuntimeInvariantViolation("terminal PWU output differs from final proposal")
    return tuple(units[node_id] for node_id in nodes), store.snapshot(terminal.source_baseline_id)
