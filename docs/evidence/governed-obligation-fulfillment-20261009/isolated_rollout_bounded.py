"""One-time isolated N1 role swap for GOF qualification.

No production container, source, database, credential, or owner export is
changed.  The old isolated containers remain stopped under a held suffix.
Configuration is copied in memory from those containers; transient env files
are created under /run with mode 0600 and never printed or retained.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile


REVISION = "84d16b1f98ee124a4a7fb11761c821e25223ad24"
IMAGE = "watt-n1-gof:84d16b1"
OLD_IMAGE = "watt-n1-gof:3a00dfc"
ROOT = Path("/data/watt/n1-qualification-20261008")
GUARDIAN = ROOT / "gof-e3de9bf" / "guardian"
ROLES = (
    "watt-n1-api-20261008",
    "watt-n1-coordinator-20261008",
    "watt-n1-worker-20261008",
    "watt-n1-tool-host-20261008",
)
START_ORDER = (ROLES[3], ROLES[0], ROLES[1], ROLES[2])
HELD_SUFFIX = "-held-3a00dfc"


def docker(*arguments: str) -> str:
    completed = subprocess.run(("docker", *arguments), check=False,
                               capture_output=True, text=True)
    if completed.returncode:
        # Docker's raw stderr may contain sensitive environment values.
        raise RuntimeError(f"Docker action {arguments[0]} failed")
    return completed.stdout.strip()


def inspect(name: str) -> dict:
    return json.loads(docker("inspect", name))[0]


def preflight() -> dict[str, dict]:
    if not GUARDIAN.is_dir() or not (GUARDIAN / "src" / "guardian").is_dir():
        raise RuntimeError("exact Guardian owner overlay unavailable")
    if not docker("image", "inspect", IMAGE):
        raise RuntimeError("exact Watt image unavailable")
    states = {}
    for role in ROLES:
        old = inspect(role)
        if (old["Config"]["Image"] != OLD_IMAGE
                or not old["State"]["Running"]
                or old["HostConfig"]["NetworkMode"] != "watt-cloud-worker_control"):
            raise RuntimeError(f"isolated preflight mismatch: {role}")
        for mount in old["Mounts"]:
            source = mount["Source"]
            if source != "/var/run/docker.sock" and not (
                    source.startswith(str(ROOT) + "/")
                    or source.startswith("/data/docker/volumes/watt-n1-workspaces-20261008/")
                    or source in {"/data/watt/owners/ecf", "/data/watt/owners/guardian"}):
                raise RuntimeError(f"unexpected mount in {role}")
        states[role] = old
    return states


def launch(role: str, old: dict) -> None:
    values = old["Config"]["Env"]
    values = [value for value in values
              if not value.startswith("SPG_RUNTIME_REVISION=")]
    values.append(f"SPG_RUNTIME_REVISION={REVISION}")
    if any("\n" in value or "\r" in value for value in values):
        raise RuntimeError("multiline environment cannot use a transient env file")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", prefix="watt-n1-gof-",
                                     dir="/run", delete=False) as stream:
        os.fchmod(stream.fileno(), 0o600)
        env_path = stream.name
        for value in values:
            stream.write(value + "\n")
    try:
        command = ["run", "-d", "--name", role,
                   "--network", old["HostConfig"]["NetworkMode"],
                   "--user", old["Config"]["User"],
                   "--workdir", old["Config"]["WorkingDir"],
                   "--env-file", env_path]
        for group in old["HostConfig"].get("GroupAdd") or ():
            command.extend(("--group-add", str(group)))
        for mount in old["Mounts"]:
            source = str(GUARDIAN) if mount["Source"] == "/data/watt/owners/guardian" else mount["Source"]
            spec = f"type=bind,src={source},dst={mount['Destination']}"
            if not mount["RW"]:
                spec += ",readonly"
            command.extend(("--mount", spec))
        for container_port, bindings in (old["HostConfig"].get("PortBindings") or {}).items():
            for binding in bindings or ():
                command.extend(("-p", f"{binding['HostIp']}:{binding['HostPort']}:{container_port}"))
        command.extend((IMAGE, *old["Config"]["Cmd"]))
        docker(*command)
    finally:
        Path(env_path).unlink(missing_ok=True)


def main() -> None:
    states = preflight()
    held: list[str] = []
    created: list[str] = []
    try:
        for role in reversed(START_ORDER):
            docker("stop", "--time", "20", role)
            docker("rename", role, role + HELD_SUFFIX)
            held.append(role)
        for role in START_ORDER:
            launch(role, states[role])
            created.append(role)
        if any(not inspect(role)["State"]["Running"] for role in ROLES):
            raise RuntimeError("new isolated role did not remain running")
    except Exception:
        for role in reversed(created):
            docker("stop", "--time", "5", role)
            docker("rm", role)
        for role in reversed(held):
            docker("rename", role + HELD_SUFFIX, role)
            docker("start", role)
        raise
    print("isolated GOF roles active:", ", ".join(ROLES))
    print("old isolated roles retained under suffix:", HELD_SUFFIX)


if __name__ == "__main__":
    main()
