"""Isolated launch, actual image observation and one-shot execution boundary."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--execute-once", action="store_true")
args = parser.parse_args()
root = Path("/data/watt/ai-native-evolution-20261013")
trial = root / "semantic-assumption-review-20261014"
source = root / "early-consumer-diagnostic-20261014"
previous = root / "decision-revision-contract-20261014"
image = "sha256:73da30f5567f5766b9767855c1e772fc5421d93a9da54f99a971db9d2f48ce53"
mode = "live" if args.execute_once else "prepare"
command = ["docker", "create", "--name", "watt-c3-assumption-review-20261014-" + mode,
    "--network", "bridge" if args.execute_once else "none", "--read-only", "--user", "10001:10001",
    "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--memory", "1024m", "--cpus", "1",
    "--tmpfs", "/tmp:rw,nosuid,size=256m", "-w", "/app", "--entrypoint", "/opt/spg-venv/bin/python"]
if args.execute_once:
    command += ["--env-file", str(root / "private/model.env")]
mounts = [
    (source / "governed_obligations.py", "/opt/spg-venv/lib/python3.13/site-packages/spg/application/governed_obligations.py", True),
    (source / "fulfillment_candidate.py", "/opt/spg-venv/lib/python3.13/site-packages/spg/providers/fulfillment_candidate.py", True),
    (trial / "probe.py", "/run.py", True),
    (trial / "protocol.md", "/protocol.md", True),
    (previous / "probe.py", "/previous_probe.py", True),
    (root / "nonholdout-15/private", "/historical", True),
    (Path("/data/watt/c3-semantic-convergence-20261009/non-holdout-cause-control-20261012/private/ordinary34"), "/inventory", True),
    (previous / "private", "/prior", True),
    (trial / "private", "/private", False),
    (trial / "evidence", "/evidence", False),
]
for path, destination, readonly in mounts:
    command += ["-v", str(path) + ":" + destination + (":ro" if readonly else "")]
command += [image, "/run.py"] + (["--execute-once"] if args.execute_once else [])
cid = subprocess.check_output(command, universal_newlines=True).strip()
actual = json.loads(subprocess.check_output(["docker", "inspect", cid], universal_newlines=True))[0]
if actual["Image"] != image:
    raise RuntimeError("ASSUMPTION_PROBE_IMAGE_DRIFT")
manifest = {"recorded_at_utc": datetime.now(timezone.utc).isoformat(), "container_id": cid,
    "actual_image_id": actual["Image"], "source_overlay": True,
    "user": actual["Config"]["User"], "network_mode": actual["HostConfig"]["NetworkMode"],
    "read_only_root": actual["HostConfig"]["ReadonlyRootfs"],
    "input_mounts_read_only": all(not m["RW"] for m in actual["Mounts"] if m["Destination"] not in {"/private", "/evidence"}),
    "business_database_access": False, "docker_socket_mounted": False, "mode": mode,
    "status": "CREATED_BEFORE_REQUEST"}
receipt = trial / "evidence" / (mode + "-runtime.json")
receipt.write_text(json.dumps(manifest, indent=2) + "\n")
completed = subprocess.run(["docker", "start", "-a", cid], stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT, universal_newlines=True)
(trial / "evidence" / (mode + ".log")).write_text(completed.stdout)
manifest.update(status="FINISHED", exit_code=completed.returncode)
receipt.write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
raise SystemExit(completed.returncode)
