"""Stage-appropriate admission and independent checks of the actual artifact."""
from copy import deepcopy
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.application.governed_obligations import (
    admitted_fulfillment_bindings, fulfillment_inventory,
    validate_fulfillment_projection,
)
from spg.application.production_brief import CONTRACT, production_brief_bindings
from spg.domain.engineering_semantics import SemanticRelation, SemanticEpistemicStatus, semantic_fact_reference
from spg.domain.governed_obligation import fulfillment_source_ref
from spg.domain.intent_realization import ProductionIntent, SemanticClause, SemanticItem, SemanticKind
from spg.domain.model_runtime import ModelUsage
from spg.domain.semantic_provenance import SemanticOrigin, SemanticProvenance
from spg.providers.managed_context_fulfillment import verify_binding_inventory, verify_fulfillment_fact_routes
from spg.providers.protected_context_verifier import StaticProtectedContextVerifier
from tests.test_fulfillment_projection import basis
from tests.test_governed_obligation_fulfillment import fact
from tests.test_static_protected_context_verifier import subject  # noqa: F401


def brief_case(scope="A local reading list", exclusion="Shared account administration", *, with_fact=True):
    revision, ir = basis(with_fact=with_fact)
    source = uuid4()
    text = f"Build {scope}. Leave {exclusion} outside this version."
    provenance = SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
        source_record_id=source, source_text=text)
    goal = ProductionIntent(objective=scope, primary_change=text, current=True, bounded_change=True,
        scope=(scope,), exclusions=(exclusion,))
    item = SemanticItem(item_id="normal-production", kind=SemanticKind.PRODUCTION_INTENT,
        statement=text, production=goal, provenance=(provenance,), confidence=1)
    clause = SemanticClause(clause_id="normal-request", source_record_id=source, source_text=text,
        semantic_item_ids=(item.item_id,), speech_act="EXPLICIT_REQUEST", polarity="AFFIRMATIVE",
        modality="REQUEST", temporal_scope="CURRENT")
    ir.items = (*ir.items, item)
    ir.clauses = (*ir.clauses, clause)
    ir.current_production = (goal,)
    revision.source_record_ids = (*revision.source_record_ids, source)
    revision.constraints = (*revision.constraints, scope, f"Excluded from this Work: {exclusion}")
    return revision, ir


def admit(revision, ir, targets=("index.html",)):
    class NoExtraInterpretation:
        def form(self, *args, **kwargs):
            raise AssertionError("A copied production brief must not require another model")
    return admitted_fulfillment_bindings(revision,
        SimpleNamespace(id=revision.source_assessment_id, semantic_ir=ir),
        provider=NoExtraInterpretation(), source_revision=revision.source_revision, exact_target_paths=targets)


@pytest.mark.parametrize("scope,exclusion", [
    ("A local reading list", "Shared account administration"),
    ("一页家庭支出记录", "银行账户同步与自动扣款"),
    ("A garden watering planner", "Remote valve control"),
])
def test_normal_requests_copy_full_sources_with_no_preproduction_model(scope, exclusion):
    revision, ir = brief_case(scope, exclusion)
    before = deepcopy(revision.engineering_semantic_facts)
    bindings = admit(revision, ir)
    receipt = bindings[0].formation_receipt
    assert receipt["source_role_contract"] == CONTRACT
    assert receipt["provider_call_count"] == 0
    assert receipt["evidence_status"] == "PENDING_ACTUAL_CANDIDATE_VERIFICATION"
    assert "semantic_review" not in receipt and "validation_passed" not in receipt
    assert revision.engineering_semantic_facts == before
    inv = fulfillment_inventory(revision, ir, exact_target_paths=("index.html",))
    assert {fulfillment_source_ref(b) for b in bindings} == {s["source_ref"] for s in inv["sources"]}
    exclusion_binding = next(b for b in bindings if b.source_quote == f"Excluded from this Work: {exclusion}")
    assert exclusion_binding.evidence_method == "EXACT_CANDIDATE_CONTENT"
    assert exclusion_binding.state == "BOUND_PENDING_EVIDENCE"
    assert exclusion_binding.component_basis.source_component_quote == exclusion_binding.source_quote
    assert any(b.component == "deploy" and b.evidence_method == "EXACT_PERMISSION_GATE"
               and b.phase.value == "CONTINUOUS_FROM_ADMISSION" for b in bindings)
    validate_fulfillment_projection(bindings, revision, ir,
        source_revision=revision.source_revision, exact_target_paths=("index.html",))


