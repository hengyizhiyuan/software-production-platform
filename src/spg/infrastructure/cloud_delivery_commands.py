"""Closed Cloud Assistant operation compiler for Watt-owned rootless runtimes.

Only validated identities and a transient signed URL enter these fixed templates.
No caller-supplied script or command is accepted by the application boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from shlex import quote
from typing import ClassVar
from uuid import UUID

from spg.domain.cloud_delivery import CloudOperationKind


class CloudCommandError(RuntimeError):
    pass


def runtime_name(deployment_id: UUID) -> str:
    return f"watt-delivery-{deployment_id.hex}"


def _safe_digest(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise CloudCommandError("INVALID_DIGEST")
    return value


def _safe_image(value: str) -> str:
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise CloudCommandError("INVALID_IMAGE_IDENTITY")
    return value


def _safe_port(port: int) -> int:
    if isinstance(port, bool) or not isinstance(port, int) or not 1024 <= port <= 65535:
        raise CloudCommandError("INVALID_PORT")
    return port


def precheck(port: int, *, previous_name: str | None = None,
             previous_image: str | None = None) -> str:
    port = _safe_port(port)
    prior = ""
    if previous_name:
        if not re.fullmatch(r"watt-delivery-[0-9a-f]{32}", previous_name):
            raise CloudCommandError("INVALID_PREVIOUS_RUNTIME")
        image = _safe_image(previous_image or "")
        prior = f"""
test "$(docker inspect -f '{{{{index .Config.Labels "watt.delivery"}}}}' {quote(previous_name)} 2>/dev/null)" = {quote(previous_name)} || {{ echo BLOCKED_PREVIOUS_NOT_OWNED; exit 20; }}
test "$(docker inspect -f '{{{{.Image}}}}' {quote(previous_name)} 2>/dev/null)" = {quote(image)} || {{ echo BLOCKED_PREVIOUS_IMAGE_CHANGED; exit 20; }}
docker port {quote(previous_name)} 2>/dev/null | grep -q '0.0.0.0:{port}$' || {{ echo BLOCKED_PREVIOUS_PORT_CHANGED; exit 20; }}
"""
    return f"""#!/bin/sh
set -eu
test "$(id -u)" -ne 0 || {{ echo BLOCKED_ROOT_IDENTITY; exit 20; }}
command -v docker >/dev/null || {{ echo BLOCKED_DOCKER_MISSING; exit 20; }}
command -v curl >/dev/null || {{ echo BLOCKED_CURL_MISSING; exit 20; }}
command -v sha256sum >/dev/null || {{ echo BLOCKED_HASH_TOOL_MISSING; exit 20; }}
command -v ss >/dev/null || {{ echo BLOCKED_PORT_INSPECTION_MISSING; exit 20; }}
docker info --format '{{{{json .SecurityOptions}}}}' 2>/dev/null | grep -q rootless || {{ echo BLOCKED_ROOTLESS_DOCKER_REQUIRED; exit 20; }}
test -w "$HOME" || {{ echo BLOCKED_HOME_NOT_WRITABLE; exit 20; }}
test "$(df -Pk "$HOME" | awk 'NR==2 {{print $4}}')" -ge 2097152 || {{ echo BLOCKED_DISK_SPACE; exit 20; }}
{prior}
if ss -ltn "sport = :{port}" | tail -n +2 | grep -q .; then
  {f'test -n "$(docker ps --filter name=^{previous_name}$ --format "{{{{.Names}}}}")" || {{ echo BLOCKED_UNKNOWN_PORT_OWNER; exit 20; }}' if previous_name else 'echo BLOCKED_UNKNOWN_PORT_OWNER; exit 20;'}
fi
echo WATT_PRECHECK_OK
"""


def deploy(*, deployment_id: UUID, manifest_id: UUID, digest: str,
           image: str, internal_port: int, external_port: int,
           signed_url: str, previous_name: str | None = None,
           previous_image: str | None = None) -> str:
    digest, image = _safe_digest(digest), _safe_image(image)
    internal_port, external_port = _safe_port(internal_port), _safe_port(external_port)
    if not signed_url.startswith("https://") or len(signed_url) > 6000 or "\n" in signed_url:
        raise CloudCommandError("INVALID_SIGNED_URL")
    name = runtime_name(deployment_id)
    old = ""
    if previous_name:
        if not re.fullmatch(r"watt-delivery-[0-9a-f]{32}", previous_name):
            raise CloudCommandError("INVALID_PREVIOUS_RUNTIME")
        prior_image = _safe_image(previous_image or "")
        old = f"""test "$(docker inspect -f '{{{{index .Config.Labels "watt.delivery"}}}}' {quote(previous_name)} 2>/dev/null)" = {quote(previous_name)} || {{ echo BLOCKED_PREVIOUS_NOT_OWNED; exit 20; }}
