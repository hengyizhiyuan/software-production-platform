"""Read-only attribution of the actual probe stop, without another model call."""
import json
from pathlib import Path
import re

from spg.application.governed_obligations import fulfillment_capability_contracts
from spg.providers.fulfillment_candidate import (
    candidate_construction_preconditions, _decode_fulfillment_candidate_wire,
)

private = Path("/private")
feedback = private.joinpath("prepared-feedback.json").read_text()
actual_preconditions = json.loads(private.joinpath("prepared-preconditions.json").read_text())
inventory = json.loads(Path("/inventory/immutable-inventory.json").read_text())
response = json.loads(private.joinpath("response-observation.json").read_text())
historical = json.loads(Path("/historical/ordinary34-owner-receipts.json").read_text())
output = response["candidate_output"]
base = {k: v for k, v in actual_preconditions.items()
    if k not in {"candidate_construction_contract", "candidate_construction_state"}}
rebuilt = candidate_construction_preconditions(base, inventory, feedback,
    construction_contract=actual_preconditions["candidate_construction_contract"])
old_state = actual_preconditions["candidate_construction_state"]
new_state = rebuilt["candidate_construction_state"]
changed = [key for key in old_state if old_state[key] != new_state[key]]
report = {
    "actual_stop_owner": "WATT_CANDIDATE_CONSTRUCTION_PRECONDITION_RECONSTRUCTION",
    "actual_failed_comparison": "candidate_construction_preconditions(base,inventory,feedback) != supplied_preconditions",
    "changed_state_fields": changed,
    "supplied_target_count": len(old_state["repair_targets"]),
    "owner_rebuilt_target_count": len(new_state["repair_targets"]),
    "model_response_basis_matches_original": json.loads(output)["basis"] == new_state["repair_basis"]["raw_sha256"],
    "feedback_only_extension_matches_original_owner_projection": rebuilt == historical[3]["owner_source_preconditions"],
    "attribution": "REQUEST_ONLY_PROTOTYPE_WIRING_DEFECT; NOT_MODEL_BASIS_DRIFT_OR_VALIDATOR_FALSE_REJECTION",
    "counterfactual_scope": "EXACT_SAVED_MODEL_OUTPUT_WITH_OWNER_REBUILT_PRECONDITIONS; DIFFERENT_REQUEST_CONTEXT; NOT_QUALIFIED_CANDIDATE",
}
# This is diagnostic attribution only. It does not modify the actual trial or
# replace its terminal result. The output bytes remain completely unchanged.
try:
    _decode_fulfillment_candidate_wire(output, inventory, fulfillment_capability_contracts(),
        validation_feedback=feedback, owner_preconditions=rebuilt)
except Exception as error:
    codes = re.findall(r"OBLIGATION_[A-Z_]+", str(error))
    report["counterfactual_decode_result"] = {"type": type(error).__name__, "code": codes[0] if codes else "UNKNOWN"}
    details = getattr(error, "diagnostics", {})
    if isinstance(details, dict):
        report["counterfactual_failed_predicates"] = [{key: row[key] for key in ("code", "source", "route") if key in row}
            for row in details.get("violations", [])]
else:
    report["counterfactual_decode_result"] = "DECODED_ONLY; NO_ADMISSION_OR_REVIEW"
Path("/evidence/boundary-attribution.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
