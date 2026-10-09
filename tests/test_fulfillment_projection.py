"""C3 exact source/phase contracts and bounded candidate replay, no live model."""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import asdict
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.application.governed_obligations import (
    FulfillmentFormationReceipts, admitted_fulfillment_bindings,
    deterministic_fulfillment_projection, evaluate_candidate_handoffs,
    form_fulfillment_projection, fulfillment_inventory, validate_fulfillment_projection,
    validate_projection_candidate)
from spg.domain.engineering_semantics import SemanticRelation, semantic_fact_reference
from spg.domain.governed_obligation import (
    FulfillmentProjectionCandidate, FulfillmentRouteCandidate, FulfillmentSourceKind,
    fulfillment_source_ref)
from spg.domain.intent_realization import ProductionIntent, SemanticClause, SemanticItem, SemanticKind
from spg.domain.semantic_provenance import SemanticOrigin, SemanticProvenance, SemanticArgument
from spg.domain.model_runtime import StructuredModelResult, ModelProvider, ModelUsage, ModelTiming
from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
from tests.test_governed_obligation_fulfillment import fact


def basis(*, with_fact=True, future=False, observed=False):
    source = uuid4()
    quote = "The external release must remain forbidden."
    statement = "External release forbidden"
    provenance = SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
        source_record_id=source, source_text=quote)
    item = SemanticItem(item_id="governed-boundary", kind=SemanticKind.CONSTRAINT,
        statement=statement, provenance=(provenance,), confidence=1)
    clause = SemanticClause(clause_id="original-clause", source_record_id=source,
        source_text=quote, semantic_item_ids=(item.item_id,), polarity="NEGATED",
        modality="REQUEST", temporal_scope="CURRENT", requested_effects=("PROHIBIT_DEPLOY",))
    goal = ProductionIntent(objective="One exact artifact", primary_change="One artifact",
        current=True, bounded_change=True, target_paths=(SemanticArgument(value="index.html", provenance=provenance),))
    facts = (fact("output.caption", SemanticRelation.EQUALITY, "Exact original", "The caption is Exact original"),) if with_fact else ()
    records = (source, *(record for f in facts for record in f.provenance.source_record_ids))
    items = [item]
    if observed:
        items.append(SemanticItem(item_id="repo-observation", kind=SemanticKind.FACT,
            statement="Repository observed record", confidence=1,
            provenance=(SemanticProvenance(origin=SemanticOrigin.REPOSITORY_OBSERVED,
                source_record_id=source, source_text="actual observation", evidence_reference="repository-observation:exact-record"),)))
    ir = SimpleNamespace(id=uuid4(), items=tuple(items), clauses=(clause,),
        current_production=(goal,), legacy_typed_projection=False)
    revision = SimpleNamespace(id=uuid4(), work_id=uuid4(), source_assessment_id=uuid4(),
        engineering_semantic_facts=facts, constraints=(statement,), context_facts=("Retained governed context",),
        source_record_ids=records, revision_fingerprint="b" * 64, source_revision="a" * 40)
    return revision, ir


def candidate(revision, ir, inventory, *, wrong_basis=False):
    routes = []
    constraint_ref = next(s["source_ref"] for s in inventory["sources"] if s["kind"] == "IR_CONSTRAINT")
    for source in inventory["sources"]:
        kind = source["kind"]
        method = {"FACT": "ARTIFACT_CONTENT", "IR_CONSTRAINT": "DENY_DEPLOY",
                  "WORK_CONSTRAINT": "DENY_DEPLOY", "IR_ITEM": "RETAIN_CONTEXT", "WORK_CONTEXT": "RETAIN_CONTEXT"}[kind]
        routes.append(FulfillmentRouteCandidate(source_ref=source["source_ref"], capability=method,
            work_constraint_indices=(source["index"],) if kind == "WORK_CONSTRAINT" else (),
            target_paths=("index.html",) if method == "ARTIFACT_CONTENT" else (),
            supporting_source_refs=(constraint_ref,) if kind == "WORK_CONSTRAINT" else (),
            rationale="Declared semantic oracle, not live intelligence"))
    return FulfillmentProjectionCandidate(inventory_fingerprint="0" * 64 if wrong_basis else inventory["inventory_fingerprint"], routes=tuple(routes))


class Oracle:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []
        self.last_observation = {"request_id": "declared-oracle", "usage": {"total_tokens": 0}, "fixture": True}
    def form(self, inventory, capabilities, *, validation_feedback=None):
        self.calls.append(validation_feedback)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


