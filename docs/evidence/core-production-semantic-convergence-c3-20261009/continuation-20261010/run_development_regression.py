"""Declared source-overlay development regression; no model, database or Work."""
import json,os,subprocess,tarfile,time
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import xml.etree.ElementTree as ET
ROOT=Path('/data/watt/c3-semantic-convergence-20261009')
TARGET=ROOT/'continuation-20261010/development-1'
INPUTS=ROOT/'continuation-development-1-inputs'
IMAGE='sha256:51c0b8be88969720cb3a3cfc4e047edc7f229aa22348a95a89cbb4bf83a18e39'
NAME='watt-c3-continuation-dev1-20261009'
assert not TARGET.exists()
for p in (ROOT,)+tuple(ROOT.parents):assert not p.is_symlink()
manifest=json.loads((INPUTS/'snapshot.json').read_text())
archive=INPUTS/'source-tests.tar'
assert sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
TARGET.mkdir(mode=0o750);source=TARGET/'source';source.mkdir(mode=0o755)
with tarfile.open(str(archive)) as tar:
 actual={m.name:sha256(tar.extractfile(m).read()).hexdigest() for m in tar.getmembers() if m.isfile()}
 assert actual==manifest['source_file_sha256']
 for m in tar.getmembers():
  path=Path(m.name);assert not path.is_absolute() and '..' not in path.parts and (m.isfile() or m.isdir())
  dest=source/path
  if m.isdir():dest.mkdir(mode=0o755,parents=True,exist_ok=True)
  else:dest.parent.mkdir(mode=0o755,parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(m).read());os.chmod(str(dest),0o644)
evidence=TARGET/'evidence';evidence.mkdir(mode=0o750);os.chown(str(evidence),10001,10001)
nodes=json.loads((INPUTS/'affected-unit-nodes.json').read_text())
assert all(n.startswith('tests/') and '..' not in n for n in nodes)
assert subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',IMAGE],universal_newlines=True).strip()==IMAGE
assert subprocess.run(['docker','inspect',NAME],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
pytest=['python','-m','pytest','-p','no:cacheprovider','--tb=short','--junitxml=/c3-evidence/result.xml']+nodes
command=['docker','run','--name',NAME,'--workdir','/qualification','--network','none','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,exec,nosuid,size=512m','--memory','1536m','--cpus','1','--label','watt.production=false','--label','watt.qualification=C3-development-only','-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/qualification/src:/qualification/tests:/opt/c3-owners/guardian/src:/opt/c3-owners/ecf/src:/opt/c3-test-deps','--mount','type=bind,src='+str(source)+',dst=/qualification,readonly','--mount','type=bind,src='+str(evidence)+',dst=/c3-evidence',IMAGE]+pytest
started=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
with (evidence/'result.log').open('x') as stream:result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
counts={k:0 for k in ('tests','failures','errors','skipped')}
if (evidence/'result.xml').exists():
 for suite in ET.parse(str(evidence/'result.xml')).iter('testsuite'):
  for k in counts:counts[k]+=int(suite.get(k,'0'))
counts['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped']
actual=json.loads(subprocess.check_output(['docker','inspect',NAME],universal_newlines=True))[0]
assert actual['Image']==IMAGE and actual['HostConfig']['NetworkMode']=='none'
receipt={'schema':'c3-development-regression-v1','started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),'wall_seconds':time.monotonic()-clock,'actual_image_id':actual['Image'],'actual_container_id':actual['Id'],'source_snapshot_sha256':manifest['archive_sha256'],'source_overlay':True,'counts':counts,'exit_code':result.returncode,'nodes':nodes,'live_model_calls':0,'real_work_created_or_modified':False,'business_database_access':False,'claim':'DEVELOPMENT_ONLY_NOT_FINAL_IMAGE_QUALIFICATION'}
(evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
