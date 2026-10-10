"""Conditional semantic review is not background admission or fulfillment."""
from copy import deepcopy
import json
import pytest
from spg.application import governed_obligations as a
from spg.domain.governed_obligation import fulfillment_source_semantic_text
from spg.domain.semantic_provenance import SemanticProvenance, SemanticOrigin
from spg.domain.interaction_actions import ActionSpeechAct
from tests.test_c3_source_role_contract import shared_item_case
from tests.test_c3_semantic_contract_calibration import review


def nominal_case():
    revision, ir, _, plan = shared_item_case("Ordinary isolated production qualification.")
    background = next(c for c in ir.clauses if c.clause_id == "description")
    background = background.model_copy(update={"modality": "REQUEST",
        "speech_act": ActionSpeechAct.EXPLICIT_REQUEST, "requested_effects": ()})
    ir.clauses = tuple(background if c.clause_id == background.clause_id else c for c in ir.clauses)
    original = revision.engineering_semantic_facts[0]
    provenance = original.provenance.model_copy(update={"source_text": "Caption must retain its exact value.",
        "governed_provenance": (SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
            source_record_id=original.provenance.source_record_ids[0], source_text=background.source_text),)})
    revision.engineering_semantic_facts = (original.model_copy(update={"provenance": provenance}),)
    inventory = a.fulfillment_inventory(revision, ir)
    by_ref = {s["source_ref"]: s for s in inventory["sources"]}
    routes = tuple(r.model_copy(update={"component_basis": r.component_basis.model_copy(update={
        "source_span_end": len(fulfillment_source_semantic_text(by_ref[r.source_ref])),
        "source_component_quote": fulfillment_source_semantic_text(by_ref[r.source_ref])})}) for r in plan.routes)
    plan = plan.model_copy(update={"inventory_fingerprint": inventory["inventory_fingerprint"], "routes": routes})
    owner = a._owner_source_preconditions(revision, ir, inventory, a.fulfillment_capability_contracts(),
        source_context_contract=a._PRIMARY_CONTEXT_CONTRACT)
    return revision, ir, inventory, plan, owner


def test_shared_provenance_empty_effect_is_only_versioned_review_eligibility():
    revision, ir, inventory, plan, owner = nominal_case()
    before = deepcopy((revision.engineering_semantic_facts, ir.clauses, plan))
    index = next(i for i,s in enumerate(inventory["sources"]) if s.get("clause_id") == "description")
    old = a._owner_source_preconditions(revision, ir, inventory, a.fulfillment_capability_contracts())
    assert not old["sources"][index]["reviewed_background_prerequisites"]["conditional_source_eligible"]
    assert owner["sources"][index]["reviewed_background_prerequisites"]["conditional_source_eligible"]
    with pytest.raises(ValueError, match="CURRENT_CLAUSE_CANNOT_BE_CONTEXT_ONLY"):
        a.validate_projection_candidate(plan, revision, ir, inventory, allow_review_pending=True)
    pending = a.validate_projection_candidate(plan, revision, ir, inventory, source_contract="v3",
        owner_preconditions=owner, allow_review_pending=True)
    assert all(b.state != "SATISFIED" for b in pending)
    with pytest.raises(ValueError, match="REVIEW_REQUIRED"):
        a.validate_projection_candidate(plan, revision, ir, inventory, source_contract="v3", owner_preconditions=owner)
    result = a.validate_projection_candidate(plan, revision, ir, inventory, source_contract="v3",
        owner_preconditions=owner, semantic_review=review(inventory, plan))
    assert any(b.state == "RETAINED_CONTEXT" for b in result)
    assert before == (revision.engineering_semantic_facts, ir.clauses, plan)
    feedback = json.loads(a.projection_validation_feedback(plan, revision, ir, inventory, "OBLIGATION_REVIEW_REQUIRED",
        source_contract="v3", owner_preconditions=owner))
    assert not any(v["code"] == "OBLIGATION_CURRENT_CLAUSE_CANNOT_BE_CONTEXT_ONLY" for v in feedback["violations"])


