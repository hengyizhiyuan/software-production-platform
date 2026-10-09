"""Read-only actual-codec measurement in the newly built exact installed image."""
from datetime import datetime
from hashlib import sha256
import json,os,subprocess
from pathlib import Path
ROOT=Path('/data/watt/c3-semantic-convergence-20261009')
HERE=ROOT/'capacity-representation-20261009'
TARGET=HERE/'exact-wire-measurement-1'
BUILD=json.loads((HERE/'final-image/evidence/build.json').read_text(encoding='utf-8'))
FREEZE=json.loads((HERE/'final-image/evidence/frozen-inputs.json').read_text(encoding='utf-8'))
assert BUILD['exit_code']==0 and not TARGET.exists()
IMAGE=BUILD['image']['Id'];SOURCE=BUILD['sources']['watt']['revision']
PROVIDER=next(row['file_sha256']['src/spg/providers/fulfillment_candidate.py'] for row in FREEZE['archives'] if row['destination']=='watt')
SCRIPTS=ROOT/'capacity-final-inputs/measurement'
assert sha256((SCRIPTS/'measure_compact_wire.py').read_bytes()).hexdigest()=='37721353ad0568863dcf14f267bcc565a840cd3f95fefc8a31f4752762663070'
assert sha256((SCRIPTS/'measure_capacity.py').read_bytes()).hexdigest()=='c87fe121a10c338ceac3310b7b694988140253642000af7bdffabbe5ff1d918d'
TARGET.mkdir();evidence=TARGET/'evidence';evidence.mkdir();os.chown(str(evidence),10001,10001)
BASIS=ROOT/'public-delivery-c3-final/retry-1/g0-owner-2/20261009T130020024208Z-2fc7b990c1b54846a25bd067bc94b849-canonical-work.json'
DIAG=ROOT/'continuation-20261010/historical-provider-diagnostic-1/evidence/provider-diagnostic.json'
BASELINE=HERE/'baseline-measurement-1/evidence/capacity-measurement.json'
cmd=['docker','create','--network','none','--read-only','--user','10001:10001','--cap-drop','ALL',
    '--security-opt','no-new-privileges','--memory','512m','--cpus','1','--tmpfs','/tmp:rw,noexec,nosuid,size=16m',
    '-v',str(SCRIPTS)+':/measurements:ro','-v',str(BASIS)+':/basis.json:ro','-v',str(DIAG)+':/diagnostic.json:ro',
    '-v',str(BASELINE)+':/baseline-measurement.json:ro','-v',str(evidence)+':/c3-evidence:rw',
    IMAGE,'python','/measurements/measure_compact_wire.py','--execute-offline','--expected-provider-sha256',PROVIDER,'--application-identity',SOURCE]
cid=subprocess.check_output(cmd,universal_newlines=True).strip();started=datetime.utcnow().isoformat()+'Z'
with (evidence/'result.log').open('x') as stream:
    subprocess.run(['docker','start','-a',cid],stdout=stream,stderr=subprocess.STDOUT)
actual=json.loads(subprocess.check_output(['docker','inspect',cid],universal_newlines=True))[0]
receipt={'source_revision':SOURCE,'sources':BUILD['sources'],'expected_provider_sha256':PROVIDER,'actual_image_id':actual['Image'],
    'container_id':cid,'network_mode':actual['HostConfig']['NetworkMode'],'source_overlay':False,
    'started_at_utc':started,'ended_at_utc':datetime.utcnow().isoformat()+'Z','model_calls':0,'http_requests_sent':0,
    'credentials_loaded':False,'exit_code':actual['State']['ExitCode'],'controller_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
(evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt))
assert actual['Image']==IMAGE and actual['State']['ExitCode']==0
