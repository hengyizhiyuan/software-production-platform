"""Correct diagnostic output ownership; retain the failed harness receipt."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess,time
R=Path('/data/watt/c3-semantic-convergence-20261009')
T=R/'semantic-contract-implementation-20261010'
E=T/'retained-replay-2';assert not E.exists();E.mkdir(mode=0o700)
build=json.loads((T/'final-image/evidence/build.json').read_text());assert build['exit_code']==0
image=build['image']['Id']
basis=R/'public-delivery-c3-final/retry-1/g0-owner-2/20261009T130020024208Z-2fc7b990c1b54846a25bd067bc94b849-canonical-work.json'
candidate=R/'capacity-representation-20261009/semantic-contract-calibration-1-run2/private/read-only-original-candidate.json'
script=T/'final-inputs/replay_retained_candidate.py'
inputs=[basis,candidate,script]
before={str(p):sha256(p.read_bytes()).hexdigest() for p in inputs}
name='watt-c3-calibration-retained-replay2-62d2ebf'
command=['docker','run','--name',name,'--network','none','--read-only','--cap-drop','ALL',
    '--security-opt','no-new-privileges','--user','0:0','--memory','1g','--cpus','1',
    '--tmpfs','/tmp:rw,nosuid,size=64m','--mount','type=bind,src='+str(E)+',dst=/evidence']
for p,target in ((basis,'/basis.json'),(candidate,'/candidate.json'),(script,'/replay.py')):
    command+=['--mount','type=bind,src='+str(p)+',dst='+target+',readonly']
command+=[image,'python','/replay.py']
start=time.monotonic();started=datetime.now(timezone.utc).isoformat()
with (E/'replay.log').open('x') as stream:result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
after={str(p):sha256(p.read_bytes()).hexdigest() for p in inputs}
actual=json.loads(subprocess.check_output(['docker','inspect',name],universal_newlines=True))[0]
record={'started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),
    'actual_image':actual['Image'],'actual_container':actual['Id'],'sources':build['sources'],
    'inputs_before':before,'inputs_after':after,'immutable_inputs':before==after,'exit_code':result.returncode,
    'wall_seconds':time.monotonic()-start,'network':'none','database_access':False,'model_calls':0,
    'output_owner':'dedicated root-owned diagnostic directory, no existing permission changed',
    'mounts':actual['Mounts'],'environment_names':[s.split('=',1)[0] for s in actual['Config']['Env']]}
(E/'controller.json').write_text(json.dumps(record,indent=2)+'\n')
assert result.returncode==0 and before==after
print(json.dumps({'retained_candidate':'REJECTED_AS_REQUIRED','actual_image':image,'output':str(E)}))
