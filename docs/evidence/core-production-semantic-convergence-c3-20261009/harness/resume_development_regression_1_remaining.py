"""Source-overlay development regression; never a final runtime qualification."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,subprocess,tarfile,time,sys
ROOT=Path('/data/watt/c3-semantic-convergence-20261009');P=ROOT/'private';E=ROOT/'evidence'
manifest=json.loads((ROOT/'development-inputs.json').read_text())
D=ROOT/manifest['directory'];assert D.is_dir()
manifest['groups']=manifest['groups'][2:]
out=E/manifest['directory'];assert out.is_dir();os.chown(str(out),10001,10001)
IMAGE='sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209'
envfile=P/(manifest['directory']+'.env')
creds=json.loads((P/'credentials.json').read_text())
subprocess.check_call(['docker','exec','watt-c3-postgres-20261009','psql','-U','c3_app','-d','postgres','-Atc','SELECT 1'])
assert envfile.is_file()
# Unsupported ECF is the previously captured regression-only source, not runtime owner.
for group in manifest['groups']:
    name='watt-c3-dev-'+group['name']+'-20261009'
    command=['python','-m','pytest','-p','no:cacheprovider','-o','junit_family=legacy']+group['nodes']+['--tb=short','--junitxml=/c3-evidence/'+group['name']+'.xml']
    args=['docker','run','--name',name,'--network','container:watt-c3-postgres-20261009','--user','10001:10001',
        '--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,exec,nosuid,size=512m',
        '--memory','1536m','--cpus','1','--label','watt.production=false','--label','watt.qualification=C3-development',
        '--env-file',str(envfile),'--mount','type=bind,src='+str(D/'watt')+',dst=/qualification,readonly',
        '--mount','type=bind,src='+str(D/'guardian')+',dst=/guardian,readonly',
        '--mount','type=bind,src=/data/watt/c2-execution-readiness-20261009/build-88f1d98/context/ecf-unsupported/src,dst=/qualification/ecf-current/src,readonly',
        '--mount','type=bind,src='+str(out)+',dst=/c3-evidence','--workdir','/guardian' if group.get('owner')=='guardian' else '/qualification',IMAGE]+command
    started=datetime.now(timezone.utc).isoformat();start=time.monotonic()
    raw=P/(name+'.raw.log')
    with raw.open('x') as stream:
        os.fchmod(stream.fileno(),0o600);result=subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT)
    safe=raw.read_text(errors='replace')
    for value in creds.values():
        if isinstance(value,str) and len(value)>20:safe=safe.replace(value,'[REDACTED]')
    (out/(group['name']+'.log')).write_text(safe)
    receipt={'schema':'c3-development-regression-v1','inputs':manifest,'dependency_image':IMAGE,
        'source_overlay':True,'is_final_runtime_qualification':False,'command':command,
        'started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),
        'wall_seconds':time.monotonic()-start,'exit_code':result.returncode,'live_model_calls':0,'real_work_created':0}
    (out/(group['name']+'-receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'group':group['name'],'exit_code':result.returncode,'wall_seconds':receipt['wall_seconds']}),flush=True)
    if result.returncode:sys.exit(result.returncode)
