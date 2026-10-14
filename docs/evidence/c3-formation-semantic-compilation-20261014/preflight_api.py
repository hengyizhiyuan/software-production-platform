"""Non-destructive preflight: run the qualified image's app factory with the API's env, no ports, no DB writes."""
import json, subprocess
api = json.loads(subprocess.check_output(['docker', 'inspect', 'watt-cloud-worker-api-1']))[0]
image = json.load(open('/data/watt/ai-native-evolution-20261013/semantic-compilation-20261014/release-e13d8258/evidence/image-build.json'))['actual_image_id']
env = [e for e in api['Config']['Env'] if not e.startswith(('PATH=', 'PYTHONPATH=', 'SPG_RUNTIME_REVISION=', 'HOME=', 'LANG=', 'GPG_KEY=', 'PYTHON_'))]
networks = list(api['NetworkSettings']['Networks'])
args = ['docker', 'run', '--rm', '--network', networks[0], '--user', api['Config']['User'] or 'spg', '--entrypoint', 'python']
for e in env:
    args += ['-e', e]
for m in api['Mounts']:
    if m['Destination'] in ('/var/run/docker.sock',):
        continue
    args += ['-v', f"{m['Source']}:{m['Destination']}:ro"]
probe = ("import json,os;from spg.api.http import create_http_application;app=create_http_application();"
         "from spg.providers import fulfillment_candidate as f;from spg.config import Settings;"
         "p=f.ModelFulfillmentCandidateProvider.from_settings(Settings());"
         "from spg.application.trace_analysis import TraceAnalysisService;"
         "print(json.dumps({'app':type(app).__name__,'revision':os.environ['SPG_RUNTIME_REVISION'],"
         "'formation_provider':p is not None,'semantic_compilation':bool(p and p.supports_semantic_compilation),"
         "'trace_analysis_importable':True,'routes':len(app.routes)}))")
out = subprocess.run(args + [image, '-c', probe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
print(out.stdout.decode()[-3000:]); raise SystemExit(out.returncode)
