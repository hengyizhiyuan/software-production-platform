"""Source-wide proof obligations, controlled independent review; no model or Work."""
from copy import deepcopy
import pytest
from spg.application import governed_obligations as a
from spg.providers import fulfillment_candidate as p
from spg.domain.governed_obligation import (
    FulfillmentSemanticReviewCandidate, fulfillment_source_semantic_text)
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case
from tests.test_c3_semantic_contract_calibration import review

CONTRACT = "existing-source-consumption-proof-v1"


def fixture_consumption_checks(inventory, plan, source_ref):
    """Only a controlled oracle; not a runtime rule inferring required meaning."""
    contracts = {row["capability"]: row for row in a.fulfillment_capability_contracts()}
    return [{"source_span_start": r.component_basis.source_span_start,
        "source_span_end": r.component_basis.source_span_end, "source_component_quote": None,
        "required_capability": r.capability,
        "required_evidence_method": contracts[r.capability]["evidence_method"],
        "required_phase": contracts[r.capability]["phase"],
        "target_paths": list(r.target_paths), "route_indices": [index]}
        for index, r in enumerate(plan.routes) if r.source_ref == source_ref and r.component_basis is not None]


def fixture_review_proof(inventory, plan, verdict, payload):
    """Bind explicit controlled oracle consumers to the actual request marker."""
    if (payload.get("existing_owner_source_preconditions") or {}).get("review_source_consumption_contract") != CONTRACT:
        return verdict
    raw = verdict.model_dump(mode="json")
    for row in raw["source_results"]:
        row["consumption_checks"] = fixture_consumption_checks(inventory, plan, row["source_ref"])
    return FulfillmentSemanticReviewCandidate.model_validate(raw)


def case(scale="small"):
    rev, ir, inv, plan = controlled_capacity_case(scale)
    result = review(inv, plan).model_dump(mode="json")
    for row in result["source_results"]:
        row["consumption_checks"] = fixture_consumption_checks(inv, plan, row["source_ref"])
    return rev, ir, inv, plan, result


def validate(plan, inv, raw):
    return a.validate_projection_components(plan, inv,
        semantic_review=FulfillmentSemanticReviewCandidate.model_validate(raw),
        review_source_consumption_contract=CONTRACT)


@pytest.mark.parametrize("scale", ("small", "medium", "complex"))
def test_legitimate_source_union_and_original_identity_remain_exact(scale):
    _, _, inv, plan, raw = case(scale)
    original = deepcopy(plan.model_dump(mode="json"))
    validate(plan, inv, raw)
    assert plan.model_dump(mode="json") == original
    # These are plans of proof, never performed verification or Human authority.
    assert all("effect_permit" not in c for row in raw["source_results"] for c in row["consumption_checks"])


@pytest.mark.parametrize("change,code", [
    ("missing", "PROOF_REQUIRED"), ("empty", "PROOF_REQUIRED"),
    ("no-route", "ROUTE_REQUIRED"), ("other-source", "UNDECLARED_DEPENDENCY"),
    ("bad-route", "ROUTE_IDENTITY_DRIFT"), ("future-instead-content", "CONSUMER_MISMATCH"),
    ("wrong-method", "METHOD_PHASE_DRIFT"), ("wrong-phase", "METHOD_PHASE_DRIFT"),
    ("wrong-path", "CONSUMER_MISMATCH"), ("wrong-quote", "QUOTE_DRIFT"),
    ("truncated", "COVERAGE_LOST"), ("duplicate", "DUPLICATE"),
])
def test_positive_review_cannot_backfill_absent_or_wrong_proof(change, code):
    _, _, inv, plan, raw = case()
    row = raw["source_results"][0]
    check = row["consumption_checks"][0]
    if change == "missing": row.pop("consumption_checks")
    elif change == "empty": row["consumption_checks"] = []
    elif change == "no-route": check["route_indices"] = []
    elif change == "other-source": check["route_indices"] = [1]
    elif change == "bad-route": check["route_indices"] = [len(plan.routes)]
    elif change == "future-instead-content":
        seal = next(c for c in a.fulfillment_capability_contracts() if c["capability"] == "CANDIDATE_SEAL")
        check.update(required_capability=seal["capability"], required_evidence_method=seal["evidence_method"], required_phase=seal["phase"])
    elif change == "wrong-method": check["required_evidence_method"] = "INVENTED_PROOF"
    elif change == "wrong-phase": check["required_phase"] = "HUMAN_INTEGRATION"
    elif change == "wrong-path": check["target_paths"] = ["not-admitted.html"]
    elif change == "wrong-quote": check["source_component_quote"] = "invented"
    elif change == "truncated": check["source_span_end"] -= 1
    elif change == "duplicate": row["consumption_checks"].append(deepcopy(check))
    with pytest.raises(ValueError, match="SOURCE_CONSUMPTION_"+code): validate(plan, inv, raw)


