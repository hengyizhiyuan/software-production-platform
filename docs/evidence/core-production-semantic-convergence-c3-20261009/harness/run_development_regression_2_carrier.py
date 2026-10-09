"""Snapshot 2 targeted development regression; no final-image/AI Work claim."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json, os, subprocess, tarfile, time, sys, xml.etree.ElementTree as ET
ROOT=Path("/data/watt/c3-semantic-convergence-20261009"); P=ROOT/"private"; E=ROOT/"evidence"
manifest=json.loads((ROOT/"development-inputs-dev-regression-2.json").read_text())
assert manifest["directory"]=="dev-regression-2"
D=ROOT/manifest["directory"];assert D.is_dir()
out=E/manifest["directory"];assert out.is_dir()
IMAGE="sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209"
envfile=P/(manifest["directory"]+".env");assert envfile.is_file()
creds=json.loads((P/"credentials.json").read_text())
manifest["groups"]=[g for g in manifest["groups"] if g["name"]=="c3-carrier"]
def sanitize(text):
    for value in creds.values():
        if isinstance(value,str) and value:text=text.replace(value,"[REDACTED]")
    return text
for group in manifest["groups"]:
    name="watt-c3-dev2-"+group["name"]+"-20261009"
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
