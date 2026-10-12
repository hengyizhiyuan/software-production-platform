"""Upgrade isolated application roles only; preserve the existing Work and contracts."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,subprocess,time
R=Path('/data/watt/c3-semantic-convergence-20261009/binding-g0-generation61-qualification-20261010')
Q=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation66-qualified-20261010')
T=R/'native-context-recovery-generation66';assert not T.exists();T.mkdir(mode=0o755)
P=T/'private';P.mkdir(mode=0o700);E=T/'evidence';E.mkdir(mode=0o755)
B=json.loads((Q/'final-image/evidence/build.json').read_text());IMAGE=B['image']['Id'];SOURCE=B['sources']['watt']['revision'];TREE=B['sources']['watt']['tree']
OLD='sha256:b0b7899e2c66a2135b90d0a7b9c8419e3fa937d587d23061f0d20a4e6ab7cbe4'
WORK='6ba2cffa-0bf3-565a-81e0-7f3c6696f21e';ATTEMPT='de98f392-b8d1-40ac-a442-a283fa938060'
CONTROL='watt-c3-bindingg0g61-control-20261010';EXECUTOR='watt-c3-bindingg0g61-executor-20261010';VOL='watt-c3-bindingg0g61-workspaces-20261010'
def call(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
 if p.returncode:
  f=P/('command-failure-'+str(time.monotonic()).replace('.','')+'.json')
  with f.open('x') as s:os.fchmod(s.fileno(),0o600);json.dump({'binary':args[0],'stderr':p.stderr,'exit':p.returncode},s)
  raise RuntimeError('ISOLATED_CONTROL_FAILURE_'+args[0])
 return p.stdout.strip()
def write(path,obj,private=False):
 with path.open('x') as f:os.fchmod(f.fileno(),0o600 if private else 0o644);json.dump(obj,f,indent=2)
for f in (Q/'final-image/evidence/watt-continuation-receipt.json',Q/'final-image/evidence/guardian-receipt.json',Q/'owner-pg-generation66-recovery1/evidence/receipt.json'):
 d=json.loads(f.read_text());assert d['exit_code']==0 and not sum(d['counts'][k] for k in ('failures','errors','skipped'))
old_pg=json.loads((Q/'owner-pg-generation66/evidence/receipt.json').read_text());assert old_pg['counts']['passed']==14 and old_pg['counts']['failures']==2 and old_pg['counts']['errors']==0 and old_pg['counts']['skipped']==0
assert call(['git','-C','/data/watt/runtime/source','rev-parse','HEAD'])=='5de657f3cb65780adf50f6557b54171a6c3cfae5'
assert call(['git','-C','/data/watt/runtime/source','rev-parse','refs/heads/main'])=='ee5bd86a53891f9391785c91d0ccef81ad2d56c3'
sql="SELECT count(*) FROM execution_allocations WHERE condition='ACTIVE'"
assert call(['docker','exec','watt-c3-bindingg0g61-postgres-20261010','psql','-U','c3_app','-d','spg_c3_bindingg0g61_qualification_20261010','-Atc',sql])=='0'
original={}
for role in ('api','coordinator','worker','tool-host'):
 name='watt-c3-bindingg0g61-'+role+'-20261010';x=json.loads(call(['docker','inspect',name]))[0]
 assert x['Image']==OLD and x['Config']['Labels']['watt.production']=='false'
 original[role]=x;write(P/(role+'-before-inspect.json'),x,True)
for role in ('worker','coordinator','api','tool-host'):
 x=original[role];name=x['Name'].lstrip('/');call(['docker','stop','-t','20',name]);call(['docker','rename',name,name+'-before-context66'])
roles=[]
for role in ('tool-host','api','coordinator','worker'):
 x=original[role];name=x['Name'].lstrip('/');env=dict(v.split('=',1) for v in x['Config']['Env'] if '=' in v)
 env['SPG_RUNTIME_REVISION']=SOURCE
 env['C3_WATT_TREE']=TREE;env['SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_IMAGE']=IMAGE
 ef=P/(role+'.env')
 with ef.open('x') as f:
  os.fchmod(f.fileno(),0o600)
  for k,v in env.items():assert '\n' not in v and '\r' not in v;f.write(k+'='+v+'\n')
 cmd=['docker','run','-d','--name',name,'--network',CONTROL,'--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m,mode=1777','--memory',str(x['HostConfig']['Memory']),'--cpus','1','--pids-limit','256','--label','watt.production=false','--label','watt.qualification=C3-binding-g0-context-recovery','--env-file',str(ef)]
 for mount in x['Mounts']:
  assert mount['Type'] in ('bind','volume')
  source=mount['Name'] if mount['Type']=='volume' else mount['Source']
  cmd+=['--mount','type='+mount['Type']+',src='+source+',dst='+mount['Destination']+(',readonly' if not mount['RW'] else '')]
 if role in ('api','tool-host'):cmd+=['--group-add',str(Path('/var/run/docker.sock').stat().st_gid)]
 if role=='api':cmd+=['--publish','127.0.0.1:18327:8000']
 call(cmd+[IMAGE]+x['Config']['Cmd']);call(['docker','network','connect',EXECUTOR,name])
 a=json.loads(call(['docker','inspect',name]))[0];assert a['Image']==IMAGE
 call(['docker','exec',name,'python','/opt/c3-build/attest_c3_image.py','--image-id',IMAGE,'--output','/tmp/c3-role-import-attestation.json'])
 att=json.loads(call(['docker','exec',name,'cat','/tmp/c3-role-import-attestation.json']))
 roles.append({'role':role,'container_id':a['Id'],'prior_container_id':x['Id'],'image_id':a['Image'],'import_attestation':att,'mounts':a['Mounts'],'networks':list(a['NetworkSettings']['Networks']),'user':a['Config']['User']})
from urllib.request import urlopen
for _ in range(30):
 try:
  with urlopen('http://127.0.0.1:18327/health',timeout=2) as f:h=json.load(f)
  if h.get('service')=='available':break
 except Exception:pass
 time.sleep(1)
else:raise RuntimeError('ISOLATED_NEW_API_NOT_READY')
frame_script="from uuid import UUID\nimport json\nfrom spg.config import Settings\nfrom spg.infrastructure.persistence import Database\nfrom spg.infrastructure.persistence.product_store import ProductStore\nfrom spg.infrastructure.persistence.runtime_store import RuntimeStore\nfrom spg.application.steering_decision import PlanFrameAssembler\nfrom spg.domain.steering import RealityReferenceKind\ns=Settings();db=Database.from_settings(s)\nw=UUID('6ba2cffa-0bf3-565a-81e0-7f3c6696f21e')\nf=PlanFrameAssembler(db).assemble(w)\nwith db.unit_of_work() as u:\n p=ProductStore(u.session);b=p.runtime_binding(w);summary=p.runtime_summary(b);rs=RuntimeStore(u.session).verification_records_for_snapshot(summary.proposed_snapshot_id)\n refs={r.identity for r in f.runtime_reality_refs if r.kind is RealityReferenceKind.VERIFICATION}\n assert all(r.id in refs for r in rs)\n print(json.dumps({'frame_assembled':True,'all_historical_verification_retained':True,'verification_count':len(rs),'selected_current_ids':summary.extra.get('verification_record_ids'),'current_results':summary.verification_results,'blocker_kinds':[x.kind.value for x in f.open_blocking_reality],'model_calls':0}))\n"
frame_result=subprocess.run(['docker','exec','-i','watt-c3-bindingg0g61-api-20261010','python','-'],input=frame_script.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if frame_result.returncode:
 write(P/'frame-startup-failure.json',{'exit_code':frame_result.returncode,'stdout':frame_result.stdout.decode(errors='replace'),'stderr':frame_result.stderr.decode(errors='replace')},True)
 raise RuntimeError('ISOLATED_OWNER_PLAN_FRAME_QUALIFICATION_FAILED')
write(E/'actual-current-frame.json',json.loads(frame_result.stdout.decode()))
ready=json.loads(call(['docker','exec','watt-c3-bindingg0g61-worker-20261010','python','-m','spg.executor_worker','--check-readiness']));assert ready['status']=='READY' and ready['provider_request_sent'] is False
state=json.loads((R/'native-context-recovery-generation65/collector-state.json').read_text());state['continuation_of_state_sha256']=sha256((R/'native-context-recovery-generation65/collector-state.json').read_bytes()).hexdigest();state['previous_runtime_identity']=state['runtime_identity'];state['runtime_identity']=dict(state['runtime_identity']);state['runtime_identity'].update({'source_revision':SOURCE,'image_id':IMAGE,'captured_at_utc':datetime.now(timezone.utc).isoformat()})
write(T/'collector-state.json',state)
write(E/'isolated-role-upgrade.json',{'captured_at_utc':datetime.now(timezone.utc).isoformat(),'source':SOURCE,'tree':TREE,'image_id':IMAGE,'roles':roles,'readiness':ready,'work_id':WORK,'attempt_id':ATTEMPT,'original_contract_modified':False,'original_production_environment_replaced':False,'prior_containers_retained':True,'work_created':0,'model_calls':0,'canonical_production_modified':False,'controller_sha256':sha256(Path(__file__).read_bytes()).hexdigest()})
print(json.dumps({'roles_upgraded':len(roles),'source':SOURCE,'image_id':IMAGE,'work_created':0,'model_calls':0,'resumed':False}))