def test_explicit_fact_dependency_can_prove_content_but_provenance_cannot():
    _, _, inv, plan, raw = case()
    consumer_index = 0
    context_index = next(i for i, r in enumerate(plan.routes) if r.capability == "RETAIN_CONTEXT")
    ref = plan.routes[context_index].source_ref
    row = next(r for r in raw["source_results"] if r["source_ref"] == ref)
    text = fulfillment_source_semantic_text(next(s for s in inv["sources"] if s["source_ref"] == ref))
    proof = deepcopy(raw["source_results"][0]["consumption_checks"][0])
    proof.update(source_span_start=0, source_span_end=len(text), route_indices=[consumer_index])
    row["consumption_checks"] = [proof]
    borrowed = plan.routes[consumer_index].source_ref
    routes = list(plan.routes)
    routes[context_index] = routes[context_index].model_copy(update={"supporting_source_refs": (borrowed,)})
    provenance = plan.model_copy(update={"routes": tuple(routes)})
    # Pure predicate tests avoid changing the already bound review identities.
    verdict = FulfillmentSemanticReviewCandidate.model_validate(raw)
    assert any(f["code"].endswith("UNDECLARED_DEPENDENCY") for f in a._review_consumption_failures(provenance, inv, verdict, required=True))
    routes[context_index] = routes[context_index].model_copy(update={"component_basis":
        routes[context_index].component_basis.model_copy(update={"linked_fact_refs": (borrowed,)})})
    declared = plan.model_copy(update={"routes": tuple(routes)})
    assert a._review_consumption_failures(declared, inv, verdict, required=True) == []


def test_negative_semantic_verdict_remains_failure_without_fabricated_checks():
    _, _, inv, plan, raw = case()
    raw["source_results"][0].update(complete_and_equivalent=False, consumption_checks=[])
    with pytest.raises(ValueError, match="SEMANTIC_COMPONENT_MISMATCH"): validate(plan, inv, raw)


def test_legacy_receipt_and_schema_are_unchanged_new_schema_is_source_first():
    _, _, inv, plan, _ = case()
    legacy = review(inv, plan)
    assert all("consumption_checks" not in row for row in legacy.model_dump(mode="json")["source_results"])
    a.validate_projection_components(plan, inv, semantic_review=legacy)
    old = p._review_output_schema(inv, plan, route_scoped=True)
    assert "consumption_checks" not in old["$defs"]["FulfillmentSemanticSourceReview"]["properties"]
    new = p._review_output_schema(inv, plan, route_scoped=True, source_consumption=True)
    assert list(new["properties"]).index("source_results") < list(new["properties"]).index("component_results")
    first = new["properties"]["source_results"]["prefixItems"][0]
    assert first["properties"]["consumption_checks"]["items"]["properties"]["route_indices"]["items"]["enum"] == [0]


def test_marker_cannot_be_applied_to_an_unqualified_legacy_review_view():
    rev, ir, inv, _, _ = case()
    with pytest.raises(ValueError, match="REQUEST_VIEW_CONTRACT_INVALID"):
        a._owner_source_preconditions(rev, ir, inv, a.fulfillment_capability_contracts(),
            review_source_consumption_contract=CONTRACT)


def test_full_source_witness_cannot_borrow_same_capability_from_partial_component():
    from tests.test_c3_semantic_contract_calibration import split_content
    _, _, inv, plan = split_content()
    raw = review(inv, plan).model_dump(mode="json")
    for row in raw["source_results"]:
        row["consumption_checks"] = fixture_consumption_checks(inv, plan, row["source_ref"])
    validate(plan, inv, raw)
    text = fulfillment_source_semantic_text(inv["sources"][0])
    raw["source_results"][0]["consumption_checks"] = [dict(
        raw["source_results"][0]["consumption_checks"][0], source_span_end=len(text), route_indices=[0])]
    with pytest.raises(ValueError, match="COMPONENT_COVERAGE_LOST"): validate(plan, inv, raw)


