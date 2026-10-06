"""Truth, privacy and lineage boundaries for the human Admin projection."""
from types import SimpleNamespace
from hashlib import sha256
import json
import pytest
from spg.evaluation.admin_projection import cockpit_projection, issue_projection, outcome_projection, version_comparison
from spg.evaluation.production_trace import safe, qualification_artifact, project_trace


def observation(version='v1', state='PASS', revision='current', policy='p'):
    return dict(id='case-run',case_id='case',case_version_id=version,title='新建官网',state=state,
                watt_revision=revision,policy_fingerprint=policy,cohorts=['REGRESSION'],created_at='2026-10-07T12:00:00Z')


def overview(revision='current',clusters=()):
    return dict(watt_revision=revision,quality=dict(clusters=list(clusters),runs=[]))


def test_cockpit_deduplicates_observations_without_faking_complete_current_qualification():
    p=cockpit_projection(overview(),[observation(),observation()])
    assert p['observed']==1 and p['qualified']==1
    p=cockpit_projection(overview(),[observation(state='UNKNOWN')])
    assert p['condition']=='资格不足'
    p=cockpit_projection(overview(),[observation(revision='old')])
    assert p['condition']=='资格不足' and '不能沿用旧版本' in p['briefing']
    assert cockpit_projection(overview(),[])['condition']=='数据不足'


def test_regression_requires_identical_case_version_and_policy():
    c=observation(state='FAIL');old=observation(revision='old')
    assert version_comparison([c],[old])[0]['kind']=='REGRESSION'
    for other in [observation(version='v2'),observation(policy='changed')]:
        assert version_comparison([c],[other])[0]['kind']=='NO_COMPARABLE_BASIS'
    p=cockpit_projection(overview(),[c,old])
    assert p['condition']=='发现回退' and p['regression_count']==1
    p=cockpit_projection(overview(),[c,observation(version='v2',revision='old')])
    assert '无法判断质量变化' in p['briefing']


def test_later_pass_does_not_close_historical_issue():
    c=dict(finding_code='MANAGED_GREENFIELD_CONTEXT_SOURCE_MISSING',stage='ECF',affected_cases=['case'],
           last_seen='2026-10-06',occurrence_count=8,closure_state='OPEN',regression_status='PERMANENT_CASE')
    i=issue_projection(c,[observation()])
    assert i['closure_state']=='OPEN' and i['requalified_case_runs']==['case-run']
    assert '仍待治理关闭' in i['repair_label'] and '8 次观测' in i['observation_label']
    assert cockpit_projection(overview(clusters=[c]),[observation()])['attention_count']==1


def test_negative_quality_pass_needs_explicit_safety_evidence():
    c={'state':'PASS','title':'Verification correctly blocks invalid code'}
    assert not outcome_projection(c)['safety_block_proven']
    c['evaluations']=[{'details':{'expected_safety_block':True}}]
    assert '错误生产被正确阻止' in outcome_projection(c)['production_label']
    c['state']='FAIL'
    assert '场景符合预期' not in outcome_projection(c)['production_label']


def test_hidden_reasoning_and_credentials_never_enter_either_trace_mode():
    x=safe(dict(reasoning_content='private-thought',nested={'api_key':'credential-secret','summary':'Bearer abc.secret token'},
                usage={'reasoning_tokens':25},url='postgresql+psycopg://user:password@host/db'))
    assert 'private-thought' not in json.dumps(x) and 'credential-secret' not in json.dumps(x)
    assert 'abc.secret' not in str(x) and 'user:password' not in str(x)
    assert x['usage']['reasoning_tokens']==25


