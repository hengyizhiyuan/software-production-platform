"""Launch the single request-only experiment in the existing isolated image."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--execute-once", action="store_true")
args = parser.parse_args()
root = Path("/data/watt/ai-native-evolution-20261013")
trial = root / "decision-revision-contract-20261014"
prior = root / "early-consumer-diagnostic-20261014"
image = "sha256:73da30f5567f5766b9767855c1e772fc5421d93a9da54f99a971db9d2f48ce53"
command = ["docker", "create", "--name", "watt-c3-decision-revision-20261014-" + ("live" if args.execute_once else "prepare"),
    "--network", "bridge" if args.execute_once else "none", "--read-only", "--user", "10001:10001",
    "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--memory", "1024m", "--cpus", "1",
    "--tmpfs", "/tmp:rw,nosuid,size=256m", "-w", "/app", "--entrypoint", "/opt/spg-venv/bin/python"]
if args.execute_once:
    command += ["--env-file", str(root / "private/model.env")]
mounts = [
    (prior / "governed_obligations.py", "/opt/spg-venv/lib/python3.13/site-packages/spg/application/governed_obligations.py", True),
    (prior / "fulfillment_candidate.py", "/opt/spg-venv/lib/python3.13/site-packages/spg/providers/fulfillment_candidate.py", True),
    (trial / "probe.py", "/run.py", True),
    (root / "nonholdout-15/private", "/historical", True),
    (Path("/data/watt/c3-semantic-convergence-20261009/non-holdout-cause-control-20261012/private/ordinary34"), "/inventory", True),
    (prior / "private", "/prior", True),
    (trial / "private", "/private", False),
    (trial / "evidence", "/evidence", False),
]
for source, destination, readonly in mounts:
    command += ["-v", str(source) + ":" + destination + (":ro" if readonly else "")]
command += [image, "/run.py"] + (["--execute-once"] if args.execute_once else [])
cid = subprocess.check_output(command, universal_newlines=True).strip()
actual = json.loads(subprocess.check_output(["docker", "inspect", cid], universal_newlines=True))[0]
if actual["Image"] != image:
    raise RuntimeError("PROBE_ACTUAL_IMAGE_DRIFT")
manifest = {"recorded_at_utc": datetime.now(timezone.utc).isoformat(), "container_id": cid,
    "actual_image_id": actual["Image"], "source_overlay": True, "user": actual["Config"]["User"],
    "network_mode": actual["HostConfig"]["NetworkMode"], "read_only_root": actual["HostConfig"]["ReadonlyRootfs"],
    "input_mounts_read_only": all(m["RW"] is False for m in actual["Mounts"] if m["Destination"] not in {"/private", "/evidence"}),
    "work_database_or_docker_socket_mounted": False, "execute_once": args.execute_once,
    "status": "CREATED_BEFORE_REQUEST"}
name = "live" if args.execute_once else "prepare"
receipt = trial / "evidence" / (name + "-runtime.json")
receipt.write_text(json.dumps(manifest, indent=2) + "\n")
completed = subprocess.run(["docker", "start", "-a", cid], stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT, universal_newlines=True)
(trial / "evidence" / (name + ".log")).write_text(completed.stdout)
manifest.update(status="FINISHED", exit_code=completed.returncode)
receipt.write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
if completed.returncode:
    raise SystemExit(completed.returncode)
