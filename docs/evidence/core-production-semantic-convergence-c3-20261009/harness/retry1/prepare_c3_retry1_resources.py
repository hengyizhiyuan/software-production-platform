import sys
sys.dont_write_bytecode = True
"""Explicitly prepare ONLY retry-1 resources; default prints a plan, no contact.

Shared PG/Gitea/networks are verified then reused, never created/restarted/reset.
Operator/internal tokens are new. Provider and PG values stay in private files.
"""
from pathlib import Path
from datetime import datetime, timezone
import json, os, secrets, socket, subprocess
from c3_retry_scope import (scoped_runtime_root, ORIGINAL_ROOT, DATABASE,
    REGRESSION_DATABASE, FIXTURE_PG, NAMES, PG, GITEA, CONTROL_NETWORK, EXECUTOR_NETWORK,
    VOLUME, QUALIFICATION, PORT, verify_frozen_controls)
ROOT=scoped_runtime_root("prepare-retry1-resources")
freeze=verify_frozen_controls(ROOT)
OLD=Path(str(ORIGINAL_ROOT));P=ROOT/"private";E=ROOT/"evidence"
assert OLD.is_dir() and not OLD.is_symlink()
assert ROOT.parent == OLD
for name in ("private", "evidence", "app", "receipts", "regression-postgres"):
    assert not (ROOT/name).exists(), ("preserve existing retry resource",name)
assert ROOT.is_dir() and not ROOT.is_symlink(), "Upload frozen controls before resource preparation"
# ROOT may already contain only explicitly uploaded controls and frozen archives.
allowed={"input-archives", "frozen-inputs.json"} | {p.name for p in Path(__file__).parent.glob("*.py")}
assert all(p.name in allowed and not p.is_symlink() for p in ROOT.iterdir()), "Unexpected retry root contents"

def invoke(args):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    if result.returncode: raise RuntimeError("RETRY1_CONTROL_ACTION_FAILED")
    return result.stdout.strip()

