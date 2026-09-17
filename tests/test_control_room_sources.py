"""Read-only Work source browser stays tied to governed repository Reality."""

from pathlib import Path
import subprocess
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.application.control_room import ControlRoomError, ControlRoomService


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def test_work_sources_are_relevant_pinned_read_only_and_exclude_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    (root / "docs").mkdir()
    (root / "src").mkdir()
    (root / "docs" / "plan.md").write_text("# Plan\n- Keep this source", encoding="utf-8")
    (root / "src" / "main.py").write_text("def produce():\n    return True\n", encoding="utf-8")
    (root / "src" / "other.py").write_text("pass\n", encoding="utf-8")
    (root / "src" / "alias.py").symlink_to("main.py")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "baseline")
    revision = _git(root, "rev-parse", "HEAD")
    work_id = uuid4()
    work = SimpleNamespace(
        artifact_target=None, change_contract=None,
        change_proposal=SimpleNamespace(proposed_targets=(SimpleNamespace(path="src/main.py"),)),
    )
    resource = SimpleNamespace(repository_identity="example", context_references=(
        SimpleNamespace(repository_relative_path="docs/plan.md"),
    ))
    work_service = SimpleNamespace(
        get_work=lambda _id: work,
        get_work_result=lambda _id: SimpleNamespace(produced_artifacts=()),
    )
    service = ControlRoomService(None, work_service)
    service._repository = lambda _id: (work, resource, root, revision)

    sources = service.sources(work_id)
    assert sources["selection"] == "WORK_RELEVANT"
    assert [item["path"] for item in sources["sources"]] == ["docs/plan.md", "src/main.py", "src/other.py"]
    assert [item["path"] for item in sources["sources"] if item["relevant"]] == ["docs/plan.md", "src/main.py"]
    assert service.file(work_id, "src/main.py", revision)["content"].startswith("def produce")
    with pytest.raises(ControlRoomError):
        service.file(work_id, "../secret.py", revision)
    assert service.file(work_id, "src/other.py", revision)["content"] == "pass\n"
    with pytest.raises(ControlRoomError):
        service.file(work_id, "src/main.py", "0" * 40)


def test_reality_browser_has_no_fabricated_files_when_work_has_no_matches(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("# Actual repository overview\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "baseline")
    revision = _git(root, "rev-parse", "HEAD")
    work = SimpleNamespace(artifact_target=None, change_contract=None, change_proposal=None)
    resource = SimpleNamespace(repository_identity="example", context_references=())
    service = ControlRoomService(None, SimpleNamespace(get_work_result=lambda _id: SimpleNamespace(produced_artifacts=())))
    service._repository = lambda _id: (work, resource, root, revision)
    sources = service.sources(uuid4())
    assert sources["selection"] == "REPOSITORY_OVERVIEW"
    assert [item["path"] for item in sources["sources"]] == ["README.md"]
