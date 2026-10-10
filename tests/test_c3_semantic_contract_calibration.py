"""Option A contract qualification. Controlled candidates, no live intelligence."""
import json
from copy import deepcopy
import pytest
from pydantic import ValidationError
from tests.test_c3_fulfillment_components import current_lifecycle_candidate, ReviewedOracle
from spg.application.governed_obligations import (
    validate_projection_candidate, validate_fulfillment_projection, form_fulfillment_projection,
    locate_projection_components, projection_validation_feedback, fulfillment_inventory,
    evaluate_continuous_gates, work_constraint_sources_correspond)
from spg.domain.governed_obligation import (
    FulfillmentSemanticComponentReview, fulfillment_component_id, exact_file_scope_paths,
    fulfillment_source_semantic_text)


def review(inventory, plan):
    old = ReviewedOracle([]).review(inventory, plan)
    return old.model_copy(update={"component_results": tuple(FulfillmentSemanticComponentReview(
        component_id=fulfillment_component_id(r, inventory["inventory_fingerprint"]), capability=r.capability,
        complete_and_equivalent=True, nonredundant=True, owner_phase_evidence_valid=True,
        context_only=r.capability == "RETAIN_CONTEXT", reason="Controlled independent component verdict.") for r in plan.routes)})


class ComponentOracle(ReviewedOracle):
    def review(self, inventory, plan):
        self.review_calls += 1
        return review(inventory, plan)


def split_content():
    rev, ir, inv, plan = current_lifecycle_candidate()
    from uuid import uuid4
    from spg.domain.engineering_semantics import SemanticRelation
    first="Heading must be Exact original. "
    second="Paragraph must be Another original."
    original=rev.engineering_semantic_facts[0]
    aggregate=original.model_copy(update={"relation":SemanticRelation.ACCEPTANCE_ASSERTION,"value":True,
        "provenance":original.provenance.model_copy(update={"source_text":first+second})})
    atoms=tuple(original.model_copy(update={"id":uuid4(),"value":value,
        "subject":"page.heading_text" if element=="h1" else "page.paragraph_text",
        "qualifiers":{"element":element},"scope":"index.html",
        "provenance":original.provenance.model_copy(update={"source_text":text})})
        for value,element,text in (("Exact original","h1",first),("Another original","p",second)))
    rev.engineering_semantic_facts=(aggregate,*atoms)
    inv=fulfillment_inventory(rev,ir)
    r = plan.routes[0]
    quote=first+second;cut=len(first)
    parts = tuple(r.model_copy(update={"component_basis": r.component_basis.model_copy(update={
        "source_span_start": a, "source_span_end": z, "source_component_quote": quote[a:z],
        "linked_fact_refs":("semantic-fact:"+str(atom.id),)})})
        for a,z,atom in ((0,cut,atoms[0]),(cut,len(quote),atoms[1])))
    atomic_routes=tuple(r.model_copy(update={"source_ref":"semantic-fact:"+str(atom.id),
        "component_basis":r.component_basis.model_copy(update={"source_span_start":0,
            "source_span_end":len(atom.provenance.source_text),"source_component_quote":atom.provenance.source_text})}) for atom in atoms)
    return rev,ir,inv,plan.model_copy(update={"inventory_fingerprint":inv["inventory_fingerprint"],
        "routes": (*parts,*atomic_routes,*plan.routes[1:])})


def test_same_source_same_capability_distinct_components_and_historical_review_shape():
    rev,ir,inv,plan=split_content()
    assert len({fulfillment_component_id(r,inv["inventory_fingerprint"]) for r in plan.routes})==len(plan.routes)
    old=ReviewedOracle([]).review(inv,plan)
    assert "component_results" not in old.model_dump(mode="json")
    with pytest.raises(ValueError,match="COMPONENT_REVIEW_REQUIRED"):
        validate_projection_candidate(plan,rev,ir,inv,semantic_review=old)
    provider=ComponentOracle([plan])
    bindings=form_fulfillment_projection(rev,ir,provider=provider)
    assert all(b.state!="UNRESOLVED" for b in bindings)
    assert len(provider.calls)==1 and provider.review_calls==1
    validate_fulfillment_projection(bindings,rev,ir,exact_target_paths=("index.html",))
    form_fulfillment_projection(rev,ir,provider=provider)
    assert len(provider.calls)==1 and provider.review_calls==1


