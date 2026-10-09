"""C3 source-linked components and independent bounded semantic validation."""
from __future__ import annotations
import pytest
from tests.test_fulfillment_projection import basis, Oracle
from spg.application.governed_obligations import (
    FulfillmentFormationReceipts, form_fulfillment_projection, fulfillment_inventory,
    validate_projection_candidate, validate_fulfillment_projection, locate_projection_components)
from spg.domain.governed_obligation import (
    FulfillmentComponentBasis, FulfillmentProjectionCandidate, FulfillmentRouteCandidate,
    FulfillmentSemanticReviewCandidate, FulfillmentSemanticSourceReview,
    fulfillment_candidate_fingerprint, fulfillment_components_fingerprint, fulfillment_source_semantic_text)


class ReviewedOracle(Oracle):
    def __init__(self, outputs, reviews=(True,)):
        super().__init__(outputs)
        self.reviews=list(reviews)
        self.review_calls=0
    def review(self, inventory, plan):
        self.review_calls+=1
        equivalent=self.reviews.pop(0)
        return FulfillmentSemanticReviewCandidate(inventory_fingerprint=inventory["inventory_fingerprint"],
            candidate_fingerprint=fulfillment_candidate_fingerprint(plan),
            components_fingerprint=fulfillment_components_fingerprint(plan),
            source_results=tuple(FulfillmentSemanticSourceReview(source_ref=source["source_ref"],
                complete_and_equivalent=equivalent,reason="Controlled separate semantic comparison")
                for source in inventory["sources"]))


def current_lifecycle_candidate():
    revision, ir=basis()
    text="Leave a reviewable Candidate for Human acceptance."
    item=ir.items[0].model_copy(update={"statement":text,"provenance":(ir.items[0].provenance[0].model_copy(update={"source_text":text}),)})
    clause=ir.clauses[0].model_copy(update={"source_text":text,"polarity":"AFFIRMATIVE","requested_effects":()})
    ir.items,ir.clauses=(item,),(clause,)
    ir.current_production=(ir.current_production[0].model_copy(update={"acceptance_required":True}),)
    revision.constraints=(text,)
    inventory=fulfillment_inventory(revision,ir)
    constraint_ref=next(source["source_ref"] for source in inventory["sources"] if source["kind"]=="IR_CONSTRAINT")
    routes=[]
    for source in inventory["sources"]:
        text=fulfillment_source_semantic_text(source)
        capability="ARTIFACT_CONTENT" if source["kind"]=="FACT" else "RETAIN_CONTEXT" if source["kind"]=="WORK_CONTEXT" else "CANDIDATE_SEAL"
        routes.append(FulfillmentRouteCandidate(source_ref=source["source_ref"],capability=capability,
            work_constraint_indices=(source["index"],) if source["kind"]=="WORK_CONSTRAINT" else (),
            supporting_source_refs=(constraint_ref,) if source["kind"]=="WORK_CONSTRAINT" else (),
            target_paths=("index.html",) if capability=="ARTIFACT_CONTENT" else (),rationale="Controlled current lifecycle component",
            component_basis=FulfillmentComponentBasis(source_span_start=0,source_span_end=len(text),source_component_quote=text)))
    return revision,ir,inventory,FulfillmentProjectionCandidate(inventory_fingerprint=inventory["inventory_fingerprint"],routes=tuple(routes))


def test_current_lifecycle_component_requires_review_and_actual_existing_gate():
    revision,ir,inventory,plan=current_lifecycle_candidate()
    with pytest.raises(ValueError,match="SEMANTIC_REVIEW_REQUIRED"):
        validate_projection_candidate(plan,revision,ir,inventory)
    oracle=ReviewedOracle([plan])
    bindings=form_fulfillment_projection(revision,ir,provider=oracle)
    assert len(oracle.calls)==1 and oracle.review_calls==1
    assert all(binding.state!="UNRESOLVED" for binding in bindings)
    assert next(binding for binding in bindings if binding.fact_id).evidence_method=="EXACT_CANDIDATE_CONTENT"
    seals=[binding for binding in bindings if binding.component=="reviewable-candidate"]
    assert seals and all(binding.phase.value=="CANDIDATE_SEAL" and binding.gate_ref=="candidate-owner:sealed-after-verification" for binding in seals)
    validate_fulfillment_projection(bindings,revision,ir,exact_target_paths=("index.html",))
    receipt=bindings[0].formation_receipt
    assert receipt["provider_call_count"]==2 and receipt["maximum_model_calls"]==4
    assert len(receipt["semantic_review_receipt_refs"])==3
    assert [row["stage"] for row in receipt["candidate_attempts"]]==["MODEL_REQUEST_PENDING","MODEL_RESPONSE_OBSERVED",
        "SEMANTIC_REVIEW_PENDING","SEMANTIC_REVIEW_OBSERVED","SEMANTIC_REVIEW_VALIDATED","CANDIDATE_VALIDATED"]


