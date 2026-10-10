import json, os, subprocess, sys, time
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

R=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010')
label=sys.argv[1]
mode=sys.argv[2]
assert label.startswith('wire-feedback-dev-') and mode in ('targeted','regression')
snapshot=R/label
manifest=json.loads((snapshot/'manifest.json').read_text())
assert sha256((snapshot/'snapshot.tar').read_bytes()).hexdigest()==manifest['archive_sha256']
for name,digest in manifest['files'].items():assert sha256((snapshot/name).read_bytes()).hexdigest()==digest
target=R/'wire-feedback-recovery-20261010'/(label+'-'+mode)
target.mkdir(mode=0o750,parents=True,exist_ok=False)
os.chown(str(target),10001,10001)
nodes=['tests/test_c3_fulfillment_wire_feedback.py']
if mode=='regression':nodes+=['tests/test_c3_fulfillment_capacity_representation.py','tests/test_c3_semantic_contract_calibration.py','tests/test_c3_fulfillment_provider_failures.py','tests/test_c3_fulfillment_components.py','tests/test_fulfillment_projection.py','tests/test_governed_obligation_fulfillment.py','tests/test_c3_fulfillment_stop_projection.py','tests/test_c3_fulfillment_admission_stop.py']
image='sha256:90f2cd847ad891fda6ca95b5736c84b680c9d58bd6a3203bf0ea31c970da0f16'
name='watt-c3-'+label+'-'+mode+'-20261010'
cmd=['docker','run','--name',name,'--network','none','--workdir','/dev-input/watt','--user','10001:10001',
 '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--memory','1536m','--cpus','1',
 '--tmpfs','/tmp:rw,exec,nosuid,size=512m','--label','watt.production=false','--label','watt.qualification=C3-predecode-development',
 '-e','PYTHONPATH=/dev-input/watt/src:/dev-input/guardian/src:/opt/c3-owners/ecf/src:/opt/c3-test-deps',
 '--mount','type=bind,src='+str(snapshot)+',dst=/dev-input,readonly',
 '--mount','type=bind,src='+str(target)+',dst=/c3-evidence',image,
 'python','-m','pytest','-p','no:cacheprovider','--tb=short','-o','addopts=','-o','junit_family=legacy',
 '--junitxml=/c3-evidence/result.xml']+nodes
started=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
with (target/'result.log').open('x') as stream:result=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT)
counts={k:0 for k in ('tests','failures','errors','skipped')}
if (target/'result.xml').exists():
 for suite in ET.parse(str(target/'result.xml')).iter('testsuite'):
  for k in counts:counts[k]+=int(suite.get(k,'0'))
counts['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped']
d=json.loads(subprocess.check_output(['docker','inspect',name],universal_newlines=True))[0]
receipt={'schema':'c3-predecode-development-regression-v1','started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),
 'wall_seconds':time.monotonic()-clock,'counts':counts,'exit_code':result.returncode,'snapshot_sha256':manifest['archive_sha256'],
 'actual_image_id':d['Image'],'actual_container_id':d['Id'],'network':d['HostConfig']['NetworkMode'],'source_overlay':True,
 'model_calls':0,'original_database_access':False,'production_resources_modified':False,'nodes':nodes,
 'controller_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'claim':'CONTROLLED_REGRESSION_NOT_EXACT_NEW_IMAGE_OR_LIVE_MODEL_QUALIFICATION'}
(target/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
if result.returncode:print((target/'result.log').read_text()[-10000:])
