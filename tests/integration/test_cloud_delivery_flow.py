"""Fake-provider proof of durable cloud authority and exact Delivery binding."""

from hashlib import sha256
from io import BytesIO
import json
import tarfile
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text

from test_software_delivery import clean_schema, produce
from spg.application.cloud_delivery import CloudDeliveryError, CloudDeliveryService
from spg.config import Settings
from spg.domain.cloud_delivery import (
    CloudDeliveryAuthorizationRequest, CloudOperationKind,
    CloudPreparedArtifact, CloudTarget,
)
from spg.domain.delivery import HumanAcceptanceRequest
from spg.infrastructure.aliyun_cloud import (
    InvocationResult, StagedCloudArtifact, TemporaryCloudSession,
)
from spg.infrastructure.cloud_delivery_network import IngressResult
from spg.infrastructure.persistence.cloud_delivery_schema import (
    cloud_connections, cloud_delivery_authorizations, cloud_deployments,
    cloud_prepared_artifacts,
)


pytestmark = pytest.mark.postgresql


class FakeCloud:
    def __init__(self, target):
        self.target = target
        self.assumptions = []
        self.operations = []
        self.grants = []
        self.fail_next_verify = False
        self.precheck_failure = None
        self.precheck_result = None
        self.zero_exit_unverified = False
        self.assumed_role_override = None
        self.ingress_operations = []

    def ensure_public_ingress(self, _session, operation):
        self.ingress_operations.append(operation)
        return IngressResult("sg-abcdefgh", "sgr-abcdefgh",
            operation.description, "CREATED", "request-ingress", True)

    def service_identity(self):
        return {"AccountId": "1111111111111111",
            "Arn": "acs:ram::1111111111111111:user/watt-service"}

    def assume_role(self, role_arn, external_id):
        self.assumptions.append((role_arn, external_id))
        return TemporaryCloudSession("temporary-id", "temporary-secret",
            "temporary-token")

    def assumed_identity(self, _session):
        role = self.assumed_role_override or self.assumptions[-1][0]
        return {"AccountId": self.target.account_id,
            "IdentityType": "AssumedRoleUser",
            "Arn": role.replace(":role/", ":assumed-role/", 1) + "/WattDelivery"}

    def regions(self, _session):
        return (self.target.region_id,)

    def instances(self, _session, account, region):
        assert account == self.target.account_id and region == self.target.region_id
        return (self.target,)

    def exact_instance(self, _session, target):
        assert target.identity == self.target.identity
        return self.target

    def target_grant_dry_run(self, _session, target):
        self.grants.append(target.identity)

    def stage(self, archive, digest):
        assert sha256(archive.read_bytes()).hexdigest() == digest
        return StagedCloudArtifact("watt-delivery/sha256/" + digest + ".tar",
            digest, "https://staging.example.invalid/signed?secret=must-not-persist")

    def run(self, _session, target, operation, client_token):
        assert target.identity == self.target.identity
        assert len(client_token) <= 64
        kind, script = operation.kind, operation.compile()
        self.operations.append((kind, script))
        if kind is CloudOperationKind.CHECK_DEPLOYMENT_PREREQUISITES and self.precheck_result:
            result, self.precheck_result = self.precheck_result, None
            return result
        output = {CloudOperationKind.PREPARE_WATT_DEPLOYMENT_HOST_V1:
                "WATT_HOST_BEFORE_BOOTSTRAP_REQUIRED\nWATT_EFFECT_USER_CREATED\nWATT_HOST_READY",
            CloudOperationKind.CHECK_DEPLOYMENT_PREREQUISITES: "WATT_PRECHECK_OK",
            CloudOperationKind.DEPLOY_WATT_RELEASE: "WATT_ACTIVATED",
            CloudOperationKind.VERIFY_WATT_RUNTIME: "WATT_RUNTIME_HEALTHY",
            CloudOperationKind.ROLLBACK_WATT_RELEASE: "WATT_ROLLBACK_HEALTHY"}[kind]
        if kind is CloudOperationKind.CHECK_DEPLOYMENT_PREREQUISITES and self.precheck_failure:
            failure,self.precheck_failure=self.precheck_failure,None
            return InvocationResult("invoke-" + str(len(self.operations)),
                "command-" + str(len(self.operations)), "Failed", 20, failure)
        if kind is CloudOperationKind.VERIFY_WATT_RUNTIME and self.fail_next_verify:
            self.fail_next_verify = False
            return InvocationResult("invoke-" + str(len(self.operations)),
                "command-" + str(len(self.operations)), "Failed", 20,
                "BLOCKED_RUNTIME_HEALTH")
        if kind is CloudOperationKind.VERIFY_WATT_RUNTIME and self.zero_exit_unverified:
            self.zero_exit_unverified=False
            return InvocationResult("invoke-" + str(len(self.operations)),
                "command-" + str(len(self.operations)), "Success", 0,
                "no observed health token")
        return InvocationResult("invoke-" + str(len(self.operations)),
            "command-" + str(len(self.operations)), "Success", 0, output)


