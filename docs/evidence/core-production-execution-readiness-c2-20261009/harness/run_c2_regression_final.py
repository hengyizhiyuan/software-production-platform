from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,subprocess,time
ROOT=Path('/data/watt/c2-execution-readiness-20261009');E=ROOT/'evidence';P=ROOT/'private'
IMAGE='watt-c2:88f1d98';IMAGE_ID='sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209';PG='watt-c2-postgres-20261009'
credentials=json.loads((P/'credentials.json').read_text())
assert subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',IMAGE],universal_newlines=True).strip()==IMAGE_ID
labels=['--label','watt.production=false','--label','watt.qualification=C2-execution-readiness']
for envname in ('c2-test.env', 'c2-migrate.env'):
    path=P/envname
    path.write_text(path.read_text().replace('3355b992e291da8188ec1ac9431332b32865322d','88f1d9805d3ed1aa779ed3c78902b193fae240f8'))
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
assert run('watt-c2-image-attest-final-20261009',['python','/opt/c2-build/attest_c2_image.py','--image-id',IMAGE_ID,'--output','/c2-evidence/runtime-image-attestation-final.json'])==0
command=['python','-m','pytest','-p','no:cacheprovider','-o','junit_family=legacy','tests/test_c2_workspace_preflight.py','tests/test_production_execution_runtime.py','tests/integration/test_c2_workspace_preflight_events.py','tests/integration/test_native_executor_runtime.py::test_production_worker_records_isolated_change_and_diff_evidence','tests/integration/test_native_executor_runtime.py::test_production_worker_verification_failure_cannot_claim_result_ready','tests/integration/test_native_executor_runtime.py::test_production_preflight_failure_keeps_exact_diagnostic_before_terminal','tests/test_c1_ecf_contract_compatibility.py','tests/test_guardian_assurance_adapter.py','tests/integration/test_c1_contract_continuity.py','--tb=short','--junitxml=/c2-evidence/final-c2-regression-default.xml']
result=run('watt-c2-regression-final-20261009',command,'c2-test.env','/qualification')
raise SystemExit(result)