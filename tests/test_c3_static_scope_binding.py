"""Open textual Scope is a reviewed derived binding, never a filename alias."""
from copy import deepcopy
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.domain.engineering_semantics import SemanticRelation, semantic_fact_reference
from spg.infrastructure.model_runtime import StructuredModelResult, ModelProvider, ModelUsage, ModelTiming
from spg.providers.static_html_semantic_verifier import StaticHTMLPlanRepair, verify_static_html_semantic_facts
from spg.providers.verification_receipts import VerificationCandidateReceipts
from tests.test_n1_static_html_semantics import _fixture, _candidate, _admitted_count, ITEMS, _git


def scope_case(tmp_path, scope="the requested landing page", qualifiers=None):
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    source = "The requested landing page of this Work is index.html; its h1 must equal N1 Budget."
    admitted = _admitted_count(source, scope=scope, subject="unlisted.visible.heading", qualifiers=qualifiers)
    admitted = admitted.model_copy(update={"relation": SemanticRelation.EQUALITY, "value": "N1 Budget"})
    fact = semantic_fact_reference(admitted, work_revision_id=admitted.admitted_work_revision_id)
    request = SimpleNamespace(verification_identity=uuid4(), snapshot_id=uuid4(), source_baseline_id=contract.source_baseline_id,
        proposed_commit_identity=candidate, tree_identity=_git(repository, "rev-parse", candidate+"^{tree}"),
        decision_context_fingerprint="scope-fixture", semantic_fact_obligations=(fact,), fulfillment_bindings=(), protected_context_obligations=())
    recorder = VerificationCandidateReceipts(request)
    calls = []
    def runtime(outputs):
        def generate(**kwargs):
            calls.append(kwargs)
            method, path = outputs[len(calls)-1]
            return StructuredModelResult(output_text=json.dumps({"method":method, "target_path":path, "source_quote":source}),
                provider=ModelProvider.DEEPSEEK, requested_model="controlled-scope-review", effective_model="controlled-scope-review",
                request_id="scope-"+str(len(calls)), usage=ModelUsage(unknown=True), timing=ModelTiming())
        return SimpleNamespace(generate=generate, registry=SimpleNamespace(close=lambda:None))
    return repository, contract, candidate, admitted, fact, recorder, calls, runtime


@pytest.mark.parametrize("scope", ["the requested landing page", "本工作要求的新建页面", "the authorized introductory surface"])
def test_open_scope_preserved_and_bound_only_after_existing_independent_review(tmp_path, scope):
    repository, contract, candidate, admitted, fact, recorder, calls, runtime = scope_case(tmp_path, scope, qualifiers={"count":1})
    before = deepcopy(admitted.model_dump(mode="json"))
    repair = StaticHTMLPlanRepair(lambda:runtime([("EXACT_H1","index.html")]*2), receipt_recorder=recorder)
    result = verify_static_html_semantic_facts(repository, candidate, contract, (fact,),
        admitted_facts={str(admitted.id):admitted}, plan_repair=repair)[0]
    assert result["passed"] and len(calls)==2
    assert result["materialization"]["scope"] == scope
    assert result["materialization"]["target_path"] == "index.html"
    assert result["materialization"]["model_repair"]["independent_plan_review"]
    assert admitted.model_dump(mode="json") == before
    for call in calls:
        payload=json.loads(call["input_text"])
        assert payload["scope"]==scope and payload["authorized_target_contract"]==contract.model_dump(mode="json")
    assert recorder.records[-1]["plan_review_role"]=="INDEPENDENT_SCOPED_PLAN_REVIEW"
    assert all(r["budget_limit"]==2 for r in recorder.records)
    frozen=deepcopy(recorder.records)
    repair.runtime_factory=lambda:(_ for _ in ()).throw(AssertionError("replay cannot request"))
    assert verify_static_html_semantic_facts(repository,candidate,contract,(fact,),
        admitted_facts={str(admitted.id):admitted},plan_repair=repair)[0]["passed"]
    assert recorder.records==frozen
    changed=contract.model_copy(update={"desired_outcome":"different Work outcome"})
    with pytest.raises(ValueError,match="REPLAY_BASIS_MISMATCH"):
        verify_static_html_semantic_facts(repository,candidate,changed,(fact,),
            admitted_facts={str(admitted.id):admitted},plan_repair=repair)


