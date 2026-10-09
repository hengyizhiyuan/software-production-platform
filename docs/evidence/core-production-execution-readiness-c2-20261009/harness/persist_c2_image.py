from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import gzip,json,subprocess
ROOT=Path('/data/watt/c2-execution-readiness-20261009');image='watt-c2:88f1d98';target=ROOT/'image-88f1d98.tar.gz'
assert not target.exists(),'Preserve image archive'
with target.open('xb') as output:
    with gzip.GzipFile(fileobj=output,mode='wb',compresslevel=1,mtime=0) as compressed:
        process=subprocess.Popen(['docker','image','save',image],stdout=subprocess.PIPE)
        for chunk in iter(lambda:process.stdout.read(1024*1024),b''):compressed.write(chunk)
        assert process.wait()==0
hasher=sha256()
with target.open('rb') as stream:
    for chunk in iter(lambda:stream.read(1024*1024),b''):hasher.update(chunk)
receipt={'captured_at_utc':datetime.now(timezone.utc).isoformat(),'archive_path':str(target),'size_bytes':target.stat().st_size,'sha256':hasher.hexdigest(),'image_id':'sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209','source_revision':'88f1d9805d3ed1aa779ed3c78902b193fae240f8','runtime_credentials_included':False,'restore':'gzip -dc image-88f1d98.tar.gz | docker image load; verify image ID, then attest'}
(ROOT/'evidence/image-recovery.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'image_archive_retained':str(target),'size_bytes':receipt['size_bytes'],'sha256':receipt['sha256']}),flush=True)