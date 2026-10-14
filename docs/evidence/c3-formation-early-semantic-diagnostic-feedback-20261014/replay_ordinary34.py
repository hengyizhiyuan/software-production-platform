"""Read-only ordinary34 diagnostic replay; writes no private model or Human text."""

import json
import sys
from hashlib import sha256

from spg.application.governed_obligations import (
    _consumer_mapping_diagnostics,
    fulfillment_capability_contracts,
)
from spg.domain.governed_obligation import FulfillmentProjectionCandidate
from spg.providers.fulfillment_candidate import _fulfillment_wire_route_observations


def main(receipts_path, inventory_path):
    with open(receipts_path, encoding="utf-8") as stream:
        rows = json.load(stream)
    with open(inventory_path, encoding="utf-8") as stream:
        inventory = json.load(stream)
    request = next(row for row in rows if row["stage"] == "MODEL_REQUEST_PENDING" and row["attempt"] == 1)
    response = next(row for row in rows if row["stage"] == "MODEL_RESPONSE_OBSERVED" and row["attempt"] == 1)
    validation = next(row for row in rows if row["stage"] == "CANDIDATE_VALIDATED" and row["attempt"] == 1)
    raw = response["candidate_output"]
    capabilities = fulfillment_capability_contracts()
    observations, unavailable = _fulfillment_wire_route_observations(
        raw, inventory, capabilities, validation_feedback=request.get("feedback"),
        owner_preconditions=request["owner_source_preconditions"])
    if unavailable:
        raise RuntimeError(f"Original Wire cannot be completely located: {unavailable}")
    candidate = FulfillmentProjectionCandidate(
        inventory_fingerprint=inventory["inventory_fingerprint"],
        routes=tuple(route for _, _, route in observations))
    diagnostic = _consumer_mapping_diagnostics(candidate, inventory, capabilities)
    feedback = json.loads(validation["validation_feedback"])
    if "consumer_mapping_diagnostics" in feedback["owner_repair_context"]:
        raise RuntimeError("Historical receipt unexpectedly contains this new diagnostic")
    original_serialized = json.dumps(feedback, separators=(",", ":")).encode()
    feedback["owner_repair_context"]["consumer_mapping_diagnostics"] = diagnostic
    updated_serialized = json.dumps(feedback, separators=(",", ":")).encode()
    print(json.dumps({
        "replay_kind": "READ_ONLY_HISTORICAL_FIRST_CANDIDATE; NOT_A_MODEL_RETRY_OR_REVIEW",
        "original_wire_sha256": sha256(raw.encode()).hexdigest(),
        "inventory_fingerprint": inventory["inventory_fingerprint"],
        "wire_route_count": len(observations),
        "candidate_fingerprint": diagnostic["candidate_fingerprint"],
        "diagnostic_route_ordinals": [item["route"] for item in diagnostic["observations"]],
        "diagnostic_source_ordinals": [item["source"] for item in diagnostic["observations"]],
        "diagnostic_status": diagnostic["status"],
        "existing_feedback_stored_bytes": len(validation["validation_feedback"].encode()),
        "existing_feedback_reserialized_bytes": len(original_serialized),
        "updated_feedback_bytes": len(updated_serialized),
        "updated_feedback_sha256": sha256(updated_serialized).hexdigest(),
        "historical_validation_result": validation["failed_predicate"],
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