def test_fact_link_on_one_component_cannot_broadcast_to_another_contribution():
    from tests.test_c3_semantic_contract_calibration import split_content
    _, _, inv, plan = split_content()
    raw = review(inv, plan).model_dump(mode="json")
    for row in raw["source_results"]:
        row["consumption_checks"] = fixture_consumption_checks(inv, plan, row["source_ref"])
    # The first partial component links only its matching atomic Fact. It cannot
    # prove the second independent part merely because both use content checks.
    raw["source_results"][0]["consumption_checks"][1]["route_indices"] = [2]
    with pytest.raises(ValueError, match="COMPONENT_COVERAGE_LOST"): validate(plan, inv, raw)


def test_explicit_unresolved_disposition_preserves_existing_failure_and_budget():
    from tests.test_c3_fulfillment_repair_context import incomplete_case
    provider, calls, wires, run = incomplete_case(remains_unresolved=True)
    result = run()
    assert all(b.state == "UNRESOLVED" for b in result)
    assert result[0].formation_receipt["terminal_reason"] == "OBLIGATION_PROJECTION_UNRESOLVED"
    assert len(wires) == 2 and len(calls) == 4
    original = deepcopy(provider._fulfillment_receipts)
    assert all(b.state == "UNRESOLVED" for b in run())
    assert original == provider._fulfillment_receipts and len(calls) == 4


def negative_scope_case():
    from uuid import uuid4
    from spg.domain.engineering_semantics import SemanticRelation
    from spg.domain.intent_realization import SemanticClause, SemanticItem, SemanticKind
    from spg.domain.semantic_provenance import SemanticProvenance, SemanticOrigin
    from spg.domain.governed_obligation import FulfillmentRouteCandidate, FulfillmentComponentBasis
    from tests.test_governed_obligation_fulfillment import fact
    rev, ir, _, plan = controlled_capacity_case()
    text = "Do not change forbidden.bin or cache/private.log; preserve the authorized file boundary."
    record = uuid4()
    provenance = SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
        source_record_id=record, source_text=text)
    item = SemanticItem(item_id="original-path-exclusion", kind=SemanticKind.CONSTRAINT,
        statement=text, provenance=(provenance,), confidence=1)
    clause = SemanticClause(clause_id="original-negative-path-clause", source_record_id=record,
        source_text=text, semantic_item_ids=(item.item_id,), polarity="NEGATED",
        modality="REQUEST", temporal_scope="CURRENT", requested_effects=())
    original = fact("unchanged-excluded-paths", SemanticRelation.SCOPE,
        ["forbidden.bin", "cache/private.log"], text).model_copy(update={
            "qualifiers": {}, "scope": None,
            "provenance": rev.engineering_semantic_facts[0].provenance.model_copy(update={
                "source_record_ids": (record,), "source_text": text})})
    rev.engineering_semantic_facts = (*rev.engineering_semantic_facts, original)
    rev.source_record_ids = (*rev.source_record_ids, record)
    ir.items = (*ir.items, item)
    ir.clauses = (*ir.clauses, clause)
    inv = a.fulfillment_inventory(rev, ir, exact_target_paths=("index.html",))
    fact_ref = "semantic-fact:"+str(original.id)
    clause_ref = next(s["source_ref"] for s in inv["sources"] if s.get("clause_id") == clause.clause_id)
    additional = []
    for ref in (fact_ref, clause_ref):
        source = next(s for s in inv["sources"] if s["source_ref"] == ref)
        quote = fulfillment_source_semantic_text(source)
        additional.append(FulfillmentRouteCandidate(source_ref=ref, capability="GIT_DIFF_SCOPE",
            target_paths=("index.html",), supporting_source_refs=(clause_ref,) if ref == fact_ref else (),
            rationale="Controlled path exclusion, never an alternative allowlist.",
            component_basis=FulfillmentComponentBasis(source_span_start=0, source_span_end=len(quote),
                source_component_quote=quote, linked_fact_refs=(fact_ref,) if ref == fact_ref else ())))
    plan = plan.model_copy(update={"inventory_fingerprint":inv["inventory_fingerprint"],
        "routes":(*plan.routes, *additional)})
    return rev, ir, inv, plan, original


