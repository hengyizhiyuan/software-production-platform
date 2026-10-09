import sys
sys.dont_write_bytecode = True
"""Retry control identity only. Importing does not contact Docker, DB or models."""
import argparse, json, sys
from pathlib import Path, PurePosixPath
ORIGINAL_ROOT = PurePosixPath("/data/watt/c3-semantic-convergence-20261009")
RETRY_ROOT = ORIGINAL_ROOT / "retry-1"
DATABASE = "spg_c3_retry1_qualification_20261009"
REGRESSION_DATABASE = "c1_contract_continuity"
FIXTURE_PG = "watt-c3-retry1-fixture-postgres-20261009"
NAMES = {role: "watt-c3-retry1-"+role+"-20261009" for role in ("api", "coordinator", "worker", "tool-host")}
CONTROL_NETWORK = "watt-c3-control-20261009"
EXECUTOR_NETWORK = "watt-c3-executor-20261009"
PG = "watt-c3-postgres-20261009"
GITEA = "watt-c3-gitea-20261009"
VOLUME = "watt-c3-retry1-workspaces-20261009"
QUALIFICATION = "C3-semantic-convergence-retry1"
PORT = 18301

def validate_run_root(value):
    # Strict literal identity; reject //, dot components, escapes and Windows paths.
    if str(value) not in (str(ORIGINAL_ROOT), str(RETRY_ROOT)):
        raise ValueError("RUN_ROOT_OUTSIDE_APPROVED_C3_SCOPE")
    if str(value) != str(RETRY_ROOT):
        raise ValueError("RETRY_CONTROL_CANNOT_OPERATE_ORIGINAL_ROOT")
    return PurePosixPath(str(value))

def scoped_runtime_root(action, execute_flag="--execute"):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--run-root", default=str(RETRY_ROOT))
    args, remainder = parser.parse_known_args()
    root = validate_run_root(args.run_root)
    # Let existing export/driver parsers handle their own options.
    sys.argv = [sys.argv[0]] + remainder
    if execute_flag not in remainder:
        print(json.dumps({"schema":"c3-retry1-control-plan-v1", "action": action,
            "run_root":str(root), "database":DATABASE, "roles":NAMES,
            "volume":VOLUME, "port":PORT, "execute_required":execute_flag,
            "remote_contact":False, "work_created":False, "model_calls":0}))
        raise SystemExit(0)
    if execute_flag == "--execute":
        sys.argv.remove(execute_flag)
    path = Path(str(root))
    # A symlink in any root component could redirect writes into preserved data.
    for component in (path,) + tuple(path.parents):
        if component.is_symlink():
            raise ValueError("SYMLINK_RUN_ROOT_REJECTED")
    return path


def verify_frozen_controls(root):
    from hashlib import sha256
    import re
    freeze = json.loads((root/"frozen-inputs.json").read_text())
    assert freeze.get("run_root")==str(root) and freeze.get("retry_identity")=="retry-1"
    assert freeze.get("schema")=="c3-frozen-inputs-v1"
    assert freeze["application_commit"]==freeze["sources"]["watt"]["revision"]
    for owner in ("watt","guardian","ecf","ecf-unsupported"):
        assert re.fullmatch(r"[0-9a-f]{40}",freeze["sources"][owner]["revision"])
        assert re.fullmatch(r"[0-9a-f]{40}",freeze["sources"][owner]["tree"])
    assert freeze["sources"]["ecf"]["revision"]=="5aa4f8833c359c15bd059eda5972aa3915bcc18c"
    for name, expected in freeze["control_harness_sha256"].items():
        assert Path(name).name==name and not (root/name).is_symlink()
        assert sha256((root/name).read_bytes()).hexdigest()==expected, ("control identity mismatch",name)
    expected_controls={"c3_retry_scope.py","prepare_c3_retry1_resources.py","prepare_c3_freeze.py",
        "build_c3_image.py","launch_c3_runtime.py","run_final_image_regression.py",
        "run_c3_normal_entry.py","c3_normal_entry.py","c3_export_owner_records.py",
        "c3_export_work_snapshot.py","worker_root_probe.py","scan_public_evidence.py"}
    assert set(freeze["control_harness_sha256"])==expected_controls, "Missing or unexpected retry control"
    for archive in freeze["archives"]:
        path=PurePosixPath(archive["path"])
        assert str(path.parent)==str(root/"input-archives") and not Path(str(path)).is_symlink()
    watt_paths={"src","tests","migrations","docker","pyproject.toml","uv.lock","alembic.ini","README.md",
        "docs/evidence/core-production-semantic-convergence-c3-20261009/Dockerfile.c3",
        "docs/evidence/core-production-semantic-convergence-c3-20261009/attest_c3_image.py"}
    records={entry["destination"]:entry for entry in freeze["archives"]}
    assert len(records)==len(freeze["archives"])==5
    assert set(records)=={"watt","guardian","ecf","ecf-unsupported","test-deps"}
    assert set(records["watt"]["git_archive_paths"])==watt_paths
    assert set(records["guardian"]["git_archive_paths"])=={"src","tests"}
    assert all(records[owner]["git_archive_paths"]==["src"] for owner in ("ecf","ecf-unsupported"))
    assert records["test-deps"]["sha256"]=="beefa9671df14d21f2763a4e85841962f10af824a37caf6c679555166b13b9a6"
    return freeze

def read_built_identity(root, freeze):
    import re
    build=json.loads((root/"evidence"/"build.json").read_text())
    assert build["exit_code"]==0 and build["sources"]==freeze["sources"]
    assert build["control_harness_revision"]==freeze["control_harness_revision"]
    assert re.fullmatch(r"sha256:[0-9a-f]{64}",build["image"]["Id"])
    assert Path(build["build_directory"]).parent==root
    expected={"org.opencontainers.image.revision":freeze["sources"]["watt"]["revision"],
        "watt.c3.source-tree":freeze["sources"]["watt"]["tree"],
        "watt.c3.guardian-revision":freeze["sources"]["guardian"]["revision"],
        "watt.c3.guardian-tree":freeze["sources"]["guardian"]["tree"],
        "watt.c3.ecf-revision":freeze["sources"]["ecf"]["revision"],
        "watt.c3.ecf-tree":freeze["sources"]["ecf"]["tree"]}
    assert all(build["image"]["labels"].get(key)==value for key,value in expected.items())
    return build