def test_complete_inventory_preserves_observed_items_context_and_fact_bytes():
    revision, ir = basis(observed=True)
    before = [f.model_dump(mode="json") for f in revision.engineering_semantic_facts]
    inventory = fulfillment_inventory(revision, ir)
    assert {s["kind"] for s in inventory["sources"]} == {"FACT", "IR_CONSTRAINT", "IR_ITEM", "WORK_CONSTRAINT", "WORK_CONTEXT"}
    bindings = validate_projection_candidate(candidate(revision, ir, inventory), revision, ir, inventory)
    assert set(map(fulfillment_source_ref, bindings)) == {s["source_ref"] for s in inventory["sources"]}
    assert [f.model_dump(mode="json") for f in revision.engineering_semantic_facts] == before
    assert next(b for b in bindings if b.source_kind is FulfillmentSourceKind.IR_ITEM).source_quote == "Repository observed record"


@pytest.mark.parametrize("subject", ["output.caption", "document.visible.identity", "a-readable-target"])
def test_typed_relation_reuse_is_independent_of_subject_vocabulary(subject):
    revision, ir = basis()
    revision.engineering_semantic_facts = (revision.engineering_semantic_facts[0].model_copy(update={"subject": subject}),)
    inventory = fulfillment_inventory(revision, ir)
    result = deterministic_fulfillment_projection(revision, ir, inventory)
    assert all(b.state != "UNRESOLVED" for b in result)
    validate_fulfillment_projection(result, revision, ir, exact_target_paths=("index.html",))
    assert next(b for b in result if b.fact_id).evidence_method == "EXACT_CANDIDATE_CONTENT"


def test_complete_typed_inventory_needs_no_provider_and_partial_never_disappears():
    revision, ir = basis()
    assessment = SimpleNamespace(id=revision.source_assessment_id, semantic_ir=ir)
    oracle = Oracle([])
    assert all(b.state != "UNRESOLVED" for b in admitted_fulfillment_bindings(revision, assessment, provider=oracle))
    assert oracle.calls == []
    ir.clauses = (ir.clauses[0].model_copy(update={"requested_effects": ()}),)
    bindings = admitted_fulfillment_bindings(revision, assessment)
    assert any(b.state == "UNRESOLVED" for b in bindings)
    assert set(map(fulfillment_source_ref, bindings)) == {s["source_ref"] for s in fulfillment_inventory(revision, ir)["sources"]}


@pytest.mark.parametrize("change,reason", [
    ("missing", "SOURCE_INVENTORY_INCOMPLETE"), ("scope", "SCOPE_EXPANSION"),
    ("revision", "STALE_BASIS"), ("wrong-index-source", "WORK_CONSTRAINT_SOURCE_MISMATCH"),
    ("current-future", "MIXED_FACT_CURRENT_COMPONENT_LOST"), ("wrong-method", "FACT_EVIDENCE_METHOD_MISMATCH")])
def test_source_scope_phase_and_method_rejections(change, reason):
    revision, ir = basis()
    inventory = fulfillment_inventory(revision, ir)
    plan = candidate(revision, ir, inventory)
    routes = list(plan.routes)
    if change == "missing": routes.pop()
    elif change == "scope": routes[0] = routes[0].model_copy(update={"target_paths": ("outside.html",)})
    elif change == "revision": plan = plan.model_copy(update={"inventory_fingerprint": "0" * 64})
    elif change == "wrong-index-source": routes[0] = routes[0].model_copy(update={"work_constraint_indices": (0,)})
    elif change == "current-future": routes[0] = routes[0].model_copy(update={"capability": "HUMAN_INTEGRATION"})
    elif change == "wrong-method": routes[0] = routes[0].model_copy(update={"capability": "GIT_DIFF_SCOPE"})
    with pytest.raises(ValueError, match=reason):
        validate_projection_candidate(plan.model_copy(update={"routes": tuple(routes)}), revision, ir, inventory)


def test_current_clause_cannot_be_delayed_by_global_acceptance_flag():
    revision, ir = basis(with_fact=False)
    item = ir.items[0].model_copy(update={"kind": SemanticKind.PRODUCTION_INTENT, "production": ir.current_production[0]})
    clause = ir.clauses[0].model_copy(update={"polarity": "AFFIRMATIVE", "requested_effects": ()})
    ir.items, ir.clauses = (item,), (clause,)
    inventory = fulfillment_inventory(revision, ir)
    routes = tuple(FulfillmentRouteCandidate(source_ref=s["source_ref"], capability="HUMAN_INTEGRATION",
        work_constraint_indices=(s["index"],) if s["kind"] == "WORK_CONSTRAINT" else (), rationale="Wrong deferral")
        if s["kind"] != "WORK_CONTEXT" else FulfillmentRouteCandidate(source_ref=s["source_ref"], capability="RETAIN_CONTEXT", rationale="context")
        for s in inventory["sources"])
    with pytest.raises(ValueError, match="CURRENT_COMPONENT_LOST"):
        validate_projection_candidate(FulfillmentProjectionCandidate(inventory_fingerprint=inventory["inventory_fingerprint"], routes=routes), revision, ir, inventory)


