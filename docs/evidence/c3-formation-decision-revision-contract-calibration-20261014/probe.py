"""Request-only decision-revision experiment, with unchanged application gates.

Prepare offline before --execute-once. Raw inputs and outputs stay private.
This tool cannot append to an existing Work or grant candidate admission.
"""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace

from spg.application.governed_obligations import (
    _consumer_mapping_diagnostics, fulfillment_capability_contracts,
)
from spg.domain.governed_obligation import FulfillmentProjectionCandidate, canonical_fingerprint
from spg.providers.fulfillment_candidate import (
    ModelFulfillmentCandidateProvider, _fulfillment_wire_route_observations,
)


def digest(value):
    return sha256(value.encode()).hexdigest()


def provider(factory):
    return ModelFulfillmentCandidateProvider(factory, candidate_construction=True,
        candidate_construction_contract="owner-local-interpretation-role-construction-v4",
        raw_role_repair=True, construction_consumer_instructions=True,
        unparsed_claim_repair=True, role_convergence=True)


def extend_request(feedback, preconditions, inventory, expected_diagnostic):
    """Resolve original decisions only; never select a replacement consumer."""
    data = json.loads(feedback)
    binding = data["repair_feedback_binding"]
    basis = preconditions["candidate_construction_state"]["repair_basis"]
    raw = data["untrusted_previous_wire"]
    if (digest(raw) != basis["raw_sha256"] or digest(raw) != binding["wire_output_fingerprint"]
            or binding != basis["parent_binding"] or binding["attempt"] != 1
            or binding["inventory_fingerprint"] != inventory["inventory_fingerprint"]
            or data["owner_repair_context"]["consumer_mapping_diagnostics"] != expected_diagnostic
            or json.loads(raw)["routes"] != basis["original_wire"]["routes"]):
        raise ValueError("PROBE_PARENT_IDENTITY_DRIFT")
    requests = []
    for observed in expected_diagnostic["observations"]:
        ordinal = observed["route"]
        route = basis["original_wire"]["routes"][ordinal]
        source = inventory["sources"][observed["source"]]
        if route["source_ref"] != source["source_ref"]:
            raise ValueError("PROBE_DECISION_SOURCE_DRIFT")
        requests.append({"original_route": ordinal, "source_ref": source["source_ref"],
            "component_id": observed["component_id"],
            "original_route_fingerprint": canonical_fingerprint(route)})
    if not requests or len({r["original_route"] for r in requests}) != len(requests):
        raise ValueError("PROBE_DECISION_TARGET_UNAVAILABLE")
    extension = {
        "contract": "request-only-decision-revision-prototype-v1",
        "parent_feedback_sha256": digest(feedback),
        "parent_binding_fingerprint": canonical_fingerprint(binding),
        "diagnostic_fingerprint": canonical_fingerprint(expected_diagnostic),
        "decision_status": "REOPEN_REQUIRED; SEMANTIC_VALIDITY_UNKNOWN",
        "invalidated_assumption": "THIS_OLD_CONSUMER_CHOICE_CAN_BE_PRESERVED_WITHOUT_REASSESSMENT",
        "not_invalidated": "NO_CONSUMER_HAS_BEEN_DECLARED_WRONG_BY_THIS_RISK_DIAGNOSTIC",
        "reason_ref": "owner_repair_context.consumer_mapping_diagnostics.question",
        "reconsider_fields": ["capability", "current_fact_dependencies", "target_paths",
            "provenance_support_refs", "rationale"],
        "preserve": ["original_source_identity_and_version", "accepted_fact_relation_value_order_scope_qualifiers_authority",
            "original_required_meaning_and_full_coverage", "existing_permissions_and_gates",
            "unrelated_lawful_decisions_unless_another_existing_failure_requires_edit"],
        "observable_outcomes": {
            "replace": "Propose a justified revised consumer and its dependent operands.",
            "remove": "Remove an unjustified extra contribution only if required meaning remains covered.",
            "retain": "You may keep this consumer after reassessment. Express the fresh method-to-meaning justification in its existing rationale through a same-choice replacement; this is a claim for Review, not evidence or PASS.",
            "unresolved": "Keep uncertainty explicit under the existing contract if no lawful choice is established."},
        "requests": requests,
        "authority": "REPAIR_FOCUS_ONLY; NO_RECOMMENDED_CONSUMER_OR_NEW_VALIDITY_PREDICATE",
    }
    changed = deepcopy(data)
    changed["owner_repair_context"]["decision_revision_requests"] = extension
    revised = deepcopy(preconditions)
    targets = revised["candidate_construction_state"]["repair_targets"]
    for i, request in enumerate(requests):
        targets.append({"status": "REOPEN_REQUIRED; NOT_A_VALIDATION_FAILURE",
            "decision_revision_ref": f"owner_repair_context.decision_revision_requests.requests[{i}]",
            "source_ref": request["source_ref"],
            "original_route_indices": [request["original_route"]],
            "original_route_fingerprints": [request["original_route_fingerprint"]]})
    # No original feedback predicate or Owner condition may be removed or edited.
    restored = deepcopy(changed)
    del restored["owner_repair_context"]["decision_revision_requests"]
    assert restored == data
    restored_preconditions = deepcopy(revised)
    restored_preconditions["candidate_construction_state"]["repair_targets"] = deepcopy(
        preconditions["candidate_construction_state"]["repair_targets"])
    assert restored_preconditions == preconditions
    return json.dumps(changed, separators=(",", ":")), revised, extension


