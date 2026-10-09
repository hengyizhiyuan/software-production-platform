"""Snapshot 2 targeted development regression; no final-image/AI Work claim."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json, os, subprocess, tarfile, time, sys, xml.etree.ElementTree as ET
ROOT=Path("/data/watt/c3-semantic-convergence-20261009"); P=ROOT/"private"; E=ROOT/"evidence"
manifest=json.loads((ROOT/"development-inputs-dev-regression-3-guardian-contract.json").read_text())
assert manifest["directory"]=="dev-regression-3-guardian-contract"
D=ROOT/manifest["base_source_directory"];assert D.is_dir()
patch=ROOT/"dev-regression-3-fixture-input";assert patch.is_dir()
archive=ROOT/manifest["fixture_patch"]["archive"]
assert sha256(archive.read_bytes()).hexdigest()==manifest["fixture_patch"]["sha256"]
for relative,digest in manifest["fixture_patch"]["file_sha256"].items():
    assert sha256((patch/relative).read_bytes()).hexdigest()==digest
guardian=ROOT/"dev-regression-3-guardian-contract-input";assert not guardian.exists();guardian.mkdir()
garchive=ROOT/manifest["guardian"]["archive"];assert sha256(garchive.read_bytes()).hexdigest()==manifest["guardian"]["sha256"]
with tarfile.open(str(garchive)) as inputs:
    for member in inputs.getmembers():
        relative=Path(member.name);assert not relative.is_absolute() and ".." not in relative.parts
        if member.isdir():continue
        assert member.isfile();inputs.extract(member,str(guardian))
for relative,digest in manifest["guardian"]["file_sha256"].items():
    assert sha256((guardian/relative).read_bytes()).hexdigest()==digest
out=E/manifest["directory"];assert not out.exists();out.mkdir();os.chown(str(out),10001,10001)
IMAGE="sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209"
envfile=P/"dev-regression-3.env";assert envfile.is_file()
creds=json.loads((P/"credentials.json").read_text())

def sanitize(text):
    for value in creds.values():
        if isinstance(value,str) and value:text=text.replace(value,"[REDACTED]")
    return text
for group in manifest["groups"]:
    name="watt-c3-dev3-contract-"+group["name"]+"-20261009"
    fixture_tmp=P/(name+"-fixture-tmp");assert not fixture_tmp.exists();fixture_tmp.mkdir(mode=0o700);os.chown(str(fixture_tmp),10001,10001)
    command=["python","-m","pytest","--basetemp=/c3-private-fixture/tests","-p","no:cacheprovider","-o","junit_family=legacy"]+group["nodes"]+["--tb=short","--junitxml=/c3-evidence/"+group["name"]+".xml"]
    args=["docker","run","--name",name,"--network","container:watt-c3-postgres-20261009","--user","10001:10001",
        "--cap-drop","ALL","--security-opt","no-new-privileges","--read-only","--tmpfs","/tmp:rw,exec,nosuid,size=512m",
        "--memory","1536m","--cpus","1","--label","watt.production=false","--label","watt.qualification=C3-development",
        "--env-file",str(envfile),"--mount","type=bind,src="+str(D/"watt")+",dst=/qualification,readonly",
        "--mount","type=bind,src="+str(guardian)+",dst=/guardian,readonly",
        "--mount","type=bind,src=/data/watt/c2-execution-readiness-20261009/build-88f1d98/context/ecf-unsupported/src,dst=/qualification/ecf-current/src,readonly",
        "--mount","type=bind,src="+str(out)+",dst=/c3-evidence",
        "--mount","type=bind,src="+str(fixture_tmp)+",dst=/c3-private-fixture","--workdir","/guardian" if group.get("owner")=="guardian" else "/qualification",IMAGE]+command
    for relative in manifest["fixture_patch"]["file_sha256"]:
        position=args.index("--workdir")
        args[position:position]=["--mount","type=bind,src="+str(patch/relative)+",dst=/qualification/"+relative+",readonly"]
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
    owner_files={}
    for file in fixture_tmp.rglob("guardian/results/*.json"):
        result_payload=json.loads(file.read_text())
        request_id=result_payload["request_id"]
        request=file.parent.parent/"requests"/(request_id+".json")
        assert request.is_file()
        owner_files[request_id]={"actual_result":result_payload,"actual_request":json.loads(request.read_text()),
            "private_result_path":str(file),"private_request_path":str(request)}
    if owner_files:
        target=out/(group["name"]+"-guardian-owner-records.json")
        target.write_text(sanitize(json.dumps({"schema":"c3-scoped-guardian-fixture-owner-records-v1",
            "sources":manifest["sources"],"container":name,"observed_at_utc":datetime.now(timezone.utc).isoformat(),
            "scope":"exact Guardian request/result files from this fixture group only","records":owner_files},indent=2))+"\n")
        receipt["guardian_owner_records"]=target.name
    receipt["private_fixture_basetemp_persisted"]=str(fixture_tmp)
    (out/(group["name"]+"-receipt.json")).write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({"group":group["name"],"exit_code":result.returncode,"counts":counts,"wall_seconds":receipt["wall_seconds"]}),flush=True)
    if result.returncode or counts["skipped"] or counts["tests"]==0:sys.exit(result.returncode or 2)