@pytest.mark.parametrize("failure", ["unauthorized-path", "unknown-qualifier", "review-refusal", "missing-review"])
def test_scope_binding_cannot_expand_targets_drop_qualifiers_or_manufacture_review(tmp_path,failure):
    values={"unsupported_open_restriction":"must remain"} if failure=="unknown-qualifier" else {}
    repository,contract,candidate,admitted,fact,recorder,calls,runtime=scope_case(tmp_path,qualifiers=values)
    outputs=[("EXACT_H1","other.html"),("EXACT_H1","index.html")] if failure=="unauthorized-path" else [
        ("EXACT_H1","index.html"),("UNVERIFIABLE","index.html") if failure=="review-refusal" else ("EXACT_H1","index.html")]
    if failure=="missing-review":
        def interrupted():
            active=runtime(outputs)
            original=active.generate
            def generate(**request):
                if calls: raise RuntimeError("controlled independent dependency unavailable")
                return original(**request)
            active.generate=generate
            return active
        with pytest.raises(ValueError,match="STATIC_HTML_PLAN_MODEL_UNAVAILABLE"):
            verify_static_html_semantic_facts(repository,candidate,contract,(fact,),
                admitted_facts={str(admitted.id):admitted},plan_repair=StaticHTMLPlanRepair(interrupted,receipt_recorder=recorder))
        assert len(calls)==1
    else:
        result=verify_static_html_semantic_facts(repository,candidate,contract,(fact,),
            admitted_facts={str(admitted.id):admitted},plan_repair=StaticHTMLPlanRepair(lambda:runtime(outputs),receipt_recorder=recorder))[0]
        assert not result["passed"] and result["disposition"]=="UNVERIFIABLE_CURRENT"
        assert len(calls)==2


def test_reviewed_scope_does_not_require_an_html_keyword_or_hide_wrong_content(tmp_path):
    repository,contract,candidate,admitted,fact,recorder,calls,runtime=scope_case(tmp_path,qualifiers={"count":1})
    source="The primary visible heading of the requested landing page at index.html must equal N1 Budget."
    admitted=admitted.model_copy(update={"provenance":admitted.provenance.model_copy(update={"source_text":source})})
    # The existing fixture runtime closes over the original source; use this
    # independent pair of controlled plan responses with the exact new source.
    def factory():
        def generate(**kwargs):
            calls.append(kwargs)
            return StructuredModelResult(output_text=json.dumps({"method":"EXACT_H1","target_path":"index.html","source_quote":source}),
                provider=ModelProvider.DEEPSEEK,requested_model="controlled-open-scope",effective_model="controlled-open-scope",
                request_id="open-scope-"+str(len(calls)),usage=ModelUsage(unknown=True),timing=ModelTiming())
        return SimpleNamespace(generate=generate,registry=SimpleNamespace(close=lambda:None))
    check=verify_static_html_semantic_facts(repository,candidate,contract,(fact,),
        admitted_facts={str(admitted.id):admitted},plan_repair=StaticHTMLPlanRepair(factory))[0]
    assert check["passed"] and len(calls)==2
    (repository/"index.html").write_text("<h1>Wrong actual content</h1>")
    _git(repository,"add","index.html");_git(repository,"commit","-m","controlled wrong content")
    wrong=_git(repository,"rev-parse","HEAD");calls.clear()
    check=verify_static_html_semantic_facts(repository,wrong,contract,(fact,),
        admitted_facts={str(admitted.id):admitted},plan_repair=StaticHTMLPlanRepair(factory))[0]
    assert not check["passed"] and check["disposition"]=="FAILED_CURRENT" and len(calls)==2


@pytest.mark.parametrize("drift", ["review-wire", "review-target", "qualifier", "role"])
def test_scoped_plan_replay_rejects_changed_review_or_original_operands_without_call(tmp_path,drift):
    repository,contract,candidate,admitted,fact,recorder,calls,runtime=scope_case(tmp_path,qualifiers={"count":1})
    repair=StaticHTMLPlanRepair(lambda:runtime([("EXACT_H1","index.html")]*2),receipt_recorder=recorder)
    assert verify_static_html_semantic_facts(repository,candidate,contract,(fact,),
        admitted_facts={str(admitted.id):admitted},plan_repair=repair)[0]["passed"]
    if drift=="review-wire": recorder.records[4]["candidate_output"]+=" "
    elif drift=="review-target": recorder.records[-1]["candidate_checks"][0]["target_path"]="other.html"
    elif drift=="role": recorder.records[-1]["plan_review_role"]="INDEPENDENT_COUNT_PLAN_REVIEW"
    else:
        admitted=admitted.model_copy(update={"qualifiers":{"count":2}})
        fact=semantic_fact_reference(admitted,work_revision_id=admitted.admitted_work_revision_id)
    repair.runtime_factory=lambda:(_ for _ in ()).throw(AssertionError("no replay model"))
    with pytest.raises(ValueError,match="REPLAY_BASIS_MISMATCH"):
        repair.repair(fact,admitted,None,target_contract=contract)
    assert len(calls)==2
