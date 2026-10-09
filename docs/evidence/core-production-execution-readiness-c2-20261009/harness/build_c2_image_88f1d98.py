from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,shutil,subprocess,tarfile
ROOT=Path('/data/watt/c2-execution-readiness-20261009')
BUILD=ROOT/'build-88f1d98'
assert not BUILD.exists(),'Preserve previous build; do not recreate'
BUILD.mkdir(mode=0o750)
CONTEXT=BUILD/'context';CONTEXT.mkdir(mode=0o755)
ARCHIVES=BUILD/'archives';ARCHIVES.mkdir(mode=0o750)
OLD=Path('/data/watt/c1-contract-qualification-20261009')
expected={'watt-88f1d98-inputs.tar':'e9c12bfe7f19b444dd714aeae56e7926a73d007854afd3a11580958e62964e51', 'guardian-exact.tar':'f2cbee8ea23ad217b9307d9288c88c4a95673f97d8a218ebff8b74f9f894d915', 'ecf.tar':'24ba8fedcd9555a6d08d90bc6aaf9206ac2b5f74d5c6f81061d99c89306b033c', 'ecf-current.tar':'0c21dafb428769a77ce1eb04d557f7ac7b06372c0365232b51f5011759b9fa16','pytest-deps.tar':'e8c5261006ae6a2db8d8a240c4247c349924d03ca0865b999ee0e357b927d4e9'}
for name in list(expected)+['pytest-py-shim.tar']:
    source=ROOT/name if name.startswith('watt-88') else OLD/name
    target=ARCHIVES/name
    shutil.copyfile(str(source),str(target))
    actual=sha256(target.read_bytes()).hexdigest()
    assert name not in expected or actual==expected[name],('ARCHIVE_DIGEST_MISMATCH',name)
    expected[name]=actual
    dest={'watt-88f1d98-inputs.tar':'watt','guardian-exact.tar':'guardian','ecf.tar':'ecf','ecf-current.tar':'ecf-unsupported','pytest-deps.tar':'test-deps','pytest-py-shim.tar':'test-deps'}[name]
    targetroot=CONTEXT/dest;targetroot.mkdir(mode=0o755,exist_ok=True)
    with tarfile.open(str(target)) as archive:
        for member in archive.getmembers():
            relative=Path(member.name)
            assert not relative.is_absolute() and '..' not in relative.parts
            if dest in ('guardian','ecf','ecf-unsupported') and (not relative.parts or relative.parts[0]!='src'):
                continue
            assert member.isdir() or member.isfile(),('NON_REGULAR_INPUT',name,member.name)
            if member.isdir():
                (targetroot/relative).mkdir(mode=0o755,parents=True,exist_ok=True)
            else:
                output=targetroot/relative;output.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
                output.write_bytes(archive.extractfile(member).read());os.chmod(str(output),member.mode & 0o777)
sources={'watt':{'revision':'88f1d9805d3ed1aa779ed3c78902b193fae240f8','tree':'69a35717087bfb46c18f5cfc9616a7a2a0acbdf7'},'guardian':{'revision':'6b974748df22d84b88f6908ea8ee90a9752fd183','tree':'c9a1bf4e102d8365a1ce27c9cced88f8ab0cd129'},'ecf':{'revision':'5aa4f8833c359c15bd059eda5972aa3915bcc18c','tree':'878d39d9c259272bb05f2e02bdf9d60c22fad460'},'ecf-unsupported':{'revision':'c6b568d006022e39b95daebedfecfb55e562ebe5','tree':'f102fa082bbd0a1abd827e77d6aa1340db8b83c5'}}
inputs={}
for path in sorted(CONTEXT.rglob('*')):
    if path.is_file(): inputs[path.relative_to(CONTEXT).as_posix()]=sha256(path.read_bytes()).hexdigest()
base='sha256:6c1f48e35ec485de278e8638f51d6aed75679b02a24d45355959bc8ddd7c0d14'
tag='watt-c2-dependency-base:6c1f48e-20261009'
subprocess.check_call(['docker','tag',base,tag])
assert subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',tag],universal_newlines=True).strip()==base
identity={'schema':'c2-source-identity-v1','sources':sources,'base_image':{'reference':tag,'image_id':base},'build_input_sha256':inputs,'archive_sha256':expected}
(CONTEXT/'c2-source-identity.json').write_text(json.dumps(identity,sort_keys=True,indent=2)+'\n')
(ROOT/'evidence/build-input-identity.json').write_text(json.dumps(identity,sort_keys=True,indent=2)+'\n')
command=['docker','build','--network=none','--build-arg','BASE_IMAGE='+tag,'--build-arg','WATT_REVISION='+sources['watt']['revision'],'--build-arg','WATT_TREE='+sources['watt']['tree'],'-f',str(CONTEXT/'watt/docs/evidence/core-production-execution-readiness-c2-20261009/Dockerfile.c2'),'-t','watt-c2:88f1d98',str(CONTEXT)]
started=datetime.now(timezone.utc).isoformat()
print(json.dumps({'build_started':started,'exact_watt':sources['watt'],'input_files':len(inputs),'model_calls':0}),flush=True)
with (ROOT/'evidence/build-88f1d98.log').open('w') as stream:
    result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
receipt={'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'command':command,'exit_code':result.returncode,'sources':sources,'build_input_identity_sha256':sha256((CONTEXT/'c2-source-identity.json').read_bytes()).hexdigest()}
if result.returncode==0:
    data=json.loads(subprocess.check_output(['docker','image','inspect','watt-c2:88f1d98'],universal_newlines=True))[0]
    receipt['image']={k:data.get(k) for k in ('Id','RepoTags','RepoDigests','Created')}
    receipt['image']['labels']=data['Config']['Labels'];receipt['image']['user']=data['Config']['User']
(ROOT/'evidence/build-88f1d98.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'build_exit':result.returncode,'image':receipt.get('image')}),flush=True)
raise SystemExit(result.returncode)