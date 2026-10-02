"""Closed Cloud Assistant operation compiler for Watt-owned rootless runtimes.

Only validated identities and a transient signed URL enter these fixed templates.
No caller-supplied script or command is accepted by the application boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
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


HOST_RECIPE_VERSION = "ALINUX3_WATT_DEPLOYMENT_HOST_V1"

# Fixed source and package allowlist. This is deliberately not a request field.
_HOST_RECIPE = r'''#!/bin/sh
set -eu
umask 077
fail() { echo "$1"; exit 20; }
test "$(id -u)" -eq 0 || fail BLOCKED_BOOTSTRAP_NOT_ROOT
test -r /etc/os-release || fail BLOCKED_UNSUPPORTED_HOST_PROFILE
. /etc/os-release
test "$ID" = alinux && test "$VERSION_ID" = 3 || fail BLOCKED_UNSUPPORTED_HOST_PROFILE
test "$(uname -m)" = x86_64 || fail BLOCKED_UNSUPPORTED_HOST_PROFILE
command -v python3 >/dev/null || fail BLOCKED_HOST_PROFILE_CONFLICT
command -v dnf >/dev/null || fail BLOCKED_HOST_PROFILE_CONFLICT
command -v newuidmap >/dev/null || fail BLOCKED_HOST_PROFILE_CONFLICT
command -v newgidmap >/dev/null || fail BLOCKED_HOST_PROFILE_CONFLICT
for tool in curl sha256sum ss; do command -v "$tool" >/dev/null || fail BLOCKED_HOST_PROFILE_CONFLICT; done
test "$(df -Pk /home | awk 'NR==2 {print $4}')" -ge 2097152 || fail BLOCKED_DISK_SPACE

user_present=0
if getent passwd wattdeploy >/dev/null; then
  user_present=1
  test "$(id -u wattdeploy)" -ne 0 || fail BLOCKED_HOST_PROFILE_CONFLICT
  test "$(getent passwd wattdeploy | cut -d: -f6)" = /home/wattdeploy || fail BLOCKED_HOST_PROFILE_CONFLICT
  test -d /home/wattdeploy && test ! -L /home/wattdeploy || fail BLOCKED_HOST_PROFILE_CONFLICT
  test "$(stat -c %u /home/wattdeploy)" = "$(id -u wattdeploy)" || fail BLOCKED_HOST_PROFILE_CONFLICT
  test "$(stat -c %g /home/wattdeploy)" = "$(id -g wattdeploy)" || fail BLOCKED_HOST_PROFILE_CONFLICT
  test "$(stat -c %a /home/wattdeploy)" = 700 || fail BLOCKED_HOST_PROFILE_CONFLICT
else
  test ! -e /home/wattdeploy && test ! -L /home/wattdeploy || fail BLOCKED_HOST_PROFILE_CONFLICT
fi

ready() {
  test "$user_present" = 1 || return 1
  uid=$(id -u wattdeploy)
  test -S "/run/user/$uid/docker.sock" || return 1
  runuser -u wattdeploy -- test -w /home/wattdeploy || return 1
  runuser -u wattdeploy -- env HOME=/home/wattdeploy \
    XDG_RUNTIME_DIR="/run/user/$uid" \
    docker context show 2>/dev/null | grep -qx rootless || return 1
  runuser -u wattdeploy -- env HOME=/home/wattdeploy \
    XDG_RUNTIME_DIR="/run/user/$uid" \
    docker info --format '{{json .SecurityOptions}}' 2>/dev/null | grep -q rootless
}
if ready; then
  echo WATT_HOST_BEFORE_READY
  echo WATT_HOST_READY
  exit 0
fi
echo WATT_HOST_BEFORE_BOOTSTRAP_REQUIRED
if test "$user_present" = 1; then
  # A compatible existing account can be completed. Unknown Docker data cannot.
  test ! -e /home/wattdeploy/.local/share/docker || fail BLOCKED_HOST_PROFILE_CONFLICT
  test ! -e /home/wattdeploy/.docker || fail BLOCKED_HOST_PROFILE_CONFLICT
  test ! -e /home/wattdeploy/.config/systemd/user/docker.service || fail BLOCKED_HOST_PROFILE_CONFLICT
fi
if command -v docker >/dev/null && test ! -f /etc/yum.repos.d/watt-docker-ce-v1.repo; then
  fail BLOCKED_HOST_PROFILE_CONFLICT
fi
if systemctl is-active --quiet docker.service || systemctl is-active --quiet docker.socket; then
  fail BLOCKED_HOST_PROFILE_CONFLICT
fi
test ! -e /etc/yum.repos.d/docker-ce.repo || fail BLOCKED_HOST_PROFILE_CONFLICT
# Validate both allocation maps before creating or changing any account.
test -f /etc/subuid && test -f /etc/subgid || fail BLOCKED_SUBID_CONFLICT
test ! -L /etc/subuid && test ! -L /etc/subgid || fail BLOCKED_SUBID_CONFLICT
python3 - <<'PY' || fail BLOCKED_SUBID_CONFLICT
from pathlib import Path
for name in ('subuid', 'subgid'):
    entries = []
    for raw in Path('/etc/' + name).read_text().splitlines():
        owner, start, count = raw.split(':')
        start, count = int(start), int(count)
        if start < 1 or count < 1: raise ValueError('invalid allocation')
        end = start + count - 1
        if any(start <= other_end and other_start <= end
               for other_start, other_end in entries):
            raise ValueError('overlapping allocation')
        entries.append((start, end))
PY

if test "$user_present" = 0; then
  useradd -m -d /home/wattdeploy -s /bin/bash wattdeploy || fail BLOCKED_USER_CREATE
  user_present=1
  test -d /home/wattdeploy && test ! -L /home/wattdeploy || fail BLOCKED_HOST_PROFILE_CONFLICT
  test "$(stat -c %u /home/wattdeploy)" = "$(id -u wattdeploy)" || fail BLOCKED_HOST_PROFILE_CONFLICT
  test "$(stat -c %g /home/wattdeploy)" = "$(id -g wattdeploy)" || fail BLOCKED_HOST_PROFILE_CONFLICT
  chmod 700 /home/wattdeploy || fail BLOCKED_HOST_PROFILE_CONFLICT
  echo WATT_EFFECT_USER_CREATED
fi

# Select a free, aligned range before either usermod call. Never alter an
# existing or overlapping mapping. Shadow may already have created both.
range=$(python3 - <<'PY'
from pathlib import Path
import sys
files = (Path('/etc/subuid'), Path('/etc/subgid'))
entries = []
mine = []
try:
    for path in files:
        parsed = []
        for raw in path.read_text().splitlines():
            owner, start, count = raw.split(':')
            start, count = int(start), int(count)
            if count < 1 or start < 1: raise ValueError()
            parsed.append((owner, start, start + count - 1))
        for i, (_, a, b) in enumerate(parsed):
            if any(a <= d and c <= b for _, c, d in parsed[i+1:]):
                raise ValueError()
        own = [(a,b) for owner,a,b in parsed if owner == 'wattdeploy']
        if len(own) > 1 or (own and own[0][1] - own[0][0] + 1 < 65536):
            raise ValueError()
        mine.append(bool(own))
        entries.extend((a,b) for _,a,b in parsed)
    for start in range(100000, 1000000000, 65536):
        end = start + 65535
        if all(end < a or start > b for a,b in entries):
            print(f'{start}-{end}'); break
    else: raise ValueError()
except (OSError, ValueError):
    sys.exit(1)
PY
) || fail BLOCKED_SUBID_CONFLICT
if ! grep -q '^wattdeploy:' /etc/subuid; then
  usermod --add-subuids "$range" wattdeploy || fail BLOCKED_SUBID_CONFLICT
  echo WATT_EFFECT_SUBUID_ALLOCATED
fi
if ! grep -q '^wattdeploy:' /etc/subgid; then
  usermod --add-subgids "$range" wattdeploy || fail BLOCKED_SUBID_CONFLICT
  echo WATT_EFFECT_SUBGID_ALLOCATED
fi

# Static Alibaba Cloud Linux 3 / CentOS 8 compatible Docker CE repository.
# Pin the official Docker signing key bytes before importing it. No existing
# repository is rewritten.
key_path=/etc/pki/rpm-gpg/WATT-DOCKER-CE-V1
key_digest=e6c650e0700b1bf4868b693b30761b926844befc8a0acb7ac0dd9b1faf1b7423
if test -e "$key_path"; then
  test -f "$key_path" && test ! -L "$key_path" &&
    test "$(sha256sum "$key_path" | cut -d' ' -f1)" = "$key_digest" ||
    fail BLOCKED_HOST_PROFILE_CONFLICT
else
  key_tmp=$(mktemp /root/watt-docker-key.XXXXXX) || fail BLOCKED_APPROVED_PACKAGE_SOURCE
  curl -fsSL --max-time 30 https://mirrors.aliyun.com/docker-ce/linux/centos/gpg \
    -o "$key_tmp" || fail BLOCKED_APPROVED_PACKAGE_SOURCE
  test "$(sha256sum "$key_tmp" | cut -d' ' -f1)" = "$key_digest" ||
    fail BLOCKED_APPROVED_PACKAGE_SOURCE
  install -m 0644 "$key_tmp" "$key_path" || fail BLOCKED_APPROVED_PACKAGE_SOURCE
  rm -f "$key_tmp"
  echo WATT_EFFECT_DOCKER_KEY_INSTALLED
fi
rpm --import "$key_path" >/dev/null 2>&1 || fail BLOCKED_APPROVED_PACKAGE_SOURCE
repo_expected=$(cat <<'REPO'
[watt-docker-ce-v1]
name=Watt approved Docker CE stable for Alibaba Cloud Linux 3
baseurl=https://mirrors.aliyun.com/docker-ce/linux/centos/8/$basearch/stable
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/WATT-DOCKER-CE-V1
REPO
)
if test -e /etc/yum.repos.d/watt-docker-ce-v1.repo; then
  test -f /etc/yum.repos.d/watt-docker-ce-v1.repo &&
    test ! -L /etc/yum.repos.d/watt-docker-ce-v1.repo &&
    test "$(cat /etc/yum.repos.d/watt-docker-ce-v1.repo)" = "$repo_expected" ||
    fail BLOCKED_HOST_PROFILE_CONFLICT
else
  printf '%s\n' "$repo_expected" > /etc/yum.repos.d/watt-docker-ce-v1.repo
  echo WATT_EFFECT_DOCKER_REPOSITORY_ADDED
fi
dnf -y --setopt=install_weak_deps=False --disablerepo='*' \
  --enablerepo='alinux3*' --enablerepo=watt-docker-ce-v1 install \
  docker-ce docker-ce-cli containerd.io docker-ce-rootless-extras \
  fuse-overlayfs systemd-container >/dev/null 2>&1 || fail BLOCKED_APPROVED_PACKAGE_INSTALL
echo WATT_EFFECT_PACKAGES_INSTALLED
if systemctl is-active --quiet docker.service || systemctl is-active --quiet docker.socket; then
  fail BLOCKED_HOST_PROFILE_CONFLICT
fi
loginctl enable-linger wattdeploy >/dev/null 2>&1 || fail BLOCKED_ROOTLESS_SETUP
echo WATT_EFFECT_USER_LINGER_ENABLED
machinectl shell wattdeploy@ /bin/sh -c \
  'export HOME=/home/wattdeploy XDG_RUNTIME_DIR=/run/user/$(id -u); test "$(id -u)" -ne 0 && dockerd-rootless-setuptool.sh --skip-iptables install && systemctl --user enable --now docker.service && docker context use rootless' \
  || fail BLOCKED_ROOTLESS_SETUP
test -f /home/wattdeploy/.config/systemd/user/docker.service || fail BLOCKED_ROOTLESS_SETUP
test -d /home/wattdeploy/.docker || fail BLOCKED_ROOTLESS_SETUP
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if ready; then
    echo WATT_EFFECT_ROOTLESS_IPTABLES_DISABLED
    echo WATT_EFFECT_ROOTLESS_RUNTIME_STARTED
    test "$(df -Pk /home/wattdeploy | awk 'NR==2 {print $4}')" -ge 2097152 || fail BLOCKED_DISK_SPACE
    echo WATT_HOST_READY
    exit 0
  fi
  sleep 2
done
fail BLOCKED_ROOTLESS_VERIFICATION
'''

HOST_RECIPE_FINGERPRINT = sha256(_HOST_RECIPE.encode()).hexdigest()


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
class PrepareDeploymentHostV1:
    kind: ClassVar[CloudOperationKind] = CloudOperationKind.PREPARE_WATT_DEPLOYMENT_HOST_V1
    recipe_version: ClassVar[str] = HOST_RECIPE_VERSION
    recipe_fingerprint: ClassVar[str] = HOST_RECIPE_FINGERPRINT

    def compile(self) -> str:
        return _HOST_RECIPE


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


CloudCommand = (PrepareDeploymentHostV1 | CheckPrerequisites | DeployRelease | VerifyRuntime |
    RollbackRelease | StopFailedRuntime)


def compile_operation(operation: CloudCommand) -> tuple[CloudOperationKind, str]:
    if type(operation) not in {PrepareDeploymentHostV1, CheckPrerequisites, DeployRelease,
            VerifyRuntime, RollbackRelease, StopFailedRuntime}:
        raise CloudCommandError("UNSUPPORTED_OPERATION")
    return operation.kind, operation.compile()
