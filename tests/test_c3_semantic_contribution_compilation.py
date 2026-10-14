"""Contribution-level expression with Owner-compiled separator geometry.

The model chooses semantic components and consumers. The Owner attaches only
punctuation between a source's own chosen components and expands a complete
per-source restatement into the candidate. Coverage, dedup, dependency,
Review and recovery gates are unchanged.
"""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from spg.application import governed_obligations as owner
from spg.domain.governed_obligation import fulfillment_source_semantic_text
from spg.domain.model_runtime import ModelProvider, ModelTiming, ModelUsage, StructuredModelResult
from spg.providers import fulfillment_candidate as wire_owner
from tests.test_c3_early_consumer_mapping_diagnostics import content_and_scope_case
from tests.test_c3_fulfillment_capacity_representation import controlled_wire, decode_review_input
from tests.test_c3_semantic_contract_calibration import review
from tests.test_c3_source_consumption_proof import fixture_review_proof


def _inventory(texts):
    return {"sources": [{"kind": "WORK_CONTEXT", "source_ref": f"s{i}", "payload": {"content": t}}
        for i, t in enumerate(texts)]}


def _route(s, a, z, text):
    return {"s": s, "c": 0, "a": a, "z": z, "q": text[a:z], "f": [], "t": [], "u": [], "r": "r"}


def test_only_punctuation_between_own_components_is_attached():
    text = "Do not deploy, publish, add pages, or change README.md."
    inventory = _inventory([text])
    routes = [_route(0, 0, 13, text), _route(0, 15, 22, text), _route(0, 24, 54, text)]
    observations = wire_owner._compile_contribution_geometry(routes, inventory)
    covered = {i for r in routes for i in range(r["a"], r["z"])}
    assert all(c.isspace() or i in covered for i, c in enumerate(text))
    assert all(r["q"] == text[r["a"]:r["z"]] for r in routes)
    assert {tuple(o["attached_codepoints"]) for o in observations} == {(13,), (22,), (54,)}
    assert all(o["predicate"] == "PUNCTUATION_ONLY_SEPARATOR" for o in observations)


@pytest.mark.parametrize("text,spans,missing", (
    # A conjunction joining two requirements is meaning, not encoding.
    ("Verify the exact heading and paragraph and leave a reviewable Candidate.",
     ((0, 38), (43, 71)), (39, 42)),
    # A governing negation must never be attached to its operation.
    ("Do not deploy, publish, add pages, or change README.md.", ((7, 13), (15, 22), (24, 54)), (0, 6)),
    ("Excluded from this Work: Deployment.", ((25, 35),), (0, 24)),
))
def test_words_negation_and_qualifiers_are_never_attached(text, spans, missing):
    inventory = _inventory([text])
    routes = [_route(0, a, z, text) for a, z in spans]
    wire_owner._compile_contribution_geometry(routes, inventory)
    covered = {i for r in routes for i in range(r["a"], r["z"])}
    assert all(i not in covered for i in range(*missing) if not text[i].isspace())


def test_compilation_never_crosses_source_identity_or_fills_unrouted_source():
    text = "Verify heading, paragraph."
    inventory = _inventory([text, text])
    routes = [_route(0, 0, 25, text)]
    wire_owner._compile_contribution_geometry(routes, inventory)
    assert routes[0]["z"] == 26 and routes[0]["q"] == text
    assert [r["s"] for r in routes] == [0]
    # The trailing gap contains words, so even its separating comma stays.
    partial = [_route(0, 0, 14, text)]
    assert wire_owner._compile_contribution_geometry(partial, _inventory([text])) == []
    assert partial[0]["z"] == 14