@pytest.mark.parametrize("change",["duplicate","rationale-only","conflict","missing","truncated"])
def test_component_identity_conflict_and_complete_half_open_coverage(change):
    rev,ir,inv,plan=split_content()
    routes=list(plan.routes)
    if change in {"duplicate","rationale-only"}:
        routes.insert(1,routes[0].model_copy(update={"rationale":"Different prose cannot create a component"}))
        code="DUPLICATE_ROUTE"
    elif change=="conflict":
        routes.insert(1,routes[0].model_copy(update={"capability":"UNRESOLVED"}))
        code="CONFLICTING_DISPOSITION"
    elif change=="missing":
        routes.pop(1);code="SOURCE_CONTRIBUTION_LOST"
    else:
        b=routes[1].component_basis
        routes[1]=routes[1].model_copy(update={"component_basis":b.model_copy(update={
            "source_span_end":b.source_span_end-1,"source_component_quote":b.source_component_quote[:-1]})})
        code="SOURCE_CONTRIBUTION_LOST"
    changed=plan.model_copy(update={"routes":tuple(routes)})
    located,adjustments=locate_projection_components(changed,inv)
    assert not adjustments  # Never widen a quote to silently restore lost punctuation.
    with pytest.raises(ValueError,match=code):
        validate_projection_candidate(located,rev,ir,inv,allow_review_pending=True)


@pytest.mark.parametrize("field",["component_id","capability","nonredundant","owner_phase_evidence_valid","context_only","complete_and_equivalent"])
def test_independent_component_review_cannot_be_substituted(field):
    rev,ir,inv,plan=split_content();result=review(inv,plan)
    row=result.component_results[0]
    value="0"*64 if field=="component_id" else "RETAIN_CONTEXT" if field=="capability" else field=="context_only"
    changed=result.model_copy(update={"component_results":(row.model_copy(update={field:value}),*result.component_results[1:])})
    with pytest.raises(ValueError,match="REVIEW_IDENTITY_DRIFT|SEMANTIC_COMPONENT_MISMATCH"):
        validate_projection_candidate(plan,rev,ir,inv,semantic_review=changed)


def test_review_boolean_evidence_is_strict_not_truthy():
    row=review(*split_content()[2:]).component_results[0].model_dump()
    row["nonredundant"]="true"
    with pytest.raises(ValidationError): FulfillmentSemanticComponentReview.model_validate(row)


def mixed_source(disposition="RETAIN_CONTEXT"):
    rev,ir,inv,plan=current_lifecycle_candidate()
    text="Leave a reviewable Candidate for Human acceptance. Background: isolated rehearsal."
    cut=text.index(" Background:")
    item=ir.items[0].model_copy(update={"statement":text,"provenance":(ir.items[0].provenance[0].model_copy(update={"source_text":text}),)})
    ir.items=(item,);ir.clauses=(ir.clauses[0].model_copy(update={"source_text":text}),)
    rev.constraints=(text,)
    inv=fulfillment_inventory(rev,ir)
    routes=[]
    for r in plan.routes:
        s=next(s for s in inv["sources"] if s["source_ref"]==r.source_ref)
        full=fulfillment_source_semantic_text(s)
        if s["kind"] in {"IR_CONSTRAINT","WORK_CONSTRAINT"}:
            for a,z,cap in ((0,cut,"CANDIDATE_SEAL"),(cut,len(text),disposition)):
                routes.append(r.model_copy(update={"capability":cap,"component_basis":r.component_basis.model_copy(update={
                    "source_span_start":a,"source_span_end":z,"source_component_quote":text[a:z]})}))
        else:
            routes.append(r.model_copy(update={"component_basis":r.component_basis.model_copy(update={
                "source_span_start":0,"source_span_end":len(full),"source_component_quote":full})}))
    return rev,ir,inv,plan.model_copy(update={"inventory_fingerprint":inv["inventory_fingerprint"],"routes":tuple(routes)})


