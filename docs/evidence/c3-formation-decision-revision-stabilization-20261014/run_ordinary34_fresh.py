"""Container launcher: no Docker socket, database, production mounts or source overlays."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
parser=argparse.ArgumentParser()
parser.add_argument('--live',action='store_true')
args=parser.parse_args()
root=Path('/data/watt/ai-native-evolution-20261013/decision-revision-stabilization-20261014')
private=root/'private/qualification'
evidence=root/'evidence/ordinary34'
for p in (private,evidence):
    p.mkdir(exist_ok=True)
    os.chown(str(p),10001,10001)
script=root/'qualify_ordinary34.py'
image=json.loads((root/'build-lf/evidence/image-build.json').read_text())['actual_image_id']
mode='live' if args.live else 'preflight'
if args.live:
    preflight=json.loads((evidence/'preflight-result.json').read_text())
    assert preflight['terminal_reason']=='SECOND_REQUEST_READY_NO_NETWORK'
    assert json.loads((evidence/'preflight-container.json').read_text())['script_sha256']==sha256(script.read_bytes()).hexdigest()
command=['docker','create','--name','c3-dr-ordinary34-'+mode,'--network','bridge' if args.live else 'none',
    '--memory','1024m','--cpus','1','--workdir','/qualification','--read-only','--tmpfs','/tmp:rw,nosuid,nodev',
    '-v',str(private)+':/private','-v',str(evidence)+':/evidence','-v',str(script)+':/probe.py:ro',
    '-v','/data/watt/c3-semantic-convergence-20261009/non-holdout-cause-control-20261012/private/ordinary34:/inventory:ro',
    '-v','/data/watt/ai-native-evolution-20261013/nonholdout-15/private/ordinary34-owner-receipts.json:/historical-owner-receipts.json:ro']
if args.live:command+=['--env-file','/data/watt/ai-native-evolution-20261013/private/model.env']
command += [image,'python','/probe.py']+(['--live'] if args.live else [])
container=subprocess.check_output(command,universal_newlines=True).strip()
fact=json.loads(subprocess.check_output(['docker','inspect',container],universal_newlines=True))[0]
assert fact['Image']==image
public={'id':fact['Id'],'actual_image':fact['Image'],'mounts':fact['Mounts'],
    'network_mode':fact['HostConfig']['NetworkMode'],'user':fact['Config']['User'],
    'script_sha256':sha256(script.read_bytes()).hexdigest(),'runtime_source_overlay':False}
(evidence/(mode+'-container.json')).write_text(json.dumps(public,indent=2))
with (evidence/(mode+'.log')).open('x') as log:
    result=subprocess.run(['docker','start','-a',container],stdout=log,stderr=subprocess.STDOUT)
state=json.loads(subprocess.check_output(['docker','inspect',container],universal_newlines=True))[0]['State']
(evidence/(mode+'-exit.json')).write_text(json.dumps({k:state[k] for k in ('ExitCode','OOMKilled','StartedAt','FinishedAt')},indent=2))
print(json.dumps({'mode':mode,'exit_code':state['ExitCode'],'actual_image':image}))
raise SystemExit(result.returncode)
