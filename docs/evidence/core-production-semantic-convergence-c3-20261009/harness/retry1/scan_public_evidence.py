import sys
sys.dont_write_bytecode = True
"""Scan retry public evidence against known retry private values; no raw values output."""
from c3_retry_scope import scoped_runtime_root, verify_frozen_controls
from pathlib import Path
from datetime import datetime,timezone
import json
ROOT=scoped_runtime_root("known-secret-public-evidence-scan");E=ROOT/"evidence"
verify_frozen_controls(ROOT)
secrets=[]
private=json.loads((ROOT/"private/credentials.json").read_text())
for key,value in private.items():
    if any(part in key.lower() for part in ("password","token","secret","api_key")) and isinstance(value,str) and value:
        secrets.append(value)
for envfile in (ROOT/"private").glob("*.env"):
    assert not envfile.is_symlink()
    for setting in envfile.read_text().splitlines():
        if "=" not in setting:continue
        key,value=setting.split("=",1)
        if value and any(part in key.upper() for part in ("PASSWORD","TOKEN","API_KEY","DATABASE_URL","DSN")):secrets.append(value)
found=[];count=0
for path in E.rglob("*"):
    assert not path.is_symlink()
    if path.is_file():
        count+=1;content=path.read_bytes()
        if any(value.encode() in content for value in secrets):found.append(path.relative_to(E).as_posix())
receipt={"captured_at_utc":datetime.now(timezone.utc).isoformat(),"run_root":str(ROOT),
    "scope":"known retry-only private credentials and authorized shared test Provider copy; retry public files only",
    "scanned_files":count,"sensitive_values_output":False,"matching_paths":found,"unknown_sensitive_values_not_claimed_absent":True}
with (E/"known-secret-scan.json").open("x") as stream:json.dump(receipt,stream,indent=2);stream.write("\n")
print(json.dumps({"public_files_scanned":count,"known_secret_matches":len(found),"matching_paths":found}))
raise SystemExit(bool(found))
