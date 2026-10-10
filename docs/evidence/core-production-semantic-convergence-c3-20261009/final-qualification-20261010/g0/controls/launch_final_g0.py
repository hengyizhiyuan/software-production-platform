from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,secrets,subprocess,socket,time,ipaddress
from urllib.request import urlopen
R=Path('/data/watt/c3-semantic-convergence-20261009/final-g0-qualification-20261010')
SOURCE='34e9ca9cc5cd5623a9463b42ba4c26ede061640f'
IMAGE='sha256:697b80141e1a11a70111166a1bb66db674457f8461ce9bea5fa21affebdbcbec'
TREE='00f053019cf3c1ba0cd43fa1b1fca023ef638a71'
PG_IMAGE='sha256:d741b376874687de90374fd34f55c6b2760e8f7bd7e4ae5cd47f50757fc08cf8'
GI_IMAGE='sha256:071efa747340e5e211213fc79a0b928003bedf9b6b48f61cb32b3c52bfd1e09e'
CONTROL='watt-c3-finalg0-control-20261010';EXECUTOR='watt-c3-finalg0-executor-20261010'
PG='watt-c3-finalg0-postgres-20261010';GI='watt-c3-finalg0-gitea-20261010';VOL='watt-c3-finalg0-workspaces-20261010'
DB='spg_c3_finalg0_qualification_20261010'
names={r:'watt-c3-finalg0-'+r+'-20261010' for r in ('api','coordinator','worker','tool-host')}
LABELS=['--label','watt.production=false','--label','watt.qualification=C3-final-g0']
def now():return datetime.now(timezone.utc).isoformat()
def call(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
 if p.returncode:
  if 'P' in globals():
   with (P/('control-failure-'+secrets.token_hex(6)+'.json')).open('x') as f:
    os.fchmod(f.fileno(),0o600);json.dump({'binary':args[0],'exit_code':p.returncode,'stderr':p.stderr},f)
  raise RuntimeError('QUALIFICATION_CONTROL_COMMAND_FAILED_'+args[0])
 return p.stdout.strip()
def write(path,data,mode=0o600):
 with path.open('x') as f:os.fchmod(f.fileno(),mode);f.write(data)
def jx(path,obj):write(path,json.dumps(obj,indent=2)+'\n',0o644)

P=R/'private';E=R/'evidence'
assert R.is_dir() and (E/'migration.json').is_file() and not (E/'normal-entry-state.json').exists()
assert not (E/'runtime-role-preparation.json').exists()
for n in names.values():assert subprocess.run(['docker','inspect',n],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
credentials=json.loads((P/'credentials.json').read_text())
source_env=dict(line.split('=',1) for line in Path('/data/watt/c3-semantic-convergence-20261009/retry-1/private/watt-c3-retry1-api-20261009.env').read_text().splitlines() if '=' in line)
provider_key=source_env['SPG_DEEPSEEK_API_KEY'];provider_base=source_env['SPG_DEEPSEEK_BASE_URL'];assert provider_base=='https://api.deepseek.com'
url='postgresql+psycopg://c3_app:'+credentials['postgres_password']+'@'+PG+':5432/'+DB
def envfile(name,env):
 assert all(chr(10) not in v and chr(13) not in v for v in env.values())
 f=P/name;write(f,''.join(k+'='+v+chr(10) for k,v in env.items()));return f
IMAGE_ID=IMAGE;REV=SOURCE;head=json.loads((E/'migration.json').read_text())['migration']
assert head=='20261007_72'
jx(E/'preparation-control-recovery.json',{'recorded_at_utc':now(),'original_control_failure':'NameError_REV_UNBOUND','boundary':'after fresh migration, before any API/coordinator/worker/tool-host or model/Work','prior_network_preflight_failure':'TypeError_NULL_IPAM_CONFIG','historical_failure_time':'UNKNOWN','models_before_recovery':0,'works_before_recovery':0,'recreated_dependencies':False,'application_code_modified':False})
common={'SPG_DATABASE_URL':url,'SPG_RUNTIME_PROFILE':'c3-finalg0-20261010','SPG_RUNTIME_REVISION':REV,'SPG_AUTH_MODE':'required','SPG_OPERATOR_TOKEN':credentials['operator_token'],'SPG_NATIVE_EXECUTOR_ENABLED':'true','SPG_EXECUTOR_ADAPTER':'watt-native','SPG_VERIFICATION_ADAPTER':'contract-driven-repository','SPG_OWNER_RUNTIME_MODE':'REQUIRED','SPG_OWNER_RUNTIME_STORE_ROOT':'/var/lib/spg/owner-runtime','SPG_WORKSPACE_ROOT':'/var/lib/spg/native-workspaces','SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT':'/var/lib/spg/native-workspaces','SPG_NATIVE_EXECUTOR_STORAGE_ROOT':'/var/lib/spg/native-executor','SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_STORE_ROOT':'/var/lib/spg/production-environments','SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_WORKSPACE_VOLUME':'watt-c3-finalg0-workspaces-20261010','SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_IMAGE':IMAGE_ID,'SPG_NATIVE_EXECUTOR_INFERENCE_PROVIDER':'deepseek','SPG_NATIVE_EXECUTOR_INFERENCE_MODEL':'deepseek-flash','SPG_NATIVE_EXECUTOR_INFERENCE_REASONING_EFFORT':'high','SPG_NATIVE_EXECUTOR_WORKER_ID':'watt-c3-finalg0-real-worker-20261010','SPG_NATIVE_EXECUTOR_WORKER_PROFILE':'local-container-v1','SPG_NATIVE_EXECUTOR_RESOURCE_PROFILE':'standard','SPG_NATIVE_EXECUTOR_TOOL_HOST_URL':'http://'+names['tool-host']+':8011','SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN':credentials['tool_host_token'],'SPG_DEEPSEEK_API_KEY':provider_key,'SPG_DEEPSEEK_BASE_URL':provider_base,'SPG_NATIVE_EXECUTOR_DEEPSEEK_API_KEY':provider_key,'SPG_NATIVE_EXECUTOR_DEEPSEEK_BASE_URL':provider_base,'SPG_WIC_PROVIDER_ADAPTER':'deepseek','SPG_CONVERSATION_PROVIDER_ADAPTER':'deepseek','SPG_WIC_PROVIDER_MODEL':'deepseek-flash','SPG_CONVERSATION_PROVIDER_MODEL':'deepseek-flash','SPG_WIC_RUNTIME_MODE':'WIC_VNEXT_CONTROLLED','SPG_MANAGED_SOURCE_PROVIDER':'gitea','SPG_MANAGED_SOURCE_ENDPOINT':'http://watt-c3-finalg0-gitea-20261010:3000','SPG_MANAGED_SOURCE_PUBLIC_ENDPOINT':'http://watt-c3-finalg0-gitea-20261010:3000','SPG_MANAGED_SOURCE_USERNAME':credentials['gitea_user'],'SPG_MANAGED_SOURCE_PASSWORD':credentials['gitea_password'],'SPG_MANAGED_SOURCE_NAMESPACE':credentials['gitea_user'],'SPG_MANAGED_SOURCE_WORKSPACE_ROOT':'/var/lib/spg/managed-source','SPG_DELIVERY_RUNTIME_ENABLED':'false','SPG_REPOSITORY_PATH':'/var/lib/spg/managed-source'}
toolenv={'SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT':'/var/lib/spg/native-workspaces','SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_WORKSPACE_VOLUME':'watt-c3-finalg0-workspaces-20261010','SPG_NATIVE_EXECUTOR_CONTAINER_ISOLATION_REQUIRED':'true','SPG_NATIVE_EXECUTOR_TOOL_HOST_ISOLATION':'production-environment-only','SPG_NATIVE_EXECUTOR_RECEIPT_SPOOL_ROOT':'/var/lib/spg/native-tool-receipts','SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN':credentials['tool_host_token'],'SPG_RUNTIME_REVISION':REV,'SPG_RUNTIME_PROFILE':'c3-finalg0-20261010'}
common.update({'SPG_WIC_PROVIDER_REASONING_EFFORT':'none','SPG_COLLABORATION_PROVIDER_TIMEOUT_SECONDS':'120','SPG_COLLABORATION_PROVIDER_MAX_OUTPUT_TOKENS':'16384','C3_WATT_TREE':TREE})
commands={'api':['python','-m','uvicorn','spg.api.http:create_http_application','--factory','--host','0.0.0.0','--port','8000'],'coordinator':['python','-m','spg.executor_coordinator'],'worker':['python','-m','spg.executor_worker'],'tool-host':['python','-m','uvicorn','spg.tool_host_api:create_tool_host_application','--factory','--host','0.0.0.0','--port','8011']}
roles=[]
for role in ('tool-host','api','coordinator','worker'):
 name=names[role];env=toolenv if role=='tool-host' else common
 ef=envfile(name+'.env',env)
 cmd=['docker','run','-d','--name',name,'--network',CONTROL,'--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m,mode=1777','--memory',{'api':'1536m','worker':'1024m','coordinator':'512m','tool-host':'512m'}[role],'--cpus','1','--pids-limit','256']+LABELS+['--env-file',str(ef),'--mount','type=bind,src='+str(R/'app')+',dst=/var/lib/spg'+(',readonly' if role=='tool-host' else ''),'--mount','type=volume,src='+VOL+',dst=/var/lib/spg/native-workspaces']
 if role in ('api','tool-host'):cmd+=['--mount','type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock','--group-add',str(Path('/var/run/docker.sock').stat().st_gid)]
 if role=='tool-host':cmd+=['--mount','type=bind,src='+str(R/'receipts')+',dst=/var/lib/spg/native-tool-receipts']
 if role=='api':cmd+=['--publish','127.0.0.1:18302:8000']
 call(cmd+[IMAGE]+commands[role]);call(['docker','network','connect',EXECUTOR,name])
 data=json.loads(call(['docker','inspect',name]))[0]
 assert data['Image']==IMAGE and data['Config']['User']=='10001:10001'
 roles.append({'role':role,'name':name,'container_id':data['Id'],'image_id':data['Image'],'mounts':data['Mounts'],'labels':data['Config']['Labels'],'user':data['Config']['User'],'networks':list(data['NetworkSettings']['Networks']),'ports':data['HostConfig']['PortBindings'],'read_only_root':data['HostConfig']['ReadonlyRootfs']})
 jx(E/(role+'-actual-runtime.json'),roles[-1])
 call(['docker','exec',name,'python','/opt/c3-build/attest_c3_image.py','--image-id',IMAGE,'--output','/tmp/c3-role-import-attestation.json'])
 jx(E/(role+'-import-attestation.json'),json.loads(call(['docker','exec',name,'cat','/tmp/c3-role-import-attestation.json'])))
for i in range(30):
 try:
  with urlopen('http://127.0.0.1:18302/health',timeout=2) as f:health=json.load(f)
  break
 except Exception:time.sleep(1)
else:raise RuntimeError('NEW_API_NOT_READY')
assert health.get('service')=='available'
ready=json.loads(call(['docker','exec',names['worker'],'python','-m','spg.executor_worker','--check-readiness']))
assert ready['status']=='READY' and ready['provider_request_sent'] is False
jx(E/'provider-config-readiness.json',ready)
probe=(R/'controls/worker_root_probe.py').read_text()
p=subprocess.run(['docker','exec','-i',names['worker'],'python','-'],input=probe,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
assert p.returncode==0,'ACTUAL_WORKER_PREFLIGHT_FAILED'
jx(E/'worker-root-preflight.json',json.loads(p.stdout))
write(P/'driver-credentials.json',json.dumps({'operator_token':credentials['operator_token']}))
identity={'qualification':'C3','qualification_run':'final-g0','isolated':True,'api_service':names['api'],'api_base_url':'http://'+names['api']+':8000','source_revision':SOURCE,'image_id':IMAGE,'database_name':DB,'captured_at_utc':now(),'model_credential_scope':'HUMAN_AUTHORIZED_SHARED_TEST','provider_ready':True,'provider_readiness_scope':'configuration only; no request yet'}
jx(E/'driver-runtime-identity.json',identity)
b=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/review-primary-qualified-20261010/final-image/evidence/build.json')
write(E/'build-reference.json',b.read_text(),0o644)
jx(E/'runtime-role-preparation.json',{'recorded_at_utc':now(),'roles':roles,'source':SOURCE,'tree':TREE,'image_id':IMAGE,'database':DB,'migration':head,'isolated_wic_formation_review_reasoning':'none','native_worker_reasoning':'high','max_output_tokens':16384,'timeout_seconds':120,'production_modified':False,'old_resources_started':False,'model_calls':0,'works_created':0,'control_sha256':sha256(Path(__file__).read_bytes()).hexdigest()})
print(json.dumps({'preparation':'PASS','source':SOURCE,'image':IMAGE,'database':DB,'actual_worker_preflight':'PASS','model_calls':0,'works_created':0}))
