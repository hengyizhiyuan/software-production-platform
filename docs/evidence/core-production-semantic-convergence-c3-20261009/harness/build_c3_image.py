"""Build only frozen exact sources, retaining all input archives and receipts."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,shutil,subprocess,tarfile,time
ROOT=Path('/data/watt/c3-semantic-convergence-20261009');E=ROOT/'evidence'
freeze=json.loads((ROOT/'frozen-inputs.json').read_text())
for name,expected in freeze['control_harness_sha256'].items():
    assert sha256((ROOT/name).read_bytes()).hexdigest()==expected, ('control harness identity mismatch',name)
BUILD=ROOT/('build-'+freeze['sources']['watt']['revision'][:7]);assert not BUILD.exists()
BUILD.mkdir(mode=0o750);CONTEXT=BUILD/'context';CONTEXT.mkdir(mode=0o755)
ARCHIVES=BUILD/'archives';ARCHIVES.mkdir(mode=0o750)
archive_hashes={}
for record in freeze['archives']:
    source=Path(record['path']);target=ARCHIVES/source.name
    shutil.copyfile(str(source),str(target))
    actual=sha256(target.read_bytes()).hexdigest();assert actual==record['sha256']
    archive_hashes[target.name]=actual
    dest=record['destination'];targetroot=CONTEXT/dest;targetroot.mkdir(mode=0o755,exist_ok=True)
    with tarfile.open(str(target)) as archive:
        for member in archive.getmembers():
            relative=Path(member.name)
            assert not relative.is_absolute() and '..' not in relative.parts
            if dest=='guardian' and relative.parts and relative.parts[0]=='tests':
                assert member.isdir() or member.isfile()
                testroot=BUILD/'test-inputs/guardian'
                output=testroot/relative
                if member.isdir():output.mkdir(mode=0o755,parents=True,exist_ok=True)
                else:
                    output.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
                    output.write_bytes(archive.extractfile(member).read());os.chmod(str(output),member.mode&0o777)
                continue
            if dest in ('guardian','ecf','ecf-unsupported') and (not relative.parts or relative.parts[0]!='src'):
                continue
            assert member.isdir() or member.isfile()
            output=targetroot/relative
            if member.isdir():output.mkdir(mode=0o755,parents=True,exist_ok=True)
            else:
                output.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
                output.write_bytes(archive.extractfile(member).read());os.chmod(str(output),member.mode&0o777)
inputs={path.relative_to(CONTEXT).as_posix():sha256(path.read_bytes()).hexdigest()
        for path in sorted(CONTEXT.rglob('*')) if path.is_file()}
base='sha256:6c1f48e35ec485de278e8638f51d6aed75679b02a24d45355959bc8ddd7c0d14'
tag='watt-c3-dependency-base:6c1f48e-20261009'
subprocess.check_call(['docker','tag',base,tag])
assert subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',tag],universal_newlines=True).strip()==base
identity={'schema':'c3-source-identity-v1','sources':freeze['sources'],
    'base_image':{'reference':tag,'image_id':base},'build_input_sha256':inputs,'archive_sha256':archive_hashes}
(CONTEXT/'c3-source-identity.json').write_text(json.dumps(identity,sort_keys=True,indent=2)+'\n')
(E/'build-input-identity.json').write_text(json.dumps(identity,sort_keys=True,indent=2)+'\n')
args=['docker','build','--network=none','--build-arg','BASE_IMAGE='+tag]
for owner,prefix in (('watt','WATT'),('guardian','GUARDIAN'),('ecf','ECF')):
    args+=['--build-arg',prefix+'_REVISION='+freeze['sources'][owner]['revision'],
           '--build-arg',prefix+'_TREE='+freeze['sources'][owner]['tree']]
image_tag='watt-c3:'+freeze['sources']['watt']['revision'][:7]
args+=['-f',str(CONTEXT/'watt/docs/evidence/core-production-semantic-convergence-c3-20261009/Dockerfile.c3'),'-t',image_tag,str(CONTEXT)]
started=datetime.now(timezone.utc).isoformat();begin=time.monotonic()
with (E/'build.log').open('x') as stream:result=subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT)
receipt={'schema':'c3-exact-image-build-v1','started_at_utc':started,
    'ended_at_utc':datetime.now(timezone.utc).isoformat(),'wall_seconds':time.monotonic()-begin,
    'exit_code':result.returncode,'command':args,'sources':freeze['sources'],
    'source_identity_sha256':sha256((CONTEXT/'c3-source-identity.json').read_bytes()).hexdigest(),
    'real_model_calls':0,'source_overlay':False}
if result.returncode==0:
    data=json.loads(subprocess.check_output(['docker','image','inspect',image_tag],universal_newlines=True))[0]
    receipt['image']={k:data.get(k) for k in ('Id','RepoTags','RepoDigests','Created')}
    receipt['image']['labels']=data['Config']['Labels'];receipt['image']['user']=data['Config']['User']
(E/'build.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'build_exit':result.returncode,'image':receipt.get('image'),'wall_seconds':receipt['wall_seconds']}),flush=True)
raise SystemExit(result.returncode)
