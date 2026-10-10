"""A review judges submitted consumers, never hypothetical sibling proofs."""
from copy import deepcopy
import json

import pytest

from spg.application import governed_obligations as a
from spg.providers import fulfillment_candidate as p
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case
from tests.test_c3_semantic_contract_calibration import review


def test_route_slots_reject_copy_error_duplicate_and_wrong_consumer_without_supplying_verdicts():
    revision, ir, inventory, plan = controlled_capacity_case("medium")
    schema = p._review_output_schema(inventory, plan, route_scoped=True)
    raw = review(inventory, plan).model_dump(mode="json")
    a.validate_projection_candidate(plan, revision, ir, inventory, semantic_review=raw)
    for kind in ("wrong-id", "duplicate", "wrong-consumer", "missing", "extra"):
        invalid = deepcopy(raw)
        if kind == "wrong-id": invalid["component_results"][0]["component_id"] = "0"*64
        elif kind == "duplicate": invalid["component_results"][1] = deepcopy(invalid["component_results"][0])
        elif kind == "wrong-consumer": invalid["component_results"][0]["capability"] = "UNRESOLVED"
        elif kind == "missing": invalid["component_results"].pop()
        else: invalid["component_results"].append(deepcopy(invalid["component_results"][0]))
        with pytest.raises(ValueError):
            a.validate_projection_candidate(plan, revision, ir, inventory, semantic_review=invalid)
    for component in raw["component_results"]:
        component.update(complete_and_equivalent=False, nonredundant=False, owner_phase_evidence_valid=False)
    with pytest.raises(ValueError, match="SEMANTIC_COMPONENT_MISMATCH"):
        a.validate_projection_candidate(plan, revision, ir, inventory, semantic_review=raw)
    slots = schema["properties"]["component_results"]["prefixItems"]
    assert len(slots) == len(plan.routes)
    for route, slot in zip(plan.routes, slots, strict=True):
        props = slot["properties"]
        assert props["capability"]["enum"] == [route.capability]
        assert route.capability in props["reason"]["description"]
        assert "imagined repaired route" in props["reason"]["description"]
    assert list(schema["properties"]).index("component_results") < list(schema["properties"]).index("source_results")


def test_bound_feedback_describes_the_rejected_consumer_and_preserves_original_dependencies():
    revision, ir, inventory, plan = controlled_capacity_case("medium")
    original = deepcopy(plan.model_dump(mode="json"))
    verdict = review(inventory, plan)
    chosen = verdict.component_results[0]
    rejected = verdict.model_copy(update={"component_results": tuple(row.model_copy(update={
        "complete_and_equivalent": False, "owner_phase_evidence_valid": False,
        "reason": "The submitted consumer does not prove this original contribution."})
        if row.component_id == chosen.component_id and row.capability == chosen.capability else row
        for row in verdict.component_results)})
    observation = {"review": rejected.model_dump(mode="json"), "attempt": 1,
        "review_output_sha256": "a"*64, "observed_receipt_id": "controlled-original-review"}
    def feedback(contract):
        return json.loads(a.projection_validation_feedback(plan, revision, ir, inventory,
            "OBLIGATION_SEMANTIC_COMPONENT_MISMATCH", semantic_observation=observation,
            owner_preconditions={"review_input_contract": contract}))
    current = feedback(p._REVIEW_INPUT_CONTRACT)
    violation = next(v for v in current["violations"] if v["code"] == "OBLIGATION_SEMANTIC_COMPONENT_MISMATCH")
    index = violation["route"]; route = plan.routes[index]
    comparison = violation["submitted_consumer_comparison"]
    assert comparison["consumer_contract"]["capability"] == route.capability
    assert comparison["declared_fact_refs"] == list(route.component_basis.linked_fact_refs)
    assert comparison["provenance_support_refs"] == list(route.supporting_source_refs)
    assert comparison["component_basis_fingerprint"] == a.canonical_fingerprint(route.component_basis.model_dump(mode="json"))
    assert current["semantic_review_feedback_binding"]["review_output_sha256"] == "a"*64
    assert current["not_evaluable"] == ["ACTUAL_OWNER_EVIDENCE", "ASSURANCE"]
    legacy = feedback(p._REVIEW_INPUT_LEGACY_CONTRACT)
    assert all("submitted_consumer_comparison" not in v for v in legacy["violations"])
    assert plan.model_dump(mode="json") == original


def test_declared_fact_review_retains_unit_version_qualifiers_and_authority_without_sibling_borrowing():
    _, _, inventory, plan = controlled_capacity_case("medium")
    fact = next(s for s in inventory["sources"] if s["kind"] == "FACT")
    basis = plan.routes[0].component_basis.model_copy(update={"linked_fact_refs": (fact["source_ref"],)})
    plan = plan.model_copy(update={"routes": (plan.routes[0].model_copy(update={"component_basis": basis}), *plan.routes[1:])})
    original = deepcopy((inventory, plan.model_dump(mode="json")))
    rows = p._review_component_table(inventory, plan, a.fulfillment_capability_contracts(), full_fact_payload=True)
    operands = rows[0]["declared_fact_evidence_operands"]
    assert len(operands) == 1 and operands[0]["original_fact"] == fact["payload"]
    assert [r["capability"] for r in operands[0]["submitted_fact_routes"]] == [
        r.capability for r in plan.routes if r.source_ref == fact["source_ref"]]
    assert (inventory, plan.model_dump(mode="json")) == original


def test_wrong_consumer_semantic_rejection_remains_failure_even_with_correct_review_identities():
    revision, ir, inventory, plan = controlled_capacity_case("medium")
    verdict = review(inventory, plan)
    denied = verdict.model_copy(update={"component_results": tuple(row.model_copy(update={
        "owner_phase_evidence_valid": False, "reason": "Controlled scope-only consumer lacks required content proof."})
        for row in verdict.component_results)})
    with pytest.raises(ValueError, match="SEMANTIC_COMPONENT_MISMATCH"):
        a.validate_projection_candidate(plan, revision, ir, inventory, semantic_review=denied)
