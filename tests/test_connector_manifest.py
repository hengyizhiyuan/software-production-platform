from spg.application.connector_manifest import built_in_executable_capabilities
from spg.application.production_intelligence import default_system_capability_reality
from spg.domain.connectors import ConnectorAvailability, SideEffectLevel
from spg.executor.tools import PUBLIC_NATIVE_TOOL_CONTRACTS
from spg.executor.tools import validate_generic_git_process
import pytest


def test_system_capability_reality_contains_truthful_executable_inventory() -> None:
    reality = default_system_capability_reality()
    entries = {item.capability_id: item for item in reality.executable_capabilities}
    assert len(entries) == len(reality.executable_capabilities)
    assert {item.capability_family for item in entries.values()} == {
        "filesystem", "shell", "git", "github", "gitlab", "gitee", "http",
        "package", "build", "test", "quality", "container", "preview",
        "browser", "database", "migration", "artifact", "secret", "ssh",
        "ci", "deployment", "object_storage", "observability", "issue",
        "mini_program", "web",
    }
    assert entries["git.branch.create"].availability is ConnectorAvailability.AVAILABLE
    assert entries["git.branch.create"].execution_provider == "native-tool:git.operation"
    assert entries["github.push"].availability is ConnectorAvailability.UNAVAILABLE
    assert entries["github.push"].credential_requirements == ("github.write",)
    assert entries["github.push"].side_effect_level is SideEffectLevel.EXTERNAL_WRITE
    assert "delivery.authorize" in entries["github.push"].permissions_required
    assert entries["http.request"].availability is ConnectorAvailability.UNAVAILABLE
    assert entries["github.repository.search"].availability is ConnectorAvailability.AVAILABLE
    assert entries["github.resource.fetch"].availability is ConnectorAvailability.AVAILABLE
    assert entries["github.code.search"].credential_requirements == ("github.read",)
    assert entries["web.search"].credential_requirements == ("brave.search",)
    assert entries["web.resource.fetch"].availability is ConnectorAvailability.AVAILABLE
    assert all(entries[name].side_effect_level is SideEffectLevel.READ for name in (
        "github.repository.search", "github.code.search", "github.issue.search",
        "github.resource.fetch", "web.search", "web.resource.fetch",
    ))
    assert all(
        item.execution_provider != "unbound"
        for item in entries.values()
        if item.availability is ConnectorAvailability.AUTHORIZATION_REQUIRED
    )


def test_native_tool_contracts_have_installed_connector_backing() -> None:
    providers = {
        item.execution_provider
        for item in built_in_executable_capabilities()
        if item.availability is ConnectorAvailability.AVAILABLE
    }
    assert {
        f"native-tool:{contract['identity']}"
        for contract in PUBLIC_NATIVE_TOOL_CONTRACTS
    } <= providers


def test_generic_process_cannot_bypass_git_delivery_authority() -> None:
    validate_generic_git_process(["git", "status"])
    validate_generic_git_process(["git", "branch", "--show-current"])
    for argv in (
        ["git", "push", "origin", "main"],
        ["git", "-c", "alias.ship=push", "ship"],
        ["git", "switch", "-c", "unadmitted"],
    ):
        with pytest.raises(ValueError, match="governed Git capability"):
            validate_generic_git_process(argv)