@pytest.mark.parametrize("change", ["drop", "duplicate", "source", "paths", "state", "support", "receipt", "quote"])
def test_pending_brief_is_recomputed_and_rejects_injected_or_lost_obligations(change):
    revision, ir = brief_case()
    bindings = list(admit(revision, ir))
    index = next(i for i, b in enumerate(bindings) if b.evidence_method == "EXACT_CANDIDATE_CONTENT")
    b = bindings[index]
    if change == "drop": bindings.pop()
    elif change == "duplicate": bindings.append(bindings[-1])
    elif change == "source": bindings[index] = b.model_copy(update={"source_revision": "0" * 40})
    elif change == "paths": bindings[index] = b.model_copy(update={"target_paths": ("secrets.txt",)})
    elif change == "state": bindings[index] = b.model_copy(update={"state": "RETAINED_CONTEXT"})
    elif change == "support": bindings[index] = b.model_copy(update={"supporting_source_refs": ("invented:origin",)})
    elif change == "quote": bindings[index] = b.model_copy(update={"source_quote": "The requirement was removed"})
    else: bindings[0] = bindings[0].model_copy(update={"formation_receipt": {
        **bindings[0].formation_receipt, "semantic_review": {"passed": True}}})
    with pytest.raises(ValueError):
        validate_fulfillment_projection(tuple(bindings), revision, ir,
            source_revision=revision.source_revision, exact_target_paths=("index.html",))


@pytest.mark.parametrize("change", ["human", "effect", "unresolved_fact", "unowned_constraint", "future"])
def test_authority_and_unsupported_sources_stay_with_existing_owner(change):
    revision, ir = brief_case()
    if change == "human": ir.items = (*ir.items[:-1], ir.items[-1].model_copy(update={"requires_human": True}))
    elif change == "effect": ir.clauses = (*ir.clauses[:-1], ir.clauses[-1].model_copy(update={"requested_effects": ("PROHIBIT_UNKNOWN_EFFECT",)}))
    elif change == "future": ir.clauses = (*ir.clauses[:-1], ir.clauses[-1].model_copy(update={"temporal_scope": "FUTURE"}))
    elif change == "unresolved_fact": revision.engineering_semantic_facts = (revision.engineering_semantic_facts[0].model_copy(update={"epistemic_status": SemanticEpistemicStatus.UNRESOLVED}),)
    else: revision.constraints = (*revision.constraints, "An invented requirement with no admitted origin")
    inv = fulfillment_inventory(revision, ir, exact_target_paths=("index.html",))
    assert production_brief_bindings(revision, ir, inv) is None


def test_missing_actual_content_consumer_is_not_a_promise_of_later_verification():
    revision, ir = brief_case()
    inv = fulfillment_inventory(revision, ir, exact_target_paths=("src/service.py",))
    assert production_brief_bindings(revision, ir, inv) is None


@pytest.mark.parametrize("early_bounded", [False, True])
def test_inspected_implementation_scope_does_not_require_wic_sizing_agreement(early_bounded):
    revision, ir = brief_case()
    item = ir.items[-1]
    goal = item.production.model_copy(update={"bounded_change": early_bounded})
    ir.items = (*ir.items[:-1], item.model_copy(update={"production": goal}))
    ir.current_production = (goal,)
    paths = ("index.html", "assets/styles.css", "assets/app.js")
    bindings = admit(revision, ir, targets=paths)
    assert bindings[0].formation_receipt["provider_call_count"] == 0
    assert all(b.target_paths == paths for b in bindings if b.evidence_method == "EXACT_CANDIDATE_CONTENT")
    assert all(b.state in {"BOUND_PENDING_EVIDENCE", "RETAINED_CONTEXT"} for b in bindings)
    assert {fulfillment_source_ref(b) for b in bindings} == {
        s["source_ref"] for s in fulfillment_inventory(revision, ir, exact_target_paths=paths)["sources"]}
    validate_fulfillment_projection(bindings, revision, ir,
        source_revision=revision.source_revision, exact_target_paths=paths)


@pytest.mark.parametrize("change", ["systemic_design", "unresolved_arguments"])
def test_inspected_files_do_not_resolve_design_or_missing_authority_arguments(change):
    revision, ir = brief_case()
    item = ir.items[-1]
    goal = item.production.model_copy(update={"bounded_change": False,
        change: True if change == "systemic_design" else ("objective",)})
    ir.items = (*ir.items[:-1], item.model_copy(update={"production": goal}))
    ir.current_production = (goal,)
    inv = fulfillment_inventory(revision, ir, exact_target_paths=("index.html",))
    assert production_brief_bindings(revision, ir, inv) is None


