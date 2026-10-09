from pathlib import Path
from datetime import datetime,timezone
import json,os,subprocess,time
ROOT=Path('/data/watt/c3-semantic-convergence-20261009');P=ROOT/'private';E=ROOT/'evidence'
credentials=json.loads((P/'credentials.json').read_text())
LABELS={'watt.production':'false','watt.qualification':'C3-semantic-convergence'}
PG='watt-c3-postgres-20261009';GITEA='watt-c3-gitea-20261009'
CONTROL='watt-c3-control-20261009';EXECUTOR='watt-c3-executor-20261009';VOLUME='watt-c3-workspaces-20261009'
def invoke(args):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    if result.returncode:raise RuntimeError('C3 isolated preparation action failed: '+args[0]+' '+args[1])
    return result.stdout.strip()
def exists(kind,name):
    return subprocess.run(['docker',kind,'inspect',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
pg=json.loads(invoke(['docker','inspect',PG]))[0]
assert pg['Config']['Labels'].items()>=LABELS.items() and pg['State']['Running']
for kind,name in [('container',GITEA),('network',EXECUTOR),('volume',VOLUME)]:assert not exists(kind,name)
labels=[]
for key,value in LABELS.items():labels+=['--label',key+'='+value]
for name,uid in [('app',10001),('receipts',10001),('gitea-data',1000),('gitea-config',1000)]:
    path=ROOT/name;assert not path.exists();path.mkdir(mode=0o755);os.chown(str(path),uid,uid)
for name in ('managed-source','native-executor','owner-runtime','production-environments','native-tool-receipts','native-workspaces'):
    path=ROOT/'app'/name;path.mkdir(mode=0o750);os.chown(str(path),10001,10001)
invoke(['docker','network','create','--internal']+labels+[EXECUTOR])
invoke(['docker','network','connect',EXECUTOR,PG])
invoke(['docker','volume','create']+labels+[VOLUME])
volume=json.loads(invoke(['docker','volume','inspect',VOLUME]))[0]
assert volume['Name']==VOLUME and volume['Labels']==LABELS
mountpoint=Path(volume['Mountpoint']);assert str(mountpoint).endswith('/volumes/'+VOLUME+'/_data') and not list(mountpoint.iterdir())
os.chown(str(mountpoint),10001,10001);os.chmod(str(mountpoint),0o755)
image='sha256:071efa747340e5e211213fc79a0b928003bedf9b6b48f61cb32b3c52bfd1e09e'
assert invoke(['docker','image','inspect','--format','{{.Id}}',image])==image
env={'GITEA__database__DB_TYPE':'sqlite3','GITEA__server__ROOT_URL':'http://'+GITEA+':3000/',
    'GITEA__server__HTTP_PORT':'3000','GITEA__security__INSTALL_LOCK':'true','GITEA__service__DISABLE_REGISTRATION':'true'}
envfile=P/'c3-gitea.env'
with envfile.open('x') as stream:
    os.fchmod(stream.fileno(),0o600)
    for key,value in env.items():stream.write(key+'='+value+'\n')
gid=invoke(['docker','run','-d','--name',GITEA,'--network',CONTROL,'--memory','512m','--cpus','0.5','--pids-limit','256']+
    labels+['--env-file',str(envfile),'--mount','type=bind,src='+str(ROOT/'gitea-data')+',dst=/var/lib/gitea',
    '--mount','type=bind,src='+str(ROOT/'gitea-config')+',dst=/etc/gitea',image])
ready=False
for index in range(25):
    ready=subprocess.run(['docker','exec',GITEA,'wget','-q','-O','/dev/null','http://127.0.0.1:3000/api/healthz'],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if ready:break
    time.sleep(1)
assert ready,'Preserve failed Gitea readiness, do not recreate it'
invoke(['docker','exec','--user','1000',GITEA,'gitea','admin','user','create','--username',credentials['gitea_user'],
    '--password',credentials['gitea_password'],'--email','c3-qualification@localhost.invalid','--admin','--must-change-password=false'])
data=json.loads(invoke(['docker','inspect',GITEA]))[0]
receipt={'schema':'c3-runtime-dependencies-v1','captured_at_utc':datetime.now(timezone.utc).isoformat(),
    'gitea_container_id':gid,'gitea_image_id':data['Image'],'gitea_mounts':data['Mounts'],
    'published_ports':data['HostConfig']['PortBindings'],'executor_network':EXECUTOR,'workspace_volume':VOLUME,
    'independent_gitea_credentials':True,'application_roles_created':False,'real_work_created':0,'provider_calls':0,
    'old_data_or_services_modified':False}
(E/'runtime-dependency-preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'new_gitea':GITEA,'ready':ready,'workspace_volume':VOLUME,'model_calls':0,'work_created':0}))