def test_distinct_background_and_candidate_components_have_separate_dispositions():
    rev,ir,inv,plan=mixed_source()
    result=form_fulfillment_projection(rev,ir,provider=ComponentOracle([plan]))
    assert all(b.state!="UNRESOLVED" for b in result)
    assert sum(b.state=="RETAINED_CONTEXT" for b in result)==3
    assert sum(b.phase.value=="CANDIDATE_SEAL" for b in result)==2
    validate_fulfillment_projection(result,rev,ir,exact_target_paths=("index.html",))


def test_distinct_unresolved_component_is_preserved_and_runtime_admission_stops():
    rev,ir,inv,plan=mixed_source("UNRESOLVED")
    pending=validate_projection_candidate(plan,rev,ir,inv,semantic_review=review(inv,plan))
    assert sum(b.state=="UNRESOLVED" for b in pending)==2
    result=form_fulfillment_projection(rev,ir,provider=ComponentOracle([plan]))
    assert all(b.state=="UNRESOLVED" for b in result)
    assert result[0].formation_receipt["terminal_reason"]=="UNRESOLVED_BINDING"
    with pytest.raises(ValueError,match="PROJECTION_UNRESOLVED"):
        validate_fulfillment_projection(result,rev,ir,exact_target_paths=("index.html",))


@pytest.mark.parametrize("qualifiers",[{"exclusive":True},{"exclusive":False},{"exclusive":1},{"exclusive":True,"other":True}])
def test_qualified_scope_preserves_exclusivity_without_guessing_arbitrary_qualifiers(qualifiers):
    from spg.domain.engineering_semantics import SemanticRelation
    rev,ir,inv,plan=current_lifecycle_candidate()
    f=rev.engineering_semantic_facts[0].model_copy(update={"relation":SemanticRelation.SCOPE,
        "value":"index.html","scope":"this request","qualifiers":qualifiers})
    original=deepcopy(f.model_dump(mode="json"))
    assert exact_file_scope_paths(f) is None
    assert exact_file_scope_paths(f,qualified=True)==(("index.html",) if qualifiers=={"exclusive":True} and type(qualifiers["exclusive"]) is bool else None)
    rev.engineering_semantic_facts=(f,);inv=fulfillment_inventory(rev,ir)
    routes=(plan.routes[0].model_copy(update={"capability":"GIT_DIFF_SCOPE"}),*plan.routes[1:])
    plan=plan.model_copy(update={"inventory_fingerprint":inv["inventory_fingerprint"],"routes":routes})
    if qualifiers=={"exclusive":True} and type(qualifiers["exclusive"]) is bool:
        validate_projection_candidate(plan,rev,ir,inv,semantic_review=review(inv,plan))
    else:
        with pytest.raises(ValueError,match="SCOPE_VALUE_UNSUPPORTED"):
            validate_projection_candidate(plan,rev,ir,inv,semantic_review=review(inv,plan))
    assert f.model_dump(mode="json")==original


def test_work_constraint_requires_actual_support_not_vacuous_all():
    rev,ir,_,_=current_lifecycle_candidate()
    assert not work_constraint_sources_correspond(ir,rev.constraints[0],[],component="artifact-content",phase=None)


