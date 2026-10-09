"""Targeted supplemental fixture correction; baked application source unchanged."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
from uuid import UUID
import json,os,subprocess,time,sys,xml.etree.ElementTree as ET
ROOT=Path('/data/watt/c3-semantic-convergence-20261009');P=ROOT/'private';E=ROOT/'evidence'
freeze=json.loads((ROOT/'frozen-inputs.json').read_text())
for name,expected in freeze['control_harness_sha256'].items():
    assert sha256((ROOT/name).read_bytes()).hexdigest()==expected,('frozen harness mismatch',name)
build=json.loads((E/'build.json').read_text());assert build['exit_code']==0
IMAGE=build['image']['Id'];data=json.loads(subprocess.check_output(['docker','image','inspect',IMAGE],universal_newlines=True))[0]
assert data['Id']==IMAGE and data['Config']['Labels']['org.opencontainers.image.revision']==build['sources']['watt']['revision']=='390fa22ec24cbab33f7feeeef96f0dfec9ce22f2'
image_env=dict(v.split('=',1) for v in data['Config']['Env'] if '=' in v)
assert image_env['PYTHONPATH']=='/opt/c3-owners/guardian/src:/opt/c3-owners/ecf/src:/opt/c3-test-deps'
assert not any(image_env.get(k) for k in ('SPG_DEEPSEEK_API_KEY','SPG_NATIVE_EXECUTOR_DEEPSEEK_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY'))
actual_imports=json.loads((E/'final-image-regression/actual-imports.json').read_text());assert actual_imports['status']=='PASS' and actual_imports['caller_observed_image_id']==IMAGE
manifest=json.loads((ROOT/'final-image-c1-supplemental-test-input.json').read_text())
test_source=ROOT/'test-inputs/c1-constraint-identity-fixture.py'
assert sha256(test_source.read_bytes()).hexdigest()==manifest['supplemental_test_source']['sha256']
assert manifest['application_revision']==build['sources']['watt']['revision']
out=E/'final-image-regression-c1-fixture-retry';assert not out.exists();out.mkdir();os.chown(str(out),10001,10001)
envfile=P/'final-image-regression.env';assert envfile.is_file();creds=json.loads((P/'credentials.json').read_text())
def sanitize(text):
    for value in creds.values():
        if isinstance(value,str) and value:text=text.replace(value,'[REDACTED]')
    return text
common=['--network','container:watt-c3-postgres-20261009','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,exec,nosuid,size=512m','--memory','1536m','--cpus','1','--label','watt.production=false','--label','watt.qualification=C3-final-image-supplemental-fixture','--env-file',str(envfile),'--mount','type=bind,src='+str(out)+',dst=/c3-evidence']
groups=[{'name':'c1-constraint-identity','supplemental':True,'nodes':['tests/integration/test_c1_contract_continuity.py::test_native_rejects_binding_loss_drift_and_injection[work-constraint_identity]','tests/integration/test_c1_contract_continuity.py::test_native_rejects_binding_loss_drift_and_injection[steering-constraint_identity]']},{'name':'c3-carrier','nodes':['tests/integration/test_c3_fulfillment_receipts.py']},{'name':'c2-pg-preflight','nodes':['tests/integration/test_c2_workspace_preflight_events.py']}]
for group in groups:
    name='watt-c3-final-supplement-'+group['name']+'-20261009'
    fixture_tmp=P/(name+'-fixture-tmp');assert not fixture_tmp.exists();fixture_tmp.mkdir(mode=0o700);os.chown(str(fixture_tmp),10001,10001)
    mount=['--mount','type=bind,src='+str(fixture_tmp)+',dst=/c3-private-fixture']
    if group.get('supplemental'):mount+=['--mount','type=bind,src='+str(test_source)+',dst=/qualification/'+manifest['supplemental_test_source']['repository_path']+',readonly']
    command=['python','-m','pytest','--basetemp=/c3-private-fixture/tests','-p','no:cacheprovider','-o','junit_family=legacy']+group['nodes']+['--tb=short','--junitxml=/c3-evidence/'+group['name']+'.xml']
    args=['docker','run','--name',name]+common+mount+['--workdir','/qualification',IMAGE]+command
    started=datetime.now(timezone.utc).isoformat();start=time.monotonic();raw=P/(name+'.raw.log')
    with raw.open('x') as stream:
        os.fchmod(stream.fileno(),0o600);result=subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT)
    (out/(group['name']+'.log')).write_text(sanitize(raw.read_text(errors='replace')))
    xml=out/(group['name']+'.xml');counts={'tests':0,'failures':0,'errors':0,'skipped':0}
    if xml.exists():
        xml.write_text(sanitize(xml.read_text(errors='replace')))
        for suite in ET.parse(xml).iter('testsuite'):
            for key in counts:counts[key]+=int(suite.get(key,'0'))
    counts['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped']
    receipt={'schema':'c3-final-image-targeted-fixture-regression-v1','sources':build['sources'],'image_id':IMAGE,'application_source_overlay':False,'pythonpath':image_env['PYTHONPATH'],'actual_imports_attestation':'../final-image-regression/actual-imports.json','supplemental_test_source':manifest['supplemental_test_source'] if group.get('supplemental') else None,'test_source_role':'single supplemental test-file correction' if group.get('supplemental') else 'original baked test inputs','command':command,'container_name':name,'started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),'wall_seconds':time.monotonic()-start,'exit_code':result.returncode,'counts':counts,'database_name':'c1_contract_continuity','database_configuration_key':'SPG_TEST_DATABASE_URL','log_and_xml_sanitized':True,'live_model_calls':0,'real_ai_work_created':0,'fixture_work_mutations_only':True,'harness_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'private_fixture_basetemp_persisted':str(fixture_tmp),'meaning':'exact installed final application image; supplemental tests distinguished; not live AI Work'}
    owner_files={}
    for file in fixture_tmp.rglob('guardian/results/*.json'):
        assert file.is_file() and not file.is_symlink() and file.stat().st_size<=4*1024*1024
        result_payload=json.loads(file.read_text());request_id=str(UUID(result_payload['request_id']));request=file.parent.parent/'requests'/(request_id+'.json')
        assert request.is_file() and not request.is_symlink() and request.stat().st_size<=4*1024*1024
        request_payload=json.loads(request.read_text());assert request_payload['request_id']==request_id
        assert result_payload['contract_version']==request_payload['contract_version']=='watt-guardian-software-assurance-v1'
        owner_files[file.relative_to(fixture_tmp).as_posix()]={'request_id':request_id,'actual_result':result_payload,'actual_request':request_payload,'private_result_path':str(file),'private_request_path':str(request)}
    if owner_files:
        target=out/(group['name']+'-guardian-owner-records.json');target.write_text(sanitize(json.dumps({'schema':'c3-scoped-final-image-guardian-fixture-owner-records-v1','sources':build['sources'],'image_id':IMAGE,'container':name,'fixture_only':True,'records':owner_files},indent=2))+'\n');receipt['guardian_owner_records']=target.name
    (out/(group['name']+'-receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'group':group['name'],'exit_code':result.returncode,'counts':counts,'wall_seconds':receipt['wall_seconds']}),flush=True)
    if result.returncode or counts['skipped'] or counts['tests']==0:sys.exit(result.returncode or 2)