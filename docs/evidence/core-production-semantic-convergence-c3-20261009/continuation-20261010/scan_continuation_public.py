"""C3 public release known-value scan; never emits or copies private credentials."""
from datetime import datetime,timezone
from hashlib import sha256
import json, os
from pathlib import Path
import sys
ROOT=Path("/data/watt/c3-semantic-convergence-20261009")
target=ROOT/"public-delivery-c3-continuation"
assert target.is_dir() and not target.is_symlink()
values=set()
for private in (ROOT/"private",ROOT/"retry-1/private")+tuple((ROOT/"continuation-20261010").glob("*/private")):
    credentials=private/"credentials.json"
    if credentials.is_file():
        for key,value in json.loads(credentials.read_text()).items():
            if any(term in key.lower() for term in ("password","token","secret","api_key")) and isinstance(value,str) and len(value)>=12:values.add(value)
    for path in private.glob("*.env"):
        for line in path.read_text().splitlines():
            if "=" not in line:continue
            key,value=line.split("=",1)
            if value and any(term in key.upper() for term in ("PASSWORD","TOKEN","API_KEY","SECRET","DATABASE_URL","POSTGRES_DSN")) and len(value)>=12:
                values.add(value)
                if key.endswith(("_DATABASE_URL","_DSN")):
                    from urllib.parse import urlsplit,unquote
                    try:
                        password=urlsplit(value).password
                        if password and len(password)>=12:values.update((password,unquote(password)))
                    except ValueError:pass
assert values,"Known-value basis must actually exist"
files=[];matches=[]
for path in sorted(target.rglob("*")):
    if not path.is_file():continue
    assert not path.is_symlink()
    raw=path.read_bytes()
    name=path.relative_to(target).as_posix()
    files.append({"path":name,"sha256":sha256(raw).hexdigest(),"bytes":len(raw)})
    if any(v.encode() in raw for v in values):matches.append(name)
receipt={"schema":"c3-public-release-known-secret-scan-v1","captured_at_utc":datetime.now(timezone.utc).isoformat(),
    "public_delivery_root":str(target),"public_files_scanned":len(files),"files":files,"matching_paths":matches,
    "status":"FAIL" if matches else "PASS_KNOWN_VALUES_ONLY","sensitive_values_output":False,
    "scope":"Known original and new C3 control/fixture credentials and authorized shared test Provider key; memory only, unknown secrets not certified absent",
    "unknown_sensitive_values_not_claimed_absent":True}
destination=ROOT/"continuation-20261010/public-release-known-secret-scan.json"
assert not destination.exists()
with destination.open("x") as f:f.write(json.dumps(receipt,indent=2)+"\n")
os.chmod(str(destination),0o644)
print(json.dumps({"status":receipt["status"],"public_files_scanned":len(files),"known_secret_matches":len(matches),"matching_paths":matches}))
sys.exit(bool(matches))