def test_structured_feedback_collects_independent_failures_and_does_not_invent_later_results():
    rev,ir,inv,plan=split_content()
    routes=(plan.routes[0],plan.routes[0],*plan.routes[2:])
    bad=plan.model_copy(update={"routes":routes})
    response=json.loads(projection_validation_feedback(bad,rev,ir,inv,"OBLIGATION_PROJECTION_DUPLICATE_ROUTE"))
    codes={r["code"] for r in response["violations"]}
    assert {"OBLIGATION_PROJECTION_DUPLICATE_ROUTE","OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST"}<=codes
    assert response["not_evaluable"]==["INDEPENDENT_SEMANTIC_REVIEW","ACTUAL_OWNER_EVIDENCE","ASSURANCE"]
    assert response["violations"][0]["component_id"]==fulfillment_component_id(routes[1],inv["inventory_fingerprint"])
    assert "source_component_quote" not in json.dumps(response)
    provider=ComponentOracle([bad,plan])
    result=form_fulfillment_projection(rev,ir,provider=provider)
    assert all(b.state!="UNRESOLVED" for b in result)
    assert len(provider.calls)==2 and provider.review_calls==1
    feedback=json.loads(provider.calls[1]);assert feedback["primary_error"]=="OBLIGATION_PROJECTION_DUPLICATE_ROUTE"
    assert result[0].formation_receipt["maximum_model_calls"]==4
    form_fulfillment_projection(rev,ir,provider=provider)
    assert len(provider.calls)==2 and provider.review_calls==1


def test_continuous_gate_cannot_upgrade_failed_content_fact():
    rev,ir,inv,plan=current_lifecycle_candidate()
    bindings=validate_projection_candidate(plan,rev,ir,inv,semantic_review=review(inv,plan))
    failed={"fact_id":str(rev.engineering_semantic_facts[0].id),"passed":False,"disposition":"UNVERIFIABLE_CURRENT"}
    result=evaluate_continuous_gates([failed],bindings,None,source_revision=rev.source_revision)
    assert result==(failed,)


def negative_fact_plan():
    from tests.test_fulfillment_projection import basis,candidate
    from spg.domain.engineering_semantics import SemanticRelation
    rev,ir=basis()
    ir.clauses=(ir.clauses[0].model_copy(update={"requested_effects":()}),)
    fact=rev.engineering_semantic_facts[0]
    provenance=fact.provenance.model_copy(update={"source_text":ir.clauses[0].source_text,
        "source_record_ids":(ir.clauses[0].source_record_id,)})
    rev.engineering_semantic_facts=(fact.model_copy(update={"relation":SemanticRelation.SCOPE,
        "value":["external release"],"qualifiers":{"negated":True},"provenance":provenance}),)
    inv=fulfillment_inventory(rev,ir)
    plan=candidate(rev,ir,inv)
    support=next(s["source_ref"] for s in inv["sources"] if s["kind"]=="IR_CONSTRAINT")
    routes=[]
    for r in plan.routes:
        s=next(s for s in inv["sources"] if s["source_ref"]==r.source_ref)
        text=fulfillment_source_semantic_text(s)
        routes.append(r.model_copy(update={"capability":"DENY_DEPLOY" if s["kind"]=="FACT" else r.capability,
            "target_paths":(),"supporting_source_refs":(support,) if s["kind"] in {"FACT","WORK_CONSTRAINT"} else (),
            "component_basis":plan.routes[0].component_basis}))
        from spg.domain.governed_obligation import FulfillmentComponentBasis
        routes[-1]=routes[-1].model_copy(update={"component_basis":FulfillmentComponentBasis(
            source_span_start=0,source_span_end=len(text),source_component_quote=text)})
    return rev,ir,inv,plan.model_copy(update={"routes":tuple(routes)})


def test_original_fact_negative_clause_and_gate_correspond_without_fabricating_effects():
    rev,ir,inv,plan=negative_fact_plan()
    before=deepcopy(ir.clauses[0].model_dump(mode="json"))
    bindings=validate_projection_candidate(plan,rev,ir,inv,semantic_review=review(inv,plan))
    assert next(b for b in bindings if b.fact_id).phase.value=="CONTINUOUS_FROM_ADMISSION"
    assert ir.clauses[0].model_dump(mode="json")==before and not ir.clauses[0].requested_effects
    missing=evaluate_continuous_gates([{"fact_id":str(rev.engineering_semantic_facts[0].id),
        "passed":False,"disposition":"UNVERIFIABLE_CURRENT"}],bindings,None,source_revision=rev.source_revision)
    assert not missing[0]["passed"] and missing[0]["reason"]=="CONTINUOUS_GATE_EVIDENCE_MISSING"


