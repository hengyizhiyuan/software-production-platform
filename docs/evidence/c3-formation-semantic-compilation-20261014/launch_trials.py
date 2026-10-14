"""ECS launcher: exact image, isolated container, read-only inputs, no DB/socket/overlay."""
from pathlib import Path
import json, subprocess, os, time
from datetime import datetime, timezone

root = Path('/data/watt/ai-native-evolution-20261013/semantic-compilation-20261014')
build = json.loads((root / 'evidence/image-build.json').read_text())
assert build['exit_code'] == 0 and build['revision'] == 'f9519044cd6ac1c18e4c5894d56258156d5f47dd'
for name in ('attestation', 'focused', 'postgres-final'):
    assert json.loads((root / f'evidence/installed/{name}-run.json').read_text())['exit_code'] == 0
trial = root / 'trials'; trial.mkdir(exist_ok=False)
for name in ('evidence', 'private'):
    (trial / name).mkdir(); os.chown(str(trial / name), 10001, 10001); os.chmod(str(trial / name), 0o700)
script = root / 'run_trials.py'; os.chmod(str(script), 0o444)
helper = Path('/data/watt/c3-semantic-convergence-20261009/non-holdout-cause-control-20261012/analyze_development.py')
image = build['actual_image_id']
args = ['docker', 'create', '--name', 'watt-c3-semantic-compilation-trials', '--network', 'bridge',
    '--read-only', '--user', '10001:10001', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
    '--memory', '1024m', '--cpus', '1', '--tmpfs', '/tmp:rw,nosuid,size=256m', '--workdir', '/qualification',
    '--env-file', '/data/watt/ai-native-evolution-20261013/private/model.env',
    '--mount', f'type=bind,src={script},dst=/run.py,readonly',
    '--mount', f'type=bind,src={helper},dst=/helper.py,readonly',
    '--mount', f'type=bind,src={trial / "evidence"},dst=/evidence',
    '--mount', f'type=bind,src={trial / "private"},dst=/private']
for case in ('ordinary34', 'ordinary41'):
    args += ['--mount', f'type=bind,src={helper.parent / "private" / case},dst=/inputs/{case},readonly']
args += [image, 'python', '/run.py']
cid = subprocess.check_output(args, universal_newlines=True).strip()
data = json.loads(subprocess.check_output(['docker', 'inspect', cid], universal_newlines=True))[0]
assert data['Image'] == image and data['Config']['Labels']['org.opencontainers.image.revision'] == build['revision']
receipt = {'schema': 'c3-semantic-compilation-runtime-v1', 'actual_container': cid, 'actual_image_id': image,
    'source_revision': build['revision'], 'source_tree': build['tree'], 'actual_user': data['Config']['User'],
    'mounts': data['Mounts'], 'database_credentials_passed': False, 'docker_socket_mounted': False,
    'public_ports': False, 'runtime_source_overlay': False, 'holdout_used': False,
    'started_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'CREATED_BEFORE_MODEL_CALLS'}
(trial / 'evidence/runtime-identity.json').write_text(json.dumps(receipt, indent=2) + '\n')
begin = time.monotonic()
with (trial / 'private/process.log').open('x') as log:
    result = subprocess.run(['docker', 'start', '-a', cid], stdout=log, stderr=subprocess.STDOUT)
receipt.update(status='FINISHED', exit_code=result.returncode, elapsed_seconds=time.monotonic() - begin)
(trial / 'evidence/runtime-identity.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: receipt[k] for k in ('status', 'exit_code', 'elapsed_seconds')}))
