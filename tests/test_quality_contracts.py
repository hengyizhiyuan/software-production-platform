from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4
import pytest
from pydantic import ValidationError
from spg.config import Settings
from spg.evaluation.contracts import *
from spg.evaluation.campaign_worker import assert_isolated_database
from spg.evaluation.operations import host_observation
from spg.evaluation.catalog import definitions, recipes


def ev(kind, result, stage=None):
    return Evaluation(evaluator=kind, outcome=result, evidence_refs=('owner:exact',), evaluator_version='1', stage=stage)

@pytest.mark.parametrize('subjective', [Evaluator.HUMAN, Evaluator.LLM])
def test_preference_cannot_override_negative_or_missing_oracle(subjective):
    assert objective_verdict((ev(Evaluator.DETERMINISTIC,'FAIL'),ev(subjective,'PASS'))) == 'FAIL'
    assert objective_verdict((ev(subjective,'PASS'),)) == 'UNKNOWN'

@pytest.mark.parametrize('owner', [Evaluator.RUNTIME,Evaluator.GUARDIAN])
def test_objective_blocker_cannot_be_offset(owner):
    assert objective_verdict((ev(Evaluator.DETERMINISTIC,'PASS'),ev(owner,'BLOCKED'))) == 'BLOCKED'


def test_divergence_is_observed_not_invented():
    d=earliest_divergence((ev(Evaluator.DETERMINISTIC,'FAIL'),ev(Evaluator.LLM,'FAIL',Stage.WIC)))
    assert d['stage'] is None and d['certainty']=='UNKNOWN'
    d=earliest_divergence((ev(Evaluator.RUNTIME,'FAIL',Stage.EXECUTION),ev(Evaluator.DETERMINISTIC,'FAIL',Stage.ECF)))
    assert d['stage']=='ECF' and not d['earlier_stages_proven']


def test_experiment_rejects_undeclared_or_fake_differences():
    kw=dict(case_id=uuid4(),name='test',rationale='known difference',variants=(
        Variant(key='a',label='A',model='same',provider='p',policy={'n':1}),
        Variant(key='b',label='B',model='same',provider='p',policy={'n':2})))
    assert ExperimentRequest(**kw,changed_variables=('policy',))
    with pytest.raises(ValidationError):ExperimentRequest(**kw,changed_variables=('model',))

@pytest.mark.parametrize('test_url,code',[
    ('postgresql+psycopg://u:p@db/prod','QUALITY_CANNOT_USE_PRODUCTION_DATABASE'),
    ('postgresql+psycopg://u:p@db/random','QUALITY_TEST_DATABASE_NOT_EXPLICIT')])
def test_runner_never_uses_production_database(test_url,code):
    with pytest.raises(QualityError,match=code):assert_isolated_database(Settings(database_url='postgresql+psycopg://u:p@db/prod',quality_test_database_url=test_url))


def test_host_metrics_unknown_and_real_delta(tmp_path):
    proc=tmp_path/'proc';proc.mkdir();(proc/'net').mkdir()
    s=Settings(admin_host_proc=proc,admin_host_network=proc / "net",admin_host_data=tmp_path/'absent',admin_node_id='i-exact')
    assert host_observation(s)['memory'] is None
    (proc/'stat').write_text('cpu 100 0 50 800 50 0 0 0 10 0\ncpu0 0\n')
    (proc/'meminfo').write_text('MemTotal: 1000 kB\nMemAvailable: 400 kB\n')
    (proc/'net/dev').write_text('head\nhead\neth0: 100 0 0 0 0 0 0 0 200 0\n')
    (proc/'uptime').write_text('3600 100\n')
    at=datetime.now(UTC);first=host_observation(s,observed_at=at)
    assert first['cpu_percent'] is None and first['cpu_count']==1
    assert first['memory']['used_bytes']==600*1024 and first['disk'] is None
    (proc/'stat').write_text('cpu 130 0 70 850 50 0 0 0 10 0\ncpu0 0\n')
    (proc/'net/dev').write_text('head\nhead\neth0: 200 0 0 0 0 0 0 0 240 0\n')
    second=host_observation(s,first,observed_at=at+timedelta(seconds=10))
    assert second['cpu_percent']==50 and second['network']['eth0']['rx_bytes_per_second']==10


def test_catalog_is_bounded_and_all_selected_oracles_exist():
    root=Path(__file__).resolve().parents[1]
    assert len(definitions())==15
    for r in recipes().values():
        if not r.selector:continue
        path,*functions=r.selector.split('::')
        assert (root/path).is_file()
        if functions:assert 'def '+functions[0]+'(' in (root/path).read_text()


def test_llm_judgment_records_exact_provider_without_objective_override():
    from types import SimpleNamespace
    from spg.evaluation.judgment import evaluate
    from spg.domain.model_runtime import ModelProvider
    class Model:
        def generate(self,**kw):
            assert kw['purpose'].value=='QUALITY_EVALUATION'
            assert 'Never overrule' in kw['instructions']
            return SimpleNamespace(output_text='{"outcome":"PASS","confidence":0.6,"rationale":"bounded opinion"}',provider=ModelProvider.DEEPSEEK,effective_model='actual',requested_model='requested',request_id='request-exact')
    e=evaluate(Settings(),case_run_id=uuid4(),case_definition={'cohorts':['GOLDEN'],'motive':'x','invariants':['x']},observed_results=[],model_runtime=Model())
    assert e.evaluator==Evaluator.LLM and e.details['model']=='actual' and not e.details['objective_override']
    assert objective_verdict((e,))=='UNKNOWN'


def test_canonical_compose_has_single_bounded_quality_tmpfs():
    import os, json, shutil, subprocess
    if not shutil.which('docker'):pytest.skip('Docker Compose is required for canonical deployment validation')
    env=dict(os.environ,SPG_POSTGRES_PASSWORD='fixture-only',SPG_OPERATOR_TOKEN='fixture-only-owner-token-32-characters',
        SPG_DEEPSEEK_API_KEY='fixture-only',SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN='fixture-only',WATT_GITEA_PASSWORD='fixture-only',
        DOCKER_GID='999',WATT_REVISION='d'*40,WATT_NODE_ID='i-fixture',WATT_NODE_REGION='cn-wulanchabu',WATT_NODE_HOSTNAME='fixture')
    out=subprocess.run(['docker','compose','-f','deploy/cloud-worker/docker-compose.yml','--profile','quality','config','--format','json'],env=env,capture_output=True,text=True,check=True)
    service=json.loads(out.stdout)['services']['quality-runner']
    assert len(service['tmpfs'])==1 and service['tmpfs'][0].startswith('/tmp:') and 'size=' in service['tmpfs'][0]
    assert service['read_only'] and service['mem_limit']<=1073741824
    assert not any(v.get('source')=='/var/run/docker.sock' for v in service['volumes'])