def negative_git_plan():
    rev,ir,inv,plan=negative_fact_plan()
    plan=plan.model_copy(update={"routes":tuple(r.model_copy(update={
        "capability":"GIT_DIFF_SCOPE","target_paths":("index.html",)})
        if next(s for s in inv["sources"] if s["source_ref"]==r.source_ref)["kind"] != "WORK_CONTEXT"
        else r for r in plan.routes)})
    return rev,ir,inv,plan


def test_negative_file_component_preserves_original_exclusion_and_requires_real_diff():
    from spg.providers.managed_context_fulfillment import _exact_fact_git_scope
    from spg.domain.engineering_semantics import semantic_fact_reference
    rev,ir,inv,plan=negative_git_plan()
    original=rev.engineering_semantic_facts[0].model_dump(mode="json")
    bindings=form_fulfillment_projection(rev,ir,provider=ComponentOracle([plan]))
    binding=next(b for b in bindings if b.fact_id)
    ref=semantic_fact_reference(rev.engineering_semantic_facts[0],work_revision_id=rev.id)
    assert _exact_fact_git_scope(ref,binding,("index.html",),("index.html",),revision=rev,ir=ir,bindings=bindings)
    for changed in ((),("README.md",),("index.html","new.html")):
        assert not _exact_fact_git_scope(ref,binding,("index.html",),changed,revision=rev,ir=ir,bindings=bindings)
    assert not _exact_fact_git_scope(ref,binding,("index.html",),("index.html",))
    assert rev.engineering_semantic_facts[0].model_dump(mode="json")==original


@pytest.mark.parametrize("change",["missing-clause-route","literal-target-conflict","html-substitute","affirmative-source"])
def test_negative_file_component_cannot_fake_correspondence(change):
    rev,ir,inv,plan=negative_git_plan()
    if change=="missing-clause-route":
        # Select by original inventory identity rather than a naming convention.
        plan=plan.model_copy(update={"routes":tuple(r.model_copy(update={"capability":"DENY_DEPLOY","target_paths":()})
            if next(s for s in inv["sources"] if s["source_ref"]==r.source_ref)["kind"] in {"IR_CLAUSE","IR_CONSTRAINT"} else r for r in plan.routes)})
    elif change=="literal-target-conflict":
        rev.engineering_semantic_facts=(rev.engineering_semantic_facts[0].model_copy(update={"value":["index.html"]}),)
    elif change=="affirmative-source":
        ir.clauses=(ir.clauses[0].model_copy(update={"polarity":"AFFIRMATIVE"}),)
    else:
        plan=plan.model_copy(update={"routes":tuple(r.model_copy(update={"capability":"ARTIFACT_CONTENT"})
            if r.source_ref.startswith("semantic-fact:") else r for r in plan.routes)})
    inv=fulfillment_inventory(rev,ir);plan=plan.model_copy(update={"inventory_fingerprint":inv["inventory_fingerprint"]})
    with pytest.raises(ValueError,match="CORRESPONDENCE_UNPROVEN|TARGET_CONFLICT|OWNER_MISMATCH|VALUE_UNSUPPORTED|POLARITY"):
        validate_projection_candidate(plan,rev,ir,inv,semantic_review=review(inv,plan))


