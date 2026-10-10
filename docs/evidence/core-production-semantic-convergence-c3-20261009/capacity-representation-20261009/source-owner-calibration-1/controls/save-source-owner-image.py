import gzip,json,os,subprocess,time
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
R=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/source-owner-calibration-20261010')
build=json.loads((R/'final-image/evidence/build.json').read_text())
image=build['image']['Id'];assert build['exit_code']==0
T=R/'image-recovery';T.mkdir(mode=0o700,exist_ok=False)
out=T/'exact-image.tar.gz';started=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
p=subprocess.Popen(['docker','image','save',image],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
with out.open('xb') as f:
 os.fchmod(f.fileno(),0o600)
 with gzip.GzipFile(fileobj=f,mode='wb',compresslevel=1,mtime=0) as z:
  for b in iter(lambda:p.stdout.read(1048576),b''):z.write(b)
assert p.wait()==0,p.stderr.read().decode(errors='replace')
h=sha256()
with out.open('rb') as f:
 for b in iter(lambda:f.read(1048576),b''):h.update(b)
receipt={'schema':'c3-exact-image-recovery-v1','image_id':image,'watt_source':build['sources']['watt']['revision'],
 'archive_path':str(out),'archive_sha256':h.hexdigest(),'archive_bytes':out.stat().st_size,
 'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),'wall_seconds':time.monotonic()-clock,
 'restore_load':'NOT_PERFORMED','offsite_backup':'NOT_PERFORMED','controller_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
(T/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
