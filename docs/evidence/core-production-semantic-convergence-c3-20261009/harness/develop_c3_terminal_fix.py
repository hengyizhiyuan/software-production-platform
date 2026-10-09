"""Capture/run the C3 final failure-seam development tests, no live models or Work."""
import argparse, compileall
from datetime import datetime,timezone
from hashlib import sha256
import json, os
from pathlib import Path
import subprocess, tarfile, time, xml.etree.ElementTree as ET
REL=Path("docs/evidence/core-production-semantic-convergence-c3-20261009")
ROOT=Path("/data/watt/c3-semantic-convergence-20261009")
NAME="dev-terminal-fix-1"
IMAGE="sha256:6f8d9b3a27e7e2452097a77427115df6e09b9a03276eb72d0170a66160e0578f"
def now():return datetime.now(timezone.utc).isoformat()
def git(repo,*args):return subprocess.check_output(["git","-C",str(repo)]+list(args),universal_newlines=True).strip()
def write(path,value):
    with path.open("x",encoding="utf-8") as f:f.write(json.dumps(value,indent=2)+"\n")
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--prepare",action="store_true");parser.add_argument("--execute",action="store_true");args=parser.parse_args()
    assert not (args.prepare and args.execute)
    if args.prepare:
        repo=Path.cwd();dest=repo/".c3-development-inputs"/NAME;assert not dest.exists();dest.mkdir()
        paths=sorted(n for n in set(git(repo,"ls-files","--cached","--others","--exclude-standard").splitlines()) if n.startswith(("src/","tests/","migrations/")) or n in ("pyproject.toml","alembic.ini","uv.lock","README.md"))
        digests={};archive=dest/"watt.tar"
        with tarfile.open(str(archive),"w") as tar:
            for name in paths:
                source=repo/name;assert source.is_file() and not source.is_symlink()
                raw=source.read_bytes()
                if name.endswith(".py"):compile(raw.decode("utf-8"),name,"exec",dont_inherit=True)
                digests[name]=sha256(raw).hexdigest();tar.add(source,arcname=name,recursive=False)
        nodes=json.loads((repo/REL/"terminal-test-nodes.json").read_text(encoding="utf-8"))
        manifest={"schema":"c3-terminal-development-regression-v1","directory":NAME,"captured_at_utc":now(),
            "source_base_revision":git(repo,"rev-parse","HEAD"),"source_base_tree":git(repo,"rev-parse","HEAD^{tree}"),
            "archive_sha256":sha256(archive.read_bytes()).hexdigest(),"file_sha256":digests,"nodes":nodes,
            "harness_sha256":sha256(Path(__file__).read_bytes()).hexdigest(),"image_id":IMAGE,"source_overlay":True,
            "guardian_revision":"d01bac1ad153e1eadefafe87d2ea4f5d65896ab6","ecf_revision":"5aa4f8833c359c15bd059eda5972aa3915bcc18c",
            "live_model_calls":0,"real_ai_work_created":0}
        write(dest/"manifest.json",manifest);print(json.dumps({"prepared":True,"directory":str(dest),"files":len(paths),"nodes":nodes}))
    elif args.execute:
        inputs=ROOT/(NAME+"-inputs");manifest=json.loads((inputs/"manifest.json").read_text())
        assert manifest["harness_sha256"]==sha256(Path(__file__).read_bytes()).hexdigest()
        assert manifest["directory"]==NAME and manifest["image_id"]==IMAGE
        archive=inputs/"watt.tar";assert sha256(archive.read_bytes()).hexdigest()==manifest["archive_sha256"]
        dest=ROOT/NAME;assert not dest.exists();dest.mkdir(mode=0o755)
        with tarfile.open(str(archive)) as tar:
            members=tar.getmembers()
            assert {m.name:sha256(tar.extractfile(m).read()).hexdigest() for m in members if m.isfile()}==manifest["file_sha256"]
            for m in members:
                path=Path(m.name);assert m.isfile() and not path.is_absolute() and ".." not in path.parts
                target=dest/path;target.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
                target.write_bytes(tar.extractfile(m).read());os.chmod(str(target),0o644)
        out=ROOT/"evidence"/NAME;assert not out.exists();out.mkdir(mode=0o755);os.chown(str(out),10001,10001)
        write(out/"development-inputs.json",manifest)
        command=["python","-m","pytest","-p","no:cacheprovider"]+manifest["nodes"]+["--tb=short","--junitxml=/c3-evidence/watt.xml"]
        name="watt-c3-dev-terminal-fix-20261009"
        args=["docker","run","--name",name,"--network","none","--user","10001:10001","--cap-drop","ALL","--security-opt","no-new-privileges",
            "--read-only","--tmpfs","/tmp:rw,exec,nosuid,size=512m","--memory","1536m","--cpus","1","--label","watt.production=false",
            "--label","watt.qualification=C3-development","--env","PYTHONPATH=/qualification/src:/qualification:/opt/c3-owners/guardian/src:/opt/c3-owners/ecf/src:/opt/c3-test-deps",
            "--mount","type=bind,src="+str(dest)+",dst=/qualification,readonly","--mount","type=bind,src="+str(out)+",dst=/c3-evidence",
            "--workdir","/qualification",IMAGE]+command
        start=time.monotonic();started=now()
        with (out/"watt.log").open("x") as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
        counts={k:0 for k in ("tests","failures","errors","skipped")}
        if (out/"watt.xml").is_file():
            for suite in ET.parse(out/"watt.xml").iter("testsuite"):
                for k in counts:counts[k]+=int(suite.get(k,"0"))
        counts["passed"]=counts["tests"]-sum(counts[k] for k in ("failures","errors","skipped"))
        receipt={**manifest,"started_at_utc":started,"ended_at_utc":now(),"wall_seconds":time.monotonic()-start,"counts":counts,"exit_code":r.returncode,
            "database_access":False,"qualification_scope":"Controlled typed failure/current stop regression; not Provider recovery or actual Work"}
        write(out/"watt-receipt.json",receipt)
        print(json.dumps({"counts":counts,"exit_code":r.returncode,"wall_seconds":receipt["wall_seconds"]}),flush=True)
        raise SystemExit(r.returncode or int(bool(counts["skipped"] or not counts["tests"])))
    else:print(json.dumps({"plan_only":True,"network_contact":False,"model_calls":0,"work_created":False}))
if __name__=="__main__":main()
