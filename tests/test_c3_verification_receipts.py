"""C3 Owner candidate receipts, phase coverage and bounded replay protection."""
import json
from types import SimpleNamespace
from uuid import uuid4
import pytest
from spg.domain.model_runtime import ModelUsage
from spg.providers.verification_receipts import VerificationCandidateReceipts, VerificationCandidateFailure
from spg.providers.protected_context_verifier import StaticProtectedContextVerifier
from tests.test_static_protected_context_verifier import subject, check


def response(output):
    return SimpleNamespace(output_text=output, provider=SimpleNamespace(value="fixture"),
        requested_model="fixture", effective_model="fixture", request_id="fixture-request",
        usage=ModelUsage(), timing=None, retry_count=0)


def test_all_candidate_receipt_copies_redact_actual_credential_categories(subject, monkeypatch):
    values={"SPG_DEEPSEEK_API_KEY":"fixture-private-provider-value",
            "SPG_OPERATOR_TOKEN":"fixture-private-operator-value",
            "SPG_MANAGED_SOURCE_PASSWORD":"fixture-private-source-value",
            "SPG_DATABASE_URL":"postgresql://fixture:fixture-dsn-password@127.0.0.1/c1_contract_continuity"}
    for name,value in values.items(): monkeypatch.setenv(name,value)
    recorder=VerificationCandidateReceipts(subject[2])
    number=recorder.begin("fixture",feedback=values)
    recorder.observed("fixture",number,response(json.dumps(values)))
    recorder.validated("fixture",number,predicate="EXACT_WITNESS_MISSING",feedback=values,
        checks=[{"reason":values["SPG_OPERATOR_TOKEN"],"quote":"fixture-dsn-password"}],terminal=True)
    rendered=json.dumps(recorder.metadata())
    assert "[REDACTED]" in rendered
    assert not any(value in rendered for value in (*values.values(),"fixture-dsn-password"))


def test_candidate_is_observed_before_schema_failure_and_feedback_is_bounded(subject):
    repo,base,request,task,contract=subject
    outputs=["{malformed",json.dumps({"checks":[check()]})]
    calls=[]
    def generate(**kwargs):
        calls.append(json.loads(kwargs["input_text"]))
        return response(outputs[len(calls)-1])
    recorder=VerificationCandidateReceipts(request)
    runtime=SimpleNamespace(generate=generate,registry=SimpleNamespace(close=lambda:None))
    results=StaticProtectedContextVerifier(lambda:runtime).verify(request,task,contract,repo,base,receipt_recorder=recorder)
    assert [row["stage"] for row in recorder.records]==["MODEL_REQUEST_PENDING","CANDIDATE_OBSERVED","CANDIDATE_VALIDATED"]*2
    assert recorder.records[1]["candidate_output"]=="{malformed"
    assert recorder.records[2]["failed_predicate"]=="PROTECTED_CONTEXT_CANDIDATE_SCHEMA_INVALID"
    assert calls[1]["predicate_feedback"]["failed_predicate"]=="PROTECTED_CONTEXT_CANDIDATE_SCHEMA_INVALID"
    assert results[0]["coverage"]=="COVERED"
    assert recorder.records[-1]["candidate_is_authority"] is False


def test_validated_success_replay_revalidates_exact_source_without_model(subject):
    repo,base,request,task,contract=subject
    recorder=VerificationCandidateReceipts(request)
    runtime=SimpleNamespace(generate=lambda **_:response(json.dumps({"checks":[check()]})),
        registry=SimpleNamespace(close=lambda:None))
    verifier=StaticProtectedContextVerifier(lambda:runtime)
    verifier.verify(request,task,contract,repo,base,receipt_recorder=recorder)
    count=len(recorder.records)
    verifier.runtime_factory=lambda: (_ for _ in ()).throw(AssertionError("No model replay"))
    replay=verifier.verify(request,task,contract,repo,base,receipt_recorder=recorder)
    assert replay[0]["coverage"]=="COVERED" and len(recorder.records)==count


@pytest.mark.parametrize("state",["pending","terminal_failure"])
def test_unknown_or_terminal_failure_replay_never_opens_another_model_request(subject,state):
    recorder=VerificationCandidateReceipts(subject[2])
    number=recorder.begin("protected-context")
    if state=="terminal_failure":
        recorder.validated("protected-context",number,predicate="PROTECTED_CONTEXT_MODEL_UNAVAILABLE",terminal=True)
    with pytest.raises(VerificationCandidateFailure): recorder.begin("protected-context")
    assert len([row for row in recorder.records if row["stage"]=="MODEL_REQUEST_PENDING"])==1


def test_truthful_unverifiable_needs_no_fabricated_witness(subject):
    repo,base,request,task,contract=subject
    payload={"checks":[{**check("UNVERIFIABLE"),"witnesses":[]}]}
    recorder=VerificationCandidateReceipts(request)
    runtime=SimpleNamespace(generate=lambda **_:response(json.dumps(payload)),registry=SimpleNamespace(close=lambda:None))
    checks=StaticProtectedContextVerifier(lambda:runtime).verify(request,task,contract,repo,base,receipt_recorder=recorder)
    assert checks[0]["coverage"]=="UNVERIFIED" and not checks[0]["witnesses"]
    assert len([row for row in recorder.records if row["stage"]=="MODEL_REQUEST_PENDING"])==1


