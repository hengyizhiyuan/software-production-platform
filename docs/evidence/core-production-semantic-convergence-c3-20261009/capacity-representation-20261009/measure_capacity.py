"""Offline, aggregate-only sizing of one already retained C3 formation basis.

No Settings, credentials, Client, generate, send, database, or Owner mutation.
Run in the exact retained application image with --network none. Input snapshots
must be readonly. Results are measurements, never a Candidate or qualification.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import ast
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import inspect
import json
from pathlib import Path
import re
import time

EXPECTED_BASIS_SHA = "9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c"
EXPECTED_INVENTORY = "7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf"
REALITY_ID = "332a3a38-8719-580c-a1a2-c331ae14a5ae"


def json_text(value, *, compact=False):
    options = {"ensure_ascii": False, "allow_nan": False}
    if compact:
        options.update(separators=(",", ":"))
    return json.dumps(value, **options)


def metric(value):
    data = value if isinstance(value, bytes) else value.encode("utf-8")
    text = data.decode("utf-8")
    return {"utf8_bytes": len(data), "unicode_chars": len(text),
            "sha256": sha256(data).hexdigest()}


def json_metric(value):
    return {"request_default_spacing": metric(json_text(value)),
            "compact_spacing": metric(json_text(value, compact=True))}


def opaque(value):
    return sha256(value.encode("utf-8")).hexdigest()


def instructions_for(provider_class, method):
    """Extract the actual constant, never execute Provider form/review."""
    tree = ast.parse(inspect.getsource(provider_class))
    function = next(node for node in tree.body[0].body
                    if isinstance(node, ast.FunctionDef) and node.name == method)
    calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == "generate"]
    assert len(calls) == 1
    value = ast.literal_eval(next(item.value for item in calls[0].keywords
                                 if item.arg == "instructions"))
    assert isinstance(value, str)
    return value


def string_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from string_values(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            yield from string_values(nested)


def repeated_fields(value):
    """Fixed schema field labels only; never serialize original field values."""
    buckets = defaultdict(list)
    keys = {"item", "clause", "provenance", "source_text", "content", "statement",
            "ir_id", "source_ref", "work_reality_revision_id", "production"}
    def visit(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if key in keys:
                    buckets[key].append(json_text(child, compact=True).encode("utf-8"))
                visit(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)
    visit(value)
    result = {}
    for key, rows in sorted(buckets.items()):
        unique = {sha256(row).hexdigest(): row for row in rows}
        total = sum(map(len, rows))
        result[key] = {"occurrences": len(rows), "distinct_values": len(unique),
                       "serialized_value_bytes": total,
                       "distinct_serialized_value_bytes": sum(map(len, unique.values())),
                       "repeated_value_bytes": total - sum(map(len, unique.values()))}
    return result


def schema_bounds(schema):
    bounds, unbounded = [], []
    def visit(value, path):
        if isinstance(value, dict):
            limits = {key: value[key] for key in ("minItems", "maxItems", "minLength", "maxLength")
                      if key in value}
            if limits:
                bounds.append({"schema_path": path, **limits})
            if value.get("type") == "string" and "maxLength" not in value and "enum" not in value:
                unbounded.append(path)
            if value.get("type") == "array" and "maxItems" not in value:
                unbounded.append(path)
            if value.get("type") == "integer" and "maximum" not in value:
                unbounded.append(path)
            for key, child in value.items():
                visit(child, path + "/" + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, path + "/" + str(index))
    visit(schema, "")
    return {"declared_bounds": bounds, "fields_without_schema_upper_bound": unbounded,
            "finite_global_byte_bound_from_schema": False,
            "token_capacity_from_bytes": "UNKNOWN_NO_PROVIDER_TOKENIZER_OR_VISIBLE_REASONING_SPLIT"}


def interned_string_experiment(inventory):
    counts = Counter(string_values(inventory))
    selected = sorted((value for value, count in counts.items()
                       if count > 1 and len(value.encode("utf-8")) >= 48), key=opaque)
    indices = {value: index for index, value in enumerate(selected)}
    def pack(value):
        if isinstance(value, str) and value in indices:
            return {"$measurement_string_ref": indices[value]}
        if isinstance(value, dict):
            return {key: pack(child) for key, child in value.items()}
        if isinstance(value, (list, tuple)):
            return [pack(child) for child in value]
        return value
    def expand(value):
        if isinstance(value, dict):
            if set(value) == {"$measurement_string_ref"}:
                return selected[value["$measurement_string_ref"]]
            return {key: expand(child) for key, child in value.items()}
        if isinstance(value, list):
            return [expand(child) for child in value]
        return value
    packed = {"string_table": selected, "inventory": pack(inventory)}
    assert expand(packed["inventory"]) == inventory
    return {"measurement_only_not_current_wire_contract": True,
            "exact_roundtrip": True, "interned_strings": len(selected),
            "metrics": json_metric(packed)}


def main(args):
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    from spg.domain.interaction import WorkRealityRevision
    from spg.domain.intent_realization import GovernedSemanticIR
    from spg.application.governed_obligations import fulfillment_inventory, fulfillment_capability_contracts
    from spg.domain.governed_obligation import (FulfillmentProjectionCandidate,
        fulfillment_source_semantic_text, fulfillment_candidate_fingerprint,
        fulfillment_components_fingerprint)
    from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
    from spg.providers.semantic_wire import _provider_strict_output_schema
    from spg.domain.model_runtime import ModelProfile, ModelPurpose, ModelProvider
    from spg.infrastructure.model_runtime import DeepSeekResponsesModelAdapter, httpx2

    basis = Path(args.basis)
    basis_bytes = basis.read_bytes()
    assert sha256(basis_bytes).hexdigest() == EXPECTED_BASIS_SHA
    data = json.loads(basis_bytes)
    diagnostic = json.loads(Path(args.diagnostic_receipt).read_bytes())
    assert diagnostic["basis_sha256"] == EXPECTED_BASIS_SHA
    assert diagnostic["inventory_fingerprint"] == EXPECTED_INVENTORY
    rows = data["datasets"]
    revision = WorkRealityRevision.model_validate(next(row for row in
        rows["work_reality_revisions"]["rows"] if row["id"] == REALITY_ID))
    assessment = next(row for row in rows["interaction_assessments"]["rows"]
                      if row["id"] == str(revision.source_assessment_id))
    ir = GovernedSemanticIR.model_validate(assessment["semantic_ir"])
    binding = data["actual_task_projections"][0]["fulfillment_bindings"][0]
    inventory = fulfillment_inventory(revision, ir, source_revision=binding["source_revision"],
                                     exact_target_paths=("index.html",))
    assert inventory["inventory_fingerprint"] == EXPECTED_INVENTORY
    capabilities = fulfillment_capability_contracts()
    assert sha256(json.dumps(capabilities, sort_keys=True).encode()).hexdigest() == diagnostic["capabilities_sha256"]
    assert [source["source_ref"] for source in inventory["sources"]] == diagnostic["source_refs"]
    profile_data = diagnostic["profile"]
    assert profile_data["provider"] == "deepseek"
    assert re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", profile_data["model"])
    profile = ModelProfile(purpose=ModelPurpose.STEERING_SEMANTIC, provider=ModelProvider.DEEPSEEK,
        model=profile_data["model"], reasoning_effort=profile_data["reasoning_effort"],
        timeout_seconds=profile_data["timeout_seconds"], max_output_tokens=profile_data["max_output_tokens"])
    instructions = instructions_for(ModelFulfillmentCandidateProvider, "form")
    input_text = json.dumps({"immutable_inventory": inventory,
        "existing_capability_contracts": capabilities, "same_basis_validation_feedback": None}, ensure_ascii=False)
    typed_schema = FulfillmentProjectionCandidate.model_json_schema()
    strict_schema = _provider_strict_output_schema(typed_schema)
    # Pure methods on an uninitialized adapter: __init__, Client and generate do not run.
    adapter = object.__new__(DeepSeekResponsesModelAdapter)
    payload = adapter._payload(profile=profile, instructions=instructions,
                              input_text=input_text, output_schema=strict_schema)
    body = httpx2.Request("POST", "https://offline.invalid/responses", json=payload).content

    sources, sizing_routes = [], []
    for source in inventory["sources"]:
        source_text = fulfillment_source_semantic_text(source)
        sources.append({"opaque_source_ref_sha256": opaque(source["source_ref"]), "kind": source["kind"],
            "source_json": json_metric(source), "semantic_text": metric(source_text),
            "field_values": {key: json_metric(value) for key, value in source.items()}})
        sizing_routes.append({"source_ref": source["source_ref"], "capability": "UNRESOLVED",
            "work_constraint_indices": [source["index"]] if source["kind"] == "WORK_CONSTRAINT" else [],
            "target_paths": [], "supporting_source_refs": [], "rationale": "Unresolved.",
            "component_basis": {"source_span_start": 0, "source_span_end": len(source_text),
                "source_component_quote": source_text, "linked_fact_refs": []}})
    candidate = FulfillmentProjectionCandidate.model_validate({
        "inventory_fingerprint": EXPECTED_INVENTORY, "routes": sizing_routes})
    full_candidate = candidate.model_dump(mode="json")
    span_only = deepcopy(full_candidate)
    for route in span_only["routes"]:
        route["component_basis"].pop("source_component_quote")
    recovered = deepcopy(span_only)
    by_ref = {source["source_ref"]: source for source in inventory["sources"]}
    for route in recovered["routes"]:
        component = route["component_basis"]
        text = fulfillment_source_semantic_text(by_ref[route["source_ref"]])
        component["source_component_quote"] = text[component["source_span_start"]:component["source_span_end"]]
    assert recovered == full_candidate
    capability_indices = {value["capability"]: index for index, value in enumerate(capabilities)}
    indexed = {"inventory_fingerprint": EXPECTED_INVENTORY, "routes": [
        {"source": index, "capability": capability_indices[route["capability"]],
         "span": [route["component_basis"]["source_span_start"], route["component_basis"]["source_span_end"]],
         "facts": [], "targets": [], "supports": [], "reason": route["rationale"]}
        for index, route in enumerate(full_candidate["routes"])]}
    counts = Counter(string_values(inventory))
    repeated = {value: count for value, count in counts.items() if count > 1}
    installed_paths = {"inventory_and_capabilities": inspect.getsourcefile(fulfillment_inventory),
        "formation_provider": inspect.getsourcefile(ModelFulfillmentCandidateProvider),
        "output_contract": inspect.getsourcefile(FulfillmentProjectionCandidate),
        "http_adapter": inspect.getsourcefile(DeepSeekResponsesModelAdapter),
        "strict_schema": inspect.getsourcefile(_provider_strict_output_schema)}
    result = {"schema": "c3-capacity-representation-measurement-v1", "started_at_utc": started,
        "scope": "OFFLINE_AGGREGATE_SIZING_ONLY", "basis_sha256": EXPECTED_BASIS_SHA,
        "inventory_fingerprint": EXPECTED_INVENTORY, "work_reality_revision_id": REALITY_ID,
        "work_id": str(revision.work_id), "source_revision": inventory["source_revision"],
        "expected_installed_application_source": args.application_source,
        "controller_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "installed_module_files": {key: {"path": path, "sha256": sha256(Path(path).read_bytes()).hexdigest()}
            for key, path in installed_paths.items()},
        "profile_from_existing_public_receipt": {key: profile_data[key] for key in
            ("provider", "model", "reasoning_effort", "timeout_seconds", "max_output_tokens")},
        "parts": {"inventory": json_metric(inventory), "capabilities": json_metric(capabilities),
            "instructions": metric(instructions), "actual_input_text": metric(input_text),
            "typed_schema": json_metric(typed_schema), "provider_strict_schema": json_metric(strict_schema),
            "actual_compact_strict_schema": json_metric(payload["text"]["format"]["schema"]),
            "actual_http_json_entity_body": metric(body)},
        "http_serialization": {"library": "installed httpx2.Request(json=payload)", "request_not_sent": True,
            "entity_body_only": True, "transport_headers_tls_framing_bytes": "UNKNOWN_NOT_MEASURED",
            "body_parse_roundtrip": json.loads(body) == payload},
        "inventory_top_level_field_metrics": {key: json_metric(value) for key, value in inventory.items()},
        "sources": sources, "source_count": len(sources), "source_kinds": dict(Counter(s["kind"] for s in inventory["sources"])),
        "capability_count": len(capabilities), "repetition": {"fixed_field_subtrees": repeated_fields(inventory),
            "method": "Raw string-value bytes and JSON subtree bytes are separate metrics; do not add them.",
            "string_occurrences": sum(counts.values()), "distinct_string_values": len(counts),
            "repeated_string_values": len(repeated),
            "raw_string_value_bytes": sum(len(value.encode()) * count for value, count in counts.items()),
            "distinct_raw_string_value_bytes": sum(len(value.encode()) for value in counts),
            "duplicate_raw_string_value_bytes": sum(len(value.encode()) * (count - 1) for value, count in repeated.items())},
        "output_schema_bounds": schema_bounds(payload["text"]["format"]["schema"]),
        "growth": {"schema_route_max_items": 1024, "schema_rationale_max_chars": 1000,
            "schema_component_quote_max_chars": 65536,
            "identity_validated_source_capability_pair_max_for_this_basis": min(1024, len(sources) * len(capabilities)),
            "universal_inventory_input_byte_upper_bound": "NOT_ESTABLISHED",
            "input_growth": "One repeated Item payload per surviving Clause-Item pair, plus current Facts and independent Work constraints/context.",
            "tokenizer_estimation": "NOT_PERFORMED_BYTES_ARE_NOT_TOKENS"},
        "representation_cost_experiments": {"semantic_status": "SYNTHETIC_ALL_UNRESOLVED_SIZING_NOT_A_LEGAL_BINDING_OR_CANDIDATE",
            "one_full_source_component_per_source_existing_wire": json_metric(full_candidate),
            "same_fields_quote_recovered_from_exact_original_span": {"metrics": json_metric(span_only), "exact_roundtrip": True,
                "current_wire_contract_support": False},
            "inventory_bound_source_capability_ordinals_and_spans": {"metrics": json_metric(indexed),
                "current_wire_contract_support": False, "source_order_map_sha256": opaque(json_text([s["source_ref"] for s in inventory["sources"]], compact=True)),
                "capability_order_map_sha256": opaque(json_text([c["capability"] for c in capabilities], compact=True))},
            "lossless_inventory_string_interning": interned_string_experiment(inventory)},
        "historical_capacity_boundary": {"observed_termination": diagnostic["provider_failure"]["provider_failure"]["termination_reason"],
            "historical_original_failure_cause": "UNKNOWN", "diagnostic_reasoning_tokens": None,
            "diagnostic_visible_json_tokens": None, "diagnostic_numeric_usage": "UNKNOWN",
            "max_output_tokens_is_not_a_proven_visible_json_budget": True,
            "offline_sizes_do_not_prove_provider_causal_exhaustion": True},
        "effects": {"model_requests": 0, "http_requests_sent": 0, "work_or_owner_writes": 0,
            "credentials_loaded": False, "prompt_or_human_text_exported": False,
            "holdout_read": False, "qualification_claim": False}}
    result.update(ended_at_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic() - clock)
    output = Path(args.output)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"scope": result["scope"], "source_count": result["source_count"],
        "inventory_fingerprint": EXPECTED_INVENTORY, "result_sha256": sha256(output.read_bytes()).hexdigest(),
        "model_requests": 0, "http_requests_sent": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-offline", action="store_true")
    parser.add_argument("--basis", default="/basis.json")
    parser.add_argument("--diagnostic-receipt", default="/diagnostic.json")
    parser.add_argument("--output", default="/c3-evidence/capacity-measurement.json")
    parser.add_argument("--application-source", default="e8e04b2")
    arguments = parser.parse_args()
    if not arguments.execute_offline:
        print(json.dumps({"plan_only": True, "model_requests": 0, "basis_sha256": EXPECTED_BASIS_SHA,
            "inventory_fingerprint": EXPECTED_INVENTORY, "requires_container_network": "none"}))
    else:
        try:
            main(arguments)
        except Exception as error:
            # No raw traceback, exception prose, prompt or snapshot values.
            print(json.dumps({"result": "OFFLINE_MEASUREMENT_FAILED", "error_type": type(error).__name__,
                "model_requests": 0, "http_requests_sent": 0}))
            raise SystemExit(1)
