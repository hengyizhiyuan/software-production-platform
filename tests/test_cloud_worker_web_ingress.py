"""The temporary browser entrypoint must not publish execution or data services."""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


def test_cloud_worker_compose_publishes_only_authenticated_watt_web() -> None:
    if shutil.which("docker") is None:
        pytest.skip("Docker Compose is unavailable")
    compose = Path(__file__).resolve().parents[1] / "deploy/cloud-worker/docker-compose.yml"
    environment = os.environ | {
        "SPG_POSTGRES_PASSWORD": "test-only",
        "SPG_OPERATOR_TOKEN": "test-only",
        "SPG_DEEPSEEK_API_KEY": "test-only",
        "SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN": "test-only",
        "WATT_GITEA_PASSWORD": "test-only",
        "DOCKER_GID": "999",
    }
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose), "config", "--format", "json"],
        check=True, capture_output=True, text=True, env=environment,
    )
    configuration = json.loads(result.stdout)
    services = configuration["services"]
    assert services["api"]["ports"] == [{
        "mode": "ingress", "host_ip": "0.0.0.0", "target": 8000,
        "published": "8080", "protocol": "tcp",
    }]
    assert all(not service.get("ports") for name, service in services.items()
               if name != "api")
    assert configuration["networks"]["executor"]["internal"] is True
    assert services["api"]["environment"]["SPG_OWNER_RUNTIME_MODE"] == "REQUIRED"