def test_detailed_candidate_payload_limit_fails_without_retaining_unbounded_copies(subject):
    recorder=VerificationCandidateReceipts(subject[2])
    number=recorder.begin("fixture")
    with pytest.raises(ValueError,match="RECEIPT_LIMIT"):
        recorder.validated("fixture",number,checks=[{"reason":"x"*200000}],terminal=True)
    assert recorder.records[-1]["terminal_reason"]=="CANDIDATE_RECEIPT_LIMIT"
    assert "candidate_checks" not in recorder.records[-1]


def test_non_ecf_current_binding_has_explicit_verification_result(subject):
    from spg.providers.managed_context_fulfillment import verify_binding_inventory
    from spg.domain.governed_obligation import FulfillmentBinding, FulfillmentSourceKind
    repo,base,request,task,contract=subject
    binding=FulfillmentBinding(source_kind=FulfillmentSourceKind.IR_CLAUSE,semantic_ir_id=uuid4(),
        constraint_item_id="open-production",constraint_clause_id="open-clause",
        constraint_fingerprint="a"*64,work_reality_revision_id=uuid4(),
        source_record_ids=(uuid4(),),provenance_fingerprint="b"*64,source_quote="Show Company Home",
        source_revision=base,component="artifact-content",owner="VERIFICATION",phase="CURRENT_VERIFICATION",
        evidence_method="EXACT_CANDIDATE_CONTENT",gate_ref="code-verification:semantic-facts",
        target_paths=("index.html",),projection_inventory_fingerprint="c"*64)
    from spg.domain.governed_obligation import fulfillment_source_ref
    def generate(**kwargs):
        candidate={"context_class":"DERIVED_VERIFICATION_OBLIGATION","semantic_key":fulfillment_source_ref(binding),
            "disposition":"SATISFIED","reason":"Exact current implementation observed",
            "witnesses":[{"path":"index.html","quote":"Company Home"}]}
        return response(json.dumps({"checks":[candidate]}))
    runtime=SimpleNamespace(generate=generate,registry=SimpleNamespace(close=lambda:None))
    outcomes,checks=verify_binding_inventory(request=request,task=task,contract=contract,repository=repo,
        baseline=base,revision=None,ir=None,bindings=(binding,),semantic_checks=(),protected_checks=(),
        static_verifier=StaticProtectedContextVerifier(lambda:runtime),receipt_recorder=VerificationCandidateReceipts(request),native_record=None)
    assert outcomes[0]["current_stage_satisfied"] is True
    assert outcomes[0]["source_ref"]==fulfillment_source_ref(binding)
    assert checks[0]["context_class"]=="DERIVED_VERIFICATION_OBLIGATION"
    assert request.protected_context_obligations[0].context_class=="PRODUCT_INTENT"


def test_non_ecf_current_binding_without_consumer_cannot_silently_skip(subject):
    from spg.providers.managed_context_fulfillment import verify_binding_inventory
    from spg.domain.governed_obligation import FulfillmentBinding
    repo,base,request,task,contract=subject
    binding=FulfillmentBinding(source_kind="IR_CLAUSE",semantic_ir_id=uuid4(),
        constraint_item_id="open-production",constraint_clause_id="open-clause",constraint_fingerprint="a"*64,
        work_reality_revision_id=uuid4(),source_record_ids=(uuid4(),),provenance_fingerprint="b"*64,
        source_quote="Show Company Home",source_revision=base,component="artifact-content",owner="VERIFICATION",
        phase="CURRENT_VERIFICATION",evidence_method="EXACT_CANDIDATE_CONTENT",gate_ref="code-verification:semantic-facts")
    with pytest.raises(ValueError,match="CURRENT_CONTENT_CONSUMER_UNAVAILABLE"):
        verify_binding_inventory(request=request,task=task,contract=contract,repository=repo,baseline=base,
            revision=None,ir=None,bindings=(binding,),semantic_checks=(),protected_checks=(),
            static_verifier=None,receipt_recorder=None,native_record=None)


@pytest.mark.parametrize("corruption",["broad-contract","wrong-path-value","unresolved-scope","unconsumed-qualifier"])
def test_git_scope_consumer_preserves_original_fact_value_scope_and_qualifiers(corruption):
    from spg.providers.managed_context_fulfillment import _exact_fact_git_scope
    reference=SimpleNamespace(relation=SimpleNamespace(value="SCOPE"), value=("index.html",),
        qualifiers={}, unit=None, scope=None)
    binding=SimpleNamespace(target_paths=("index.html",))
    targets=("index.html",)
    changed=("index.html",)
    assert _exact_fact_git_scope(reference,binding,targets,changed)
    if corruption=="broad-contract":
        targets=("index.html","README.md");binding.target_paths=targets;changed=targets
    elif corruption=="wrong-path-value": reference.value=("README.md",)
    elif corruption=="unresolved-scope": reference.scope="some unrelated lifecycle scope"
    else: reference.qualifiers={"operation":"delete"}
    assert not _exact_fact_git_scope(reference,binding,targets,changed)


