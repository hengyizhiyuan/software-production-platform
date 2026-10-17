from types import SimpleNamespace
from uuid import uuid4
import json
import subprocess

import pytest
from spg.providers.protected_context_verifier import StaticProtectedContextVerifier
from spg.domain.production_intelligence import ProtectedContextObligation
from spg.domain.verification import VerificationCapabilityRequest, VerificationCapabilityResult, VerificationEvidence, VerificationResultValue
from spg.application.verification import _project_decision_context_evidence
from spg.providers.repository_code_verifier import _exact_protected_context_coverage
from hashlib import sha256


@pytest.fixture
def subject(tmp_path):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args]).decode().strip()
    git('init', '-b', 'main'); git('config', 'user.name', 'Verification'); git('config', 'user.email', 'verification@example.invalid')
    (tmp_path/'index.html').write_text('<main>Company Home</main>')
    (tmp_path/'README.md').write_text('Company Home is required')
    git('add','.');git('commit','-m','Exact subject')
    revision=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
    obligation=ProtectedContextObligation(context_class='PRODUCT_INTENT',semantic_key='homepage',source_ref='git:README.md',source_revision=revision,authority='product',content='Company Home',content_digest=sha256(b'Company Home').hexdigest(),package_fingerprint='f'*64)
    req=VerificationCapabilityRequest(verification_identity=uuid4(),obligation='PATH_SCOPE',snapshot_id=uuid4(),proposed_commit_identity=revision,tree_identity=tree,completion_evaluation_id=uuid4(),plan_revision_id=uuid4(),source_baseline_id=uuid4(),decision_context_fingerprint='f'*64,protected_context_obligations=(obligation,))
    task=SimpleNamespace(task_contract_id=uuid4(),objective='Company home',scope=('index.html',),constraints=(),out_of_scope=(),decision_context=SimpleNamespace(package_fingerprint='f'*64,protected_obligations=(obligation,)))
    contract=SimpleNamespace(allowed_areas=(),exact_targets=(SimpleNamespace(path='index.html'),))
    return tmp_path,revision,req,task,contract


def invoke(subject, checks):
    repo,base,request,task,contract=subject
    response=SimpleNamespace(output_text=json.dumps({'checks':checks}),provider=SimpleNamespace(value='test'),effective_model='test',request_id='test',usage=SimpleNamespace())
    from spg.domain.model_runtime import ModelUsage
    response.usage=ModelUsage()
    runtime=SimpleNamespace(generate=lambda **kwargs:response,registry=SimpleNamespace(close=lambda:None))
    return StaticProtectedContextVerifier(lambda:runtime).verify(request,task,contract,repo,base)


def check(disposition='SATISFIED',path='index.html',quote='Company Home'):
    return {'context_class':'PRODUCT_INTENT','semantic_key':'homepage','disposition':disposition,'reason':'The exact implementation is inspected','witnesses':[{'path':path,'quote':quote}]}


def test_exact_source_witness_is_persisted_and_projects_coverage(subject):
    checks=invoke(subject,[check()]);request=subject[2]
    assert checks[0]['candidate_revision']==request.proposed_commit_identity
    assert checks[0]['observed_source_digests']['index.html']==sha256(b'<main>Company Home</main>').hexdigest()
    result=VerificationCapabilityResult(result=VerificationResultValue.PASS,evidence=VerificationEvidence(obligation='PATH_SCOPE',subject_commit_identity=request.proposed_commit_identity,subject_tree_identity=request.tree_identity,expected='Protected obligation',observed='PASS',metadata={'protected_context_checks':checks}))
    projected=_project_decision_context_evidence(request,result)['metadata']['decision_context']
    assert projected['protected_obligations'][0]['coverage']=='COVERED'
    wrong={**checks[0],'package_fingerprint':'0'*64}
    assert _project_decision_context_evidence(request,result.model_copy(update={'evidence':result.evidence.model_copy(update={'metadata':{'protected_context_checks':[wrong]}})}))['metadata']['decision_context']['protected_obligations'][0]['coverage']=='UNVERIFIED'
    assert _project_decision_context_evidence(request,result.model_copy(update={'result':VerificationResultValue.FAIL}))['metadata']['decision_context']['protected_obligations'][0]['coverage']=='UNVERIFIED'