def run_case(*, compile_contract=True, first="duplicate", repair="reexpress", equivalent=True):
    """Live-like local repair over the existing role-construction path.

    first="duplicate": the first proposal repeats a retained component with the
    same consumer, the observed ordinary34 pattern; "punctuation": one quote
    omits only its terminal punctuation.
    """
    revision, ir, inventory, plan, content_ref = content_and_scope_case()
    original = deepcopy((revision, ir, inventory, plan))
    calls = []
    texts = {s["source_ref"]: fulfillment_source_semantic_text(s) for s in inventory["sources"]}
    content = next(i for i, r in enumerate(plan.routes) if r.source_ref == content_ref and r.capability == "ARTIFACT_CONTENT")
    clipped = next(i for i, r in enumerate(plan.routes)
        if r.component_basis.source_component_quote == texts[r.source_ref]
        and texts[r.source_ref][-1] in {".", "。"} and texts[r.source_ref].count(texts[r.source_ref][:-1]) == 1
        and sum(1 for o in plan.routes if o.source_ref == r.source_ref) == 1)
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
                if first == "duplicate":
                    twin = deepcopy(roles[content])
                    twin["rationale"] = "Different wording for the same contribution."
                    roles.append(twin)
                else:
                    roles[clipped]["component_quote"] = texts[roles[clipped]["source_ref"]][:-1]
                output = json.dumps({"routes": roles})
            else:
                basis = payload["owner_source_preconditions"]["candidate_construction_state"]["repair_basis"]
                old = basis["original_wire"]["routes"]
                edited = {"basis": basis["raw_sha256"], "replace": [], "remove": [], "append": []}
                if compile_contract:
                    edited["source_reexpressions"] = []
                if first == "punctuation":
                    edited["replace"].append({"index": clipped, "route": roles[clipped]})
                elif repair in {"reexpress", "conflict"}:
                    members = [i for i, r in enumerate(old) if r["source_ref"] == content_ref]
                    unique = []
                    for i in members:
                        choice = {k: v for k, v in old[i].items() if k != "rationale"}
                        if all(choice != {k: v for k, v in u.items() if k != "rationale"} for u in unique):
                            unique.append(deepcopy(old[i]))
                    edited["source_reexpressions"].append({"source_ref": content_ref, "routes": unique})
                    if repair == "conflict":
                        edited["remove"].append({"index": members[-1]})
                else:
                    edited["remove"].append({"index": len(old) - 1})
                output = json.dumps(edited)
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-compilation", effective_model="controlled-compilation",
            request_id=f"controlled-compilation-{len(calls)}", usage=ModelUsage(unknown=True), timing=ModelTiming(), retry_count=0)
    provider = wire_owner.ModelFulfillmentCandidateProvider(
        lambda: SimpleNamespace(generate=generate, close=lambda: None), candidate_construction=True,
        candidate_construction_contract="owner-local-interpretation-role-construction-v4",
        raw_role_repair=True, construction_consumer_instructions=True, role_convergence=True,
        semantic_compilation=compile_contract)
    kwargs = {"provider": provider, "source_revision": inventory["source_revision"], "exact_target_paths": inventory["exact_target_paths"]}
    result = owner.form_fulfillment_projection(revision, ir, **kwargs)
    assert original == (revision, ir, inventory, plan)
    return result, provider, calls, (revision, ir, inventory, kwargs), content_ref


def _constructions(provider, revision, inventory):
    rows = owner.FulfillmentFormationReceipts(revision, inventory, memory=provider._fulfillment_receipts).records()
    return rows, [r["wire_presentation"].get("candidate_construction") for r in rows if r["stage"] == "MODEL_RESPONSE_OBSERVED"]


def test_marker_is_negotiated_and_projected_to_actual_construction_request():
    _, provider, calls, (revision, _, inventory, _), _ = run_case()
    rows, _ = _constructions(provider, revision, inventory)
    starts = [r for r in rows if r["stage"] == "MODEL_REQUEST_PENDING"]
    assert all(r["owner_source_preconditions"]["semantic_compilation_contract"]
        == wire_owner._SEMANTIC_COMPILATION_CONTRACT for r in starts)
    first, repair = calls[0][0], calls[1][0]
    assert "contribution level" in first["instructions"]
    assert "Preserve punctuation and all nonspace characters" not in first["instructions"]
    assert "one component with the same consumer is ONE binding" in first["instructions"]
    assert "source_reexpressions" in repair["instructions"]
    assert "source_reexpressions" in repair["output_schema"]["properties"]


def test_source_reexpression_removes_duplicate_without_owner_selecting_routes():
    result, provider, calls, (revision, ir, inventory, kwargs), content_ref = run_case()
    assert len(calls) == 3 and all(b.state != "UNRESOLVED" for b in result)
    _, constructions = _constructions(provider, revision, inventory)
    repair = constructions[-1]
    # The model's restated set, not an Owner choice, removes the duplicate.
    assert len(repair["reexpressed_original_ordinals"]) == repair["restated_route_count"] + 1
    assert repair["removed_original_ordinals"] == [] and repair["replaced_original_ordinals"] == []
    assert "COVERAGE_GATE_UNCHANGED" in repair["geometry_compilation"]["status"]
    before = deepcopy(provider._fulfillment_receipts)
    owner.form_fulfillment_projection(revision, ir, **kwargs)
    assert len(calls) == 3 and provider._fulfillment_receipts == before