def test_refine_receipts_and_success_replay_use_one_cumulative_budget():
    revision, ir = basis()
    inventory = fulfillment_inventory(revision, ir)
    oracle = Oracle([candidate(revision, ir, inventory, wrong_basis=True), candidate(revision, ir, inventory)])
    result = form_fulfillment_projection(revision, ir, provider=oracle)
    assert all(b.state != "UNRESOLVED" for b in result)
    assert len(oracle.calls) == 2 and "STALE_BASIS" in oracle.calls[1]
    assert [r["stage"] for r in oracle._fulfillment_receipts] == ["MODEL_REQUEST_PENDING", "MODEL_RESPONSE_OBSERVED", "CANDIDATE_VALIDATED"] * 2
    replay = form_fulfillment_projection(revision, ir, provider=oracle)
    assert len(oracle.calls) == 2
    assert [b.model_dump(exclude={"formation_receipt"}) for b in result] == [b.model_dump(exclude={"formation_receipt"}) for b in replay]


def test_pending_unknown_and_transport_failure_do_not_blindly_retry():
    revision, ir = basis()
    inventory = fulfillment_inventory(revision, ir)
    oracle = Oracle([TimeoutError()])
    result = form_fulfillment_projection(revision, ir, provider=oracle)
    assert all(b.state == "UNRESOLVED" for b in result)
    assert len(oracle.calls) == 1
    form_fulfillment_projection(revision, ir, provider=oracle)
    assert len(oracle.calls) == 1
    paused = Oracle([])
    paused._fulfillment_receipts = []
    recorder = FulfillmentFormationReceipts(revision, inventory, memory=paused._fulfillment_receipts)
    recorder.append("MODEL_REQUEST_PENDING", 1)
    assert all(b.state == "UNRESOLVED" for b in form_fulfillment_projection(revision, ir, provider=paused))
    assert paused.calls == []


def test_observed_response_recovers_without_repeating_model_call():
    revision, ir = basis()
    inventory = fulfillment_inventory(revision, ir)
    oracle = Oracle([])
    oracle._fulfillment_receipts = []
    recorder = FulfillmentFormationReceipts(revision, inventory, memory=oracle._fulfillment_receipts)
    recorder.append("MODEL_REQUEST_PENDING", 1)
    recorder.append("MODEL_RESPONSE_OBSERVED", 1, candidate=candidate(revision, ir, inventory).model_dump(mode="json"))
    assert all(b.state != "UNRESOLVED" for b in form_fulfillment_projection(revision, ir, provider=oracle))
    assert oracle.calls == []


def test_real_provider_keeps_schema_invalid_response_before_validation():
    result = StructuredModelResult(output_text=json.dumps({"unexpected_shape": "not a plan"}),
        provider=ModelProvider.DEEPSEEK, requested_model="controlled", effective_model="controlled", request_id="request-controlled",
        usage=ModelUsage(total_tokens=17), timing=ModelTiming(completed_seconds=0.1))
    runtime = SimpleNamespace(generate=lambda **kwargs: result, close=lambda: None)
    provider = ModelFulfillmentCandidateProvider(lambda: runtime)
    observed = []
    with pytest.raises(ValueError): provider.form({}, [], receipt_callback=lambda **kwargs: observed.append(kwargs))
    assert observed[0]["model"]["request_id"] == "request-controlled"
    assert observed[0]["model"]["usage"]["total_tokens"] == 17
    assert json.loads(observed[0]["candidate_output"]) == {"unexpected_shape": "not a plan"}


def test_receipt_observation_cannot_substitute_human_authorization(monkeypatch):
    from spg.application.integration import RepositoryIntegrationService
    from spg.domain.integration import RepositoryIntegrationRequest
    from spg.infrastructure.persistence.runtime_store import RuntimeStore
    from spg.application.runtime import RuntimeRecordNotFound
    observed_id = uuid4()
    @contextmanager
    def unit_of_work():
        yield SimpleNamespace(session=object())
    database = SimpleNamespace(unit_of_work=unit_of_work)
    monkeypatch.setattr(RuntimeStore, "baseline_candidate", lambda self, identity: SimpleNamespace(id=identity))
    monkeypatch.setattr(RuntimeStore, "human_authorization", lambda self, identity: None)
    monkeypatch.setattr(RuntimeStore, "governance_for_subject", lambda self, identity: [SimpleNamespace(
        id=observed_id, decision_type="WORK_FULFILLMENT_OBSERVATION", authority_identity="work-governance:derived-candidate-observation",
        scope={"validation_passed": True})])
    service = RepositoryIntegrationService(database)
    with pytest.raises(RuntimeRecordNotFound, match="Human Authorization not found"):
        service._prepare_operation(RepositoryIntegrationRequest(candidate_id=uuid4(), candidate_fingerprint="a" * 64,
            human_authorization_id=observed_id))


