import sys
sys.dont_write_bytecode = True
from c3_retry_scope import scoped_runtime_root, verify_frozen_controls, read_built_identity
from pathlib import Path
from datetime import datetime,timezone
import json,os,subprocess
from hashlib import sha256
ROOT=scoped_runtime_root("run_c3_normal_entry.py");E=ROOT/'evidence';P=ROOT/'private'
freeze=verify_frozen_controls(ROOT)
build=read_built_identity(ROOT,freeze);IMAGE_ID=build['image']['Id']
imports=json.loads((E/'final-image-regression/actual-imports.json').read_text())
assert imports['status']=='PASS' and imports['caller_observed_image_id']==IMAGE_ID
for group in ('watt-unit','guardian-unit','c1-chain','c3-carrier','c2-pg-preflight'):
    regression=json.loads((E/'final-image-regression'/(group+'-receipt.json')).read_text())
    assert regression['image_id']==IMAGE_ID and regression['sources']==freeze['sources'] and regression['exit_code']==0
    counts=regression['counts'];assert counts['tests']>0 and counts['failures']==counts['errors']==counts['skipped']==0
worker=json.loads(subprocess.check_output(['docker','inspect','watt-c3-retry1-worker-20261009'],universal_newlines=True))[0]
assert worker['Image']==IMAGE_ID and worker['State']['Running'] is True and worker['Config']['User']=='10001:10001'
assert not (E/'normal-entry-state.json').exists(),'Preserve state; never recreate Work'
with (ROOT/'worker_root_probe.py').open() as source:
    result=subprocess.run(['docker','exec','-i','watt-c3-retry1-worker-20261009','python','-'],stdin=source,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
assert result.returncode==0,'Worker root probe failed; no Work created'
receipt=json.loads(result.stdout);(E/'worker-root-preflight.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'actual_worker_root_preflight':'PASS','uid':10001,'write_probe_removed':True}),flush=True)
credential=P/'driver-credentials.json';os.chown(str(credential),0,10001);os.chmod(str(credential),0o640)
for name in ('original-g0-input.json','driver-runtime-identity.json'):os.chmod(str(E/name),0o644)
command=['docker','run','--name','watt-c3-retry1-normal-entry-validated-20261009','--network','watt-c3-control-20261009','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,nosuid,nodev,size=64m,mode=1777','--memory','256m','--cpus','0.5','--pids-limit','64','--label','watt.production=false','--label','watt.qualification=C3-semantic-convergence-retry1','--mount','type=bind,src='+str(ROOT/'c3_normal_entry.py')+',dst=/control/c3_normal_entry.py,readonly','--mount','type=bind,src='+str(credential)+',dst=/control/private.json,readonly','--mount','type=bind,src='+str(E)+',dst=/evidence',IMAGE_ID,'python','/control/c3_normal_entry.py','--base-url','http://watt-c3-retry1-api-20261009:8000','--identity-path','/evidence/driver-runtime-identity.json','--credentials-file','/control/private.json','--input-file','/evidence/original-g0-input.json','--state-file','/evidence/normal-entry-state.json','--evidence-dir','/evidence/normal-entry','--poll-limit','100','--poll-seconds','5','--execute']
start=datetime.now(timezone.utc).isoformat()
with (E/'normal-entry-console.log').open('x') as stream:
    result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
(E/'normal-entry-runner.json').write_text(json.dumps({'started_at_utc':start,'finished_at_utc':datetime.now(timezone.utc).isoformat(),'command':command,'exit_code':result.returncode,'provider_scope':'HUMAN_AUTHORIZED_SHARED_TEST','source_overlay':False},indent=2)+'\n')
print((E/'normal-entry-console.log').read_text(),flush=True)
raise SystemExit(result.returncode)