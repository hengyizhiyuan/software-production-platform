"""Universal discovery, incomplete lineage and bounded read regressions."""
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, insert, update, event, text
import pytest
from spg.config import Settings
from spg.api.admin import install_admin
from spg.api.authority import install_authority_boundary
from spg.infrastructure.persistence import metadata
from spg.evaluation.work_registry import WorkRegistryService
from spg.evaluation.production_trace import ProductionTraceService
from spg.evaluation.service import QualityService
from tests.integration.test_work_delivery import clean_schema
from tests.integration.test_software_delivery import produce

pytestmark=pytest.mark.postgresql


def simple(db,condition='READY',owner='human:owner',title='普通真实 Work'):
    pid,wid=uuid4(),uuid4()
    with db.engine.begin() as c:
        c.execute(insert(metadata.tables['software_products']).values(id=pid,owner_id=owner,name='产品',lifecycle='ACTIVE'))
        c.execute(insert(metadata.tables['product_works']).values(id=wid,product_id=pid,work_mode='LONG_LIVED_STEERING',raw_user_requirement=title,refined_title=title,condition=condition,constraints=[],tags=[]))
    return wid


def trace(db,wid,settings=None,**kwargs):
    settings=settings or Settings()
    return ProductionTraceService(db,settings,QualityService(db,settings)).entity_trace('work',wid,**kwargs)


@pytest.mark.parametrize('condition,pulse,expected',[
    ('DRAFT',None,'COMMUNICATING'),('READY',None,'PREPARING'),
    ('READY',{'active':True,'stop_reason':'BLOCKED'},'BLOCKED'),
    ('AWAITING_APPROVAL',None,'WAITING_HUMAN'),('DISCARDED',None,'STOPPED')])
def test_partial_no_quality_no_candidate_states_remain_discoverable_and_traceable(postgres_database,condition,pulse,expected,tmp_path):
    db=postgres_database;wid=simple(db,condition)
    pulses={str(wid):pulse} if pulse else {}
    registry=WorkRegistryService(db);result=registry.list('human:owner',pulses=pulses)
    row=next(r for r in result['items'] if r['work_id']==str(wid))
    assert row['state']==expected and row['candidate_id'] is None
    t=trace(db,wid,Settings(native_executor_production_environment_store_root=tmp_path/'absent'),work=row,detail=False)
    assert t['work']['state']==expected and not t['candidate']
    assert t['diagnosis']['quality_label']!='PASS' and '尚未进入执行' in t['story']['flow_ended']
    assert not (tmp_path/'absent').exists()
    assert str(wid) in str(t['source_references'])


def test_owner_scope_pagination_query_count_and_latest_meaningful_activity(postgres_database,monkeypatch):
    db=postgres_database;ids=[simple(db) for _ in range(4)];foreign=simple(db,owner='human:another')
    with db.engine.begin() as c:c.execute(update(metadata.tables['product_works']).where(metadata.tables['product_works'].c.id==ids[0]).values(updated_at=datetime.now(timezone.utc)+timedelta(seconds=5)))
    def forbidden(*a,**k):raise AssertionError('List must not hydrate Trace or scan filesystem')
    monkeypatch.setattr(ProductionTraceService,'entity_trace',forbidden);monkeypatch.setattr(Path,'glob',forbidden)
    queries=[]
    def count(*a):queries.append(a[2])
    event.listen(db.engine,'before_cursor_execute',count)
    try:r=WorkRegistryService(db).list('human:owner',limit=2)
    finally:event.remove(db.engine,'before_cursor_execute',count)
    assert len(queries)==2 and r['total']==4 and r['next_offset']==2
    assert r['items'][0]['work_id']==str(ids[0]) and str(foreign) not in str(r)
    second=WorkRegistryService(db).list('human:owner',limit=2,offset=2)
    assert not set(x['work_id'] for x in r['items'])&set(x['work_id'] for x in second['items'])
    assert WorkRegistryService(db).list('human:owner',filter='WAITING')['total']==0