@pytest.mark.parametrize("change",["affirmative","wrong-source","missing-support","wrong-gate","invented-preview"])
def test_prohibition_cannot_invent_source_operation_or_permission(change):
    rev,ir,inv,plan=negative_fact_plan()
    if change=="affirmative":ir.clauses=(ir.clauses[0].model_copy(update={"polarity":"AFFIRMATIVE"}),)
    elif change=="wrong-source":
        from uuid import uuid4
        f=rev.engineering_semantic_facts[0]
        rev.engineering_semantic_facts=(f.model_copy(update={"provenance":f.provenance.model_copy(update={"source_record_ids":(uuid4(),)})}),)
    elif change=="missing-support":plan=plan.model_copy(update={"routes":(plan.routes[0].model_copy(update={"supporting_source_refs":()}),*plan.routes[1:])})
    elif change=="wrong-gate":plan=plan.model_copy(update={"routes":(plan.routes[0].model_copy(update={"capability":"DENY_PUBLISH"}),*plan.routes[1:])})
    else:
        # An independent reviewer rejects an invented operation; no keyword routing.
        plan=plan.model_copy(update={"routes":tuple(r.model_copy(update={"capability":"DENY_PREVIEW"})
            if r.capability=="DENY_DEPLOY" else r for r in plan.routes)})
    inv=fulfillment_inventory(rev,ir);plan=plan.model_copy(update={"inventory_fingerprint":inv["inventory_fingerprint"]})
    verdict=review(inv,plan)
    if change=="invented-preview":verdict=verdict.model_copy(update={"component_results":tuple(
        r.model_copy(update={"owner_phase_evidence_valid":False}) if r.capability=="DENY_PREVIEW" else r for r in verdict.component_results)})
    with pytest.raises(ValueError,match="EXACT_CLAUSE|CORRESPONDENCE_UNPROVEN|POLARITY_CONFLICT|SEMANTIC_COMPONENT_MISMATCH"):
        validate_projection_candidate(plan,rev,ir,inv,semantic_review=verdict)


def test_distinct_content_components_have_distinct_protected_context_keys():
    from spg.providers.protected_context_verifier import StaticProtectedContextVerifier
    rev,ir,inv,plan=split_content()
    bindings=validate_projection_candidate(plan,rev,ir,inv,semantic_review=review(inv,plan))
    bindings=tuple(b for b in bindings if b.evidence_method=="EXACT_CANDIDATE_CONTENT")
    derived=StaticProtectedContextVerifier._derived_obligations(bindings,"b"*64)
    assert len({d.semantic_key for d in derived})==len(derived)


@pytest.mark.parametrize("capability",["GIT_DIFF_SCOPE","DENY_DEPLOY"])
def test_production_exclusion_wrapper_uses_exact_original_sources_with_empty_effects(capability):
    from spg.domain.intent_realization import SemanticKind
    from spg.domain.governed_obligation import FulfillmentPhase
    rev,ir,inv,plan=negative_fact_plan()
    production=ir.items[0].model_copy(update={"item_id":"original-production","kind":SemanticKind.PRODUCTION_INTENT,
        "production":ir.current_production[0].model_copy(update={"exclusions":("a protected external effect",)})})
    prod_clause=ir.clauses[0].model_copy(update={"clause_id":"production-request","semantic_item_ids":(production.item_id,),"polarity":"AFFIRMATIVE"})
    ir.items=(*ir.items,production);ir.clauses=(*ir.clauses,prod_clause)
    inv=fulfillment_inventory(rev,ir)
    entries=[s for s in inv["sources"] if s["kind"] in {"IR_CONSTRAINT","IR_CLAUSE"}]
    phase=FulfillmentPhase.CURRENT_VERIFICATION if capability=="GIT_DIFF_SCOPE" else FulfillmentPhase.CONTINUOUS_FROM_ADMISSION
    component="git-diff-scope" if capability=="GIT_DIFF_SCOPE" else "deploy"
    quote="Excluded from this Work: a protected external effect"
    assert work_constraint_sources_correspond(ir,quote,entries,component=component,phase=phase,
        semantic_component_declared=True,calibrated=True)
    assert not work_constraint_sources_correspond(ir,quote,entries,component=component,phase=phase,
        semantic_component_declared=True,calibrated=False)
    assert not work_constraint_sources_correspond(ir,"Excluded from this Work: invented effect",entries,
        component=component,phase=phase,semantic_component_declared=True,calibrated=True)


