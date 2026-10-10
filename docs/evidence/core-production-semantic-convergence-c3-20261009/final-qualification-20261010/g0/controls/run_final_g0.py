from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json, os, subprocess
R=Path('/data/watt/c3-semantic-convergence-20261009/final-g0-qualification-20261010')
P=R/'private';E=R/'evidence';C=R/'controls'
IMAGE='sha256:697b80141e1a11a70111166a1bb66db674457f8461ce9bea5fa21affebdbcbec'
identity=json.loads((E/'driver-runtime-identity.json').read_text())
assert identity['image_id']==IMAGE and identity['source_revision']=='34e9ca9cc5cd5623a9463b42ba4c26ede061640f'
assert not (E/'normal-entry-state.json').exists() and not (P/'g0-started.json').exists()
ready=json.loads((E/'worker-root-preflight.json').read_text());assert ready['probe_write_succeeded'] and ready['probe_removed']
for role in ('api','worker','coordinator','tool-host'):
 x=json.loads(subprocess.check_output(['docker','inspect','watt-c3-finalg0-'+role+'-20261010'],universal_newlines=True))[0]
 assert x['Image']==IMAGE and x['State']['Running'] and x['Config']['Labels']['watt.production']=='false'
state={'schema':'c3-real-g0-once-execution-v1','started_at_utc':datetime.now(timezone.utc).isoformat(),
 'source':identity['source_revision'],'image':IMAGE,'maximum_new_work':1,
 'authorization':'Human 2026-10-10: execute one real G0 on final exact source/image; preserve production/history; no Human Integration/Acceptance/Delivery authority',
 'driver_sha256':sha256((C/'c3_normal_entry.py').read_bytes()).hexdigest()}
with (P/'g0-started.json').open('x') as f:os.fchmod(f.fileno(),0o600);json.dump(state,f,indent=2)
os.chown(str(E),10001,10001);os.chmod(str(E),0o750)
credentials=P/'driver-credentials.json';os.chown(str(credentials),0,10001);os.chmod(str(credentials),0o640)
cmd=['docker','run','--name','watt-c3-finalg0-normal-entry-20261010','--network','watt-c3-finalg0-control-20261010','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,nosuid,nodev,size=64m,mode=1777','--memory','256m','--cpus','0.5','--pids-limit','64','--label','watt.production=false','--label','watt.qualification=C3-final-g0',
 '--mount','type=bind,src='+str(C/'c3_normal_entry.py')+',dst=/control/c3_normal_entry.py,readonly',
 '--mount','type=bind,src='+str(credentials)+',dst=/control/private.json,readonly',
 '--mount','type=bind,src='+str(E)+',dst=/evidence',IMAGE,'python','/control/c3_normal_entry.py',
 '--base-url',identity['api_base_url'],'--identity-path','/evidence/driver-runtime-identity.json','--credentials-file','/control/private.json','--input-file','/evidence/original-g0-input.json','--state-file','/evidence/normal-entry-state.json','--evidence-dir','/evidence/normal-entry','--poll-limit','100','--poll-seconds','5','--execute']
with (P/'normal-entry.raw.log').open('x') as f:
 os.fchmod(f.fileno(),0o600);result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
state.update({'ended_at_utc':datetime.now(timezone.utc).isoformat(),'exit_code':result.returncode,'qualification_claim':'OBSERVATION_ONLY_NOT_WORK_PASS'})
with (E/'normal-entry-runner.json').open('x') as f:json.dump(state,f,indent=2)
if (E/'normal-entry-state.json').exists():
 s=json.loads((E/'normal-entry-state.json').read_text())
 print(json.dumps({'work_id':s.get('work_id'),'product_id':s.get('product_id'),'driver_status':s.get('driver_status'),'latest_observation':s.get('latest_observation'),'exit_code':result.returncode}))
else:print(json.dumps({'runner_exit_code':result.returncode,'state':'ABSENT','work_outcome':'UNKNOWN'}))
raise SystemExit(result.returncode)