def test_only_exact_checksum_qualification_artifact_may_be_read(tmp_path):
    root=tmp_path/'owner';q=root/'qualifications';q.mkdir(parents=True)
    p=q/'proof.json';p.write_text('{"proof":true}')
    settings=SimpleNamespace(owner_runtime_store_root=root)
    reference=lambda path,digest:f'evidence:{path}:sha256:{digest}'
    h=sha256(p.read_bytes()).hexdigest()
    assert qualification_artifact(settings,reference(p,h))[1]=={'proof':True}
    assert qualification_artifact(settings,reference(p,'0'*64)) is None
    outside=tmp_path/'private.json';outside.write_bytes(p.read_bytes())
    (q/'symlink.json').symlink_to(outside)
    assert qualification_artifact(settings,reference(outside,h)) is None
    assert qualification_artifact(settings,reference(q/'symlink.json',h)) is None


def trace_tables():
    return dict(production_work_units=[dict(id='a',node_id='A',plan_revision_id='plan',source_baseline_id='base',objective='主页',condition='SATISFIED',completion_contract={}),
        dict(id='b',node_id='B',plan_revision_id='plan',source_baseline_id='resultA',parent_baseline_ids=['resultA'],objective='导航',condition='QUEUED',completion_contract={})],
        plan_revisions=[dict(id='plan',graph={'nodes':[dict(node_id='A',objective='主页',dependency_ids=[]),dict(node_id='B',objective='导航',dependency_ids=['A'])]})],
        production_snapshots=[dict(id='base',repository_revision='exact-base'),dict(id='resultA',repository_revision='exact-resultA')],
        execution_attempts=[dict(id='attempt',work_unit_id='a')],
        execution_steps=[dict(id='model',attempt_id='attempt',session_id='session',kind='INFERENCE',condition='COMPLETED',sequence=1,started_at='2026-10-07T01:00:00Z',finished_at='2026-10-07T01:00:02Z',
            request_payload={'objective':'governed objective'},result_payload={'summary':'observable output','reasoning':'hidden','provider_observation':{'effective_model':'real-model','provider_identity':'real-provider','usage':{'input_tokens':100,'output_tokens':20},'transport':{'elapsed_ms':2000}}})],
        execution_events=[dict(id=str(i),pwu_id='a',event_type=e,created_at=f'2026-10-07T01:00:{i:02d}Z') for i,e in enumerate(['NativeExecutionQueued','NativeExecutionStarted','NativeExecutionPaused','NativeExecutionResumed','ExecutionWorkerCompleted'])])


def test_trace_uses_exact_dependency_output_not_root_revision_and_preserves_transitions():
    p=project_trace(trace_tables(),scene='网站',purpose='验证',basis={'mode':'HISTORICAL_QUALIFICATION'})
    a,b=p['units'];assert a['source_revision']=='exact-base' and b['source_revision']=='exact-resultA'
    assert b['dependencies']==['A'] and b['dependency_names']==['主页']
    assert {'暂停执行','恢复执行','执行完成'}<=set(e['title'] for e in a['events'])
    assert a['metrics']['input_tokens']==100 and a['metrics']['model_seconds']==2
    assert a['metrics']['cpu'] is None and b['metrics']['model_call_count'] is None
    assert p['model_calls'][0]['provider']=='real-provider' and 'hidden' not in json.dumps(p)
    assert p['diagnostic_owners'][7]['events']==[e for e in p['timeline'] if e['owner']=='EXECUTION']


def test_missing_dependent_snapshot_never_borrows_root_baseline():
    t=trace_tables();t['production_snapshots']=t['production_snapshots'][:1]
    t['work_source_bases']=[{'source_revision':'current-HEAD','source_baseline_id':'base'}]
    p=project_trace(t,scene='test',purpose='test')
    assert p['units'][1]['source_revision'] is None


def test_trace_never_fabricates_unobserved_input_conversation_search_or_deployment():
    p=project_trace({},scene='synthetic qualification',purpose='fixture motive',case={'state':'PASS'})
    assert p['first_human_input'] is None and not p['conversation'] and not p['deployment']
    assert '不能判断' in p['search_note'] and '不能宣称已上线' in p['deployment_note']