@pytest.mark.parametrize('checks',[[],[check(),check()],[check(quote='invented behavior')],[check(path='README.md',quote='Company Home is required')]])
def test_missing_duplicate_fabricated_or_requirement_only_witness_blocks(subject,checks):
    with pytest.raises(ValueError):invoke(subject,checks)


@pytest.mark.parametrize('disposition',['CONTRADICTED','UNVERIFIABLE'])
def test_failure_or_unknown_never_covers_protected_meaning(subject,disposition):
    assert invoke(subject,[check(disposition)])[0]['coverage']=='UNVERIFIED'


def test_exact_tree_cannot_be_substituted(subject):
    repo,base,request,task,contract=subject
    with pytest.raises(ValueError,match='TREE_MISMATCH'):
        invoke((repo,base,request.model_copy(update={'tree_identity':'0'*40}),task,contract),[check()])


def test_protected_coverage_must_match_every_exact_obligation_and_candidate(subject):
    request=subject[2]
    checks=invoke(subject,[check()])
    assert _exact_protected_context_coverage(request,checks)
    assert not _exact_protected_context_coverage(request,())
    assert not _exact_protected_context_coverage(request,(*checks,*checks))
    for key,value in [('source_revision','wrong'),('candidate_tree','0'*40),
                      ('coverage','UNVERIFIED')]:
        assert not _exact_protected_context_coverage(
            request,({**checks[0],key:value},))


def test_managed_context_cannot_blanket_defer_source_obligations(subject):
    from spg.application.decision_context import MANAGED_WEB_SURFACE
    repo,base,request,task,contract=subject
    task.decision_context.surface=MANAGED_WEB_SURFACE
    with pytest.raises(AssertionError, match='source model must not judge governance'):
        StaticProtectedContextVerifier(lambda: (_ for _ in ()).throw(
            AssertionError('source model must not judge governance'))).verify(
                request,task,contract,repo,base)


def test_wire_repair_is_bounded_and_preserves_a_contradiction(subject):
    repo,base,request,task,contract=subject
    outputs=[{'checks':[check('CONTRADICTED',quote='not an observed quote')]},
             {'checks':[check('CONTRADICTED')]}]
    payloads=[]
    def generate(**kwargs):
        payloads.append(json.loads(kwargs['input_text']))
        from spg.domain.model_runtime import ModelUsage
        return SimpleNamespace(output_text=json.dumps(outputs[len(payloads)-1]),provider=SimpleNamespace(value='test'),effective_model='test',request_id='test',usage=ModelUsage())
    runtime=SimpleNamespace(generate=generate,registry=SimpleNamespace(close=lambda:None))
    result=StaticProtectedContextVerifier(lambda:runtime).verify(request,task,contract,repo,base)
    assert len(payloads)==2
    assert payloads[1]['wire_feedback']=='PROTECTED_CONTEXT_WITNESS_NOT_OBSERVED'
    assert result[0]['disposition']=='CONTRADICTED'
    assert result[0]['coverage']=='UNVERIFIED'


def test_static_context_adapter_does_not_replace_other_profile_verification(subject):
    contract=subject[4]
    assert StaticProtectedContextVerifier.supports(contract)
    assert not StaticProtectedContextVerifier.supports(SimpleNamespace(allowed_areas=(),exact_targets=(SimpleNamespace(path='src/app.py'),)))
    assert not StaticProtectedContextVerifier.supports(SimpleNamespace(allowed_areas=('src/**',),exact_targets=()))


def test_wire_repair_cannot_upgrade_a_contradiction(subject):
    repo,base,request,task,contract=subject
    outputs=[{'checks':[check('CONTRADICTED',quote='not observed')]}, {'checks':[check('SATISFIED')]}]
    calls=[]
    def generate(**kwargs):
        from spg.domain.model_runtime import ModelUsage
        calls.append(kwargs)
        return SimpleNamespace(output_text=json.dumps(outputs[len(calls)-1]),provider=SimpleNamespace(value='test'),effective_model='test',request_id='test',usage=ModelUsage())
    runtime=SimpleNamespace(generate=generate,registry=SimpleNamespace(close=lambda:None))
    with pytest.raises(ValueError,match='REPAIR_CHANGED_JUDGMENT'):
        StaticProtectedContextVerifier(lambda:runtime).verify(request,task,contract,repo,base)
    assert len(calls)==2


