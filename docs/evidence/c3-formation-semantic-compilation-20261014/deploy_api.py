"""Replace only the formal API image with the qualified C3 image; automatic rollback.

Reuses the existing trace release procedure: exact image, compose files preserved,
API-only override, quiescence admission, health gate, rollback on any failure.
"""
import hashlib, json, os, pathlib, subprocess, time, urllib.request
os.umask(0o077)
r = pathlib.Path(__file__).resolve().parent
SOURCE = 'e13d82588877379c6021f30d73c9503ecb0a0ea5'
build = json.loads((r / 'evidence/image-build.json').read_text())
assert build['exit_code'] == 0 and build['revision'] == SOURCE
for name in ('attestation', 'focused', 'postgres-final'):
    assert json.loads((r / f'evidence/installed/{name}-run.json').read_text())['exit_code'] == 0
qualified = build['actual_image_id']
tag = 'watt-cloud-worker:c3-semantic-compilation-' + SOURCE[:8]
def run(*a, input=None, timeout=120):
    return subprocess.check_output(a, input=input, timeout=timeout, stderr=subprocess.STDOUT)
out = r / 'deploy'; out.mkdir(exist_ok=False)
api = json.loads(run('docker', 'inspect', 'watt-cloud-worker-api-1'))[0]
files = api['Config']['Labels']['com.docker.compose.project.config_files'].split(',')
args = ['docker', 'compose', '-p', 'watt-cloud-worker']
for f in files: args += ['-f', f]
before_config = json.loads(run(*args, 'config', '--format', 'json'))
(out / 'original-compose-config.private.json').write_text(json.dumps(before_config))
hashes = {f: hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest() for f in files}
rollback = 'watt-cloud-worker:c3-predeploy-rollback-' + SOURCE[:8]
run('docker', 'tag', api['Image'], rollback)
ids = run('docker', 'ps', '-q', '--no-trunc').decode().split()
containers = [{'name': c['Name'].lstrip('/'), 'id': c['Id'], 'image': c['Image'], 'status': c['State']['Status']}
    for c in json.loads(run('docker', 'inspect', *ids))]
(out / 'containers-before.json').write_text(json.dumps(containers, indent=2))
backup = {'source_commit': SOURCE, 'old_api_id': api['Id'], 'old_image': api['Image'],
    'old_revision_label': api['Config']['Labels'].get('org.opencontainers.image.revision'),
    'rollback_tag': rollback, 'compose_files': files, 'compose_sha256': hashes}
(out / 'backup.json').write_text(json.dumps(backup, indent=2))
run('docker', 'tag', qualified, tag)
assert json.loads(run('docker', 'image', 'inspect', tag))[0]['Id'] == qualified
admission = """import json
from spg.config import Settings
from spg.infrastructure.persistence import Database
from sqlalchemy import text
s=Settings();db=Database.from_settings(s)
with db.engine.connect() as c:
 c.execute(text('SET TRANSACTION READ ONLY'))
 a=c.execute(text('SELECT count(*) FROM execution_allocations WHERE released_at IS NULL')).scalar()
 q=c.execute(text("SELECT count(*) FROM executor_queue WHERE condition NOT IN ('COMPLETED','FAILED','CANCELLED')")).scalar();c.rollback()
assert a==0 and q==0 and not (s.native_executor_storage_root/'trace-analysis'/'.active-investigation').exists(),'Active work/investigation; defer'
print(json.dumps({'status':'ADMITTED','unreleased_allocations':a,'active_queue_entries':q,'analysis_lock_present':False}))
"""
(out / 'final-admission.json').write_bytes(run('docker', 'exec', '-i', 'watt-cloud-worker-api-1', 'python', '-', input=admission.encode()))
override = out / 'deployed-api.override.yml'
override.write_text('services:\n  api:\n    image: ' + tag + '\n')
after = json.loads(run(*args, '-f', str(override), 'config', '--format', 'json'))
assert after['services']['api']['image'] == tag
after['services']['api']['image'] = before_config['services']['api']['image']
assert after == before_config, 'Unexpected configuration change'
def recreate(path, log):
    p = subprocess.run(args + ['-f', str(path), 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
        '--force-recreate', 'api'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
    (out / log).write_bytes(p.stdout); p.check_returncode()
def healthy():
    for _ in range(120):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=5) as h:
                raw = h.read(); assert h.status == 200
            health = json.loads(raw); assert health.get('application_initialized'); return health
        except Exception:
            time.sleep(5)
    raise RuntimeError('Health not restored in 10 minutes')
try:
    recreate(override, 'activation.private.log')
    health = healthy()
    new = json.loads(run('docker', 'inspect', 'watt-cloud-worker-api-1'))[0]
    assert new['Image'] == qualified
    smoke = run('docker', 'exec', 'watt-cloud-worker-api-1', 'python', '-c',
        "import json,os;from spg.providers import fulfillment_candidate as f;from spg.config import Settings;"
        "p=f.ModelFulfillmentCandidateProvider.from_settings(Settings());"
        "print(json.dumps({'revision':os.environ['SPG_RUNTIME_REVISION'],'provider_configured':p is not None,"
        "'semantic_compilation':bool(p and p.supports_semantic_compilation),'contract':f._SEMANTIC_COMPILATION_CONTRACT}))")
    smoke = json.loads(smoke.decode().strip().splitlines()[-1])
    assert smoke['revision'] == SOURCE and smoke['provider_configured'] and smoke['semantic_compilation']
    result = {'status': 'PASS', 'source_commit': SOURCE, 'old_image': api['Image'], 'old_revision_label': backup['old_revision_label'],
        'new_image': qualified, 'new_api_id': new['Id'], 'started_at': new['State']['StartedAt'], 'health': health,
        'runtime_smoke': smoke, 'scope': 'API_IMAGE_ONLY_LAST_OVERRIDE', 'compose_files_preserved': files,
        'deployment_override': str(override), 'rollback_tag': rollback}
    (out / 'activation-result.json').write_text(json.dumps(result, indent=2)); print(json.dumps(result), flush=True)
except Exception as error:
    rb = out / 'rollback.override.private.yml'
    rb.write_text('services:\n  api:\n    image: ' + rollback + '\n')
    recreate(rb, 'rollback.private.log'); healthy()
    print(json.dumps({'event': 'ROLLBACK_EXECUTED', 'image': api['Image'], 'error': repr(error)[:400]}), flush=True)
    raise