@pytest.mark.parametrize("change", ("negative", "effect", "human", "action", "primary-fact", "missing-fact", "missing-sibling"))
def test_new_background_path_never_erases_authority_or_required_consumers(change):
    revision, ir, inventory, plan, owner = nominal_case()
    item, clause = ir.items[0], next(c for c in ir.clauses if c.clause_id == "description")
    if change == "negative": clause = clause.model_copy(update={"polarity": "NEGATED"})
    if change == "effect": clause = clause.model_copy(update={"requested_effects": ("PROHIBIT_DEPLOY",)})
    if change == "human": item = item.model_copy(update={"requires_human": True})
    if change == "action": item = item.model_copy(update={"action": object()})
    if change == "primary-fact":
        fact = revision.engineering_semantic_facts[0]
        revision.engineering_semantic_facts = (fact.model_copy(update={"provenance": fact.provenance.model_copy(
            update={"source_text": clause.source_text})}),)
    if change in {"negative", "effect", "human", "action", "primary-fact"}:
        assert not a._reviewed_background_clause_eligible(revision, item, clause, source_contract="v3",
            context_contract=a._PRIMARY_CONTEXT_CONTRACT)
    else:
        routes = tuple(r.model_copy(update={"capability": "UNRESOLVED", "target_paths": ()})
            if (change == "missing-fact" and r.source_ref.startswith("semantic-fact:") or
                change == "missing-sibling" and r.source_ref.endswith(":current-artifact")) else r for r in plan.routes)
        changed = plan.model_copy(update={"routes": routes})
        assert not a._reviewed_background_context_refs(changed, revision, ir, inventory, source_contract="v3",
            context_contract=a._PRIMARY_CONTEXT_CONTRACT)


def test_independent_semantic_rejection_is_not_overridden_by_eligibility():
    revision, ir, inventory, plan, owner = nominal_case()
    verdict = review(inventory, plan)
    rejected = verdict.model_copy(update={"source_results": tuple(r.model_copy(update={
        "complete_and_equivalent": False}) for r in verdict.source_results)})
    with pytest.raises(ValueError):
        a.validate_projection_candidate(plan, revision, ir, inventory, semantic_review=rejected,
            source_contract="v3", owner_preconditions=owner)


@pytest.mark.parametrize("tamper", (None, "review-missing", "component-missing", "component-false", "review-identity", "wire", "marker"))
def test_actual_consumer_rechecks_complete_bound_background_plan(tamper):
    from tests.test_c3_fulfillment_capacity_representation import controlled_model_provider
    revision, ir, inventory, plan, _ = nominal_case()
    provider, calls = controlled_model_provider(inventory, plan)
    bindings = a.form_fulfillment_projection(revision, ir, provider=provider,
        source_revision=inventory["source_revision"], exact_target_paths=inventory["exact_target_paths"])
    assert all(b.state != "UNRESOLVED" for b in bindings) and len(calls) == 2
    before = deepcopy((revision.engineering_semantic_facts, ir.clauses))
    receipt = deepcopy(bindings[0].formation_receipt)
    if tamper == "review-missing": receipt["semantic_review"] = None
    if tamper == "component-missing": receipt["semantic_review"]["component_results"].pop()
    if tamper == "component-false": receipt["semantic_review"]["component_results"][0]["complete_and_equivalent"] = False
    if tamper == "review-identity": receipt["semantic_review"]["candidate_fingerprint"] = "0" * 64
    if tamper == "wire":
        row = next(r for r in receipt["candidate_attempts"] if r["stage"] == "MODEL_RESPONSE_OBSERVED")
        row["candidate_output"] += " "
    if tamper == "marker":
        for row in receipt["candidate_attempts"]:
            if row["stage"] in {"MODEL_REQUEST_PENDING", "MODEL_RESPONSE_OBSERVED"}:
                row["owner_source_preconditions"].pop("source_context_contract")
    changed = (bindings[0].model_copy(update={"formation_receipt": receipt}), *bindings[1:])
    if tamper is None:
        a.validate_fulfillment_projection(changed, revision, ir, exact_target_paths=inventory["exact_target_paths"])
        assert a._reviewed_background_clause_retained(revision, ir, ir.items[0].item_id, "description", changed)
    else:
        with pytest.raises(ValueError):
            a.validate_fulfillment_projection(changed, revision, ir, exact_target_paths=inventory["exact_target_paths"])
    assert before == (revision.engineering_semantic_facts, ir.clauses) and len(calls) == 2
