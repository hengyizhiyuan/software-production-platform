from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,time,hashlib
import xml.etree.ElementTree as ET
q=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation62-qualified-20261010');b=q/'final-image';e=b/'evidence';build=json.loads((e/'build.json').read_text());image=build['image']['Id'];freeze=json.loads((e/'frozen-inputs.json').read_text())
initial=json.loads((e/'watt-continuation-receipt.json').read_text());assert initial['counts']=={'tests':132,'failures':1,'errors':0,'skipped':0,'passed':131}
web=b/'context/watt/src/spg/web';record=next(r for r in freeze['archives'] if r['destination']=='watt')
for name in ('advanced.html','app.js','experience.js'):assert hashlib.sha256((web/name).read_bytes()).hexdigest()==record['file_sha256']['src/spg/web/'+name]
common=['--network','none','--user','10001:10001','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,exec,nosuid,size=512m','--memory','1536m','--cpus','1','--label','watt.production=false','--mount','type=bind,src='+str(web)+',dst=/qualification/src/spg/web,readonly','--mount','type=bind,src='+str(e)+',dst=/out','--workdir','/qualification']
probe="from importlib.resources import files;from pathlib import Path;from hashlib import sha256;import json; names=('advanced.html','app.js','experience.js');out={n:sha256(files('spg.web').joinpath(n).read_bytes()).hexdigest() for n in names};assert all(files('spg.web').joinpath(n).read_bytes()==Path('/qualification/src/spg/web',n).read_bytes() for n in names);print(json.dumps(out))"
p=subprocess.run(['docker','run','--name','watt-c3-context62-static-resource-equality']+common+[image,'python','-c',probe],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True);assert p.returncode==0,'INSTALLED_UI_RESOURCE_FIXTURE_DRIFT'
with (e/'ui-installed-resource-equality.json').open('x') as f:json.dump({'actual_image_id':image,'resource_sha256':json.loads(p.stdout),'exact_equality':True,'model_calls':0,'source_import_overlay':False},f,indent=2)
start=time.monotonic();name='watt-c3-context62-ui-fixture-recovery1'
cmd=['docker','run','--name',name]+common+[image,'python','-m','pytest','-p','no:cacheprovider','-o','addopts=','--tb=short','--junitxml=/out/ui-recovery.xml','tests/test_native_executor_contracts.py::test_native_queue_and_controls_are_human_visible_without_claiming_trust']
with (e/'ui-recovery.log').open('x') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
counts={k:0 for k in ('tests','failures','errors','skipped')}
for suite in ET.parse(e/'ui-recovery.xml').iter('testsuite'):
 for k in counts:counts[k]+=int(suite.get(k,'0'))
counts['passed']=counts['tests']-sum(counts[k] for k in ('failures','errors','skipped'))
a=json.loads(subprocess.check_output(['docker','inspect',name],universal_newlines=True))[0]
receipt={'exit_code':r.returncode,'counts':counts,'wall_seconds':time.monotonic()-start,'actual_container_id':a['Id'],'actual_image_id':a['Image'],'model_calls':0,'static_resource_fixture':True,'source_or_runtime_import_overlay':False,'original_failure_retained':True,'cause':'UI test reads repository-relative resource paths absent from installed qualification layout; fixture bytes independently verified identical to actual installed package','image_rebuilt':False}
with (e/'ui-recovery-receipt.json').open('x') as f:json.dump(receipt,f,indent=2)
assert r.returncode==0 and counts['passed']==1
aggregate=dict(initial);aggregate.update({'exit_code':0,'counts':{'tests':132,'failures':0,'errors':0,'skipped':0,'passed':132},'qualification':'131 original installed passes plus one targeted fixture-path recovery','basis_receipts':['watt-continuation-receipt.json','ui-recovery-receipt.json','ui-installed-resource-equality.json'],'original_initial_failure_retained':True})
with (e/'watt-qualified-aggregate.json').open('x') as f:json.dump(aggregate,f,indent=2)
print(json.dumps(receipt))