test "$(docker inspect -f '{{{{.Image}}}}' {quote(previous_name)} 2>/dev/null)" = {quote(prior_image)} || {{ echo BLOCKED_PREVIOUS_IMAGE_CHANGED; exit 20; }}
docker port {quote(previous_name)} 2>/dev/null | grep -q '0.0.0.0:{external_port}$' || {{ echo BLOCKED_PREVIOUS_PORT_CHANGED; exit 20; }}
docker stop {quote(previous_name)} >/dev/null || {{ echo BLOCKED_PREVIOUS_STOP; exit 20; }}"""
    return f"""#!/bin/sh
set -eu
umask 077
root="$HOME/.watt/deployments/{deployment_id.hex}"
mkdir -p "$root"
test ! -e "$root/image.tar" || {{ echo BLOCKED_EXISTING_ARTIFACT; exit 20; }}
curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' --max-time 120 {quote(signed_url)} -o "$root/image.tar" 2>/dev/null || {{ echo BLOCKED_ARTIFACT_DOWNLOAD; exit 20; }}
test "$(sha256sum "$root/image.tar" | cut -d' ' -f1)" = {quote(digest)} || {{ echo BLOCKED_ARTIFACT_DIGEST; exit 20; }}
docker load -i "$root/image.tar" >/dev/null || {{ echo BLOCKED_IMAGE_LOAD; exit 20; }}
docker image inspect {quote(image)} >/dev/null 2>&1 || {{ echo BLOCKED_IMAGE_IDENTITY; exit 20; }}
stage={quote(name + '-stage')}
stage_id=$(docker run -d --name "$stage" --label watt.delivery={quote(name)} --label watt.manifest={quote(str(manifest_id))} -p 127.0.0.1::{internal_port} {quote(image)}) || {{ echo BLOCKED_STAGE_START; exit 20; }}
trap 'docker rm -f "$stage_id" >/dev/null 2>&1 || true' EXIT
stage_port=$(docker port "$stage" {internal_port}/tcp | sed -n 's/.*://p' | head -n 1)
case "$stage_port" in ''|*[!0-9]*) echo BLOCKED_STAGE_PORT; exit 20;; esac
healthy=0
for n in 1 2 3 4 5 6 7 8 9 10; do
  if curl --fail --silent --max-time 3 "http://127.0.0.1:$stage_port/" -o /dev/null; then healthy=1; break; fi
  sleep 2
done
test "$healthy" = 1 || {{ echo BLOCKED_STAGE_HEALTH; exit 20; }}
docker rm -f "$stage_id" >/dev/null
trap - EXIT
{old}
docker run -d --name {quote(name)} --label watt.delivery={quote(name)} --label watt.manifest={quote(str(manifest_id))} -p 0.0.0.0:{external_port}:{internal_port} {quote(image)} >/dev/null || {{ echo BLOCKED_ACTIVATION; exit 20; }}
echo WATT_ACTIVATED
"""


def verify(deployment_id: UUID, image: str, port: int) -> str:
    name = runtime_name(deployment_id)
    image, port = _safe_image(image), _safe_port(port)
    return f"""#!/bin/sh
set -eu
test "$(docker inspect -f '{{{{index .Config.Labels "watt.delivery"}}}}' {quote(name)} 2>/dev/null)" = {quote(name)} || {{ echo BLOCKED_RUNTIME_OWNER; exit 20; }}
test "$(docker inspect -f '{{{{.Image}}}}' {quote(name)})" = {quote(image)} || {{ echo BLOCKED_RUNTIME_IMAGE; exit 20; }}
test "$(docker inspect -f '{{{{.State.Running}}}}' {quote(name)})" = true || {{ echo BLOCKED_RUNTIME_STOPPED; exit 20; }}
curl --fail --silent --max-time 5 http://127.0.0.1:{port}/ -o /dev/null || {{ echo BLOCKED_RUNTIME_HEALTH; exit 20; }}
echo WATT_RUNTIME_HEALTHY
"""


def rollback(deployment_id: UUID, previous_id: UUID, previous_image: str,
             port: int) -> str:
    new, old = runtime_name(deployment_id), runtime_name(previous_id)
    image, port = _safe_image(previous_image), _safe_port(port)
    return f"""#!/bin/sh
