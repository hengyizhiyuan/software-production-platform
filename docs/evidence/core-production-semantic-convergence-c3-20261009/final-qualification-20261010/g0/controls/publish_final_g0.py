from pathlib import Path
from hashlib import sha256
import json,os,tarfile
R=Path('/data/watt/c3-semantic-convergence-20261009/final-g0-qualification-20261010');E=R/'evidence'
assert (E/'private-recovery-checkpoint.json').is_file()
DEST=R/'public-delivery';assert not DEST.exists()
credentials=json.loads((R/'private/credentials.json').read_text())
values={v.encode() for v in credentials.values() if isinstance(v,str) and len(v)>=20}
env=Path('/data/watt/c3-semantic-convergence-20261009/retry-1/private/watt-c3-retry1-api-20261009.env').read_text()
for line in env.splitlines():
 if '=' in line:
  k,v=line.split('=',1)
  if v and any(t in k for t in ('KEY','TOKEN','SECRET','PASSWORD')):values.add(v.encode())
original=json.loads((E/'original-g0-input.json').read_text())['prompt'].encode()
files={}
for p in E.rglob('*.json'):
 if p.name=='original-g0-input.json':continue
 b=p.read_bytes();assert not any(v in b for v in values),'PUBLIC_CREDENTIAL_VALUE_FOUND'
 assert original not in b,'PUBLIC_ORIGINAL_HUMAN_TEXT_FOUND'
 json.loads(b)
 files['receipts/'+p.relative_to(E).as_posix()]=b
inputs=R.parent/'final-g0-control-inputs-20261010'
for p in inputs.glob('*.py'):
 b=p.read_bytes();assert not any(v in b for v in values) and original not in b
 files['controls/'+p.name]=b
files['manifest.json']=(json.dumps({'schema':'c3-final-g0-public-byte-manifest-v1','files':[{'file':n,'sha256':sha256(b).hexdigest(),'bytes':len(b)} for n,b in sorted(files.items())],'raw_original_inventory_or_candidate_released':False,'credential_scan':'PASS_KNOWN_VALUES','private_original_input_scan':'PASS'},indent=2)+'\n').encode()
DEST.mkdir(mode=0o755)
for n,b in files.items():
 p=DEST/n;p.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
 with p.open('xb') as f:os.fchmod(f.fileno(),0o644);f.write(b)
tar=R/'public-delivery.tar.gz'
with tarfile.open(str(tar),'x:gz') as a:
 for n in sorted(files):a.add(str(DEST/n),arcname=n)
print(json.dumps({'public_directory':str(DEST),'archive':str(tar),'sha256':sha256(tar.read_bytes()).hexdigest(),'files':len(files),'credentials_found':False,'private_input_found':False}))
