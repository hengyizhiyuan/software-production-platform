"""Run directed GOF regressions against the disposable N1 regression database.

Execute on ECS from a disposable image with Docker CLI and socket. Secrets are
copied only to an ephemeral 0600 env file and are never printed.
"""

import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path("/data/watt/n1-qualification-20261008/gof-84d16b1/watt")


def main():
    raw = subprocess.run(["docker", "inspect", "watt-n1-api-20261008"],
                         check=True, capture_output=True, text=True).stdout
    config = json.loads(raw)[0]["Config"]
    source = next(value.split("=", 1)[1] for value in config["Env"]
                  if value.startswith("SPG_DATABASE_URL="))
    regression = source.rsplit("/", 1)[0] + "/spg_n1_regression_20261008_b"
    descriptor, env_path = tempfile.mkstemp(prefix="gof-test-", dir="/run")
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write("SPG_TEST_DATABASE_URL=" + regression + "\n")
        result = subprocess.run([
            "docker", "run", "--rm", "--network", "watt-cloud-worker_control",
            "--env-file", env_path, "-e",
            "PYTHONPATH=/app/src:/opt/watt-owners/guardian/src:/opt/watt-owners/ecf/src",
            "-v", str(ROOT) + ":/app:ro", "-w", "/app",
            "-v", "/data/watt/n1-qualification-20261008/gof-e3de9bf/guardian:/opt/watt-owners/guardian:ro",
            "-v", "/data/watt/owners/ecf:/opt/watt-owners/ecf:ro",
            "watt-n1-pytest:20261008", "python", "-m", "pytest", "-q",
            "tests/integration/test_native_executor_runtime.py::test_production_preflight_failure_keeps_exact_diagnostic_before_terminal",
            "tests/test_governed_obligation_fulfillment.py",
            "tests/test_production_execution_runtime.py",
            "tests/test_n1_static_html_semantics.py",
            "tests/test_static_protected_context_verifier.py",
            "tests/test_static_candidate_assurance.py",
            "tests/test_guardian_assurance_adapter.py",
        ], check=False)
        raise SystemExit(result.returncode)
    finally:
        os.unlink(env_path)


if __name__ == "__main__":
    main()
