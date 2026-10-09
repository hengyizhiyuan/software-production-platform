"""Snapshot 2 targeted development regression; no final-image/AI Work claim."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json, os, subprocess, tarfile, time, sys, xml.etree.ElementTree as ET
ROOT=Path("/data/watt/c3-semantic-convergence-20261009"); P=ROOT/"private"; E=ROOT/"evidence"
manifest=json.loads((ROOT/"development-inputs-dev-regression-3.json").read_text())
assert manifest["directory"]=="dev-regression-3"
D=ROOT/manifest["directory"];D.mkdir(mode=0o755,exist_ok=True)
for owner in ("watt","guardian"):
    archive=ROOT/manifest[owner]["archive"]
    assert sha256(archive.read_bytes()).hexdigest()==manifest[owner]["sha256"]
    dest=D/owner
    if dest.exists():
        assert {str(path.relative_to(dest)):sha256(path.read_bytes()).hexdigest() for path in dest.rglob("*") if path.is_file()}==manifest[owner]["file_sha256"]
    else:
        dest.mkdir(mode=0o755)
        with tarfile.open(str(archive)) as inputs:
            for member in inputs.getmembers():
                relative=Path(member.name)
                assert member.isfile() and not relative.is_absolute() and ".." not in relative.parts
                inputs.extract(member,str(dest))
    actual={name:sha256((dest/name).read_bytes()).hexdigest() for name in manifest[owner]["file_sha256"]}
    assert actual==manifest[owner]["file_sha256"]
(D/"watt/ecf-current/src").mkdir(mode=0o755,parents=True,exist_ok=True)
out=E/manifest["directory"];out.mkdir(mode=0o755,exist_ok=True);assert not list(out.glob("*-receipt.json"));os.chown(str(out),10001,10001)
(out/"development-inputs.json").write_text(json.dumps(manifest,indent=2)+"\n")
IMAGE="sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209"
assert subprocess.check_output(["docker","image","inspect","--format","{{.Id}}",IMAGE],universal_newlines=True).strip()==IMAGE
envfile=P/(manifest["directory"]+".env")
creds=json.loads((P/"credentials.json").read_text())
url="postgresql+psycopg://c3_app:"+creds["postgres_password"]+"@127.0.0.1:5432/c1_contract_continuity"
with envfile.open("x") as stream:
    os.fchmod(stream.fileno(),0o600)
    stream.write("SPG_TEST_DATABASE_URL="+url+"\nSPG_DATABASE_URL="+url+"\n")
    stream.write("SPG_TEST_POSTGRES_DSN=postgresql://c3_app:"+creds["postgres_password"]+"@127.0.0.1:5432/c1_contract_continuity\n")
    stream.write("PYTHONPATH=/qualification/src:/qualification:/guardian/src:/opt/c2-owners/ecf/src:/opt/c2-test-deps\nPYTHONDONTWRITEBYTECODE=1\n")
    stream.write("C1_ECF_CURRENT_MAIN_SOURCE=/qualification/ecf-current/src\n")
def sanitize(text):
    for value in creds.values():
        if isinstance(value,str) and value:text=text.replace(value,"[REDACTED]")
    return text
for group in manifest["groups"]:
    name="watt-c3-dev3-"+group["name"]+"-20261009"
    command=["python","-m","pytest","-p","no:cacheprovider","-o","junit_family=legacy"]+group["nodes"]+["--tb=short","--junitxml=/c3-evidence/"+group["name"]+".xml"]
    args=["docker","run","--name",name,"--network","container:watt-c3-postgres-20261009","--user","10001:10001",
        "--cap-drop","ALL","--security-opt","no-new-privileges","--read-only","--tmpfs","/tmp:rw,exec,nosuid,size=512m",
        "--memory","1536m","--cpus","1","--label","watt.production=false","--label","watt.qualification=C3-development",
        "--env-file",str(envfile),"--mount","type=bind,src="+str(D/"watt")+",dst=/qualification,readonly",
        "--mount","type=bind,src="+str(D/"guardian")+",dst=/guardian,readonly",
        "--mount","type=bind,src=/data/watt/c2-execution-readiness-20261009/build-88f1d98/context/ecf-unsupported/src,dst=/qualification/ecf-current/src,readonly",
        "--mount","type=bind,src="+str(out)+",dst=/c3-evidence","--workdir","/guardian" if group.get("owner")=="guardian" else "/qualification",IMAGE]+command
    started=datetime.now(timezone.utc).isoformat();start=time.monotonic();raw=P/(name+".raw.log")
    with raw.open("x") as stream:
        os.fchmod(stream.fileno(),0o600);result=subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT)
    (out/(group["name"]+".log")).write_text(sanitize(raw.read_text(errors="replace")))
    xml=out/(group["name"]+".xml");counts={"tests":0,"failures":0,"errors":0,"skipped":0}
    if xml.exists():
        xml.write_text(sanitize(xml.read_text(errors="replace")))
        for suite in ET.parse(xml).iter("testsuite"):
            for key in counts:counts[key]+=int(suite.get(key,"0"))
    counts["passed"]=counts["tests"]-counts["failures"]-counts["errors"]-counts["skipped"]
    receipt={"schema":"c3-development-regression-v2","inputs":manifest,"dependency_image":IMAGE,
        "source_overlay":True,"is_final_runtime_qualification":False,"command":command,"container_name":name,
        "started_at_utc":started,"ended_at_utc":datetime.now(timezone.utc).isoformat(),"wall_seconds":time.monotonic()-start,
        "exit_code":result.returncode,"counts":counts,"credential_categories_redacted":["isolated PostgreSQL/control credentials"],
        "log_and_xml_sanitized":True,"live_model_calls":0,"real_ai_work_created":0,"fixture_work_mutations_only":True,
        "database_name":"c1_contract_continuity","database_configuration_key":"SPG_TEST_DATABASE_URL"}
    (out/(group["name"]+"-receipt.json")).write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({"group":group["name"],"exit_code":result.returncode,"counts":counts,"wall_seconds":receipt["wall_seconds"]}),flush=True)
    if result.returncode or counts["skipped"] or counts["tests"]==0:sys.exit(result.returncode or 2)
