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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen
from base64 import b64decode
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
        self._static_servers: dict[UUID, ThreadingHTTPServer] = {}

    def _static_record_path(self, preview_id: UUID) -> Path:
        return self._workspace(preview_id).parent / "static-runtime.json"

    def _static_start(self, preview_id: UUID, revision: str, tree: str) -> dict:
        """Serve immutable Git blobs; never execute Candidate code in the API.

        Guardian uses this private observation endpoint. Human review remains
        on Watt's authenticated, sandboxed exact-Candidate artifact route.
        """
        from spg.application.delivery import read_artifact, artifact_media_type
        from spg.application.preview_security import PREVIEW_CONTENT_SECURITY_POLICY

        repository = self._workspace(preview_id)
        record_path = self._static_record_path(preview_id)
        record = json.loads(record_path.read_text()) if record_path.exists() else None
        if record and (record["revision"], record["tree"]) != (revision, tree):
            raise EnvironmentProviderError("Static runtime identity changed")
        paths = self._run(["git", "-C", str(repository), "ls-tree", "-r",
            "--name-only", revision]).stdout.splitlines()
        html = sorted(path for path in paths if path.endswith(".html"))
        if not html or len(paths) > 500:
            raise EnvironmentProviderError("Candidate is not a bounded static Web tree")
        entrypoint = "index.html" if "index.html" in html else html[0]
        allowed = {path for path in paths if Path(path).suffix.lower() in {
            ".html", ".css", ".js", ".mjs", ".json", ".svg", ".png", ".jpg",
            ".jpeg", ".gif", ".ico", ".webp", ".woff", ".woff2", ".ttf"}}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = unquote(urlsplit(self.path).path).removeprefix("/") or entrypoint
                try:
                    if path not in allowed:
                        raise ValueError("not a declared static asset")
                    body = read_artifact(str(repository), revision, path, software=True)
                except (ValueError, RuntimeError):
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", artifact_media_type(path))
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Candidate-Revision", revision)
                self.send_header("X-Candidate-Tree", tree)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Security-Policy", PREVIEW_CONTENT_SECURITY_POLICY)
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        server = self._static_servers.get(preview_id)
        if server is None:
            server = ThreadingHTTPServer(("127.0.0.1", 0 if record is None else record["port"]), Handler)
            self._static_servers[preview_id] = server
            Thread(target=server.serve_forever, daemon=True,
                name=f"candidate-static-{preview_id}").start()
            record = {"revision": revision, "tree": tree, "port": server.server_port,
                "entrypoint": entrypoint}
            temporary = record_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(record, sort_keys=True))
            os.replace(temporary, record_path)
        return {"endpoint": f"http://127.0.0.1:{server.server_port}/",
            "services": (f"static-git:{preview_id}",), "resources": (str(repository),),
            "health": {"application": "READY", "repository_revision": revision,
                "repository_tree": tree}, "topology": {"frontend": "immutable-git-blobs"}}

    def _static_verify(self, preview_id: UUID, revision: str, tree: str) -> dict:
        from spg.application.delivery import read_artifact
        record = json.loads(self._static_record_path(preview_id).read_text())
        if (record["revision"], record["tree"]) != (revision, tree):
            raise EnvironmentProviderError("Static runtime differs from Candidate")
        expected = read_artifact(str(self._workspace(preview_id)), revision,
            record["entrypoint"], software=True)
        with urlopen(f"http://127.0.0.1:{record['port']}/", timeout=3) as response:
            observed = response.read(len(expected) + 1)
            if (response.status != 200 or observed != expected
                    or response.headers.get("X-Candidate-Revision") != revision
                    or response.headers.get("X-Candidate-Tree") != tree):
                raise EnvironmentProviderError("Served static subject differs from exact Git result")
        return {"result": "PASS", "candidate_revision": revision, "candidate_tree": tree,
            "http_status": 200, "entrypoint_sha256": sha256(observed).hexdigest(),
            "entrypoint": record["entrypoint"]}

    def restore_static(self, preview_id: UUID, revision: str, tree: str) -> None:
        self._static_start(preview_id, revision, tree)

    def shutdown(self) -> None:
        for server in self._static_servers.values():
            server.shutdown()
            server.server_close()
        self._static_servers.clear()

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

    def _run(self, argv: list[str], *, timeout: int = 120, check: bool = True,
        input_data: str | None = None) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, check=False, input=input_data)
        if check and result.returncode:
            detail = (result.stderr or result.stdout).strip()[-3000:]
            raise EnvironmentProviderError(f"Preview operation failed: {detail}")
        return result

    def _docker(self, *args: str, timeout: int = 120, check: bool = True,
        input_data: str | None = None) -> subprocess.CompletedProcess[str]:
        return self._run([self.docker_binary, *args], timeout=timeout, check=check,
            input_data=input_data)

    def preflight(self) -> dict:
        """Qualify the verifier namespace before building a Candidate image.

        The public endpoint belongs to the Docker host. Internal observations
        use a disposable, unprivileged verifier on the gateway network instead.
        No host loopback or host.docker.internal assumption is needed.
        """
        self._docker("info", "--format", "{{.ServerVersion}}")
        self._docker("image", "inspect", self.verification_image)
        self._docker("run", "--rm", "--network", "none", "--read-only",
            "--user", "65534:65534",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--entrypoint", "python", self.verification_image, "-c",
            "import urllib.request, json, base64; print('verifier-ready')")
        return {"verifier_namespace": "candidate-gateway-network",
            "verifier_image": self.verification_image,
            "public_endpoint_namespace": "docker-host"}

    def _gateway_request(self, preview_id: UUID, path: str, *,
        payload: dict | None = None, headers: dict | None = None) -> dict:
        """Observe the same proxy as Human, from a namespace with a route to it.

        Credentials travel only over stdin. Redirects are rejected so Candidate
        content cannot redirect an authenticated probe to an external endpoint.
        """
        names = self._names(preview_id)
        script = '''import base64, json, sys
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None
value = json.load(sys.stdin)
body = None if value["payload"] is None else json.dumps(value["payload"]).encode()
request = Request(value["url"], data=body, headers=value["headers"],
    method="GET" if body is None else "POST")
try:
    response = build_opener(NoRedirect).open(request, timeout=10)
except HTTPError as error:
    response = error
with response:
    print(json.dumps({"status": response.code,
        "body": base64.b64encode(response.read(1000000)).decode(),
        "content_type": response.headers.get("Content-Type", ""),
        "cookie": response.headers.get("Set-Cookie", "").split(";", 1)[0],
        "url": response.geturl()}))
'''
        if not path.startswith("/") or path.startswith("//"):
            raise EnvironmentProviderError("Preview verification path is not relative")
        value = {"url": f"http://{names['proxy']}{path}",
            "payload": payload, "headers": headers or {}}
        result = self._docker("run", "--rm", "-i", "--network", names["gateway"],
            "--user", "65534:65534",
            "--label", f"watt.candidate-preview={preview_id}", "--read-only",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--memory", "128m", "--pids-limit", "64",
            "--entrypoint", "python", self.verification_image, "-c", script,
            timeout=30, input_data=json.dumps(value))
        try:
            return json.loads(result.stdout)
        except (ValueError, TypeError) as error:
            raise EnvironmentProviderError("Preview verifier returned invalid evidence") from error

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
        topology = ({"verifier_namespace": "api-private-static-observation"}
            if mode is CandidatePreviewMode.STATIC_PREVIEW else self.preflight())
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
            if mode is CandidatePreviewMode.STATIC_PREVIEW:
                return {"workspace": str(workspace), "revision": observed_revision,
                    "tree": observed_tree, "topology_preflight": topology}
            required = ("Dockerfile", "pyproject.toml", "uv.lock", "docker/start_app.py", "alembic.ini") \
                if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else ("Dockerfile", "package.json")
            if any(not (workspace / item).is_file() for item in required) or (
                mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME and not (workspace / "migrations").is_dir()
            ):
                raise EnvironmentProviderError("Candidate has no supported project-native runtime definition")
            return {"workspace": str(workspace), "revision": observed_revision,
                "tree": observed_tree, "topology_preflight": topology,
                "dockerfile_sha256": sha256((workspace / "Dockerfile").read_bytes()).hexdigest()}
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
        if mode is CandidatePreviewMode.STATIC_PREVIEW:
            observed = self._run(["git", "-C", str(workspace), "rev-parse", "HEAD", "HEAD^{tree}"]).stdout.splitlines()
            if observed != [revision, tree]:
                raise EnvironmentProviderError("Static build differs from exact Candidate")
            log = self._evidence(preview_id) / "static-build.json"
            log.write_text(json.dumps({"revision": revision, "tree": tree,
                "code_executed": False}))
            return {"image_id": f"git-tree:{tree}", "build_log": str(log),
                "build_log_sha256": sha256(log.read_bytes()).hexdigest()}
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
        if mode is CandidatePreviewMode.STATIC_PREVIEW:
            return self._static_start(preview_id, revision, tree)
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
            f"add_header X-Candidate-Revision {revision} always; "
            f"add_header X-Candidate-Tree {tree} always; "
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
        if mode is CandidatePreviewMode.STATIC_PREVIEW:
            try:
                self._static_verify(preview_id, revision, tree)
                return True
            except (OSError, ValueError, EnvironmentProviderError):
                return False
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
        if mode is CandidatePreviewMode.STATIC_PREVIEW:
            return self._static_verify(preview_id, revision, tree)
        if not self.probe(preview_id, revision, tree, mode=mode):
            raise EnvironmentProviderError("Served runtime differs from the exact Candidate")
        names = self._names(preview_id)
        host_port = self._docker("port", names["proxy"], "80/tcp").stdout.strip()
        if not re.fullmatch(r"127\.0\.0\.1:\d+", host_port):
            raise EnvironmentProviderError("Served runtime has no isolated gateway")
        public_origin = f"http://{host_port}"
        origin = f"http://{names['proxy']}"

        cookie: str | None = None
        bearer = self._preview_auth_tokens.get(preview_id)
        if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME and bearer is not None:
            login_response = self._gateway_request(preview_id, "/auth/session",
                payload={"token": bearer}, headers={"Content-Type": "application/json"})
            # Older supported Candidates use bearer-only authentication.
            if login_response["status"] != 404:
                if login_response["status"] != 200:
                    raise EnvironmentProviderError("Candidate login contract failed")
                cookie = login_response["cookie"]
                if not cookie.startswith("watt_session="):
                    raise EnvironmentProviderError("Candidate session cookie is unavailable")

        def request(path: str, *, payload: dict | None = None) -> tuple[int, bytes, str, str]:
            headers = {"Content-Type": "application/json"} if payload is not None else {}
            if bearer is not None:
                headers["Authorization"] = f"Bearer {bearer}"
            if cookie is not None:
                headers["Cookie"] = cookie
            response = self._gateway_request(preview_id, path,
                payload=payload, headers=headers)
            return (response["status"], b64decode(response["body"]),
                response["content_type"], response["url"])

        observations: dict[str, object] = {
            "candidate_revision": revision,
            "candidate_tree": tree,
            "gateway": origin,
            "public_gateway": public_origin,
            "verifier_namespace": names["gateway"],
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
        if self._static_record_path(preview_id).exists():
            server = self._static_servers.pop(preview_id, None)
            if server is not None:
                server.shutdown()
                server.server_close()
            self._remove_workspace(preview_id)
            return {"static_runtime": "STOPPED"}
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
