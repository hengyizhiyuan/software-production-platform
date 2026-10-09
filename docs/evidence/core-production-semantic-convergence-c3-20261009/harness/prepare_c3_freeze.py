"""Local exact Git archive producer. Does not change branches or remote resources."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from hashlib import sha256
import argparse, json, subprocess, tarfile

ROOT = PurePosixPath("/data/watt/c3-semantic-convergence-20261009")
E_REL = Path("docs/evidence/core-production-semantic-convergence-c3-20261009")
WATT_INPUTS = ("src", "tests", "migrations", "docker", "pyproject.toml", "uv.lock", "alembic.ini", "README.md",
    (E_REL/"Dockerfile.c3").as_posix(), (E_REL/"attest_c3_image.py").as_posix())

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watt-revision",required=True)
    parser.add_argument("--guardian-revision",required=True)
    parser.add_argument("--control-revision")
    parser.add_argument("--build-attempt-id",type=int,default=1)
    args=parser.parse_args()
    repo=Path.cwd(); guardian=Path("D:/hy/c3-open-obligation-convergence/guardian")
    ecf=Path("D:/hy/engineering-context-fabric")
    assert args.build_attempt_id >= 1
    control_revision=args.control_revision or git(repo,"rev-parse","HEAD")
    output=repo/(".c3-development-inputs/frozen-attempt-"+str(args.build_attempt_id)); assert not output.exists(); output.mkdir()
    source_specs=(("watt",repo,args.watt_revision,WATT_INPUTS),
        ("guardian",guardian,args.guardian_revision,("src","tests")),
        ("ecf",ecf,"5aa4f8833c359c15bd059eda5972aa3915bcc18c",("src",)),
        ("ecf-unsupported",ecf,"c6b568d006022e39b95daebedfecfb55e562ebe5",("src",)))
    sources={};archives=[]
    for owner, checkout, revision, paths in source_specs:
        commit=git(checkout,"rev-parse",revision+"^{commit}")
        assert commit==revision
        tree=git(checkout,"rev-parse",revision+"^{tree}")
        if owner=="guardian": assert git(checkout,"rev-parse","HEAD")==commit
        if owner=="watt": assert not git(checkout,"diff","--name-only",commit,"HEAD","--",*WATT_INPUTS), "Baked application inputs changed after code freeze"
        if owner=="guardian": assert not git(checkout,"status","--porcelain")
        name=owner+"-"+commit[:7]+"-frozen.tar";path=output/name
        subprocess.check_call(["git","-C",str(checkout),"archive","--format=tar","--output",str(path),commit,"--",*paths])
        with tarfile.open(path) as tar:
            inventory={member.name:sha256(tar.extractfile(member).read()).hexdigest() for member in tar.getmembers() if member.isfile()}
            assert inventory and all(member.isdir() or member.isfile() for member in tar.getmembers())
        sources[owner]={"revision":commit,"tree":tree}
        archives.append({"path":str(ROOT/"input-archives"/name),"destination":owner,
            "sha256":sha256(path.read_bytes()).hexdigest(),"git_archive_paths":list(paths),"file_sha256":inventory})
    archives.append({"path":str(ROOT/"input-archives/c2-retained-test-deps.tar"),"destination":"test-deps",
        "sha256":"beefa9671df14d21f2763a4e85841962f10af824a37caf6c679555166b13b9a6",
        "origin":"retained C2 build dependencies; not C2 source or C3 qualification"})
    # These host/control files are separate from the baked application. Their
    # committed blob hashes must match the files actually placed under ROOT.
    controls={}
    active={"prepare_c3_freeze.py", "build_c3_image.py", "launch_c3_runtime.py",
        "run_final_image_regression.py", "run_c3_normal_entry.py", "c3_normal_entry.py",
        "worker_root_probe.py", "scan_public_evidence.py"}
    for path in sorted((repo/E_REL/"harness").glob("*.py")):
        if path.name not in active and not path.name.startswith(("c3_export", "freeze_c3", "capture_c3", "persist_c3", "quiesce_c3", "export_c3", "verify_c3")):
            continue
        relative=path.relative_to(repo).as_posix()
        body=subprocess.check_output(["git","-C",str(repo),"show",control_revision+":"+relative])
        assert body==path.read_bytes(),("uncommitted control harness",relative)
        controls[path.name]=sha256(body).hexdigest()
    result={"schema":"c3-frozen-inputs-v1","captured_at_utc":datetime.now(timezone.utc).isoformat(),
        "sources":sources,"archives":archives,"control_harness_sha256":controls,
        "watt_archive_scope":"Only explicit Docker COPY source/test/migration/metadata inputs; not full repository",
        "application_commit":args.watt_revision,"application_tree":sources["watt"]["tree"],
        "control_harness_revision":control_revision,"build_attempt_id":args.build_attempt_id,
        "external_control_harness_is_baked_application":False,
        "canonical_ecs_main_preserved":"ee5bd86a53891f9391785c91d0ccef81ad2d56c3",
        "model_credential_scope":"HUMAN_AUTHORIZED_SHARED_TEST","actual_image_identity":"NOT_BUILT",
        "holdout_seal_sha256":"770828adeabec942548218c17bc6e9dbb9222ce19df19bc89c260f28ed8f4cf0"}
    payload=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    (output/"frozen-inputs.json").write_text(payload,encoding="utf-8")
    (repo/E_REL/"frozen-inputs.json").write_text(payload,encoding="utf-8")
    print(json.dumps({"sources":sources,"archives":len(archives),"control_files":len(controls),"output":str(output)}))
if __name__=="__main__":main()
