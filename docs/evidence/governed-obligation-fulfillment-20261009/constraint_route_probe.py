"""Isolated regression of the actual failed G0 IR constraint binding."""

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from spg.application.governed_obligations import (
    evaluate_constraint_routes, materialize_continuous_gates,
    validate_continuous_gates,
)
from spg.domain.intent_realization import SemanticClause, SemanticItem, ProductionIntent


snapshot = json.loads(Path("/qualification/blocker-forensics-snapshot.json").read_text(
    encoding="utf-8-sig"))
revision = SimpleNamespace(
    id=UUID(snapshot["revision"]),
    source_assessment_id=UUID(snapshot["source_assessment_id"]),
    source_record_ids=tuple(UUID(value) for value in snapshot["revision_source_record_ids"]),
    constraints=tuple(snapshot["constraints"]),
    source_revision=snapshot["source_revision"],
    revision_fingerprint="a" * 64,
    engineering_semantic_facts=(),
)
ir = SimpleNamespace(
    id=UUID(snapshot["ir_id"]),
    items=tuple(SemanticItem.model_validate(value) for value in snapshot["items"]),
    clauses=tuple(SemanticClause.model_validate({
        **{key: field for key, field in value.items() if key != "id"},
        "clause_id": value["id"]}) for value in snapshot["clauses"]),
    current_production=tuple(ProductionIntent.model_validate(value["production"])
                             for value in snapshot["items"] if value["production"]
                             and value["production"]["current"]),
)
bindings = materialize_continuous_gates(revision, ir)
assert {(item.constraint_item_id, item.component) for item in bindings} == {
    ("si-2", "git-diff-scope"), ("si-3", "deploy"),
    ("si-3", "publish"), ("si-3", "git-diff-scope"),
}
assert all(item.fact_id is None for item in bindings)
validate_continuous_gates(bindings, revision, ir)

attempt = uuid4()
native = SimpleNamespace(
    attempt_id=attempt,
    production_context=SimpleNamespace(work_reality_revision_id=revision.id),
    obligation_references=tuple(
        f"ir-constraint:{item.constraint_item_id}:{item.constraint_clause_id}"
        for item in bindings),
    source_vector=SimpleNamespace(members=(
        SimpleNamespace(source_commit_oid=revision.source_revision,
                        write_scope=("index.html",), forbidden_paths=("README.md",)),)),
    capability_grants=(),
)
record = SimpleNamespace(attempt_id=attempt, binding_digest="b" * 64,
                         binding=native)
assert all(item["passed"] for item in evaluate_constraint_routes(
    bindings, record, source_revision=revision.source_revision,
    path_scope_passed=True, exact_target_paths=("index.html",)))
native.obligation_references = ()
assert not any(item["passed"] for item in evaluate_constraint_routes(
    bindings, record, source_revision=revision.source_revision,
    path_scope_passed=True, exact_target_paths=("index.html",)))
native.obligation_references = tuple(
    f"ir-constraint:{item.constraint_item_id}:{item.constraint_clause_id}"
    for item in bindings)
native.capability_grants = (SimpleNamespace(identity="cloud.deploy"),)
assert not next(item for item in evaluate_constraint_routes(
    bindings, record, source_revision=revision.source_revision,
    path_scope_passed=True, exact_target_paths=("index.html",))
    if item["component"] == "deploy")["passed"]
native.capability_grants = ()
assert not all(item["passed"] for item in evaluate_constraint_routes(
    bindings, record, source_revision="0" * 40,
    path_scope_passed=True, exact_target_paths=("index.html",)))
assert not all(item["passed"] for item in evaluate_constraint_routes(
    bindings, record, source_revision=revision.source_revision,
    path_scope_passed=False, exact_target_paths=("index.html",)))
assert not all(item["passed"] for item in evaluate_constraint_routes(
    bindings, record, source_revision=revision.source_revision,
    path_scope_passed=True, exact_target_paths=("README.md",)))

print(json.dumps({"source_work_revision": str(revision.id),
                  "source_ir": str(ir.id),
                  "route_count": len(bindings),
                  "negative_cases": ["missing-reference", "forbidden-grant",
                                     "wrong-revision", "failed-git-scope",
                                     "wrong-target-scope"],
                  "result": "PASS"}, sort_keys=True))
