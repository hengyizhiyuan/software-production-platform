"""Guards for the one-grant, typed-root Alibaba Cloud Linux 3 host path."""

from hashlib import sha256
from pathlib import Path
import re
import subprocess
import sys

from spg.application.cloud_delivery import assess_invocation_result
from spg.domain.cloud_delivery import CloudOperationKind, connection_policy
from spg.infrastructure.aliyun_cloud import InvocationResult
from spg.infrastructure.cloud_delivery_commands import (
    HOST_RECIPE_FINGERPRINT, HOST_RECIPE_VERSION, PrepareDeploymentHostV1,
    CheckPrerequisites, compile_operation,
)


def test_one_connection_policy_has_exact_five_actions_and_two_run_as_identities():
    policy = connection_policy("1284723705318814")
    statements = policy["Statement"]
    assert len(statements) == 3
    assert {action for row in statements for action in row["Action"]} == {
        "ecs:DescribeInstances", "ecs:DescribeCloudAssistantStatus",
        "ecs:RunCommand", "ecs:DescribeInvocations",
        "ecs:DescribeInvocationResults"}
    instance = "acs:ecs:*:1284723705318814:instance/*"
    command = "acs:ecs:*:1284723705318814:command/*"
    assert statements[0]["Resource"] == [instance]
    assert statements[1]["Resource"] == [instance]
    assert statements[1]["Condition"] == {"StringEquals": {
        "ecs:CommandRunAs": ["root", "wattdeploy"]}}
    assert statements[2]["Resource"] == [instance, command]
    assert all(row["Resource"] != ["*"] for row in statements)


def test_bootstrap_is_fixed_fingerprinted_and_separate_from_nonroot_precheck():
    bootstrap = PrepareDeploymentHostV1()
    kind, script = compile_operation(bootstrap)
    assert kind is CloudOperationKind.PREPARE_WATT_DEPLOYMENT_HOST_V1
    assert HOST_RECIPE_VERSION == bootstrap.recipe_version
    assert HOST_RECIPE_FINGERPRINT == sha256(script.encode()).hexdigest()
    assert len(script.encode()) < 16000
    assert re.search(r'test "\$ID" = alinux && test "\$VERSION_ID" = 3', script)
    assert script.index("getent passwd wattdeploy") < script.index("useradd -m")
    assert script.index("overlapping allocation") < script.index("useradd -m")
    assert "--add-subuids" in script and "--add-subgids" in script
    assert "dockerd-rootless-setuptool.sh install" in script
    assert "systemctl --user enable --now docker.service" in script
    assert "docker info --format '{{json .SecurityOptions}}'" in script
    assert "docker context show" in script
    assert "gpgcheck=1" in script and "e6c650e0700b1bf4" in script
    assert "curl -fsSL" in script and "| sh" not in script
    for forbidden in ("systemctl start docker.service", "systemctl enable docker.service",
                      "usermod -aG docker", "nginx", "firewall-cmd", "iptables -A",
                      "security_group", "sshd_config", "dnf update", "rm -rf"):
        assert forbidden not in script
    _, ordinary = compile_operation(CheckPrerequisites(8080))
    assert "useradd" not in ordinary and "dnf" not in ordinary


def test_bootstrap_receipt_requires_final_ready_marker_and_keeps_failures_typed():
    kind = CloudOperationKind.PREPARE_WATT_DEPLOYMENT_HOST_V1
    good = InvocationResult("inv", "cmd", "Success", 0,
        "WATT_HOST_BEFORE_BOOTSTRAP_REQUIRED\nWATT_EFFECT_USER_CREATED\nWATT_HOST_READY")
    assert assess_invocation_result(good, "wattdeploy", kind)[:2] == (
        "WATT_HOST_READY", True)
    partial = InvocationResult("inv", "cmd", "Success", 0,
        "WATT_HOST_BEFORE_BOOTSTRAP_REQUIRED\nWATT_EFFECT_USER_CREATED")
    assert assess_invocation_result(partial, "wattdeploy", kind)[:2] == (
        "CLOUD_OPERATION_UNVERIFIED", False)
    conflict = InvocationResult("inv", "cmd", "Failed", 20,
        "WATT_HOST_BEFORE_BOOTSTRAP_REQUIRED\nBLOCKED_SUBID_CONFLICT")
    assert assess_invocation_result(conflict, "wattdeploy", kind)[:2] == (
        "HOST_PROFILE_CONFLICT", False)
    unsupported = InvocationResult("inv", "cmd", "Failed", 20,
        "BLOCKED_UNSUPPORTED_HOST_PROFILE")
    assert assess_invocation_result(unsupported, "wattdeploy", kind)[:2] == (
        "UNSUPPORTED_HOST_PROFILE", False)


def test_embedded_subid_allocator_rejects_collision_and_chooses_free_range(tmp_path):
    script = PrepareDeploymentHostV1().compile()
    preflight, allocator = re.findall(r"python3 - <<'PY'[^\n]*\n(.*?)\nPY",
        script, re.S)
    subuid, subgid = tmp_path / "subuid", tmp_path / "subgid"
    preflight = preflight.replace("Path('/etc/' + name)",
        f"Path({str(tmp_path)!r} + '/' + name)")
    allocator = allocator.replace("Path('/etc/subuid')", f"Path({str(subuid)!r})")
    allocator = allocator.replace("Path('/etc/subgid')", f"Path({str(subgid)!r})")
    subuid.write_text("alice:100000:65536\nbob:150000:65536\n")
    subgid.write_text("alice:100000:65536\n")
    collision = subprocess.run([sys.executable, "-c", preflight],
        capture_output=True, text=True)
    assert collision.returncode != 0
    subuid.write_text("alice:100000:65536\n")
    clean = subprocess.run([sys.executable, "-c", preflight],
        capture_output=True, text=True)
    assert clean.returncode == 0
    chosen = subprocess.run([sys.executable, "-c", allocator],
        capture_output=True, text=True)
    assert chosen.returncode == 0
    assert chosen.stdout.strip() == "165536-231071"


def test_product_does_not_offer_second_ram_grant_or_change_workspace_quadrants():
    base = Path(__file__).resolve().parents[1]
    flow = (base / "src/spg/web/cloud_delivery.js").read_text()
    assert "前往阿里云授权此主机" not in flow
    assert "我决定准备部署" not in flow
    assert "授权并部署" in flow and "自动检查" in flow
    workspace = (base / "src/spg/web/experience.js").read_text()
    for quadrant in ("Agenda", "Reality", "Actions", "Production"):
        assert quadrant in workspace
