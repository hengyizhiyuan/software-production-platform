"""Read-only installed d8ea projection counterexample; only a declared test overlay."""
import json,subprocess,os,time
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import xml.etree.ElementTree as ET
ROOT=Path('/data/watt/c3-semantic-convergence-20261009');TARGET=ROOT/'continuation-20261010/pre-fix-stop-projection-control2'
assert not TARGET.exists();TARGET.mkdir(mode=0o750)
E=TARGET/'evidence';E.mkdir(mode=0o750);os.chown(str(E),10001,10001)
source=ROOT/'test_c3_fulfillment_stop_projection.py';assert sha256(source.read_bytes()).hexdigest()=='37453ae076f22833377c9ff80e89593e1a07085988c3c58bf993f7bc06d4a6a5'
IMAGE='sha256:51c0b8be88969720cb3a3cfc4e047edc7f229aa22348a95a89cbb4bf83a18e39';NAME='watt-c3-stop-projection-red2-20261009'
assert subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',IMAGE],universal_newlines=True).strip()==IMAGE
assert subprocess.run(['docker','inspect',NAME],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
node='tests/test_c3_fulfillment_stop_projection.py::test_fresh_projection_consumes_current_durable_fulfillment_stop'
command=['docker','run','--name',NAME,'--workdir','/qualification','--network','none','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,exec,nosuid,size=256m','--memory','1536m','--cpus','1','--label','watt.production=false','--label','watt.qualification=C3-counterexample','--mount','type=bind,src='+str(source)+',dst=/qualification/tests/test_c3_fulfillment_stop_projection.py,readonly','--mount','type=bind,src='+str(E)+',dst=/c3-evidence',IMAGE,'python','-m','pytest','-p','no:cacheprovider',node,'--tb=short','--junitxml=/c3-evidence/result.xml']
start=time.monotonic();started=datetime.now(timezone.utc).isoformat()
with (E/'result.log').open('x') as stream:result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
counts={k:0 for k in ('tests','failures','errors','skipped')}
for suite in ET.parse(str(E/'result.xml')).iter('testsuite'):
 for k in counts:counts[k]+=int(suite.get(k,'0'))
actual=json.loads(subprocess.check_output(['docker','inspect',NAME],universal_newlines=True))[0]
receipt={'schema':'c3-pre-fix-projection-counterexample-v1','started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),'wall_seconds':time.monotonic()-start,'exit_code':result.returncode,'counts':counts,'node':node,'actual_image_id':actual['Image'],'actual_container_id':actual['Id'],'source_revision':actual['Config']['Labels'].get('org.opencontainers.image.revision'),'test_sha256':sha256(source.read_bytes()).hexdigest(),'source_overlay':False,'test_overlay':True,'live_model_calls':0,'business_database_access':False,'real_work_created_or_modified':False,'claim':'CONTROLLED_COUNTEREXAMPLE_NOT_WORK_FAILURE_OR_PASS'}
(E/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))