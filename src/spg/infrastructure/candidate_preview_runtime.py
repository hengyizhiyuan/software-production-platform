"""Container Production Environment adapter for an exact Candidate application.

The Candidate is never run in the trusted Work runtime. The only host-facing
container is a fixed reverse proxy; the application and database stay on an
internal network without production credentials or a Docker socket.
"""

from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import time
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from uuid import UUID

from spg.domain.production_environment import CandidatePreviewMode, EnvironmentProviderError


class DockerCandidatePreviewRuntime:
    definition_version = "watt-compose-topology-v1"
    _SUPPORTING_SERVICES = {
        "redis": ("redis:7.4-alpine", ["redis-cli", "ping"]),
    }

    def __init__(self, root: Path, *, docker_binary: str = "docker",
        verification_image: str = "watt-native-executor-runtime:local") -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.docker_binary = docker_binary
        self.verification_image = verification_image
        self._preview_auth_tokens: dict[UUID, str] = {}

    @staticmethod
    def _names(preview_id: UUID) -> dict[str, str]:
        prefix = f"watt-candidate-preview-{preview_id.hex}"
        return {
            "image": f"{prefix}:candidate",
            "internal": f"{prefix}-internal",
            "gateway": f"{prefix}-gateway",
            "source": f"{prefix}-source",
            "database": f"{prefix}-database",
            "data": f"{prefix}-data",
            "staging": f"{prefix}-staging",
            "postgres": f"{prefix}-postgres",
            "app": f"{prefix}-app",
            "proxy": f"{prefix}-proxy",
            "redis": f"{prefix}-redis",
        }

    def _supporting_services(self, preview_id: UUID) -> tuple[str, ...]:
        declaration = self._workspace(preview_id) / ".watt" / "preview-topology.json"
        if not declaration.exists():
            return ()
        try:
            value = json.loads(declaration.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise EnvironmentProviderError("Candidate preview topology declaration is invalid") from error
        if (not isinstance(value, dict)
                or set(value) != {"schema_version", "supporting_services"}
                or value["schema_version"] != 1
                or not isinstance(value["supporting_services"], list)
                or len(value["supporting_services"]) > 1
                or any(not isinstance(item, str)
                    for item in value["supporting_services"])
                or any(item not in self._SUPPORTING_SERVICES
                    for item in value["supporting_services"])
                or len(set(value["supporting_services"])) != len(value["supporting_services"])):
            raise EnvironmentProviderError("Candidate declares an unsupported preview topology")
        return tuple(value["supporting_services"])

    def _run(self, argv: list[str], *, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, check=False)
        if check and result.returncode:
            detail = (result.stderr or result.stdout).strip()[-3000:]
            raise EnvironmentProviderError(f"Preview operation failed: {detail}")
        return result

    def _docker(self, *args: str, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self._run([self.docker_binary, *args], timeout=timeout, check=check)

    def _workspace(self, preview_id: UUID) -> Path:
        path = (self.root / str(preview_id) / "workspace").resolve()
        if self.root not in path.parents or path.parent.name != str(preview_id):
            raise EnvironmentProviderError("Preview workspace escapes Production Environment root")
        return path

    def _evidence(self, preview_id: UUID) -> Path:
        path = (self.root / "evidence" / str(preview_id)).resolve()
        if self.root not in path.parents:
            raise EnvironmentProviderError("Preview evidence path escapes Production Environment root")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def prepare(self, preview_id: UUID, repository: Path, revision: str, tree: str,
        *, mode: CandidatePreviewMode = CandidatePreviewMode.FULL_APPLICATION_RUNTIME) -> dict:
        """Make an isolated branch at the exact sealed commit; source remains untouched."""
        workspace = self._workspace(preview_id)
        if workspace.exists():
            raise EnvironmentProviderError("Preview Workspace already exists")
        workspace.parent.mkdir(parents=True)
        try:
            self._run(["git", "clone", "--local", "--no-hardlinks", "--no-checkout",
                "--", str(repository), str(workspace)], timeout=120)
            self._run(["git", "-C", str(workspace), "switch", "-c",
                f"candidate-preview-{preview_id.hex[:12]}", revision])
            observed_revision = self._run(["git", "-C", str(workspace), "rev-parse", "HEAD"]).stdout.strip()
            observed_tree = self._run(["git", "-C", str(workspace), "rev-parse", "HEAD^{tree}"]).stdout.strip()
            if (observed_revision, observed_tree) != (revision, tree):
                raise EnvironmentProviderError("Preview Workspace differs from sealed Candidate")
            if self._run(["git", "-C", str(workspace), "status", "--porcelain"]).stdout.strip():
                raise EnvironmentProviderError("Preview Workspace is not clean")
            required = ("Dockerfile", "pyproject.toml", "uv.lock", "docker/start_app.py", "alembic.ini") \
                if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else ("Dockerfile", "package.json")
            if any(not (workspace / item).is_file() for item in required) or (
                mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME and not (workspace / "migrations").is_dir()
            ):
                raise EnvironmentProviderError("Candidate has no supported project-native runtime definition")
            return {"workspace": str(workspace), "revision": observed_revision,
                "tree": observed_tree, "dockerfile_sha256": sha256((workspace / "Dockerfile").read_bytes()).hexdigest()}
        except Exception:
            self._remove_workspace(preview_id)
            raise

    def _remove_workspace(self, preview_id: UUID) -> None:
        workspace_parent = self._workspace(preview_id).parent
        if not workspace_parent.exists():
            return
        if workspace_parent.resolve().parent != self.root:
            raise EnvironmentProviderError("Preview cleanup path escapes Production Environment root")
        for attempt in range(30):
            try:
                shutil.rmtree(workspace_parent)
                return
            except PermissionError:
                if attempt == 29:
                    raise
                time.sleep(0.1)

    def build(self, preview_id: UUID, revision: str, tree: str,
        *, mode: CandidatePreviewMode = CandidatePreviewMode.FULL_APPLICATION_RUNTIME) -> dict:
        workspace = self._workspace(preview_id)
        names = self._names(preview_id)
        dockerfile = (workspace / "Dockerfile").read_text(encoding="utf-8")
        if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME and not re.search(
            r"(?im)^FROM\s+\S+\s+AS\s+native-verification\s*$", dockerfile,
        ):
            raise EnvironmentProviderError("Candidate Dockerfile lacks its application verification target")
        target = ["--target", "native-verification"] if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else []
        result = self._docker("build", *target,
            "--label", f"watt.candidate-preview={preview_id}",
            "--label", f"watt.candidate-revision={revision}",
            "--label", f"watt.candidate-tree={tree}",
            "-t", names["image"], str(workspace), timeout=900, check=False)
        log = self._evidence(preview_id) / "build.log"
        log.write_text((result.stdout + "\n" + result.stderr)[-200_000:], encoding="utf-8")
        if result.returncode:
            raise EnvironmentProviderError("Candidate image build failed; inspect Preview build evidence")
        image_id = self._docker("image", "inspect", "--format", "{{.Id}}", names["image"]).stdout.strip()
        if not image_id.startswith("sha256:"):
            raise EnvironmentProviderError("Candidate image identity is unavailable")
        tracked = self._run(["git", "-C", str(workspace), "ls-files", "-z"]).stdout.split("\0")
        copied = [path for path in tracked if path and (path.startswith(("src/", "migrations/", "docker/"))
            or path in {"pyproject.toml", "uv.lock", "README.md", "alembic.ini"})] \
            if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else []
        for offset in range(0, len(copied), 40):
            chunk = copied[offset:offset + 40]
            observed = self._docker("run", "--rm", "--network", "none", "--entrypoint", "sha256sum",
                names["image"], *("/app/" + path for path in chunk), timeout=90).stdout
            checksums = dict(line.split("  ", 1)[::-1] for line in observed.splitlines())
            for path in chunk:
                expected = sha256((workspace / path).read_bytes()).hexdigest()
                if checksums.get("/app/" + path) != expected:
                    raise EnvironmentProviderError(f"Built image differs from exact Candidate source: {path}")
        if self._run(["git", "-C", str(workspace), "rev-parse", "HEAD"]).stdout.strip() != revision:
            raise EnvironmentProviderError("Candidate revision changed during build")
        if self._run(["git", "-C", str(workspace), "rev-parse", "HEAD^{tree}"]).stdout.strip() != tree:
            raise EnvironmentProviderError("Candidate tree changed during build")
        return {"image": names["image"], "image_id": image_id,
            "verified_image_files": len(copied),
            "build_log": str(log), "build_log_sha256": sha256(log.read_bytes()).hexdigest()}

    def start(self, preview_id: UUID, revision: str, tree: str,
        *, mode: CandidatePreviewMode = CandidatePreviewMode.FULL_APPLICATION_RUNTIME) -> dict:
        names = self._names(preview_id)
        label = f"watt.candidate-preview={preview_id}"
        workspace = self._workspace(preview_id)
        supporting_services = self._supporting_services(preview_id)
        if mode is not CandidatePreviewMode.FULL_APPLICATION_RUNTIME and supporting_services:
            raise EnvironmentProviderError("Frontend-only preview cannot declare backend supporting services")
        password = secrets.token_urlsafe(24)
        operator_token = secrets.token_urlsafe(36)
        self._preview_auth_tokens[preview_id] = operator_token
        port = 8000
        if mode is CandidatePreviewMode.FRONTEND_RUNTIME:
            exposed = re.findall(r"(?im)^EXPOSE\s+(\d+)\s*$", (workspace / "Dockerfile").read_text(encoding="utf-8"))
            if len(exposed) != 1:
                raise EnvironmentProviderError("Frontend Dockerfile must declare one exact exposed port")
            port = int(exposed[0])
        self._docker("network", "create", "--internal", "--label", label, names["internal"])
        self._docker("network", "create", "--label", label, names["gateway"])
        volume_keys = ("source", "database", "data") if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else ("source",)
        for key in volume_keys:
            self._docker("volume", "create", "--label", label, names[key])
        self._docker("create", "--name", names["staging"], "--label", label,
            "--mount", f"type=volume,source={names['source']},target=/source",
            "--entrypoint", "sh", self.verification_image, "-c", "true")
        try:
            self._docker("cp", str(workspace) + "/.", names["staging"] + ":/source", timeout=180)
        finally:
            self._docker("rm", "-f", names["staging"], check=False)
        source_revision = self._docker("run", "--rm", "--mount",
            f"type=volume,source={names['source']},target=/source,readonly",
            "--entrypoint", "git", self.verification_image, "-c", "safe.directory=/source",
            "-C", "/source", "rev-parse", "HEAD").stdout.strip()
        source_tree = self._docker("run", "--rm", "--mount",
            f"type=volume,source={names['source']},target=/source,readonly",
            "--entrypoint", "git", self.verification_image, "-c", "safe.directory=/source",
            "-C", "/source", "rev-parse", "HEAD^{tree}").stdout.strip()
        if (source_revision, source_tree) != (revision, tree):
            raise EnvironmentProviderError("Preview runtime source volume differs from sealed Candidate")
        if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME:
            self._docker("run", "-d", "--name", names["postgres"], "--label", label,
                "--network", names["internal"], "--network-alias", "db",
                "-e", "POSTGRES_USER=spg", "-e", f"POSTGRES_PASSWORD={password}",
                "-e", "POSTGRES_DB=spg_dev", "--mount",
                f"type=volume,source={names['database']},target=/var/lib/postgresql/data",
                "postgres:17.6-alpine")
            self._wait(preview_id, names["postgres"], ["pg_isready", "-U", "spg"], timeout=90)
            for service in supporting_services:
                image, health = self._SUPPORTING_SERVICES[service]
                self._docker("run", "-d", "--name", names[service], "--label", label,
                    "--network", names["internal"], "--network-alias", service,
                    image)
                self._wait(preview_id, names[service], health, timeout=60)
        database_url = (f"postgresql+psycopg://spg:{password}@db:5432/spg_dev"
            "?sslmode=disable&connect_timeout=5")
        runtime_arguments = (["-e", f"SPG_DATABASE_URL={database_url}",
            "-e", f"SPG_OPERATOR_TOKEN={operator_token}",
            "-e", "SPG_REPOSITORY_PATH=/var/lib/spg/repository",
            "-e", "SPG_WORKSPACE_ROOT=/var/lib/spg/workspaces",
            "-e", "SPG_NATIVE_EXECUTOR_STORAGE_ROOT=/var/lib/spg/native-checkpoints",
            "-e", "SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT=/var/lib/spg/native-workspaces",
            "-e", "SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_STORE_ROOT=/var/lib/spg/production-environments",
            "-e", "SPG_RUNTIME_PROFILE=watt-candidate-preview",
            "-e", "SPG_NATIVE_EXECUTOR_ENABLED=false",
            *(["-e", "REDIS_URL=redis://redis:6379"]
                if "redis" in supporting_services else []),
            "--mount", f"type=volume,source={names['data']},target=/var/lib/spg"]
            if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else [])
        self._docker("run", "-d", "--name", names["app"], "--label", label,
            "--label", f"watt.preview-port={port}",
            "--network", names["internal"], "--network-alias", "app",
            "--mount", f"type=volume,source={names['source']},target=/source,readonly",
            *runtime_arguments,
            names["image"])
        if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME:
            self._wait(preview_id, names["app"], ["python", "-c",
                "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"], timeout=150)
        config = workspace.parent / "proxy.conf"
        config.write_text("server { listen 80; server_name _; location / { "
            f"proxy_pass http://app:{port}; proxy_http_version 1.1; "
            "proxy_set_header Host $host; proxy_buffering off; "
            "proxy_read_timeout 3600s; } }\n", encoding="utf-8")
        self._docker("create", "--name", names["proxy"], "--label", label,
            "--network", names["gateway"], "-p", "127.0.0.1::80", "nginx:1.27-alpine")
        self._docker("network", "connect", names["internal"], names["proxy"])
        self._docker("cp", str(config), names["proxy"] + ":/etc/nginx/conf.d/default.conf")
        self._docker("start", names["proxy"])
        path = "/health" if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else "/"
        self._wait(preview_id, names["proxy"], ["wget", "-qO-", f"http://app:{port}{path}"], timeout=40)
        host_port = self._docker("port", names["proxy"], "80/tcp").stdout.strip()
        if not re.fullmatch(r"127\.0\.0\.1:\d+", host_port):
            raise EnvironmentProviderError("Preview Gateway did not publish a local endpoint")
        services = ((names["postgres"],)
            if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else ()) + \
            tuple(names[item] for item in supporting_services) + (names["app"], names["proxy"])
        resources = (names["internal"], names["gateway"]) + tuple(names[key] for key in volume_keys)
        return {"endpoint": f"http://{host_port}{'/app' if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else '/'}",
            "services": services, "resources": resources,
            "health": {"database": "READY" if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else "NOT_REQUIRED",
                "application": "READY", "gateway": "READY",
                **{item: "READY" for item in supporting_services},
                "repository_revision": source_revision, "repository_tree": source_tree},
            "topology": {"frontend": "app", "backend": "app",
                "database": "postgres" if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else None,
                "supporting_services": supporting_services}}

    def _wait(self, preview_id: UUID, container: str, command: list[str], *, timeout: int) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            alive = self._docker("inspect", "--format", "{{.State.Running}}", container,
                check=False).stdout.strip()
            if alive != "true":
                break
            if self._docker("exec", container, *command, check=False).returncode == 0:
                return
            time.sleep(2)
        logs = self._docker("logs", "--tail", "80", container, check=False)
        log = self._evidence(preview_id) / f"{container}.log"
        log.write_text((logs.stdout + logs.stderr)[-30_000:], encoding="utf-8")
        raise EnvironmentProviderError(f"Preview service {container} failed readiness; evidence: {log}")

    def probe(self, preview_id: UUID, revision: str, tree: str,
        *, mode: CandidatePreviewMode = CandidatePreviewMode.FULL_APPLICATION_RUNTIME) -> bool:
        # A caller without Docker authority must not convert an unobservable
        # healthy runtime into an observed runtime failure.
        self._docker("info", "--format", "{{.ServerVersion}}", timeout=15)
        names = self._names(preview_id)
        supporting_services = self._supporting_services(preview_id)
        services = ((names["postgres"],) if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else ()) + \
            tuple(names[item] for item in supporting_services) + (names["app"], names["proxy"])
        for name in services:
            if self._docker("inspect", "--format", "{{.State.Running}}", name,
                    check=False).stdout.strip() != "true":
                return False
        if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME:
            if self._docker("exec", names["app"], "python", "-c",
                    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()",
                    check=False).returncode:
                return False
            actual = self._docker("exec", names["app"], "git", "-C", "/var/lib/spg/repository",
                "rev-parse", "HEAD", check=False).stdout.strip()
            actual_tree = self._docker("exec", names["app"], "git", "-C", "/var/lib/spg/repository",
                "rev-parse", "HEAD^{tree}", check=False).stdout.strip()
        else:
            exposed_port = self._docker("inspect", "--format",
                "{{index .Config.Labels \"watt.preview-port\"}}", names["app"],
                check=False).stdout.strip()
            if not exposed_port.isdigit() or self._docker("exec", names["proxy"],
                    "wget", "-qO-", f"http://app:{exposed_port}/",
                    check=False).returncode:
                return False
            actual = self._docker("run", "--rm", "--mount",
                f"type=volume,source={names['source']},target=/source,readonly",
                "--entrypoint", "git", self.verification_image, "-c", "safe.directory=/source",
                "-C", "/source", "rev-parse", "HEAD", check=False).stdout.strip()
            actual_tree = self._docker("run", "--rm", "--mount",
                f"type=volume,source={names['source']},target=/source,readonly",
                "--entrypoint", "git", self.verification_image, "-c", "safe.directory=/source",
                "-C", "/source", "rev-parse", "HEAD^{tree}", check=False).stdout.strip()
        return (actual, actual_tree) == (revision, tree)

    def verify_served(self, preview_id: UUID, revision: str, tree: str,
        *, mode: CandidatePreviewMode = CandidatePreviewMode.FULL_APPLICATION_RUNTIME) -> dict:
        """Observe the served Candidate, including a database-backed API round trip.

        This is deliberately separate from container readiness.  A healthy
        process or a successful image build cannot establish application
        correctness through the gateway.
        """
        if not self.probe(preview_id, revision, tree, mode=mode):
            raise EnvironmentProviderError("Served runtime differs from the exact Candidate")
        names = self._names(preview_id)
        host_port = self._docker("port", names["proxy"], "80/tcp").stdout.strip()
        if not re.fullmatch(r"127\.0\.0\.1:\d+", host_port):
            raise EnvironmentProviderError("Served runtime has no isolated gateway")
        origin = f"http://{host_port}"

        cookie: str | None = None
        bearer = self._preview_auth_tokens.get(preview_id)
        if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME and bearer is not None:
            try:
                login_payload = json.dumps({"token": bearer}).encode("utf-8")
                with urlopen(Request(origin + "/auth/session", data=login_payload,
                    headers={"Content-Type": "application/json"}, method="POST"),
                    timeout=10) as login_response:
                    if login_response.status != 200:
                        raise EnvironmentProviderError("Candidate login contract failed")
                    cookie = login_response.headers.get("Set-Cookie", "").split(";", 1)[0]
                    if not cookie.startswith("watt_session="):
                        raise EnvironmentProviderError("Candidate session cookie is unavailable")
            except HTTPError as error:
                if error.code != 404:
                    raise EnvironmentProviderError("Candidate login contract failed") from error

        def request(path: str, *, payload: dict | None = None) -> tuple[int, bytes, str, str]:
            headers = {"Content-Type": "application/json"} if payload is not None else {}
            if bearer is not None:
                headers["Authorization"] = f"Bearer {bearer}"
            if cookie is not None:
                headers["Cookie"] = cookie
            body = None if payload is None else json.dumps(payload).encode("utf-8")
            try:
                with urlopen(Request(origin + path, data=body, headers=headers,
                    method="POST" if body is not None else "GET"), timeout=10) as response:
                    return (response.status, response.read(1_000_000),
                        response.headers.get("Content-Type", ""), response.geturl())
            except (OSError, URLError) as error:
                raise EnvironmentProviderError(f"Served runtime request failed at {path}") from error

        observations: dict[str, object] = {
            "candidate_revision": revision,
            "candidate_tree": tree,
            "gateway": origin,
            "mode": mode.value,
        }
        page_path = "/app" if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else "/"
        status, page, content_type, final_url = request(page_path)
        if (status != 200 or not page or "html" not in content_type.lower()
                or final_url != origin + page_path):
            raise EnvironmentProviderError("Served frontend did not return an HTML page")
        observations["frontend"] = {"path": page_path, "status": status,
            "body_sha256": sha256(page).hexdigest()}
        if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME:
            status, body, _, _ = request("/health")
            health = json.loads(body)
            if status != 200 or health.get("database") != "available":
                raise EnvironmentProviderError("Served backend cannot reach its database")
            observations["health"] = health
            status, body, _, _ = request("/api/goals")
            if status != 200 or not isinstance(json.loads(body), list):
                raise EnvironmentProviderError("Served backend read contract failed")
            title = f"Preview verification {preview_id}"
            status, body, _, _ = request("/api/goals", payload={"title": title})
            created = json.loads(body)
            goal_id = created.get("id") or created.get("goal_id")
            if status != 201 or not isinstance(goal_id, str):
                raise EnvironmentProviderError("Served backend write contract failed")
            status, body, _, _ = request(f"/api/goals/{goal_id}")
            observed = json.loads(body)
            if status != 200 or observed.get("goal", {}).get("title") != title:
                raise EnvironmentProviderError("Served backend read-after-write contract failed")
            observations["database_round_trip"] = {"goal_id": goal_id,
                "created_status": 201, "observed_status": status}
        observations["result"] = "PASS"
        return observations

    def stop(self, preview_id: UUID) -> dict:
        self._preview_auth_tokens.pop(preview_id, None)
        names = self._names(preview_id)
        label = str(preview_id)
        logs = []
        try:
            supporting_services = (self._supporting_services(preview_id)
                if self._workspace(preview_id).exists()
                else tuple(self._SUPPORTING_SERVICES))
        except EnvironmentProviderError:
            supporting_services = tuple(self._SUPPORTING_SERVICES)
        for key in ("proxy", "app", "postgres", *supporting_services, "staging"):
            name = names[key]
            owned = self._docker("inspect", "--format", "{{index .Config.Labels \"watt.candidate-preview\"}}",
                name, check=False).stdout.strip()
            if owned == label:
                output = self._docker("logs", "--tail", "500", name, check=False)
                log = self._evidence(preview_id) / f"{name}.log"
                log.write_text((output.stdout + output.stderr)[-100_000:], encoding="utf-8")
                logs.append(str(log))
                self._docker("rm", "-f", name)
        for key in ("gateway", "internal"):
            name = names[key]
            owned = self._docker("network", "inspect", "--format",
                "{{index .Labels \"watt.candidate-preview\"}}", name, check=False).stdout.strip()
            if owned == label:
                self._docker("network", "rm", name)
        for key in ("data", "database", "source"):
            name = names[key]
            owned = self._docker("volume", "inspect", "--format",
                "{{index .Labels \"watt.candidate-preview\"}}", name, check=False).stdout.strip()
            if owned == label:
                self._docker("volume", "rm", name)
        owned_image = self._docker("image", "inspect", "--format",
            "{{index .Config.Labels \"watt.candidate-preview\"}}", names["image"], check=False).stdout.strip()
        if owned_image == label:
            self._docker("image", "rm", names["image"], check=False)
        self._remove_workspace(preview_id)
        return {"service_logs": tuple(logs)}
