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


def run_case(*, enable=True, repair_consumer=True, equivalent=True, unauthorized=False,
             action_consistency=False, disposition=None, revised_fields=(), replay_claim=False, legal_path=False):
    if legal_path:
        from spg.domain.engineering_semantics import SemanticRelation
        from tests.test_c3_reviewed_fact_method_applicability import case
        revision, ir, inventory, plan = case(SemanticRelation.EQUALITY)
        content_ref = next(r.source_ref for r in plan.routes if r.capability == "GIT_DIFF_SCOPE")
    else:
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
                edited = {"basis": state["repair_basis"]["raw_sha256"],
                    "replace": [{"index": broken, "route": replacement}],
                    "remove": [risk] if repair_consumer else [], "append": []}
                if action_consistency:
                    assert "decision_revisions" in request["output_schema"]["required"]
                    assert decisions["action_consistency"]["contract"] == wire_owner._DECISION_ACTION_CONTRACT
                    chosen = disposition or ("remove" if repair_consumer else "retain")
                    edited["decision_revisions"] = [{"original_route": risk, "disposition": chosen,
                        "revised_fields": list(revised_fields), "justification": "An unadmitted revised interpretation, subject to independent Review."}]
                    if not repair_consumer:
                        decision = deepcopy(roles[risk])
                        # Narrative deliberately contradicts a retain disposition:
                        # it is not a command and must never be parsed as one.
                        decision["rationale"] = "Removed as unsupported."
                        if chosen == "unresolved":
                            decision.update(capability="UNRESOLVED", current_fact_dependencies=[], target_paths=[], provenance_support_refs=[])
                        if chosen == "revise" and revised_fields == ("provenance_support_refs",):
                            decision["provenance_support_refs"] = []
                        if chosen == "revise" and revised_fields == ("component_quote",):
                            from spg.domain.governed_obligation import fulfillment_source_semantic_text
                            decision["component_quote"] = (None if decision["component_quote"] is not None else
                                fulfillment_source_semantic_text(next(s for s in inventory["sources"] if s["source_ref"] == content_ref)))
                        edited["replace"].append({"index": risk, "route": decision})
                    if replay_claim:
                        edited["append"].append(deepcopy(roles[risk]))
                    if chosen == "missing":
                        edited.pop("decision_revisions")
                output = json.dumps(edited)
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-decision-revision", effective_model="controlled-decision-revision",
            request_id=f"controlled-decision-revision-{len(calls)}", usage=ModelUsage(unknown=True), timing=ModelTiming(), retry_count=0)
    provider = wire_owner.ModelFulfillmentCandidateProvider(
        lambda: SimpleNamespace(generate=generate, close=lambda: None), candidate_construction=True,
        candidate_construction_contract="owner-local-interpretation-role-construction-v4",
        raw_role_repair=True, role_convergence=enable, decision_revision_actions=action_consistency)
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


def action_observations(provider, revision, inventory):
    rows = owner.FulfillmentFormationReceipts(revision, inventory, memory=provider._fulfillment_receipts).records()
    return rows, [r["wire_presentation"]["candidate_construction"]["decision_revision_action_observation"]
        for r in rows if r["stage"] == "MODEL_RESPONSE_OBSERVED" and r["attempt"] == 2]


def test_removal_claim_cannot_replace_same_consumer_or_reach_review():
    result, p, calls, (revision, _, inventory, _) = run_case(
        action_consistency=True, repair_consumer=False, disposition="remove")
    assert len(calls) == 2
    assert result[0].formation_receipt["terminal_reason"] == "OBLIGATION_FORMATION_DECISION_ACTION_INCONSISTENT"
    rows = owner.FulfillmentFormationReceipts(revision, inventory, memory=p._fulfillment_receipts).records()
    evidence = next(r["wire_presentation"]["candidate_construction"]["diagnostics"]["decision_revision_action_observation"]
        for r in rows if r["stage"] == "MODEL_RESPONSE_OBSERVED" and r["attempt"] == 2)
    assert evidence["status"] == "INCONSISTENT"
    assert evidence["decisions"][0]["disposition"] == "remove"
    assert evidence["decisions"][0]["operation"] == "replace"