set -eu
test "$(docker inspect -f '{{{{index .Config.Labels "watt.delivery"}}}}' {quote(old)} 2>/dev/null)" = {quote(old)} || {{ echo BLOCKED_ROLLBACK_OWNER; exit 20; }}
test "$(docker inspect -f '{{{{.Image}}}}' {quote(old)})" = {quote(image)} || {{ echo BLOCKED_ROLLBACK_IMAGE; exit 20; }}
if docker inspect {quote(new)} >/dev/null 2>&1; then
  test "$(docker inspect -f '{{{{index .Config.Labels "watt.delivery"}}}}' {quote(new)})" = {quote(new)} || {{ echo BLOCKED_NEW_RUNTIME_OWNER; exit 20; }}
  docker rm -f {quote(new)} >/dev/null || {{ echo BLOCKED_NEW_RUNTIME_STOP; exit 20; }}
fi
docker start {quote(old)} >/dev/null || {{ echo BLOCKED_ROLLBACK_START; exit 20; }}
curl --fail --silent --max-time 5 http://127.0.0.1:{port}/ -o /dev/null || {{ echo BLOCKED_ROLLBACK_HEALTH; exit 20; }}
echo WATT_ROLLBACK_HEALTHY
"""


def cleanup(deployment_id: UUID) -> str:
    name = runtime_name(deployment_id)
    return f"""#!/bin/sh
set -eu
if docker inspect {quote(name)} >/dev/null 2>&1; then
  test "$(docker inspect -f '{{{{index .Config.Labels "watt.delivery"}}}}' {quote(name)})" = {quote(name)} || {{ echo BLOCKED_CLEANUP_OWNER; exit 20; }}
  docker rm -f {quote(name)} >/dev/null || {{ echo BLOCKED_CLEANUP; exit 20; }}
fi
echo WATT_CLEANUP_OK
"""


@dataclass(frozen=True)
class CheckPrerequisites:
    port: int
    previous_name: str | None = None
    previous_image: str | None = None
    kind: ClassVar[CloudOperationKind] = CloudOperationKind.CHECK_DEPLOYMENT_PREREQUISITES

    def compile(self) -> str:
        return precheck(self.port, previous_name=self.previous_name,
            previous_image=self.previous_image)


@dataclass(frozen=True)
class DeployRelease:
    deployment_id: UUID
    manifest_id: UUID
    digest: str
    image: str
    internal_port: int
    external_port: int
    signed_url: str
    previous_name: str | None = None
    previous_image: str | None = None
    kind: ClassVar[CloudOperationKind] = CloudOperationKind.DEPLOY_WATT_RELEASE

    def compile(self) -> str:
        return deploy(deployment_id=self.deployment_id, manifest_id=self.manifest_id,
            digest=self.digest, image=self.image, internal_port=self.internal_port,
            external_port=self.external_port, signed_url=self.signed_url,
            previous_name=self.previous_name, previous_image=self.previous_image)


@dataclass(frozen=True)
class VerifyRuntime:
    deployment_id: UUID
    image: str
    port: int
    kind: ClassVar[CloudOperationKind] = CloudOperationKind.VERIFY_WATT_RUNTIME

    def compile(self) -> str:
        return verify(self.deployment_id, self.image, self.port)


@dataclass(frozen=True)
class RollbackRelease:
    deployment_id: UUID
    previous_id: UUID
    previous_image: str
    port: int
    kind: ClassVar[CloudOperationKind] = CloudOperationKind.ROLLBACK_WATT_RELEASE

    def compile(self) -> str:
        return rollback(self.deployment_id, self.previous_id,
            self.previous_image, self.port)


@dataclass(frozen=True)
class StopFailedRuntime:
    deployment_id: UUID
    kind: ClassVar[CloudOperationKind] = CloudOperationKind.STOP_WATT_RUNTIME

    def compile(self) -> str:
        return cleanup(self.deployment_id)


CloudCommand = (CheckPrerequisites | DeployRelease | VerifyRuntime |
    RollbackRelease | StopFailedRuntime)


def compile_operation(operation: CloudCommand) -> tuple[CloudOperationKind, str]:
    if type(operation) not in {CheckPrerequisites, DeployRelease,
            VerifyRuntime, RollbackRelease, StopFailedRuntime}:
        raise CloudCommandError("UNSUPPORTED_OPERATION")
    return operation.kind, operation.compile()
