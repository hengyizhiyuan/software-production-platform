from types import SimpleNamespace
from uuid import uuid4
import json
import subprocess

import pytest
from spg.providers.protected_context_verifier import StaticProtectedContextVerifier
from spg.domain.production_intelligence import ProtectedContextObligation
from spg.domain.verification import VerificationCapabilityRequest, VerificationCapabilityResult, VerificationEvidence, VerificationResultValue
from spg.application.verification import _project_decision_context_evidence
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
