"""Use the existing exact-source C3 Dockerfile and frozen Owner dependencies."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--root", required=True)
root = Path(parser.parse_args().root)
previous = Path("/data/watt/ai-native-evolution-20261013/build-d27707cb/image/context")
frozen = json.loads((root / "private/frozen-source-manifest.json").read_text())
archive = root / "private/watt-source.tar"
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(archive) == frozen["archive_sha256"]
context = root / "image/context"
context.mkdir(parents=True, exist_ok=False)
source = context / "watt"
source.mkdir()
with tarfile.open(archive) as tar:
    assert tar.pax_headers.get("comment") == frozen["revision"]
    assert all(not m.name.startswith("/") and ".." not in Path(m.name).parts
        and not m.issym() and not m.islnk() for m in tar.getmembers())
    tar.extractall(source)
old = json.loads((previous / "c3-source-identity.json").read_text())
for name in ("guardian", "ecf", "ecf-unsupported", "test-deps"):
    shutil.copytree(str(previous / name), str(context / name))
inputs = {}
for path in sorted(context.rglob("*")):
    if not path.is_file():
        continue
    name = str(path.relative_to(context))
    inputs[name] = sha(path)
    if name.startswith(("guardian/", "ecf/", "ecf-unsupported/", "test-deps/")):
        assert old["build_input_sha256"][name] == inputs[name], name
dependency = "sha256:6c1f48e35ec485de278e8638f51d6aed75679b02a24d45355959bc8ddd7c0d14"
actual = json.loads(subprocess.check_output(["docker", "image", "inspect", dependency], universal_newlines=True))[0]
assert actual["Id"] == dependency
identity = {"schema": "c3-source-identity-v1",
    "sources": dict(old["sources"], watt={"revision": frozen["revision"], "tree": frozen["tree"]}),
    "base_image": {"reference": dependency, "image_id": dependency},
    "build_input_sha256": inputs, "archive_sha256": {"watt-source.tar": sha(archive)},
    "inherited_owner_source_observation": {"prior_input_manifest": str(previous / "c3-source-identity.json"),
        "raw_owner_and_test_dependency_files_match_prior_build_manifest": True}}
(context / "c3-source-identity.json").write_text(json.dumps(identity, indent=2) + "\n")
tag = "watt-c3-decision-revision:" + frozen["revision"][:8]
args = ["docker", "build", "--network", "none", "--memory", "1024m",
    "--cpu-period", "100000", "--cpu-quota", "100000", "--tag", tag,
    "--file", str(source / "docs/evidence/core-production-semantic-convergence-c3-20261009/Dockerfile.c3")]
for key, value in (("BASE_IMAGE", dependency), ("BASE_IMAGE_ID", dependency),
    ("WATT_REVISION", frozen["revision"]), ("WATT_TREE", frozen["tree"]),
    ("GUARDIAN_REVISION", identity["sources"]["guardian"]["revision"]),
    ("GUARDIAN_TREE", identity["sources"]["guardian"]["tree"])):
    args += ["--build-arg", key + "=" + value]
args.append(str(context))
started = time.monotonic()
with (root / "evidence/image-build.log").open("x") as log:
    completed = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT,
        env=dict(os.environ, DOCKER_BUILDKIT="0"))
receipt = {"recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "revision": frozen["revision"], "tree": frozen["tree"], "tag": tag,
    "source_archive_sha256": sha(archive), "elapsed_seconds": time.monotonic() - started,
    "exit_code": completed.returncode, "network": "none", "source_reinstalled": completed.returncode == 0,
    "runtime_source_overlay": False, "owner_sources": identity["sources"]}
if completed.returncode == 0:
    actual = json.loads(subprocess.check_output(["docker", "image", "inspect", tag], universal_newlines=True))[0]
    receipt.update(actual_image_id=actual["Id"], labels=actual["Config"]["Labels"], repo_digests=actual.get("RepoDigests", []))
(root / "evidence/image-build.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
raise SystemExit(completed.returncode)
