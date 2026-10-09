from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import base64,json,os,subprocess
ROOT=Path('/data/watt/c2-execution-readiness-20261009');P=ROOT/'private';E=ROOT/'evidence';API='watt-c2-api-20261009'
target=P/'canonical-freeze'
if not target.exists():target.mkdir(mode=0o700)
assert not list(target.iterdir()),'Preserve previous raw freeze'
code='import json;from pathlib import Path;p=Path("/tmp/private/c2-canonical");print(json.dumps({f.name:f.read_text() for f in p.iterdir() if f.is_file()}))'
files=json.loads(subprocess.check_output(['docker','exec',API,'python','-c',code],universal_newlines=True))
assert len(files)==2
for name,content in files.items():
    assert Path(name).name==name
    with (target/name).open('x') as stream:os.fchmod(stream.fileno(),0o600);stream.write(content)
secrets=[]
for path in P.glob('*.env'):
    for line in path.read_text().splitlines():
        if '=' not in line:continue
        key,value=line.split('=',1)
        if value and any(word in key for word in ('KEY','TOKEN','PASSWORD','DATABASE_URL')):secrets.append(value)
credentials=json.loads((P/'credentials.json').read_text());secrets += [str(value) for key,value in credentials.items() if any(word in key for word in ('password','token'))]
secrets.append(base64.b64encode((credentials['gitea_user']+':'+credentials['gitea_password']).encode()).decode())
public=E/'canonical-freeze';public.mkdir(mode=0o750)
redactions=0
for file in target.iterdir():
    content=file.read_text()
    for value in sorted(set(secrets),key=len,reverse=True):
        redactions+=content.count(value);content=content.replace(value,'[REDACTED]')
    data=json.loads(content)
    data['public_release']={'method':'exact known private credential values removed before publication','captured_at_utc':datetime.now(timezone.utc).isoformat(),'private_root_released':False,'evidence_level':'persistent Owner facts; no qualification PASS inferred'}
    (public/file.name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
print(json.dumps({'canonical_public_files':len(list(public.iterdir())),'known_credential_redactions':redactions,'private_source_retained':str(target),'new_work_only':True}),flush=True)