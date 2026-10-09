from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,subprocess,time
ROOT=Path('/data/watt/c2-execution-readiness-20261009');E=ROOT/'evidence';P=ROOT/'private'
IMAGE='watt-c2:3355b99';IMAGE_ID='sha256:6ecaf8f204d7503278671270919d2b5331ea437a016133f3c2c4b56821834b45';PG='watt-c2-postgres-20261009'
credentials=json.loads((P/'credentials.json').read_text())
assert subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',IMAGE],universal_newlines=True).strip()==IMAGE_ID
labels=['--label','watt.production=false','--label','watt.qualification=C2-execution-readiness']
for name,database in [('c2-migrate.env','spg_c2_qualification_20261009'),('c2-test.env','c1_contract_continuity')]:
    path=P/name;assert not path.exists()
    url='postgresql+psycopg://'+credentials['database_user']+':'+credentials['database_password']+'@127.0.0.1:5432/'+database
    env={'SPG_DATABASE_URL':url,'SPG_TEST_DATABASE_URL':url,'SPG_RUNTIME_PROFILE':'c2-execution-readiness-20261009','SPG_RUNTIME_REVISION':'3355b992e291da8188ec1ac9431332b32865322d','PYTHONPATH':'/opt/c2-owners/guardian/src:/opt/c2-owners/ecf/src:/opt/c2-test-deps:/qualification','C1_APPLICATION_REVISION':'3355b992e291da8188ec1ac9431332b32865322d','C1_GUARDIAN_REVISION':'6b974748df22d84b88f6908ea8ee90a9752fd183','C1_ECF_REVISION':'5aa4f8833c359c15bd059eda5972aa3915bcc18c','C1_EVIDENCE_OUTPUT':'/c2-evidence/exact-contract-chain'}
    with path.open('x') as stream:
        os.fchmod(stream.fileno(),0o600)
        for key,value in env.items():stream.write(key+'='+value+'\n')
def run(name,command,env_file=None,workdir='/app'):
    assert subprocess.run(['docker','inspect',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
    args=['docker','run','--name',name,'--network','container:'+PG,'--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','1536m','--cpus','1.0','--pids-limit','256']+labels+['--mount','type=bind,src='+str(E)+',dst=/c2-evidence','--workdir',workdir]
    if env_file:args+=['--env-file',str(P/env_file)]
    start=datetime.now(timezone.utc).isoformat();began=time.monotonic()
    raw=P/(name+'.raw.log')
    with raw.open('x') as stream:
        os.fchmod(stream.fileno(),0o600)
        result=subprocess.run(args+[IMAGE]+command,stdout=stream,stderr=subprocess.STDOUT)
    safe=raw.read_text(errors='replace')
    for value in credentials.values():
        if isinstance(value,str) and len(value)>20:safe=safe.replace(value,'[REDACTED]')
    (E/(name+'.log')).write_text(safe)
    data=json.loads(subprocess.check_output(['docker','inspect',name],universal_newlines=True))[0]
    receipt={'name':name,'container_id':data['Id'],'image_id':data['Image'],'actual_user':data['Config']['User'],'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-began,'exit_code':result.returncode,'command':command,'network_mode':data['HostConfig']['NetworkMode'],'mounts':data['Mounts'],'database_name':'c1_contract_continuity' if env_file=='c2-test.env' else 'spg_c2_qualification_20261009','model_calls':0,'source_overlay':False,'docker_socket':False}
    (E/(name+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    for xml in E.glob('*.xml'):
        content=xml.read_text()
        for value in credentials.values():
            if isinstance(value,str) and len(value)>20:content=content.replace(value,'[REDACTED]')
        xml.write_text(content)
    print(json.dumps({'name':name,'exit_code':result.returncode,'elapsed_seconds':receipt['elapsed_seconds']}),flush=True)
    return result.returncode
assert run('watt-c2-image-attest-20261009',['python','/opt/c2-build/attest_c2_image.py','--image-id',IMAGE_ID,'--output','/c2-evidence/runtime-image-attestation.json'])==0
assert run('watt-c2-migrate-20261009',['python','-m','alembic','upgrade','head'],'c2-migrate.env')==0
version=subprocess.check_output(['docker','exec',PG,'psql','-U',credentials['database_user'],'-d','spg_c2_qualification_20261009','-At','-c','select version_num from alembic_version'],universal_newlines=True).strip()
(E/'migration.json').write_text(json.dumps({'database':'spg_c2_qualification_20261009','version':version,'captured_at_utc':datetime.now(timezone.utc).isoformat(),'production_database_modified':False},indent=2)+'\n')
assert version=='20261007_72'
command=['python','-m','pytest','-p','no:cacheprovider','-o','junit_family=legacy','tests/test_c2_workspace_preflight.py','tests/test_production_execution_runtime.py','tests/integration/test_c2_workspace_preflight.py','tests/integration/test_native_executor_runtime.py::test_production_worker_records_isolated_change_and_diff_evidence','tests/integration/test_native_executor_runtime.py::test_production_worker_verification_failure_cannot_claim_result_ready','tests/integration/test_native_executor_runtime.py::test_production_preflight_failure_keeps_exact_diagnostic_before_terminal','tests/test_c1_ecf_contract_compatibility.py','tests/test_guardian_assurance_adapter.py','tests/integration/test_c1_contract_continuity.py','--tb=short','--junitxml=/c2-evidence/final-c2-regression.xml']
result=run('watt-c2-regression-20261009',command,'c2-test.env','/qualification')
raise SystemExit(result)