def test_mixed_production_clauses_keep_full_negative_business_requirements():
    revision, ir = brief_case()
    production = ir.clauses[-1]
    ir.clauses = (*ir.clauses[:-1], production.model_copy(update={"requested_effects": ("PRODUCTION_INTENT",)}),
        production.model_copy(update={"clause_id": "business-exclusion", "polarity": "NEGATED"}))
    bindings = admit(revision, ir)
    negatives = [b for b in bindings if b.constraint_clause_id == "business-exclusion"]
    assert len(negatives) == 1 and negatives[0].evidence_method == "EXACT_CANDIDATE_CONTENT"
    assert negatives[0].source_quote == production.source_text


@pytest.mark.parametrize("annotation", ["CONSTRAINT", "KEEP_OFFLINE_PRODUCT_BOUNDARY", "CHECK_FIRST_RELEASE_SCOPE"])
def test_current_constraint_kind_is_copied_without_an_extra_classification_review(annotation):
    revision, ir = brief_case()
    item = ir.items[-1]
    constraint = item.model_copy(update={"item_id": "negative-product-boundary", "kind": SemanticKind.CONSTRAINT,
        "production": None, "statement": "The first release excludes shared accounts"})
    ir.items = (*ir.items, constraint)
    clause = ir.clauses[-1].model_copy(update={"clause_id": "typed-constraint", "polarity": "NEGATED",
        "requested_effects": (annotation,), "semantic_item_ids": (constraint.item_id,)})
    ir.clauses = (*ir.clauses, clause)
    revision.constraints = (*revision.constraints, constraint.statement)
    bindings = admit(revision, ir)
    assert any(b.constraint_item_id == constraint.item_id and b.evidence_method == "EXACT_CANDIDATE_CONTENT"
        for b in bindings)


def model_verifier(disposition, calls):
    def generate(**kwargs):
        payload = json.loads(kwargs["input_text"])
        calls.append(payload)
        checks = [{"context_class": o["context_class"], "semantic_key": o["semantic_key"],
            "disposition": disposition, "reason": "Independent observed candidate judgement",
            "witnesses": [{"path": "index.html", "quote": "Company Home"}]}
            for o in payload["protected_obligations"]]
        return SimpleNamespace(output_text=json.dumps({"checks": checks}), provider=SimpleNamespace(value="fixture"),
            effective_model="fixture", request_id="controlled-independent-check", usage=ModelUsage())
    return StaticProtectedContextVerifier(lambda: SimpleNamespace(generate=generate,
        registry=SimpleNamespace(close=lambda: None)))


@pytest.mark.parametrize("disposition,passed", [("SATISFIED", True), ("CONTRADICTED", False), ("UNVERIFIABLE", False)])
def test_exclusion_needs_actual_candidate_verification(subject, disposition, passed):
    repo, baseline, request, task, contract = subject
    revision, ir = brief_case(with_fact=False)
    revision.source_revision = baseline
    bindings = admit(revision, ir)
    exclusion = next(b for b in bindings if b.source_quote.startswith("Excluded from this Work:"))
    calls = []
    result, evidence = verify_binding_inventory(request=request, task=task, contract=contract,
        repository=repo, baseline=baseline, revision=revision, ir=ir, bindings=(exclusion,),
        semantic_checks=(), protected_checks=(), static_verifier=model_verifier(disposition, calls),
        receipt_recorder=None, native_record=None)
    assert len(calls) == 1
    assert result[0]["current_stage_satisfied"] is passed
    assert evidence[0]["coverage"] == ("COVERED" if passed else "UNVERIFIED")
    assert exclusion.source_quote in calls[0]["protected_obligations"][0]["content"]
    assert calls[0]["exact_candidate_revision"] == request.proposed_commit_identity


def test_unstructured_scope_uses_real_content_consumer_without_fabricated_review(subject):
    repo, baseline, request, task, contract = subject
    revision, ir = brief_case(with_fact=False)
    scope = fact("unlisted.display.requirement", SemanticRelation.SCOPE, "Company Home",
        "Show Company Home as the first version.", qualifiers={"purpose": "displayed heading"})
    revision.engineering_semantic_facts = (scope,)
    revision.source_record_ids = (*revision.source_record_ids, *scope.provenance.source_record_ids)
    revision.source_revision = baseline
    bindings = admit(revision, ir)
    references = (semantic_fact_reference(scope, work_revision_id=revision.id),)
    request = request.model_copy(update={"semantic_fact_obligations": references})
    contract.source_revision = baseline
    calls = []
    result = verify_fulfillment_fact_routes(repository=repo, request=request, contract=contract,
        references=references, admitted_facts={str(scope.id): scope}, revision=revision, ir=ir, baseline=baseline,
        bindings=bindings, plan_repair=None, static_verifier=model_verifier("SATISFIED", calls),
        task=task)
    assert calls and result[0]["passed"] is True
    assert result[0]["current_evidence_verified"] is True
