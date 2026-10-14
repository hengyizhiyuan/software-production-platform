"""Bound decision reassessment preserves the existing local repair and gates."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from spg.application import governed_obligations as owner
from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
from spg.providers import fulfillment_candidate as wire_owner
from tests.test_c3_early_consumer_mapping_diagnostics import content_and_scope_case
from tests.test_c3_fulfillment_capacity_representation import controlled_wire, decode_review_input
from tests.test_c3_semantic_contract_calibration import review
from tests.test_c3_source_consumption_proof import fixture_review_proof


def run_case(*, enable=True, repair_consumer=True, equivalent=True, unauthorized=False):
    revision, ir, inventory, plan, content_ref = content_and_scope_case()
    original = deepcopy((revision, ir, inventory, plan))
    calls = []
    risk = next(i for i, r in enumerate(plan.routes) if r.source_ref == content_ref and r.capability == "GIT_DIFF_SCOPE")
    broken = next(i for i, r in enumerate(plan.routes) if r.source_ref != content_ref
        and len(r.component_basis.source_component_quote) > 1)
    def generate(**request):
        payload = json.loads(request["input_text"])
        calls.append((request, payload))
        if "untrusted_fulfillment_candidate" in payload:
            candidate = decode_review_input(payload)
            reviewed = review(inventory, candidate)
            if not equivalent:
                reviewed = reviewed.model_copy(update={"component_results": tuple(
                    row.model_copy(update={"complete_and_equivalent": False}) for row in reviewed.component_results)})
            output = fixture_review_proof(inventory, candidate, reviewed, payload).model_dump_json()
        else:
            feedback = payload["same_basis_validation_feedback"]
            wire, _ = controlled_wire(inventory, plan, feedback=feedback, owner_preconditions=payload["owner_source_preconditions"])
            caps = payload["existing_capability_contracts"]
            def role(row):
                return {"source_ref": inventory["sources"][row["s"]]["source_ref"],
                    "capability": caps[row["c"]]["capability"], "component_quote": row["q"],
                    "current_fact_dependencies": [inventory["sources"][i]["source_ref"] for i in row["f"]],
                    "target_paths": [inventory["exact_target_paths"][i] for i in row["t"]],
                    "provenance_support_refs": [inventory["sources"][i]["source_ref"] for i in row["u"]],
                    "rationale": row["r"]}
            roles = [role(row) for row in wire["routes"]]
            if feedback is None:
                roles[broken]["component_quote"] = plan.routes[broken].component_basis.source_component_quote[:-1]
                output = json.dumps({"routes": roles})
            else:
                data = json.loads(feedback)
                context = data["owner_repair_context"]
                assert ("decision_revision_requests" in context) is enable
                state = payload["owner_source_preconditions"]["candidate_construction_state"]
                if enable:
                    decisions = context["decision_revision_requests"]
                    assert decisions["contract"] == wire_owner._DECISION_REVISION_CONTRACT
                    assert [r["original_route"] for r in decisions["requests"]] == [risk]
                    assert "SEMANTIC_VALIDITY_UNKNOWN" in decisions["status"]
                    assert "replacement_consumer" not in json.dumps(decisions)
                    assert any(t.get("decision_revision_ref") for t in state["repair_targets"])
                    assert any(t.get("predicate") == "OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST" for t in state["repair_targets"])
                    assert context["violations"] or data["violations"]
                replacement = roles[broken]
                if unauthorized:
                    replacement["target_paths"] = ["/unapproved-target"]
                output = json.dumps({"basis": state["repair_basis"]["raw_sha256"],
                    "replace": [{"index": broken, "route": replacement}],
                    "remove": [risk] if repair_consumer else [], "append": []})
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-decision-revision", effective_model="controlled-decision-revision",
            request_id=f"controlled-decision-revision-{len(calls)}", usage=ModelUsage(unknown=True), timing=ModelTiming(), retry_count=0)
    provider = wire_owner.ModelFulfillmentCandidateProvider(
        lambda: SimpleNamespace(generate=generate, close=lambda: None), candidate_construction=True,
        candidate_construction_contract="owner-local-interpretation-role-construction-v4",
        raw_role_repair=True, role_convergence=enable)
    kwargs = {"provider": provider, "source_revision": inventory["source_revision"], "exact_target_paths": inventory["exact_target_paths"]}
    result = owner.form_fulfillment_projection(revision, ir, **kwargs)
    assert original == (revision, ir, inventory, plan)
    return result, provider, calls, (revision, ir, inventory, kwargs)


def test_owner_constructs_revision_targets_and_preserves_other_repairs_and_replay():
    result, provider, calls, (revision, ir, inventory, kwargs) = run_case()
    assert all(b.state != "UNRESOLVED" for b in result), result[0].formation_receipt["terminal_reason"]
    assert len(calls) == 3
    rows = deepcopy(provider._fulfillment_receipts)
    hydrated = owner.FulfillmentFormationReceipts(revision, inventory, memory=provider._fulfillment_receipts).records()
    owner._validate_wire_feedback_lineage(hydrated, revision, ir, inventory, owner.fulfillment_capability_contracts())
    owner.form_fulfillment_projection(revision, ir, **kwargs)
    assert len(calls) == 3 and provider._fulfillment_receipts == rows
    assert "semantic_assumption_review" not in calls[1][0]["input_text"]


@pytest.mark.parametrize("change", ("decision", "derived-state", "raw", "marker"))
def test_decision_and_recovery_identity_drift_stops_without_calls(change):
    _, provider, calls, (revision, ir, inventory, kwargs) = run_case()
    rows = provider._fulfillment_receipts
    rows[:] = owner.FulfillmentFormationReceipts(revision, inventory, memory=rows).records()
    if change == "derived-state":
        start = next(r for r in rows if r["stage"] == "MODEL_REQUEST_PENDING" and r["attempt"] == 2)
        start["owner_source_preconditions"]["candidate_construction_state"]["repair_targets"].pop()
    elif change == "decision":
        validated = next(r for r in rows if r["stage"] == "CANDIDATE_VALIDATED" and r["attempt"] == 1)
        data = json.loads(validated["validation_feedback"])
        data["owner_repair_context"]["decision_revision_requests"]["requests"][0]["source_ref"] = "other-source"
        validated["validation_feedback"] = json.dumps(data)
    elif change == "marker":
        next(r for r in rows if r["stage"] == "MODEL_REQUEST_PENDING")["decision_revision_contract"] = "unknown"
    else:
        next(r for r in rows if r["stage"] == "MODEL_RESPONSE_OBSERVED")["candidate_output"] += " "
    stopped = owner.form_fulfillment_projection(revision, ir, **kwargs)
    assert len(calls) == 3 and all(b.state == "UNRESOLVED" for b in stopped)


@pytest.mark.parametrize("repair_consumer,equivalent,unauthorized", ((False, False, False), (True, False, False), (True, True, True)))
def test_reassessment_never_grants_validity_or_bypasses_existing_gates(repair_consumer, equivalent, unauthorized):
    result, _, calls, _ = run_case(repair_consumer=repair_consumer, equivalent=equivalent, unauthorized=unauthorized)
    assert all(b.state == "UNRESOLVED" for b in result)
    assert len(calls) == (2 if unauthorized else 3)


def test_unnegotiated_owner_contract_does_not_acquire_revision_state():
    result, _, calls, _ = run_case(enable=False)
    assert all(b.state != "UNRESOLVED" for b in result)
    assert len(calls) == 3
