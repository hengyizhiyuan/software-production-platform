"""Exact installed Owners, bounded frozen tests and unmodified historical input."""
import json,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import xml.etree.ElementTree as ET
R=Path('/data/watt/c3-semantic-convergence-20261009')
T=R/'semantic-contract-implementation-20261010'
B=T/'final-image-2';E=B/'evidence'
build=json.loads((E/'build.json').read_text())
assert build['exit_code']==0
image=build['image']['Id']
common=['--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
    '--tmpfs','/tmp:rw,nosuid,size=256m','--memory','1536m','--cpus','1']
nodes=['tests/test_c3_component_calibration.py','tests/test_c3_phase_evidence.py',
       'tests/test_c1_governed_evidence_continuity.py','tests/test_governed_obligation_evidence.py']
name='watt-c3-calibration-guardian-final-a91442c'
command=['docker','run','--name',name]+common+['--user','10001:10001','--mount','type=bind,src='+str(E)+',dst=/evidence',
    '--mount','type=bind,src='+str(B/'guardian-tests')+',dst=/guardian-tests,readonly','-w','/guardian-tests',
    image,'python','-m','pytest','-p','no:cacheprovider','-o','junit_family=legacy','--tb=short',
    '--junitxml=/evidence/guardian.xml']+nodes
start=time.monotonic();started=datetime.now(timezone.utc).isoformat()
with (E/'guardian.log').open('x') as output:result=subprocess.run(command,stdout=output,stderr=subprocess.STDOUT)
counts={k:0 for k in ('tests','failures','errors','skipped')}
if (E/'guardian.xml').exists():
    for suite in ET.parse(str(E/'guardian.xml')).iter('testsuite'):
        for key in counts:counts[key]+=int(suite.get(key,'0'))
counts['passed']=counts['tests']-sum(counts[k] for k in ('failures','errors','skipped'))
actual=json.loads(subprocess.check_output(['docker','inspect',name],universal_newlines=True))[0]
receipt={'started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),
    'wall_seconds':time.monotonic()-start,'counts':counts,'exit_code':result.returncode,'sources':build['sources'],
    'actual_image':actual['Image'],'actual_container':actual['Id'],'runtime_source_overlay':False,
    'test_inputs':'Exact Guardian Git archive from frozen build manifest','nodes':nodes,
    'network':'none','model_calls':0,'claim':'Controlled independent Owner evidence regressions, not live Assurance'}
(E/'guardian-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert result.returncode==0 and counts['skipped']==0
