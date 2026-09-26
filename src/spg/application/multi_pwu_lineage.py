"""Exact, reusable proof of a completed versioned multi-PWU production graph."""

from spg.domain.planning import ProductionNodeKind
from spg.domain.runtime import RuntimeInvariantViolation, SnapshotCondition, WorkUnitCondition
from spg.infrastructure.persistence.runtime_store import RuntimeStore


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
