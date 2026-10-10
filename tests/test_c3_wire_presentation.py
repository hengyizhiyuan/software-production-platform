"""Lossless representation is request bound; no Candidate repair or authority."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from spg.application import governed_obligations as a
from spg.providers import fulfillment_candidate as p
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case, controlled_wire


def case():
    rev, ir, inventory, plan = controlled_capacity_case()
    caps = a.fulfillment_capability_contracts()
    owner = a._owner_source_preconditions(rev, ir, inventory, caps,
        wire_presentation_contract=p._WIRE_PRESENTATION_CONTRACT)
    wire, metadata = controlled_wire(inventory, plan, owner_preconditions=owner)
    body = json.dumps(wire, ensure_ascii=False)
    raw = " \n```json\n" + body + "\n```\n "
    return rev, ir, inventory, plan, caps, owner, metadata, body, raw


def test_exact_frame_and_unicode_geometry_keep_original_identity():
    _, _, inventory, plan, caps, owner, metadata, body, raw = case()
    before = deepcopy((inventory, plan, owner))
    decoded = p._decode_fulfillment_candidate_wire(raw, inventory, caps, owner_preconditions=owner)
    plain = p._decode_fulfillment_candidate_wire(body, inventory, caps, owner_preconditions=owner)
    assert decoded == plain
    inner, observation = p._fulfillment_wire_value(raw, owner)
    assert inner == body
    assert observation["original_wire_sha256"] == sha256(raw.encode()).hexdigest()
    start, end = observation["inner_character_range"]
    a0, z0 = observation["inner_utf8_byte_range"]
    assert raw[start:end] == body and raw.encode()[a0:z0] == body.encode()
    assert p._safe_fulfillment_response_output(raw, owner_preconditions=owner)[:3] == (
        raw, sha256(raw.encode()).hexdigest(), len(raw.encode()))
    assert before == (inventory, plan, owner)
    assert all(r.component_basis is not None for r in decoded.routes)
    legacy_wire, _ = controlled_wire(inventory, plan)
    with pytest.raises(p._FulfillmentWireValidationError, match="WIRE_JSON_INVALID"):
        p._decode_fulfillment_candidate_wire("```json\n"+json.dumps(legacy_wire)+"\n```", inventory, caps)


@pytest.mark.parametrize("mutation", ("prose", "second-value", "second-frame", "no-close", "truncated", "duplicate", "wrong-identity", "wrong-source"))
def test_framing_never_repairs_json_or_bypasses_original_gates(mutation):
    _, _, inventory, _, caps, owner, _, body, raw = case()
    wire = json.loads(body)
    if mutation == "prose": raw = "Explanation\n" + raw
    if mutation == "second-value": raw = "```json\n" + body + "{}\n```"
    if mutation == "second-frame": raw += "\n```json\n{}\n```"
    if mutation == "no-close": raw = "```json\n" + body
    if mutation == "truncated": raw = "```json\n" + body[:-8] + "\n```"
    if mutation == "duplicate": raw = "```json\n{\"v\":1," + body[1:] + "\n```"
    if mutation == "wrong-identity":
        wire["h"] = "0" * 64; raw = "```json\n" + json.dumps(wire) + "\n```"
    if mutation == "wrong-source":
        wire["routes"][0]["s"] = len(inventory["sources"]); raw = "```json\n" + json.dumps(wire) + "\n```"
    with pytest.raises(ValueError):
        p._decode_fulfillment_candidate_wire(raw, inventory, caps, owner_preconditions=owner)


def test_persisted_raw_receipt_and_replay_geometry_cannot_drift():
    rev, ir, inventory, _, caps, owner, metadata, body, raw = case()
    recorder = a.FulfillmentFormationReceipts(rev, inventory)
    common = dict(owner_source_preconditions=owner, owner_repair_context_contract="existing-owner-preconditions-v1", **metadata)
    recorder.append("MODEL_REQUEST_PENDING", 1, source_role_contract="v3", feedback=None, **common)
    recorder.append("MODEL_RESPONSE_OBSERVED", 1, candidate_output=raw, candidate_output_sha256=sha256(raw.encode()).hexdigest(),
        candidate_output_bytes=len(raw.encode()), candidate_retained=True, **common)
    rows = recorder.records()
    original, bound = a._wire_response_basis(rows, 1, rev, inventory, caps)
    assert original == raw and bound["wire_presentation"] == p._fulfillment_wire_value(raw, owner)[1]
    changed = deepcopy(list(rows))
    changed[1]["wire_presentation"]["inner_character_range"][0] += 1
    with pytest.raises(p._FulfillmentWireReceiptIdentityError, match="IDENTITY_DRIFT"):
        a._wire_response_basis(changed, 1, rev, inventory, caps)
    assert a._wire_response_basis(rows, 1, rev, inventory, caps)[0] == raw


@pytest.mark.parametrize("checkpoint", (None, "first-observation", "first-validation", "second-observation"))
def test_framed_feedback_recovery_preserves_original_attempt_and_model_budget(checkpoint):
    from dataclasses import replace
    from types import SimpleNamespace
    from tests.test_c3_fulfillment_wire_feedback import provider_for_case, run_case, Checkpoint
    revision, ir, inventory, plan = controlled_capacity_case()
    provider, calls = provider_for_case(inventory, plan, checkpoint=checkpoint)
    original_factory = provider.runtime_factory
    def factory():
        runtime = original_factory()
        def generate(**request):
            result = runtime.generate(**request)
            if "untrusted_fulfillment_candidate" not in json.loads(request["input_text"]):
                result = replace(result, output_text="```json\n" + result.output_text + "\n```")
            return result
        return SimpleNamespace(generate=generate, close=runtime.close)
    provider.runtime_factory = factory
    if checkpoint is not None:
        with pytest.raises(Checkpoint): run_case(revision, ir, inventory, provider)
        before = deepcopy(list(provider._fulfillment_receipts))
        provider._fulfillment_receipts = list(provider._fulfillment_receipts)
        provider.runtime_factory = factory
        # The fixture's callback interruption is one-shot only when disabled.
        provider.form = p.ModelFulfillmentCandidateProvider.form.__get__(provider)
    result = run_case(revision, ir, inventory, provider)
    assert all(b.state != "UNRESOLVED" for b in result) and len(calls) == 3
    rows = provider._fulfillment_receipts
    observed = [r for r in rows if r["stage"] == "MODEL_RESPONSE_OBSERVED"]
    assert len(observed) == 2 and all(r["candidate_output"].startswith("```json") for r in observed)
    failed = next(r for r in rows if r["stage"] == "CANDIDATE_VALIDATED" and r["attempt"] == 1)
    feedback = json.loads(failed["validation_feedback"])
    bound = feedback["wire_diagnostic_binding"]
    assert bound["attempt"] == 1 and bound["wire_output_fingerprint"] == observed[0]["candidate_output_sha256"]
    assert bound["wire_presentation"] == observed[0]["wire_presentation"]
    before = deepcopy(rows)
    a.validate_fulfillment_projection(result, revision, ir, exact_target_paths=inventory["exact_target_paths"])
    run_case(revision, ir, inventory, provider)
    assert len(calls) == 3 and provider._fulfillment_receipts == before
