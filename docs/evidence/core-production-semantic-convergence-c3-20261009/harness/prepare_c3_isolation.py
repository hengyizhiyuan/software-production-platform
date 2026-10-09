from pathlib import Path
from datetime import datetime,timezone
import base64,json,os,secrets,subprocess
import urllib.request
ROOT=Path('/data/watt/c3-semantic-convergence-20261009')
assert not ROOT.exists(),'Existing C3 resources must be inspected rather than overwritten'
def call(args):
    return subprocess.check_output(args,universal_newlines=True).strip()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
endpoint='http://100.100.100.200/latest/'
token=opener.open(urllib.request.Request(endpoint+'api/token',
    headers={'X-aliyun-ecs-metadata-token-ttl-seconds':'60'},method='PUT'),timeout=5).read().decode()
def metadata(name):
    return opener.open(urllib.request.Request(endpoint+'meta-data/'+name,
        headers={'X-aliyun-ecs-metadata-token':token}),timeout=5).read().decode()
instance,region=metadata('instance-id'),metadata('region-id')
assert instance=='i-0jl386xnbauudq5j9jk0' and region=='cn-wulanchabu'
assert call(['git','-C','/data/watt/runtime/source','rev-parse','HEAD'])=='ee5bd86a53891f9391785c91d0ccef81ad2d56c3'
assert not call(['git','-C','/data/watt/runtime/source','status','--porcelain'])
old_running=call(['docker','ps','--no-trunc','--format','{{.ID}}']).splitlines()
c2=json.loads(Path('/data/watt/c2-execution-readiness-20261009/quiescence-and-preservation.json').read_text()) if Path('/data/watt/c2-execution-readiness-20261009/quiescence-and-preservation.json').exists() else json.loads(Path('/data/watt/c2-execution-readiness-20261009/evidence/quiescence-and-preservation.json').read_text())
for row in c2['new_c2_stopped_only']:
    assert call(['docker','inspect','--format','{{.State.Status}}',row['container_id']])=='exited'
ROOT.mkdir(mode=0o755)
P=ROOT/'private';E=ROOT/'evidence'
P.mkdir(mode=0o700);E.mkdir(mode=0o755)
credentials={'postgres_password':secrets.token_urlsafe(36),
'operator_token':secrets.token_urlsafe(36),'tool_host_token':secrets.token_urlsafe(36),
'gitea_user':'watt-c3-qualification','gitea_password':secrets.token_urlsafe(36)}
def private_file(name,body):
    path=P/name
    with path.open('x') as stream:
        os.fchmod(stream.fileno(),0o600);stream.write(body)
private_file('credentials.json',json.dumps(credentials,indent=2)+'\n')
pg='watt-c3-postgres-20261009';network='watt-c3-control-20261009'
PG_IMAGE='sha256:d741b376874687de90374fd34f55c6b2760e8f7bd7e4ae5cd47f50757fc08cf8'
assert call(['docker','image','inspect','--format','{{.Id}}',PG_IMAGE])==PG_IMAGE
BASE='sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209'
assert call(['docker','image','inspect','--format','{{.Id}}',BASE])==BASE
labels=['--label','watt.production=false','--label','watt.qualification=C3-semantic-convergence']
private_file('c3-postgres.env','POSTGRES_USER=c3_app\nPOSTGRES_PASSWORD='+credentials['postgres_password']+'\nPOSTGRES_DB=spg_c3_qualification_20261009\n')
private_file('c3-test.env',
'SPG_TEST_POSTGRES_DSN=postgresql://c3_app:'+credentials['postgres_password']+'@127.0.0.1:5432/c3_contract_regression\n'
+'SPG_DATABASE_URL=postgresql://c3_app:'+credentials['postgres_password']+'@127.0.0.1:5432/c3_contract_regression\n'
+'PYTHONPATH=/qualification/src:/qualification:/opt/c2-test-deps:/opt/c2-owners/guardian/src:/opt/c2-owners/ecf/src\n'
+'PYTHONDONTWRITEBYTECODE=1\n')
(ROOT/'postgres').mkdir(mode=0o700)
call(['docker','network','create']+labels+[network])
container=call(['docker','run','-d','--name',pg,'--network',network,
'--env-file',str(P/'c3-postgres.env'),
'--mount','type=bind,src='+str(ROOT/'postgres')+',dst=/var/lib/postgresql/data']+labels+[PG_IMAGE])
receipt={'schema':'c3-isolated-preparation-v1','captured_at_utc':datetime.now(timezone.utc).isoformat(),
'instance_id':instance,'region':region,'qualification_root':str(ROOT),'postgres_container_id':container,
'postgres_image_id':PG_IMAGE,'control_network':network,
'new_database':'spg_c3_qualification_20261009','test_database':'c3_contract_regression',
'dependency_test_base_image':BASE,'base_is_final_qualified_c3_image':False,
'new_independent_control_credentials':True,'model_credential_scope':'HUMAN_AUTHORIZED_SHARED_TEST',
'model_key_copied_for_runtime':False,'original_running_ids':old_running,
'c2_services_remain_stopped':True,'canonical_source_clean':True,
'canonical_source_revision':'ee5bd86a53891f9391785c91d0ccef81ad2d56c3',
'original_business_data_copied':False,'runtime_roles_created':False,'real_works_created':0}
(E/'isolation-preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'new_root':str(ROOT),'postgres_container':pg,'new_control_credentials_generated':True,'old_services_preserved':True,'model_key_printed':False,'runtime_roles_or_work_created':False}))
