"""A multi-Turn Work constraint is proved by its admitted origin, never by itself.

Live Work e88d6f02: the latest Turn's admitted ProductionIntent.scope carries
every accumulated constraint, so the Owner's only lawful proof for each
constraint is the latest Human clause. Proposers kept citing the constraint
itself; the Owner now compiles that self-citation to the unique admitted
origin. Correspondence, phase and Review gates are unchanged.
"""
from types import SimpleNamespace
from uuid import uuid4

from spg.application import governed_obligations as owner
from spg.domain.intent_realization import ProductionIntent, SemanticClause, SemanticItem, SemanticKind
from spg.domain.semantic_provenance import SemanticOrigin, SemanticProvenance
from spg.providers import fulfillment_candidate as wire_owner

SCOPE = ("待办清单核心功能", "Web 页面形式", "新建事项时可设置分类", "按分类文件夹管理不同类别的清单", "不同分类用不同图表区别展示")
LATEST = "不同的分类用几种不同的图表来区别展示"


def multi_turn_case():
    record = uuid4()
    provenance = SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT, source_record_id=record, source_text=LATEST)
    goal = ProductionIntent(objective="构建一个类似待办清单的 Web 小应用", primary_change="分类图表区分",
        current=True, bounded_change=True, scope=SCOPE, preview_required=True, acceptance_required=True)
    item = SemanticItem(item_id="si-category-visual-distinction", kind=SemanticKind.PRODUCTION_INTENT,
        statement="Categories are visually distinguished", provenance=(provenance,), confidence=0.85, production=goal)
    clause = SemanticClause(clause_id="cl-3", source_record_id=record, source_text=LATEST,
        semantic_item_ids=(item.item_id,), polarity="AFFIRMATIVE", modality="REQUEST", temporal_scope="CURRENT",
        requested_effects=("DISTINGUISH_CATEGORIES_BY_DIFFERENT_CHARTS",))
    ir = SimpleNamespace(id=uuid4(), items=(item,), clauses=(clause,), current_production=(goal,),
        legacy_typed_projection=False, source_record_id=record)
    revision = SimpleNamespace(id=uuid4(), work_id=uuid4(), source_assessment_id=uuid4(),
        engineering_semantic_facts=(), constraints=SCOPE, context_facts=(),
        source_record_ids=(uuid4(), uuid4(), record), revision_fingerprint="b" * 64, source_revision="a" * 40)
    return revision, ir


def test_each_accumulated_constraint_has_exactly_the_latest_clause_as_owner_proof():
    revision, ir = multi_turn_case()
    inventory = owner.fulfillment_inventory(revision, ir, source_revision="a" * 40,
                                            exact_target_paths=("index.html", "app.js", "styles.css"))
    capabilities = owner.fulfillment_capability_contracts()
    preconditions = owner._owner_source_preconditions(revision, ir, inventory, capabilities)
    clause = next(i for i, s in enumerate(inventory["sources"]) if s["kind"] == "IR_CLAUSE")
    content = next(i for i, c in enumerate(capabilities) if c["capability"] == "ARTIFACT_CONTENT")
    constraints = [i for i, s in enumerate(inventory["sources"]) if s["kind"] == "WORK_CONSTRAINT"]
    assert len(constraints) == len(SCOPE)
    for index in constraints:
        row = preconditions["sources"][index]
        proof = next(p for p in row["necessary_source_proofs"] if p["capability"] == content)
        # The constraint itself is never a lawful proof; the latest clause is.
        assert proof["minimal_support_sets"] == [[clause]]


def test_live_self_citation_compiles_to_the_proof_the_owner_already_requires():
    revision, ir = multi_turn_case()
    inventory = owner.fulfillment_inventory(revision, ir, source_revision="a" * 40,
                                            exact_target_paths=("index.html", "app.js", "styles.css"))
    capabilities = owner.fulfillment_capability_contracts()
    preconditions = {**owner._owner_source_preconditions(revision, ir, inventory, capabilities),
                     "constraint_provenance_contract": wire_owner._CONSTRAINT_PROVENANCE_CONTRACT}
    content = next(i for i, c in enumerate(capabilities) if c["capability"] == "ARTIFACT_CONTENT")
    clause = next(i for i, s in enumerate(inventory["sources"]) if s["kind"] == "IR_CLAUSE")
    # The exact shape proposed in all four live rounds: each constraint cites itself.
    routes = [{"s": i, "c": content, "u": [i]} for i, s in enumerate(inventory["sources"]) if s["kind"] == "WORK_CONSTRAINT"]
    observations = wire_owner._compile_constraint_provenance(routes, inventory, preconditions)
    assert len(observations) == len(SCOPE)
    assert all(route["u"] == [clause] for route in routes)
    # Every compiled support passes the unchanged binding Owner predicate.
    for route in routes:
        source = inventory["sources"][route["s"]]
        assert owner.work_constraint_sources_correspond(ir, source["payload"]["content"],
            [inventory["sources"][j] for j in route["u"]], component="artifact-content",
            phase=owner.FulfillmentPhase.CURRENT_VERIFICATION, semantic_component_declared=True,
            calibrated=True, source_contract="v3", revision=revision,
            exact_target_paths=inventory["exact_target_paths"])
        assert not owner.work_constraint_sources_correspond(ir, source["payload"]["content"], [source],
            component="artifact-content", phase=owner.FulfillmentPhase.CURRENT_VERIFICATION,
            semantic_component_declared=True, calibrated=True, source_contract="v3",
            revision=revision, exact_target_paths=inventory["exact_target_paths"])


def test_a_multi_pwu_leaf_rechecks_the_plan_over_the_admitted_target_set():
    """Live Work e88d6f02: the plan was formed over three files, the leaf owns one."""
    import pytest
    from spg.domain.governed_obligation import FulfillmentProjectionCandidate, FulfillmentRouteCandidate
    revision, ir = multi_turn_case()
    admitted = ("index.html", "app.js", "styles.css")
    inventory = owner.fulfillment_inventory(revision, ir, source_revision="a" * 40, exact_target_paths=admitted)
    clause = next(s["source_ref"] for s in inventory["sources"] if s["kind"] == "IR_CLAUSE")
    routes = tuple(FulfillmentRouteCandidate(source_ref=s["source_ref"], capability="ARTIFACT_CONTENT",
        work_constraint_indices=(s["index"],) if s["kind"] == "WORK_CONSTRAINT" else (), target_paths=admitted,
        supporting_source_refs=(clause,) if s["kind"] == "WORK_CONSTRAINT" else (), rationale="oracle")
        for s in inventory["sources"])
    bindings = owner.validate_projection_candidate(FulfillmentProjectionCandidate(
        inventory_fingerprint=inventory["inventory_fingerprint"], routes=routes), revision, ir, inventory, source_contract="v1")
    bindings = tuple(b.model_copy(update={"formation_receipt": {"exact_target_paths": list(admitted)}}) for b in bindings)
    for leaf in (("styles.css",), ("index.html", "app.js"), admitted):
        owner.validate_fulfillment_projection(bindings, revision, ir, source_revision="a" * 40, exact_target_paths=leaf)
    with pytest.raises(ValueError, match="OBLIGATION_SCOPE_EXPANSION"):
        owner.validate_fulfillment_projection(bindings, revision, ir, source_revision="a" * 40, exact_target_paths=("evil.js",))
