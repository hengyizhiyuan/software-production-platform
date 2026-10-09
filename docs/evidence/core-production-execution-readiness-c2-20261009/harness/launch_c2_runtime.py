from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,socket,subprocess,time
from urllib.request import urlopen
ROOT=Path('/data/watt/c2-execution-readiness-20261009');P=ROOT/'private';E=ROOT/'evidence'
IMAGE='watt-c2:88f1d98';IMAGE_ID='sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209';REV='88f1d9805d3ed1aa779ed3c78902b193fae240f8'
assert subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',IMAGE],universal_newlines=True).strip()==IMAGE_ID
names={role:'watt-c2-'+role+'-20261009' for role in ('api','coordinator','worker','tool-host')}
for name in names.values():
    assert subprocess.run(['docker','inspect',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0,('preserve existing',name)
with socket.socket() as check:
    check.bind(('127.0.0.1',18200))
credentials=json.loads((P/'credentials.json').read_text())
old=json.loads(subprocess.check_output(['docker','inspect','watt-n1-api-20261008'],universal_newlines=True))[0]
source_env=dict(item.split('=',1) for item in old['Config']['Env'] if '=' in item)
provider_key=source_env.get('SPG_DEEPSEEK_API_KEY') or source_env.get('SPG_NATIVE_EXECUTOR_DEEPSEEK_API_KEY')
assert provider_key,'Human-authorized existing test Provider credential absent'
provider_base=source_env.get('SPG_DEEPSEEK_BASE_URL') or source_env.get('SPG_NATIVE_EXECUTOR_DEEPSEEK_BASE_URL') or 'https://api.deepseek.com'
assert provider_base=='https://api.deepseek.com'
image=json.loads(subprocess.check_output(['docker','image','inspect',IMAGE],universal_newlines=True))[0]
for setting in image['Config']['Env']:
    key,value=setting.split('=',1)
    if any(part in key for part in ('API_KEY','ACCESS_KEY','PASSWORD','TOKEN')):
        assert not value,('Unexpected embedded credential',key)
url='postgresql+psycopg://'+credentials['database_user']+':'+credentials['database_password']+'@watt-c2-postgres-20261009:5432/spg_c2_qualification_20261009'
common={'SPG_DATABASE_URL':url,'SPG_RUNTIME_PROFILE':'c2-execution-readiness-20261009','SPG_RUNTIME_REVISION':REV,'SPG_AUTH_MODE':'required','SPG_OPERATOR_TOKEN':credentials['operator_token'],'SPG_NATIVE_EXECUTOR_ENABLED':'true','SPG_EXECUTOR_ADAPTER':'watt-native','SPG_VERIFICATION_ADAPTER':'contract-driven-repository','SPG_OWNER_RUNTIME_MODE':'REQUIRED','SPG_OWNER_RUNTIME_STORE_ROOT':'/var/lib/spg/owner-runtime','SPG_WORKSPACE_ROOT':'/var/lib/spg/native-workspaces','SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT':'/var/lib/spg/native-workspaces','SPG_NATIVE_EXECUTOR_STORAGE_ROOT':'/var/lib/spg/native-executor','SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_STORE_ROOT':'/var/lib/spg/production-environments','SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_WORKSPACE_VOLUME':'watt-c2-workspaces-20261009','SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_IMAGE':IMAGE_ID,'SPG_NATIVE_EXECUTOR_INFERENCE_PROVIDER':'deepseek','SPG_NATIVE_EXECUTOR_INFERENCE_MODEL':'deepseek-flash','SPG_NATIVE_EXECUTOR_INFERENCE_REASONING_EFFORT':'high','SPG_NATIVE_EXECUTOR_WORKER_ID':'watt-c2-real-worker-20261009','SPG_NATIVE_EXECUTOR_WORKER_PROFILE':'local-container-v1','SPG_NATIVE_EXECUTOR_RESOURCE_PROFILE':'standard','SPG_NATIVE_EXECUTOR_TOOL_HOST_URL':'http://'+names['tool-host']+':8011','SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN':credentials['tool_host_token'],'SPG_DEEPSEEK_API_KEY':provider_key,'SPG_DEEPSEEK_BASE_URL':provider_base,'SPG_NATIVE_EXECUTOR_DEEPSEEK_API_KEY':provider_key,'SPG_NATIVE_EXECUTOR_DEEPSEEK_BASE_URL':provider_base,'SPG_WIC_PROVIDER_ADAPTER':'deepseek','SPG_CONVERSATION_PROVIDER_ADAPTER':'deepseek','SPG_WIC_PROVIDER_MODEL':'deepseek-flash','SPG_CONVERSATION_PROVIDER_MODEL':'deepseek-flash','SPG_WIC_RUNTIME_MODE':'WIC_VNEXT_CONTROLLED','SPG_MANAGED_SOURCE_PROVIDER':'gitea','SPG_MANAGED_SOURCE_ENDPOINT':'http://watt-c2-gitea-20261009:3000','SPG_MANAGED_SOURCE_PUBLIC_ENDPOINT':'http://watt-c2-gitea-20261009:3000','SPG_MANAGED_SOURCE_USERNAME':credentials['gitea_user'],'SPG_MANAGED_SOURCE_PASSWORD':credentials['gitea_password'],'SPG_MANAGED_SOURCE_NAMESPACE':credentials['gitea_user'],'SPG_MANAGED_SOURCE_WORKSPACE_ROOT':'/var/lib/spg/managed-source','SPG_DELIVERY_RUNTIME_ENABLED':'false','SPG_REPOSITORY_PATH':'/var/lib/spg/managed-source'}
toolenv={'SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT':'/var/lib/spg/native-workspaces','SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_WORKSPACE_VOLUME':'watt-c2-workspaces-20261009','SPG_NATIVE_EXECUTOR_CONTAINER_ISOLATION_REQUIRED':'true','SPG_NATIVE_EXECUTOR_TOOL_HOST_ISOLATION':'production-environment-only','SPG_NATIVE_EXECUTOR_RECEIPT_SPOOL_ROOT':'/var/lib/spg/native-tool-receipts','SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN':credentials['tool_host_token'],'SPG_RUNTIME_REVISION':REV,'SPG_RUNTIME_PROFILE':'c2-execution-readiness-20261009'}
commands={'api':['python','-m','uvicorn','spg.api.http:create_http_application','--factory','--host','0.0.0.0','--port','8000'],'coordinator':['python','-m','spg.executor_coordinator'],'worker':['python','-m','spg.executor_worker'],'tool-host':['python','-m','uvicorn','spg.tool_host_api:create_tool_host_application','--factory','--host','0.0.0.0','--port','8011']}
labels=['--label','watt.production=false','--label','watt.qualification=C2-execution-readiness']
for child in ('managed-source','native-executor','owner-runtime','production-environments'):
    path=ROOT/'app'/child;assert not path.exists();path.mkdir(mode=0o750);os.chown(str(path),10001,10001)
def invoke(args):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    if result.returncode:raise RuntimeError('C2 action failed: '+args[0]+' '+args[1])
    return result.stdout.strip()
receipts=[]
for role in ('tool-host','api','coordinator','worker'):
    name=names[role];env=toolenv if role=='tool-host' else common
    envfile=P/(name+'.env')
    with envfile.open('x') as stream:
        os.fchmod(stream.fileno(),0o600)
        for key,value in env.items():
            assert '\n' not in value and '\r' not in value
            stream.write(key+'='+value+'\n')
    command=['docker','run','-d','--name',name,'--network','watt-c2-control-20261009','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m,mode=1777','--memory',{'api':'1536m','worker':'1024m','coordinator':'512m','tool-host':'512m'}[role],'--cpus','1','--pids-limit','256']+labels+['--env-file',str(envfile)]
    command+=['--mount','type=bind,src='+str(ROOT/'app')+',dst=/var/lib/spg'+(',readonly' if role=='tool-host' else ''),'--mount','type=volume,src=watt-c2-workspaces-20261009,dst=/var/lib/spg/native-workspaces']
    if role in ('api','tool-host'):
        command+=['--mount','type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock','--group-add','992']
    if role=='tool-host':command+=['--mount','type=bind,src='+str(ROOT/'receipts')+',dst=/var/lib/spg/native-tool-receipts']
    if role=='api':command+=['--publish','127.0.0.1:18200:8000']
    invoke(command+[IMAGE_ID]+commands[role])
    invoke(['docker','network','connect','watt-c2-executor-20261009',name])
    data=json.loads(invoke(['docker','inspect',name]))[0]
    assert data['Image']==IMAGE_ID and data['Config']['User']=='10001:10001'
    receipts.append({'role':role,'name':name,'container_id':data['Id'],'image_id':data['Image'],'command':commands[role],'labels':data['Config']['Labels'],'mounts':data['Mounts'],'user':data['Config']['User'],'group_add':data['HostConfig']['GroupAdd'],'networks':list(data['NetworkSettings']['Networks']),'ports':data['HostConfig']['PortBindings'],'read_only_root':data['HostConfig']['ReadonlyRootfs']})
    (E/'runtime-role-preparation.json').write_text(json.dumps({'captured_at_utc':datetime.now(timezone.utc).isoformat(),'roles':receipts,'source_revision':REV,'database':'spg_c2_qualification_20261009','model_credential_scope':'HUMAN_AUTHORIZED_SHARED_TEST','human_authorization':'explicit reply 2026-10-09: reuse existing test credential','production_resources_modified':False,'shared_docker_daemon':True},indent=2)+'\n')
health=None
for index in range(20):
    try:
        with urlopen('http://127.0.0.1:18200/health',timeout=2) as response:health=json.load(response)
        break
    except Exception:time.sleep(1)
assert health and health.get('service')=='available'
provider=json.loads(invoke(['docker','exec',names['worker'],'python','-m','spg.executor_worker','--check-readiness']))
assert provider['status']=='READY' and provider['provider_request_sent'] is False
(E/'provider-config-readiness.json').write_text(json.dumps(provider,indent=2)+'\n')
identity={'qualification':'C2','isolated':True,'api_service':names['api'],'api_base_url':'http://watt-c2-api-20261009:8000','source_revision':REV,'image_id':IMAGE_ID,'database_name':'spg_c2_qualification_20261009','captured_at_utc':datetime.now(timezone.utc).isoformat(),'model_credential_scope':'HUMAN_AUTHORIZED_SHARED_TEST','provider_ready':True,'provider_readiness_scope':'configuration only; no Provider request yet','deployment_receipt':'runtime-role-preparation.json'}
(E/'driver-runtime-identity.json').write_text(json.dumps(identity,indent=2)+'\n')
# A separate control runner needs only the new operator token, never the model key.
with (P/'driver-credentials.json').open('x') as stream:
    os.fchmod(stream.fileno(),0o600);json.dump({'operator_token':credentials['operator_token']},stream)
print(json.dumps({'new_roles':list(names.values()),'image_id':IMAGE_ID,'api_health':health,'provider_configuration':'READY','model_calls':0,'shared_provider_human_authorized':True}),flush=True)