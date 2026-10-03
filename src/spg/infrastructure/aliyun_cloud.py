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
from spg.infrastructure.cloud_delivery_network import (
    CloudNetworkError, EnsureWattPublicIngressV1, IngressResult,
    RevokeWattPublicIngressV1,
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

    def _selected_security_group(self, session: TemporaryCloudSession,
                                 target: CloudTarget) -> str:
        """The caller never supplies a security group; resolve it from the exact ECS."""
        from alibabacloud_ecs20140526 import models
        client = self._ecs_client(session, target.region_id)
        try:
            body = self._body(client.describe_instances(models.DescribeInstancesRequest(
                region_id=target.region_id,
                instance_ids=json.dumps([target.instance_id]))))
            rows = body["Instances"]["Instance"]
            if len(rows) != 1 or rows[0].get("InstanceId") != target.instance_id:
                raise CloudNetworkError("EXACT_TARGET_CHANGED")
            groups = rows[0].get("SecurityGroupIds", {}).get("SecurityGroupId", [])
            if (not isinstance(groups, list) or len(groups) != 1 or
                    not re.fullmatch(r"sg-[A-Za-z0-9]{6,64}", groups[0])):
                raise CloudNetworkError("SECURITY_GROUP_SELECTION_AMBIGUOUS")
            group = groups[0]
            listed = self._body(client.describe_security_groups(
                models.DescribeSecurityGroupsRequest(region_id=target.region_id,
                    security_group_ids=json.dumps([group]))))
            matches = listed.get("SecurityGroups", {}).get("SecurityGroup", [])
            if len(matches) != 1 or matches[0].get("SecurityGroupId") != group:
                raise CloudNetworkError("EXACT_SECURITY_GROUP_NOT_VERIFIED")
            return group
        except CloudNetworkError:
            raise
        except Exception as error:
            raise CloudProviderError("SECURITY_GROUP_DISCOVERY_FAILED") from error

    def _ingress_rules(self, session: TemporaryCloudSession, target: CloudTarget,
                       group: str) -> tuple[dict, ...]:
        from alibabacloud_ecs20140526 import models
        client = self._ecs_client(session, target.region_id)
        found, token = [], None
        try:
            for _ in range(10):
                body = self._body(client.describe_security_group_attribute(
                    models.DescribeSecurityGroupAttributeRequest(
                        region_id=target.region_id, security_group_id=group,
                        direction="ingress", max_results=1000, next_token=token)))
                if body.get("SecurityGroupId") != group or body.get(
                        "RegionId", target.region_id) != target.region_id:
                    raise CloudNetworkError("EXACT_SECURITY_GROUP_NOT_VERIFIED")
                rules = body.get("Permissions", {}).get("Permission", [])
                if not isinstance(rules, list):
                    raise CloudNetworkError("SECURITY_GROUP_RULES_UNVERIFIED")
                found.extend(rules)
                if len(found) > 10_000:
                    raise CloudNetworkError("SECURITY_GROUP_RULES_UNVERIFIED")
                next_token = body.get("NextToken") or None
                if not next_token:
                    return tuple(found)
                if next_token == token:
                    raise CloudNetworkError("SECURITY_GROUP_RULES_UNVERIFIED")
                token = next_token
            raise CloudNetworkError("SECURITY_GROUP_RULES_UNVERIFIED")
        except CloudNetworkError:
            raise
        except Exception as error:
            raise CloudProviderError("SECURITY_GROUP_RULE_READ_FAILED") from error

    @staticmethod
    def _exact_public_rule(rule: dict, port: int) -> bool:
        return (str(rule.get("Direction", "")).lower() == "ingress" and
            str(rule.get("IpProtocol", "")).lower() == "tcp" and
            str(rule.get("Policy", "")).lower() == "accept" and
            rule.get("PortRange") == f"{port}/{port}" and
            rule.get("SourceCidrIp") == "0.0.0.0/0" and
            not any(rule.get(key) for key in ("SourceGroupId", "SourcePrefixListId",
                "Ipv6SourceCidrIp", "PortRangeListId")) and
            rule.get("SourcePortRange") in (None, "", "-1/-1"))

    def ensure_public_ingress(self, session: TemporaryCloudSession,
                              operation: EnsureWattPublicIngressV1) -> IngressResult:
        from alibabacloud_ecs20140526 import models
        if type(operation) is not EnsureWattPublicIngressV1:
            raise CloudNetworkError("UNSUPPORTED_NETWORK_OPERATION")
        target, port = operation.target, operation.port
        group = self._selected_security_group(session, target)
        before = self._ingress_rules(session, target, group)
        exact = [rule for rule in before if self._exact_public_rule(rule, port)]
        if exact:
            rule = sorted(exact, key=lambda item: str(item.get("SecurityGroupRuleId", "")))[0]
            rule_id = rule.get("SecurityGroupRuleId")
            if not isinstance(rule_id, str) or not re.fullmatch(
                    r"sgr-[A-Za-z0-9]{6,64}", rule_id):
                raise CloudNetworkError("SECURITY_GROUP_RULES_UNVERIFIED")
            return IngressResult(group, rule_id, "",
                "REUSED", None, True)
        client = self._ecs_client(session, target.region_id)
        try:
            response = self._body(client.authorize_security_group(
                models.AuthorizeSecurityGroupRequest(region_id=target.region_id,
                    security_group_id=group,
                    client_token=f"WattIngressV1-{operation.deployment_id.hex}",
                    permissions=[models.AuthorizeSecurityGroupRequestPermissions(
                        ip_protocol="TCP", port_range=f"{port}/{port}",
                        source_cidr_ip="0.0.0.0/0", policy="accept", priority="1",
                        description=operation.description)])))
        except Exception as error:
            raise CloudProviderError("PUBLIC_INGRESS_CREATE_FAILED") from error
        after = self._ingress_rules(session, target, group)
        created = [rule for rule in after if self._exact_public_rule(rule, port) and
            rule.get("Description") == operation.description]
        if len(created) != 1 or not re.fullmatch(r"sgr-[A-Za-z0-9]{6,64}",
                str(created[0].get("SecurityGroupRuleId", ""))):
            raise CloudNetworkError("PUBLIC_INGRESS_UNVERIFIED")
        return IngressResult(group, created[0]["SecurityGroupRuleId"],
            operation.description, "CREATED", response.get("RequestId"), True)

    def revoke_public_ingress(self, session: TemporaryCloudSession,
                              operation: RevokeWattPublicIngressV1) -> IngressResult:
        from alibabacloud_ecs20140526 import models
        if type(operation) is not RevokeWattPublicIngressV1:
            raise CloudNetworkError("UNSUPPORTED_NETWORK_OPERATION")
        target, receipt = operation.target, operation.creation_receipt
        group = self._selected_security_group(session, target)
        if group != receipt.security_group_id:
            raise CloudNetworkError("EXACT_SECURITY_GROUP_CHANGED")
        matches = [rule for rule in self._ingress_rules(session, target, group)
            if rule.get("SecurityGroupRuleId") == receipt.security_group_rule_id]
        if (len(matches) != 1 or not self._exact_public_rule(matches[0], operation.port)
                or matches[0].get("Description") != receipt.network_rule_description):
            raise CloudNetworkError("WATT_CREATED_RULE_REALITY_CHANGED")
        try:
            response = self._body(self._ecs_client(session, target.region_id)
                .revoke_security_group(models.RevokeSecurityGroupRequest(
                    region_id=target.region_id, security_group_id=group,
                    security_group_rule_id=[receipt.security_group_rule_id],
                    client_token=f"WattRevokeV1-{operation.deployment_id.hex}")))
        except Exception as error:
            raise CloudProviderError("PUBLIC_INGRESS_REVOKE_FAILED") from error
        if any(rule.get("SecurityGroupRuleId") == receipt.security_group_rule_id
                for rule in self._ingress_rules(session, target, group)):
            raise CloudNetworkError("PUBLIC_INGRESS_REVOKE_UNVERIFIED")
        return IngressResult(group, receipt.security_group_rule_id,
            receipt.network_rule_description, "REVOKED", response.get("RequestId"), True)

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