def test_same_source_current_unknown_is_not_replaced_by_other_fact_passes():
    revision, ir = basis()
    current = revision.engineering_semantic_facts[0]
    assertion = fact("review.outcome", SemanticRelation.ACCEPTANCE_ASSERTION, "Exact original and reviewable Candidate", "Review exact original and then Candidate")
    revision.engineering_semantic_facts = (current, assertion)
    inventory = fulfillment_inventory(revision, ir)
    plan = candidate(revision, ir, inventory)
    routes = (*plan.routes, FulfillmentRouteCandidate(source_ref=f"semantic-fact:{assertion.id}", capability="CANDIDATE_SEAL", rationale="Future owner"))
    bindings = validate_projection_candidate(plan.model_copy(update={"routes": routes}), revision, ir, inventory)
    checks = ({"fact_id": str(current.id), "passed": True, "disposition": "VERIFIED_CURRENT"},
        {"fact_id": str(assertion.id), "passed": False, "disposition": "UNVERIFIABLE_CURRENT"})
    result = evaluate_candidate_handoffs(checks, references=tuple(semantic_fact_reference(f, work_revision_id=revision.id) for f in revision.engineering_semantic_facts),
        admitted_facts={str(f.id): f for f in revision.engineering_semantic_facts}, ir=ir,
        source_revision=revision.source_revision, exact_target_paths=("index.html",), fulfillment_bindings=bindings)
    assert result[-1]["passed"] is False


def test_observed_item_retains_owner_evidence_without_fabricated_human_record():
    revision, ir = basis(observed=True)
    observed = ir.items[-1]
    provenance = observed.provenance[0].model_copy(update={"source_record_id": None, "source_text": None})
    ir.items = (*ir.items[:-1], observed.model_copy(update={"provenance": (provenance,),
        "observed_facts": {"repository.record": SemanticArgument(value="observed", provenance=provenance)}}))
    inventory = fulfillment_inventory(revision, ir)
    bindings = validate_projection_candidate(candidate(revision, ir, inventory), revision, ir, inventory)
    retained = next(b for b in bindings if b.source_kind is FulfillmentSourceKind.IR_ITEM)
    assert retained.state == "RETAINED_CONTEXT" and retained.source_record_ids == ()
    assert retained.semantic_ir_id == ir.id
    source = next(s for s in inventory["sources"] if s["kind"] == "IR_ITEM")
    assert source["payload"]["item"]["provenance"][0]["evidence_reference"] == "repository-observation:exact-record"
    from spg.domain.governed_obligation import FulfillmentBinding
    human = next(b for b in bindings if b.source_kind is FulfillmentSourceKind.WORK_CONSTRAINT)
    with pytest.raises(ValueError, match="exact admitted source records"):
        FulfillmentBinding.model_validate({**human.model_dump(mode="json"), "source_record_ids": []})


@pytest.mark.parametrize("value,qualifiers,reason", [
    (["README.md"], {}, "SCOPE_VALUE_MISMATCH"),
    (["index.html"], {"additional_condition": "must remain protected"}, "SCOPE_VALUE_UNSUPPORTED")])
def test_original_scope_value_and_qualifiers_cannot_be_replaced_by_contract_paths(value, qualifiers, reason):
    revision, ir = basis()
    revision.engineering_semantic_facts = (fact("open.file.scope", SemanticRelation.SCOPE, value,
        "Original authoritative file scope", qualifiers=qualifiers).model_copy(update={"scope": None}),)
    inventory = fulfillment_inventory(revision, ir)
    plan = candidate(revision, ir, inventory)
    routes = (plan.routes[0].model_copy(update={"capability": "GIT_DIFF_SCOPE"}), *plan.routes[1:])
    with pytest.raises(ValueError, match=reason):
        validate_projection_candidate(plan.model_copy(update={"routes": routes}), revision, ir, inventory)
    result = deterministic_fulfillment_projection(revision, ir, inventory)
    assert next(b for b in result if b.fact_id).state == "UNRESOLVED"
