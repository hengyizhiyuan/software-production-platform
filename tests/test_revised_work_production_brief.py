"""A governed Work revision owns retained requirements even when current IR is a delta."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
from uuid import uuid4

import pytest

from spg.application.production_brief import production_brief_bindings, REVISED_WORK_CONTRACT, CONTINUITY_CONTRACT
from spg.application.governed_obligations import fulfillment_inventory, validate_fulfillment_projection
from spg.domain.intent_realization import GovernedSemanticIR
from spg.domain.interaction import WorkRealityRevision
from tests.test_production_brief_admission import brief_case, admit


@pytest.mark.parametrize("retained", ["保持单页离线使用与原有配色", "Retain the existing keyboard navigation", "保留本地音乐及原有栏目"])
def test_full_admitted_constraint_is_pending_actual_content_without_reinterpretation(retained):
    revision, ir = brief_case()
    revision.revision_number = 2
    revision.previous_revision_id = uuid4()
    revision.constraints = (*revision.constraints, retained)
    before = deepcopy((vars(revision), vars(ir)))
    inventory = fulfillment_inventory(revision, ir, exact_target_paths=("index.html",))
    assert production_brief_bindings(revision, ir, inventory, contract=CONTINUITY_CONTRACT) is None
    bindings = admit(revision, ir)
    assert bindings[0].formation_receipt["source_role_contract"] == REVISED_WORK_CONTRACT
    binding = next(b for b in bindings if b.source_quote == retained)
    assert binding.evidence_method == "EXACT_CANDIDATE_CONTENT"
    assert binding.state == "BOUND_PENDING_EVIDENCE"
    assert binding.phase.value == "CURRENT_VERIFICATION"
    assert binding.component_basis.source_component_quote == retained
    assert before == (vars(revision), vars(ir))
    validate_fulfillment_projection(bindings, revision, ir,
        source_revision=revision.source_revision, exact_target_paths=("index.html",))
    changed = list(bindings)
    at = bindings.index(binding)
    changed[at] = binding.model_copy(update={"source_quote": retained + " rewritten"})
    with pytest.raises(ValueError):
        validate_fulfillment_projection(tuple(changed), revision, ir,
            source_revision=revision.source_revision, exact_target_paths=("index.html",))


@pytest.mark.parametrize("change", ["initial-revision", "no-parent", "unknown-effect"])
def test_revised_brief_cannot_turn_unknown_effects_or_unadmitted_continuity_into_content(change):
    revision, ir = brief_case()
    revision.revision_number = 2
    revision.previous_revision_id = uuid4()
    revision.constraints = (*revision.constraints, "A retained admitted content requirement")
    if change == "initial-revision": revision.revision_number = 1
    elif change == "no-parent": revision.previous_revision_id = None
    else:
        ir.clauses = (*ir.clauses[:-1], ir.clauses[-1].model_copy(update={
            "requested_effects": ("PROHIBIT_UNQUALIFIED_EFFECT",)}))
    inventory = fulfillment_inventory(revision, ir, exact_target_paths=("index.html",))
    assert production_brief_bindings(revision, ir, inventory, contract=REVISED_WORK_CONTRACT) is None


def test_real_revised_work_keeps_all_sources_with_no_formation_model_call():
    data = json.loads(gzip.decompress((Path(__file__).parent / "fixtures" /
        "revised-work-brief-source-20261017.json.gz").read_bytes()))
    revision = WorkRealityRevision.model_validate(data["revision"])
    ir = GovernedSemanticIR.model_validate(data["ir"])
    before = (revision.model_dump(mode="json"), ir.model_dump(mode="json"))
    inventory = fulfillment_inventory(revision, ir, source_revision=revision.source_revision,
        exact_target_paths=tuple(data["paths"]))
    assert production_brief_bindings(revision, ir, inventory, contract=CONTINUITY_CONTRACT) is None
    bindings = production_brief_bindings(revision, ir, inventory)
    assert bindings is not None
    assert bindings[0].formation_receipt["provider_call_count"] == 0
    assert bindings[0].formation_receipt["evidence_status"] == "PENDING_ACTUAL_CANDIDATE_VERIFICATION"
    assert bindings[0].formation_receipt["source_role_contract"] == REVISED_WORK_CONTRACT
    assert {b.source_quote for b in bindings if b.source_kind.value == "WORK_CONSTRAINT"} == set(revision.constraints)
    validate_fulfillment_projection(bindings, revision, ir,
        source_revision=revision.source_revision, exact_target_paths=tuple(data["paths"]))
    assert before == (revision.model_dump(mode="json"), ir.model_dump(mode="json"))
