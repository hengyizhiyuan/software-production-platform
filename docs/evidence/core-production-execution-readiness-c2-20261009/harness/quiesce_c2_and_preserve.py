from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import base64,json,os,subprocess,tarfile
ROOT=Path('/data/watt/c2-execution-readiness-20261009');P=ROOT/'private';E=ROOT/'evidence';IMAGE_ID='sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209'
state=json.loads((E/'normal-entry-state.json').read_text());assert state['latest_observation']['work_status']=='NEEDS_ATTENTION' and state['latest_observation']['automatic_progression_state']=='STOPPED'
before=json.loads((E/'dependency-preparation.json').read_text())['existing_running_ids_before']
def call(args):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    assert result.returncode==0,'C2 finish action failed: '+args[0]+' '+args[1]
    return result.stdout.strip()
stopped=[]
for name in ['watt-c2-'+role+'-20261009' for role in ('worker','coordinator','api','tool-host','gitea')]:
    data=json.loads(call(['docker','inspect',name]))[0]
    assert data['Config']['Labels'].get('watt.qualification')=='C2-execution-readiness' and data['Config']['Labels'].get('watt.production')=='false'
    assert any(mount.get('Source','').startswith(str(ROOT)) for mount in data['Mounts'])
    identifier=data['Id'];call(['docker','stop','--time','10',identifier])
    after=json.loads(call(['docker','inspect',identifier]))[0]
    stopped.append({'name':name,'container_id':identifier,'state':after['State']['Status'],'image_id':after['Image'],'purpose':'C2 quiescence after failed Work; preserve containers/data for recovery'})
volume=json.loads(call(['docker','volume','inspect','watt-c2-workspaces-20261009']))[0]
assert volume['Labels'].get('watt.qualification')=='C2-execution-readiness'
archive_path=P/'runtime-data-quiesced-20261009.tar.gz';assert not archive_path.exists()
with archive_path.open('xb') as stream:
    os.fchmod(stream.fileno(),0o600)
    with tarfile.open(fileobj=stream,mode='w:gz',dereference=False) as archive:
        for child in ('app','receipts','gitea-data','gitea-config'):archive.add(str(ROOT/child),arcname=child)
        archive.add(volume['Mountpoint'],arcname='native-workspaces')
digest=sha256()
with archive_path.open('rb') as stream:
    for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
pg=json.loads(call(['docker','inspect','watt-c2-postgres-20261009']))[0]
assert pg['Config']['Labels'].get('watt.qualification')=='C2-execution-readiness'
call(['docker','stop','--time','10',pg['Id']]);stopped.append({'name':'watt-c2-postgres-20261009','container_id':pg['Id'],'state':'exited','image_id':pg['Image'],'purpose':'C2 database preserved on its isolated bind after consistent pg_dump'})
remaining=set(call(['docker','ps','--no-trunc','--format','{{.ID}}']).splitlines());assert set(before).issubset(remaining)
source_head=call(['git','-C','/data/watt/runtime/source','rev-parse','HEAD']);assert source_head=='ee5bd86a53891f9391785c91d0ccef81ad2d56c3'
source_status=call(['git','-C','/data/watt/runtime/source','status','--porcelain']);assert not source_status
receipt={'captured_at_utc':datetime.now(timezone.utc).isoformat(),'new_c2_stopped_only':stopped,'production_and_old_n1_running_ids_retained':before,'all_original_running_ids_still_running':True,'canonical_source_revision':source_head,'canonical_source_clean':True,'new_failed_work_preserved':state['work_id'],'new_c2_volume_retained':volume['Name'],'private_quiesced_runtime_archive':{'path':str(archive_path),'size_bytes':archive_path.stat().st_size,'sha256':digest.hexdigest(),'consistency':'All new C2 app roles and isolated Gitea stopped before archive; private data only'},'database_backup':'persistent-recovery.json','business_work_mutation_by_shutdown':False,'historical_records_modified':False}
(E/'quiescence-and-preservation.json').write_text(json.dumps(receipt,indent=2)+'\n')
# Known value scan, no secret/prefix/hash is displayed or copied.
secret_values=[]
for path in P.glob('*.env'):
    for line in path.read_text().splitlines():
        if '=' not in line:continue
        key,value=line.split('=',1)
        if value and any(word in key for word in ('KEY','TOKEN','PASSWORD','DATABASE_URL')):secret_values.append(value.encode())
credentials=json.loads((P/'credentials.json').read_text())
secret_values += [str(value).encode() for key,value in credentials.items() if any(word in key for word in ('password','token'))]
secret_values.append(base64.b64encode((credentials['gitea_user']+':'+credentials['gitea_password']).encode()))
scanned=0;matches=[]
for path in E.rglob('*'):
    if not path.is_file():continue
    raw=path.read_bytes();scanned+=1
    if any(value in raw for value in secret_values):matches.append(path.relative_to(E).as_posix())
assert not matches,('Known credential public artifact matches; do not publish',matches)
(E/'credential-publication-scan.json').write_text(json.dumps({'captured_at_utc':datetime.now(timezone.utc).isoformat(),'scanned_files':scanned,'known_credential_matches':0,'private_directory_excluded':True,'model_credential_scope':'HUMAN_AUTHORIZED_SHARED_TEST','model_key_changed_or_rotated':False,'scope':'Exact known private credential values only; not a universal secret detector'},indent=2)+'\n')
print(json.dumps({'new_c2_roles_quiesced':len(stopped),'original_running_ids_unchanged':True,'canonical_source_clean':True,'known_public_credential_matches':0,'failed_work_preserved':state['work_id']}),flush=True)