@pytest.mark.parametrize("change,reason",[("quote","SOURCE_QUOTE_DRIFT"),("coverage","SOURCE_CONTRIBUTION_LOST"),
    ("fact","FACT_REFERENCE_SUBSTITUTED"),("missing","MIXED_FACT_CURRENT_COMPONENT_LOST")])
def test_component_identity_and_full_contribution_cannot_be_forged(change,reason):
    revision,ir,inventory,plan=current_lifecycle_candidate()
    route=plan.routes[1];component=route.component_basis
    if change=="quote":component=component.model_copy(update={"source_component_quote":"invented quote"})
    elif change=="coverage":component=component.model_copy(update={"source_span_end":5,"source_component_quote":component.source_component_quote[:5]})
    elif change=="fact":component=component.model_copy(update={"linked_fact_refs":("semantic-fact:not-present",)})
    else:component=None
    changed=plan.model_copy(update={"routes":(plan.routes[0],route.model_copy(update={"component_basis":component}),*plan.routes[2:])})
    with pytest.raises(ValueError,match=reason):
        validate_projection_candidate(changed,revision,ir,inventory,allow_review_pending=True)


def test_semantic_mismatch_is_bounded_and_same_basis_does_not_repeat_either_call():
    revision,ir,inventory,plan=current_lifecycle_candidate()
    oracle=ReviewedOracle([plan,plan],reviews=(False,False))
    result=form_fulfillment_projection(revision,ir,provider=oracle)
    assert len(oracle.calls)==2 and oracle.review_calls==2
    assert all(binding.state=="UNRESOLVED" for binding in result)
    assert "SEMANTIC_COMPONENT_MISMATCH" in oracle.calls[1]
    form_fulfillment_projection(revision,ir,provider=oracle)
    assert len(oracle.calls)==2 and oracle.review_calls==2
    assert result[0].formation_receipt["provider_call_count"]==4


def test_review_pending_outcome_unknown_is_not_repeated_after_resume():
    revision,ir,inventory,plan=current_lifecycle_candidate()
    oracle=ReviewedOracle([])
    oracle._fulfillment_receipts=[]
    recorder=FulfillmentFormationReceipts(revision,inventory,memory=oracle._fulfillment_receipts)
    recorder.append("MODEL_REQUEST_PENDING",1)
    recorder.append("MODEL_RESPONSE_OBSERVED",1,candidate=plan.model_dump(mode="json"))
    recorder.append("SEMANTIC_REVIEW_PENDING",1)
    result=form_fulfillment_projection(revision,ir,provider=oracle)
    assert all(binding.state=="UNRESOLVED" for binding in result)
    assert oracle.calls==[] and oracle.review_calls==0
    form_fulfillment_projection(revision,ir,provider=oracle)
    assert oracle.calls==[] and oracle.review_calls==0


def test_semantic_review_wrong_candidate_identity_cannot_validate_components():
    revision,ir,inventory,plan=current_lifecycle_candidate()
    review=ReviewedOracle([]).review(inventory,plan).model_copy(update={"candidate_fingerprint":"0"*64})
    with pytest.raises(ValueError,match="SEMANTIC_REVIEW_IDENTITY_DRIFT"):
        validate_projection_candidate(plan,revision,ir,inventory,semantic_review=review)