def test_reexpression_conflicting_with_per_route_edit_is_rejected_before_review():
    result, _, calls, _, _ = run_case(repair="conflict")
    assert len(calls) == 2 and all(b.state == "UNRESOLVED" for b in result)
    assert result[0].formation_receipt["terminal_reason"] == "OBLIGATION_FORMATION_LOCAL_EDIT_TARGET_INVALID"


def test_restatement_cannot_override_negative_independent_review():
    result, _, calls, _, _ = run_case(equivalent=False)
    assert len(calls) == 3 and all(b.state == "UNRESOLVED" for b in result)


def test_unnegotiated_provider_keeps_historical_request_and_edit_shape():
    result, provider, calls, (revision, _, inventory, _), _ = run_case(compile_contract=False, repair="remove")
    assert len(calls) == 3 and all(b.state != "UNRESOLVED" for b in result)
    rows, constructions = _constructions(provider, revision, inventory)
    assert all("semantic_compilation_contract" not in (r.get("owner_source_preconditions") or {})
        for r in rows if r["stage"] == "MODEL_REQUEST_PENDING")
    assert "source_reexpressions" not in calls[1][0]["output_schema"]["properties"]
    assert all("geometry_compilation" not in (c or {}) for c in constructions)


def test_old_receipts_are_not_upgraded_and_marker_drift_stops_without_calls():
    _, provider, calls, (revision, ir, inventory, kwargs), _ = run_case(compile_contract=False, repair="remove")
    before = deepcopy(provider._fulfillment_receipts)
    provider.supports_semantic_compilation = True
    owner.form_fulfillment_projection(revision, ir, **kwargs)
    assert len(calls) == 3 and provider._fulfillment_receipts == before
    _, provider, calls, (revision, ir, inventory, kwargs), _ = run_case()
    rows = provider._fulfillment_receipts
    rows[:] = owner.FulfillmentFormationReceipts(revision, inventory, memory=rows).records()
    next(r for r in rows if r["stage"] == "MODEL_REQUEST_PENDING")["owner_source_preconditions"][
        "semantic_compilation_contract"] = "unknown"
    stopped = owner.form_fulfillment_projection(revision, ir, **kwargs)
    assert len(calls) == 3 and all(b.state == "UNRESOLVED" for b in stopped)


def test_first_duplicate_is_reported_by_unchanged_gate():
    _, provider, _, (revision, _, inventory, _), _ = run_case()
    rows, _ = _constructions(provider, revision, inventory)
    first = next(r for r in rows if r["stage"] == "CANDIDATE_VALIDATED" and r["attempt"] == 1)
    assert first["validation_passed"] is False
    assert "OBLIGATION_PROJECTION_DUPLICATE_ROUTE" in json.dumps(first)


def test_punctuation_only_omission_is_compiled_and_reaches_review_in_one_candidate():
    result, provider, calls, (revision, _, inventory, _), _ = run_case(first="punctuation")
    assert len(calls) == 2 and all(b.state != "UNRESOLVED" for b in result)
    _, constructions = _constructions(provider, revision, inventory)
    attached = constructions[0]["geometry_compilation"]["attachments"]
    assert len(attached) == 1 and attached[0]["predicate"] == "PUNCTUATION_ONLY_SEPARATOR"


def test_same_omission_without_marker_still_fails_unchanged_coverage_gate():
    _, provider, _, (revision, _, inventory, _), _ = run_case(compile_contract=False, first="punctuation")
    rows, _ = _constructions(provider, revision, inventory)
    first = next(r for r in rows if r["stage"] == "CANDIDATE_VALIDATED" and r["attempt"] == 1)
    assert first["validation_passed"] is False
    assert "OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST" in json.dumps(first)


