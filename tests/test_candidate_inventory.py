"""A documentation Candidate in a large repository remains exactly downloadable."""

from pathlib import Path
import subprocess

import pytest

from spg.application.delivery import candidate_change_diff, candidate_file_inventory
from spg.domain.product import ProductInvariantViolation


def test_document_candidate_uses_only_exact_artifact_in_large_repository(tmp_path: Path) -> None:
    repo = tmp_path / "source"
    repo.mkdir()
    for command in (("init",), ("config", "user.email", "test@example.invalid"), ("config", "user.name", "Test")):
        subprocess.run(["git", "-C", str(repo), *command], check=True, capture_output=True)
    (repo / "docs").mkdir()
    (repo / "docs" / "review.md").write_text("# Exact review\n", encoding="utf-8")
    (repo / "index.html").write_text("<h1>Unrelated site</h1>", encoding="utf-8")
    for number in range(501):
        (repo / f"source-{number:03d}.txt").write_text("source", encoding="utf-8")
    for command in (("add", "."), ("commit", "-m", "Candidate")):
        subprocess.run(["git", "-C", str(repo), *command], check=True, capture_output=True)
    revision = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()

    paths, entrypoint = candidate_file_inventory(str(repo), revision, ("docs/review.md",))
    assert paths == ["docs/review.md"]
    assert entrypoint is None
    paths, entrypoint = candidate_file_inventory(str(repo), revision, ("index.html",))
    assert paths == ["index.html"]
    assert entrypoint is None
    with pytest.raises(ProductInvariantViolation, match="absent"):
        candidate_file_inventory(str(repo), revision, ("docs/missing.md",))

    (repo / "index.html").write_text('<h1>Review</h1><a href="https://docs.gonglv.work">工律使用文档</a>', encoding="utf-8")
    for command in (("add", "index.html"), ("commit", "-m", "Add documentation link")):
        subprocess.run(["git", "-C", str(repo), *command], check=True, capture_output=True)
    updated_revision = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    diff = candidate_change_diff(str(repo), updated_revision, ("index.html",))
    assert '+<h1>Review</h1><a href="https://docs.gonglv.work">工律使用文档</a>' in diff
    assert "source-000.txt" not in diff
