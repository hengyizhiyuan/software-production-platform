from pathlib import Path
from datetime import datetime,timezone
import json,os,subprocess
from hashlib import sha256
ROOT=Path('/data/watt/c3-semantic-convergence-20261009');E=ROOT/'evidence';P=ROOT/'private'
freeze=json.loads((ROOT/'frozen-inputs.json').read_text())
for name,expected in freeze['control_harness_sha256'].items():
    assert sha256((ROOT/name).read_bytes()).hexdigest()==expected, ('control harness identity mismatch',name)
build=json.loads((E/'build.json').read_text());assert build['exit_code']==0;IMAGE_ID=build['image']['Id']
assert not (E/'normal-entry-state.json').exists(),'Preserve state; never recreate Work'
with (ROOT/'worker_root_probe.py').open() as source:
    result=subprocess.run(['docker','exec','-i','watt-c3-worker-20261009','python','-'],stdin=source,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
assert result.returncode==0,'Worker root probe failed; no Work created'
receipt=json.loads(result.stdout);(E/'worker-root-preflight.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'actual_worker_root_preflight':'PASS','uid':10001,'write_probe_removed':True}),flush=True)
credential=P/'driver-credentials.json';os.chown(str(credential),0,10001);os.chmod(str(credential),0o640)
for name in ('original-g0-input.json','driver-runtime-identity.json'):os.chmod(str(E/name),0o644)
command=['docker','run','--name','watt-c3-normal-entry-validated-20261009','--network','watt-c3-control-20261009','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,nosuid,nodev,size=64m,mode=1777','--memory','256m','--cpus','0.5','--pids-limit','64','--label','watt.production=false','--label','watt.qualification=C3-semantic-convergence','--mount','type=bind,src='+str(ROOT/'c3_normal_entry.py')+',dst=/control/c3_normal_entry.py,readonly','--mount','type=bind,src='+str(credential)+',dst=/control/private.json,readonly','--mount','type=bind,src='+str(E)+',dst=/evidence',IMAGE_ID,'python','/control/c3_normal_entry.py','--base-url','http://watt-c3-api-20261009:8000','--identity-path','/evidence/driver-runtime-identity.json','--credentials-file','/control/private.json','--input-file','/evidence/original-g0-input.json','--state-file','/evidence/normal-entry-state.json','--evidence-dir','/evidence/normal-entry','--poll-limit','100','--poll-seconds','5','--execute']
start=datetime.now(timezone.utc).isoformat()
with (E/'normal-entry-console.log').open('x') as stream:
    result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
(E/'normal-entry-runner.json').write_text(json.dumps({'started_at_utc':start,'finished_at_utc':datetime.now(timezone.utc).isoformat(),'command':command,'exit_code':result.returncode,'provider_scope':'HUMAN_AUTHORIZED_SHARED_TEST','source_overlay':False},indent=2)+'\n')
print((E/'normal-entry-console.log').read_text(),flush=True)
raise SystemExit(result.returncode)