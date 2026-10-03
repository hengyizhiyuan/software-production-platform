"""Exact public ingress must be derived from ECS Reality and Delivery authority."""

from datetime import UTC, datetime
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.application.cloud_delivery import CloudDeliveryService, _has_public_ipv4
from spg.domain.cloud_delivery import (
    CloudDeliveryAuthorization, CloudExposureMode, CloudOperationKind,
    CloudOperationReceipt, CloudTarget,
)
from spg.infrastructure.aliyun_cloud import AliyunCloudProvider, TemporaryCloudSession
from spg.infrastructure.cloud_delivery_network import (
    CloudNetworkError, EnsureWattPublicIngressV1, RevokeWattPublicIngressV1,
)


def _response(payload):
    return SimpleNamespace(body=SimpleNamespace(to_map=lambda: payload))


class FakeEcs:
    def __init__(self, target, rules=()):
        self.target, self.rules, self.mutations = target, list(rules), []

    def describe_instances(self, _request):
        return _response({"Instances": {"Instance": [{
            "InstanceId": self.target.instance_id,
            "SecurityGroupIds": {"SecurityGroupId": ["sg-abcdefgh"]}}]}})

    def describe_security_groups(self, _request):
        return _response({"SecurityGroups": {"SecurityGroup": [
            {"SecurityGroupId": "sg-abcdefgh"}]}})

    def describe_security_group_attribute(self, _request):
        return _response({"SecurityGroupId": "sg-abcdefgh",
            "RegionId": self.target.region_id,
            "Permissions": {"Permission": list(self.rules)}, "NextToken": ""})

    def authorize_security_group(self, request):
        assert request.security_group_id == "sg-abcdefgh"
        assert len(request.permissions) == 1
        item = request.permissions[0]
        assert (item.ip_protocol, item.port_range, item.source_cidr_ip,
            item.policy, item.priority) == ("TCP", "8080/8080", "0.0.0.0/0",
            "accept", "1")
        self.mutations.append(("authorize", request.security_group_id))
        self.rules.append(_rule("sgr-created1", item.description))
        return _response({"RequestId": "create-request"})

    def revoke_security_group(self, request):
        assert request.security_group_id == "sg-abcdefgh"
        assert request.security_group_rule_id == ["sgr-created1"]
        self.mutations.append(("revoke", request.security_group_rule_id[0]))
        self.rules = [rule for rule in self.rules if
            rule["SecurityGroupRuleId"] != request.security_group_rule_id[0]]
        return _response({"RequestId": "revoke-request"})


def _rule(rule_id, description, port="8080/8080"):
    return {"SecurityGroupRuleId": rule_id, "Direction": "ingress",
        "IpProtocol": "TCP", "Policy": "Accept", "PortRange": port,
        "SourceCidrIp": "0.0.0.0/0", "Description": description}


@pytest.fixture
def authority():
    target = CloudTarget(account_id="1234567890123456", region_id="cn-hongkong",
        instance_id="i-abcdefgh", name="chosen", os_name="Alibaba Cloud Linux 3",
        status="Running", cloud_assistant_ready=True)
    authorization = CloudDeliveryAuthorization(id=uuid4(), work_id=uuid4(),
        product_id=uuid4(), actor_id="human:owner", connection_id=uuid4(),
        manifest_id=uuid4(), manifest_fingerprint="a" * 64,
        artifact_sha256="b" * 64, candidate_revision="c" * 40,
        target=target, port=8080, exposure_mode=CloudExposureMode.PUBLIC,
        rationale="public delivery", authorized_at=datetime.now(UTC))
    return authorization, target


def _provider(target, rules=()):
    provider = AliyunCloudProvider(SimpleNamespace())
    client = FakeEcs(target, rules)
    provider._ecs_client = lambda _session, _region: client
    session = TemporaryCloudSession("id", "secret", "token")
    return provider, client, session


def test_existing_exact_rule_is_reused_and_other_rules_are_untouched(authority):
    authorization, target = authority
    rules = [_rule("sgr-existing1", "owned by customer"),
        _rule("sgr-unrelated", "SSH rule", "22/22")]
    provider, client, session = _provider(target, rules)
    operation = EnsureWattPublicIngressV1(authorization, uuid4(), target, 8080)
    result = provider.ensure_public_ingress(session, operation)
    assert (result.effect, result.rule_id, result.verified) == (
        "REUSED", "sgr-existing1", True)
    assert client.mutations == [] and client.rules == rules


