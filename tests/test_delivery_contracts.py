import pytest
from pathlib import Path
import subprocess
from types import SimpleNamespace
from uuid import uuid4
from pydantic import ValidationError
from spg.application.delivery import DeliveryApplicationService, read_artifact
from spg.domain.product import ProductInvariantViolation
from spg.domain.delivery import DeliveryTargetRequest, HumanAcceptanceRequest, SoftwareRuntimeRecipe
from spg.domain.verification import VerificationResultValue

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
    {"adapter": "FULL_APPLICATION_RUNTIME", "entrypoint": "index.html"},
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
    full_application = DeliveryTargetRequest(**request, software_form="WEB_APPLICATION",
        runtime_recipe={"adapter": "FULL_APPLICATION_RUNTIME", "entrypoint": None})
    assert full_application.runtime_recipe.adapter == "FULL_APPLICATION_RUNTIME"


def test_full_application_delivery_packages_exact_supported_runtime_tree(
    tmp_path: Path, monkeypatch,
):
    repository = tmp_path / "repo"
    repository.mkdir()
    def git(*arguments):
        return subprocess.run(["git", "-C", str(repository), *arguments],
            check=True, capture_output=True, text=True).stdout.strip()
    git("init", "-b", "main")
    git("config", "user.name", "Delivery Test")
    git("config", "user.email", "delivery@example.invalid")
    (repository / "README.md").write_text("baseline\n")
    git("add", ".")
    git("commit", "-m", "baseline")
    baseline = git("rev-parse", "HEAD")
    files = {
        "Dockerfile": "FROM python:3.13 AS native-verification\nCOPY . /app\n",
        "pyproject.toml": "[project]\nname='example'\nversion='0.1'\n",
        "uv.lock": "version = 1\n",
        "alembic.ini": "[alembic]\nscript_location = migrations\n",
        "docker/start_app.py": "print('ready')\n",
        "migrations/versions/001.py": "revision = '001'\n",
        "src/app.py": "print('serving')\n",
    }
    for name, content in files.items():
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    for index in range(510):
        path = repository / "docs" / f"reference-{index:03d}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Historical documentation\n")
    (repository / "docs" / "oversize.png").write_bytes(b"x" * (1024 * 1024 + 1))
    git("add", ".")
    git("commit", "-m", "full application")
    revision = git("rev-parse", "HEAD")
    work_unit_id, verification_id = uuid4(), uuid4()
    record = SimpleNamespace(result=VerificationResultValue.PASS,
        proposed_commit_identity=revision, work_unit_id=work_unit_id,
        obligation="PYTEST_TARGET:tests/test_app.py",
        model_dump=lambda mode: {"result": "PASS", "obligation": "PYTEST_TARGET:tests/test_app.py"})
    unit = SimpleNamespace(completion_contract=SimpleNamespace(
        change_contract=object()))
    class Store:
        def __init__(self, _session):
            pass
        def work_unit(self, identity):
            return unit if identity == work_unit_id else None
        def verification_record(self, identity):
            return record if identity == verification_id else None
    monkeypatch.setattr("spg.application.delivery.RuntimeStore", Store)
    target = SimpleNamespace(software_form="WEB_APPLICATION",
        runtime_recipe=SoftwareRuntimeRecipe(adapter="FULL_APPLICATION_RUNTIME",
            entrypoint=None))
    commit = SimpleNamespace(satisfied_work_unit_ids=(work_unit_id,),
        verification_record_ids=(verification_id,), repository_revision=revision,
        expected_source_repository_revision=baseline)
    resource = SimpleNamespace(location_ref=str(repository),
        authoritative_ref="refs/heads/main")
    software, paths = DeliveryApplicationService._software_basis(
        None, target, None, commit, resource)
    assert set(files).issubset(paths)
    assert not any(path.startswith("docs/") for path in paths)
    assert software.runtime_recipe.adapter == "FULL_APPLICATION_RUNTIME"
    assert any(item["path"] == "src/app.py" for item in software.changed_files)
    assert any("isolated PostgreSQL" in step for step in software.reproduction)
