import pytest
from pydantic import ValidationError
from spg.application.delivery import read_artifact
from spg.domain.product import ProductInvariantViolation
from spg.domain.delivery import DeliveryTargetRequest, HumanAcceptanceRequest

@pytest.mark.parametrize("path", ["../secret.md", "/secret.md", ".git/config.md", "x\\y.md", "x:y.md", "docs/../secret.md", "docs//file.md", "page.html"])
def test_delivery_paths_cannot_address_unadmitted_content(path):
    with pytest.raises(ProductInvariantViolation):
        read_artifact("unused", "a"*40, path)

@pytest.mark.parametrize("revision", ["HEAD", "main", "--help", "a"*39, "g"*40])
def test_delivery_requires_immutable_commit_identity(revision):
    with pytest.raises(ProductInvariantViolation):
        read_artifact("unused", revision, "docs/design.md")


def test_target_and_human_decision_require_substantive_input():
    with pytest.raises(ValidationError):
        DeliveryTargetRequest(kind="DOCUMENT_PACKAGE", title="Design", acceptance_criteria=(" ",), authority_identity="human:test")
    with pytest.raises(ValidationError):
        HumanAcceptanceRequest(manifest_fingerprint="a"*64, decision="ACCEPT", authority_identity=" ", rationale="Read it")


@pytest.mark.parametrize("recipe", [
    {"adapter": "SHELL", "entrypoint": "index.html"},
    {"adapter": "STATIC_WEB", "entrypoint": "../index.html"},
    {"adapter": "STATIC_WEB", "entrypoint": "index.js"},
    {"adapter": "STATIC_WEB", "entrypoint": "x//index.html"},
])
def test_software_target_cannot_supply_host_commands_or_unsafe_entrypoints(recipe):
    with pytest.raises(ValidationError):
        DeliveryTargetRequest(kind="SOFTWARE_ARTIFACT", title="Inventory", acceptance_criteria=("Can operate inventory",),
            authority_identity="human:test", software_form="WEB_APPLICATION", runtime_recipe=recipe)


def test_software_target_requires_explicit_supported_runtime_and_form():
    request = dict(kind="SOFTWARE_ARTIFACT", title="Inventory", acceptance_criteria=("Can operate inventory",), authority_identity="human:test")
    with pytest.raises(ValidationError):
        DeliveryTargetRequest(**request)
    with pytest.raises(ValidationError):
        DeliveryTargetRequest(**request, software_form="CLI_TOOL", runtime_recipe={"adapter":"STATIC_WEB"})
    software = DeliveryTargetRequest(**request, software_form="WEB_APPLICATION", runtime_recipe={"adapter":"STATIC_WEB"})
    assert software.kind.value == "SOFTWARE_ARTIFACT"
