"""Sanitize a retained repair proposal without exposing original source text."""

import json
import re
from pathlib import Path

from spg.application.governed_obligations import fulfillment_capability_contracts
from spg.providers.fulfillment_candidate import _decode_fulfillment_candidate_wire


rows = json.loads(Path("/historical/ordinary34-owner-receipts.json").read_text())
inventory = json.loads(Path("/inventory/immutable-inventory.json").read_text())
output = json.loads(Path("/private/response-observation.json").read_text())
raw = output["candidate_output"]
edits = json.loads(raw)
feedback = Path("/private/bound-feedback.json").read_text()
status = "DECODED"
failure_predicates = []
try:
    _decode_fulfillment_candidate_wire(raw, inventory, fulfillment_capability_contracts(),
        validation_feedback=feedback,
        wire_metadata={k: output[k] for k in (
            "provider_wire_version", "wire_request_fingerprint", "wire_table_fingerprint",
            "wire_schema_fingerprint")},
        owner_preconditions=rows[3]["owner_source_preconditions"])
except Exception as error:
    status = type(error).__name__
    codes = re.findall(r"OBLIGATION_[A-Z_]+", str(error))
    if codes:
        status += ":" + codes[0]
    diagnostics = getattr(error, "diagnostics", {})
    if isinstance(diagnostics, dict):
        failure_predicates = [{key: row[key] for key in ("code", "route", "source", "component_id") if key in row}
            for row in diagnostics.get("violations", [])]
report = {
    "decode_status": status,
    "failure_predicates": failure_predicates,
    "replacement_ordinals": [row["index"] for row in edits.get("replace", [])],
    "removed_ordinals": edits.get("remove", []),
    "appended_count": len(edits.get("append", [])),
    "appended_capabilities": [row.get("capability") for row in edits.get("append", [])],
    "risky_route_1_replaced": 1 in [row["index"] for row in edits.get("replace", [])],
    "risky_route_3_replaced": 3 in [row["index"] for row in edits.get("replace", [])],
    "risky_routes_removed": 1 in edits.get("remove", []) or 3 in edits.get("remove", []),
}
print(json.dumps(report, sort_keys=True))
