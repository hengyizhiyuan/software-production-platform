"""Existing Native Tool contracts executed through Production Environment."""

from __future__ import annotations

import asyncio
import base64
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from uuid import UUID

from spg.domain.native_execution import (
    EffectCondition,
    ToolExecutionRequest,
    ToolExecutionResult,
    WorkspaceManifest,
)
from spg.domain.production_environment import (
    EnvironmentCommand,
    ProductionEnvironmentProvider,
    ProviderEnvironmentHandle,
)
from spg.executor.tools import (
    PUBLIC_NATIVE_TOOL_CONTRACTS,
    NativeToolRegistry,
    ToolDefinition,
    validate_generic_git_process,
)
from spg.executor.git_operations import git_operation_commands, git_operation_is_read_only
from spg.infrastructure.production_environment import GitRepositoryAcquirer


class ProductionEnvironmentNativeToolHost:
    """Implement the current Native tools while PE owns their execution location."""

    _PROCESS_ALLOWLIST = {
        "python", "python3", "pytest", "node", "npm", "git", "uv",
        "pnpm", "yarn", "pip", "poetry", "mvn", "gradle", "go", "cargo", "dotnet",
        "ruff", "mypy", "eslint", "prettier", "npx", "alembic", "rg",
        "psql", "mysql", "sqlite3", "redis-cli",
    }

    def __init__(
        self,
        *,
        provider: ProductionEnvironmentProvider,
        handle: ProviderEnvironmentHandle,
        environment_reference: str,
        workspace_reference: str,
        workspace_root: str = "/workspace/primary",
        host_repository_path: Path | None = None,
    ) -> None:
        self.provider = provider
        self.handle = handle
        self.environment_reference = environment_reference
        self.workspace_reference = workspace_reference
        self.workspace_root = workspace_root.rstrip("/")
        self.host_repository_path = None if host_repository_path is None else host_repository_path.resolve()

    @classmethod
    def from_manifest(
        cls,
        manifest: WorkspaceManifest,
        *,
        provider: ProductionEnvironmentProvider,
    ) -> "ProductionEnvironmentNativeToolHost | None":
        resources = tuple(manifest.service_resources)
        environment = cls._resource(resources, "production-environment:")
        workspace = cls._resource(resources, "production-workspace:")
        provider_identity = cls._resource(
            resources,
            "production-environment-provider:",
        )
        opaque_reference = cls._resource(
            resources,
            "production-environment-handle:",
        )
        if not any((environment, workspace, provider_identity, opaque_reference)):
            return None
        if not all((environment, workspace, provider_identity, opaque_reference)):
            raise ValueError("Production Environment service resources are incomplete")
        if provider_identity != getattr(provider, "provider_identity", None):
            raise ValueError("Production Environment Provider identity differs")
        return cls(
            provider=provider,
            handle=ProviderEnvironmentHandle(
                provider_identity=provider_identity,
                environment_id=UUID(environment),
                opaque_reference=opaque_reference,
            ),
            environment_reference=f"production-environment:{environment}",
            workspace_reference=f"production-workspace:{workspace}",
            host_repository_path=Path(manifest.mounts[0].host_path),
        )

    def registry(self) -> NativeToolRegistry:
        handlers = {
            "file.read": self.read_file,
            "file.write": self.write_file,
            "filesystem.operation": self.filesystem_operation,
            "process.run": self.run_process,
            "git.status": self.git_status,
            "git.diff": self.git_diff,
            "git.operation": self.git_operation,
            "test.run": self.run_test,
            "build.run": self.run_build,
            "dependency.sync": self.sync_dependencies,
            "preview.inspect": self.inspect_preview,
        }
        return NativeToolRegistry(
            tuple(
                ToolDefinition(
                    identity=str(contract["identity"]),
                    version=str(contract["version"]),
                    description=str(contract["description"]),
                    input_schema=dict(contract["input_schema"]),
                    effect_classification=str(contract["effect_classification"]),
                    handler=handlers[str(contract["identity"])],
                )
                for contract in PUBLIC_NATIVE_TOOL_CONTRACTS
            )
        )

    async def read_file(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        relative = self._relative(str(request.proposal.arguments["path"]))
        script = (
            "from pathlib import Path; import sys; p=Path(sys.argv[1]); "
            "sys.exit(44) if not p.is_file() else None; "
            "sys.stdout.write(p.read_text(encoding='utf-8'))"
        )
        observation = await self._execute(
            ("python", "-c", script, relative),
            cwd=self.workspace_root,
        )
        if observation.result.exit_code == 44:
            return self._result(
                request,
                "file.read",
                {
                    "path": relative,
                    "exists": False,
                    "content": None,
                    "bytes": 0,
                    "truncated": False,
                },
                observation,
                settled=True,
            )
        self._require_success(observation, "file.read")
        return self._result(
            request,
            "file.read",
            {
                "path": relative,
                "exists": True,
                "content": observation.stdout,
                "bytes": len(observation.stdout.encode("utf-8")),
                "truncated": observation.stdout_truncated,
            },
            observation,
            settled=True,
        )

    async def filesystem_operation(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Use one bounded family tool inside the isolated PE mount."""

        args = request.proposal.arguments
        operation = str(args["operation"])
        if operation not in {"search", "stat", "mkdir", "move", "delete", "diff"}:
            raise ValueError("filesystem operation is not installed")
        path = str(args["path"])
        if operation == "search" and path == ".":
            relative = "."
        else:
            relative = self._relative(path)
        destination = None
        if operation == "move":
            destination = self._relative(str(args["destination"]))
        if operation == "diff":
            observation = await self._execute(
                ("git", "-c", f"safe.directory={self.workspace_root}", "diff", "--no-ext-diff", "--", relative),
                cwd=self.workspace_root,
            )
            return self._result(request, "filesystem.operation", {
                "operation": operation, "path": relative, "diff": observation.stdout,
                "returncode": observation.result.exit_code,
                "environment_reference": self.environment_reference,
                "workspace_reference": self.workspace_reference,
            }, observation, settled=observation.result.exit_code == 0)
        query = args.get("query")
        if operation == "search" and (not isinstance(query, str) or not query or len(query) > 200):
            raise ValueError("filesystem search requires a bounded query")
        script = """import json, pathlib, sys
root = pathlib.Path.cwd().resolve()
a = json.loads(sys.argv[1]); op = a['operation']
def checked(raw):
    p = root / raw
    if not p.resolve().is_relative_to(root): raise ValueError('path escapes workspace')
    cur = root
    for part in pathlib.PurePosixPath(raw).parts:
        if part in ('', '.', '..', '.git'): raise ValueError('unsafe workspace path')
        cur = cur / part
        if cur.is_symlink(): raise ValueError('symlink path is not admitted')
    return p
p = root if a['path'] == '.' and op == 'search' else checked(a['path'])
if op == 'search':
    if not p.is_dir(): raise ValueError('search root is not a directory')
    query = a['query'].casefold(); matches = []
    for child in p.rglob('*'):
        if len(matches) >= 200: break
        if '.git' in child.relative_to(root).parts or child.is_symlink() or not child.is_file(): continue
        if query in child.name.casefold(): matches.append(str(child.relative_to(root)).replace('\\\\','/')); continue
        if child.stat().st_size <= 1024*1024:
            try:
                if query in child.read_text(encoding='utf-8').casefold(): matches.append(str(child.relative_to(root)).replace('\\\\','/'))
            except (UnicodeError, OSError): pass
    result = {'matches': matches, 'truncated': len(matches) >= 200}
elif op == 'stat':
    result = {'exists': p.exists(), 'is_file': p.is_file(), 'is_dir': p.is_dir(), 'bytes': p.stat().st_size if p.is_file() else None}
elif op == 'mkdir':
    p.mkdir(parents=True, exist_ok=False); result = {'created': True}
elif op == 'move':
    dest = checked(a['destination'])
    if not p.exists() or dest.exists(): raise ValueError('move source missing or destination exists')
    dest.parent.mkdir(parents=True, exist_ok=True); p.rename(dest); result = {'moved': True, 'destination': a['destination']}
elif op == 'delete':
    if p.is_file(): p.unlink()
    elif p.is_dir(): p.rmdir()
    else: raise ValueError('delete target missing or unsupported')
    result = {'deleted': True}
else: raise ValueError('filesystem operation is not installed')
print(json.dumps(result, sort_keys=True))
"""
        payload = {"operation": operation, "path": relative}
        if destination is not None:
            payload["destination"] = destination
        if operation == "search":
            payload["query"] = query
        observation = await self._execute(
            ("python", "-c", script, json.dumps(payload, ensure_ascii=False)),
            cwd=self.workspace_root,
        )
        output = {
            "operation": operation,
            "path": relative,
            "returncode": observation.result.exit_code,
            "result": (
                json.loads(observation.stdout)
                if observation.result.exit_code == 0 else None
            ),
            "stderr": observation.stderr,
            "environment_reference": self.environment_reference,
            "workspace_reference": self.workspace_reference,
        }
        return self._result(
            request, "filesystem.operation", output, observation,
            settled=observation.result.exit_code == 0,
        )

    async def write_file(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        relative = self._relative(str(request.proposal.arguments["path"]))
        content = request.proposal.arguments.get("content")
        if not isinstance(content, str):
            raise ValueError("file.write content must be text")
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        script = (
            "from pathlib import Path; import base64, os, sys; "
            "p=Path(sys.argv[1]); p.parent.mkdir(parents=True, exist_ok=True); "
            "t=p.with_name('.'+p.name+'.'+sys.argv[3]+'.tmp'); "
            "t.write_bytes(base64.b64decode(sys.argv[2])); os.replace(t,p)"
        )
        observation = await self._execute(
            ("python", "-c", script, relative, encoded, str(request.delivery_id)),
            cwd=self.workspace_root,
        )
        self._require_success(observation, "file.write")
        return self._result(
            request,
            "file.write",
            {"path": relative, "bytes": len(content.encode("utf-8"))},
            observation,
            settled=True,
        )

    async def run_process(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        return await self._run_argv(request, "process.run")

    async def git_status(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        return await self._run_argv(
            request,
            "git.status",
            argv=["git", "status", "--short", "--untracked-files=all"],
        )

    async def git_diff(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        return await self._run_argv(
            request,
            "git.diff",
            argv=["git", "diff", "--no-ext-diff", "--binary"],
        )

    async def git_operation(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Execute one Task Contract-granted Git operation through PE, then observe Reality."""

        arguments = request.proposal.arguments
        operation = str(arguments["operation"])
        commands = git_operation_commands(arguments)
        cwd = self._cwd(str(arguments.get("cwd", ".")))
        if operation == "fetch":
            if cwd != self.workspace_root or self.host_repository_path is None:
                raise ValueError("Git fetch requires the exact bound Production Workspace")
            observed = await asyncio.to_thread(
                GitRepositoryAcquirer().fetch_selected_branch,
                self.host_repository_path,
                str(arguments["branch"]),
            )
            branch = await self._execute(("git", "-c", f"safe.directory={cwd}", "branch", "--show-current"), cwd=cwd)
            revision = await self._execute(("git", "-c", f"safe.directory={cwd}", "rev-parse", "HEAD"), cwd=cwd)
            if branch.result.exit_code or revision.result.exit_code:
                raise ValueError("Git fetch could not observe current Workspace Reality")
            output = {
                "operation": operation,
                "branch": str(arguments["branch"]),
                "returncode": observed["returncode"],
                "stdout": observed["stdout"],
                "stderr": observed["stderr"],
                "fetched_revision": observed["fetched_revision"],
                "resulting_branch": branch.stdout.strip(),
                "resulting_revision": revision.stdout.strip(),
                "environment_reference": self.environment_reference,
                "workspace_reference": self.workspace_reference,
            }
            return ToolExecutionResult(
                delivery_id=request.delivery_id,
                tool_identity="git.operation",
                condition=(EffectCondition.SETTLED if observed["returncode"] == 0 else EffectCondition.FAILED),
                output=output,
                output_digest=sha256(json.dumps(output, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                evidence=({
                    "type": "PRODUCTION_ENVIRONMENT_GIT_FETCH",
                    "workspace_reference": self.workspace_reference,
                    "environment_reference": self.environment_reference,
                    "source": "origin",
                    "branch": str(arguments["branch"]),
                },),
            )
        observations = []
        for command in commands:
            # The isolated container UID need not match the host Workspace owner.
            # Trust only this admitted mount for this one invocation, never globally.
            safe_command = ("git", "-c", f"safe.directory={cwd}", *command[1:])
            observation = await self._execute(safe_command, cwd=cwd)
            observations.append(observation)
            if observation.result.exit_code != 0:
                if operation == "ancestry" and observation.result.exit_code == 1:
                    break
                return self._git_result(
                    request, operation, observations,
                    settled=False,
                )
        extra: dict[str, object] = {}
        if operation == "ancestry":
            extra["is_ancestor"] = observations[-1].result.exit_code == 0
        if not git_operation_is_read_only(operation):
            branch = await self._execute(("git", "-c", f"safe.directory={cwd}", "branch", "--show-current"), cwd=cwd)
            revision = await self._execute(("git", "-c", f"safe.directory={cwd}", "rev-parse", "HEAD"), cwd=cwd)
            observations.extend((branch, revision))
            if branch.result.exit_code or revision.result.exit_code:
                return self._git_result(request, operation, observations, settled=False)
            extra["resulting_branch"] = branch.stdout.strip()
            extra["resulting_revision"] = revision.stdout.strip()
        return self._git_result(request, operation, observations, settled=True, extra=extra)

    def _git_result(
        self,
        request: ToolExecutionRequest,
        operation: str,
        observations: list,
        *,
        settled: bool,
        extra: dict[str, object] | None = None,
    ) -> ToolExecutionResult:
        last = observations[-1]
        output = {
            "operation": operation,
            "cwd": str(request.proposal.arguments.get("cwd", ".")),
            "returncode": last.result.exit_code,
            "stdout": last.stdout,
            "stderr": last.stderr,
            "environment_reference": self.environment_reference,
            "workspace_reference": self.workspace_reference,
            **(extra or {}),
        }
        digest = sha256(json.dumps(output, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return ToolExecutionResult(
            delivery_id=request.delivery_id,
            tool_identity="git.operation",
            condition=EffectCondition.SETTLED if settled else EffectCondition.FAILED,
            output=output,
            output_digest=digest,
            evidence=tuple(
                {
                    "type": "PRODUCTION_ENVIRONMENT_GIT_COMMAND",
                    "digest": sha256(item.result.command.model_dump_json().encode()).hexdigest(),
                    "environment_reference": self.environment_reference,
                    "workspace_reference": self.workspace_reference,
                    "stdout_reference": item.result.stdout_reference,
                    "stderr_reference": item.result.stderr_reference,
                }
                for item in observations
            ),
        )

    async def run_test(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        argv = self._argv(request)
        allowed = (
            argv[0] == "pytest"
            or argv[:2] == ["node", "--test"]
            or (argv[0] == "node" and len(argv) >= 2 and not argv[1].startswith("-"))
            or argv[:3] in (["python", "-m", "pytest"], ["python3", "-m", "pytest"])
            or argv[:2] == ["npm", "test"]
            or argv[:3] == ["npm", "run", "test"]
            or argv[:2] in (["pnpm", "test"], ["yarn", "test"], ["cargo", "test"], ["go", "test"], ["dotnet", "test"], ["mvn", "test"], ["gradle", "test"])
            or argv[:3] == ["uv", "run", "pytest"]
        )
        if not allowed:
            raise ValueError("test.run requires a supported project-native test recipe")
        return await self._run_argv(request, "test.run", argv=argv)

    async def run_build(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        argv = self._argv(request)
        if not (
            argv[:3] in (["npm", "run", "build"], ["python", "-m", "build"])
            or argv[:2] in (["pnpm", "build"], ["yarn", "build"], ["cargo", "build"], ["go", "build"], ["dotnet", "build"], ["mvn", "package"], ["gradle", "build"], ["uv", "build"])
        ):
            raise ValueError("build.run requires a supported project-native build recipe")
        return await self._run_argv(request, "build.run", argv=argv)

    async def sync_dependencies(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        argv = self._argv(request)
        locked = (
            argv[:3] == ["uv", "sync", "--locked"]
            or argv[:2] == ["npm", "ci"]
            or argv[:3] == ["pnpm", "install", "--frozen-lockfile"]
            or argv[:3] == ["yarn", "install", "--immutable"]
            or argv[:3] == ["poetry", "install", "--sync"]
            or argv[:3] == ["cargo", "fetch", "--locked"]
            or argv[:3] == ["go", "mod", "download"]
            or argv[:3] == ["dotnet", "restore", "--locked-mode"]
            or argv[:2] == ["mvn", "dependency:go-offline"]
            or argv[:2] == ["gradle", "dependencies"]
        )
        if not locked:
            raise ValueError("dependency.sync requires a lock-governed project-native recipe")
        return await self._run_argv(request, "dependency.sync", argv=argv)

    async def inspect_preview(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        read = await self.read_file(request)
        output = read.output
        if not output.get("exists"):
            raise ValueError("preview artifact is unavailable")
        return ToolExecutionResult(
            delivery_id=request.delivery_id,
            tool_identity="preview.inspect",
            condition=read.condition,
            output={
                "path": output["path"],
                "bytes": output["bytes"],
                "content_head": output["content"],
                "truncated": output["truncated"],
                "environment_reference": self.environment_reference,
            },
            output_digest=read.output_digest,
            evidence=read.evidence,
        )

    async def _run_argv(
        self,
        request: ToolExecutionRequest,
        identity: str,
        *,
        argv: list[str] | None = None,
    ) -> ToolExecutionResult:
        argv = argv or self._argv(request)
        executable = Path(argv[0]).name.lower()
        if executable not in self._PROCESS_ALLOWLIST:
            raise ValueError(f"process executable is not allowlisted: {executable}")
        if identity == "process.run":
            validate_generic_git_process(argv)
        for argument in argv[1:]:
            candidate = Path(argument)
            if argument in {"-c", "-e", "--eval"} and executable in {
                "python",
                "python3",
                "node",
            }:
                raise ValueError("inline code execution is not admitted by process.run")
            if candidate.is_absolute() or ".." in candidate.parts:
                raise ValueError("process arguments cannot escape the execution workspace")
        cwd = self._cwd(str(request.proposal.arguments.get("cwd", ".")))
        observation = await self._execute(tuple(argv), cwd=cwd)
        output = {
            "argv": argv,
            "cwd": str(request.proposal.arguments.get("cwd", ".")),
            "process_identity": str(request.delivery_id),
            "pid": None,
            "returncode": observation.result.exit_code,
            "stdout": observation.stdout,
            "stderr": observation.stderr,
            "stdout_truncated": observation.stdout_truncated,
            "stderr_truncated": observation.stderr_truncated,
            "timed_out": False,
            "process_group_terminated": False,
            "isolation": "production-environment:container-v1",
            "environment_reference": self.environment_reference,
            "workspace_reference": self.workspace_reference,
        }
        return self._result(
            request,
            identity,
            output,
            observation,
            settled=observation.result.exit_code == 0,
        )

    async def _execute(self, argv: tuple[str, ...], *, cwd: str):
        return await asyncio.to_thread(
            self.provider.execute_observed,
            self.handle,
            EnvironmentCommand(argv=argv, working_directory=cwd),
        )

    def _result(self, request, identity, output, observation, *, settled: bool):
        encoded = json.dumps(
            output,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        digest = sha256(encoded).hexdigest()
        command_digest = sha256(
            observation.result.command.model_dump_json().encode("utf-8")
        ).hexdigest()
        return ToolExecutionResult(
            delivery_id=request.delivery_id,
            tool_identity=identity,
            condition=(EffectCondition.SETTLED if settled else EffectCondition.FAILED),
            output=output,
            output_digest=digest,
            evidence=(
                {
                    "type": "PRODUCTION_ENVIRONMENT_COMMAND",
                    "digest": command_digest,
                    "environment_reference": self.environment_reference,
                    "workspace_reference": self.workspace_reference,
                    "stdout_reference": observation.result.stdout_reference,
                    "stderr_reference": observation.result.stderr_reference,
                },
            ),
        )

    @staticmethod
    def _require_success(observation, identity: str) -> None:
        if observation.result.exit_code:
            raise ValueError(f"{identity} failed inside Production Environment")

    def _cwd(self, value: str) -> str:
        if value == ".":
            return self.workspace_root
        relative = self._relative(value)
        return f"{self.workspace_root}/{relative}"

    @staticmethod
    def _relative(value: str) -> str:
        if "\\" in value:
            raise ValueError("workspace paths must use POSIX separators")
        path = PurePosixPath(value)
        if path.is_absolute() or value in {"", "."} or ".." in path.parts:
            raise ValueError("path must be safe and workspace-relative")
        if ".git" in path.parts:
            raise ValueError("direct access to Git metadata is prohibited")
        return str(path)

    @staticmethod
    def _argv(request: ToolExecutionRequest) -> list[str]:
        argv = request.proposal.arguments.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            raise ValueError("tool argv must be a non-empty string array")
        return argv

    @staticmethod
    def _resource(resources: tuple[str, ...], prefix: str) -> str | None:
        matches = [item.removeprefix(prefix) for item in resources if item.startswith(prefix)]
        if len(matches) > 1:
            raise ValueError(f"duplicate Production Environment resource: {prefix}")
        return matches[0] if matches else None