def run_decision_case(disposition, *, keep_consumer):
    """Decision revision + action consistency, answered with a source restatement."""
    revision, ir, inventory, plan, content_ref = content_and_scope_case()
    calls = []
    def generate(**request):
        payload = json.loads(request["input_text"])
        calls.append((request, payload))
        if "untrusted_fulfillment_candidate" in payload:
            candidate = decode_review_input(payload)
            output = fixture_review_proof(inventory, candidate, review(inventory, candidate), payload).model_dump_json()
        else:
            feedback = payload["same_basis_validation_feedback"]
            wire, _ = controlled_wire(inventory, plan, feedback=feedback, owner_preconditions=payload["owner_source_preconditions"])
            caps = payload["existing_capability_contracts"]
            roles = [{"source_ref": inventory["sources"][row["s"]]["source_ref"],
                "capability": caps[row["c"]]["capability"], "component_quote": row["q"],
                "current_fact_dependencies": [inventory["sources"][i]["source_ref"] for i in row["f"]],
                "target_paths": [inventory["exact_target_paths"][i] for i in row["t"]],
                "provenance_support_refs": [inventory["sources"][i]["source_ref"] for i in row["u"]],
                "rationale": row["r"]} for row in wire["routes"]]
            if feedback is None:
                # Omit a leading word (meaning), never only punctuation.
                texts = {s["source_ref"]: fulfillment_source_semantic_text(s) for s in inventory["sources"]}
                broken = next(i for i, r in enumerate(roles) if r["source_ref"] != content_ref
                    and sum(1 for o in roles if o["source_ref"] == r["source_ref"]) == 1
                    and " " in texts[r["source_ref"]] and texts[r["source_ref"]][0].isalnum()
                    and texts[r["source_ref"]].count(texts[r["source_ref"]].split(" ", 1)[1]) == 1)
                roles[broken]["component_quote"] = texts[roles[broken]["source_ref"]].split(" ", 1)[1]
                output = json.dumps({"routes": roles})
            else:
                state = payload["owner_source_preconditions"]["candidate_construction_state"]
                basis = state["repair_basis"]
                old = basis["original_wire"]["routes"]
                target = next(t for t in state["repair_targets"] if t.get("decision_revision_ref"))["original_route_indices"][0]
                broken = next(t for t in state["repair_targets"] if t.get("predicate")
                    == "OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST")["original_route_indices"][0]
                repaired = deepcopy(old[broken])
                repaired["component_quote"] = None
                restated = [deepcopy(r) for i, r in enumerate(old) if r["source_ref"] == content_ref
                    and (i != target or keep_consumer)]
                output = json.dumps({"basis": basis["raw_sha256"], "replace": [{"index": broken, "route": repaired}],
                    "remove": [], "append": [],
                    "source_reexpressions": [{"source_ref": content_ref, "routes": restated}],
                    "decision_revisions": [{"original_route": target, "disposition": disposition,
                        "revised_fields": [], "justification": "Restated the complete source contribution set."}]})
        return StructuredModelResult(output_text=output, provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-compilation", effective_model="controlled-compilation",
            request_id=f"controlled-compilation-{len(calls)}", usage=ModelUsage(unknown=True), timing=ModelTiming(), retry_count=0)
    provider = wire_owner.ModelFulfillmentCandidateProvider(
        lambda: SimpleNamespace(generate=generate, close=lambda: None), candidate_construction=True,
        candidate_construction_contract="owner-local-interpretation-role-construction-v4",
        raw_role_repair=True, construction_consumer_instructions=True, role_convergence=True,
        decision_revision_actions=True, semantic_compilation=True)
    result = owner.form_fulfillment_projection(revision, ir, provider=provider,
        source_revision=inventory["source_revision"], exact_target_paths=inventory["exact_target_paths"])
    return result, calls


def test_restated_removal_satisfies_remove_disposition_without_owner_choice():
    result, calls = run_decision_case("remove", keep_consumer=False)
    assert len(calls) == 3 and all(b.state != "UNRESOLVED" for b in result)


@pytest.mark.parametrize("disposition", ("remove", "revise"))
def test_restatement_reproducing_original_choice_cannot_claim_remove_or_revise(disposition):
    result, calls = run_decision_case(disposition, keep_consumer=True)
    assert len(calls) == 2 and all(b.state == "UNRESOLVED" for b in result)
    assert result[0].formation_receipt["terminal_reason"] == "OBLIGATION_FORMATION_DECISION_ACTION_INCONSISTENT"
