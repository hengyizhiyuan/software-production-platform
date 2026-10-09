from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import base64,json,os,subprocess
ROOT=Path('/data/watt/c2-execution-readiness-20261009');P=ROOT/'private';E=ROOT/'evidence';API='watt-c2-api-20261009'
script=ROOT/'c2_export_work_snapshot.py';os.chmod(str(script),0o644)
assert subprocess.run(['docker','exec','-i',API,'python','-c','import sys;from pathlib import Path;Path("/tmp/c2_export_work_snapshot.py").write_bytes(sys.stdin.buffer.read())'],input=script.read_bytes(),stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode==0
state=(E/'normal-entry-state.json').read_bytes()
assert subprocess.run(['docker','exec','-i',API,'python','-c','import sys;from pathlib import Path;Path("/tmp/c2-frozen-state.json").write_bytes(sys.stdin.buffer.read())'],input=state,stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode==0
command=['docker','exec',API,'python','/tmp/c2_export_work_snapshot.py','--state-file','/tmp/c2-frozen-state.json','--work-id','b9c67d91-2cc1-5f91-bf61-8d7939b45cc3','--expected-database','spg_c2_qualification_20261009','--private-output-dir','/tmp/private/c2-canonical']
result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
info=json.loads(result.stdout);print(json.dumps(info),flush=True)
assert result.returncode==0,'Private canonical export failed; preserve failure without public raw message'
target=P/'canonical-freeze';assert not target.exists()
subprocess.check_call(['docker','cp',API+':/tmp/private/c2-canonical',str(target)],stdout=subprocess.DEVNULL)
os.chmod(str(target),0o700)
for file in target.iterdir():os.chmod(str(file),0o600)
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