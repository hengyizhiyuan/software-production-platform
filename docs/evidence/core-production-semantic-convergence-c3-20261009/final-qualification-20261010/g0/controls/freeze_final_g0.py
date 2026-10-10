from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json,os,subprocess,tarfile
R=Path('/data/watt/c3-semantic-convergence-20261009/final-g0-qualification-20261010')
REC=R.parent/'final-g0-recovery-20261010';E=R/'evidence'
assert not REC.exists();assert (E/'normal-entry-runner.json').is_file()
state=json.loads((E/'normal-entry-state.json').read_text());review=json.loads((E/'real-g0-terminal-review.json').read_text())
assert state['driver_status']=='BOUNDED_OBSERVATION_WINDOW_ENDED'
assert review['formation_logical_calls']==2 and review['table_counts']['execution_attempts']==review['table_counts']['baseline_candidates']==0
def call(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 assert p.returncode==0,'NEW_QUALIFICATION_CHECKPOINT_COMMAND_FAILED'
 return p.stdout
def inspect(n):return json.loads(call(['docker','inspect',n]).decode())[0]
def digest(p):
 h=sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
before=json.loads((E/'preparation-preflight.json').read_text())
old_before=before['original_running_container_ids']
old_states=[{'id':n,'running':inspect(n)['State']['Running']} for n in old_before]
assert all(x['running'] for x in old_states),'PREEXISTING_CONTAINER_STATE_CHANGED_REVIEW_REQUIRED'
roles=['watt-c3-finalg0-'+r+'-20261010' for r in ('api','coordinator','worker','tool-host')]
PG='watt-c3-finalg0-postgres-20261010';GI='watt-c3-finalg0-gitea-20261010'
for n in roles+[PG,GI]:
 x=inspect(n);assert x['Config']['Labels']['watt.production']=='false' and x['Config']['Labels']['watt.qualification']=='C3-final-g0'
 for m in x['Mounts']:
  if m['Type']=='bind' and m['Source']!='/var/run/docker.sock':assert Path(m['Source']).resolve().is_relative_to(R) if hasattr(Path(), 'is_relative_to') else str(Path(m['Source']).resolve()).startswith(str(R)+'/')
REC.mkdir(mode=0o700)
start=datetime.now(timezone.utc).isoformat()
call(['docker','stop']+roles)
DB='spg_c3_finalg0_qualification_20261010'
dump=REC/'qualification.pgcustom'
with dump.open('xb') as f:
 os.fchmod(f.fileno(),0o600)
 result=subprocess.run(['docker','exec',PG,'pg_dump','-U','c3_app','-d',DB,'-Fc','--serializable-deferrable'],stdout=f,stderr=subprocess.PIPE)
assert result.returncode==0 and dump.read_bytes()[:5]==b'PGDMP'
listing=call(['docker','exec','-i',PG,'pg_restore','--list'],) if False else subprocess.run(['docker','exec','-i',PG,'pg_restore','--list'],input=dump.read_bytes(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
assert listing.returncode==0
with (REC/'dump-list.private.txt').open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(listing.stdout)
call(['docker','stop',PG,GI])
archive=REC/'qualification-root.tar.gz'
with tarfile.open(str(archive),'x:gz') as a:a.add(str(R),arcname=R.name)
os.chmod(str(archive),0o600)
with tarfile.open(str(archive),'r:gz') as a:members=a.getmembers();assert members and all(not m.name.startswith('/') and '..' not in Path(m.name).parts for m in members)
vol='watt-c3-finalg0-workspaces-20261010';v=json.loads(call(['docker','volume','inspect',vol]).decode())[0]
assert v['Labels']['watt.production']=='false'
volume=REC/'workspace-volume.tar.gz'
with tarfile.open(str(volume),'x:gz') as a:a.add(v['Mountpoint'],arcname='workspace-volume')
os.chmod(str(volume),0o600)
source=call(['git','-C','/data/watt/runtime/source','rev-parse','HEAD']).decode().strip()
main=call(['git','-C','/data/watt/runtime/source','rev-parse','refs/heads/main']).decode().strip()
assert source=='5de657f3cb65780adf50f6557b54171a6c3cfae5' and main=='ee5bd86a53891f9391785c91d0ccef81ad2d56c3'
old_basis=R.parent/'public-delivery-c3-final/retry-1/g0-owner-2/20261009T130020024208Z-2fc7b990c1b54846a25bd067bc94b849-canonical-work.json'
assert digest(old_basis)=='9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c'
images=R.parent/'semantic-contract-implementation-20261010/review-primary-qualified-20261010/image-recovery/exact-image.tar.gz'
assert digest(images)=='286053124619831b03f243c02f79b35df6408035fe86e234c752a40df465a377'
d={'schema':'c3-final-g0-private-recovery-checkpoint-v1','started_at_utc':start,'finished_at_utc':datetime.now(timezone.utc).isoformat(),'work_id':state['work_id'],'result':'G0_FAIL_C3_PARTIAL','private_recovery_directory':str(REC),'archives':[{'path':str(p),'sha256':digest(p),'bytes':p.stat().st_size} for p in (dump,archive,volume)],'exact_application_image_archive':str(images),'exact_application_image_archive_sha256':digest(images),'image_id':review['image'],'database':DB,'migration':'20261007_72','pg_dump_exit_code':result.returncode,'pg_restore_list_exit_code':listing.returncode,'dump_consistency':'pg_dump read-only consistent snapshot after new application roles quiesced; filesystem archive after new PG/Gitea cold stop; not one cross-resource transaction','stopped_only_new_names':roles+[PG,GI],'preexisting_container_states':old_states,'original_ecs_head':source,'original_ecs_main_ref':main,'original_historical_basis_sha256':digest(old_basis),'production_modified':False,'historical_work_modified':False,'model_calls':0,'restore_test':'NOT_PERFORMED','offsite_backup':'NOT_PERFORMED','private_archive_contains_credentials':True,'public_release_contains_private_archive':False}
with (REC/'checkpoint.json').open('x') as f:os.fchmod(f.fileno(),0o600);json.dump(d,f,indent=2)
with (E/'private-recovery-checkpoint.json').open('x') as f:json.dump(d,f,indent=2)
print(json.dumps({'result':d['result'],'recovery_directory':str(REC),'stopped_only_new_roles':len(roles)+2,'preexisting_containers_unchanged':len(old_states),'restore_test':'NOT_PERFORMED'}))
