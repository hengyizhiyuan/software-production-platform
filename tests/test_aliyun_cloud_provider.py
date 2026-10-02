"""Alibaba SDK request-shape tests; no live network or credentials."""

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import SecretStr

from spg.config import Settings
from spg.domain.cloud_delivery import CloudTarget
from spg.infrastructure.aliyun_cloud import AliyunCloudProvider, CloudProviderError
from spg.infrastructure.cloud_delivery_commands import CheckPrerequisites, PrepareDeploymentHostV1


class Response:
    def __init__(self, payload):
        self.body = self
        self.payload = payload

    def to_map(self):
        return self.payload


def test_sts_assume_role_passes_exact_role_and_external_id(monkeypatch):
    calls = []
    class STS:
        def get_caller_identity(self):
            return Response({"AccountId": "1111111111111111",
                "Arn": "acs:ram::1111111111111111:user/watt-service"})
        def assume_role(self, request):
            calls.append(request)
            return Response({"Credentials": {"AccessKeyId": "temporary-id",
                "AccessKeySecret": "temporary-secret", "SecurityToken": "temporary-token"}})
    monkeypatch.setattr(AliyunCloudProvider, "_sts_client",
        staticmethod(lambda *_: STS()))
    provider=AliyunCloudProvider(Settings(aliyun_access_key_id=SecretStr("service-id"),
        aliyun_access_key_secret=SecretStr("service-secret")))
    assert provider.service_identity()["AccountId"] == "1111111111111111"
    session=provider.assume_role("acs:ram::1234567890123456:role/WattECSDelivery",
        "unique-external-id")
    assert calls[0].role_arn == "acs:ram::1234567890123456:role/WattECSDelivery"
    assert calls[0].external_id == "unique-external-id"
    assert "temporary-secret" not in repr(session)


def test_ecs_discovery_dry_run_and_typed_invocation(monkeypatch):
    calls=[]
    class ECS:
        def describe_regions(self, request):
            return Response({"Regions":{"Region":[{"RegionId":"cn-hangzhou"}]}})
        def describe_instances(self, request):
            return Response({"Instances":{"Instance":[{"InstanceId":"i-abcdefgh",
                "InstanceName":"官网生产环境","OSName":"Alibaba Cloud Linux",
                "OSType":"linux","Status":"Running",
                "PublicIpAddress":{"IpAddress":["203.0.113.10"]}}]}})
        def describe_cloud_assistant_status(self, request):
            return Response({"InstanceCloudAssistantStatusSet":{
                "InstanceCloudAssistantStatus":[{"CloudAssistantStatus":"true",
                    "OSType":"Linux"}]}})
        def run_command(self, request):
            calls.append(request)
            return Response({"InvokeId":"invoke-exact","CommandId":"command-exact"})
        def describe_invocation_results(self, request):
            assert request.invoke_id == "invoke-exact"
            assert request.instance_id == "i-abcdefgh"
            return Response({"Invocation":{"InvocationResults":{
                "InvocationResult":[{"InvocationStatus":"Success",
                    "ExitCode":0,"Output":"WATT_PRECHECK_OK"}]}}})
    monkeypatch.setattr(AliyunCloudProvider, "_ecs_client",
        staticmethod(lambda *_: ECS()))
    provider=AliyunCloudProvider(Settings())
    session=object()
    assert provider.regions(session)==("cn-hangzhou",)
    target=provider.instances(session,"1234567890123456","cn-hangzhou")[0]
    assert target.identity == ("1234567890123456","cn-hangzhou","i-abcdefgh")
    assert target.os_type == "Linux" and target.cloud_assistant_ready
    assert provider.exact_instance(session,target).identity==target.identity
    provider.target_grant_dry_run(session,target)
    assert calls[0].repeat_mode == "DryRun"
    assert [calls[0].username, calls[1].username] == ["root", "wattdeploy"]
    assert calls[1].working_dir == "/home/wattdeploy"
    assert calls[0].keep_command is False
    observed=provider.run(session,target,CheckPrerequisites(8080),uuid4().hex)
    assert observed.invocation_id=="invoke-exact" and observed.exit_code==0
    assert calls[2].repeat_mode == "Once"
    assert "BLOCKED_ROOTLESS_DOCKER_REQUIRED" in calls[2].command_content
    assert calls[2].username == "wattdeploy"
    assert calls[2].working_dir == "/home/wattdeploy"
    provider.run(session,target,PrepareDeploymentHostV1(),uuid4().hex)
    assert calls[3].username == "root"
    assert calls[3].working_dir == calls[0].working_dir == "/root"
    assert "WATT_EFFECT_USER_CREATED" in calls[3].command_content


def test_invalid_invocation_keeps_provider_reason_transiently(monkeypatch):
    class ECS:
        def run_command(self, _request):
            return Response({"InvokeId":"invoke-exact", "CommandId":"command-exact",
                "RequestId":"request-exact"})

        def describe_invocation_results(self, request):
            assert request.invoke_id == "invoke-exact"
            assert request.command_id == "command-exact"
            return Response({"Invocation":{"InvocationResults":{"InvocationResult":[{
                "InvocationStatus":"Invalid", "ExitCode":None, "Output":"",
                "ErrorCode":"AccountNotExists",
                "ErrorInfo":"The specified username does not exists: wattdeploy"
            }]}}})

    monkeypatch.setattr(AliyunCloudProvider, "_ecs_client",
        staticmethod(lambda *_: ECS()))
    target=CloudTarget(account_id="1234567890123456", region_id="cn-hangzhou",
        instance_id="i-abcdefgh", name="test", os_name="Linux", os_type="Linux",
        status="Running", cloud_assistant_ready=True)
    result=AliyunCloudProvider(Settings()).run(object(), target,
        CheckPrerequisites(8080), uuid4().hex)
    assert result.status == "Invalid" and result.exit_code is None
    assert result.error_code == "AccountNotExists"
    assert result.error_info == "The specified username does not exists: wattdeploy"
    assert result.request_id == "request-exact"
    assert "wattdeploy" not in repr(result)


def test_oss_staging_checks_digest_and_keeps_signed_url_transient(monkeypatch,tmp_path):
    import alibabacloud_oss_v2 as oss
    uploaded=[]
    class Client:
        def __init__(self, config):
            assert config.region == "cn-hangzhou"
        def put_object(self, request):
            uploaded.append((request.key,request.acl,request.body.read()))
        def presign(self, request, expires):
            assert expires.total_seconds()==300
            return SimpleNamespace(url="https://private.example.invalid/signed?token=secret")
    monkeypatch.setattr(oss.config,"load_default",lambda:SimpleNamespace())
    monkeypatch.setattr(oss,"Client",Client)
    settings=Settings(aliyun_access_key_id=SecretStr("service-id"),
        aliyun_access_key_secret=SecretStr("service-secret"),
        aliyun_oss_bucket="watt-private-stage", aliyun_oss_region="cn-hangzhou")
    provider=AliyunCloudProvider(settings)
    archive=tmp_path/"image.tar";archive.write_bytes(b"exact archive")
    digest=sha256(archive.read_bytes()).hexdigest()
    with pytest.raises(CloudProviderError, match="ARTIFACT_DIGEST_CHANGED"):
        provider.stage(archive,"0"*64)
    staged=provider.stage(archive,digest)
    assert uploaded==[(f"watt-delivery/sha256/{digest}.tar","private",b"exact archive")]
    assert staged.digest==digest
    assert "secret" not in repr(staged)