@pytest.mark.parametrize("future_gate", (True, False))
def test_current_consumer_receives_same_source_lifecycle_plan_without_claiming_seal(subject, future_gate):
    from copy import deepcopy
    from tests.test_c3_reviewed_fact_method_applicability import case, preconditions, verdict
    from spg.application import governed_obligations as admission
    from spg.domain.governed_obligation import fulfillment_source_ref
    from spg.domain.engineering_semantics import semantic_fact_reference
    from spg.domain.model_runtime import ModelUsage
    repo, baseline, request, task, contract = subject
    revision, ir, inventory, proposal = case(mixed=True)
    plan = admission.validate_projection_candidate(proposal, revision, ir, inventory,
        source_contract="v3", owner_preconditions=preconditions(revision, ir, inventory),
        semantic_review=verdict(inventory, proposal))
    current = plan[0]
    future = plan[1]
    # Immutable test fixture source identity is bound to the exact test Git.
    current = current.model_copy(update={"source_revision": baseline})
    future = future.model_copy(update={"source_revision": baseline})
    reference = semantic_fact_reference(revision.engineering_semantic_facts[0], work_revision_id=revision.id)
    request = request.model_copy(update={"semantic_fact_obligations": (reference,)})
    full_plan = (current, future) if future_gate else (current,)
    before = deepcopy(full_plan)
    calls = []
    def generate(**kwargs):
        payload = json.loads(kwargs["input_text"]); calls.append(payload)
        matching = [b for b in payload["assigned_fulfillment_bindings"]
            if b["fact_id"] == str(current.fact_id) and b["phase"] == "CANDIDATE_SEAL"]
        checks = [{"context_class": item["context_class"], "semantic_key": item["semantic_key"],
            "disposition": "SATISFIED" if matching else "UNVERIFIABLE",
            "reason": "Current content inspected; the separate Candidate gate remains pending" if matching
                else "No separate lifecycle responsibility has been supplied",
            "witnesses": [{"path": "index.html", "quote": "Company Home"}] if matching else []}
            for item in payload["protected_obligations"]]
        return SimpleNamespace(output_text=json.dumps({"checks": checks}), provider=SimpleNamespace(value="test"),
            effective_model="test", request_id="same-source-plan", usage=ModelUsage())
    runtime = SimpleNamespace(generate=generate, registry=SimpleNamespace(close=lambda: None))
    verifier = StaticProtectedContextVerifier(lambda: runtime)
    checked = verifier.verify_fulfillment_bindings(request, task, contract, repo, baseline,
        bindings=(current,), fulfillment_bindings=full_plan)
    assert checked[0]["coverage"] == ("COVERED" if future_gate else "UNVERIFIED")
    assert full_plan == before and len(calls) == 1
    assert calls[0]["assigned_fulfillment_bindings"] == [b.model_dump(mode="json") for b in full_plan]
    assert len(calls[0]["protected_obligations"]) == 1
    assert checked[0]["binding"] == current.model_dump(mode="json")
    with pytest.raises(ValueError, match="CURRENT_COMPONENT_NOT_ASSIGNED"):
        verifier.verify_fulfillment_bindings(request, task, contract, repo, baseline,
            bindings=(current,), fulfillment_bindings=())


@pytest.mark.parametrize("drift", ("source_revision", "work_reality_revision_id", "source_quote", "provenance_fingerprint"))
def test_related_future_binding_cannot_substitute_original_source(subject, drift):
    from tests.test_c3_reviewed_fact_method_applicability import case, preconditions, verdict
    from spg.application import governed_obligations as admission
    repo, baseline, request, task, contract = subject
    revision, ir, inventory, proposal = case(mixed=True)
    plan = admission.validate_projection_candidate(proposal, revision, ir, inventory,
        source_contract="v3", owner_preconditions=preconditions(revision, ir, inventory),
        semantic_review=verdict(inventory, proposal))
    invalid = plan[1].model_copy(update={drift: uuid4() if drift == "work_reality_revision_id" else "different"})
    calls = []
    verifier = StaticProtectedContextVerifier(lambda: calls.append(True))
    with pytest.raises(ValueError, match="RESPONSIBILITY_SOURCE_MISMATCH"):
        verifier.verify_fulfillment_bindings(request, task, contract, repo, baseline,
            bindings=(plan[0],), fulfillment_bindings=(plan[0], invalid))
    assert calls == []


