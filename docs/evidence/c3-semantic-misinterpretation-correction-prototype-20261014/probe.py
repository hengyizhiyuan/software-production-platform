"""Single request-only assumption-review probe; unchanged application Owners."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace

from spg.application import governed_obligations as owner
from spg.domain.governed_obligation import canonical_fingerprint
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.providers import fulfillment_candidate as wire

spec = importlib.util.spec_from_file_location("prior_probe_helpers", "/previous_probe.py")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def digest(value):
    return sha256(value.encode()).hexdigest()


def revised_feedback(previous_feedback, preconditions, original_rows, prior_response, inventory):
    data = json.loads(previous_feedback)
    basis = preconditions["candidate_construction_state"]["repair_basis"]
    binding = data["repair_feedback_binding"]
    raw = data["untrusted_previous_wire"]
    if (digest(raw) != binding["wire_output_fingerprint"] or digest(raw) != basis["raw_sha256"]
            or binding != basis["parent_binding"] or binding["attempt"] != 1
            or binding["inventory_fingerprint"] != inventory["inventory_fingerprint"]
            or binding["request_receipt_id"] != original_rows[0]["receipt_id"]
            or binding["response_receipt_id"] != original_rows[1]["receipt_id"]
            or basis["original_wire"]["routes"] != json.loads(raw)["routes"]):
        raise ValueError("ASSUMPTION_PROBE_PARENT_IDENTITY_DRIFT")
    prior_raw = prior_response["candidate_output"]
    if digest(prior_raw) != prior_response["candidate_output_sha256"]:
        raise ValueError("ASSUMPTION_PROBE_INTERPRETATION_DRIFT")
    prior_edits = json.loads(prior_raw)
    if prior_edits["basis"] != basis["raw_sha256"]:
        raise ValueError("ASSUMPTION_PROBE_INTERPRETATION_PARENT_DRIFT")
    claims = {r["index"]: r["route"] for r in prior_edits["replace"]}
    revision = data["owner_repair_context"]["decision_revision_requests"]
    diagnostics = data["owner_repair_context"]["consumer_mapping_diagnostics"]
    if (revision["parent_binding_fingerprint"] != canonical_fingerprint(binding)
            or revision["diagnostic_fingerprint"] != canonical_fingerprint(diagnostics)):
        raise ValueError("ASSUMPTION_PROBE_DIAGNOSTIC_DRIFT")
    risks = {r["route"]: r for r in diagnostics["observations"]}
    requests = []
    for target in revision["requests"]:
        index = target["original_route"]
        original = basis["original_wire"]["routes"][index]
        risk = risks[index]
        if (target["source_ref"] != original["source_ref"]
                or inventory["sources"][risk["source"]]["source_ref"] != target["source_ref"]
                or target["original_route_fingerprint"] != canonical_fingerprint(original)
                or target["component_id"] != risk["component_id"]
                or claims[index]["source_ref"] != target["source_ref"]):
            raise ValueError("ASSUMPTION_PROBE_TARGET_IDENTITY_DRIFT")
        requests.append({"decision_to_reopen": deepcopy(target),
            "current_interpretation": {
                "status": "UNADMITTED_PRIOR_PROPOSER_CLAIM; NOT_FACT_OR_REVIEW_EVIDENCE",
                "origin_request_id": prior_response["model"]["request_id"],
                "origin_response_sha256": digest(prior_raw),
                "origin_replacement_index": index,
                "claim_sha256": digest(claims[index]["rationale"]),
                "proposed_consumer": claims[index]["capability"],
                "public_method_justification": claims[index]["rationale"]},
            "assumption_under_review": {
                "status": "ANALYST_HYPOTHESIS_EXTRACTED_FROM_PRIOR_CLAIM; NOT_ADMITTED_TRUTH",
                "claim": "A file identity inside the primary Fact subject independently establishes an additional changed-path restriction, beyond that Fact's original predicate."},
            "why_the_assumption_may_be_invalid": {
                "challenge": "Identify the original accepted relation, value, Scope or qualifier that entails the additional predicate asserted by this interpretation. Test whether the referent's identity establishes that predicate, or only identifies what the Fact concerns. A supporting provenance reference does not by itself import every obligation in that source. Recompare the proposed method's observable with this exact primary contribution.",
                "authority": "HYPOTHESIS_CHALLENGE_ONLY; YOU_MAY_REFUTE_IT_USING_THE_ORIGINAL_FACT; NO_REPLACEMENT_CONSUMER_IS_SUPPLIED"},
            "facts_that_must_remain_unchanged": deepcopy(revision["preserve"]),
            "fields_that_may_be_reconsidered": deepcopy(revision["reconsider_fields"]),
            "source_of_truth_ref": f"immutable_inventory.sources[{risk['source']}].payload"})
    if not requests or len({r["decision_to_reopen"]["original_route"] for r in requests}) != len(requests):
        raise ValueError("ASSUMPTION_PROBE_TARGET_SET_DRIFT")
    context = {"contract": "isolated-semantic-assumption-review-prototype-v1",
        "parent_feedback_sha256": digest(previous_feedback),
        "parent_revision_fingerprint": canonical_fingerprint(revision),
        "editing_basis": "ORIGINAL_FIRST_WIRE; PRIOR_INTERPRETATION_IS_ONLY_A_CLAIM_OBSERVATION",
        "requests": requests,
        "response_observation": "Use the unchanged local-edit schema. Where an existing rationale is returned, give a short inspectable statement of the chosen source-to-method interpretation and any rejected or unresolved alternative. Do not expose hidden reasoning or add fields/routes just to list alternatives. All original feedback failures remain to be addressed.",
        "authority": "NO_AUTOMATIC_CONSUMER_SELECTION; NO_FACT_CHANGE; NO_VALIDITY_OR_REVIEW_VERDICT"}
    changed = deepcopy(data)
    changed["owner_repair_context"]["semantic_assumption_review"] = context
    restored = deepcopy(changed)
    del restored["owner_repair_context"]["semantic_assumption_review"]
    assert restored == data
    return json.dumps(changed, separators=(",", ":")), context


def prepare():
    rows_path = Path("/historical/ordinary34-owner-receipts.json")
    rows = json.loads(rows_path.read_text())
    inventory_path = Path("/inventory/immutable-inventory.json")
    inventory = json.loads(inventory_path.read_text())
    previous_feedback = Path("/prior/prepared-feedback.json").read_text()
    prior_response = json.loads(Path("/prior/response-observation.json").read_text())
    if (digest(previous_feedback) != "9a364b36536f8ca65bd12b407ab80efcd62e19d6f858c99ff651d769d6c1f88a"
            or digest(prior_response["candidate_output"]) != "b5ff1b986992a1423eaf4b5ae65b6d21d88f2af77f6acf9e1743680ea35fbc90"):
        raise ValueError("ASSUMPTION_PROBE_PRIOR_OBSERVATION_DRIFT")
    original_preconditions = rows[3]["owner_source_preconditions"]
    base = {k: v for k, v in original_preconditions.items()
        if k not in {"candidate_construction_contract", "candidate_construction_state"}}
    bound, extension = revised_feedback(previous_feedback, original_preconditions, rows, prior_response, inventory)
    contract = original_preconditions["candidate_construction_contract"]
    preconditions = wire.candidate_construction_preconditions(base, inventory, bound, construction_contract=contract)
    assert preconditions == wire.candidate_construction_preconditions(base, inventory, bound, construction_contract=contract)
    assert preconditions == original_preconditions
    capabilities = owner.fulfillment_capability_contracts()
    old_request = prior.capture_request(inventory, capabilities, previous_feedback, preconditions)
    new_request = prior.capture_request(inventory, capabilities, bound, preconditions)
    assert old_request["instructions"] == new_request["instructions"]
    assert old_request["output_schema"] == new_request["output_schema"]
    # Decode the exact prior bytes to exercise the real reconstruction guard.
    try:
        wire._decode_fulfillment_candidate_wire(prior_response["candidate_output"], inventory, capabilities,
            validation_feedback=bound, owner_preconditions=preconditions)
    except wire._FulfillmentWireReceiptIdentityError:
        raise
    except ValueError as error:
        match = re.search(r"OBLIGATION_[A-Z_]+", str(error))
        preflight_decode = match.group() if match else type(error).__name__
    else:
        preflight_decode = "DECODED_PRIOR_OUTPUT_ONLY; NOT_MODEL_QUALIFICATION"
    rejected = []
    for name in ("wire", "inventory", "decision-route", "interpretation-response"):
        bad, bad_claim = json.loads(previous_feedback), deepcopy(prior_response)
        if name == "wire": bad["untrusted_previous_wire"] += " "
        elif name == "inventory": bad["repair_feedback_binding"]["inventory_fingerprint"] = "0" * 64
        elif name == "decision-route": bad["owner_repair_context"]["decision_revision_requests"]["requests"][0]["original_route_fingerprint"] = "0" * 64
        else: bad_claim["candidate_output"] += " "
        try:
            revised_feedback(json.dumps(bad), original_preconditions, rows, bad_claim, inventory)
        except ValueError:
            rejected.append(name)
        else:
            raise ValueError("ASSUMPTION_PROBE_NEGATIVE_CONTROL_NOT_REJECTED")
    manifest = {"recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_baseline": "86619c7ce28febcd916a767a98e3ffeefed25171",
        "scope": "REQUEST_ONLY_PROTOTYPE; NOT_NEW_RUNTIME_OR_G0",
        "historical_receipts_sha256": sha256(rows_path.read_bytes()).hexdigest(),
        "inventory_file_sha256": sha256(inventory_path.read_bytes()).hexdigest(),
        "inventory_fingerprint": inventory["inventory_fingerprint"],
        "original_wire_sha256": rows[1]["candidate_output_sha256"],
        "parent_receipt_ids": {k: rows[i]["receipt_id"] for i, k in enumerate(("request", "response", "validation"))},
        "prior_interpretation_response_sha256": digest(prior_response["candidate_output"]),
        "prior_interpretation_request_id": prior_response["model"]["request_id"],
        "prior_feedback_sha256": digest(previous_feedback), "new_feedback_sha256": digest(bound),
        "feedback_bytes_before": len(previous_feedback.encode()), "feedback_bytes_after": len(bound.encode()),
        "assumption_context_fingerprint": canonical_fingerprint(extension),
        "source_count": len(inventory["sources"]),
        "target_original_route_indices": [r["decision_to_reopen"]["original_route"] for r in extension["requests"]],
        "owner_preconditions_roundtrip_exact": True, "manually_injected_derived_state": False,
        "original_feedback_preserved": True, "instructions_unchanged": True, "output_schema_unchanged": True,
        "preflight_decode_of_prior_bytes": preflight_decode, "negative_controls_rejected": rejected,
        "generation_input_sha256": digest(new_request["input_text"]),
        "generation_instructions_sha256": digest(new_request["instructions"]),
        "schema_fingerprint": canonical_fingerprint(new_request["output_schema"]),
        "protocol_sha256": sha256(Path("/protocol.md").read_bytes()).hexdigest(),
        "probe_script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "helper_script_sha256": sha256(Path("/previous_probe.py").read_bytes()).hexdigest(),
        "source_module_sha256": {Path(m.__file__).name: sha256(Path(m.__file__).read_bytes()).hexdigest() for m in (owner, wire)},
        "comparison_limit": "PRIOR_PROBE_DERIVED_STATE_WIRING_CORRECTED_AS_WELL; HISTORICAL_DESCRIPTIVE_COMPARISON_NOT_CONTROLLED_CAUSAL_PROOF"}
    return inventory, capabilities, bound, preconditions, extension, manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-once", action="store_true")
    args = parser.parse_args()
    inventory, caps, bound, preconditions, extension, manifest = prepare()
    private, evidence = Path("/private"), Path("/evidence")
    if not args.execute_once:
        private.joinpath("prepared-feedback.json").write_text(bound)
        private.joinpath("prepared-preconditions.json").write_text(json.dumps(preconditions))
        private.joinpath("assumption-context.json").write_text(json.dumps(extension, ensure_ascii=False, indent=2))
        evidence.joinpath("preflight.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(json.dumps(manifest, indent=2))
        return
    frozen = json.loads(evidence.joinpath("preflight.json").read_text())
    if any(v != frozen[k] for k, v in manifest.items() if k != "recorded_at_utc"):
        raise ValueError("ASSUMPTION_PROBE_FROZEN_INPUT_DRIFT")
    private.joinpath("call-started").touch(exist_ok=False)
    from spg.domain.model_runtime import (ModelProfile, ModelProvider, ModelPurpose,
        ModelProviderRegistry, PurposeProfileRouter, WattModelRuntime)
    from spg.infrastructure.model_runtime import DeepSeekResponsesModelAdapter
    calls = []
    def runtime():
        registry = ModelProviderRegistry()
        registry.register(DeepSeekResponsesModelAdapter(api_key=lambda: os.environ["SPG_DEEPSEEK_API_KEY"],
            base_url=os.environ["SPG_DEEPSEEK_BASE_URL"]))
        profile = ModelProfile(purpose=ModelPurpose.STEERING_SEMANTIC, provider=ModelProvider.DEEPSEEK,
            model="deepseek-flash", reasoning_effort="none", max_output_tokens=16384, timeout_seconds=120)
        actual = WattModelRuntime(registry, PurposeProfileRouter({ModelPurpose.STEERING_SEMANTIC: profile}))
        def generate(**request):
            if calls or digest(request["input_text"]) != frozen["generation_input_sha256"]:
                raise RuntimeError("ASSUMPTION_PROBE_CALL_OR_INPUT_DRIFT")
            calls.append(True)
            return actual.generate(**request)
        return SimpleNamespace(generate=generate, close=actual.close)
    p, observed = prior.provider(runtime), {}
    def callback(**values):
        observed.update(values)
        private.joinpath("response-observation.json").write_text(json.dumps(values, ensure_ascii=False, indent=2))
    candidate, failed, predicates, stage = None, None, [], "PROVIDER_OR_WIRE"
    try:
        candidate = p.form(inventory, caps, validation_feedback=bound,
            owner_preconditions=preconditions, receipt_callback=callback)
        stage = "EXISTING_CANDIDATE_VALIDATOR"
        data = json.loads(Path("/inventory/basis.json").read_text())["datasets"]
        revision = WorkRealityRevision.model_validate(next(row for row in data["work_reality_revisions"]["rows"]
            if row["id"] == inventory["work_reality_revision_id"]))
        ir = GovernedSemanticIR.model_validate(next(row for row in data["interaction_assessments"]["rows"]
            if row["id"] == str(revision.source_assessment_id))["semantic_ir"])
        before = (revision.model_dump_json(), ir.model_dump_json())
        candidate, _ = owner.locate_projection_components(candidate, inventory)
        owner.validate_projection_candidate(candidate, revision, ir, inventory,
            allow_review_pending=True, source_contract="v3", owner_preconditions=preconditions)
        assert before == (revision.model_dump_json(), ir.model_dump_json())
        private.joinpath("decoded-candidate.json").write_text(candidate.model_dump_json())
    except Exception as error:
        codes = re.findall(r"OBLIGATION_[A-Z_]+", str(error))
        failed = {"stage": stage, "type": type(error).__name__, "code": codes[0] if codes else "UNKNOWN"}
        diagnostic = getattr(error, "diagnostics", {})
        if isinstance(diagnostic, dict):
            predicates = [{k: row[k] for k in ("code", "source", "route", "component_id") if k in row}
                for row in diagnostic.get("violations", [])]
    telemetry = p.last_observation or {}
    report = {"recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "logical_formation_calls": len(calls), "review_calls": 0,
        "profile": {"model": "deepseek-flash", "reasoning_effort": "none", "max_output_tokens": 16384, "timeout_seconds": 120},
        "new_work_created": False, "historical_work_modified": False,
        "decoded_candidate": candidate is not None,
        "existing_candidate_validator": "ELIGIBILITY_PASS_PENDING_REVIEW" if failed is None else "NOT_PASSED",
        "failure": failed, "failed_predicates": predicates,
        "assumption_context_fingerprint": frozen["assumption_context_fingerprint"],
        "provider": {k: telemetry.get(k) for k in ("request_id", "provider", "requested_model", "effective_model", "usage", "timing",
            "transport_retry_count", "output_evidence", "validation_feedback_sha256", "generation_input_sha256", "generation_instructions_sha256")},
        "response_sha256": observed.get("candidate_output_sha256"), "response_bytes": observed.get("candidate_output_bytes"),
        "edit_observation": prior.inspect_edits(observed["candidate_output"], preconditions,
            {"requests": [r["decision_to_reopen"] for r in extension["requests"]]})
            if isinstance(observed.get("candidate_output"), str) else "NOT_EVALUABLE",
        "independent_review_admission_guardian": "NOT_EXECUTED; NO_PASS_GRANTED"}
    evidence.joinpath("result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
