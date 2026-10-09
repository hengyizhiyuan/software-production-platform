"""Preserve only the new isolated exact image; never resumes any Work/service."""
import gzip,json,os,shutil,subprocess,time
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
ROOT=Path('/data/watt/c3-semantic-convergence-20261009')
TARGET=ROOT/'continuation-20261010/image-recovery'
assert not TARGET.exists();TARGET.mkdir(mode=0o700)
build=json.loads((ROOT/'continuation-20261010/continuation-final-image/evidence/build.json').read_text())
IMAGE=build['image']['Id'];actual=json.loads(subprocess.check_output(['docker','image','inspect',IMAGE],universal_newlines=True))[0]
assert actual['Id']==IMAGE and actual['Config']['Labels']['org.opencontainers.image.revision']==build['sources']['watt']['revision']
assert shutil.disk_usage(str(TARGET)).free>actual['Size']*2
archive=TARGET/'exact-image.tar.gz';started=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
with archive.open('xb') as stream:
 os.fchmod(stream.fileno(),0o600)
 process=subprocess.Popen(['docker','image','save',IMAGE],stdout=subprocess.PIPE)
 with gzip.GzipFile(fileobj=stream,mode='wb',compresslevel=1) as zipped:shutil.copyfileobj(process.stdout,zipped,1024*1024)
 process.stdout.close();code=process.wait()
assert code==0
h=sha256()
with archive.open('rb') as stream:
 for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
receipt={'schema':'c3-continuation-image-recovery-v1','started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),'wall_seconds':time.monotonic()-clock,'actual_image_id':IMAGE,'sources':build['sources'],'archive_path':str(archive),'archive_sha256':h.hexdigest(),'archive_bytes':archive.stat().st_size,'archive_permissions':'0600','owner':'root','services_started':False,'business_database_mutations':False,'restore_exercise_performed':False,'offsite_copy_proven':False,'controller_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'New qualification image only; old checkpoints untouched; restore requires identity verification and isolation'}
(ROOT/'continuation-20261010/image-recovery-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