@pytest.mark.parametrize("repair_consumer,disposition", ((True, "remove"), (False, "retain")))
def test_lawful_disposition_passes_structural_check_and_keeps_existing_review(repair_consumer, disposition):
    result, p, calls, (revision, ir, inventory, kwargs) = run_case(
        action_consistency=True, repair_consumer=repair_consumer, disposition=disposition)
    assert len(calls) == 3 and all(b.state != "UNRESOLVED" for b in result)
    rows, observations = action_observations(p, revision, inventory)
    assert observations[0]["status"].startswith("STRUCTURALLY_CONSISTENT")
    assert observations[0]["decisions"][0]["disposition"] == disposition
    before = deepcopy(p._fulfillment_receipts)
    owner.form_fulfillment_projection(revision, ir, **kwargs)
    assert len(calls) == 3 and before == p._fulfillment_receipts
    # A fixture Reviewer accepts the test plan; this never qualifies a real
    # consumer semantically, and the real independent gate remains unchanged.


@pytest.mark.parametrize("fields", ((), ("capability",)))
def test_revision_claim_requires_actual_declared_non_rationale_change(fields):
    result, _, calls, _ = run_case(action_consistency=True, repair_consumer=False,
        disposition="revise", revised_fields=fields)
    assert len(calls) == 2
    assert result[0].formation_receipt["terminal_reason"] == "OBLIGATION_FORMATION_DECISION_ACTION_INCONSISTENT"


def test_explicit_unresolved_is_preserved_and_never_admitted():
    result, p, calls, (revision, _, inventory, _) = run_case(action_consistency=True,
        repair_consumer=False, disposition="unresolved")
    assert len(calls) == 2 and all(b.state == "UNRESOLVED" for b in result)
    _, evidence = action_observations(p, revision, inventory)
    assert evidence[0]["status"].startswith("STRUCTURALLY_CONSISTENT")


def test_remove_cannot_reinsert_identical_choice_via_append():
    result, _, calls, _ = run_case(action_consistency=True, replay_claim=True)
    assert len(calls) == 2
    assert result[0].formation_receipt["terminal_reason"] == "OBLIGATION_FORMATION_DECISION_ACTION_INCONSISTENT"


def test_structural_consistency_cannot_override_negative_independent_review():
    result, _, calls, _ = run_case(action_consistency=True, equivalent=False)
    assert len(calls) == 3 and all(b.state == "UNRESOLVED" for b in result)


@pytest.mark.parametrize("change", ("action-marker", "disposition", "raw"))
def test_action_identity_drift_cannot_reopen_model_slot(change):
    _, p, calls, (revision, ir, inventory, kwargs) = run_case(action_consistency=True)
    rows = list(owner.FulfillmentFormationReceipts(revision, inventory, memory=p._fulfillment_receipts).records())
    p._fulfillment_receipts[:] = rows
    if change == "action-marker":
        next(r for r in rows if r["stage"] == "MODEL_REQUEST_PENDING")["decision_revision_action_contract"] = "unknown"
    elif change == "disposition":
        row = next(r for r in rows if r["stage"] == "MODEL_RESPONSE_OBSERVED" and r["attempt"] == 2)
        raw = json.loads(row["candidate_output"])
        raw["decision_revisions"][0]["disposition"] = "retain"
        row["candidate_output"] = json.dumps(raw)
    else:
        next(r for r in rows if r["stage"] == "MODEL_RESPONSE_OBSERVED")["candidate_output"] += " "
    stopped = owner.form_fulfillment_projection(revision, ir, **kwargs)
    assert len(calls) == 3 and all(b.state == "UNRESOLVED" for b in stopped)


def test_legitimate_path_equality_can_retain_its_existing_consumer():
    result, _, calls, _ = run_case(legal_path=True, action_consistency=True, repair_consumer=False, disposition="retain")
    assert len(calls) == 3 and all(b.state != "UNRESOLVED" for b in result)


def test_declared_component_representation_change_can_be_revised_without_forcing_consumer_change():
    result, p, calls, (revision, _, inventory, _) = run_case(action_consistency=True,
        repair_consumer=False, disposition="revise", revised_fields=("component_quote",))
    assert len(calls) == 3 and all(b.state != "UNRESOLVED" for b in result)
    _, evidence = action_observations(p, revision, inventory)
    assert "component_quote" in evidence[0]["decisions"][0]["observed_changed_fields"]


def test_missing_structured_disposition_cannot_infer_intent_from_remove():
    result, _, calls, _ = run_case(action_consistency=True, disposition="missing")
    assert len(calls) == 2
    assert result[0].formation_receipt["terminal_reason"] == "OBLIGATION_FORMATION_DECISION_ACTION_INCONSISTENT"


def test_old_receipts_are_not_upgraded_when_runtime_capability_changes():
    _, p, calls, (revision, ir, _, kwargs) = run_case()
    before = deepcopy(p._fulfillment_receipts)
    p.supports_decision_revision_actions = True
    owner.form_fulfillment_projection(revision, ir, **kwargs)
    assert len(calls) == 3 and before == p._fulfillment_receipts
