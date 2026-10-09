from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,shutil,subprocess,tarfile,time
ROOT=Path('/data/watt/c3-semantic-convergence-20261009');P=ROOT/'private';E=ROOT/'evidence'
D=ROOT/'dev-pe-baseline'
assert not D.exists()
shutil.copytree('/data/watt/c2-execution-readiness-20261009/build-88f1d98/context/watt',str(D))
archive=ROOT/'c3-pe-development-source.tar'
assert sha256(archive.read_bytes()).hexdigest()=='1e325c94ba6f3f4984bb44a9ac872aae13bc09a8d6bf6de67cf9531915aa92be'
with tarfile.open(str(archive),'r') as inputs:
    for member in inputs.getmembers():
        assert member.isfile() and not member.issym() and not member.islnk()
        path=(D/member.name).resolve()
        assert D.resolve() in path.parents
        inputs.extract(member,str(D))
out=E/'pe-development';out.mkdir(mode=0o755);os.chown(str(out),10001,10001)
IMAGE='sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209'
name='watt-c3-pe-development-20261009'
command=['python','-m','pytest','-p','no:cacheprovider','-o','junit_family=legacy',
'tests/test_container_production_environment_provider.py','-m','not real_container',
'--tb=short','--junitxml=/c3-evidence/pe.xml']
args=['docker','run','--name',name,'--network','none','--user','10001:10001',
'--cap-drop','ALL','--security-opt','no-new-privileges','--read-only',
'--tmpfs','/tmp:rw,exec,nosuid,size=256m','--memory','1024m','--cpus','1',
'--label','watt.production=false','--label','watt.qualification=C3-development',
'--mount','type=bind,src='+str(D)+',dst=/qualification,readonly',
'--mount','type=bind,src='+str(out)+',dst=/c3-evidence',
'-e','PYTHONPATH=/qualification/src:/qualification:/opt/c2-test-deps:/opt/c2-owners/guardian/src:/opt/c2-owners/ecf/src',
'-e','PYTHONDONTWRITEBYTECODE=1','--workdir','/qualification',IMAGE]+command
started=datetime.now(timezone.utc).isoformat();start=time.monotonic()
raw=P/'pe-development.raw.log'
with raw.open('x') as stream:
    os.fchmod(stream.fileno(),0o600)
    result=subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT)
safe=raw.read_text(errors='replace')
for value in json.loads((P/'credentials.json').read_text()).values():
    if isinstance(value,str) and len(value)>20:safe=safe.replace(value,'[REDACTED]')
(out/'console.log').write_text(safe)
receipt={'schema':'c3-pe-development-regression-v1','source_base_revision':'88f1d9805d3ed1aa779ed3c78902b193fae240f8',
'input_patch_archive_sha256':sha256(archive.read_bytes()).hexdigest(),
'dependency_test_image':IMAGE,'source_overlay':True,'is_final_c3_runtime_qualification':False,
'started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),
'wall_seconds':time.monotonic()-start,'exit_code':result.returncode,
'command':command,'user':'10001:10001','real_model_calls':0,'real_works_created':0,
'original_environment_modified':False}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
raise SystemExit(result.returncode)
