"""One synthetic limit counterexample, using the unchanged installed baseline."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import os
import subprocess

TARGET=Path('/data/watt/c3-semantic-convergence-20261009/capacity-representation-20261009/baseline-receipt-counterexample')
IMAGE='sha256:4d3c64b1e3543a3574cd69b435d6f703fad6edc23b9db7d54d799dc1a652bf6e'
TEST=Path('/tmp/test_c3_fulfillment_capacity_representation.py')
assert not TARGET.exists()
assert sha256(TEST.read_bytes()).hexdigest()=='7b9d70d7a57775f78317b64e8fd74be49423677e2ada570fd5e3a6c3a94e7b68'
TARGET.mkdir(parents=True)
os.chown(str(TARGET),10001,10001)
cmd=['python','-m','pytest','-p','no:cacheprovider','-o','junit_family=legacy',
    'tests/test_c3_fulfillment_capacity_representation.py::test_expanded_observation_capacity_stop_returns_unresolved_and_replays_without_calls',
    '--tb=short','--junitxml=/c3-evidence/pytest.xml']
cid=subprocess.check_output(['docker','create','--network','none','--read-only','--user','10001:10001',
    '--cap-drop','ALL','--security-opt','no-new-privileges','--memory','768m','--cpus','1',
    '--tmpfs','/tmp:rw,nosuid,size=64m','--workdir','/qualification',
    '-v',str(TEST)+':/qualification/tests/'+TEST.name+':ro',
    '-v',str(TARGET)+':/c3-evidence:rw',IMAGE]+cmd,universal_newlines=True).strip()
started=datetime.utcnow().isoformat()+'Z'
with (TARGET/'pytest.log').open('x') as stream:
    result=subprocess.run(['docker','start','-a',cid],stdout=stream,stderr=subprocess.STDOUT)
actual=json.loads(subprocess.check_output(['docker','inspect',cid],universal_newlines=True))[0]
receipt={'started_at_utc':started,'ended_at_utc':datetime.utcnow().isoformat()+'Z','actual_image':actual['Image'],
    'container_id':cid,'source_overlay':False,'test_overlay':True,'test_sha256':sha256(TEST.read_bytes()).hexdigest(),
    'exit_code':actual['State']['ExitCode'],'model_calls':0,'network_mode':actual['HostConfig']['NetworkMode'],'command':cmd}
(TARGET/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt))
