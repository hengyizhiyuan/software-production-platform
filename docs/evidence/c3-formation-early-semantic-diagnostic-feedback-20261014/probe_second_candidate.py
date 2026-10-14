"""One isolated ordinary34 Formation repair call; no Work or database access.

The full response stays under /private on the isolated ECS. Standard output
contains only identity, usage and route disposition metadata.
"""

import json
import os
from hashlib import sha256
from pathlib import Path

from spg.application.governed_obligations import _consumer_mapping_diagnostics, fulfillment_capability_contracts
from spg.domain.governed_obligation import FulfillmentProjectionCandidate
from spg.domain.model_runtime import (
    ModelProfile, ModelProvider, ModelPurpose, ModelProviderRegistry,
    PurposeProfileRouter, WattModelRuntime,
)
from spg.infrastructure.model_runtime import DeepSeekResponsesModelAdapter
from spg.providers.fulfillment_candidate import (
    ModelFulfillmentCandidateProvider, _fulfillment_wire_route_observations,
)


def main():
    rows = json.loads(Path("/historical/ordinary34-owner-receipts.json").read_text())
    inventory = json.loads(Path("/inventory/immutable-inventory.json").read_text())
    capabilities = fulfillment_capability_contracts()
    first_request, first_response, first_validation, second_request = rows[:4]
    observed, unavailable = _fulfillment_wire_route_observations(
        first_response["candidate_output"], inventory, capabilities,
        validation_feedback=first_request.get("feedback"),
        owner_preconditions=first_request["owner_source_preconditions"])
    if unavailable:
        raise RuntimeError("Original first Wire is not completely evaluable")
    original = FulfillmentProjectionCandidate(
        inventory_fingerprint=inventory["inventory_fingerprint"],
        routes=tuple(route for _, _, route in observed))
    diagnostic = _consumer_mapping_diagnostics(original, inventory, capabilities)
    feedback = json.loads(first_validation["validation_feedback"])
    feedback["owner_repair_context"]["consumer_mapping_diagnostics"] = diagnostic
    bound_feedback = json.dumps(feedback, separators=(",", ":"))
    private = Path("/private")
    if private.joinpath("response-observation.json").exists() or private.joinpath("call-started").exists():
        raise RuntimeError("One-shot probe already started; do not repeat")
    private.joinpath("bound-feedback.json").write_text(bound_feedback)

    def runtime():
        registry = ModelProviderRegistry()
        registry.register(DeepSeekResponsesModelAdapter(
            api_key=lambda: os.environ["SPG_DEEPSEEK_API_KEY"],
            base_url=os.environ["SPG_DEEPSEEK_BASE_URL"]))
        profile = ModelProfile(
            purpose=ModelPurpose.STEERING_SEMANTIC,
            provider=ModelProvider.DEEPSEEK,
            model="deepseek-flash", reasoning_effort="none",
            timeout_seconds=120, max_output_tokens=16384)
        return WattModelRuntime(registry, PurposeProfileRouter({ModelPurpose.STEERING_SEMANTIC: profile}))

    provider = ModelFulfillmentCandidateProvider(
        runtime, candidate_construction=True,
        candidate_construction_contract="owner-local-interpretation-role-construction-v4",
        raw_role_repair=True, construction_consumer_instructions=True,
        unparsed_claim_repair=True, role_convergence=True)
    observed_output = {}

    def receipt_callback(**values):
        observed_output.update(values)
        private.joinpath("response-observation.json").write_text(json.dumps(values, ensure_ascii=False, indent=2))

    result, failure_type = None, None
    private.joinpath("call-started").touch(exist_ok=False)
    try:
        result = provider.form(inventory, capabilities, validation_feedback=bound_feedback,
            owner_preconditions=second_request["owner_source_preconditions"],
            receipt_callback=receipt_callback)
    except Exception as error:
        failure_type = type(error).__name__

    risk_refs = {inventory["sources"][item["source"]]["source_ref"]
        for item in diagnostic["observations"]}
    original_risk = sum(route.source_ref in risk_refs and route.capability == "GIT_DIFF_SCOPE"
        for route in original.routes)
    new_risk = (sum(route.source_ref in risk_refs and route.capability == "GIT_DIFF_SCOPE"
        for route in result.routes) if result is not None else None)
    original_content = sum(route.source_ref in risk_refs and route.capability == "ARTIFACT_CONTENT"
        for route in original.routes)
    new_content = (sum(route.source_ref in risk_refs and route.capability == "ARTIFACT_CONTENT"
        for route in result.routes) if result is not None else None)
    telemetry = provider.last_observation or {}
    report = {
        "schema": "c3-ordinary34-isolated-second-candidate-probe-v1",
        "historical_work_modified": False, "new_work_created": False,
        "provider_logical_call_limit": 1, "model": "deepseek-flash",
        "reasoning_effort": "none", "max_output_tokens": 16384,
        "timeout_seconds": 120,
        "inventory_fingerprint": inventory["inventory_fingerprint"],
        "original_wire_sha256": first_response["candidate_output_sha256"],
        "bound_feedback_sha256": sha256(bound_feedback.encode()).hexdigest(),
        "diagnostic_original_route_ordinals": [item["route"] for item in diagnostic["observations"]],
        "original_risky_diff_routes": original_risk,
        "result_risky_diff_routes": new_risk,
        "original_content_routes_same_sources": original_content,
        "result_content_routes_same_sources": new_content,
        "decoded_second_candidate": result is not None,
        "failure_type": failure_type,
        "response_output_sha256": observed_output.get("candidate_output_sha256"),
        "response_bytes": observed_output.get("candidate_output_bytes"),
        "provider_usage": telemetry.get("usage"),
        "provider_timing": telemetry.get("timing"),
        "transport_retry_count": telemetry.get("transport_retry_count"),
        "request_id": telemetry.get("request_id"),
    }
    private.joinpath("sanitized-result.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