@pytest.mark.parametrize("offsets",[(1,9999),(-3,0)])
def test_exact_unique_unicode_quote_locates_offsets_without_another_model_call(offsets):
    revision,ir,inventory,plan=current_lifecycle_candidate()
    original=revision.engineering_semantic_facts[0]
    quote="\u539f\u59cb\u6807\u9898\u8981\u6c42\uff1aExact original\uff0c\u4fdd\u6301\u51c6\u786e\u3002\U0001f642"
    revision.engineering_semantic_facts=(original.model_copy(update={"provenance":original.provenance.model_copy(update={"source_text":quote})}),)
    inventory=fulfillment_inventory(revision,ir)
    routes=[]
    for route in plan.routes:
        source=next(source for source in inventory["sources"] if source["source_ref"]==route.source_ref)
        quote=fulfillment_source_semantic_text(source)
        routes.append(route.model_copy(update={"component_basis":route.component_basis.model_copy(update={
            "source_span_start":0,"source_span_end":len(quote),"source_component_quote":quote})}))
    plan=plan.model_copy(update={"inventory_fingerprint":inventory["inventory_fingerprint"],"routes":tuple(routes)})
    raw=plan.model_copy(update={"routes":tuple(route.model_copy(update={"component_basis":route.component_basis.model_copy(
        update={"source_span_start":offsets[0],"source_span_end":offsets[1]})}) for route in plan.routes)})
    oracle=ReviewedOracle([raw])
    result=form_fulfillment_projection(revision,ir,provider=oracle)
    assert all(binding.state!="UNRESOLVED" for binding in result)
    assert len(oracle.calls)==1 and oracle.review_calls==1
    located=next(row for row in result[0].formation_receipt["candidate_attempts"] if row["stage"]=="CANDIDATE_LOCATED")
    assert located["raw_candidate_fingerprint"]!=located["candidate_fingerprint"]
    assert len(located["locator_adjustments"])==len(plan.routes)
    assert all(binding.component_basis.source_span_start==0 for binding in result)


def test_ambiguous_quote_with_wrong_offsets_is_not_guessed():
    revision,ir,inventory,plan=current_lifecycle_candidate()
    inventory["sources"][1]["payload"]["clause"]["source_text"]="same fragment; same fragment"
    route=plan.routes[1].model_copy(update={"component_basis":plan.routes[1].component_basis.model_copy(update={
        "source_span_start":1,"source_span_end":2,"source_component_quote":"same fragment"})})
    with pytest.raises(ValueError,match="SOURCE_LOCATION_AMBIGUOUS"):
        locate_projection_components(plan.model_copy(update={"routes":(plan.routes[0],route,*plan.routes[2:])}),inventory)


def test_semantic_review_capability_contract_drift_is_not_rebound_on_read():
    revision,ir,inventory,plan=current_lifecycle_candidate()
    result=form_fulfillment_projection(revision,ir,provider=ReviewedOracle([plan]))
    first=result[0].model_copy(update={"formation_receipt":dict(result[0].formation_receipt,capabilities_fingerprint="0"*64)})
    with pytest.raises(ValueError,match="SEMANTIC_REVIEW_CAPABILITIES_DRIFT"):
        validate_fulfillment_projection((first,*result[1:]),revision,ir,exact_target_paths=("index.html",))


@pytest.mark.parametrize("relation,role,value,reason",[
    ("REFERENCE","PROJECT_REPOSITORY","exact accepted Product source","PROJECT_SOURCE_OWNER_MISMATCH"),
    ("SCOPE",None,["index.html"],"FILE_SCOPE_OWNER_MISMATCH")])
def test_typed_source_and_exact_contract_file_scope_cannot_use_artifact_strings(relation,role,value,reason):
    from spg.domain.engineering_semantics import SemanticRelation, SemanticReferenceRole
    revision,ir,inventory,plan=current_lifecycle_candidate()
    original=revision.engineering_semantic_facts[0]
    original=original.model_copy(update={"relation":SemanticRelation(relation),"value":value,"qualifiers":{},
        "reference_role":None if role is None else SemanticReferenceRole(role)})
    revision.engineering_semantic_facts=(original,)
    inventory=fulfillment_inventory(revision,ir)
    plan=plan.model_copy(update={"inventory_fingerprint":inventory["inventory_fingerprint"]})
    with pytest.raises(ValueError,match=reason):
        validate_projection_candidate(plan,revision,ir,inventory,allow_review_pending=True)
