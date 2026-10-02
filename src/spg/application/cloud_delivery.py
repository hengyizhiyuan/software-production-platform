"""Governed Alibaba ECS Delivery on the existing exact Delivery manifest."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from ipaddress import ip_address
from pathlib import Path
import re
import secrets
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from sqlalchemy import insert, select, update

from spg.domain.cloud_delivery import (
    CloudConnection, CloudConnectionState, CloudDeliveryAuthorization,
    CloudDeliveryAuthorizationRequest, CloudDeployment, CloudDeploymentState,
    CloudOperationKind, CloudOperationReceipt, CloudPreparedArtifact, HostProfileState,
    connection_policy, trust_policy,
)
from spg.infrastructure.aliyun_cloud import (
    AliyunCloudProvider, CloudProviderError, InvocationResult,
)
from spg.infrastructure.cloud_delivery_artifact import CloudDeliveryArtifactBuilder
from spg.infrastructure import cloud_delivery_commands as commands
from spg.infrastructure.persistence.cloud_delivery_schema import (
    cloud_connections, cloud_delivery_authorizations, cloud_deployments,
    cloud_prepared_artifacts,
)


class CloudDeliveryError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _now() -> datetime:
    return datetime.now(UTC)


def _payload(value) -> dict:
    return value.model_dump(mode="json")


def _require_assumed_role(observed: dict, role_arn: str) -> None:
    account = role_arn.split(":")[3]
    if str(observed.get("AccountId", "")) != account:
        raise CloudDeliveryError("ASSUMED_ACCOUNT_MISMATCH")
    expected = role_arn.replace(":role/", ":assumed-role/", 1) + "/WattDelivery"
    if observed.get("IdentityType") != "AssumedRoleUser" or \
            observed.get("Arn") != expected:
        raise CloudDeliveryError("ASSUMED_ROLE_MISMATCH")


def assess_invocation_result(result: InvocationResult, username: str,
        kind: CloudOperationKind) -> tuple[
        str, bool, str | None, str | None]:
    """Return a stable blocker without persisting arbitrary provider output.

    ErrorInfo is transient. Only one recognized, controlled username message is
    reconstructed for durable evidence; unfamiliar text may contain secrets.
    """
    # Provider error text is not trusted as durable data. Keep only known
    # non-sensitive codes; the raw code remains available in InvocationResult.
    code = result.error_code if result.error_code in {
        "AccountNotExists", "GuestOSError"} else None
    info = result.error_info or ""
    markers = [line.strip() for line in result.output.splitlines()
        if re.fullmatch(r"(?:WATT|BLOCKED)_[A-Z0-9_]{2,80}", line.strip())]
    marker = markers[-1] if markers else None
    verified = (result.status == "Success" and result.exit_code == 0 and
        code is None and not info.strip() and
        marker is not None and marker.startswith("WATT_") and
        (kind is not CloudOperationKind.PREPARE_WATT_DEPLOYMENT_HOST_V1 or
            marker == "WATT_HOST_READY"))
    if verified:
        return marker, True, code, None
    if kind is CloudOperationKind.CHECK_DEPLOYMENT_PREREQUISITES and \
            code == "AccountNotExists" and result.status == "Invalid" and re.fullmatch(
            r"The specified username does not exists?:\s*" + re.escape(username),
            info.strip(), flags=re.IGNORECASE):
        return ("DEPLOYMENT_USER_NOT_FOUND", False, code,
            f"Deployment user {username} is missing on target ECS.")
    if marker is not None and marker.startswith("BLOCKED_"):
        if marker == "BLOCKED_UNSUPPORTED_HOST_PROFILE":
            return "UNSUPPORTED_HOST_PROFILE", False, None, None
        if marker in {"BLOCKED_HOST_PROFILE_CONFLICT", "BLOCKED_SUBID_CONFLICT"}:
            return "HOST_PROFILE_CONFLICT", False, None, None
        return marker, False, None, None
    if result.error_code or info.strip():
        return "CLOUD_ASSISTANT_REPORTED_FAILURE", False, code, None
    if result.status in {"Failed", "Error", "Timeout", "Cancelled",
            "Aborted", "Invalid", "Terminated"} or (
            result.exit_code is not None and result.exit_code != 0):
        return "CLOUD_ASSISTANT_COMMAND_FAILED", False, None, None
    return "CLOUD_OPERATION_UNVERIFIED", False, None, None


class CloudDeliveryService:
    """Connection reuse never implies authority for a particular deployment."""

    def __init__(self, database, delivery, settings, *, preview=None,
                 provider=None, builder=None, owner_check=None, external_probe=None):
        if settings.aliyun_ecs_deployment_user != "wattdeploy":
            raise CloudDeliveryError("UNSUPPORTED_DEPLOYMENT_IDENTITY")
        self.database, self.delivery, self.settings = database, delivery, settings
        self.provider = provider or AliyunCloudProvider(settings)
        self.builder = builder or CloudDeliveryArtifactBuilder(delivery, preview,
            settings.owner_runtime_store_root, settings.aliyun_ecs_static_base_image)
        self.owner_check = owner_check
        self.external_probe = external_probe or self._external_probe

    def _own_manifest(self, actor: str, work_id: UUID, manifest_id: UUID):
        if self.owner_check is None:
            raise CloudDeliveryError("OWNER_BOUNDARY_UNAVAILABLE")
        detail = self.owner_check(actor, manifest_id)
        if detail["summary"]["work_id"] != str(work_id):
            raise CloudDeliveryError("DELIVERABLE_OWNER_MISMATCH")
        if not detail["current"] or not detail["acceptance"] or \
                detail["acceptance"]["decision"] != "ACCEPT":
            raise CloudDeliveryError("CURRENT_HUMAN_ACCEPTED_DELIVERY_REQUIRED")
        manifest = self.delivery.manifest(work_id, manifest_id)
        if manifest.software is None:
            raise CloudDeliveryError("SOFTWARE_DELIVERY_REQUIRED")
        context = self.delivery.candidate_context(work_id)
        if context is None or context["repository_revision"] != manifest.repository_revision:
            raise CloudDeliveryError("STALE_CANDIDATE")
        return manifest, context

    @staticmethod
    def _connection(session, actor: str, connection_id: UUID, *, lock=False) -> CloudConnection:
        query = select(cloud_connections.c.payload).where(
            cloud_connections.c.id == connection_id,
            cloud_connections.c.owner_id == actor)
        if lock:
            query = query.with_for_update()
        row = session.execute(query).scalar_one_or_none()
        if row is None:
            raise CloudDeliveryError("CLOUD_CONNECTION_NOT_FOUND")
        return CloudConnection.model_validate(row)

    @staticmethod
    def _save_connection(session, connection: CloudConnection) -> CloudConnection:
        updated = connection.model_copy(update={"updated_at": _now(),
            "version": connection.version + 1})
        session.execute(update(cloud_connections).where(cloud_connections.c.id == updated.id)
            .values(payload=_payload(updated), state=updated.state.value,
                    version=updated.version, updated_at=updated.updated_at))
        return updated

    def list_connections(self, actor: str) -> list[dict]:
        with self.database.unit_of_work() as uow:
            rows = uow.session.execute(select(cloud_connections.c.payload)
                .where(cloud_connections.c.owner_id == actor)
                .order_by(cloud_connections.c.created_at.desc())).scalars().all()
        return [CloudConnection.model_validate(row).model_dump(mode="json") for row in rows]

    def draft(self, actor: str) -> dict:
        identity = self.provider.service_identity()
        account, principal = str(identity.get("AccountId", "")), str(identity.get("Arn", ""))
        if not re.fullmatch(r"[0-9]{8,32}", account) or not re.fullmatch(
                rf"acs:ram::{account}:(?:user|role)/[A-Za-z0-9_.@-]+", principal):
            raise CloudDeliveryError("DEDICATED_SERVICE_RAM_IDENTITY_REQUIRED")
        now = _now()
        connection = CloudConnection(id=uuid4(), owner_id=actor,
            service_account_id=account, service_principal_arn=principal,
            external_id=secrets.token_urlsafe(48),
            recommended_role_name="WattECSDelivery", role_arn=None,
            state=CloudConnectionState.AWAITING_CLOUD_AUTHORIZATION,
            created_at=now, updated_at=now)
        with self.database.unit_of_work() as uow:
            uow.session.execute(insert(cloud_connections).values(id=connection.id,
                owner_id=actor, state=connection.state.value, version=connection.version,
                payload=_payload(connection), created_at=now, updated_at=now))
            uow.commit()
        return self.connection(actor, connection.id)

    def connection(self, actor: str, connection_id: UUID) -> dict:
        with self.database.unit_of_work() as uow:
            connection = self._connection(uow.session, actor, connection_id)
        result = _payload(connection)
        result["trust_policy"] = trust_policy(connection.service_principal_arn,
            connection.external_id)
        result["connection_policy"] = (None if connection.customer_account_id is None
            else connection_policy(connection.customer_account_id))
        result["discovered_targets"] = [{"selection_token": str(uuid5(NAMESPACE_URL,
            f"watt:ecs:{connection.id}:{target.account_id}:{target.region_id}:{target.instance_id}")),
            "name": target.name, "region_id": target.region_id,
            "status": target.status, "os_name": target.os_name,
            "public_address_available": target.public_address is not None,
            "cloud_assistant_ready": target.cloud_assistant_ready}
            for target in connection.discovered_targets]
        return result

    def verify_role(self, actor: str, connection_id: UUID, role_arn: str) -> dict:
        if not re.fullmatch(r"acs:ram::[0-9]{8,32}:role/[A-Za-z0-9_.-]+", role_arn):
            raise CloudDeliveryError("INVALID_ROLE_ARN")
        with self.database.unit_of_work() as uow:
            connection = self._connection(uow.session, actor, connection_id)
        if connection.state is CloudConnectionState.REVOKED:
            raise CloudDeliveryError("CONNECTION_REVOKED")
        if connection.role_arn is not None and connection.role_arn != role_arn:
            raise CloudDeliveryError("CONNECTION_ROLE_IMMUTABLE")
        account = role_arn.split(":")[3]
        session = self.provider.assume_role(role_arn, connection.external_id)
        observed = self.provider.assumed_identity(session)
        _require_assumed_role(observed, role_arn)
        regions = self.provider.regions(session)
        targets = tuple(target for region in regions
            for target in self.provider.instances(session, account, region))
        if len(targets) > 1000 or any(target.account_id != account for target in targets):
            raise CloudDeliveryError("DISCOVERY_IDENTITY_INVALID")
        eligible = next((target for target in targets if target.status == "Running" and
            target.os_type.lower() == "linux" and target.cloud_assistant_ready), None)
        if eligible is not None:
            self.provider.target_grant_dry_run(session, eligible)
        with self.database.unit_of_work() as uow:
            locked = self._connection(uow.session, actor, connection_id, lock=True)
            if locked.version != connection.version:
                raise CloudDeliveryError("CONNECTION_CHANGED_RETRY")
            updated = locked.model_copy(update={"role_arn": role_arn,
                "customer_account_id": account, "discovered_targets": targets,
                "discovery_verified_at": _now(),
                "target": None, "target_grant_verified_at": None,
                "state": CloudConnectionState.DISCOVERY_READY})
            self._save_connection(uow.session, updated)
            uow.commit()
        return self.connection(actor, connection_id)

    def set_role(self, actor: str, connection_id: UUID, role_arn: str) -> dict:
        """Bind the role ARN so exact discovery policy is available before the grant."""
        if not re.fullmatch(r"acs:ram::[0-9]{8,32}:role/[A-Za-z0-9_.-]+", role_arn):
            raise CloudDeliveryError("INVALID_ROLE_ARN")
        with self.database.unit_of_work() as uow:
            connection = self._connection(uow.session, actor, connection_id, lock=True)
            if connection.state is CloudConnectionState.REVOKED:
                raise CloudDeliveryError("CONNECTION_REVOKED")
            if connection.role_arn is not None and connection.role_arn != role_arn:
                raise CloudDeliveryError("CONNECTION_ROLE_IMMUTABLE")
            account = role_arn.split(":")[3]
            self._save_connection(uow.session, connection.model_copy(update={
                "role_arn": role_arn, "customer_account_id": account}))
            uow.commit()
        return self.connection(actor, connection_id)

    def select(self, actor: str, connection_id: UUID, selection_token: UUID) -> dict:
        with self.database.unit_of_work() as uow:
            connection = self._connection(uow.session, actor, connection_id, lock=True)
            if connection.state not in {CloudConnectionState.DISCOVERY_READY,
                    CloudConnectionState.TARGET_SELECTED,
                    CloudConnectionState.TARGET_AUTHORIZATION_REQUIRED,
                    CloudConnectionState.READY}:
                raise CloudDeliveryError("DISCOVERY_REQUIRED")
            target = next((item for item in connection.discovered_targets if
                uuid5(NAMESPACE_URL, f"watt:ecs:{connection.id}:{item.account_id}:"
                    f"{item.region_id}:{item.instance_id}") == selection_token), None)
            if target is None:
                raise CloudDeliveryError("TARGET_NOT_IN_DISCOVERY")
            updated = connection.model_copy(update={"target": target,
                "state": CloudConnectionState.TARGET_SELECTED,
                "target_grant_verified_at": None})
            self._save_connection(uow.session, updated)
            uow.commit()
        return self.verify_target(actor, connection_id)

    def verify_target(self, actor: str, connection_id: UUID) -> dict:
        with self.database.unit_of_work() as uow:
            connection = self._connection(uow.session, actor, connection_id)
        if connection.state in {CloudConnectionState.REVOKED,
                CloudConnectionState.INVALID, CloudConnectionState.EXPIRED}:
            raise CloudDeliveryError("CONNECTION_NOT_USABLE")
        if connection.target is None or connection.role_arn is None:
            raise CloudDeliveryError("TARGET_SELECTION_REQUIRED")
        session = self.provider.assume_role(connection.role_arn, connection.external_id)
        observed = self.provider.assumed_identity(session)
        _require_assumed_role(observed, connection.role_arn)
        target = self.provider.exact_instance(session, connection.target)
        if target.identity != connection.target.identity or target.status != "Running" or \
                target.os_type.lower() != "linux" or \
                not target.cloud_assistant_ready:
            raise CloudDeliveryError("TARGET_NOT_READY")
        if not re.match(r"^Alibaba Cloud Linux\s+3(?:\.|\b)", target.os_name):
            raise CloudDeliveryError("UNSUPPORTED_HOST_PROFILE")
        try:
            self.provider.target_grant_dry_run(session, target)
        except CloudProviderError:
            with self.database.unit_of_work() as uow:
                locked = self._connection(uow.session, actor, connection_id, lock=True)
                if locked.target is not None and locked.target.identity == target.identity:
                    self._save_connection(uow.session, locked.model_copy(update={
                        "state": CloudConnectionState.TARGET_SELECTED,
                        "target_grant_verified_at": None}))
                    uow.commit()
            raise
        with self.database.unit_of_work() as uow:
            locked = self._connection(uow.session, actor, connection_id, lock=True)
            if locked.version != connection.version or locked.target.identity != target.identity:
                raise CloudDeliveryError("TARGET_CHANGED_RETRY")
            updated = locked.model_copy(update={"target": target,
                "state": CloudConnectionState.READY,
                "target_grant_verified_at": _now()})
            self._save_connection(uow.session, updated)
            uow.commit()
        return self.connection(actor, connection_id)

    def revoke(self, actor: str, connection_id: UUID) -> dict:
        with self.database.unit_of_work() as uow:
            connection = self._connection(uow.session, actor, connection_id, lock=True)
            self._save_connection(uow.session, connection.model_copy(update={
                "state": CloudConnectionState.REVOKED,
                "target_grant_verified_at": None}))
            uow.commit()
        return self.connection(actor, connection_id)

    def _prepared(self, manifest, context) -> CloudPreparedArtifact:
        with self.database.unit_of_work() as uow:
            row = uow.session.execute(select(cloud_prepared_artifacts.c.payload)
                .where(cloud_prepared_artifacts.c.manifest_id == manifest.id)).scalar_one_or_none()
        if row is not None:
            prepared = CloudPreparedArtifact.model_validate(row)
            path = Path(prepared.archive_path)
            digest = sha256()
            if not path.is_file():
                raise CloudDeliveryError("PREPARED_ARTIFACT_UNAVAILABLE")
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if prepared.manifest_fingerprint != manifest.fingerprint or \
                    digest.hexdigest() != prepared.artifact_sha256:
                raise CloudDeliveryError("PREPARED_ARTIFACT_UNAVAILABLE")
            return prepared
        prepared = self.builder.prepare(manifest, UUID(context["candidate_id"]))
        with self.database.unit_of_work() as uow:
            uow.session.execute(insert(cloud_prepared_artifacts).values(
                id=prepared.id, manifest_id=manifest.id,
                payload=_payload(prepared), created_at=prepared.created_at))
            uow.commit()
        return prepared

    def authorize(self, actor: str, work_id: UUID,
                  request: CloudDeliveryAuthorizationRequest) -> dict:
        # Expiry means recheck the same one-time grant, never send the Human
        # back to RAM for an instance-specific policy.
        with self.database.unit_of_work() as uow:
            current = self._connection(uow.session, actor, request.connection_id)
        if current.target is not None and (current.target_grant_verified_at is None or
                _now() - current.target_grant_verified_at > timedelta(minutes=10)):
            self.verify_target(actor, request.connection_id)
        manifest, context = self._own_manifest(actor, work_id, request.manifest_id)
        if manifest.fingerprint != request.manifest_fingerprint:
            raise CloudDeliveryError("MANIFEST_FINGERPRINT_MISMATCH")
        guardian = self.delivery.guardian_assurance_client
        if guardian is not None and not guardian.passed(work_id,
                UUID(context["candidate_id"])):
            raise CloudDeliveryError("EXACT_GUARDIAN_PASS_REQUIRED")
        with self.database.unit_of_work() as uow:
            connection = self._connection(uow.session, actor, request.connection_id)
            previous_row = (None if request.expected_current_deployment_id is None else
                uow.session.execute(select(cloud_deployments.c.payload).where(
                    cloud_deployments.c.id == request.expected_current_deployment_id,
                    cloud_deployments.c.connection_id == connection.id)).scalar_one_or_none())
        target = connection.target
        if connection.state is not CloudConnectionState.READY or target is None or \
                connection.target_grant_verified_at is None or \
                _now() - connection.target_grant_verified_at > timedelta(minutes=10):
            raise CloudDeliveryError("FRESH_EXACT_TARGET_GRANT_REQUIRED")
        if target.identity != (request.target_account_id,
                request.target_region_id, request.target_instance_id):
            raise CloudDeliveryError("AUTHORIZATION_TARGET_MISMATCH")
        if previous_row is not None:
            previous = CloudDeployment.model_validate(previous_row)
            if previous.state is not CloudDeploymentState.SUCCEEDED or \
                    previous.target.identity != target.identity or previous.port != request.port or \
                    previous.image_identity is None:
                raise CloudDeliveryError("PREVIOUS_DEPLOYMENT_NOT_VERIFIED")
        elif request.expected_current_deployment_id is not None:
            raise CloudDeliveryError("PREVIOUS_DEPLOYMENT_NOT_FOUND")
        prepared = self._prepared(manifest, context)
        if prepared.artifact_kind == "FULL_APPLICATION_RUNTIME":
            raise CloudDeliveryError("FULL_APPLICATION_RUNTIME_CONFIGURATION_REQUIRED")
        now = _now()
        authorization = CloudDeliveryAuthorization(id=uuid4(), work_id=work_id,
            actor_id=actor, connection_id=connection.id, manifest_id=manifest.id,
            manifest_fingerprint=manifest.fingerprint,
            artifact_sha256=prepared.artifact_sha256,
            candidate_revision=manifest.repository_revision, target=target,
            host_recipe_version=commands.HOST_RECIPE_VERSION,
            host_recipe_fingerprint=commands.HOST_RECIPE_FINGERPRINT,
            expected_current_deployment_id=request.expected_current_deployment_id,
            port=request.port, rationale=request.rationale, authorized_at=now)
        with self.database.unit_of_work() as uow:
            uow.session.execute(insert(cloud_delivery_authorizations).values(
                id=authorization.id, connection_id=connection.id,
                manifest_id=manifest.id, actor_id=actor,
                payload=_payload(authorization), created_at=now))
            uow.commit()
        return _payload(authorization)

    @staticmethod
    def _external_probe(target, port: int, expected_sha256: str) -> bool:
        if not target.public_address:
            return False
        try:
            address = ip_address(target.public_address)
            if not address.is_global:
                return False
            import http.client
            connection = http.client.HTTPConnection(str(address), port, timeout=5)
            connection.request("GET", "/")
            response = connection.getresponse()
            body = response.read(1_000_001)
            connection.close()
            return 200 <= response.status < 300 and len(body) <= 1_000_000 and \
                sha256(body).hexdigest() == expected_sha256
        except (ValueError, OSError):
            return False

    def _save_deployment(self, deployment: CloudDeployment) -> None:
        with self.database.unit_of_work() as uow:
            uow.session.execute(update(cloud_deployments).where(
                cloud_deployments.c.id == deployment.id).values(
                state=deployment.state.value, payload=_payload(deployment),
                updated_at=deployment.updated_at))
            uow.commit()

    def deployment(self, actor: str, deployment_id: UUID) -> dict:
        with self.database.unit_of_work() as uow:
            row = uow.session.execute(select(cloud_deployments.c.payload)
                .join(cloud_connections,
                    cloud_deployments.c.connection_id == cloud_connections.c.id)
                .where(cloud_deployments.c.id == deployment_id,
                    cloud_connections.c.owner_id == actor)).scalar_one_or_none()
        if row is None:
            raise CloudDeliveryError("DEPLOYMENT_NOT_FOUND")
        return row

    def deployments_for_manifest(self, actor: str, manifest_id: UUID) -> list[dict]:
        if self.owner_check is None:
            raise CloudDeliveryError("OWNER_BOUNDARY_UNAVAILABLE")
        self.owner_check(actor, manifest_id)
        with self.database.unit_of_work() as uow:
            rows = uow.session.execute(select(cloud_deployments.c.payload)
                .where(cloud_deployments.c.manifest_id == manifest_id)
                .order_by(cloud_deployments.c.created_at.desc()).limit(20)).scalars().all()
        return list(rows)

    def deployments_for_connection(self, actor: str, connection_id: UUID) -> list[dict]:
        with self.database.unit_of_work() as uow:
            self._connection(uow.session, actor, connection_id)
            rows = uow.session.execute(select(cloud_deployments.c.payload)
                .where(cloud_deployments.c.connection_id == connection_id)
                .order_by(cloud_deployments.c.created_at.desc()).limit(50)).scalars().all()
        return list(rows)

    def _effect(self, deployment, session, operation):
        kind = operation.kind
        started = _now()
        result = self.provider.run(session, deployment.target, operation,
            sha256(f"{deployment.id}:{kind.value}".encode()).hexdigest())
        summary, verified, error_code, error_info = assess_invocation_result(
            result, self.settings.aliyun_ecs_deployment_user, kind)
        host_operation = kind is CloudOperationKind.PREPARE_WATT_DEPLOYMENT_HOST_V1
        markers = set(result.output.splitlines()) if host_operation else set()
        before = (HostProfileState.READY if "WATT_HOST_BEFORE_READY" in markers else
            HostProfileState.BOOTSTRAP_REQUIRED if
                "WATT_HOST_BEFORE_BOOTSTRAP_REQUIRED" in markers else None)
        effects = tuple(sorted(marker for marker in markers if marker in {
            "WATT_EFFECT_USER_CREATED", "WATT_EFFECT_SUBUID_ALLOCATED",
            "WATT_EFFECT_SUBGID_ALLOCATED", "WATT_EFFECT_DOCKER_KEY_INSTALLED",
            "WATT_EFFECT_DOCKER_REPOSITORY_ADDED",
            "WATT_EFFECT_PACKAGES_INSTALLED", "WATT_EFFECT_USER_LINGER_ENABLED",
            "WATT_EFFECT_ROOTLESS_RUNTIME_STARTED"}))
        host_after = (HostProfileState.READY if verified and host_operation else
            HostProfileState.UNSUPPORTED if summary == "UNSUPPORTED_HOST_PROFILE" else
            HostProfileState.CONFLICTED if summary == "HOST_PROFILE_CONFLICT" else
            HostProfileState.FAILED if host_operation else None)
        receipt = CloudOperationReceipt(kind=kind,
            account_id=deployment.target.account_id,
            region_id=deployment.target.region_id,
            instance_id=deployment.target.instance_id,
            invocation_id=result.invocation_id, command_id=result.command_id,
            provider_request_id=result.request_id,
            provider_error_code=error_code, provider_error_info=error_info,
            deployment_user="root" if host_operation else
                self.settings.aliyun_ecs_deployment_user,
            recipe_version=operation.recipe_version if host_operation else None,
            recipe_fingerprint=operation.recipe_fingerprint if host_operation else None,
            host_os_profile="ALIBABA_CLOUD_LINUX_3_X86_64" if host_operation else None,
            host_before=before, host_after=host_after, host_effects=effects,
            started_at=started, finished_at=_now(), status=result.status,
            exit_code=result.exit_code, output_summary=summary,
            verified=verified)
        deployment = deployment.model_copy(update={"operations": deployment.operations + (receipt,),
            "host_profile_state": host_after if host_operation else deployment.host_profile_state,
            "updated_at": _now()})
        self._save_deployment(deployment)
        if not receipt.verified:
            raise CloudDeliveryError(summary)
        return deployment

    def execute(self, actor: str, authorization_id: UUID) -> dict:
        with self.database.unit_of_work() as uow:
            row = uow.session.execute(select(cloud_delivery_authorizations.c.payload)
                .where(cloud_delivery_authorizations.c.id == authorization_id,
                    cloud_delivery_authorizations.c.actor_id == actor)).scalar_one_or_none()
        if row is None:
            raise CloudDeliveryError("AUTHORIZATION_NOT_FOUND")
        authorization = CloudDeliveryAuthorization.model_validate(row)
        if authorization.host_recipe_version != commands.HOST_RECIPE_VERSION or \
                authorization.host_recipe_fingerprint != commands.HOST_RECIPE_FINGERPRINT:
            raise CloudDeliveryError("HOST_RECIPE_AUTHORIZATION_STALE")
        manifest, context = self._own_manifest(actor, authorization.work_id,
            authorization.manifest_id)
        if manifest.fingerprint != authorization.manifest_fingerprint or \
                context["repository_revision"] != authorization.candidate_revision:
            raise CloudDeliveryError("AUTHORIZATION_STALE")
        with self.database.unit_of_work() as uow:
            connection = self._connection(uow.session, actor,
                authorization.connection_id, lock=True)
            if connection.state is not CloudConnectionState.READY or \
                    connection.target is None or \
                    connection.target.identity != authorization.target.identity:
                raise CloudDeliveryError("EXACT_CONNECTION_NOT_READY")
            if uow.session.execute(select(cloud_deployments.c.id).where(
                    cloud_deployments.c.authorization_id == authorization_id)).scalar_one_or_none():
                raise CloudDeliveryError("AUTHORIZATION_ALREADY_USED")
            prepared_row = uow.session.execute(select(cloud_prepared_artifacts.c.payload)
                .where(cloud_prepared_artifacts.c.manifest_id == manifest.id)).scalar_one_or_none()
            if prepared_row is None:
                raise CloudDeliveryError("PREPARED_ARTIFACT_REQUIRED")
            prepared = CloudPreparedArtifact.model_validate(prepared_row)
            if prepared.artifact_sha256 != authorization.artifact_sha256:
                raise CloudDeliveryError("ARTIFACT_CHANGED")
            now = _now()
            deployment_id = uuid4()
            deployment = CloudDeployment(id=deployment_id, authorization_id=authorization_id,
                connection_id=connection.id, manifest_id=manifest.id,
                work_id=authorization.work_id, target=authorization.target,
                state=CloudDeploymentState.PRECHECK,
                artifact_sha256=prepared.artifact_sha256,
                image_identity=prepared.image_identity,
                runtime_name=commands.runtime_name(deployment_id),
                port=authorization.port, created_at=now, updated_at=now)
            uow.session.execute(insert(cloud_deployments).values(id=deployment.id,
                authorization_id=authorization_id, connection_id=connection.id,
                manifest_id=manifest.id, state=deployment.state.value,
                payload=_payload(deployment), created_at=now, updated_at=now))
            uow.commit()
        previous = None
        activation_attempted = False
        try:
            if authorization.expected_current_deployment_id:
                previous = CloudDeployment.model_validate(self.deployment(actor,
                    authorization.expected_current_deployment_id))
                if previous.state is not CloudDeploymentState.SUCCEEDED or \
                        previous.target.identity != deployment.target.identity or \
                        previous.port != deployment.port or not previous.health_verified:
                    raise CloudDeliveryError("PREVIOUS_DEPLOYMENT_CHANGED")
            session = self.provider.assume_role(connection.role_arn, connection.external_id)
            identity = self.provider.assumed_identity(session)
            _require_assumed_role(identity, connection.role_arn)
            observed = self.provider.exact_instance(session, deployment.target)
            if observed.identity != deployment.target.identity or observed.status != "Running" or \
                    observed.os_type.lower() != "linux" or \
                    not observed.cloud_assistant_ready:
                raise CloudDeliveryError("TARGET_NOT_READY")
            self.provider.target_grant_dry_run(session, observed)
            if not re.match(r"^Alibaba Cloud Linux\s+3(?:\.|\b)", observed.os_name):
                raise CloudDeliveryError("UNSUPPORTED_HOST_PROFILE")
            deployment = deployment.model_copy(update={
                "host_profile_state": HostProfileState.BOOTSTRAPPING,
                "updated_at": _now()})
            self._save_deployment(deployment)
            deployment = self._effect(deployment, session,
                commands.PrepareDeploymentHostV1())
            deployment = self._effect(deployment, session,
                commands.CheckPrerequisites(deployment.port,
                    previous_name=None if previous is None else previous.runtime_name,
                    previous_image=None if previous is None else previous.image_identity))
            deployment = deployment.model_copy(update={"state": CloudDeploymentState.STAGING,
                "updated_at": _now()})
            self._save_deployment(deployment)
            stage_started = _now()
            staged = self.provider.stage(Path(prepared.archive_path), prepared.artifact_sha256)
            if staged.digest != prepared.artifact_sha256:
                raise CloudDeliveryError("STAGED_ARTIFACT_MISMATCH")
            stage_receipt = CloudOperationReceipt(kind=CloudOperationKind.STAGE_ARTIFACT,
                account_id=deployment.target.account_id,
                region_id=deployment.target.region_id,
                instance_id=deployment.target.instance_id,
                provider_request_id=staged.request_id,
                started_at=stage_started, finished_at=_now(),
                status="PUT_OBJECT_CONFIRMED", exit_code=None,
                output_summary="WATT_ARTIFACT_STAGED", verified=True)
            deployment = deployment.model_copy(update={"state": CloudDeploymentState.PREPARING,
                "staging_object": staged.object_key,
                "operations": deployment.operations + (stage_receipt,),
                "updated_at": _now()})
            self._save_deployment(deployment)
            activation_attempted = True
            deployment = self._effect(deployment, session,
                commands.DeployRelease(deployment_id=deployment.id, manifest_id=manifest.id,
                    digest=prepared.artifact_sha256, image=prepared.image_identity,
                    internal_port=prepared.internal_port, external_port=deployment.port,
                    signed_url=staged.signed_url,
                    previous_name=None if previous is None else previous.runtime_name,
                    previous_image=None if previous is None else previous.image_identity))
            deployment = deployment.model_copy(update={"state": CloudDeploymentState.VERIFYING,
                "updated_at": _now()})
            self._save_deployment(deployment)
            deployment = self._effect(deployment, session,
                commands.VerifyRuntime(deployment.id, prepared.image_identity,
                    deployment.port))
            entrypoint = manifest.software.runtime_recipe.entrypoint
            if entrypoint is None:
                raise CloudDeliveryError("BUSINESS_VERIFICATION_UNAVAILABLE")
            expected_body = self.delivery.artifact(manifest.work_id,
                manifest.id, entrypoint)
            public_started = _now()
            business = self.external_probe(deployment.target, deployment.port,
                sha256(expected_body).hexdigest())
            public_receipt = CloudOperationReceipt(
                kind=CloudOperationKind.VERIFY_PUBLIC_BUSINESS,
                account_id=deployment.target.account_id,
                region_id=deployment.target.region_id,
                instance_id=deployment.target.instance_id,
                started_at=public_started, finished_at=_now(),
                status="HTTP_DIGEST_MATCH" if business else "HTTP_VERIFICATION_FAILED",
                output_summary="WATT_PUBLIC_DIGEST_MATCH" if business else
                    "BLOCKED_PUBLIC_VERIFICATION", verified=business)
            deployment = deployment.model_copy(update={
                "operations": deployment.operations + (public_receipt,),
                "updated_at": _now()})
            self._save_deployment(deployment)
            if not business and previous is not None:
                raise CloudDeliveryError("PUBLIC_BUSINESS_VERIFICATION_FAILED")
            deployment = deployment.model_copy(update={
                "state": (CloudDeploymentState.SUCCEEDED if business else
                    CloudDeploymentState.NEEDS_HUMAN_ATTENTION),
                "health_verified": True, "business_verified": business,
                "blocker": None if business else "PUBLIC_BUSINESS_VERIFICATION_REQUIRED",
                "updated_at": _now()})
            self._save_deployment(deployment)
            return _payload(deployment)
        except Exception as error:
            code = (getattr(error, "code", str(error)) if isinstance(error,
                (CloudDeliveryError, CloudProviderError)) else
                "CLOUD_EXECUTION_INTERNAL_ERROR")
            # _effect commits the invocation receipt before it reports a failed
            # observed operation. Reload it so reconciliation never erases that
            # failure evidence with an older in-memory projection.
            deployment = CloudDeployment.model_validate(self.deployment(actor, deployment.id))
            try:
                if previous is not None and activation_attempted:
                    deployment = self._effect(deployment, session,
                        commands.RollbackRelease(deployment.id, previous.id,
                            previous.image_identity, previous.port))
                    prior_manifest = self.delivery.manifest(previous.work_id,
                        previous.manifest_id)
                    prior_entrypoint = prior_manifest.software.runtime_recipe.entrypoint
                    prior_body = self.delivery.artifact(previous.work_id,
                        previous.manifest_id, prior_entrypoint)
                    rollback_started = _now()
                    rollback_business = self.external_probe(previous.target,
                        previous.port, sha256(prior_body).hexdigest())
                    rollback_receipt = CloudOperationReceipt(
                        kind=CloudOperationKind.VERIFY_ROLLBACK_BUSINESS,
                        account_id=previous.target.account_id,
                        region_id=previous.target.region_id,
                        instance_id=previous.target.instance_id,
                        started_at=rollback_started, finished_at=_now(),
                        status="HTTP_DIGEST_MATCH" if rollback_business else
                            "HTTP_VERIFICATION_FAILED",
                        output_summary="WATT_ROLLBACK_BUSINESS_MATCH" if rollback_business
                            else "BLOCKED_ROLLBACK_BUSINESS",
                        verified=rollback_business)
                    deployment = deployment.model_copy(update={
                        "state": (CloudDeploymentState.ROLLED_BACK if rollback_business
                                  else CloudDeploymentState.NEEDS_HUMAN_ATTENTION),
                        "rollback_verified": rollback_business,
                        "business_verified": rollback_business,
                        "operations": deployment.operations + (rollback_receipt,),
                        "blocker": code if rollback_business else
                            "ROLLBACK_BUSINESS_UNVERIFIED",
                        "updated_at": _now()})
                else:
                    if deployment.state is CloudDeploymentState.VERIFYING:
                        deployment = self._effect(deployment, session,
                            commands.StopFailedRuntime(deployment.id))
                    uncertain = activation_attempted and deployment.state is \
                        CloudDeploymentState.PREPARING and not any(
                            receipt.kind is CloudOperationKind.DEPLOY_WATT_RELEASE
                            for receipt in deployment.operations)
                    deployment = deployment.model_copy(update={
                        "state": (CloudDeploymentState.NEEDS_HUMAN_ATTENTION if uncertain
                                  else CloudDeploymentState.FAILED), "blocker": (
                            "RECONCILIATION_REQUIRED" if uncertain else code),
                        "host_profile_state": (HostProfileState.UNSUPPORTED if code ==
                            "UNSUPPORTED_HOST_PROFILE" else deployment.host_profile_state),
                        "updated_at": _now()})
            except Exception:
                deployment = CloudDeployment.model_validate(
                    self.deployment(actor, deployment.id))
                deployment = deployment.model_copy(update={
                    "state": CloudDeploymentState.NEEDS_HUMAN_ATTENTION,
                    "blocker": "RECONCILIATION_REQUIRED", "updated_at": _now()})
            self._save_deployment(deployment)
            return _payload(deployment)