@pytest.mark.parametrize('disposition', ['SATISFIED', 'CONTRADICTED'])
def test_one_candidate_assessment_reused_across_fact_constraint_and_repository_policy(subject, disposition):
    from tests.test_c3_reviewed_fact_method_applicability import case, preconditions, verdict
    from spg.application import governed_obligations as admission
    from spg.domain.engineering_semantics import semantic_fact_reference
    from spg.domain.model_runtime import ModelUsage
    repo, baseline, request, task, contract = subject
    revision, ir, inventory, proposal = case(mixed=True)
    plan = admission.validate_projection_candidate(proposal, revision, ir, inventory,
        source_contract='v3', owner_preconditions=preconditions(revision, ir, inventory),
        semantic_review=verdict(inventory, proposal))
    current = plan[0].model_copy(update={'source_revision': baseline, 'work_constraint_indices': (0,)})
    future = plan[1].model_copy(update={'source_revision': baseline, 'work_constraint_indices': (0,)})
    constraint = request.protected_context_obligations[0].model_copy(update={
        'context_class': 'APPROVED_CONSTRAINT', 'semantic_key': 'greenfield-constraint:0',
        'source_ref': 'work-constraint:0', 'content': current.source_quote,
        'content_digest': sha256(current.source_quote.encode()).hexdigest()})
    policy = constraint.model_copy(update={'context_class': 'APPROVED_DECISION',
        'semantic_key': 'existing-policy', 'source_ref': 'repository:policy',
        'content': 'Company Home', 'content_digest': sha256(b'Company Home').hexdigest()})
    task.decision_context.protected_obligations = (constraint, policy)
    request = request.model_copy(update={'protected_context_obligations': (constraint, policy),
        'semantic_fact_obligations': (semantic_fact_reference(
            revision.engineering_semantic_facts[0], work_revision_id=revision.id),)})
    calls = []
    def generate(**kwargs):
        payload = json.loads(kwargs['input_text']); calls.append(payload)
        return SimpleNamespace(output_text=json.dumps({'checks': [{
            'context_class': o['context_class'], 'semantic_key': o['semantic_key'],
            'disposition': disposition, 'reason': 'Controlled exact-source inspection',
            'witnesses': [{'path': 'index.html', 'quote': 'Company Home'}],
        } for o in payload['protected_obligations']]}), provider=SimpleNamespace(value='test'),
            effective_model='test', request_id='test', usage=ModelUsage())
    runtime = SimpleNamespace(generate=generate, registry=SimpleNamespace(close=lambda: None))
    verifier = StaticProtectedContextVerifier(lambda: runtime)
    session = verifier.for_candidate(request, task, contract, repo, baseline,
        bindings=(current, future), receipt_recorder=None)
    fact_checks = session.verify_fulfillment_bindings(request, task, contract, repo, baseline,
        bindings=(current,), fulfillment_bindings=(current, future))
    projected = session.verify(request, task, contract, repo, baseline,
        obligations=(constraint, policy), fulfillment_bindings=(current, future))
    repeated = session.verify_fulfillment_bindings(request, task, contract, repo, baseline, bindings=(current,))
    assert len(calls) == 1
    assert len(calls[0]['protected_obligations']) == 2
    assert repeated == fact_checks
    assert all(row['coverage'] == ('COVERED' if disposition == 'SATISFIED' else 'UNVERIFIED')
               for row in (*fact_checks, *projected))
    assert projected[0]['source_ref'] == constraint.source_ref
    assert projected[1]['source_ref'] == policy.source_ref
    assert len(calls[0]['assigned_fulfillment_bindings']) == 2
    with pytest.raises(ValueError, match='BATCH_BASIS_MISMATCH'):
        session.verify(request.model_copy(update={'tree_identity': '0'*40}), task, contract,
                       repo, baseline, obligations=(constraint,))
    with pytest.raises(ValueError, match='NOT_ASSIGNED'):
        session.verify_fulfillment_bindings(request, task, contract, repo, baseline,
            bindings=(current.model_copy(update={'source_quote': 'changed'}),))


