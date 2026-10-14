"""Read-only source/method/coverage observations on the unchanged live output."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import unicodedata

from spg.application import governed_obligations as owner
from spg.domain.governed_obligation import fulfillment_source_semantic_text
from spg.domain.interaction import WorkRealityRevision
from spg.domain.intent_realization import GovernedSemanticIR
from spg.providers import fulfillment_candidate as wire

private, evidence = Path("/private"), Path("/evidence")
inventory = json.loads(Path("/inventory/immutable-inventory.json").read_text())
preconditions = json.loads(private.joinpath("prepared-preconditions.json").read_text())
feedback = private.joinpath("prepared-feedback.json").read_text()
response = json.loads(private.joinpath("response-observation.json").read_text())
raw = response["candidate_output"]
observed, unavailable = wire._fulfillment_wire_route_observations(raw, inventory,
    owner.fulfillment_capability_contracts(), validation_feedback=feedback, owner_preconditions=preconditions)
details = []
for index, source in enumerate(inventory["sources"]):
    selected = [(ordinal, route) for ordinal, _, route in observed if route.source_ref == source["source_ref"]]
    text = fulfillment_source_semantic_text(source)
    covered = {offset for _, route in selected for offset in range(
        route.component_basis.source_span_start, route.component_basis.source_span_end)}
    missing = [offset for offset, char in enumerate(text) if not char.isspace() and offset not in covered]
    details.append({"source_ordinal": index, "source_kind": source["kind"],
        "proposed_consumers": [route.capability for _, route in selected],
        "uncovered_nonwhitespace_codepoints": len(missing),
        "missing_unicode_categories": dict(Counter(unicodedata.category(text[i]) for i in missing))})
edits = json.loads(raw)
original = preconditions["candidate_construction_state"]["repair_basis"]["original_wire"]["routes"]
replacements = {row["index"]: row["route"] for row in edits["replace"]}
data = json.loads(Path("/inventory/basis.json").read_text())["datasets"]
revision = WorkRealityRevision.model_validate(next(row for row in data["work_reality_revisions"]["rows"]
    if row["id"] == inventory["work_reality_revision_id"]))
ir = GovernedSemanticIR.model_validate(next(row for row in data["interaction_assessments"]["rows"]
    if row["id"] == str(revision.source_assessment_id))["semantic_ir"])
context = owner._owner_repair_context(raw, revision, ir, inventory, owner.fulfillment_capability_contracts(),
    validation_feedback=feedback, owner_preconditions=preconditions)
report = {"scope": "UNADMITTED_COMPLETE_OUTPUT_OBSERVATION; NO_PARTIAL_CANDIDATE_ADMISSION_OR_REVIEW",
    "response_sha256": sha256(raw.encode()).hexdigest(),
    "observation_unavailable": unavailable, "observed_route_count": len(observed),
    "sources": details,
    "replacement_sources_unchanged": all(original[i]["source_ref"] == route["source_ref"] for i, route in replacements.items()),
    "replacement_targets_within_original_allowlist": all(set(route["target_paths"]).issubset(inventory["exact_target_paths"]) for route in replacements.values()),
    "replacement_rationale_sha256": {str(i): sha256(route["rationale"].encode()).hexdigest() for i, route in replacements.items()},
    "owner_context_violations": [{key: row[key] for key in ("code", "source", "route", "component_id") if key in row}
        for row in context["violations"]],
    "owner_context_additional_violation_count": context["additional_violation_count"],
    "note": "Empty prerequisite errors do not prove semantic equivalence, fulfilled evidence, or full-plan validity."}
evidence.joinpath("source-coverage-observations.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
