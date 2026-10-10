"""Opt-in bounded C3 Option A live verification, exact image; no production resources."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/data/watt/c3-semantic-convergence-20261009')
TARGET = ROOT / 'semantic-contract-implementation-20261010/source-ownerprobe-live-1'
INPUT = ROOT / 'semantic-contract-implementation-20261010/source-ownerprobe-live-inputs-1'
IMAGE = 'sha256:97a8db7f77c2898a65bdc975bb0f49f0f3350fe3e20c6e3650f4aeb3e54c01fa'
SOURCE = '8c2b3d224e898b3dc8e8220f78f6a6723c158941'
BASIS = ROOT / 'public-delivery-c3-final/retry-1/g0-owner-2/20261009T130020024208Z-2fc7b990c1b54846a25bd067bc94b849-canonical-work.json'
ATTESTATION = ROOT / 'semantic-contract-implementation-20261010/source-ownerprobe-qualified-20261010/final-image/evidence/actual-imports.json'


def inspect_container(name):
    return json.loads(subprocess.check_output(['docker', 'inspect', name], universal_newlines=True))[0]


def write_json(path, value):
    with path.open('x') as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main(execute):
    mode = 'live' if execute else 'preflight'
    image = json.loads(subprocess.check_output(['docker', 'image', 'inspect', IMAGE], universal_newlines=True))[0]
    assert image['Id'] == IMAGE
    assert image['Config']['Labels'].get('org.opencontainers.image.revision') == SOURCE
    assert sha256(BASIS.read_bytes()).hexdigest() == '9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c'
    assert sha256(ATTESTATION.read_bytes()).hexdigest() == 'af30ff5c42afd287defc73a9ae217118447d09b4c58582175a059271869bbb08'
    script = INPUT / 'verify_live_model.py'
    assert script.is_file() and not script.is_symlink()
    for path in (ROOT,) + tuple(ROOT.parents) + (INPUT,):
        assert not path.is_symlink()
    if not execute:
        assert not TARGET.exists()
        TARGET.mkdir(mode=0o700)
        private = TARGET / 'private'
        private.mkdir(mode=0o700)
        observations = private / 'model-observations'
        observations.mkdir(mode=0o700)
        os.chown(str(observations), 10001, 10001)
        (TARGET / 'evidence').mkdir(mode=0o750)
        os.chown(str(TARGET / 'evidence'), 10001, 10001)
        original = ROOT / 'retry-1/private/watt-c3-retry1-api-20261009.env'
        assert original.is_file() and not original.is_symlink() and original.stat().st_mode & 0o077 == 0
        allowed = {'SPG_DEEPSEEK_API_KEY', 'SPG_DEEPSEEK_BASE_URL', 'SPG_WIC_PROVIDER_ADAPTER',
            'SPG_WIC_PROVIDER_MODEL', 'SPG_WIC_PROVIDER_REASONING_EFFORT',
            'SPG_COLLABORATION_PROVIDER_TIMEOUT_SECONDS', 'SPG_COLLABORATION_PROVIDER_MAX_OUTPUT_TOKENS'}
        settings = {key: value for key, value in (line.split('=', 1) for line in original.read_text().splitlines() if '=' in line) if key in allowed}
        assert settings.get('SPG_DEEPSEEK_API_KEY') and settings.get('SPG_DEEPSEEK_BASE_URL') == 'https://api.deepseek.com'
        with (private / 'provider-only.env').open('x') as stream:
            os.fchmod(stream.fileno(), 0o600)
            for key, value in settings.items():
                stream.write(key + '=' + value + '\n')
    else:
        assert TARGET.is_dir() and not TARGET.is_symlink()
        preflight = json.loads((TARGET / 'evidence/preflight-container.json').read_text())
        assert preflight['exit_code'] == 0 and preflight['preflight']['preflight'] == 'PASS'
        assert preflight['probe_sha256'] == sha256(script.read_bytes()).hexdigest()
        assert not (TARGET / 'execution-started.json').exists()
        write_json(TARGET / 'execution-started.json', {'started_at_utc': datetime.now(timezone.utc).isoformat(),
            'source': SOURCE, 'image': IMAGE, 'authorization': 'Human 2026-10-10 instruction to finish source/Owner convergence after qualified repair: two Formation, one feedback, conditional independent Review, four logical calls',
            'automatic_resume_or_repeat': False})
    name = 'watt-c3-source-ownerprobe-live1-' + mode + '-20261010'
    assert subprocess.run(['docker', 'inspect', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
    private = TARGET / 'private'
    evidence = TARGET / 'evidence'
    command = ['docker', 'create', '--name', name, '--network', 'watt-c3-control-20261009' if execute else 'none',
        '--user', '10001:10001', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--read-only',
        '--tmpfs', '/tmp:rw,nosuid,size=256m', '--memory', '1536m', '--cpus', '1', '--pids-limit', '128',
        '--label', 'watt.production=false', '--label', 'watt.qualification=C3-authorized-source-owner-calibration',
        '--env-file', str(private / 'provider-only.env'),
        '--mount', 'type=bind,src=' + str(script) + ',dst=/probe.py,readonly',
        '--mount', 'type=bind,src=' + str(BASIS) + ',dst=/basis.json,readonly',
        '--mount', 'type=bind,src=' + str(ATTESTATION) + ',dst=/qualified-imports.json,readonly',
        '--mount', 'type=bind,src=' + str(evidence) + ',dst=/c3-evidence',
        '--mount', 'type=bind,src=' + str(private / 'model-observations') + ',dst=/c3-private',
        IMAGE, 'python', '/probe.py']
    if execute:
        command.append('--execute-authorized-live')
    subprocess.check_output(command, universal_newlines=True)
    actual = inspect_container(name)
    assert actual['Image'] == IMAGE and actual['Config']['Labels'].get('org.opencontainers.image.revision') == SOURCE
    assert actual['Config']['User'] == '10001:10001' and actual['HostConfig']['ReadonlyRootfs']
    assert not actual['HostConfig'].get('PortBindings')
    receipt = {'schema': 'c3-authorized-capacity-container-v1', 'created_observed_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_revision': SOURCE, 'actual_container_id': actual['Id'], 'actual_image_id': actual['Image'],
        'user': actual['Config']['User'], 'mounts': actual['Mounts'], 'network_mode': actual['HostConfig']['NetworkMode'],
        'probe_sha256': sha256(script.read_bytes()).hexdigest(), 'controller_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_overlay': False, 'business_database_access': False, 'new_work_created': False,
        'existing_services_started_or_modified': False, 'mode': mode}
    write_json(evidence / (mode + '-container-before.json'), receipt)
    with (private / (mode + '.raw.log')).open('x') as stream:
        os.fchmod(stream.fileno(), 0o600)
        subprocess.run(['docker', 'start', '-a', name], stdout=stream, stderr=subprocess.STDOUT)
    actual = inspect_container(name)
    receipt.update(recorded_at_utc=datetime.now(timezone.utc).isoformat(), exit_code=actual['State']['ExitCode'],
        docker_started_at=actual['State']['StartedAt'], docker_finished_at=actual['State']['FinishedAt'], running=actual['State']['Running'])
    if not execute:
        lines = (private / 'preflight.raw.log').read_text().splitlines()
        parsed = [json.loads(line) for line in lines if line.startswith('{')]
        receipt['preflight'] = parsed[-1] if parsed else {'preflight': 'UNKNOWN'}
    write_json(evidence / (mode + '-container.json'), receipt)
    if execute and (evidence / 'live-result.json').is_file():
        report = json.loads((evidence / 'live-result.json').read_text())
        print(json.dumps({key: report.get(key) for key in ('result', 'failure_stage', 'failed_predicate', 'logical_calls', 'wall_seconds')}, sort_keys=True))
    else:
        print(json.dumps({'mode': mode, 'exit_code': receipt['exit_code'], 'preflight': receipt.get('preflight')}, sort_keys=True))
    assert receipt['exit_code'] == 0
    if execute:
        assert (evidence / 'live-result.json').is_file()
    else:
        assert receipt['preflight']['preflight'] == 'PASS'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--execute-authorized-live', action='store_true')
    args = parser.parse_args()
    assert not (args.preflight and args.execute_authorized_live)
    if args.preflight or args.execute_authorized_live:
        main(args.execute_authorized_live)
    else:
        print(json.dumps({'plan_only': True, 'source': SOURCE, 'image': IMAGE, 'model_calls': 0}))