@pytest.mark.parametrize('disposition', ['SATISFIED', 'CONTRADICTED', 'UNVERIFIABLE'])
def test_owner_batch_reference_resolves_exact_identity_without_model_uuid_echo(subject, disposition):
    from spg.domain.model_runtime import ModelUsage
    repo,base,request,task,contract=subject
    payloads=[]
    def generate(**kwargs):
        payload=json.loads(kwargs['input_text']);payloads.append(payload)
        assert kwargs['output_schema']['$defs']['ReferencedCheck']['properties']['check_ref']['enum']==['c0']
        assert payload['protected_obligations'][0]['semantic_key']=='homepage'
        assert payload['protected_obligations'][0]['source_revision']==base
        return SimpleNamespace(output_text=json.dumps({'checks':[{
            'check_ref':payload['protected_obligations'][0]['check_ref'],
            'disposition':disposition,'reason':'Observed exact source under unchanged acceptance criteria',
            'witnesses':[{'path':'index.html','quote':'Company Home'}]}]}),
            provider=SimpleNamespace(value='test'),effective_model='test',request_id='test',usage=ModelUsage())
    runtime=SimpleNamespace(generate=generate,registry=SimpleNamespace(close=lambda:None))
    result=StaticProtectedContextVerifier(lambda:runtime).verify(request,task,contract,repo,base)
    assert len(payloads)==1
    assert result[0]['semantic_key']=='homepage' and result[0]['source_revision']==base
    assert result[0]['disposition']==disposition
    assert (result[0]['coverage']=='COVERED') is (disposition=='SATISFIED')
    assert result[0]['candidate_tree']==request.tree_identity


@pytest.mark.parametrize('change',['missing','duplicate','unknown','fake-witness','mixed-shape'])
def test_short_references_do_not_waive_coverage_or_witness_validation(subject, change):
    from spg.domain.model_runtime import ModelUsage
    repo,base,request,task,contract=subject
    c={'check_ref':'c0','disposition':'SATISFIED','reason':'Check exact implementation',
        'witnesses':[{'path':'index.html','quote':'Company Home'}]}
    rows=[c]
    if change=='missing':rows=[]
    elif change=='duplicate':rows=[c,c]
    elif change=='unknown':rows=[{**c,'check_ref':'c99'}]
    elif change=='fake-witness':rows=[{**c,'witnesses':[{'path':'index.html','quote':'Fabricated'}]}]
    else:rows=[{**c,'semantic_key':'homepage'}]
    calls=[]
    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(output_text=json.dumps({'checks':rows}),provider=SimpleNamespace(value='test'),
            effective_model='test',request_id='test',usage=ModelUsage())
    runtime=SimpleNamespace(generate=generate,registry=SimpleNamespace(close=lambda:None))
    with pytest.raises(ValueError):
        StaticProtectedContextVerifier(lambda:runtime).verify(request,task,contract,repo,base)
    assert len(calls)==2


def test_chinese_content_review_keeps_language_and_exact_source(subject):
    from spg.domain.model_runtime import ModelUsage
    repo,base,request,task,contract=subject
    task.objective='调整现有阅读页字号。'
    def generate(**kwargs):
        assert '新自然语言保持中文' in kwargs['instructions']
        assert 'Company Home' in kwargs['input_text']
        return SimpleNamespace(output_text=json.dumps({'checks':[{
            'check_ref':'c0','disposition':'UNVERIFIABLE','reason':'当前证据不能证明全部运行效果。','witnesses':[]}]}),
            provider=SimpleNamespace(value='test'),effective_model='test',request_id='test',usage=ModelUsage())
    runtime=SimpleNamespace(generate=generate,registry=SimpleNamespace(close=lambda:None))
    assert StaticProtectedContextVerifier(lambda:runtime).verify(request,task,contract,repo,base)[0]['coverage']=='UNVERIFIED'


