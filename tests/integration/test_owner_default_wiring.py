from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from spg.application.bootstrap import bootstrap
from spg.application.control_room import ControlRoomService
from spg.config import Settings


pytestmark = [pytest.mark.postgresql, pytest.mark.cross_repository]


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(["git", "-C", str(repository), *arguments],
        check=True, capture_output=True, text=True).stdout.strip()


def test_required_owner_runtime_reobserves_superseded_repository_across_sessions(
    postgres_database, tmp_path: Path,
):
    pytest.importorskip("ecf.runtime")
    pytest.importorskip("guardian.runtime")
    repository = tmp_path / "source"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Watt test")
    _git(repository, "config", "user.email", "watt@example.invalid")
    (repository / "README.md").write_text("first\n")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "first")
    first_revision = _git(repository, "rev-parse", "HEAD")
    settings = Settings(executor_adapter="watt-native", owner_runtime_mode="REQUIRED",
        owner_runtime_store_root=tmp_path / "owners",
        native_executor_production_environment_store_root=tmp_path / "pe",
        workspace_root=tmp_path / "workspaces")
    first_work = bootstrap(settings).work(postgres_database)
    assert first_work.production_recorder is not None
    identity = "test://owner-default-wiring"
    first = first_work.production_recorder.reality.discover_repository_payload(
        repository, repository_identity=identity)

    # A new Watt session reads the ECF-owned latest pointer.  A changed Git
    # revision must supersede the previous Reality before it is consumed.
    second_work = bootstrap(settings).work(postgres_database)
    control = ControlRoomService(postgres_database, second_work)
    resource = SimpleNamespace(repository_identity=identity,
        authoritative_ref="refs/heads/main")
    same = control._owner_repository_reality(resource, repository, first_revision)
    assert same["reality_id"] == str(first["reality_id"])
    (repository / "README.md").write_text("second\n")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "second")
    second_revision = _git(repository, "rev-parse", "HEAD")
    updated = control._owner_repository_reality(resource, repository, second_revision)
    assert updated["revision"] == second_revision
    assert updated["reality_id"] != same["reality_id"]
    assert updated["superseded_previous"] is True
