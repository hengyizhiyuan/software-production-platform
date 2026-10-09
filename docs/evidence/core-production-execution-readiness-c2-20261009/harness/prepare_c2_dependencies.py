from pathlib import Path
from datetime import datetime,timezone
import json,os,secrets,subprocess,time
ROOT=Path('/data/watt/c2-execution-readiness-20261009')
LABELS={'watt.production':'false','watt.qualification':'C2-execution-readiness'}
PG='watt-c2-postgres-20261009'
GITEA='watt-c2-gitea-20261009'
CONTROL='watt-c2-control-20261009'
EXECUTOR='watt-c2-executor-20261009'
VOLUME='watt-c2-workspaces-20261009'
def invoke(args):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    if result.returncode:
        raise RuntimeError('Isolated action failed: '+args[0]+' '+args[1])
    return result.stdout.strip()
def exists(kind,name):
    return subprocess.run(['docker',kind,'inspect',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
assert ROOT.is_dir() and ROOT.stat().st_uid==0
for kind,name in [('container',PG),('container',GITEA),('network',CONTROL),('network',EXECUTOR),('volume',VOLUME)]:
    assert not exists(kind,name),('existing resource must be preserved',kind,name)
assert not (ROOT/'private').exists()
before=invoke(['docker','ps','--no-trunc','--format','{{.ID}}']).splitlines()
private=ROOT/'private';private.mkdir(mode=0o700)
credentials={'database_password':secrets.token_urlsafe(32),'operator_token':secrets.token_urlsafe(40),'tool_host_token':secrets.token_urlsafe(40),'gitea_password':secrets.token_urlsafe(32),'database_user':'c2_app','gitea_user':'watt-c2-qualification'}
private_file=private/'credentials.json'
with private_file.open('x') as stream:
    os.fchmod(stream.fileno(),0o600);json.dump(credentials,stream)
for name,uid in [('app',10001),('checkpoints',10001),('receipts',10001),('gitea-data',1000),('gitea-config',1000),('postgres',70),('evidence',10001)]:
    path=ROOT/name;path.mkdir(mode=0o750);os.chown(str(path),uid,uid)
labelargs=[]
for key,value in LABELS.items():labelargs+=['--label',key+'='+value]
invoke(['docker','network','create']+labelargs+[CONTROL])
invoke(['docker','network','create','--internal']+labelargs+[EXECUTOR])
invoke(['docker','volume','create']+labelargs+[VOLUME])
volume=json.loads(invoke(['docker','volume','inspect',VOLUME]))[0]
assert volume['Name']==VOLUME and volume['Labels']==LABELS
mountpoint=Path(volume['Mountpoint'])
assert str(mountpoint).endswith('/volumes/'+VOLUME+'/_data') and not list(mountpoint.iterdir())
os.chown(str(mountpoint),10001,10001);os.chmod(str(mountpoint),0o755)
def launch(name,image,env,mounts,extra=()):
    path=private/(name+'.env')
    with path.open('x') as stream:
        os.fchmod(stream.fileno(),0o600)
        for key,value in env.items():
            assert '\n' not in str(value) and '\r' not in str(value)
            stream.write(key+'='+str(value)+'\n')
    command=['docker','run','-d','--name',name,'--network',CONTROL,'--memory','512m','--cpus','0.5','--pids-limit','256']+labelargs+['--env-file',str(path)]
    for source,destination in mounts:command+=['--mount','type=bind,src='+str(source)+',dst='+destination]
    identifier=invoke(command+list(extra)+[image])
    return identifier
pgid=launch(PG,'public.ecr.aws/docker/library/postgres:17.6-alpine',{'POSTGRES_USER':credentials['database_user'],'POSTGRES_PASSWORD':credentials['database_password'],'POSTGRES_DB':'spg_c2_qualification_20261009'},[(ROOT/'postgres','/var/lib/postgresql/data')])
invoke(['docker','network','connect',EXECUTOR,PG])
giteaid=launch(GITEA,'docker.gitea.com/gitea:1.27.3-rootless',{'GITEA__database__DB_TYPE':'sqlite3','GITEA__server__ROOT_URL':'http://'+GITEA+':3000/','GITEA__server__HTTP_PORT':'3000','GITEA__security__INSTALL_LOCK':'true','GITEA__service__DISABLE_REGISTRATION':'true'},[(ROOT/'gitea-data','/var/lib/gitea'),(ROOT/'gitea-config','/etc/gitea')])
for check in range(30):
    pgready=subprocess.run(['docker','exec',PG,'pg_isready','-U',credentials['database_user'],'-d','spg_c2_qualification_20261009'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    gready=subprocess.run(['docker','exec',GITEA,'wget','-q','-O','/dev/null','http://127.0.0.1:3000/api/healthz'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if pgready and gready:break
    time.sleep(1)
assert pgready and gready,'new dependency readiness failed; preserve its evidence'
invoke(['docker','exec',PG,'createdb','-U',credentials['database_user'],'c1_contract_continuity'])
invoke(['docker','exec','--user','1000',GITEA,'gitea','admin','user','create','--username',credentials['gitea_user'],'--password',credentials['gitea_password'],'--email','c2-qualification@localhost.invalid','--admin','--must-change-password=false'])
safe=[]
for name in (PG,GITEA):
    data=json.loads(invoke(['docker','inspect',name]))[0]
    assert data['Config']['Labels']==LABELS and not data['HostConfig']['PortBindings']
    safe.append({'id':data['Id'],'name':data['Name'],'image_id':data['Image'],'image':data['Config']['Image'],'user':data['Config']['User'],'labels':data['Config']['Labels'],'networks':list(data['NetworkSettings']['Networks']),'mounts':data['Mounts'],'published_ports':data['HostConfig']['PortBindings']})
receipt={'captured_at_utc':datetime.now(timezone.utc).isoformat(),'qualification_root':str(ROOT),'existing_running_ids_before':before,'new_dependencies':safe,'control_network':CONTROL,'executor_network':EXECUTOR,'workspace_volume':VOLUME,'new_credentials_categories':['dedicated PostgreSQL','Operator API','Tool Host','isolated Gitea'],'production_credentials_copied':False,'provider_credential_status':'WAITING_INDEPENDENT_QUALIFICATION_CREDENTIAL','model_calls':0,'business_work_created':False,'shared_docker_daemon':True}
(ROOT/'evidence/dependency-preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'new_dependencies':[PG,GITEA],'workspace_volume':VOLUME,'new_private_credentials_generated':True,'production_credentials_copied':False,'model_calls':0}))
