import sys
sys.dont_write_bytecode = True
"""Local exact Git archive producer. Does not change branches or remote resources."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
from hashlib import sha256
import argparse, json, subprocess, tarfile

from c3_retry_scope import RETRY_ROOT, validate_run_root
ROOT = RETRY_ROOT
E_REL = Path("docs/evidence/core-production-semantic-convergence-c3-20261009")
WATT_INPUTS = ("src", "tests", "migrations", "docker", "pyproject.toml", "uv.lock", "alembic.ini", "README.md",
    (E_REL/"Dockerfile.c3").as_posix(), (E_REL/"attest_c3_image.py").as_posix())

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root",default=str(RETRY_ROOT))
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--watt-revision",required=True)
    parser.add_argument("--guardian-revision",required=True)
    parser.add_argument("--control-revision")
    parser.add_argument("--build-attempt-id",type=int,default=1)
    args=parser.parse_args()
    global ROOT
    ROOT=validate_run_root(args.run_root)
    if not args.execute:
        print(json.dumps({"prepared_only":True,"run_root":str(ROOT),"local_archives_written":False,"remote_contact":False}));return
    repo=Path.cwd(); guardian=Path("D:/hy/c3-open-obligation-convergence/guardian")
    ecf=Path("D:/hy/engineering-context-fabric")
    assert args.build_attempt_id >= 1
    control_revision=args.control_revision or git(repo,"rev-parse","HEAD")
    output=repo/(".c3-development-inputs/retry-1/frozen-attempt-"+str(args.build_attempt_id)); assert not output.exists(); output.mkdir(parents=True)
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
    for path in sorted((repo/E_REL/"harness"/"retry1").glob("*.py")):
        relative=path.relative_to(repo).as_posix()
        body=subprocess.check_output(["git","-C",str(repo),"show",control_revision+":"+relative])
        assert body==path.read_bytes(),("uncommitted control harness",relative)
        controls[path.name]=sha256(body).hexdigest()
    result={"schema":"c3-frozen-inputs-v1","run_root":str(ROOT),"retry_identity":"retry-1","captured_at_utc":datetime.now(timezone.utc).isoformat(),
        "sources":sources,"archives":archives,"control_harness_sha256":controls,
        "watt_archive_scope":"Only explicit Docker COPY source/test/migration/metadata inputs; not full repository",
        "application_commit":args.watt_revision,"application_tree":sources["watt"]["tree"],
        "control_harness_revision":control_revision,"build_attempt_id":args.build_attempt_id,
        "external_control_harness_is_baked_application":False,
        "historical_canonical_main_revision":"ee5bd86a53891f9391785c91d0ccef81ad2d56c3",
        "external_checkout_head_is_canonical_main":False,
        "external_checkout_preparation_expectation":{"head":"5de657f3cb65780adf50f6557b54171a6c3cfae5",
            "branch":"codex/admin-work-ai-diagnostic-export-ecs","status_porcelain":"",
            "refs_heads_main":"ee5bd86a53891f9391785c91d0ccef81ad2d56c3"},
        "model_credential_scope":"HUMAN_AUTHORIZED_SHARED_TEST","actual_image_identity":"NOT_BUILT",
        "holdout_seal_sha256":"770828adeabec942548218c17bc6e9dbb9222ce19df19bc89c260f28ed8f4cf0"}
    payload=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    (output/"frozen-inputs.json").write_text(payload,encoding="utf-8")
    destination=repo/E_REL/"retry-1";destination.mkdir(exist_ok=True)
    manifest=destination/"frozen-inputs.json"
    assert not manifest.exists(),"Preserve prior retry freeze; use a separately approved attempt identity"
    manifest.write_text(payload,encoding="utf-8")
    print(json.dumps({"sources":sources,"archives":len(archives),"control_files":len(controls),"output":str(output)}))
if __name__=="__main__":main()