@pytest.mark.parametrize("corruption", [None, "missing", "failed", "wrong-file"])
def test_reviewed_component_uses_only_its_exact_current_fact_evidence(subject, corruption):
    from spg.providers.managed_context_fulfillment import verify_binding_inventory
    from spg.domain.governed_obligation import FulfillmentBinding, fulfillment_source_ref
    repo, base, request, task, contract = subject
    revision, fact_id = uuid4(), uuid4()
    quote = "Create index.html and leave a reviewable Candidate."
    current = FulfillmentBinding(source_kind="IR_CLAUSE", semantic_ir_id=uuid4(),
        constraint_item_id="production", constraint_clause_id="request", constraint_fingerprint="a"*64,
        work_reality_revision_id=revision, source_record_ids=(uuid4(),), provenance_fingerprint="b"*64,
        source_quote=quote, source_revision=base, component="artifact-content", owner="VERIFICATION",
        phase="CURRENT_VERIFICATION", evidence_method="EXACT_CANDIDATE_CONTENT",
        gate_ref="code-verification:semantic-facts", target_paths=("index.html",),
        component_basis={"source_span_start":0, "source_span_end":17, "source_component_quote":"Create index.html",
            "linked_fact_refs":["semantic-fact:"+str(fact_id)]})
    fact_route={"source_kind":"FACT", "fact_id":str(fact_id), "fact_fingerprint":"d"*64,
        "work_reality_revision_id":str(revision), "source_revision":base,
        "phase":"CURRENT_VERIFICATION", "evidence_method":"EXACT_CANDIDATE_CONTENT", "target_paths":["index.html"]}
    check={"fact_id":str(fact_id), "scope":"index.html", "passed":True, "current_evidence_verified":True,
        "fulfillment_bindings":[fact_route]}
    checks=[check]
    if corruption == "missing": checks=[]
    elif corruption == "failed": check["passed"]=False
    elif corruption == "wrong-file": check["scope"]="other.html"
    outcomes, evidence=verify_binding_inventory(request=request, task=task, contract=contract, repository=repo,
        baseline=base, revision=None, ir=None, bindings=(current,), semantic_checks=checks,
        protected_checks=(), static_verifier=None, receipt_recorder=None, native_record=None)
    assert outcomes[0]["source_ref"] == fulfillment_source_ref(current)
    assert outcomes[0]["current_stage_satisfied"] is (corruption is None)
    assert evidence[0]["evidence_method"] == "EXACT_LINKED_FACT_CURRENT_EVIDENCE"
    assert request.protected_context_obligations == subject[2].protected_context_obligations


def test_current_component_keeps_full_original_source_but_checks_only_its_contribution(subject):
    from spg.domain.governed_obligation import FulfillmentBinding, fulfillment_source_ref
    repo, base, request, task, contract = subject
    quote="Show Company Home. Leave a Candidate for Human acceptance."
    binding=FulfillmentBinding(source_kind="IR_CLAUSE", semantic_ir_id=uuid4(), constraint_item_id="request",
        constraint_clause_id="mixed", constraint_fingerprint="a"*64, work_reality_revision_id=uuid4(),
        source_record_ids=(uuid4(),), provenance_fingerprint="b"*64, source_quote=quote, source_revision=base,
        component="artifact-content", owner="VERIFICATION", phase="CURRENT_VERIFICATION",
        evidence_method="EXACT_CANDIDATE_CONTENT", gate_ref="code-verification:semantic-facts", target_paths=("index.html",),
        component_basis={"source_span_start":0, "source_span_end":18, "source_component_quote":"Show Company Home.", "linked_fact_refs":[]})
    calls=[]
    def generate(**kwargs):
        calls.append(json.loads(kwargs["input_text"]))
        return response(json.dumps({"checks":[{"context_class":"DERIVED_VERIFICATION_OBLIGATION",
            "semantic_key":fulfillment_source_ref(binding), "disposition":"SATISFIED", "reason":"Current exact content observed",
            "witnesses":[{"path":"index.html", "quote":"Company Home"}]}]}))
    runtime=SimpleNamespace(generate=generate, registry=SimpleNamespace(close=lambda:None))
    results=StaticProtectedContextVerifier(lambda:runtime).verify_fulfillment_bindings(request, task, contract, repo, base,
        bindings=(binding,), receipt_recorder=VerificationCandidateReceipts(request))
    contribution=calls[0]["current_component_contributions"][0]["contributions"][0]
    assert contribution["original_source_quote"]==quote
    assert contribution["current_component_quote"]=="Show Company Home."
    assert results[0]["source_component_evidence"][0]["component_basis"]==binding.component_basis.model_dump(mode="json")
    from spg.providers.protected_context_verifier import _content_component
    forged=binding.model_copy(update={"component_basis":binding.component_basis.model_copy(update={"source_span_end":19})})
    with pytest.raises(ValueError, match="CURRENT_COMPONENT_SOURCE_MISMATCH"):
        _content_component(forged)