def test_exact_rule_created_verified_and_only_evidenced_rule_revoked(authority):
    authorization, target = authority
    unrelated = _rule("sgr-unrelated", "SSH rule", "22/22")
    provider, client, session = _provider(target, [unrelated])
    deployment_id = uuid4()
    operation = EnsureWattPublicIngressV1(authorization, deployment_id, target, 8080)
    result = provider.ensure_public_ingress(session, operation)
    assert result.effect == "CREATED" and result.verified
    assert result.description == operation.description
    assert client.rules[0] == unrelated
    receipt = CloudOperationReceipt(kind=CloudOperationKind.ENSURE_WATT_PUBLIC_INGRESS_V1,
        account_id=target.account_id, region_id=target.region_id,
        instance_id=target.instance_id, security_group_id=result.security_group_id,
        security_group_rule_id=result.rule_id,
        network_rule_description=result.description, network_effect=result.effect,
        started_at=datetime.now(UTC), finished_at=datetime.now(UTC),
        status="OBSERVED", output_summary="WATT_PUBLIC_INGRESS_CREATED", verified=True)
    revoked = provider.revoke_public_ingress(session, RevokeWattPublicIngressV1(
        authorization, deployment_id, target, 8080, receipt))
    assert revoked.effect == "REVOKED" and revoked.verified
    assert client.rules == [unrelated]
    assert client.mutations == [("authorize", "sg-abcdefgh"),
        ("revoke", "sgr-created1")]


def test_arbitrary_target_port_or_unowned_rule_cannot_be_mutated(authority):
    authorization, target = authority
    deployment_id = uuid4()
    wrong_target = target.model_copy(update={"instance_id": "i-wrong123"})
    with pytest.raises(CloudNetworkError, match="PUBLIC_INGRESS_AUTHORITY_MISMATCH"):
        EnsureWattPublicIngressV1(authorization, deployment_id, wrong_target, 8080)
    with pytest.raises(CloudNetworkError, match="PUBLIC_INGRESS_AUTHORITY_MISMATCH"):
        EnsureWattPublicIngressV1(authorization, deployment_id, target, 9090)
    private = authorization.model_copy(update={"exposure_mode": CloudExposureMode.PRIVATE})
    with pytest.raises(CloudNetworkError, match="PUBLIC_INGRESS_AUTHORITY_MISMATCH"):
        EnsureWattPublicIngressV1(private, deployment_id, target, 8080)
    reused = CloudOperationReceipt(kind=CloudOperationKind.ENSURE_WATT_PUBLIC_INGRESS_V1,
        account_id=target.account_id, region_id=target.region_id,
        instance_id=target.instance_id, security_group_id="sg-abcdefgh",
        security_group_rule_id="sgr-existing1",
        network_rule_description="owned by customer", network_effect="REUSED",
        started_at=datetime.now(UTC), finished_at=datetime.now(UTC),
        status="OBSERVED", output_summary="WATT_PUBLIC_INGRESS_REUSED", verified=True)
    with pytest.raises(CloudNetworkError, match="WATT_CREATED_RULE_EVIDENCE_REQUIRED"):
        RevokeWattPublicIngressV1(authorization, deployment_id, target, 8080, reused)


def test_multiple_or_unverified_security_groups_fail_before_mutation(authority):
    authorization, target = authority
    provider, client, session = _provider(target)
    client.describe_instances = lambda _request: _response({"Instances": {
        "Instance": [{"InstanceId": target.instance_id,
            "SecurityGroupIds": {"SecurityGroupId": [
                "sg-abcdefgh", "sg-other123"]}}]}})
    with pytest.raises(CloudNetworkError, match="SECURITY_GROUP_SELECTION_AMBIGUOUS"):
        provider.ensure_public_ingress(session, EnsureWattPublicIngressV1(
            authorization, uuid4(), target, 8080))
    assert client.mutations == []


def test_public_business_verification_requires_real_http_body_match(monkeypatch):
    body = b"qualified public body"
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *_):
            pass
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    class TestAddress:
        is_global = True
        def __str__(self):
            return "127.0.0.1"
    monkeypatch.setattr("spg.application.cloud_delivery.ip_address",
        lambda _value: TestAddress())
    target = SimpleNamespace(public_address="127.0.0.1")
    try:
        assert CloudDeliveryService._external_probe(target, server.server_port,
            sha256(body).hexdigest())
        assert not CloudDeliveryService._external_probe(target, server.server_port,
            sha256(b"different").hexdigest())
    finally:
        server.shutdown()
        server.server_close()


def test_public_mode_requires_a_current_public_ipv4_address():
    assert _has_public_ipv4(SimpleNamespace(public_address="47.243.29.212"))
    assert not _has_public_ipv4(SimpleNamespace(public_address=None))
    assert not _has_public_ipv4(SimpleNamespace(public_address="127.0.0.1"))
