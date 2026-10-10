"""Persist the isolated exact application image; no production mutation."""
from datetime import datetime
from hashlib import sha256
import gzip,json,os,shutil,subprocess,time
from pathlib import Path
ROOT=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010')
BUILD=json.loads((ROOT/'final-image-2/evidence/build.json').read_text(encoding='utf-8'))
IMAGE=BUILD['image']['Id'];SOURCE=BUILD['sources']['watt']['revision']
assert IMAGE=='sha256:90f2cd847ad891fda6ca95b5736c84b680c9d58bd6a3203bf0ea31c970da0f16'
actual=json.loads(subprocess.check_output(['docker','image','inspect',IMAGE],universal_newlines=True))[0]
assert actual['Id']==IMAGE and actual['Config']['Labels']['org.opencontainers.image.revision']==SOURCE
env=dict(item.split('=',1) for item in actual['Config']['Env'] if '=' in item)
assert not any(env.get(key) for key in ('SPG_DEEPSEEK_API_KEY','SPG_NATIVE_EXECUTOR_DEEPSEEK_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY'))
TARGET=ROOT/'image-recovery-final';assert not TARGET.exists();TARGET.mkdir(mode=0o700)
archive=TARGET/'exact-image.tar.gz';started=datetime.utcnow().isoformat()+'Z';clock=time.monotonic()
with archive.open('xb') as file:
    os.fchmod(file.fileno(),0o600)
    with gzip.GzipFile(fileobj=file,mode='wb',mtime=0) as compressed:
        proc=subprocess.Popen(['docker','image','save',IMAGE],stdout=subprocess.PIPE)
        shutil.copyfileobj(proc.stdout,compressed,1024*1024)
        proc.stdout.close();assert proc.wait()==0
hash_value=sha256()
with archive.open('rb') as file:
    for block in iter(lambda:file.read(1024*1024),b''):hash_value.update(block)
receipt={'source':SOURCE,'sources':BUILD['sources'],'actual_image_id':IMAGE,'path':str(archive),
    'sha256':hash_value.hexdigest(),'bytes':archive.stat().st_size,'mode':'0600',
    'started_at_utc':started,'ended_at_utc':datetime.utcnow().isoformat()+'Z','wall_seconds':time.monotonic()-clock,
    'restore_test':'NOT_PERFORMED','offsite_copy':'NOT_PERFORMED','production_resource_mutation':False,
    'controller_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
(TARGET/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt))