class Captured(Exception):
    pass


def capture_request(inventory, capabilities, feedback, preconditions):
    captured = {}
    def generate(**request):
        captured.update(request)
        raise Captured()
    try:
        provider(lambda: SimpleNamespace(generate=generate, close=lambda: None)).form(
            inventory, capabilities, validation_feedback=feedback, owner_preconditions=preconditions)
    except Captured:
        return captured
    raise RuntimeError("PROBE_PREFLIGHT_DID_NOT_CAPTURE")


def prepare():
    rows_path = Path("/historical/ordinary34-owner-receipts.json")
    inventory_path = Path("/inventory/immutable-inventory.json")
    rows = json.loads(rows_path.read_text())
    inventory = json.loads(inventory_path.read_text())
    feedback = Path("/prior/bound-feedback.json").read_text()
    if digest(feedback) != "6503e481b0ebfe6f5a4cc6a5817a7f065dcbcf99981bcd1973ef731296b67ffb":
        raise ValueError("PROBE_PREVIOUS_FEEDBACK_DRIFT")
    capabilities = fulfillment_capability_contracts()
    observed, unavailable = _fulfillment_wire_route_observations(rows[1]["candidate_output"],
        inventory, capabilities, validation_feedback=rows[0].get("feedback"),
        owner_preconditions=rows[0]["owner_source_preconditions"])
    if unavailable:
        raise ValueError("PROBE_ORIGINAL_CANDIDATE_NOT_EVALUABLE")
    original = FulfillmentProjectionCandidate(inventory_fingerprint=inventory["inventory_fingerprint"],
        routes=tuple(route for _, _, route in observed))
    diagnostic = _consumer_mapping_diagnostics(original, inventory, capabilities)
    preconditions = rows[3]["owner_source_preconditions"]
    bound, revised, extension = extend_request(feedback, preconditions, inventory, diagnostic)
    old_request = capture_request(inventory, capabilities, feedback, preconditions)
    new_request = capture_request(inventory, capabilities, bound, revised)
    if old_request["instructions"] != new_request["instructions"] or old_request["output_schema"] != new_request["output_schema"]:
        raise ValueError("PROBE_UNEXPECTED_PROMPT_OR_SCHEMA_CHANGE")
    # Negative controls must fail before any network request.
    rejected = []
    for name in ("raw-wire", "inventory", "diagnostic-route", "parent-binding"):
        bad = json.loads(feedback)
        if name == "raw-wire": bad["untrusted_previous_wire"] += " "
        elif name == "inventory": bad["repair_feedback_binding"]["inventory_fingerprint"] = "0" * 64
        elif name == "diagnostic-route": bad["owner_repair_context"]["consumer_mapping_diagnostics"]["observations"][0]["route"] += 1
        else: bad["repair_feedback_binding"]["response_receipt_id"] = "different-receipt"
        try:
            extend_request(json.dumps(bad), preconditions, inventory, diagnostic)
        except ValueError:
            rejected.append(name)
        else:
            raise ValueError("PROBE_NEGATIVE_CONTROL_NOT_REJECTED")
    manifest = {
        "prototype": "ISOLATED_REQUEST_ONLY; NOT_INSTALLED_RUNTIME_CONTRACT",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": "a5d7712e8978d9a26faa4ef8bb1379c22540d156",
        "historical_receipts_sha256": sha256(rows_path.read_bytes()).hexdigest(),
        "inventory_file_sha256": sha256(inventory_path.read_bytes()).hexdigest(),
        "inventory_fingerprint": inventory["inventory_fingerprint"],
        "original_wire_sha256": digest(rows[1]["candidate_output"]),
        "historical_attempt": rows[0]["attempt"],
        "parent_request_receipt_id": rows[0]["receipt_id"],
        "parent_response_receipt_id": rows[1]["receipt_id"],
        "parent_validation_receipt_id": rows[2]["receipt_id"],
        "prior_feedback_sha256": digest(feedback), "revised_feedback_sha256": digest(bound),
        "feedback_bytes_before": len(feedback.encode()), "feedback_bytes_after": len(bound.encode()),
        "extension_fingerprint": canonical_fingerprint(extension),
        "revision_original_route_ordinals": [r["original_route"] for r in extension["requests"]],
        "old_repair_target_count": len(preconditions["candidate_construction_state"]["repair_targets"]),
        "revised_repair_target_count": len(revised["candidate_construction_state"]["repair_targets"]),
        "instructions_unchanged": True, "output_schema_unchanged": True,
        "original_feedback_and_preconditions_preserved": True,
        "negative_controls_rejected": rejected,
        "generation_input_sha256": digest(new_request["input_text"]),
        "generation_instructions_sha256": digest(new_request["instructions"]),
        "output_schema_fingerprint": canonical_fingerprint(new_request["output_schema"]),
        "probe_script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    from spg.application import governed_obligations as owner_module
    from spg.providers import fulfillment_candidate as provider_module
    manifest["actual_source_module_sha256"] = {Path(module.__file__).name:
        sha256(Path(module.__file__).read_bytes()).hexdigest() for module in (owner_module, provider_module)}
    return inventory, capabilities, bound, revised, extension, manifest


def inspect_edits(output, preconditions, extension):
    try:
        edits = json.loads(output)
        original = preconditions["candidate_construction_state"]["repair_basis"]["original_wire"]["routes"]
        replacements = {row["index"]: row["route"] for row in edits.get("replace", [])}
        removed = [row if type(row) is int else row["index"] for row in edits.get("remove", [])]
        outcomes = []
        for target in extension["requests"]:
            index = target["original_route"]
            old, new = original[index], replacements.get(index)
            outcomes.append({"original_route": index,
                "operation": "REMOVE" if index in removed else "REPLACE" if new is not None else "UNCHANGED",
                "capability_before": old["capability"],
                "capability_after": None if index in removed else (new or old)["capability"],
                "changed_fields": [key for key in old if new is not None and old.get(key) != new.get(key)],
                "fresh_rationale_sha256": digest(new["rationale"]) if new is not None else None})
        return {"decision_outcomes": outcomes, "replacement_ordinals": list(replacements),
            "removed_ordinals": removed, "appended_count": len(edits.get("append", [])),
            "retained_original_ordinals": [i for i in range(len(original)) if i not in replacements and i not in removed],
            "interpretation": "EDIT_OBSERVATION_ONLY; NO_SEMANTIC_CORRECTNESS_VERDICT"}
    except (ValueError, KeyError, TypeError):
        return {"decision_outcomes": "NOT_EVALUABLE"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-once", action="store_true")
    args = parser.parse_args()
    inventory, capabilities, bound, preconditions, extension, manifest = prepare()
    private, evidence = Path("/private"), Path("/evidence")
    if not args.execute_once:
        private.joinpath("prepared-feedback.json").write_text(bound)
        private.joinpath("prepared-preconditions.json").write_text(json.dumps(preconditions))
        evidence.joinpath("preflight.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(json.dumps(manifest, indent=2))
        return
    frozen = json.loads(evidence.joinpath("preflight.json").read_text())
    for key in manifest:
        if key != "recorded_at_utc" and manifest[key] != frozen[key]:
            raise ValueError("PROBE_PREPARED_IDENTITY_DRIFT")
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
                raise RuntimeError("PROBE_CALL_COUNT_OR_INPUT_DRIFT")
            calls.append(True)
            return actual.generate(**request)
        return SimpleNamespace(generate=generate, close=actual.close)
    p = provider(runtime)
    observed = {}
    def callback(**values):
        observed.update(values)
        private.joinpath("response-observation.json").write_text(json.dumps(values, ensure_ascii=False, indent=2))
    failure, failure_predicates, candidate = None, [], None
    try:
        candidate = p.form(inventory, capabilities, validation_feedback=bound,
            owner_preconditions=preconditions, receipt_callback=callback)
    except Exception as error:
        codes = re.findall(r"OBLIGATION_[A-Z_]+", str(error))
        failure = {"type": type(error).__name__, "code": codes[0] if codes else "UNKNOWN"}
        diagnostics = getattr(error, "diagnostics", {})
        if isinstance(diagnostics, dict):
            failure_predicates = [{key: row[key] for key in ("code", "source", "route", "component_id") if key in row}
                for row in diagnostics.get("violations", [])]
    telemetry = p.last_observation or {}
    report = {"recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "preflight_extension_fingerprint": frozen["extension_fingerprint"],
        "logical_formation_calls": len(calls), "review_calls": 0,
        "profile": {"model": "deepseek-flash", "reasoning_effort": "none", "max_output_tokens": 16384, "timeout_seconds": 120},
        "new_work_created": False, "historical_work_modified": False,
        "decoded_candidate": candidate is not None, "failure": failure,
        "failed_predicates": failure_predicates,
        "provider": {key: telemetry.get(key) for key in ("request_id", "provider", "requested_model", "effective_model",
            "usage", "timing", "transport_retry_count", "output_evidence", "validation_feedback_sha256",
            "generation_input_sha256", "generation_instructions_sha256")},
        "response_sha256": observed.get("candidate_output_sha256"),
        "response_bytes": observed.get("candidate_output_bytes"),
        "edit_observation": inspect_edits(observed["candidate_output"], preconditions, extension)
            if isinstance(observed.get("candidate_output"), str) else "NOT_EVALUABLE",
        "full_validator_review_admission_guardian": "NOT_EXECUTED; NO_PASS_GRANTED"}
    evidence.joinpath("result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
