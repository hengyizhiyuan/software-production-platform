"""Run an unsent-payload measurement in the retained exact image; no credentials."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
import subprocess

ROOT = Path('/data/watt/c3-semantic-convergence-20261009')
TARGET = ROOT / 'capacity-representation-20261009/baseline-measurement-1'
IMAGE = 'sha256:4d3c64b1e3543a3574cd69b435d6f703fad6edc23b9db7d54d799dc1a652bf6e'
SOURCE = 'e8e04b296b31d776a13dda728fa19469681cbaab'
BASIS = ROOT / 'public-delivery-c3-final/retry-1/g0-owner-2/20261009T130020024208Z-2fc7b990c1b54846a25bd067bc94b849-canonical-work.json'
DIAGNOSTIC = ROOT / 'continuation-20261010/historical-provider-diagnostic-1/evidence/provider-diagnostic.json'
SCRIPT = Path(__file__).with_name('measure_capacity.py')

def run(args):
    return subprocess.check_output(args, universal_newlines=True).strip()

def main():
    assert not TARGET.exists(), 'new evidence target required'
    assert hashlib.sha256(SCRIPT.read_bytes()).hexdigest() == 'c87fe121a10c338ceac3310b7b694988140253642000af7bdffabbe5ff1d918d'
    assert hashlib.sha256(BASIS.read_bytes()).hexdigest() == '9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c'
    observed_image = json.loads(run(['docker', 'image', 'inspect', IMAGE]))[0]
    assert observed_image['Id'] == IMAGE
    assert observed_image['Config']['Labels']['org.opencontainers.image.revision'] == SOURCE
    TARGET.mkdir(parents=True)
    output = TARGET / 'evidence'
    output.mkdir()
    import os
    os.chown(str(output), 10001, 10001)
    started = datetime.utcnow().isoformat() + 'Z'
    cid = run(['docker', 'create', '--network', 'none', '--read-only', '--user', '10001:10001',
        '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--memory', '512m', '--cpus', '1',
        '--tmpfs', '/tmp:rw,noexec,nosuid,size=16m',
        '-v', str(SCRIPT)+':/measure.py:ro', '-v', str(BASIS)+':/basis.json:ro',
        '-v', str(DIAGNOSTIC)+':/diagnostic.json:ro', '-v', str(output)+':/c3-evidence:rw',
        IMAGE, 'python', '/measure.py', '--execute-offline', '--application-source', SOURCE])
    inspection = json.loads(run(['docker', 'inspect', cid]))[0]
    completed = subprocess.run(['docker', 'start', '-a', cid], stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, universal_newlines=True)
    (TARGET / 'stdout.txt').write_text(completed.stdout, encoding='utf-8')
    final = json.loads(run(['docker', 'inspect', cid]))[0]
    receipt = {'started_at_utc': started, 'ended_at_utc': datetime.utcnow().isoformat()+'Z',
        'application_source': SOURCE, 'actual_image_id': final['Image'], 'container_id': cid,
        'network_mode': inspection['HostConfig']['NetworkMode'], 'mounts': inspection['Mounts'],
        'exit_code': final['State']['ExitCode'], 'model_requests': 0, 'http_requests_sent': 0,
        'credential_inputs': 0, 'controller_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'measurement_sha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest()}
    (TARGET / 'execution-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'result': 'OFFLINE_MEASUREMENT_PASS' if final['State']['ExitCode']==0 else 'OFFLINE_MEASUREMENT_FAILED',
        'actual_image_id': final['Image'], 'container_id': cid, 'exit_code': final['State']['ExitCode']}))
    return final['State']['ExitCode']

if __name__ == '__main__':
    raise SystemExit(main())
