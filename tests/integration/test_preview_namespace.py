"""Actual Docker gateway observation, independent of tester/host loopback."""
import shutil
import subprocess
from uuid import uuid4

import pytest

from spg.infrastructure.candidate_preview_runtime import DockerCandidatePreviewRuntime


def test_verifier_uses_gateway_namespace_and_rejects_redirect(tmp_path):
    if shutil.which("docker") is None:
        pytest.skip("Docker runtime required")
    provider = DockerCandidatePreviewRuntime(tmp_path)
    provider.preflight()
    preview_id = uuid4()
    names = provider._names(preview_id)
    network = names["gateway"]
    configuration = tmp_path / "nginx.conf"
    configuration.write_text('events {}\nhttp { server { listen 80;\n'
        'location / { default_type text/html; return 200 "<p>Exact candidate</p>"; }\n'
        'location /redirect { return 302 http://example.invalid/; }\n} }\n')
    subprocess.run(["docker", "network", "create", network], check=True, capture_output=True)
    try:
        subprocess.run(["docker", "run", "-d", "--name", names["proxy"],
            "--network", network, "-v", f"{configuration}:/etc/nginx/nginx.conf:ro",
            "nginx:1.27-alpine"], check=True, capture_output=True)
        response = provider._gateway_request(preview_id, "/")
        assert response["status"] == 200
        assert names["proxy"] in response["url"]
        assert "127.0.0.1" not in response["url"]
        redirect = provider._gateway_request(preview_id, "/redirect")
        assert redirect["status"] == 302
        assert redirect["url"] == f"http://{names['proxy']}/redirect"
    finally:
        subprocess.run(["docker", "rm", "-f", names["proxy"]], capture_output=True)
        subprocess.run(["docker", "network", "rm", network], capture_output=True)