def test_work_routes_keep_owner_auth_and_reject_unbounded_queries(postgres_database):
    db=postgres_database;wid=simple(db)
    s=Settings(auth_mode='required',operator_token='private-test-owner-secret-at-least32')
    app=FastAPI();install_authority_boundary(app,database=db,settings=s);install_admin(app,db,s)
    with TestClient(app) as c:
        assert c.get('/api/admin/works').status_code==401
        assert c.get(f'/api/admin/traces/work/{wid}').status_code==401
        c.post('/auth/session',json={'token':s.operator_token.get_secret_value()})
        assert c.get('/api/admin/works?limit=101').status_code==422
        assert c.get('/api/admin/works?filter=UNKNOWN').status_code==409
        assert c.get('/api/admin/works').json()['total']==1
        assert c.get(f'/api/admin/traces/work/{wid}?view=summary').status_code==200
        assert c.get(f'/api/admin/traces/work/{wid}?view=unknown').status_code==409


def enqueue(db,wid,condition):
    with db.engine.begin() as c:
        binding=c.execute(select(metadata.tables['work_runtime_bindings']).where(metadata.tables['work_runtime_bindings'].c.work_id==wid).order_by(metadata.tables['work_runtime_bindings'].c.cycle_number.desc())).mappings().first()
        attempt=c.execute(select(metadata.tables['execution_attempts']).where(metadata.tables['execution_attempts'].c.work_unit_id==binding['work_unit_id'])).mappings().first()
        now=datetime.now(timezone.utc)
        c.execute(insert(metadata.tables['executor_queue']).values(id=uuid4(),command_id=uuid4(),request_digest='f'*64,actor_identity='human:test',work_id=wid,pwu_id=binding['work_unit_id'],attempt_id=attempt['id'],grant_revision=1,fairness_group=str(wid),priority=0,condition=condition,required_capabilities=[],required_provider_profile='test',required_resource_profile='test',enqueued_at=now,available_at=now))


@pytest.mark.parametrize('kind', ['candidate','active','failed','completed'])
def test_execution_candidate_and_historical_completion_are_traceable(postgres_database,tmp_path,kind):
    db=postgres_database
    service,wid,delivery,_=produce(db,tmp_path,failing=kind=='failed',authorize_candidate=kind=='completed',set_delivery_target=False)
    # Completion is an owner fact; establish the immediate bounded Work mode
    # for the committed historical result, not a guessed terminal UI flag.
    with db.engine.begin() as c:
        c.execute(update(metadata.tables['product_works']).where(metadata.tables['product_works'].c.id==wid).values(work_mode='IMMEDIATE_PRODUCTION'))
    if kind in {'failed','active'}:enqueue(db,wid,'FAILED' if kind=='failed' else 'EXECUTING')
    row=WorkRegistryService(db).get('human:owner',wid)
    assert row['state']=={'candidate':'REVIEWING','active':'RUNNING','failed':'FAILED','completed':'COMPLETED'}[kind]
    t=trace(db,wid,work=row)
    assert t['units'] and t['timeline'] and t['advanced']['owners']['execution_attempts']
    if kind=='failed':
        # A previous design Candidate is historical; code PWU failure is still
        # exposed with the exact failed execution and no code result Candidate.
        assert any(e['detail'].get('condition')=='FAILED' for e in t['timeline'] if e['source_ref'].startswith('executor_queue:'))
    else:assert t['candidate']
    assert t['diagnosis']['quality_label']==row['state_label']


def test_shared_interaction_does_not_pull_sibling_work_or_unrelated_human_turn(postgres_database):
    db=postgres_database;a=simple(db,title='第一个目标');b=simple(db,title='第二个目标')
    with db.engine.begin() as c:
        iid=uuid4();c.execute(insert(metadata.tables['product_interactions']).values(id=iid,created_by='human:owner',updated_by='human:owner',condition='OPEN',current_work_id=a))
        for number,wid in enumerate([a,b],1):
            c.execute(insert(metadata.tables['interaction_records']).values(id=uuid4(),interaction_id=iid,sequence=number,actor='HUMAN',source='test',content='第一个目标' if wid==a else '不属于这个 Work 的秘密',content_fingerprint=str(wid),supporting_references=[],work_focus_id=wid))
    t=trace(db,a)
    assert t['first_human_input']=='第一个目标'
    assert '不属于这个 Work 的秘密' not in str(t) and str(b) not in str(t['advanced'])
