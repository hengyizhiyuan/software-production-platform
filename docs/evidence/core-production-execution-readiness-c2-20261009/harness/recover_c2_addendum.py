from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import base64,json,os,subprocess
ROOT=Path('/data/watt/c2-execution-readiness-20261009');P=ROOT/'private';E=ROOT/'evidence';API='watt-c2-api-20261009'
code='import json;from pathlib import Path;paths=[Path("/tmp/private/c2-readonly-boundary/5c1611bf99234cceba6a1c355157b358.json"),*Path("/tmp/private/c2-canonical-readonly").glob("*.json")];print(json.dumps({p.name:p.read_text() for p in paths if p.is_file()}))'
files=json.loads(subprocess.check_output(['docker','exec',API,'python','-c',code],universal_newlines=True))
target=P/'agent-readonly-snapshots';assert not target.exists();target.mkdir(mode=0o700)
secrets=[]
for path in P.glob('*.env'):
    for line in path.read_text().splitlines():
        if '=' not in line:continue
        key,value=line.split('=',1)
        if value and any(word in key for word in ('KEY','TOKEN','PASSWORD','DATABASE_URL')):secrets.append(value)
credentials=json.loads((P/'credentials.json').read_text());secrets += [str(value) for key,value in credentials.items() if any(word in key for word in ('password','token'))]
secrets.append(base64.b64encode((credentials['gitea_user']+':'+credentials['gitea_password']).encode()).decode())
for name,content in files.items():
    assert Path(name).name==name
    with (target/name).open('x') as stream:os.fchmod(stream.fileno(),0o600);stream.write(content)
    if not name.endswith('where-owner-addendum.json'):continue
    redactions=0
    for value in sorted(set(secrets),key=len,reverse=True):redactions+=content.count(value);content=content.replace(value,'[REDACTED]')
    value=json.loads(content);value['public_release']={'known_credential_redactions':redactions,'scope':'persistent WHERE Owner records; no deleted container image observation is fabricated'}
    (E/'where-owner-addendum.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
print(json.dumps({'private_snapshots_retained':len(files),'path':str(target),'where_owner_addendum_published':(E/'where-owner-addendum.json').exists(),'credentials_published':False}))