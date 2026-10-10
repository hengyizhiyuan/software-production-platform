import json,subprocess,gzip,shutil,hashlib,time,os
from pathlib import Path
from datetime import datetime,timezone
T=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/wire-feedback-recovery-20261010')
b=json.loads((T/'final-image/evidence/build.json').read_text())
image=b['image']['Id'];assert image=='sha256:e42fcb7dfe18254f1396f2faaaadd95b0d24efe445db6ce19beedfdebac32726'
assert subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',image],universal_newlines=True).strip()==image
p=T/'image-recovery';p.mkdir(mode=0o700)
out=p/'exact-image.tar.gz'
started=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
with out.open('xb') as f:
 os.fchmod(f.fileno(),0o600)
 proc=subprocess.Popen(['docker','save',image],stdout=subprocess.PIPE)
 with gzip.GzipFile(fileobj=f,mode='wb',compresslevel=1) as gz:shutil.copyfileobj(proc.stdout,gz,1024*1024)
 assert proc.wait()==0
h=hashlib.sha256()
with out.open('rb') as f:
 for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
receipt={'schema':'c3-predecode-exact-image-recovery-v1','application_source':b['sources']['watt']['revision'],
 'image_id':image,'archive':str(out),'archive_bytes':out.stat().st_size,'archive_sha256':h.hexdigest(),
 'started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),'wall_seconds':time.monotonic()-clock,
 'archive_mode':'0600','directory_mode':'0700','model_calls':0,'production_resources_modified':False,
 'restore_test':'NOT_PERFORMED','offsite_backup':'NOT_PERFORMED','purpose':'Restore exact qualified isolated image; rebuilding may produce another image identity'}
(T/'image-recovery-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
