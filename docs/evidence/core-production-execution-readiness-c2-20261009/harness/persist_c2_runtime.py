from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,subprocess,tarfile
ROOT=Path('/data/watt/c2-execution-readiness-20261009');P=ROOT/'private';E=ROOT/'evidence';IMAGE_ID='sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209'
snapshot=json.loads(next((E/'canonical-freeze').glob('*canonical-work.json')).read_text());binding=snapshot['datasets']['native_attempt_bindings']['rows'][0]['binding_payload']
attempt=binding['attempt_id'];workspace=binding['workspace']['host_storage_id'];member=binding['source_vector']['members'][0]
assert attempt=='74ba6435-c067-4277-9d2d-2d0bae4a87a5' and workspace=='/var/lib/spg/native-workspaces/'+attempt
worker='watt-c2-worker-20261009'
def call(args,input=None):
    result=subprocess.run(args,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert result.returncode==0,'C2 recovery action failed: '+args[0]+' '+args[1]
    return result.stdout
for role in ('api','worker','coordinator','tool-host'):
    name='watt-c2-'+role+'-20261009';data=json.loads(call(['docker','inspect',name]))[0]
    assert data['Image']==IMAGE_ID and data['Config']['Labels'].get('watt.qualification')=='C2-execution-readiness'
    call(['docker','exec',name,'python','/opt/c2-build/attest_c2_image.py','--image-id',IMAGE_ID,'--output','/tmp/c2-final-attestation.json'])
    raw=call(['docker','exec',name,'cat','/tmp/c2-final-attestation.json'])
    (E/(role+'-final-import-attestation.json')).write_bytes(raw)
pe=next(value.split(':',1)[1] for value in binding['workspace']['service_resources'] if value.startswith('production-environment-handle:'))
data=json.loads(call(['docker','inspect',pe]))[0];assert data['Image']==IMAGE_ID
(E/'actual-production-environment.json').write_text(json.dumps({'captured_at_utc':datetime.now(timezone.utc).isoformat(),'container_id':data['Id'],'image_id':data['Image'],'user':data['Config']['User'],'mounts':data['Mounts'],'network_mode':data['HostConfig']['NetworkMode'],'read_only_root':data['HostConfig']['ReadonlyRootfs'],'labels':data['Config']['Labels'],'source_revision':data['Config']['Labels'].get('org.opencontainers.image.revision'),'identity_scope':'actual Native Tool Production Environment; metadata only'},indent=2)+'\n')
output=call(['docker','exec',worker,'git','-C',workspace,'rev-parse','HEAD']).decode().strip()
output_tree=call(['docker','exec',worker,'git','-C',workspace,'rev-parse','HEAD^{tree}']).decode().strip()
source=member['source_commit_oid'];source_tree=call(['docker','exec',worker,'git','-C',workspace,'rev-parse',source+'^{tree}']).decode().strip()
assert source_tree==member['source_tree_oid']
assert output=='7fcaeb4498b6f0bc2ca4d153414384308cb70cd9' and output_tree=='95b94416d825a3e87e85d2244eaa18300d390a6d'
changed=call(['docker','exec',worker,'git','-C',workspace,'diff','--name-status',source,output,'--']).decode().splitlines()
artifact=call(['docker','exec',worker,'git','-C',workspace,'show',output+':index.html'])
pack=call(['docker','exec','-i',worker,'git','-C',workspace,'pack-objects','--stdout','--revs'],(source+'\n'+output+'\n').encode())
witness=E/'git-witness';witness.mkdir(mode=0o750)
(witness/'source-output.pack').write_bytes(pack);(witness/'index.html').write_bytes(artifact)
(witness/'manifest.json').write_text(json.dumps({'captured_at_utc':datetime.now(timezone.utc).isoformat(),'work_id':binding['work_id'],'pwu_id':binding['pwu_id'],'attempt_id':attempt,'workspace_id':binding['workspace']['workspace_id'],'workspace':workspace,'source_revision':source,'source_tree':source_tree,'output_revision':output,'output_tree':output_tree,'changed_paths':changed,'artifact_sha256':sha256(artifact).hexdigest(),'pack_sha256':sha256(pack).hexdigest(),'snapshot_owner':'proposed_repository_snapshots','candidate_sealed':False,'qualification_scope':'read-only Git object observation; not Verification PASS or Human Acceptance'},indent=2)+'\n')
# New qualification DB only; no production or fixture database export.
dump=P/'spg_c2_qualification_20261009.dump';assert not dump.exists()
with dump.open('xb') as stream:
    os.fchmod(stream.fileno(),0o600)
    process=subprocess.run(['docker','exec','watt-c2-postgres-20261009','pg_dump','-U','c2_app','-d','spg_c2_qualification_20261009','-Fc'],stdout=stream,stderr=subprocess.PIPE)
assert process.returncode==0,'Preserve failed backup for diagnosis'
volume=json.loads(call(['docker','volume','inspect','watt-c2-workspaces-20261009']))[0]
assert volume['Name']=='watt-c2-workspaces-20261009' and volume['Labels'].get('watt.qualification')=='C2-execution-readiness'
backup=P/'runtime-data-20261009.tar.gz';assert not backup.exists()
with backup.open('xb') as stream:
    os.fchmod(stream.fileno(),0o600)
    with tarfile.open(fileobj=stream,mode='w:gz',dereference=False) as archive:
        archive.add(str(ROOT/'app'),arcname='app')
        archive.add(str(ROOT/'receipts'),arcname='receipts')
        archive.add(volume['Mountpoint'],arcname='native-workspaces')
        archive.add(str(ROOT/'gitea-data'),arcname='gitea-data')
        archive.add(str(ROOT/'gitea-config'),arcname='gitea-config')
def file_hash(path):
    digest=sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()
(E/'persistent-recovery.json').write_text(json.dumps({'captured_at_utc':datetime.now(timezone.utc).isoformat(),'qualification_root':str(ROOT),'private_backups':[{'path':str(path),'size_bytes':path.stat().st_size,'sha256':file_hash(path),'mode':oct(path.stat().st_mode&0o777),'scope':'restricted C2 database/runtime data; not Git/public artifact'} for path in (dump,backup)],'public_git_witness':'git-witness/manifest.json','credentials_location':str(P)+' (root-only; never Git)','image_recovery':'image-recovery.json','production_data_copied':False,'new_work_preserved':binding['work_id'],'restore_policy':'Restore into a fresh isolated DB/root after checksum verification; do not replace source canonical or overwrite existing failed Work; new independent control credentials may be established separately.'},indent=2)+'\n')
print(json.dumps({'source':source,'output':output,'changed_paths':changed,'actual_pe_image':data['Image'],'new_database_backup':str(dump),'new_runtime_backup':str(backup),'private_credentials_published':False}),flush=True)