@pytest.mark.parametrize('use_old_witness',[False, True])
def test_predecessor_is_comparison_only_and_cannot_prove_current_implementation(subject,use_old_witness):
    from spg.domain.model_runtime import ModelUsage
    repo,base,request,task,contract=subject
    comparison={'candidate_id':str(uuid4()),'candidate_revision':'a'*40,'candidate_tree':'b'*40,
        'comparison_only':True,'grants_current_pass_or_authority':False,
        'sources':{'index.html':{'sha256':'c'*64,'content':'Old report layout'}}}
    def generate(**kwargs):
        payload=json.loads(kwargs['input_text'])
        assert payload['comparison_candidates']==[comparison]
        assert payload['baseline_revision']==base
        quote='Old report layout' if use_old_witness else 'Company Home'
        return SimpleNamespace(output_text=json.dumps({'checks':[{
            'check_ref':'c0','disposition':'SATISFIED','reason':'Compare against exact earlier source',
            'witnesses':[{'path':'index.html','quote':quote}]}]}),provider=SimpleNamespace(value='test'),
            effective_model='test',request_id='test',usage=ModelUsage())
    runtime=SimpleNamespace(generate=generate,registry=SimpleNamespace(close=lambda:None))
    def run():return StaticProtectedContextVerifier(lambda:runtime).verify(request,task,contract,repo,base,
        comparison_candidates=(comparison,))
    if use_old_witness:
        with pytest.raises(ValueError,match='WITNESS_NOT_OBSERVED'):run()
    else:
        row=run()[0]
        assert row['candidate_tree']==request.tree_identity
        assert row['comparison_candidate_references']==[{k:v for k,v in comparison.items() if k!='sources'}]
        assert row['observed_source_digests']=={'index.html':sha256(b'<main>Company Home</main>').hexdigest()}


@pytest.mark.parametrize('change',[None,'unknown','duplicate','empty','requirements-only'])
def test_owner_source_passages_preserve_exact_proof_and_refuse_invalid_selection(subject,change):
    from spg.domain.model_runtime import ModelUsage
    repo,base,request,task,contract=subject
    calls=[]
    def generate(**kwargs):
        calls.append(kwargs)
        data=json.loads(kwargs['input_text']);passages=data['candidate_source_passages']
        assert 'candidate_sources' not in data
        path='README.md' if change=='requirements-only' else 'index.html'
        selected=[p['witness_ref'] for p in passages if p['path']==path]
        assert kwargs['output_schema']['$defs']['ReferencedCheck']['properties']['witness_refs']['items']['enum']==[p['witness_ref'] for p in passages]
        if change=='unknown':selected=['unobserved']
        elif change=='duplicate':selected=selected*2
        elif change=='empty':selected=[]
        return SimpleNamespace(output_text=json.dumps({'checks':[{'check_ref':'c0',
            'disposition':'SATISFIED','reason':'Actual implementation is selected','witness_refs':selected}]}),
            provider=SimpleNamespace(value='test'),effective_model='test',request_id='test',usage=ModelUsage())
    runtime=SimpleNamespace(generate=generate,registry=SimpleNamespace(close=lambda:None))
    def run():return StaticProtectedContextVerifier(lambda:runtime).verify(request,task,contract,repo,base)
    if change is None:
        row=run()[0]
        assert row['witnesses']==[{'path':'index.html','quote':'<main>Company Home</main>'}]
        assert row['observed_source_digests']['index.html']==sha256(b'<main>Company Home</main>').hexdigest()
    else:
        with pytest.raises(ValueError):run()
        assert len(calls)==2


def test_source_passages_cover_every_character_without_normalization():
    from spg.providers.protected_context_verifier import _source_passages
    source='\r\n'.join('第'+str(i)+'行' for i in range(25))+'\r\n  '
    passages=_source_passages({'src/display.js':source})
    assert ''.join(p['quote'] for p in passages)==source
    assert len({p['witness_ref'] for p in passages})==len(passages)
    assert [p['first_line'] for p in passages]==[1,9,17,25]
