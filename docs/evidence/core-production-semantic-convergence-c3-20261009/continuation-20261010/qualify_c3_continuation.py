"""C3 continuation exact image/regression control, never submits or resumes Work.

Local --prepare freezes exact Git archives. ECS --execute builds a new image
and runs installed-package, network-disabled deterministic regressions only.
No credentials, production resources, existing source/Work or model calls.
Host execution is compatible with Python 3.6.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json, os
from pathlib import Path
import subprocess, tarfile, time
import xml.etree.ElementTree as ET

ROOT=Path("/data/watt/c3-semantic-convergence-20261009")
TARGET=ROOT/"continuation-20261010/continuation-final-image"
REL="docs/evidence/core-production-semantic-convergence-c3-20261009"
BASE="sha256:6c1f48e35ec485de278e8638f51d6aed75679b02a24d45355959bc8ddd7c0d14"
DEPS_SHA="beefa9671df14d21f2763a4e85841962f10af824a37caf6c679555166b13b9a6"
WATT_INPUTS=("src","tests","migrations","docker","pyproject.toml","uv.lock","alembic.ini","README.md",REL+"/Dockerfile.c3",REL+"/attest_c3_image.py")

def now():
    return datetime.now(timezone.utc).isoformat()

def git(repo,*args):
    return subprocess.check_output(["git","-C",str(repo)]+list(args),universal_newlines=True).strip()

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def write(path,data):
    with path.open("x",encoding="utf-8") as stream:
        stream.write(json.dumps(data,indent=2)+"\n")

def prepare(args):
    repo=Path.cwd()
    assert git(repo,"rev-parse","--abbrev-ref","HEAD")=="codex/c3-open-semantic-obligation-convergence"
    revision=git(repo,"rev-parse",args.watt_revision+"^{commit}")
    assert args.watt_revision==revision
    assert not git(repo,"diff","--name-only",revision,"--",*WATT_INPUTS),"Uncommitted frozen inputs"
    other=set(git(repo,"ls-files","--others","--exclude-standard").splitlines())
    assert not any(n.startswith(("src/","tests/","migrations/","docker/")) for n in other)
    output=repo/".c3-development-inputs/continuation-final-image"
    assert not output.exists();output.mkdir()
    guardian=Path("D:/hy/c3-open-obligation-convergence/guardian")
    assert not git(guardian,"status","--porcelain")
    specs=(("watt",repo,revision,WATT_INPUTS),("guardian",guardian,"d01bac1ad153e1eadefafe87d2ea4f5d65896ab6",("src","tests")),
        ("ecf",Path("D:/hy/engineering-context-fabric"),"5aa4f8833c359c15bd059eda5972aa3915bcc18c",("src",)),
        ("ecf-unsupported",Path("D:/hy/engineering-context-fabric"),"c6b568d006022e39b95daebedfecfb55e562ebe5",("src",)))
    manifest={"schema":"c3-continuation-frozen-inputs-v1","run_root":TARGET.as_posix(),"captured_at_utc":now(),
        "sources":{},"archives":[],"controller_sha256":digest(Path(__file__)),
        "scope":"Bounded R1 target proof, R2 failure continuity, P0 safe metadata and R3 exact stop projection; not real G0 or Holdout",
        "controller_revision":git(repo,"rev-parse","HEAD"),"real_model_calls":0,"new_business_work":0}
    for owner,checkout,commit,paths in specs:
        assert git(checkout,"rev-parse",commit+"^{commit}")==commit
        file=output/(owner+"-"+commit[:7]+".tar")
        subprocess.check_call(["git","-C",str(checkout),"archive","--format=tar","--output",str(file),commit,"--"]+list(paths))
        with tarfile.open(str(file)) as archive:
            hashes={m.name:sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers() if m.isfile()}
            assert hashes and all(m.isdir() or m.isfile() for m in archive.getmembers())
        manifest["sources"][owner]={"revision":commit,"tree":git(checkout,"rev-parse",commit+"^{tree}")}
        manifest["archives"].append({"destination":owner,"file":file.name,"sha256":digest(file),"file_sha256":hashes})
    nodes=repo/REL/"continuation-20261010/final-image-test-nodes.json"
    manifest["test_nodes_sha256"]=digest(nodes)
    (output/"test-nodes.json").write_bytes(nodes.read_bytes())
    write(output/"frozen-inputs.json",manifest)
    print(json.dumps({"prepared":True,"directory":str(output),"sources":manifest["sources"],"controller_sha256":manifest["controller_sha256"]}))

def execute():
    for path in (ROOT,TARGET)+tuple(ROOT.parents):
        assert not path.is_symlink()
    assert TARGET.parent==ROOT/"continuation-20261010" and not TARGET.exists()
    inputs=ROOT/"continuation-final-inputs"
    freeze=json.loads((inputs/"frozen-inputs.json").read_text(encoding="utf-8"))
    assert freeze["run_root"]==str(TARGET) and freeze["controller_sha256"]==digest(Path(__file__))
    assert freeze["sources"]["guardian"]["revision"]=="d01bac1ad153e1eadefafe87d2ea4f5d65896ab6"
    TARGET.mkdir(mode=0o750)
    context=TARGET/"context";context.mkdir(mode=0o755)
    evidence=TARGET/"evidence";evidence.mkdir(mode=0o755);os.chown(str(evidence),10001,10001)
    private=TARGET/"private";private.mkdir(mode=0o700)
    write(evidence/"frozen-inputs.json",freeze)
    archives=list(freeze["archives"])+[{"destination":"test-deps","file":"c2-retained-test-deps.tar","sha256":DEPS_SHA}]
    archive_hashes={}
    for record in archives:
        source=inputs/record["file"]
        assert digest(source)==record["sha256"]
        archive_hashes[source.name]=record["sha256"]
        with tarfile.open(str(source)) as archive:
            members=archive.getmembers()
            if "file_sha256" in record:
                actual={m.name:sha256(archive.extractfile(m).read()).hexdigest() for m in members if m.isfile()}
                assert actual==record["file_sha256"]
            for member in members:
                path=Path(member.name)
                assert not path.is_absolute() and ".." not in path.parts and (member.isdir() or member.isfile())
                if record["destination"]=="guardian" and path.parts and path.parts[0]=="tests":
                    dest=TARGET/"guardian-tests"/path
                else:
                    if record["destination"] in ("guardian","ecf","ecf-unsupported") and (not path.parts or path.parts[0]!="src"):
                        continue
                    dest=context/record["destination"]/path
                if member.isdir():dest.mkdir(mode=0o755,parents=True,exist_ok=True)
                else:
                    dest.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
                    dest.write_bytes(archive.extractfile(member).read());os.chmod(str(dest),member.mode&0o777)
    base_tag="watt-c3-continuation-dependency-base:6c1f48e-20261009"
    assert subprocess.check_output(["docker","image","inspect","--format","{{.Id}}",BASE],universal_newlines=True).strip()==BASE
    subprocess.check_call(["docker","tag",BASE,base_tag])
    identity={"schema":"c3-source-identity-v1","sources":freeze["sources"],"base_image":{"reference":base_tag,"image_id":BASE},
        "build_input_sha256":{p.relative_to(context).as_posix():digest(p) for p in context.rglob("*") if p.is_file()},
        "archive_sha256":archive_hashes}
    write(context/"c3-source-identity.json",identity);write(evidence/"build-input-identity.json",identity)
    rev=freeze["sources"]["watt"]["revision"];tag="watt-c3-continuation:"+rev[:7]
    command=["docker","build","--network=none","--build-arg","BASE_IMAGE="+base_tag]
    for owner,prefix in (("watt","WATT"),("guardian","GUARDIAN"),("ecf","ECF")):
        for key in ("revision","tree"):command+=["--build-arg",prefix+"_"+key.upper()+"="+freeze["sources"][owner][key]]
    command+=["-f",str(context/"watt"/REL/"Dockerfile.c3"),"-t",tag,str(context)]
    start=time.monotonic();started=now()
    with (evidence/"build.log").open("x") as stream:
        result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
    build={"schema":"c3-exact-image-build-v1","started_at_utc":started,"ended_at_utc":now(),"wall_seconds":time.monotonic()-start,
        "exit_code":result.returncode,"sources":freeze["sources"],"command":command,"source_overlay":False,"real_model_calls":0,"scope":freeze["scope"]}
    if result.returncode==0:
        image=json.loads(subprocess.check_output(["docker","image","inspect",tag],universal_newlines=True))[0]
        build["image"]={key:image.get(key) for key in ("Id","RepoDigests","Created")}
        assert image["Config"]["Labels"]["org.opencontainers.image.revision"]==rev
    write(evidence/"build.json",build)
    assert result.returncode==0,"Exact build failed; no repeat build"
    image_id=image["Id"]
    image_env=dict(v.split("=",1) for v in image["Config"]["Env"] if "=" in v)
    assert image_env["PYTHONPATH"]=="/opt/c3-owners/guardian/src:/opt/c3-owners/ecf/src:/opt/c3-test-deps"
    assert not any(image_env.get(k) for k in ("SPG_DEEPSEEK_API_KEY","SPG_NATIVE_EXECUTOR_DEEPSEEK_API_KEY","OPENAI_API_KEY","ANTHROPIC_API_KEY"))
    common=["--network","none","--user","10001:10001","--cap-drop","ALL","--security-opt","no-new-privileges","--read-only",
        "--tmpfs","/tmp:rw,exec,nosuid,size=512m","--memory","1536m","--cpus","1","--label","watt.production=false",
        "--label","watt.qualification=C3-final-image-regression","--mount","type=bind,src="+str(evidence)+",dst=/c3-evidence"]
    name="watt-c3-continuation-imports-"+rev[:7]
    command=["docker","run","--name",name]+common+[image_id,"python","/opt/c3-build/attest_c3_image.py","--image-id",image_id,"--output","/c3-evidence/actual-imports.json"]
    with (evidence/"actual-imports.log").open("x") as stream:
        result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
    assert result.returncode==0
    att=json.loads((evidence/"actual-imports.json").read_text())
    assert att["status"]=="PASS" and att["caller_observed_image_id"]==image_id
    assert digest(inputs/"test-nodes.json")==freeze["test_nodes_sha256"]
    nodes=json.loads((inputs/"test-nodes.json").read_text(encoding="utf-8"))
    assert isinstance(nodes,list) and nodes and all(isinstance(n,str) and n.startswith("tests/") and ".." not in n for n in nodes)
    command=["python","-m","pytest","-p","no:cacheprovider","-o","junit_family=legacy"]+nodes+["-m","not real_container","--tb=short","--junitxml=/c3-evidence/watt-continuation.xml"]
    name="watt-c3-continuation-regression-"+rev[:7]
    started=now();start=time.monotonic()
    with (evidence/"watt-continuation.log").open("x") as stream:
        result=subprocess.run(["docker","run","--name",name]+common+["--workdir","/qualification",image_id]+command,stdout=stream,stderr=subprocess.STDOUT)
    counts={k:0 for k in ("tests","failures","errors","skipped")}
    xml=evidence/"watt-continuation.xml"
    if xml.is_file():
        for suite in ET.parse(xml).iter("testsuite"):
            for k in counts:counts[k]+=int(suite.get(k,"0"))
    counts["passed"]=counts["tests"]-sum(counts[k] for k in ("failures","errors","skipped"))
    actual=json.loads(subprocess.check_output(["docker","inspect",name],universal_newlines=True))[0]
    assert actual["Image"]==image_id and actual["Config"]["User"]=="10001:10001"
    assert actual["HostConfig"]["NetworkMode"]=="none"
    receipt={"schema":"c3-continuation-exact-image-regression-v1","started_at_utc":started,"ended_at_utc":now(),"wall_seconds":time.monotonic()-start,
        "sources":freeze["sources"],"image_id":image_id,"actual_container_id":actual["Id"],"command":command,"counts":counts,
        "exit_code":result.returncode,"source_overlay":False,"live_model_calls":0,"real_ai_work_created":0,"business_database_access":False,
        "proof_boundary":"Deterministic isolated regressions only; not real G0, Provider recovery, Guardian live Assurance, Holdout or Human Acceptance"}
    write(evidence/"watt-continuation-receipt.json",receipt)
    print(json.dumps({"build_image":image_id,"build_wall_seconds":build["wall_seconds"],"counts":counts,"exit_code":result.returncode}),flush=True)
    assert result.returncode==0 and counts["tests"]>0 and not counts["skipped"]

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--watt-revision")
    args=parser.parse_args()
    assert not (args.prepare and args.execute)
    if args.prepare:
        assert args.watt_revision;prepare(args)
    elif args.execute:execute()
    else:print(json.dumps({"static_plan":True,"run_root":TARGET.as_posix(),"network_contact":False,"model_calls":0,"work_created":False}))
