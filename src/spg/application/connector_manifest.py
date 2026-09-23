"""Repository-versioned executable part of System Capability Reality.

An AVAILABLE entry names an existing executable boundary. Other entries are
discoverable capability gaps, never promises of an installed integration.
"""

from __future__ import annotations

from spg.domain.connectors import (
    CapabilityScope,
    ConnectorAvailability,
    ConnectorMaturity,
    ExecutableCapability,
    SideEffectLevel,
)


_PROVENANCE = ("src/spg/application/connector_manifest.py",)


def _cap(
    family: str,
    operation: str,
    *,
    provider: str = "unbound",
    effect: SideEffectLevel = SideEffectLevel.READ,
    permissions: tuple[str, ...] = (),
    credentials: tuple[str, ...] = (),
    connector: str | None = None,
    adapter_ready: bool = False,
) -> ExecutableCapability:
    provider_installed = provider != "unbound"
    available = provider_installed and not adapter_ready and not credentials
    return ExecutableCapability(
        capability_id=f"{family}.{operation}",
        connector_id=connector or f"builtin:{family}",
        capability_family=family,
        operation=operation,
        scope=CapabilityScope.PLATFORM,
        owner_id="Watt",
        maturity=(ConnectorMaturity.BUILT_IN if available else ConnectorMaturity.UNAVAILABLE),
        availability=(
            ConnectorAvailability.AVAILABLE
            if available
            else ConnectorAvailability.AUTHORIZATION_REQUIRED
            if provider_installed and credentials
            else ConnectorAvailability.ADAPTER_READY
            if provider_installed and adapter_ready
            else ConnectorAvailability.UNAVAILABLE
        ),
        permissions_required=permissions,
        credential_requirements=credentials,
        side_effect_level=effect,
        execution_provider=provider,
        version="1",
        provenance=_PROVENANCE,
    )


def built_in_executable_capabilities() -> tuple[ExecutableCapability, ...]:
    """Only backed operations are marked executable; no shell-command catalog."""

    W = SideEffectLevel.WORKSPACE_MUTATION
    E = SideEffectLevel.EXTERNAL_WRITE
    D = SideEffectLevel.DESTRUCTIVE
    entries = (
        _cap("filesystem", "read", provider="native-tool:file.read"),
        _cap("filesystem", "write", provider="native-tool:file.write", effect=W, permissions=("work.workspace.write",)),
        _cap("filesystem", "search", provider="native-tool:filesystem.operation"),
        _cap("filesystem", "stat", provider="native-tool:filesystem.operation"),
        _cap("filesystem", "mkdir", provider="native-tool:filesystem.operation", effect=W),
        _cap("filesystem", "move", provider="native-tool:filesystem.operation", effect=W),
        _cap("filesystem", "delete", provider="native-tool:filesystem.operation", effect=D, permissions=("work.filesystem.delete",)),
        _cap("filesystem", "diff", provider="native-tool:filesystem.operation"),
        _cap("shell", "execute", provider="native-tool:process.run", effect=W, permissions=("work.command.execute",)),
        _cap("shell", "background"),
        _cap("git", "repository.acquire", provider="production-environment:git-acquirer", effect=W),
        _cap("git", "branch.create", provider="native-tool:git.operation", effect=W, permissions=("work.branch.create",)),
        _cap("git", "branch.current", provider="native-tool:git.operation"),
        _cap("git", "status", provider="native-tool:git.status"),
        _cap("git", "diff", provider="native-tool:git.diff"),
        _cap("git", "branch.list", provider="native-tool:git.operation"),
        _cap("git", "checkout", provider="native-tool:git.operation", effect=W),
        _cap("git", "fetch", provider="native-tool:git.operation", effect=W),
        _cap("git", "revision.checkout", provider="native-tool:git.operation", effect=W),
        _cap("git", "log", provider="native-tool:git.operation"),
        _cap("git", "ancestry", provider="native-tool:git.operation"),
        _cap("git", "commit", provider="native-tool:git.operation", effect=W),
        _cap("git", "tag", provider="native-tool:git.operation", effect=W),
        _cap("git", "remote.inspect", provider="native-tool:git.operation"),
        _cap("github", "push", effect=E, credentials=("github.write",), permissions=("delivery.authorize",)),
        _cap("github", "pr.prepare", effect=E, credentials=("github.write",), permissions=("delivery.authorize",)),
        _cap("github", "repository.metadata", credentials=("github.read",)),
        _cap("gitlab", "push", effect=E, credentials=("gitlab.write",), permissions=("delivery.authorize",)),
        _cap("gitlab", "mr.prepare", effect=E, credentials=("gitlab.write",), permissions=("delivery.authorize",)),
        _cap("gitee", "push", effect=E, credentials=("gitee.write",), permissions=("delivery.authorize",)),
        _cap("http", "request"),
        _cap("package", "sync", provider="native-tool:dependency.sync", effect=W),
        _cap("build", "run", provider="native-tool:build.run", effect=W),
        _cap("test", "run", provider="native-tool:test.run", effect=W),
        _cap("quality", "run", provider="native-tool:process.run", effect=W, adapter_ready=True),
        _cap("container", "execute", provider="production-environment:execute-observed", effect=W),
        _cap("container", "lifecycle", provider="production-environment:provider", effect=W),
        _cap("preview", "inspect", provider="native-tool:preview.inspect"),
        _cap("preview", "lifecycle", provider="production-environment:preview-runtime", effect=W),
        _cap("browser", "automate"),
        _cap("database", "query", provider="native-tool:process.run", adapter_ready=True),
        _cap("database", "mutate", provider="native-tool:process.run", effect=D, permissions=("work.database.mutate",), adapter_ready=True),
        _cap("migration", "run", provider="native-tool:process.run", effect=D, permissions=("work.migration.apply",), adapter_ready=True),
        _cap("artifact", "reference", provider="production-record:artifact-reference"),
        _cap("secret", "inject"),
        _cap("ssh", "execute", effect=E, credentials=("ssh.host",)),
        _cap("ci", "status", credentials=("remote.ci.read",)),
        _cap("deployment", "run", effect=E, credentials=("deployment.write",), permissions=("delivery.authorize",)),
        _cap("object_storage", "upload", effect=E, credentials=("object_storage.write",)),
        _cap("observability", "logs", provider="production-environment:runtime-logs"),
        _cap("issue", "update", effect=E, credentials=("issue.write",)),
        _cap("mini_program", "build", provider="native-tool:build.run", effect=W, adapter_ready=True),
        _cap("mini_program", "upload", effect=E, credentials=("wechat.upload",)),
    )
    identities = [item.capability_id for item in entries]
    if len(identities) != len(set(identities)):
        raise ValueError("built-in executable capability identities must be unique")
    return entries
