"""Unreviewed mapping risks reach bounded repair without changing admission."""
import json

from spg.application import governed_obligations as owner
from spg.domain.engineering_semantics import SemanticRelation
from tests.test_c3_fulfillment_capacity_representation import (
    controlled_capacity_case, controlled_model_provider)


def content_and_scope_case():
    revision, ir, original, plan = controlled_capacity_case()
    content = next(f for f in revision.engineering_semantic_facts
        if f.relation is not SemanticRelation.SCOPE and f.scope in original["exact_target_paths"])
    revision.engineering_semantic_facts = tuple(f.model_copy(update={
        "relation": SemanticRelation.EQUALITY, "value": "Visible heading"}) if f.id == content.id else f
        for f in revision.engineering_semantic_facts)
    inventory = owner.fulfillment_inventory(revision, ir,
        source_revision=original["source_revision"], exact_target_paths=original["exact_target_paths"])
    routes = list(plan.routes)
    content_route = next(r for r in routes if r.source_ref == f"semantic-fact:{content.id}")
    routes.insert(routes.index(content_route) + 1, content_route.model_copy(update={
        "capability": "GIT_DIFF_SCOPE", "target_paths": tuple(inventory["exact_target_paths"])}))
    plan = plan.model_copy(update={"inventory_fingerprint": inventory["inventory_fingerprint"],
        "routes": tuple(routes)})
    return revision, ir, inventory, plan, content_route.source_ref


def test_diagnostic_flags_method_meaning_risk_without_a_verdict_or_candidate_edit():
    revision, ir, inventory, plan, content_ref = content_and_scope_case()
    before = plan.model_dump(mode="json")
    diagnostics = owner._consumer_mapping_diagnostics(plan, inventory, owner.fulfillment_capability_contracts())
    assert diagnostics["contract"] == "existing-consumer-mapping-risk-v1"
    assert diagnostics["candidate_fingerprint"] == owner.fulfillment_candidate_fingerprint(plan)
    assert diagnostics["additional_observation_count"] == 0
    assert len(diagnostics["observations"]) == 1
    risk = diagnostics["observations"][0]
    assert inventory["sources"][risk["source"]]["source_ref"] == content_ref
    assert diagnostics["consumer"] == "GIT_DIFF_SCOPE"
    assert risk["fact_relation"] == "EQUALITY"
    assert "NOT_A_VIOLATION_OR_REVIEW_VERDICT" in diagnostics["status"]
    assert plan.model_dump(mode="json") == before
    assert revision.engineering_semantic_facts and ir.current_production


def test_risk_enters_existing_repair_context_after_structural_failure():
    revision, ir, inventory, plan, content_ref = content_and_scope_case()
    routes = list(plan.routes)
    other = next(i for i, route in enumerate(routes) if route.source_ref != content_ref
        and len(route.component_basis.source_component_quote) > 1)
    basis = routes[other].component_basis
    routes[other] = routes[other].model_copy(update={"component_basis": basis.model_copy(update={
        "source_span_end": basis.source_span_end - 1,
        "source_component_quote": basis.source_component_quote[:-1]})})
    plan = plan.model_copy(update={"routes": tuple(routes)})
    provider, calls = controlled_model_provider(inventory, plan)
    result = owner.form_fulfillment_projection(revision, ir, provider=provider,
        source_revision=inventory["source_revision"], exact_target_paths=inventory["exact_target_paths"])
    rows = provider._fulfillment_receipts
    first = next(row for row in rows if row["stage"] == "CANDIDATE_VALIDATED" and row["attempt"] == 1)
    feedback = json.loads(first["validation_feedback"])
    assert first["validation_passed"] is False
    assert first["failed_predicate"] == "OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST"
    start = next(row for row in rows if row["stage"] == "MODEL_REQUEST_PENDING" and row["attempt"] == 1)
    assert start.get("consumer_mapping_diagnostic_contract") == "existing-consumer-mapping-risk-v1"
    assert "consumer_mapping_diagnostics" in feedback["owner_repair_context"], (
        feedback["owner_repair_context"].keys(), feedback.get("repair_feedback_binding"))
    risk = feedback["owner_repair_context"]["consumer_mapping_diagnostics"]
    assert any(inventory["sources"][item["source"]]["source_ref"] == content_ref
        for item in risk["observations"])
    assert json.loads(calls[1]["same_basis_validation_feedback"])["owner_repair_context"][
        "consumer_mapping_diagnostics"] == risk
    assert next(row for row in rows if row["stage"] == "MODEL_REQUEST_PENDING"
        and row["attempt"] == 1)["consumer_mapping_diagnostic_contract"] == risk["contract"]
    assert result[0].formation_receipt["provider_call_count"] <= 4
    owner._validate_wire_feedback_lineage(rows, revision, ir, inventory, owner.fulfillment_capability_contracts())
    from copy import deepcopy
    from hashlib import sha256
    import pytest
    tampered = deepcopy(rows)
    altered = next(row for row in tampered if row["stage"] == "CANDIDATE_VALIDATED"
        and row["attempt"] == 1)
    changed = json.loads(altered["validation_feedback"])
    changed["owner_repair_context"]["consumer_mapping_diagnostics"]["observations"][0]["route"] += 1
    altered["validation_feedback"] = json.dumps(changed, separators=(",", ":"))
    altered["validation_feedback_sha256"] = sha256(altered["validation_feedback"].encode()).hexdigest()
    altered["validation_feedback_bytes"] = len(altered["validation_feedback"].encode())
    with pytest.raises(Exception, match="OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT"):
        owner._validate_wire_feedback_lineage(tampered, revision, ir, inventory,
            owner.fulfillment_capability_contracts())
    without_opt_in = [dict(row) for row in rows]
    legacy_start = next(row for row in without_opt_in if row["stage"] == "MODEL_REQUEST_PENDING"
        and row["attempt"] == 1)
    legacy_start.pop("consumer_mapping_diagnostic_contract")
    legacy_feedback = owner._bind_repair_feedback(first["validation_feedback"], without_opt_in, 1,
        revision, inventory, owner.fulfillment_capability_contracts(), None,
        ir=ir, include_owner_preconditions=True)
    assert "consumer_mapping_diagnostics" not in json.loads(legacy_feedback)["owner_repair_context"]

    invalid_start = next(row for row in without_opt_in if row["stage"] == "MODEL_REQUEST_PENDING"
        and row["attempt"] == 1)
    invalid_start["consumer_mapping_diagnostic_contract"] = "unrecognized-contract"
    with pytest.raises(Exception, match="OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT"):
        owner._validate_wire_feedback_lineage(without_opt_in, revision, ir, inventory,
            owner.fulfillment_capability_contracts())


def test_legitimate_path_valued_equality_is_observed_not_rejected():
    from tests.test_c3_reviewed_fact_method_applicability import case, preconditions
    revision, ir, inventory, plan = case(SemanticRelation.EQUALITY)
    diagnostics = owner._consumer_mapping_diagnostics(plan, inventory, owner.fulfillment_capability_contracts())
    assert diagnostics["observations"]
    assert "NOT_A_VIOLATION_OR_REVIEW_VERDICT" in diagnostics["status"]
    assert owner.validate_projection_candidate(plan, revision, ir, inventory,
        source_contract="v3", allow_review_pending=True,
        owner_preconditions=preconditions(revision, ir, inventory))
