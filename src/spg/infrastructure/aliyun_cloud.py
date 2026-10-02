"""Alibaba SDK adapter; customer STS tokens and signed URLs stay in memory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path
import re
from time import monotonic, sleep

from spg.domain.cloud_delivery import CloudTarget
from spg.infrastructure.cloud_delivery_commands import (
    CloudCommand, PrepareDeploymentHostV1, CheckPrerequisites, compile_operation,
)


class CloudProviderError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, repr=False)
class TemporaryCloudSession:
    access_key_id: str
    access_key_secret: str
    security_token: str


@dataclass(frozen=True, repr=False)
class StagedCloudArtifact:
    object_key: str
    digest: str
    signed_url: str
    request_id: str | None = None


@dataclass(frozen=True, repr=False)
class InvocationResult:
    invocation_id: str
    command_id: str
    status: str
    exit_code: int | None
    output: str
    request_id: str | None = None
    error_code: str | None = None
    error_info: str | None = None


class AliyunCloudProvider:
    """Only the audited STS, ECS, and Watt-owned OSS operations used by Delivery."""

    def __init__(self, settings):
        self.settings = settings

    def _service_keys(self) -> tuple[str, str]:
        key, secret = self.settings.aliyun_access_key_id, self.settings.aliyun_access_key_secret
        if key is None or secret is None or not key.get_secret_value() or not secret.get_secret_value():
            raise CloudProviderError("SERVICE_IDENTITY_REQUIRED")
        return key.get_secret_value(), secret.get_secret_value()

    @staticmethod
    def _sts_client(key: str, secret: str, token: str | None = None):
        from alibabacloud_sts20150401.client import Client
        from alibabacloud_tea_openapi.models import Config
        return Client(Config(access_key_id=key, access_key_secret=secret,
            security_token=token, endpoint="sts.aliyuncs.com", protocol="HTTPS",
            connect_timeout=5000, read_timeout=10000))

    @staticmethod
    def _ecs_client(session: TemporaryCloudSession, region: str):
        from alibabacloud_ecs20140526.client import Client
        from alibabacloud_tea_openapi.models import Config
        if not re.fullmatch(r"[a-z]{2}-[a-z0-9-]{2,48}", region):
            raise CloudProviderError("INVALID_REGION")
        return Client(Config(access_key_id=session.access_key_id,
            access_key_secret=session.access_key_secret, security_token=session.security_token,
            endpoint=f"ecs.{region}.aliyuncs.com", protocol="HTTPS",
            connect_timeout=5000, read_timeout=15000))

    @staticmethod
    def _body(response) -> dict:
        body = response.body.to_map()
        if not isinstance(body, dict):
            raise CloudProviderError("PROVIDER_PROTOCOL_ERROR")
        return body

    def service_identity(self) -> dict:
        try:
            key, secret = self._service_keys()
            return self._body(self._sts_client(key, secret).get_caller_identity())
        except CloudProviderError:
            raise
        except Exception as error:
            raise CloudProviderError("SERVICE_IDENTITY_UNAVAILABLE") from error

    def assume_role(self, role_arn: str, external_id: str) -> TemporaryCloudSession:
        from alibabacloud_sts20150401 import models
        try:
            key, secret = self._service_keys()
            response = self._body(self._sts_client(key, secret).assume_role(
                models.AssumeRoleRequest(role_arn=role_arn, external_id=external_id,
                    role_session_name="WattDelivery", duration_seconds=900)))
            issued = response["Credentials"]
            return TemporaryCloudSession(issued["AccessKeyId"],
                issued["AccessKeySecret"], issued["SecurityToken"])
        except CloudProviderError:
            raise
        except Exception as error:
            raise CloudProviderError("ROLE_ASSUMPTION_FAILED") from error

    def assumed_identity(self, session: TemporaryCloudSession) -> dict:
        try:
            return self._body(self._sts_client(session.access_key_id,
                session.access_key_secret, session.security_token).get_caller_identity())
        except Exception as error:
            raise CloudProviderError("ASSUMED_IDENTITY_UNAVAILABLE") from error

    def regions(self, session: TemporaryCloudSession) -> tuple[str, ...]:
        from alibabacloud_ecs20140526 import models
        try:
            body = self._body(self._ecs_client(session, "cn-hangzhou").describe_regions(
                models.DescribeRegionsRequest(resource_type="instance")))
            rows = body["Regions"]["Region"]
            if not isinstance(rows, list) or len(rows) > 100:
                raise CloudProviderError("PROVIDER_PROTOCOL_ERROR")
            return tuple(row["RegionId"] for row in rows if re.fullmatch(
                r"[a-z]{2}-[a-z0-9-]{2,48}", row.get("RegionId", "")))
        except CloudProviderError:
            raise
        except Exception as error:
            raise CloudProviderError("REGION_DISCOVERY_FAILED") from error

    def instances(self, session: TemporaryCloudSession, account_id: str,
                  region: str) -> tuple[CloudTarget, ...]:
        from alibabacloud_ecs20140526 import models
        try:
            client = self._ecs_client(session, region)
            found = []
            for page in range(1, 11):
                body = self._body(client.describe_instances(models.DescribeInstancesRequest(
                    region_id=region, page_number=page, page_size=100)))
                rows = body["Instances"]["Instance"]
                if not isinstance(rows, list):
                    raise CloudProviderError("PROVIDER_PROTOCOL_ERROR")
                found.extend(rows)
                if len(rows) < 100:
                    break
                if page == 10:
                    raise CloudProviderError("DISCOVERY_LIMIT_EXCEEDED")
            if len(found) > 1000:
                raise CloudProviderError("DISCOVERY_LIMIT_EXCEEDED")
            result = []
            for row in found:
                instance_id = row["InstanceId"]
                ca = self._body(client.describe_cloud_assistant_status(
                    models.DescribeCloudAssistantStatusRequest(region_id=region,
                        instance_id=[instance_id])))
                states = ca.get("InstanceCloudAssistantStatusSet", {}).get(
                    "InstanceCloudAssistantStatus", [])
                ready = bool(states and str(states[0].get("CloudAssistantStatus", "")).lower() == "true")
                addresses = row.get("PublicIpAddress", {}).get("IpAddress", [])
                public_address = (addresses[0] if addresses else
                    row.get("EipAddress", {}).get("IpAddress"))
                result.append(CloudTarget(account_id=account_id, region_id=region,
                    instance_id=instance_id, name=row.get("InstanceName") or instance_id,
                    os_name=row.get("OSName") or row.get("OSType") or "unknown",
                    os_type=(states[0].get("OSType") if states else None) or
                        row.get("OSType") or "Unknown",
                    status=row.get("Status") or "Unknown",
                    public_address=public_address,
                    cloud_assistant_ready=ready))
            return tuple(result)
        except CloudProviderError:
            raise
        except Exception as error:
            raise CloudProviderError("INSTANCE_DISCOVERY_FAILED") from error

    def exact_instance(self, session: TemporaryCloudSession, target: CloudTarget) -> CloudTarget:
        from alibabacloud_ecs20140526 import models
        try:
            client = self._ecs_client(session, target.region_id)
            body = self._body(client.describe_instances(models.DescribeInstancesRequest(
                region_id=target.region_id, instance_ids=json.dumps([target.instance_id]))))
            rows = body["Instances"]["Instance"]
            if len(rows) != 1 or rows[0].get("InstanceId") != target.instance_id:
                raise CloudProviderError("TARGET_MISSING")
            ca = self._body(client.describe_cloud_assistant_status(
                models.DescribeCloudAssistantStatusRequest(region_id=target.region_id,
                    instance_id=[target.instance_id])))
            states = ca.get("InstanceCloudAssistantStatusSet", {}).get("InstanceCloudAssistantStatus", [])
            ready = bool(states and str(states[0].get("CloudAssistantStatus", "")).lower() == "true")
            row = rows[0]
            addresses = row.get("PublicIpAddress", {}).get("IpAddress", [])
            public_address = (addresses[0] if addresses else
                row.get("EipAddress", {}).get("IpAddress"))
            return CloudTarget(account_id=target.account_id, region_id=target.region_id,
                instance_id=target.instance_id, name=row.get("InstanceName") or target.name,
                os_name=row.get("OSName") or row.get("OSType") or target.os_name,
                os_type=(states[0].get("OSType") if states else None) or
                    row.get("OSType") or "Unknown",
                status=row.get("Status") or "Unknown",
                public_address=public_address,
                cloud_assistant_ready=ready)
        except CloudProviderError:
            raise
        except Exception as error:
            raise CloudProviderError("TARGET_OBSERVATION_FAILED") from error

    def target_grant_dry_run(self, session: TemporaryCloudSession,
                             target: CloudTarget) -> None:
        from alibabacloud_ecs20140526 import models
        try:
            for operation in (PrepareDeploymentHostV1(), CheckPrerequisites(8080)):
                _, script = compile_operation(operation)
                username = "root" if type(operation) is PrepareDeploymentHostV1 else "wattdeploy"
                self._ecs_client(session, target.region_id).run_command(
                    models.RunCommandRequest(region_id=target.region_id,
                        instance_id=[target.instance_id], type="RunShellScript",
                        command_content=script, username=username,
                        working_dir="/root" if username == "root" else "/home/wattdeploy",
                        keep_command=False, repeat_mode="DryRun", timeout=30))
        except Exception as error:
            raise CloudProviderError("CONNECTION_EXECUTION_GRANT_REQUIRED") from error

    def run(self, session: TemporaryCloudSession, target: CloudTarget,
            operation: CloudCommand, client_token: str) -> InvocationResult:
        """Compile only the exact closed operation union, never caller script text."""
        from alibabacloud_ecs20140526 import models
        _, script = compile_operation(operation)
        username = "root" if type(operation) is PrepareDeploymentHostV1 else "wattdeploy"
        if len(script.encode()) > 16_000:
            raise CloudProviderError("COMMAND_SIZE_EXCEEDED")
        client = self._ecs_client(session, target.region_id)
        try:
            body = self._body(client.run_command(models.RunCommandRequest(
                region_id=target.region_id, instance_id=[target.instance_id],
                type="RunShellScript", command_content=script, username=username,
                working_dir="/root" if username == "root" else f"/home/{username}",
                keep_command=False, repeat_mode="Once", timeout=600,
                client_token=client_token)))
            invoke_id, command_id = body["InvokeId"], body["CommandId"]
            request_id = body.get("RequestId")
            deadline = monotonic() + 660
            while monotonic() < deadline:
                result = self._body(client.describe_invocation_results(
                    models.DescribeInvocationResultsRequest(region_id=target.region_id,
                        instance_id=target.instance_id, invoke_id=invoke_id,
                        command_id=command_id, content_encoding="PlainText")))
                rows = result.get("Invocation", {}).get("InvocationResults", {}).get(
                    "InvocationResult", [])
                if rows:
                    row = rows[0]
                    status = row.get("InvocationStatus", "Unknown")
                    if status in {"Success", "Failed", "Error", "Timeout", "Cancelled",
                                  "Aborted", "Invalid", "Terminated"}:
                        return InvocationResult(invoke_id, command_id, status,
                            row.get("ExitCode"), str(row.get("Output") or "")[:24000],
                            request_id,
                            None if row.get("ErrorCode") is None else
                                str(row["ErrorCode"])[:256],
                            None if row.get("ErrorInfo") is None else
                                str(row["ErrorInfo"])[:4096])
                sleep(2)
            raise CloudProviderError("INVOCATION_TIMEOUT")
        except CloudProviderError:
            raise
        except Exception as error:
            raise CloudProviderError("INVOCATION_FAILED") from error

    def stage(self, archive: Path, expected_digest: str) -> StagedCloudArtifact:
        import alibabacloud_oss_v2 as oss
        bucket, region = self.settings.aliyun_oss_bucket, self.settings.aliyun_oss_region
        if not bucket or not region:
            raise CloudProviderError("STAGING_NOT_CONFIGURED")
        try:
            key, secret = self._service_keys()
            config = oss.config.load_default()
            config.credentials_provider = oss.credentials.StaticCredentialsProvider(key, secret)
            config.region = region
            client = oss.Client(config)
            digest = sha256()
            with archive.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected_digest:
                raise CloudProviderError("ARTIFACT_DIGEST_CHANGED")
            object_key = f"watt-delivery/sha256/{expected_digest}.tar"
            with archive.open("rb") as stream:
                uploaded = client.put_object(oss.PutObjectRequest(bucket=bucket, key=object_key,
                    body=stream, content_length=archive.stat().st_size,
                    content_type="application/x-tar", object_acl="private",
                    metadata={"sha256": expected_digest}))
            url = client.presign(oss.GetObjectRequest(bucket=bucket, key=object_key),
                expires=timedelta(minutes=5)).url
            if not url.startswith("https://"):
                raise CloudProviderError("SIGNED_URL_NOT_HTTPS")
            return StagedCloudArtifact(object_key, expected_digest, url,
                getattr(uploaded, "request_id", None))
        except CloudProviderError:
            raise
        except Exception as error:
            raise CloudProviderError("STAGING_FAILED") from error