def test_negative_scope_values_never_become_positive_allowlist_and_actual_diff_stays_exact():
    from tests.test_c3_fulfillment_capacity_representation import controlled_model_provider
    from spg.domain.engineering_semantics import semantic_fact_reference
    from spg.providers.managed_context_fulfillment import _exact_fact_git_scope
    rev, ir, inv, plan, original = negative_scope_case()
    before = original.model_dump(mode="json")
    with pytest.raises(ValueError, match="FACT_SCOPE_VALUE_MISMATCH"):
        a._projection_binding(rev, ir, inv, plan.routes[-2], allow_calibrated=True, source_contract="v3")
    provider, calls = controlled_model_provider(inv, plan)
    bindings = a.form_fulfillment_projection(rev, ir, provider=provider,
        source_revision=inv["source_revision"], exact_target_paths=inv["exact_target_paths"])
    assert all(b.state != "UNRESOLVED" for b in bindings) and len(calls) == 2
    binding = next(b for b in bindings if b.fact_id == original.id)
    reference = semantic_fact_reference(original, work_revision_id=rev.id)
    a.validate_fulfillment_projection(bindings, rev, ir,
        source_revision=inv["source_revision"], exact_target_paths=("index.html",))
    assert bindings[0].formation_receipt is not None
    assert any((r.get("owner_source_preconditions") or {}).get("review_source_consumption_contract") == CONTRACT
        for r in bindings[0].formation_receipt["candidate_attempts"] if r.get("stage") == "MODEL_REQUEST_PENDING")
    assert _exact_fact_git_scope(reference, binding, ("index.html",), ("index.html",),
        revision=rev, ir=ir, bindings=bindings)
    for changes in ((), ("forbidden.bin",), ("index.html", "other.txt")):
        assert not _exact_fact_git_scope(reference, binding, ("index.html",), changes,
            revision=rev, ir=ir, bindings=bindings)
    assert not _exact_fact_git_scope(reference.model_copy(update={"value":("invented.txt",)}),
        binding, ("index.html",), ("index.html",), revision=rev, ir=ir, bindings=bindings)
    assert not _exact_fact_git_scope(reference, binding, ("index.html",), ("index.html",))
    assert not _exact_fact_git_scope(reference, binding.model_copy(update={"supporting_source_refs":()}),
        ("index.html",), ("index.html",), revision=rev, ir=ir, bindings=bindings)
    no_receipt = (bindings[0].model_copy(update={"formation_receipt":None}), *bindings[1:])
    assert not _exact_fact_git_scope(reference, binding, ("index.html",), ("index.html",),
        revision=rev, ir=ir, bindings=no_receipt)
    assert original.model_dump(mode="json") == before


@pytest.mark.parametrize("change", ("missing-u", "wrong-record", "wrong-text", "affirmative", "expanded-path"))
def test_negative_scope_cannot_derive_a_new_allowlist_without_exact_original_authority(change):
    from uuid import uuid4
    rev, ir, inv, plan, original = negative_scope_case()
    route = plan.routes[-2]
    if change == "missing-u": route = route.model_copy(update={"supporting_source_refs":()})
    elif change == "expanded-path": route = route.model_copy(update={"target_paths":("unapproved.txt",)})
    elif change in {"wrong-record", "wrong-text"}:
        provenance = original.provenance.model_copy(update=(
            {"source_record_ids":(uuid4(),)} if change == "wrong-record" else {"source_text":"unrelated fact"}))
        rev.engineering_semantic_facts = (*rev.engineering_semantic_facts[:-1], original.model_copy(update={"provenance":provenance}))
    else: ir.clauses = (*ir.clauses[:-1], ir.clauses[-1].model_copy(update={"polarity":"AFFIRMATIVE"}))
    inv = a.fulfillment_inventory(rev, ir, exact_target_paths=("index.html",))
    with pytest.raises(ValueError, match="VALUE_MISMATCH|SCOPE_EXPANSION|QUOTE_DRIFT|POLARITY"):
        a._projection_binding(rev, ir, inv, route, allow_calibrated=True, source_contract="v3",
            source_consumption_contract=CONTRACT)
