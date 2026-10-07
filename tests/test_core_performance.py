"""Structural gates for bounded observation and read API work."""
import asyncio
import json
from pathlib import Path

from spg.infrastructure.performance import Observation, PerformanceMiddleware, _current, span
from spg.evaluation.production_trace import compact_trace_tables, safe, project_trace


def test_unmeasured_categories_are_unknown_not_invented_zero():
    observation = Observation()
    record = observation.record(route='/api/works/{work_id}', method='GET', status=200,total=1,size=20)
    assert 'model_provider' in record['unmeasured']
    assert 'model_provider' not in record['times_ms']


def test_spans_are_inclusive_and_request_local():
    observation = Observation();token=_current.set(observation)
    try:
        with span('projection'):
            with span('db'):pass
        assert observation.counts == {'db':1,'projection':1}
        assert observation.elapsed['projection'] >= observation.elapsed['db']
    finally:_current.reset(token)
    with span('db'):pass
    assert observation.counts['db']==1


def test_asgi_timing_records_stream_bytes_and_route_without_secrets(caplog):
    async def handler(scope, receive, send):
        scope['route']=type('Route',(),{'path':'/api/works/{work_id}'})()
        with span('projection'):pass
        await send({'type':'http.response.start','status':200,'headers':[]})
        await send({'type':'http.response.body','body':b'first','more_body':True})
        await send({'type':'http.response.body','body':b'end'})
    async def run():
        output=[]
        async def send(msg):output.append(msg)
        await PerformanceMiddleware(handler)({'type':'http','method':'GET','path':'/api/works/secret',
            'headers':[(b'authorization',b'Bearer credential')]},None,send)
        return output
    caplog.set_level('INFO',logger='spg.performance');output=asyncio.run(run())
    record=json.loads(caplog.records[-1].message.split('请求性能 ',1)[1])
    assert record['endpoint']=='/api/works/{work_id}' and record['response_bytes']==8
    assert 'credential' not in caplog.text and '/api/works/secret' not in caplog.text
    assert _current.get() is None
    assert any(k==b'x-watt-request-id' for k,v in output[0]['headers'])


def test_trace_summary_keeps_exact_identity_without_full_model_bodies():
    rows={'execution_steps':[{'id':'step','attempt_id':'attempt','kind':'INFERENCE',
        'request_payload':{'objective':'approved','hidden_large':'x'*100000},
        'result_payload':{'provider_observation':{'effective_model':'model','transport':{'elapsed_ms':12}},
            'secret':'do not expose','tool_calls':[{'large':'x'*100000}]}}]}
    compact=compact_trace_tables(rows)
    assert compact['execution_steps'][0]['id']=='step'
    assert compact['execution_steps'][0]['result_payload']['provider_observation']['transport']['elapsed_ms']==12
    assert len(json.dumps(compact)) < 1000
    assert len(rows['execution_steps'][0]['request_payload']['hidden_large'])==100000


def test_shared_trace_redaction_never_leaks_credentials_or_hidden_reasoning():
    shared={'credential':'secret','analysis':'private','content':'Bearer abc.def','password':'pw'}
    result=safe({'first':shared,'again':shared})
    assert result['first'] == result['again'] == {'content':'Bearer [已脱敏]'}


def test_trace_summary_preserves_qualified_candidate_and_unknown_metrics():
    trace=project_trace({'baseline_candidates':[{'id':'candidate','fingerprint':'exact','condition':'SEALED'}]},
        scene='case',purpose='same authority',detail=False)
    assert trace['candidate'][0]['fingerprint']=='exact'
    assert trace['advanced']=={} and trace['detail_level']=='summary'
    assert trace['units']==[]


def test_projection_memo_expires_before_authority_command():
    from spg.infrastructure.performance import projection_memo, projection_scope
    calls=[]
    class Owner:
        @projection_memo
        def read(self, identity):calls.append(identity);return len(calls)
    owner=Owner()
    @projection_scope
    def view():return owner.read('exact'),owner.read('exact')
    assert view()==(1,1)
    assert owner.read('exact')==2
    assert view()==(3,3)


def test_read_sets_do_not_replace_unknown_tables_or_command_reads():
    from types import SimpleNamespace
    from spg.infrastructure.persistence.projection_reads import rows_for,first_for
    table=SimpleNamespace(name='exact');session=SimpleNamespace(info={})
    assert rows_for(session,table,{'id':'x'}) is None
    session.info['watt_projection_rows']={'exact':[{'id':'x','state':'READY'}]}
    assert first_for(session,table,{'id':'x'})['state']=='READY'
    assert first_for(session,table,{'id':'absent'})=={}
    assert rows_for(session,SimpleNamespace(name='other'),{}) is None


def test_read_set_order_preserves_postgresql_null_and_mixed_tie_order():
    from types import SimpleNamespace
    from spg.infrastructure.persistence.projection_reads import rows_for
    table=SimpleNamespace(name='versions');session=SimpleNamespace(info={'watt_projection_rows':{'versions':[
        {'id':'b','version':1},{'id':'a','version':1},{'id':'n','version':None}]}})
    rows=rows_for(session,table,{},order=('version',),descending=True,ascending_ties=('id',))
    assert [r['id'] for r in rows]==['n','a','b']


def test_read_budget_bounds_composition_and_releases_after_failure():
    from spg.infrastructure.performance import ReadConcurrencyMiddleware
    async def run():
        active = peak = 0
        started = asyncio.Event()
        release = asyncio.Event()
        bypassed = []
        async def app(scope, receive, send):
            nonlocal active, peak
            if scope['method'] == 'POST' or scope['path'] == '/health':
                bypassed.append(scope['path'])
                return
            active += 1
            peak = max(peak, active)
            started.set()
            try:
                await release.wait()
                if scope.get('fail'):raise ValueError('read failed')
            finally:
                active -= 1
        middleware = ReadConcurrencyMiddleware(app, limit=1)
        scope = {'type':'http','method':'GET','path':'/api/experience/home'}
        first = asyncio.create_task(middleware({**scope,'fail':True},None,None))
        await started.wait()
        second = asyncio.create_task(middleware(scope,None,None))
        await middleware({**scope,'method':'POST'},None,None)
        await middleware({**scope,'path':'/health'},None,None)
        release.set()
        results = await asyncio.gather(first,second,return_exceptions=True)
        assert isinstance(results[0],ValueError) and results[1] is None
        assert peak == 1 and len(bypassed) == 2 and middleware.budget._value == 1
    asyncio.run(run())