def test_multi_predicate_feedback_keeps_wrong_link_identity_visible():
    rev,ir,inv,plan=split_content()
    r=plan.routes[0].model_copy(update={"component_basis":plan.routes[0].component_basis.model_copy(update={
        "linked_fact_refs":("semantic-fact:missing",)})})
    bad=plan.model_copy(update={"routes":(r,r,*plan.routes[1:])})
    feedback=json.loads(projection_validation_feedback(bad,rev,ir,inv,"OBLIGATION_PROJECTION_DUPLICATE_ROUTE"))
    assert {"OBLIGATION_COMPONENT_FACT_REFERENCE_SUBSTITUTED","OBLIGATION_PROJECTION_DUPLICATE_ROUTE"}<={r["code"] for r in feedback["violations"]}


@pytest.mark.parametrize("content",["correct","wrong-paragraph","missing-proof"])
def test_mixed_acceptance_fact_consumes_completed_exact_git_content_evidence(tmp_path,content):
    import subprocess
    from types import SimpleNamespace
    from spg.domain.engineering_semantics import semantic_fact_reference
    from spg.providers.managed_context_fulfillment import verify_fulfillment_fact_routes
    rev,ir,inv,plan=split_content()
    aggregate=rev.engineering_semantic_facts[0]
    suffix=" Leave a reviewable Candidate for Human acceptance."
    old=aggregate.provenance.source_text
    aggregate=aggregate.model_copy(update={"provenance":aggregate.provenance.model_copy(update={"source_text":old+suffix})})
    rev.engineering_semantic_facts=(aggregate,*rev.engineering_semantic_facts[1:])
    inv=fulfillment_inventory(rev,ir)
    seal=plan.routes[0].model_copy(update={"capability":"CANDIDATE_SEAL","target_paths":(),
        "component_basis":plan.routes[0].component_basis.model_copy(update={"source_span_start":len(old),
            "source_span_end":len(old+suffix),"source_component_quote":suffix,"linked_fact_refs":()})})
    plan=plan.model_copy(update={"inventory_fingerprint":inv["inventory_fingerprint"],"routes":(*plan.routes,seal)})
    bindings=validate_projection_candidate(plan,rev,ir,inv,semantic_review=review(inv,plan))
    def git(*args):return subprocess.check_output(["git","-C",str(tmp_path),*args],text=True).strip()
    git("init","-q");git("-c","user.name=Qualification","-c","user.email=qualification@example.invalid","commit","--allow-empty","-qm","baseline")
    baseline=git("rev-parse","HEAD")
    paragraph="Wrong content" if content=="wrong-paragraph" else "Another original"
    (tmp_path/"index.html").write_text("<h1>Exact original</h1><p>"+paragraph+"</p>",encoding="utf-8")
    git("add","index.html");git("-c","user.name=Qualification","-c","user.email=qualification@example.invalid","commit","-qm","candidate")
    head=git("rev-parse","HEAD");tree=git("rev-parse","HEAD^{tree}")
    refs=tuple(semantic_fact_reference(f,work_revision_id=rev.id) for f in rev.engineering_semantic_facts)
    if content=="missing-proof":refs=(refs[0],refs[1])
    result=verify_fulfillment_fact_routes(repository=tmp_path,request=SimpleNamespace(proposed_commit_identity=head,tree_identity=tree),
        contract=SimpleNamespace(source_revision=baseline,exact_targets=(SimpleNamespace(path="index.html"),)),
        references=refs,admitted_facts={str(f.id):f for f in rev.engineering_semantic_facts},
        revision=rev,ir=ir,baseline=SimpleNamespace(),bindings=bindings,plan_repair=None)
    row=result[0]
    assert row["passed"] is (content=="correct")
    assert row["current_evidence_verified"] is (content=="correct")
    assert len(row["current_component_evidence"])==2
    assert row["future_evidence_status"]=="PENDING_FUTURE_OWNER_GATE"
    assert all(e["candidate_revision"]==head and e["candidate_tree"]==tree for e in row["current_component_evidence"])
