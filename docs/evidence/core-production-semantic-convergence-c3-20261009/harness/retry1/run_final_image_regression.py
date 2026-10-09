import sys
sys.dont_write_bytecode = True
from c3_retry_scope import scoped_runtime_root, verify_frozen_controls, read_built_identity, FIXTURE_PG
"""Prepared only: qualify installed packages in the new exact C3 image."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID
import json, os, subprocess, tarfile, time, sys, xml.etree.ElementTree as ET
ROOT=scoped_runtime_root("final-image-regression");P=ROOT/"private";E=ROOT/"evidence"
freeze=verify_frozen_controls(ROOT)
build=read_built_identity(ROOT,freeze)
IMAGE=build["image"]["Id"]
data=json.loads(subprocess.check_output(["docker","image","inspect",IMAGE],universal_newlines=True))[0]
assert data["Id"]==IMAGE and data["Config"]["Labels"]["org.opencontainers.image.revision"]==build["sources"]["watt"]["revision"]
image_env=dict(value.split("=",1) for value in data["Config"]["Env"] if "=" in value)
assert image_env["PYTHONPATH"]=="/opt/c3-owners/guardian/src:/opt/c3-owners/ecf/src:/opt/c3-test-deps"
assert not any(image_env.get(key) for key in ("SPG_DEEPSEEK_API_KEY","SPG_NATIVE_EXECUTOR_DEEPSEEK_API_KEY","OPENAI_API_KEY","ANTHROPIC_API_KEY")), "Test image must not carry model credential defaults"
# Root prepares Guardian tests from the immutable freeze Git archive; this
# path carries tests only and never src. Import search extends tests only.
revision=build["sources"]["watt"]["revision"]
build_directory=Path(build["build_directory"])
assert build_directory.parent==ROOT and build_directory.name.startswith("build-"+revision[:7])
guardian_tests=build_directory/"test-inputs"/"guardian"
assert guardian_tests.is_dir() and (guardian_tests/"tests").is_dir()
assert not (guardian_tests/"src").exists(), "Guardian input must contain tests only"
guardian_test_hashes={path.relative_to(guardian_tests).as_posix():sha256(path.read_bytes()).hexdigest()
    for path in sorted(guardian_tests.rglob("*.py"))}
expected_guardian_tests={name: value for archive in freeze["archives"] if archive["destination"]=="guardian"
    for name,value in archive["file_sha256"].items() if name.startswith("tests/") and name.endswith(".py")}
assert guardian_test_hashes and guardian_test_hashes==expected_guardian_tests, "Frozen Guardian tests drift"
out=E/"final-image-regression";assert not out.exists();out.mkdir(mode=0o755);os.chown(str(out),10001,10001)
creds=json.loads((P/"credentials.json").read_text());envfile=P/"final-image-regression.env"
url="postgresql+psycopg://c3_app:"+creds["regression_postgres_password"]+"@127.0.0.1:5432/c1_contract_continuity"
with envfile.open("x") as stream:
    os.fchmod(stream.fileno(),0o600)
    stream.write("SPG_TEST_DATABASE_URL="+url+"\nSPG_DATABASE_URL="+url+"\n")
    stream.write("SPG_TEST_POSTGRES_DSN=postgresql://c3_app:"+creds["regression_postgres_password"]+"@127.0.0.1:5432/c1_contract_continuity\n")
# No model key enters this environment. The DB is the dedicated fixture database.
prep=json.loads((E/"isolation-preparation.json").read_text())
fixture=json.loads(subprocess.check_output(["docker","inspect",FIXTURE_PG],universal_newlines=True))[0]
assert fixture["Id"]==prep["fixture_postgres_container_id"] and fixture["Image"]==prep["fixture_postgres_image_id"]
assert fixture["State"]["Running"] is True and not fixture["HostConfig"]["PortBindings"]
common=["--network","container:"+FIXTURE_PG,"--user","10001:10001","--cap-drop","ALL",
    "--security-opt","no-new-privileges","--read-only","--tmpfs","/tmp:rw,exec,nosuid,size=512m",
    "--memory","1536m","--cpus","1","--label","watt.production=false","--label","watt.qualification=C3-retry1-final-image-regression",
    "--env-file",str(envfile),"--mount","type=bind,src="+str(out)+",dst=/c3-evidence"]
def sanitize(text):
    for value in creds.values():
        if isinstance(value,str) and value:text=text.replace(value,"[REDACTED]")
    return text
# Observe installed imports before tests. No source, package or PYTHONPATH overlays.
attest_name="watt-c3-retry1-final-imports-20261009"
command=["python","/opt/c3-build/attest_c3_image.py","--image-id",IMAGE,"--output","/c3-evidence/actual-imports.json"]
raw=P/(attest_name+".raw.log")
with raw.open("x") as stream:
    os.fchmod(stream.fileno(),0o600)
    result=subprocess.run(["docker","run","--name",attest_name]+common+[IMAGE]+command,stdout=stream,stderr=subprocess.STDOUT)
(out/"actual-imports.log").write_text(sanitize(raw.read_text(errors="replace")))
assert result.returncode==0,"Actual installed import attestation failed"
attestation=json.loads((out/"actual-imports.json").read_text());assert attestation["status"]=="PASS" and attestation["scope"]=="actual-installed-imports"
assert attestation["caller_observed_image_id"]==IMAGE
unit=["tests/test_guardian_assurance_adapter.py","tests/test_c3_admitted_source_facets.py","tests/test_fulfillment_projection.py","tests/test_c3_fulfillment_components.py","tests/test_c3_evidence_projection.py","tests/test_c3_verification_receipts.py",
    "tests/test_static_protected_context_verifier.py","tests/test_n1_static_html_semantics.py","tests/test_governed_obligation_fulfillment.py",
    "tests/test_container_production_environment_provider.py","tests/test_c2_workspace_preflight.py","-m","not real_container"]
groups=[{"name":"watt-unit","nodes":unit},
    {"name":"guardian-unit","owner":"guardian","nodes":["tests/test_c3_phase_evidence.py","tests/test_c1_governed_evidence_continuity.py",
        "tests/test_governed_obligation_evidence.py","tests/test_software_assurance.py"]},
    {"name":"c1-chain","nodes":["tests/integration/test_c1_contract_continuity.py"]},
    {"name":"c3-carrier","nodes":["tests/integration/test_c3_fulfillment_receipts.py"]},
    {"name":"c2-pg-preflight","nodes":["tests/integration/test_c2_workspace_preflight_events.py"]}]
for group in groups:
    name="watt-c3-retry1-final-"+group["name"]+"-20261009"
    fixture_tmp=P/(name+"-fixture-tmp")
    assert not fixture_tmp.exists(), "Never reuse fixture temporary evidence"
    fixture_tmp.mkdir(mode=0o700);os.chown(str(fixture_tmp),10001,10001)
    command=["python","-m","pytest","--basetemp=/c3-private-fixture/tests","-p","no:cacheprovider","-o","junit_family=legacy"]+group["nodes"]+["--tb=short","--junitxml=/c3-evidence/"+group["name"]+".xml"]
    mount=["--mount","type=bind,src="+str(fixture_tmp)+",dst=/c3-private-fixture"]
    if group.get("owner")=="guardian":mount += ["--mount","type=bind,src="+str(guardian_tests)+",dst=/guardian-tests,readonly",
        "--env","PYTHONPATH="+image_env["PYTHONPATH"]+":/guardian-tests"]
    args=["docker","run","--name",name]+common+mount+["--workdir","/guardian-tests" if group.get("owner")=="guardian" else "/qualification",IMAGE]+command
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
    receipt={"schema":"c3-final-image-regression-v1","sources":build["sources"],"image_id":IMAGE,
        "source_overlay":False,"pythonpath":image_env["PYTHONPATH"]+":/guardian-tests" if group.get("owner")=="guardian" else image_env["PYTHONPATH"],"actual_imports_attestation":"actual-imports.json",
        "guardian_test_input_path":str(guardian_tests),"guardian_test_file_sha256":guardian_test_hashes,"command":command,"container_name":name,
        "started_at_utc":started,"ended_at_utc":datetime.now(timezone.utc).isoformat(),"wall_seconds":time.monotonic()-start,
        "exit_code":result.returncode,"counts":counts,"database_name":"c1_contract_continuity","database_server":FIXTURE_PG,
        "database_configuration_key":"SPG_TEST_DATABASE_URL","log_and_xml_sanitized":True,
        "live_model_calls":0,"real_ai_work_created":0,"fixture_work_mutations_only":True,
        "meaning":"exact baked-image regression; not a live AI Work qualification"}
    owner_files={}
    # Only exact Guardian Owner result/request files produced by this test group.
    # Private basetemp persists across container exit; no whole-/tmp extraction.
    for file in fixture_tmp.rglob("guardian/results/*.json"):
        assert file.is_file() and not file.is_symlink()
        assert file.stat().st_size <= 4*1024*1024, "Owner result exceeds scoped export bound"
        result_payload=json.loads(file.read_text())
        request_id=str(UUID(result_payload["request_id"]))
        request=file.parent.parent/"requests"/(request_id+".json")
        assert request.is_file() and not request.is_symlink()
        assert request.stat().st_size <= 4*1024*1024, "Owner request exceeds scoped export bound"
        request_payload=json.loads(request.read_text())
        assert request_payload["request_id"]==request_id
        assert result_payload["contract_version"]==request_payload["contract_version"]=="watt-guardian-software-assurance-v1"
        # Independent pytest fixtures may intentionally reuse request IDs in
        # separate Owner stores; preserve each actual file instead of merging.
        file_key=file.relative_to(fixture_tmp).as_posix()
        assert file_key not in owner_files
        owner_files[file_key]={"request_id":request_id,"actual_result":result_payload,"actual_request":request_payload,
            "private_result_path":str(file),"private_request_path":str(request)}
    if owner_files:
        target=out/(group["name"]+"-guardian-owner-records.json")
        target.write_text(sanitize(json.dumps({"schema":"c3-scoped-final-image-guardian-fixture-owner-records-v1",
            "sources":build["sources"],"image_id":IMAGE,"actual_imports_attestation":"actual-imports.json",
            "container":name,"observed_at_utc":datetime.now(timezone.utc).isoformat(),
            "scope":"exact Guardian request/result files produced by this fixture group only",
            "fixture_only":True,"records":owner_files},indent=2))+"\n")
        receipt["guardian_owner_records"]=target.name
    receipt["private_fixture_basetemp_persisted"]=str(fixture_tmp)
    receipt["harness_sha256"]=sha256(Path(__file__).read_bytes()).hexdigest()
    (out/(group["name"]+"-receipt.json")).write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({"group":group["name"],"exit_code":result.returncode,"counts":counts,"wall_seconds":receipt["wall_seconds"]}),flush=True)
    if result.returncode or counts["skipped"] or counts["tests"]==0:sys.exit(result.returncode or 2)
