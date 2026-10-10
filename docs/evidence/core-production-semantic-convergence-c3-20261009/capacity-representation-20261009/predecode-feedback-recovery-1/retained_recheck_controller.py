
from pathlib import Path
import json,os,subprocess,hashlib
from datetime import datetime,timezone
T=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/wire-feedback-recovery-20261010')
L=T.parent/'option-a-live-bounded-1'
target=T/'retained-diagnostic-recheck';target.mkdir(mode=0o750)
e=target/'evidence';e.mkdir(mode=0o750);os.chown(str(e),10001,10001)
private=target/'private';private.mkdir(mode=0o700)
build=json.loads((T/'final-image/evidence/build.json').read_text());assert build['exit_code']==0
image=build['image']['Id'];assert build['sources']['watt']['revision']=='e7afb5a15df4c187a9248b4a073391a62037677f'
basis=Path('/data/watt/c3-semantic-convergence-20261009/public-delivery-c3-final/retry-1/g0-owner-2/20261009T130020024208Z-2fc7b990c1b54846a25bd067bc94b849-canonical-work.json')
probe=T/'final-inputs/recheck_retained_outputs.py'
files=[basis,probe]+list((L/'private/model-observations').glob('*'))
before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
name='watt-c3-wire-feedback-retained-recheck-20261010'
cmd=['docker','run','--name',name,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user','10001:10001','--pids-limit','128','--memory','1536m','--cpus','1','--tmpfs','/tmp:rw,noexec,nosuid,size=32m','--label','watt.production=false']
for src,dst in ((probe,'/probe.py'),(basis,'/basis.json'),(L/'private/model-observations','/retained')):
 cmd+=['--mount','type=bind,src='+str(src)+',dst='+dst+',readonly']
cmd+=['--mount','type=bind,src='+str(e)+',dst=/evidence',image,'python','/probe.py']
with (private/'raw.log').open('x') as stream:
 os.fchmod(stream.fileno(),0o600);result=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT)
after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
assert before==after
actual=json.loads(subprocess.check_output(['docker','inspect',name],universal_newlines=True))[0]
receipt={'schema':'c3-retained-recheck-controller-v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
 'application_source':build['sources']['watt']['revision'],'actual_image_id':actual['Image'],'actual_container_id':actual['Id'],
 'network':actual['HostConfig']['NetworkMode'],'source_overlay':False,'diagnostic_probe_mount':True,
 'inputs_before':before,'inputs_after':after,'immutable_inputs':before==after,'exit_code':result.returncode,
 'model_calls':0,'database_access':False,'history_mutated':False,'production_resources_modified':False,'controller_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest() if '__file__' in globals() and Path(__file__).exists() else 'STDIN_CONTROL'}
(e/'controller.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
assert result.returncode==0,'Retained recheck failed; private log retained, no retry'
print(json.dumps({'diagnostics':[{'attempt':a['attempt'],'primary_error':a['primary_error'],'violations':a['new_derived_diagnostics']['violations'],'binding':a['new_derived_diagnostics']['binding']} for a in json.loads((e/'retained-diagnostic-recheck.json').read_text())['attempts']]}))
