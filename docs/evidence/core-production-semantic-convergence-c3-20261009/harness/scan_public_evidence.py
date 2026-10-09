"""Known-secret scan; never print values or copy private state into public evidence."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess
ROOT=Path('/data/watt/c3-semantic-convergence-20261009'); E=ROOT/'evidence'
secrets=[]
private=json.loads((ROOT/'private/credentials.json').read_text())
for key,value in private.items():
    if any(part in key.lower() for part in ('password','token','secret','api_key')) and isinstance(value,str) and len(value)>=12:
        secrets.append(value)
old=json.loads(subprocess.check_output(['docker','inspect','watt-n1-api-20261008'],universal_newlines=True))[0]
for setting in old['Config']['Env']:
    key,value=setting.split('=',1)
    if any(part in key for part in ('PASSWORD','TOKEN','API_KEY','DATABASE_URL')) and len(value)>=12:
        secrets.append(value)
found=[];count=0
for path in E.rglob('*'):
    if path.is_file():
        count+=1; content=path.read_bytes()
        if any(value.encode() in content for value in secrets):found.append(path.relative_to(E).as_posix())
receipt={'captured_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'known new control credentials and authorized shared test Provider credential; public C3 files only','scanned_files':count,'sensitive_values_output':False,'matching_paths':found,'unknown_sensitive_values_not_claimed_absent':True}
(E/'known-secret-scan.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'public_files_scanned':count,'known_secret_matches':len(found),'matching_paths':found}))
raise SystemExit(bool(found))
