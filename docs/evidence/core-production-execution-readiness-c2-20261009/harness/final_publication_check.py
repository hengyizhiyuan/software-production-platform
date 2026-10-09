from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import base64, json, tarfile
ROOT=Path('/data/watt/c2-execution-readiness-20261009')
P=ROOT/'private'
archive=ROOT/'c2-final-publication-input.tar'
target=ROOT/'delivery'/'publication-check-20261009'
assert not target.exists()
target.mkdir(parents=True,mode=0o755)
with tarfile.open(str(archive),'r') as source:
    for item in source.getmembers():
        assert not item.issym() and not item.islnk()
        assert item.isfile() or item.isdir()
        destination=(target/item.name).resolve()
        assert destination==target.resolve() or target.resolve() in destination.parents
        source.extract(item,str(target))
values=[]
for path in P.glob('*.env'):
    for line in path.read_text().splitlines():
        if '=' not in line: continue
        key,value=line.split('=',1)
        if value and any(word in key for word in ('KEY','TOKEN','PASSWORD','DATABASE_URL')):
            values.append(value.encode())
credentials=json.loads((P/'credentials.json').read_text())
values += [str(value).encode() for key,value in credentials.items()
           if any(word in key for word in ('password','token'))]
values.append(base64.b64encode((credentials['gitea_user']+':'+credentials['gitea_password']).encode()))
files=sorted(p for p in target.rglob('*') if p.is_file())
matches=[p.relative_to(target).as_posix() for p in files
         if any(value in p.read_bytes() for value in values)]
assert not matches,('Known credential matches; publication blocked',matches)
receipt={'schema':'c2-final-publication-check-v1',
'captured_at_utc':datetime.now(timezone.utc).isoformat(),
'scanned_public_files':len(files),'known_credential_matches':0,
'input_archive_sha256':sha256(archive.read_bytes()).hexdigest(),
'input_archive_size_bytes':archive.stat().st_size,
'private_directory_excluded':True,
'model_credential_scope':'HUMAN_AUTHORIZED_SHARED_TEST',
'model_key_changed_or_rotated':False,
'scope':'Exact known private credential values only; includes final reports, harness and public Owner evidence; not a universal secret detector.',
'qualification_status':'C2 PARTIAL — Exact Engineering Blocker'}
output=ROOT/'delivery'/'publication-check.json'
output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'scanned_public_files':len(files),'known_credential_matches':0,'receipt_path':str(output)}))
