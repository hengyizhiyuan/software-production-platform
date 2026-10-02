"""Fail-closed contracts for the bounded ECS operation set."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from spg.domain.cloud_delivery import (
    CloudConnection, CloudConnectionState, CloudDeliveryAuthorizationRequest,
    CloudDeployment, CloudDeploymentState, CloudTarget,
    discovery_policy, target_execution_policy, trust_policy,
)
from spg.infrastructure import cloud_delivery_commands as commands
from spg.infrastructure.cloud_delivery_artifact import (
    CloudArtifactError, CloudDeliveryArtifactBuilder,
)


@pytest.fixture
def target():
    return CloudTarget(account_id="1234567890123456", region_id="cn-hangzhou",
        instance_id="i-abcdefgh", name="官网生产环境", os_name="Alibaba Cloud Linux",
        status="Running", cloud_assistant_ready=True)


def test_discovery_and_exact_target_policies_do_not_widen_write_authority(target):
    discovery = discovery_policy(target.account_id)
    assert discovery["Statement"][0]["Action"] == [
        "ecs:DescribeInstances", "ecs:DescribeCloudAssistantStatus"]
    assert all("RunCommand" not in action for action in discovery["Statement"][0]["Action"])
    execution = target_execution_policy(target, "wattdeploy")
    write = execution["Statement"][0]
    assert write["Action"] == ["ecs:RunCommand"]
    assert write["Resource"] == [
        "acs:ecs:cn-hangzhou:1234567890123456:instance/i-abcdefgh"]
    assert write["Condition"] == {"StringEquals": {"ecs:CommandRunAs": "wattdeploy"}}
    assert all("ecs:RunCommand" not in item["Action"]
        for item in execution["Statement"][1:])
    with pytest.raises(ValueError):
        target_execution_policy(target, "root")


def test_trust_is_exact_principal_and_external_id():
    principal = "acs:ram::1111111111111111:user/watt-service"
    external = "x" * 48
    statement = trust_policy(principal, external)["Statement"][0]
    assert statement["Principal"] == {"RAM": [principal]}
    assert statement["Condition"] == {"StringEquals": {"sts:ExternalId": external}}
    with pytest.raises(ValueError):
        trust_policy("acs:ram::*", external)


def test_authorization_request_refuses_raw_commands_and_other_target(target):
    values = dict(connection_id=uuid4(), manifest_id=uuid4(),
        manifest_fingerprint="a" * 64, target_account_id=target.account_id,
        target_region_id=target.region_id,
        target_instance_id=target.instance_id, port=8080, rationale="confirmed")
    for name in ("raw_command", "shell", "script", "command_text"):
        with pytest.raises(ValidationError):
            CloudDeliveryAuthorizationRequest(**values, **{name: "touch /tmp/escape"})
    with pytest.raises(ValidationError):
        CloudDeliveryAuthorizationRequest(**{**values,
            "target_instance_id": "other-host"})


def test_connection_is_not_ready_from_role_or_selection_alone(target):
    base = dict(id=uuid4(), owner_id="human:test", service_account_id="1111111111111111",
        service_principal_arn="acs:ram::1111111111111111:user/watt-service",
        external_id="x" * 48, recommended_role_name="WattECSDelivery",
        role_arn="acs:ram::1234567890123456:role/WattECSDelivery",
        customer_account_id=target.account_id, created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC))
    with pytest.raises(ValidationError):
        CloudConnection(**base, state=CloudConnectionState.READY, target=target)
    with pytest.raises(ValidationError):
        CloudConnection(**{**base, "customer_account_id": "2222222222222222"},
            state=CloudConnectionState.TARGET_SELECTED, target=target)


def test_runtime_success_and_rollback_require_observed_verification(target):
    base = dict(id=uuid4(), authorization_id=uuid4(), connection_id=uuid4(),
        manifest_id=uuid4(), work_id=uuid4(), target=target,
        artifact_sha256="a" * 64, port=8080,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
    with pytest.raises(ValidationError):
        CloudDeployment(**base, state=CloudDeploymentState.SUCCEEDED)
    with pytest.raises(ValidationError):
        CloudDeployment(**base, state=CloudDeploymentState.ROLLED_BACK)


def test_compiler_never_accepts_untyped_shell_or_unscoped_runtime():
    with pytest.raises(commands.CloudCommandError, match="UNSUPPORTED_OPERATION"):
        commands.compile_operation("echo unsafe")
    deploy_id, manifest_id = uuid4(), uuid4()
    with pytest.raises(TypeError):
        commands.deploy(raw_command="rm -rf /", deployment_id=deploy_id)
    with pytest.raises(commands.CloudCommandError):
        commands.deploy(deployment_id=deploy_id, manifest_id=manifest_id,
            digest="bad", image="sha256:" + "a" * 64,
            internal_port=8080, external_port=8080,
            signed_url="https://example.invalid/archive")
    with pytest.raises(commands.CloudCommandError):
        commands.deploy(deployment_id=deploy_id, manifest_id=manifest_id,
            digest="a" * 64, image="sha256:" + "b" * 64,
            internal_port=8080, external_port=8080,
            signed_url="http://insecure.invalid/archive")
    precheck = commands.precheck(8080)
    assert "rootless" in precheck and "BLOCKED_DOCKER_MISSING" in precheck
    assert "BLOCKED_UNKNOWN_PORT_OWNER" in precheck
    assert "apt-get" not in precheck and "yum" not in precheck
    assert "useradd" not in precheck and "systemctl" not in precheck
    assert "docker rm -f" not in precheck
    script = commands.deploy(deployment_id=deploy_id, manifest_id=manifest_id,
        digest="a" * 64, image="sha256:" + "b" * 64,
        internal_port=8080, external_port=8080,
        signed_url="https://example.invalid/archive?token=secret")
    assert "sha256sum" in script and "watt.delivery" in script
    assert "docker load" in script and "WATT_ACTIVATED" in script
    assert "docker stop" not in script


def test_rollback_script_only_names_exact_watt_runtime_and_checks_health():
    old, new = uuid4(), uuid4()
    script = commands.rollback(new, old, "sha256:" + "a" * 64, 8080)
    assert commands.runtime_name(old) in script
    assert commands.runtime_name(new) in script
    assert "watt.delivery" in script and "WATT_ROLLBACK_HEALTHY" in script
    assert "docker rm -f" in script and "curl --fail" in script


def test_static_builder_requires_pinned_base_and_never_copies_code(tmp_path):
    class Delivery:
        @staticmethod
        def artifact(_work, _manifest, path):
            return {"site/index.html": b"<h1>Ready</h1>",
                "site/app.js": b"document.body.dataset.ready='yes'"}[path]
    class Item:
        def __init__(self, path): self.path = path
    class Recipe:
        adapter = "STATIC_WEB"
        entrypoint = "site/index.html"
    class Software:
        runtime_recipe = Recipe()
    class Manifest:
        id, work_id = uuid4(), uuid4()
        fingerprint = "a" * 64
        repository_revision = "b" * 40
        software = Software()
        artifacts = [Item("site/index.html"), Item("site/app.js"),
            Item("site/secrets.py"), Item("site/.env")]
    builder = CloudDeliveryArtifactBuilder(Delivery(), None, tmp_path, None)
    with pytest.raises(CloudArtifactError, match="PINNED"):
        builder.prepare(Manifest(), uuid4())
    builder.static_base_image = "python@sha256:" + "c" * 64
    calls=[]
    def docker(*args, **_):
        calls.append(args)
        if args[0:2] == ("image", "inspect"):
            return "sha256:" + "d" * 64
        if args[0] == "save":
            Path(args[2]).write_bytes(b"image archive")
        return ""
    builder._docker = docker
    result = builder.prepare(Manifest(), uuid4())
    assert result.artifact_kind == "STATIC_WEB"
    site=Path(result.archive_path).parent/"site"
    assert (site/"index.html").read_bytes() == b"<h1>Ready</h1>"
    assert (site/"app.js").is_file()
    assert not (site/"secrets.py").exists() and not (site/".env").exists()
    dockerfile = (site.parent/"Dockerfile").read_text()
    assert 'USER 101' in dockerfile
    assert '"http.server", "8080"' in dockerfile
    assert any(call[0]=="build" for call in calls)


def test_full_application_export_uses_exact_served_preview_image(tmp_path):
    image="sha256:"+"e"*64
    class Delivery:
        @staticmethod
        def candidate_context(_work):
            return {"tree":"f"*40}
    class Preview:
        def require_served_for_delivery(self, work_id, candidate_id, revision, tree):
            assert (work_id,candidate_id,revision,tree)==(
                manifest.work_id,candidate,manifest.repository_revision,"f"*40)
            return type("Session",(),{"image_reference":image})()
    class Recipe:
        adapter="FULL_APPLICATION_RUNTIME"
        entrypoint=None
    class Software:
        runtime_recipe=Recipe()
    class Manifest:
        id,work_id=uuid4(),uuid4()
        fingerprint="a"*64
        repository_revision="b"*40
        software=Software()
    manifest,candidate=Manifest(),uuid4()
    builder=CloudDeliveryArtifactBuilder(Delivery(),Preview(),tmp_path,None)
    calls=[]
    def docker(*args,**_):
        calls.append(args)
        if args[0]=="save": Path(args[2]).write_bytes(b"exact preview image")
        return ""
    builder._docker=docker
    prepared=builder.prepare(manifest,candidate)
    assert prepared.image_identity==image
    assert calls==[("save","-o",prepared.archive_path,image)]
    assert prepared.artifact_kind=="FULL_APPLICATION_RUNTIME"
