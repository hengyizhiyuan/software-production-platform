"""Pure offline comparison using the actual private wire context and decoder.

Structural all-UNRESOLVED fixture only; no semantic or Runtime qualification.
Mount this evidence folder readonly, exact basis/receipts readonly, and one new
output directory. No environment file, client, model call, database or Owner write.
"""
import sys
sys.dont_write_bytecode = True
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import inspect
import json
from pathlib import Path
import re
import time

from measure_capacity import (EXPECTED_BASIS_SHA, EXPECTED_INVENTORY, REALITY_ID,
    json_metric, json_text, metric, opaque)

BASELINE_RESULT_SHA = "fbcd899b4b8d7831f5764f75d812d24e74e5afe0aeb308765162f36e4d9dd105"
WIRE_METADATA_KEYS = ("provider_wire_version", "wire_request_fingerprint",
    "wire_table_fingerprint", "wire_schema_fingerprint")


def main(args):
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    from spg.domain.interaction import WorkRealityRevision
    from spg.domain.intent_realization import GovernedSemanticIR
    from spg.application.governed_obligations import fulfillment_inventory, fulfillment_capability_contracts
    from spg.domain.governed_obligation import (FulfillmentProjectionCandidate,
        fulfillment_source_semantic_text, fulfillment_candidate_fingerprint,
        fulfillment_components_fingerprint)
    from spg.providers.fulfillment_candidate import (ModelFulfillmentCandidateProvider,
        _fulfillment_wire_context, _decode_fulfillment_candidate_wire, _fulfillment_wire_schema)
    from spg.domain.model_runtime import (ModelProfile, ModelPurpose, ModelProvider,
        StructuredModelResult, ModelUsage, ModelTiming)
    from spg.infrastructure.model_runtime import DeepSeekResponsesModelAdapter, httpx2

    provider_path = Path(inspect.getsourcefile(ModelFulfillmentCandidateProvider))
    actual_provider_sha = sha256(provider_path.read_bytes()).hexdigest()
    assert actual_provider_sha == args.expected_provider_sha256
    basis_bytes = Path(args.basis).read_bytes()
    assert sha256(basis_bytes).hexdigest() == EXPECTED_BASIS_SHA
    baseline_bytes = Path(args.baseline_measurement).read_bytes()
    assert sha256(baseline_bytes).hexdigest() == BASELINE_RESULT_SHA
    baseline = json.loads(baseline_bytes)
    diagnostic = json.loads(Path(args.diagnostic_receipt).read_bytes())
    assert diagnostic["basis_sha256"] == EXPECTED_BASIS_SHA
    assert diagnostic["inventory_fingerprint"] == EXPECTED_INVENTORY
    data = json.loads(basis_bytes)
    rows = data["datasets"]
    revision = WorkRealityRevision.model_validate(next(row for row in
        rows["work_reality_revisions"]["rows"] if row["id"] == REALITY_ID))
    assessment = next(row for row in rows["interaction_assessments"]["rows"]
        if row["id"] == str(revision.source_assessment_id))
    ir = GovernedSemanticIR.model_validate(assessment["semantic_ir"])
    source_revision = data["actual_task_projections"][0]["fulfillment_bindings"][0]["source_revision"]
    inventory = fulfillment_inventory(revision, ir, source_revision=source_revision,
        exact_target_paths=("index.html",))
    assert inventory["inventory_fingerprint"] == EXPECTED_INVENTORY
    capabilities = fulfillment_capability_contracts()
    assert sha256(json.dumps(capabilities, sort_keys=True).encode()).hexdigest() == diagnostic["capabilities_sha256"]
    assert [source["source_ref"] for source in inventory["sources"]] == diagnostic["source_refs"]
    context = _fulfillment_wire_context(inventory, capabilities)
    metadata = {key: context[key] for key in WIRE_METADATA_KEYS}
    unresolved_index = next(index for index, capability in enumerate(capabilities)
        if capability["capability"] == "UNRESOLVED")
    old_routes, wire_routes = [], []
    for index, source in enumerate(inventory["sources"]):
        text = fulfillment_source_semantic_text(source)
        old_routes.append({"source_ref": source["source_ref"], "capability": "UNRESOLVED",
            "work_constraint_indices": [source["index"]] if source["kind"] == "WORK_CONSTRAINT" else [],
            "target_paths": [], "supporting_source_refs": [], "rationale": "Unresolved.",
            "component_basis": {"source_span_start": 0, "source_span_end": len(text),
                "source_component_quote": text, "linked_fact_refs": []}})
        wire_routes.append({"s": index, "c": unresolved_index, "a": 0, "z": len(text), "q": None,
            "f": [], "t": [], "u": [], "r": "Unresolved."})
    formal = FulfillmentProjectionCandidate.model_validate({"inventory_fingerprint": EXPECTED_INVENTORY,
        "routes": old_routes})
    formal_dump = formal.model_dump(mode="json")
    formal_size = json_metric(formal_dump)
    assert formal_size == baseline["representation_cost_experiments"]["one_full_source_component_per_source_existing_wire"]
    wire = {"v": 1, "h": context["wire_request_fingerprint"],
        "d": context["wire_table_fingerprint"], "routes": wire_routes}
    wire_text = json_text(wire, compact=True)
    decoded = _decode_fulfillment_candidate_wire(wire_text, inventory, capabilities, wire_metadata=metadata)
    assert decoded.model_dump(mode="json") == formal_dump
    assert fulfillment_candidate_fingerprint(decoded) == fulfillment_candidate_fingerprint(formal)
    assert fulfillment_components_fingerprint(decoded) == fulfillment_components_fingerprint(formal)
    assert len(decoded.routes) == len(formal.routes) == len(inventory["sources"])
    assert sum(route.component_basis is not None for route in decoded.routes) == len(formal.routes)
    temporary_wire = {**metadata,
        "source_index_table": [{"index": index, **entry} for index, entry in enumerate(context["tables"]["sources"])],
        "capability_index_table": [{"index": index, "capability": entry["capability"]}
            for index, entry in enumerate(context["tables"]["capabilities"])],
        "target_index_table": [{"index": index, "path": path}
            for index, path in enumerate(context["tables"]["target_paths"])]}
    independently_reconstructed_input = json.dumps({"immutable_inventory": inventory,
        "existing_capability_contracts": capabilities,
        "same_basis_validation_feedback": context["validation_feedback"],
        "temporary_wire": temporary_wire}, ensure_ascii=False)
    profile_data = diagnostic["profile"]
    # This controlled capability captures actual kwargs and returns only the
    # sizing fixture. No WattModelRuntime/adapter/client is initialized or called.
    captured, callbacks = [], []
    class CaptureOnlyRuntime:
        closed = False
        def generate(self, **kwargs):
            captured.append(kwargs)
            assert len(captured) == 1 and kwargs["purpose"] is ModelPurpose.STEERING_SEMANTIC
            return StructuredModelResult(output_text=wire_text, provider=ModelProvider.DEEPSEEK,
                requested_model=profile_data["model"], effective_model=None,
                request_id="offline-controlled-wire-sizing", usage=ModelUsage(unknown=True),
                timing=ModelTiming())
        def close(self):
            self.closed = True
    capture_runtime = CaptureOnlyRuntime()
    provider = ModelFulfillmentCandidateProvider(lambda: capture_runtime)
    provider_decoded = provider.form(inventory, capabilities,
        receipt_callback=lambda **values: callbacks.append(values))
    assert capture_runtime.closed and len(captured) == len(callbacks) == 1
    assert provider_decoded.model_dump(mode="json") == formal_dump
    assert captured[0]["input_text"] == independently_reconstructed_input
    assert captured[0]["output_schema"] == _fulfillment_wire_schema()
    assert all(callbacks[0][key] == metadata[key] for key in WIRE_METADATA_KEYS)
    input_text, instructions = captured[0]["input_text"], captured[0]["instructions"]
    profile = ModelProfile(purpose=ModelPurpose.STEERING_SEMANTIC, provider=ModelProvider.DEEPSEEK,
        model=profile_data["model"], reasoning_effort=profile_data["reasoning_effort"],
        timeout_seconds=profile_data["timeout_seconds"], max_output_tokens=profile_data["max_output_tokens"])
    adapter = object.__new__(DeepSeekResponsesModelAdapter)
    payload = adapter._payload(profile=profile, instructions=instructions,
        input_text=input_text, output_schema=captured[0]["output_schema"])
    body = httpx2.Request("POST", "https://offline.invalid/responses", json=payload).content
    current_size, compact_size = formal_size["compact_spacing"]["utf8_bytes"], len(wire_text.encode())
    old_body_bytes = baseline["parts"]["actual_http_json_entity_body"]["utf8_bytes"]
    result = {"schema": "c3-actual-compact-wire-measurement-v1", "started_at_utc": started,
        "scope": "OFFLINE_ACTUAL_CODEC_STRUCTURAL_ROUNDTRIP_ONLY", "basis_sha256": EXPECTED_BASIS_SHA,
        "inventory_fingerprint": EXPECTED_INVENTORY, "baseline_result_sha256": BASELINE_RESULT_SHA,
        "expected_application_source_or_snapshot": args.application_identity,
        "actual_provider_module": {"path": str(provider_path), "sha256": actual_provider_sha},
        "controller_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "wire_identity": metadata, "source_count": len(inventory["sources"]),
        "source_kinds": dict(Counter(source["kind"] for source in inventory["sources"])),
        "capability_count": len(capabilities), "component_count": len(formal.routes),
        "unique_source_coverage": len({route.source_ref for route in decoded.routes}),
        "sample_semantic_status": "ALL_UNRESOLVED_NOT_AN_ADMITTED_LEGAL_PLAN",
        "canonical_roundtrip": {"full_typed_json_equal": True, "candidate_fingerprint_equal": True,
            "components_fingerprint_equal": True, "component_count_preserved": True,
            "provider_form_uses_same_actual_decoder": True,
            "candidate_fingerprint": fulfillment_candidate_fingerprint(formal),
            "components_fingerprint": fulfillment_components_fingerprint(formal),
            "actual_decoder": "spg.providers.fulfillment_candidate._decode_fulfillment_candidate_wire"},
        "parts": {"current_formal_candidate": formal_size, "actual_compact_wire": json_metric(wire),
            "actual_compact_wire_response_text": metric(wire_text), "exact_decoder_expanded_json": metric(decoded.model_dump_json()),
            "wire_dictionary_tables": json_metric(context["tables"]), "temporary_wire_input_table": json_metric(temporary_wire),
            "new_input_text": metric(input_text), "new_instructions": metric(instructions),
            "new_compact_strict_schema": json_metric(payload["text"]["format"]["schema"]),
            "new_http_json_entity_body": metric(body)},
        "old_baseline_request_parts": {key: baseline["parts"][key] for key in
            ("instructions", "actual_input_text", "actual_compact_strict_schema", "actual_http_json_entity_body")},
        "request_part_byte_deltas": {
            "instructions": len(instructions.encode()) - baseline["parts"]["instructions"]["utf8_bytes"],
            "input_text": len(input_text.encode()) - baseline["parts"]["actual_input_text"]["utf8_bytes"],
            "compact_schema": len(json_text(payload["text"]["format"]["schema"], compact=True).encode())
                - baseline["parts"]["actual_compact_strict_schema"]["compact_spacing"]["utf8_bytes"],
            "http_json_entity_body": len(body) - old_body_bytes},
        "differences": {"response_reduction_utf8_bytes": current_size - compact_size,
            "response_reduction_percent": round(100 * (current_size - compact_size) / current_size, 6),
            "request_body_delta_utf8_bytes": len(body) - old_body_bytes,
            "request_plus_synthetic_response_delta_utf8_bytes": len(body) + compact_size - old_body_bytes - current_size,
            "sum_is_only_serialized_bytes_not_model_compute_or_token_cost": True},
        "per_source_route_metrics": [{"opaque_source_ref_sha256": opaque(source["source_ref"]),
            "kind": source["kind"], "full_route": metric(json_text(old_route, compact=True)),
            "actual_compact_route": metric(json_text(wire_route, compact=True))}
            for source, old_route, wire_route in zip(inventory["sources"], old_routes, wire_routes)],
        "limits": {"real_candidate_semantic_plan_validation": "NOT_PERFORMED", "independent_semantic_review": "NOT_PERFORMED",
            "live_provider_output_qualification": "NOT_PERFORMED", "reasoning_tokens": None, "visible_json_tokens": None,
            "byte_to_token_conversion": "NOT_PERFORMED", "historical_failure_cause": "UNKNOWN",
            "real_mixed_components_and_refs_covered_by_this_fixture": False},
        "effects": {"model_requests": 0, "http_requests_sent": 0, "credentials_loaded": False,
            "controlled_fixture_generate_entries": len(captured), "real_model_runtime_entries": 0,
            "work_or_owner_writes": 0, "prompt_or_human_text_exported": False, "holdout_read": False,
            "budget_increase": False, "qualification_claim": False}}
    result.update(ended_at_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic() - clock)
    output = Path(args.output)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"scope": result["scope"], "model_requests": 0,
        "canonical_roundtrip": True, "source_count": result["source_count"],
        "component_count": result["component_count"], "result_sha256": sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-offline", action="store_true")
    parser.add_argument("--basis", default="/basis.json")
    parser.add_argument("--diagnostic-receipt", default="/diagnostic.json")
    parser.add_argument("--baseline-measurement", default="/baseline-measurement.json")
    parser.add_argument("--expected-provider-sha256")
    parser.add_argument("--application-identity", default="PENDING_UNCOMMITTED_PRIVATE_WIRE_SNAPSHOT")
    parser.add_argument("--output", default="/c3-evidence/actual-compact-wire-measurement.json")
    args = parser.parse_args()
    if not args.execute_offline:
        print(json.dumps({"plan_only": True, "model_requests": 0,
            "requires_actual_wire_helpers": True, "requires_container_network": "none"}))
    else:
        try:
            assert re.fullmatch(r"[0-9a-f]{64}", args.expected_provider_sha256 or "")
            main(args)
        except Exception as error:
            print(json.dumps({"result": "OFFLINE_WIRE_MEASUREMENT_FAILED",
                "error_type": type(error).__name__, "model_requests": 0, "http_requests_sent": 0}))
            raise SystemExit(1)