class FakeBuilder:
    def __init__(self, tmp_path):
        self.tmp_path = tmp_path

    def prepare(self, manifest, _candidate_id):
        path = self.tmp_path / "exact-image.tar"
        config = b'{"architecture":"amd64","os":"linux"}'
        digest = sha256(config).hexdigest()
        image_manifest = json.dumps([{"Config": f"blobs/sha256/{digest}",
            "RepoTags": None, "Layers": []}]).encode()
        with tarfile.open(path, "w") as archive:
            for name, content in (("manifest.json", image_manifest),
                    (f"blobs/sha256/{digest}", config)):
                member = tarfile.TarInfo(name)
                member.size = len(content)
                archive.addfile(member, BytesIO(content))
        return CloudPreparedArtifact(id=uuid4(), manifest_id=manifest.id,
            manifest_fingerprint=manifest.fingerprint,
            candidate_revision=manifest.repository_revision,
            artifact_sha256=sha256(path.read_bytes()).hexdigest(),
            archive_path=str(path), image_identity="sha256:" + "a" * 64,
            internal_port=8080, artifact_kind="STATIC_WEB",
            created_at=manifest.created_at)


def test_exact_connection_target_authorization_and_deployment(
        postgres_database, tmp_path):
    with postgres_database.engine.begin() as connection:
        connection.execute(text("TRUNCATE cloud_deployments, cloud_delivery_authorizations, "
            "cloud_prepared_artifacts, cloud_connections CASCADE"))
    _, work_id, delivery, _ = produce(postgres_database, tmp_path)
    manifest = delivery.publish(work_id)
    delivery.runtime_probe = lambda *_: {"status": "READY"}
    delivery.decide(work_id, manifest.id, HumanAcceptanceRequest(
        manifest_fingerprint=manifest.fingerprint, decision="ACCEPT",
        authority_identity="human:test", rationale="inspected current result"))
    target = CloudTarget(account_id="1234567890123456",
        region_id="cn-hangzhou", instance_id="i-abcdefgh",
        name="官网生产环境", os_name="Alibaba Cloud Linux  3.2104 LTS 64位",
        os_type="Linux",
        status="Running", public_address="8.8.8.8",
        cloud_assistant_ready=True)
    provider = FakeCloud(target)
    product_id = uuid4()
    service = CloudDeliveryService(postgres_database, delivery, Settings(),
        provider=provider, builder=FakeBuilder(tmp_path),
        owner_check=lambda _actor, manifest_id: {
            "summary": {"work_id": str(work_id), "product_id": str(product_id)},
            "current": manifest_id == manifest.id,
            "acceptance": {"decision": "ACCEPT"}},
        external_probe=lambda *_: True)
    actor = "human:owner"
    first, second = service.draft(actor), service.draft(actor)
    assert first["external_id"] != second["external_id"]
    assert first["state"] == "AWAITING_CLOUD_AUTHORIZATION"
    role = "acs:ram::1234567890123456:role/WattECSDelivery"
    with pytest.raises(CloudDeliveryError, match="INVALID_ROLE_ARN"):
        service.set_role(actor, UUID(second["id"]), "acs:ram::*")
    other_role = "acs:ram::9999999999999999:role/WattECSDelivery"
    service.set_role(actor, UUID(second["id"]), other_role)
    with pytest.raises(CloudDeliveryError, match="ASSUMED_ACCOUNT_MISMATCH"):
        service.verify_role(actor, UUID(second["id"]), other_role)
    provider.assumed_role_override="acs:ram::1234567890123456:role/OtherRole"
    with pytest.raises(CloudDeliveryError, match="ASSUMED_ROLE_MISMATCH"):
        service.verify_role(actor, UUID(first["id"]), role)
    provider.assumed_role_override=None
    bound = service.set_role(actor, UUID(first["id"]), role)
    assert bound["connection_policy"]["Statement"][0]["Action"] == [
        "ecs:DescribeInstances", "ecs:DescribeCloudAssistantStatus"]
    discovered = service.verify_role(actor, UUID(first["id"]), role)
    assert provider.assumptions[-1] == (role, first["external_id"])
    assert len(discovered["discovered_targets"]) == 1
    assert "instance_id" not in discovered["discovered_targets"][0]
    selected = service.select(actor, UUID(first["id"]),
        UUID(discovered["discovered_targets"][0]["selection_token"]))
    assert selected["state"] == "READY"
    provider.target = target.model_copy(update={"cloud_assistant_ready": False})
    with pytest.raises(CloudDeliveryError, match="TARGET_NOT_READY"):
        service.verify_target(actor, UUID(first["id"]))
    assert not provider.operations
    provider.target = target
    ready = service.verify_target(actor, UUID(first["id"]))
    assert ready["state"] == "READY"
    assert provider.grants[-1] == target.identity
    request = CloudDeliveryAuthorizationRequest(connection_id=UUID(first["id"]),
        manifest_id=manifest.id, manifest_fingerprint=manifest.fingerprint,
        target_account_id=target.account_id,
        target_region_id=target.region_id,
        target_instance_id=target.instance_id,
        port=8080, exposure_mode="PUBLIC",
        rationale="approved exact version and target")
    wrong = request.model_copy(update={"target_instance_id": "i-different"})
    with pytest.raises(CloudDeliveryError, match="AUTHORIZATION_TARGET_MISMATCH"):
        service.authorize(actor, work_id, wrong)
    owner_check=service.owner_check
    service.owner_check=lambda *_:{"summary":{"work_id":str(work_id)},
        "current":False,"acceptance":{"decision":"ACCEPT"}}
    with pytest.raises(CloudDeliveryError, match="CURRENT_HUMAN_ACCEPTED_DELIVERY_REQUIRED"):
        service.authorize(actor, work_id, request)
    service.owner_check=owner_check
    authorized = service.authorize(actor, work_id, request)
    result = service.execute(actor, UUID(authorized["id"]))
    assert result["state"] == "SUCCEEDED"
    assert result["health_verified"] and result["business_verified"]
    assert [row["kind"] for row in result["operations"]] == [
        "PREPARE_WATT_DEPLOYMENT_HOST_V1", "CHECK_DEPLOYMENT_PREREQUISITES",
        "ENSURE_WATT_PUBLIC_INGRESS_V1", "STAGE_ARTIFACT", "DEPLOY_WATT_RELEASE",
        "VERIFY_WATT_RUNTIME", "VERIFY_PUBLIC_BUSINESS"]
    assert all(row["verified"] for row in result["operations"])
    assert all(row["invocation_id"] and row["command_id"]
        for row in result["operations"] if row["kind"] not in {
            "ENSURE_WATT_PUBLIC_INGRESS_V1", "STAGE_ARTIFACT",
            "VERIFY_PUBLIC_BUSINESS"})
    assert "must-not-persist" not in str(result)
    assert "must-not-persist" not in str(service.deployment(actor, UUID(result["id"])))
    assert "must-not-persist" in provider.operations[2][1]
    with pytest.raises(CloudDeliveryError, match="AUTHORIZATION_ALREADY_USED"):
        service.execute(actor, UUID(authorized["id"]))
    replacement = service.authorize(actor, work_id, request.model_copy(update={
        "expected_current_deployment_id": UUID(result["id"])}))
    loaded_id = "sha256:" + sha256(
        b'{"architecture":"amd64","os":"linux"}').hexdigest()
    with postgres_database.unit_of_work() as uow:
        repaired = uow.session.execute(select(cloud_prepared_artifacts.c.payload)
            .where(cloud_prepared_artifacts.c.manifest_id == manifest.id)).scalar_one()
    assert repaired["image_identity"] == loaded_id
    assert repaired["artifact_sha256"] == authorized["artifact_sha256"]
    assert result["image_identity"] == "sha256:" + "a" * 64
    provider.fail_next_verify = True
    rolled_back = service.execute(actor, UUID(replacement["id"]))
    assert rolled_back["image_identity"] == loaded_id
    assert rolled_back["state"] == "ROLLED_BACK"
    assert rolled_back["rollback_verified"]
    assert [item["kind"] for item in rolled_back["operations"]][-3:] == [
        "VERIFY_WATT_RUNTIME", "ROLLBACK_WATT_RELEASE", "VERIFY_ROLLBACK_BUSINESS"]
    assert rolled_back["operations"][-3]["output_summary"] == "BLOCKED_RUNTIME_HEALTH"
    assert rolled_back["operations"][-2]["verified"]
    assert rolled_back["operations"][-1]["verified"]
    provider.zero_exit_unverified=True
    again=service.authorize(actor,work_id,request.model_copy(update={
        "expected_current_deployment_id":UUID(result["id"])}))
    unverified=service.execute(actor,UUID(again["id"]))
    assert unverified["state"]=="ROLLED_BACK"
    assert unverified["operations"][-3]["status"]=="Success"
    assert not unverified["operations"][-3]["verified"]
    for port, failure in ((9090,"BLOCKED_DOCKER_MISSING"),
                          (9091,"BLOCKED_UNKNOWN_PORT_OWNER")):
        provider.precheck_failure=failure
        blocked_auth=service.authorize(actor,work_id,request.model_copy(update={
            "expected_current_deployment_id":None,"port":port}))
        before=len(provider.operations)
        blocked=service.execute(actor,UUID(blocked_auth["id"]))
        assert blocked["state"]=="FAILED" and blocked["blocker"]==failure
        assert [kind for kind,_ in provider.operations[before:]]==[
            CloudOperationKind.PREPARE_WATT_DEPLOYMENT_HOST_V1,
            CloudOperationKind.CHECK_DEPLOYMENT_PREREQUISITES]
    for port, observed, expected in (
        (9092, InvocationResult("invoke-missing-user", "command-missing-user",
            "Invalid", None, "", "request-missing-user", "AccountNotExists",
            "The specified username does not exists: wattdeploy"),
            "DEPLOYMENT_USER_NOT_FOUND"),
        (9093, InvocationResult("invoke-provider-failed", "command-provider-failed",
            "Failed", None, "", "request-provider-failed", "GuestOSError",
            "token=must-not-persist"), "CLOUD_ASSISTANT_REPORTED_FAILURE"),
        (9094, InvocationResult("invoke-ambiguous", "command-ambiguous",
            "Success", 0, "no observed health token"),
            "CLOUD_OPERATION_UNVERIFIED"),
        (9095, InvocationResult("invoke-sensitive-code", "command-sensitive-code",
            "Failed", None, "", "request-sensitive-code",
            "AccessKeySecret-must-not-persist", "token=must-not-persist"),
            "CLOUD_ASSISTANT_REPORTED_FAILURE"),
    ):
        provider.precheck_result = observed
        blocked_auth = service.authorize(actor, work_id, request.model_copy(update={
            "expected_current_deployment_id": None, "port": port}))
        before = len(provider.operations)
        blocked = service.execute(actor, UUID(blocked_auth["id"]))
        assert blocked["state"] == "FAILED" and blocked["blocker"] == expected
        assert [kind for kind, _ in provider.operations[before:]] == [
            CloudOperationKind.PREPARE_WATT_DEPLOYMENT_HOST_V1,
            CloudOperationKind.CHECK_DEPLOYMENT_PREREQUISITES]
        assert len(blocked["operations"]) == 2
        receipt = blocked["operations"][1]
        assert receipt["output_summary"] == expected and not receipt["verified"]
        assert receipt["invocation_id"] == observed.invocation_id
        assert receipt["command_id"] == observed.command_id
        assert receipt["provider_request_id"] == observed.request_id
        assert "must-not-persist" not in str(blocked)
        if expected == "DEPLOYMENT_USER_NOT_FOUND":
            assert receipt["provider_error_code"] == "AccountNotExists"
            assert receipt["deployment_user"] == "wattdeploy"
            assert receipt["provider_error_info"] == (
                "Deployment user wattdeploy is missing on target ECS.")
        elif expected == "CLOUD_ASSISTANT_REPORTED_FAILURE":
            assert receipt["provider_error_code"] == (
                "GuestOSError" if port == 9093 else None)
            assert receipt["provider_error_info"] is None
    service.external_probe = lambda *_: False
    blocked_public_auth = service.authorize(actor, work_id,
        request.model_copy(update={"expected_current_deployment_id": None,
            "port": 9097}))
    blocked_public = service.execute(actor, UUID(blocked_public_auth["id"]))
    assert blocked_public["state"] == "NEEDS_HUMAN_ATTENTION"
    assert blocked_public["health_verified"] and not blocked_public["business_verified"]
    service.external_probe = lambda *_: True
    retry_auth = service.authorize(actor, work_id, request.model_copy(update={
        "expected_current_deployment_id": UUID(blocked_public["id"]),
        "port": 9097}))
    retried = service.execute(actor, UUID(retry_auth["id"]))
    assert retried["state"] == "SUCCEEDED" and retried["business_verified"]
    assert service.deployment(actor, UUID(blocked_public["id"]))["state"] == (
        "NEEDS_HUMAN_ATTENTION")
    before_ingress = len(provider.ingress_operations)
    service.external_probe = lambda *_: (_ for _ in ()).throw(
        AssertionError("PRIVATE deployment must not probe public HTTP"))
    private_auth = service.authorize(actor, work_id, request.model_copy(update={
        "expected_current_deployment_id": None, "port": 9096,
        "exposure_mode": "PRIVATE"}))
    private = service.execute(actor, UUID(private_auth["id"]))
    assert private["state"] == "SUCCEEDED" and private["health_verified"]
    assert not private["business_verified"]
    assert len(provider.ingress_operations) == before_ingress
    assert not any(row["kind"] in {"ENSURE_WATT_PUBLIC_INGRESS_V1",
        "VERIFY_PUBLIC_BUSINESS"} for row in private["operations"])
    with postgres_database.unit_of_work() as uow:
        persisted=str(uow.session.execute(select(cloud_connections.c.payload)).scalars().all())
        persisted+=str(uow.session.execute(select(cloud_delivery_authorizations.c.payload)).scalars().all())
        persisted+=str(uow.session.execute(select(cloud_deployments.c.payload)).scalars().all())
    for secret in ("temporary-id","temporary-secret","temporary-token",
                   "must-not-persist"):
        assert secret not in persisted
    assert "BLOCKED_UNKNOWN_PORT_OWNER" in persisted
    old_target = target.identity
    provider.target = target.model_copy(update={
        "instance_id": "i-newtarget1", "name": "Alibaba Cloud Linux ECS",
        "os_name": "Alibaba Cloud Linux 3"})
    rediscovered = service.verify_role(actor, UUID(first["id"]), role)
    assert rediscovered["id"] == first["id"]
    assert rediscovered["target"] is None
    assert rediscovered["target_grant_verified_at"] is None
    with pytest.raises(CloudDeliveryError, match="EXACT_CONNECTION_NOT_READY"):
        service.execute(actor, UUID(authorized["id"]))
    selected_new = service.select(actor, UUID(first["id"]),
        UUID(rediscovered["discovered_targets"][0]["selection_token"]))
    assert selected_new["target"]["instance_id"] == "i-newtarget1"
    assert selected_new["target_grant_verified_at"] is not None
    assert "i-newtarget1" not in str(selected_new["connection_policy"])
    verified_new = service.verify_target(actor, UUID(first["id"]))
    assert verified_new["state"] == "READY"
    with pytest.raises(CloudDeliveryError, match="EXACT_CONNECTION_NOT_READY"):
        service.execute(actor, UUID(authorized["id"]))
    with pytest.raises(CloudDeliveryError, match="AUTHORIZATION_TARGET_MISMATCH"):
        service.authorize(actor, work_id, request)
    assert service.deployment(actor, UUID(result["id"]))["target"]["instance_id"] == old_target[2]
    service.revoke(actor, UUID(first["id"]))
    with pytest.raises(CloudDeliveryError, match="CONNECTION_NOT_USABLE"):
        service.authorize(actor, work_id, request)
    with postgres_database.engine.begin() as connection:
        connection.execute(text("TRUNCATE cloud_deployments, cloud_delivery_authorizations, "
            "cloud_prepared_artifacts, cloud_connections CASCADE"))