def exists(kind,name):
    return subprocess.run(["docker",kind,"inspect",name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0

def inspect_container(name):
    data=json.loads(invoke(["docker","inspect",name]))[0]
    labels=data.get("Config",{}).get("Labels") or {}
    assert labels.get("watt.production")=="false" and labels.get("watt.qualification")=="C3-semantic-convergence"
    assert data["State"]["Running"] is True
    return {"name":name,"container_id":data["Id"],"image_id":data["Image"],"running":True}

# Preserve legitimate work in a different checkout; never switch/reset/write it.
EXPECTED_EXTERNAL_HEAD="5de657f3cb65780adf50f6557b54171a6c3cfae5"
EXPECTED_EXTERNAL_BRANCH="codex/admin-work-ai-diagnostic-export-ecs"
CANONICAL_MAIN="ee5bd86a53891f9391785c91d0ccef81ad2d56c3"
def external_checkout_observation():
    prefix=["git","--no-optional-locks","-C","/data/watt/runtime/source"]
    observed={"head":invoke(prefix+["rev-parse","HEAD"]),
        "branch":invoke(prefix+["symbolic-ref","--short","HEAD"]),
        "status_porcelain":invoke(prefix+["status","--porcelain"]),
        "canonical_main_ref":invoke(prefix+["rev-parse","refs/heads/main"])}
    assert observed=={"head":EXPECTED_EXTERNAL_HEAD,"branch":EXPECTED_EXTERNAL_BRANCH,
        "status_porcelain":"","canonical_main_ref":CANONICAL_MAIN}, "External checkout observation changed; do not overwrite"
    return observed
external_pre=external_checkout_observation()
shared=[inspect_container(PG),inspect_container(GITEA)]
for name in (CONTROL_NETWORK,EXECUTOR_NETWORK):
    net=json.loads(invoke(["docker","network","inspect",name]))[0]
    assert net["Labels"].get("watt.production")=="false" and net["Labels"].get("watt.qualification")=="C3-semantic-convergence"
    assert name != EXECUTOR_NETWORK or net["Internal"] is True, "Executor network isolation required"
    shared.append({"name":name,"network_id":net["Id"],"internal":net["Internal"]})
for name in list(NAMES.values())+[FIXTURE_PG,"watt-c3-retry1-migration-20261009","watt-c3-retry1-normal-entry-validated-20261009"]:
    assert not exists("container",name),("preserve existing retry role",name)
assert not exists("volume",VOLUME),"Preserve existing retry volume"
with socket.socket() as probe: probe.bind(("127.0.0.1",PORT))
# Actual secrets are read from already approved C3 private files only.
credential_file=OLD/"private"/"credentials.json"
assert credential_file.is_file() and not credential_file.is_symlink() and credential_file.stat().st_mode & 0o077 == 0
assert (OLD/"private").is_dir() and not (OLD/"private").is_symlink()
source=json.loads(credential_file.read_text())
assert all(isinstance(source.get(key),str) and source[key] for key in ("postgres_password","gitea_user","gitea_password"))
provider_env=OLD/"private"/"watt-c3-api-20261009.env"
assert provider_env.is_file() and not provider_env.is_symlink() and provider_env.stat().st_mode & 0o077 == 0
values={line.split("=",1)[0]:line.split("=",1)[1] for line in provider_env.read_text().splitlines() if "=" in line}
provider_key=values.get("SPG_DEEPSEEK_API_KEY") or values.get("SPG_NATIVE_EXECUTOR_DEEPSEEK_API_KEY")
provider_base=values.get("SPG_DEEPSEEK_BASE_URL") or values.get("SPG_NATIVE_EXECUTOR_DEEPSEEK_BASE_URL")
assert provider_key and provider_base=="https://api.deepseek.com"
for db in (DATABASE,):
    observed=invoke(["docker","exec",PG,"psql","-U","c3_app","-d","postgres","-Atc",
        "SELECT datname FROM pg_database WHERE datname='"+db+"'"])
    assert not observed,("preserve existing database",db)
input_source=OLD/"evidence"/"original-g0-input.json"
assert input_source.is_file() and not input_source.is_symlink()
input_raw=input_source.read_bytes();input_payload=json.loads(input_raw)
assert input_payload.get("schema")=="c2-original-g0-input-v1"
P.mkdir(mode=0o700);E.mkdir(mode=0o755);os.chown(str(E),10001,10001)
with (E/"original-g0-input.json").open("xb") as stream:stream.write(input_raw)
os.chmod(str(E/"original-g0-input.json"),0o644)
credentials={"postgres_password":source["postgres_password"],"gitea_user":source["gitea_user"],
    "gitea_password":source["gitea_password"],"operator_token":secrets.token_urlsafe(36),
    "tool_host_token":secrets.token_urlsafe(36),"regression_postgres_password":secrets.token_urlsafe(36)}
def private_file(name,body):
    with (P/name).open("x") as stream: os.fchmod(stream.fileno(),0o600);stream.write(body)
private_file("credentials.json",json.dumps(credentials,indent=2)+"\n")
private_file("provider.env","SPG_DEEPSEEK_API_KEY="+provider_key+"\nSPG_DEEPSEEK_BASE_URL="+provider_base+"\n")
for db in (DATABASE,):
    invoke(["docker","exec",PG,"psql","-U","c3_app","-d","postgres","-v","ON_ERROR_STOP=1","-c","CREATE DATABASE "+db+" OWNER c3_app"])
# A separate fixture PostgreSQL server preserves the historical C1 database.
PG_IMAGE="sha256:d741b376874687de90374fd34f55c6b2760e8f7bd7e4ae5cd47f50757fc08cf8"
assert invoke(["docker","image","inspect","--format","{{.Id}}",PG_IMAGE])==PG_IMAGE
private_file("regression-postgres.env","POSTGRES_USER=c3_app\nPOSTGRES_PASSWORD="+credentials["regression_postgres_password"]+"\nPOSTGRES_DB="+REGRESSION_DATABASE+"\n")
pgroot=ROOT/"regression-postgres";pgroot.mkdir(mode=0o700)
fixture_id=invoke(["docker","run","-d","--name",FIXTURE_PG,"--network",CONTROL_NETWORK,
    "--memory","512m","--cpus","0.5","--pids-limit","256","--label","watt.production=false",
    "--label","watt.qualification="+QUALIFICATION,"--env-file",str(P/"regression-postgres.env"),
    "--mount","type=bind,src="+str(pgroot)+",dst=/var/lib/postgresql/data",PG_IMAGE])
fixture=json.loads(invoke(["docker","inspect",FIXTURE_PG]))[0]
assert fixture["Id"]==fixture_id and fixture["Image"]==PG_IMAGE and not fixture["HostConfig"]["PortBindings"]
for name in ("app","receipts"):
    path=ROOT/name;path.mkdir(mode=0o750);os.chown(str(path),10001,10001)
for name in ("managed-source","native-executor","owner-runtime","production-environments","native-tool-receipts","native-workspaces"):
    path=ROOT/"app"/name;path.mkdir(mode=0o750);os.chown(str(path),10001,10001)
labels=["--label","watt.production=false","--label","watt.qualification="+QUALIFICATION]
invoke(["docker","volume","create"]+labels+[VOLUME])
volume=json.loads(invoke(["docker","volume","inspect",VOLUME]))[0]
assert volume["Name"]==VOLUME and volume["Labels"].get("watt.qualification")==QUALIFICATION
mountpoint=Path(volume["Mountpoint"])
assert str(mountpoint).endswith("/volumes/"+VOLUME+"/_data") and not mountpoint.is_symlink() and not list(mountpoint.iterdir())
os.chown(str(mountpoint),10001,10001);os.chmod(str(mountpoint),0o755)
from hashlib import sha256
external_post=external_checkout_observation()
assert external_pre==external_post
receipt={"schema":"c3-retry1-isolated-preparation-v1","captured_at_utc":datetime.now(timezone.utc).isoformat(),
    "qualification_root":str(ROOT),"preserved_original_root":str(OLD),"shared_dependencies":shared,
    "new_database":DATABASE,"new_regression_database":REGRESSION_DATABASE,"fixture_postgres_container_id":fixture_id,
    "fixture_postgres_name":FIXTURE_PG,"fixture_postgres_image_id":PG_IMAGE,"fixture_postgres_published_ports":False,"workspace_volume":VOLUME,
    "role_names":NAMES,"api_loopback_port":PORT,"new_operator_and_tool_host_tokens":True,
    "provider_credential_scope":"HUMAN_AUTHORIZED_SHARED_TEST","credential_values_released":False,
    "canonical_main_ref_revision":CANONICAL_MAIN,"external_checkout_before":external_pre,
    "external_checkout_after":external_post,"external_checkout_change_origin":"UNKNOWN",
    "external_checkout_written_or_switched":False,"original_g0_input_sha256":sha256(input_raw).hexdigest(),
    "existing_services_restarted_reset_or_recreated":False,"old_business_databases_mutated":False,
    "shared_postgres_cluster_new_database_created":True,"application_roles_created":False,
    "work_created":0,"model_calls":0,"partial_preparation_requires_read_only_reconciliation":True}
with (E/"isolation-preparation.json").open("x") as stream: json.dump(receipt,stream,indent=2);stream.write("\n")
print(json.dumps({"new_root":str(ROOT),"new_main_database":DATABASE,"fixture_server":FIXTURE_PG,"fixture_database":REGRESSION_DATABASE,"new_volume":VOLUME,
    "old_business_databases_modified":False,"existing_services_restarted_or_reset":False,"provider_key_printed":False,"model_calls":0,"work_created":0}))
