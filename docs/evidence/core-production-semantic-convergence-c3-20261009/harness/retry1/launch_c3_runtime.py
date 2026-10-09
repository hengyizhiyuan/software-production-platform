import sys
sys.dont_write_bytecode = True
from c3_retry_scope import scoped_runtime_root, verify_frozen_controls, read_built_identity
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,socket,subprocess,time
from urllib.request import urlopen
ROOT=scoped_runtime_root("launch_c3_runtime.py");P=ROOT/'private';E=ROOT/'evidence'
freeze=verify_frozen_controls(ROOT)
build=read_built_identity(ROOT,freeze)
IMAGE_ID=build['image']['Id'];IMAGE=IMAGE_ID;REV=build['sources']['watt']['revision']
assert subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',IMAGE],universal_newlines=True).strip()==IMAGE_ID
names={role:'watt-c3-retry1-'+role+'-20261009' for role in ('api','coordinator','worker','tool-host')}
for name in names.values():
    assert subprocess.run(['docker','inspect',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0,('preserve existing',name)
with socket.socket() as check:
    check.bind(('127.0.0.1',18301))
preparation=json.loads((E/'isolation-preparation.json').read_text())
assert preparation['qualification_root']==str(ROOT) and preparation['new_database']=='spg_c3_retry1_qualification_20261009'
assert preparation['workspace_volume']=='watt-c3-retry1-workspaces-20261009'
assert preparation['role_names']==names
credentials=json.loads((P/'credentials.json').read_text())
credentials['database_user']='c3_app';credentials['database_password']=credentials['postgres_password']
# Read the authorized C3 private copy; never inspect old N1 configuration.
provider_file=P/'provider.env'
assert provider_file.is_file() and not provider_file.is_symlink() and provider_file.stat().st_mode & 0o077 == 0
source_env=dict(line.split('=',1) for line in provider_file.read_text().splitlines() if '=' in line)
provider_key=source_env.get('SPG_DEEPSEEK_API_KEY')
provider_base=source_env.get('SPG_DEEPSEEK_BASE_URL')
assert provider_key and provider_base=='https://api.deepseek.com'
image=json.loads(subprocess.check_output(['docker','image','inspect',IMAGE],universal_newlines=True))[0]
for setting in image['Config']['Env']:
    key,value=setting.split('=',1)
    if any(part in key for part in ('API_KEY','ACCESS_KEY','PASSWORD','TOKEN')):
        assert not value,('Unexpected embedded credential',key)
url='postgresql+psycopg://'+credentials['database_user']+':'+credentials['database_password']+'@watt-c3-postgres-20261009:5432/spg_c3_retry1_qualification_20261009'
dbfile=P/'c3-retry1-main-db.env'
with dbfile.open('x') as stream:
    os.fchmod(stream.fileno(),0o600);stream.write('SPG_DATABASE_URL='+url+'\n')
raw=P/'main-migration.raw.log'
with raw.open('x') as stream:
    os.fchmod(stream.fileno(),0o600)
    migration=subprocess.run(['docker','run','--name','watt-c3-retry1-migration-20261009',
        '--network','watt-c3-control-20261009','--user','10001:10001','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,nosuid,size=64m',
        '--label','watt.production=false','--label','watt.qualification=C3-semantic-convergence-retry1',
        '--env-file',str(dbfile),IMAGE_ID,'python','-m','alembic','upgrade','head'],
        stdout=stream,stderr=subprocess.STDOUT)
assert migration.returncode==0,'Preserve failed migration; no Work created'
safe=raw.read_text(errors='replace')
for value in list(credentials.values())+[provider_key]:
    if isinstance(value,str) and len(value)>20:safe=safe.replace(value,'[REDACTED]')
(E/'migration.log').write_text(safe)
head=subprocess.check_output(['docker','exec','watt-c3-postgres-20261009','psql','-U','c3_app',
    '-d','spg_c3_retry1_qualification_20261009','-Atc','select version_num from alembic_version'],universal_newlines=True).strip()
assert head=='20261007_72', ('migration identity mismatch',head)
(E/'migration.json').write_text(json.dumps({'captured_at_utc':datetime.now(timezone.utc).isoformat(),
    'image_id':IMAGE_ID,'source_revision':REV,'database':'spg_c3_retry1_qualification_20261009',
    'migration_head':head,'exit_code':migration.returncode,'production_database_modified':False},indent=2)+'\n')
common={'SPG_DATABASE_URL':url,'SPG_RUNTIME_PROFILE':'c3-semantic-convergence-retry1-20261009','SPG_RUNTIME_REVISION':REV,'SPG_AUTH_MODE':'required','SPG_OPERATOR_TOKEN':credentials['operator_token'],'SPG_NATIVE_EXECUTOR_ENABLED':'true','SPG_EXECUTOR_ADAPTER':'watt-native','SPG_VERIFICATION_ADAPTER':'contract-driven-repository','SPG_OWNER_RUNTIME_MODE':'REQUIRED','SPG_OWNER_RUNTIME_STORE_ROOT':'/var/lib/spg/owner-runtime','SPG_WORKSPACE_ROOT':'/var/lib/spg/native-workspaces','SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT':'/var/lib/spg/native-workspaces','SPG_NATIVE_EXECUTOR_STORAGE_ROOT':'/var/lib/spg/native-executor','SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_STORE_ROOT':'/var/lib/spg/production-environments','SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_WORKSPACE_VOLUME':'watt-c3-retry1-workspaces-20261009','SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_IMAGE':IMAGE_ID,'SPG_NATIVE_EXECUTOR_INFERENCE_PROVIDER':'deepseek','SPG_NATIVE_EXECUTOR_INFERENCE_MODEL':'deepseek-flash','SPG_NATIVE_EXECUTOR_INFERENCE_REASONING_EFFORT':'high','SPG_NATIVE_EXECUTOR_WORKER_ID':'watt-c3-retry1-real-worker-20261009','SPG_NATIVE_EXECUTOR_WORKER_PROFILE':'local-container-v1','SPG_NATIVE_EXECUTOR_RESOURCE_PROFILE':'standard','SPG_NATIVE_EXECUTOR_TOOL_HOST_URL':'http://'+names['tool-host']+':8011','SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN':credentials['tool_host_token'],'SPG_DEEPSEEK_API_KEY':provider_key,'SPG_DEEPSEEK_BASE_URL':provider_base,'SPG_NATIVE_EXECUTOR_DEEPSEEK_API_KEY':provider_key,'SPG_NATIVE_EXECUTOR_DEEPSEEK_BASE_URL':provider_base,'SPG_WIC_PROVIDER_ADAPTER':'deepseek','SPG_CONVERSATION_PROVIDER_ADAPTER':'deepseek','SPG_WIC_PROVIDER_MODEL':'deepseek-flash','SPG_CONVERSATION_PROVIDER_MODEL':'deepseek-flash','SPG_WIC_RUNTIME_MODE':'WIC_VNEXT_CONTROLLED','SPG_MANAGED_SOURCE_PROVIDER':'gitea','SPG_MANAGED_SOURCE_ENDPOINT':'http://watt-c3-gitea-20261009:3000','SPG_MANAGED_SOURCE_PUBLIC_ENDPOINT':'http://watt-c3-gitea-20261009:3000','SPG_MANAGED_SOURCE_USERNAME':credentials['gitea_user'],'SPG_MANAGED_SOURCE_PASSWORD':credentials['gitea_password'],'SPG_MANAGED_SOURCE_NAMESPACE':credentials['gitea_user'],'SPG_MANAGED_SOURCE_WORKSPACE_ROOT':'/var/lib/spg/managed-source','SPG_DELIVERY_RUNTIME_ENABLED':'false','SPG_REPOSITORY_PATH':'/var/lib/spg/managed-source'}
toolenv={'SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT':'/var/lib/spg/native-workspaces','SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_WORKSPACE_VOLUME':'watt-c3-retry1-workspaces-20261009','SPG_NATIVE_EXECUTOR_CONTAINER_ISOLATION_REQUIRED':'true','SPG_NATIVE_EXECUTOR_TOOL_HOST_ISOLATION':'production-environment-only','SPG_NATIVE_EXECUTOR_RECEIPT_SPOOL_ROOT':'/var/lib/spg/native-tool-receipts','SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN':credentials['tool_host_token'],'SPG_RUNTIME_REVISION':REV,'SPG_RUNTIME_PROFILE':'c3-semantic-convergence-retry1-20261009'}
commands={'api':['python','-m','uvicorn','spg.api.http:create_http_application','--factory','--host','0.0.0.0','--port','8000'],'coordinator':['python','-m','spg.executor_coordinator'],'worker':['python','-m','spg.executor_worker'],'tool-host':['python','-m','uvicorn','spg.tool_host_api:create_tool_host_application','--factory','--host','0.0.0.0','--port','8011']}
labels=['--label','watt.production=false','--label','watt.qualification=C3-semantic-convergence-retry1']
for child in ('managed-source','native-executor','owner-runtime','production-environments'):
    path=ROOT/'app'/child
    if path.exists():
        assert path.is_dir() and not path.is_symlink() and not list(path.iterdir()), ('preserve unexpected existing workspace',child)
    else:path.mkdir(mode=0o750)
    assert path.stat().st_uid==10001, ('unexpected workspace owner',child)
    os.chmod(str(path),0o750)
# Evidence output belongs only to this isolated qualification runner.
os.chown(str(E),10001,10001)
def invoke(args):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    if result.returncode:raise RuntimeError('C3 action failed: '+args[0]+' '+args[1])
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
    command=['docker','run','-d','--name',name,'--network','watt-c3-control-20261009','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m,mode=1777','--memory',{'api':'1536m','worker':'1024m','coordinator':'512m','tool-host':'512m'}[role],'--cpus','1','--pids-limit','256']+labels+['--env-file',str(envfile)]
    command+=['--mount','type=bind,src='+str(ROOT/'app')+',dst=/var/lib/spg'+(',readonly' if role=='tool-host' else ''),'--mount','type=volume,src=watt-c3-retry1-workspaces-20261009,dst=/var/lib/spg/native-workspaces']
    if role in ('api','tool-host'):
        command+=['--mount','type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock','--group-add',str(Path('/var/run/docker.sock').stat().st_gid)]
    if role=='tool-host':command+=['--mount','type=bind,src='+str(ROOT/'receipts')+',dst=/var/lib/spg/native-tool-receipts']
    if role=='api':command+=['--publish','127.0.0.1:18301:8000']
    invoke(command+[IMAGE_ID]+commands[role])
    invoke(['docker','network','connect','watt-c3-executor-20261009',name])
    data=json.loads(invoke(['docker','inspect',name]))[0]
    assert data['Image']==IMAGE_ID and data['Config']['User']=='10001:10001'
    receipts.append({'role':role,'name':name,'container_id':data['Id'],'image_id':data['Image'],'command':commands[role],'labels':data['Config']['Labels'],'mounts':data['Mounts'],'user':data['Config']['User'],'group_add':data['HostConfig']['GroupAdd'],'networks':list(data['NetworkSettings']['Networks']),'ports':data['HostConfig']['PortBindings'],'read_only_root':data['HostConfig']['ReadonlyRootfs']})
    (E/'runtime-role-preparation.json').write_text(json.dumps({'captured_at_utc':datetime.now(timezone.utc).isoformat(),'roles':receipts,'source_revision':REV,'database':'spg_c3_retry1_qualification_20261009','model_credential_scope':'HUMAN_AUTHORIZED_SHARED_TEST','human_authorization':'explicit reply 2026-10-09: reuse existing test credential','production_resources_modified':False,'shared_docker_daemon':True},indent=2)+'\n')
for role,name in names.items():
    invoke(['docker','exec',name,'python','/opt/c3-build/attest_c3_image.py','--image-id',IMAGE_ID,
        '--output','/tmp/c3-role-import-attestation.json'])
    captured=invoke(['docker','exec',name,'cat','/tmp/c3-role-import-attestation.json'])
    (E/(role+'-import-attestation.json')).write_text(captured+'\n')
health=None
for index in range(20):
    try:
        with urlopen('http://127.0.0.1:18301/health',timeout=2) as response:health=json.load(response)
        break
    except Exception:time.sleep(1)
assert health and health.get('service')=='available'
provider=json.loads(invoke(['docker','exec',names['worker'],'python','-m','spg.executor_worker','--check-readiness']))
assert provider['status']=='READY' and provider['provider_request_sent'] is False
(E/'provider-config-readiness.json').write_text(json.dumps(provider,indent=2)+'\n')
identity={'qualification':'C3','qualification_run':'retry-1','isolated':True,'api_service':names['api'],'api_base_url':'http://watt-c3-retry1-api-20261009:8000','source_revision':REV,'image_id':IMAGE_ID,'database_name':'spg_c3_retry1_qualification_20261009','captured_at_utc':datetime.now(timezone.utc).isoformat(),'model_credential_scope':'HUMAN_AUTHORIZED_SHARED_TEST','provider_ready':True,'provider_readiness_scope':'configuration only; no Provider request yet','deployment_receipt':'runtime-role-preparation.json'}
(E/'driver-runtime-identity.json').write_text(json.dumps(identity,indent=2)+'\n')
# A separate control runner needs only the new operator token, never the model key.
with (P/'driver-credentials.json').open('x') as stream:
    os.fchmod(stream.fileno(),0o600);json.dump({'operator_token':credentials['operator_token']},stream)
print(json.dumps({'new_roles':list(names.values()),'image_id':IMAGE_ID,'api_health':health,'provider_configuration':'READY','model_calls':0,'shared_provider_human_authorized':True}),flush=True)