from pathlib import Path
import json,subprocess,time,hashlib
import xml.etree.ElementTree as ET
r=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation62-qualified-20261010');b=r/'final-image';e=b/'evidence';f=r/'final-inputs'
freeze=json.loads((e/'frozen-inputs.json').read_text());build=json.loads((e/'build.json').read_text());image=build['image']['Id'];tests=b/'guardian-tests'
assert (tests/'tests/test_c3_review_identity_binding.py').is_file()
record=next(x for x in freeze['archives'] if x['destination']=='guardian')
for name,digest in record['file_sha256'].items():
 if name.startswith('tests/'):assert hashlib.sha256((tests/name).read_bytes()).hexdigest()==digest
cmd=['docker','run','--name','watt-c3-matched-guardian-c125ec6-recovery1','--network','none','--user','10001:10001','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,exec,nosuid,size=512m','--memory','1536m','--cpus','1','--label','watt.production=false','--mount','type=bind,src='+str(tests)+',dst=/guardian-qualification,readonly','--mount','type=bind,src='+str(e)+',dst=/out','--workdir','/guardian-qualification',image,'python','-m','pytest','-p','no:cacheprovider','-o','addopts=','--tb=short','--junitxml=/out/guardian-installed.xml','tests/test_c3_review_identity_binding.py','tests/test_c3_component_calibration.py']
start=time.monotonic()
with (e/'guardian-installed.log').open('x') as log:q=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
counts={k:0 for k in ('tests','failures','errors','skipped')}
for suite in ET.parse(e/'guardian-installed.xml').iter('testsuite'):
 for k in counts:counts[k]+=int(suite.get(k,'0'))
counts['passed']=counts['tests']-sum(counts[k] for k in ('failures','errors','skipped'))
actual=json.loads(subprocess.check_output(['docker','inspect','watt-c3-matched-guardian-c125ec6-recovery1'],universal_newlines=True))[0];assert actual['Image']==image
receipt={'exit_code':q.returncode,'counts':counts,'wall_seconds':time.monotonic()-start,'actual_image_id':actual['Image'],'actual_container_id':actual['Id'],'sources':freeze['sources'],'source_overlay':False,'tests_from_verified_frozen_archive':True,'fixture_only':True,'live_model_calls':0,'original_database_access':False,'proof_boundary':'Independent Guardian frozen installed contract regression; no Watt PASS substitution or runtime overlay'}
with (e/'guardian-installed-receipt.json').open('x') as stream:json.dump(receipt,stream,indent=2)
print(json.dumps(receipt));assert q.returncode==0 and counts['passed']==46 and not sum(counts[k] for k in ('failures','errors','skipped'))
