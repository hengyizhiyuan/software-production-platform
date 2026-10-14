"""Persist focused, network-free prototype qualification and baseline comparison."""

import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

root = Path("/data/watt/ai-native-evolution-20261013/early-consumer-diagnostic-20261014")
image = "sha256:73da30f5567f5766b9767855c1e772fc5421d93a9da54f99a971db9d2f48ce53"
evidence = root / "evidence"
evidence.mkdir(exist_ok=True)
os.chown(str(evidence), 10001, 10001)
base = ["docker", "run", "--rm", "--network", "none", "-v", f"{root}/tests:/app/tests:ro",
    "-v", f"{evidence}:/evidence", "-w", "/app", "--entrypoint", "/opt/spg-venv/bin/python"]
overlay = []
for source, target in (("governed_obligations.py", "application"), ("fulfillment_candidate.py", "providers")):
    overlay += ["-v", f"{root}/{source}:/opt/spg-venv/lib/python3.13/site-packages/spg/{target}/{source}:ro"]
suite = ["tests/test_c3_early_consumer_mapping_diagnostics.py",
    "tests/test_c3_fulfillment_wire_feedback.py", "tests/test_c3_reviewer_contract_feedback.py",
    "tests/test_c3_reviewed_fact_method_applicability.py"]
report = {"recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "image_id": subprocess.check_output(["docker", "image", "inspect", image, "--format", "{{.Id}}"], universal_newlines=True).strip(),
    "qualification": "SOURCE_OVERLAY_PROTOTYPE; NOT_A_NEW_APPLICATION_IMAGE_OR_G0",
    "source_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ("governed_obligations.py", "fulfillment_candidate.py", "tests/test_c3_early_consumer_mapping_diagnostics.py")},
    "runs": []}
for name, mounts, tests in (
    ("prototype-focused", overlay, suite),
    ("unchanged-image-duplicate-controls", [], [
        "tests/test_c3_fulfillment_wire_feedback.py::test_feedback_drift_stops_before_another_model_request[duplicate-response]",
        "tests/test_c3_fulfillment_wire_feedback.py::test_feedback_drift_stops_before_another_model_request[duplicate-validation]"]),
):
    args = base + mounts + [image, "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "--junitxml", f"/evidence/{name}.xml"] + tests
    completed = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    log = evidence / f"{name}.log"
    log.write_text(completed.stdout)
    tree = ET.parse(evidence / f"{name}.xml")
    cases = tree.findall(".//testcase")
    failures = [case.get("name") for case in cases if case.find("failure") is not None or case.find("error") is not None]
    report["runs"].append({"name": name, "exit_code": completed.returncode,
        "tests": len(cases), "failures": failures,
        "passed": sum(case.find("failure") is None and case.find("error") is None
            and case.find("skipped") is None for case in cases),
        "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
    (evidence / "qualification.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
