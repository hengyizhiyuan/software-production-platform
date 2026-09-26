"""A Human nav-link request admits only repository-proven necessary paths."""

from pathlib import Path
import subprocess
from uuid import uuid4

from spg.domain.refinement import RepositoryChangeProposalRequest
from spg.providers.repository_change_proposal import RepositoryAwareChangeProposalProvider


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def test_nav_link_discovers_markup_without_promoting_adjacent_files(tmp_path: Path) -> None:
    repository = tmp_path / "source"
    (repository / "src/spg/web").mkdir(parents=True)
    (repository / "tests").mkdir()
    _git(repository, "init", "-b", "main")
    (repository / "src/spg/web/index.html").write_text(
        '<header class="topbar"><nav><a href="/delivery">Deliveries</a></nav></header>',
        encoding="utf-8",
    )
    (repository / "src/spg/web/app.js").write_text(
        "const app = document.querySelector('main');\n", encoding="utf-8",
    )
    (repository / "src/spg/web/styles.css").write_text(
        ".topbar { display: flex; }\n", encoding="utf-8",
    )
    (repository / "tests/test_ui.py").write_text(
        "def test_smoke(): pass\n", encoding="utf-8",
    )
    _git(repository, "add", ".")
    _git(repository, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "commit", "-m", "baseline")
    revision = _git(repository, "rev-parse", "HEAD")

    proposal = RepositoryAwareChangeProposalProvider().propose(
        RepositoryChangeProposalRequest(
            work_id=uuid4(),
            refined_code_intent=(
                "在现有网站顶部导航栏增加一个“关于我们”的文字链接，链接到 /about。"
            ),
            constraints=("改动限于在现有网站顶部导航栏新增一个文字链接",),
            engineering_resource_id=uuid4(),
            repository_identity="https://example.invalid/source.git",
            repository_location=str(repository),
            source_baseline_id=uuid4(), source_ref="refs/heads/main",
            source_revision=revision,
        )
    )

    assert [target.path for target in proposal.required_targets] == [
        "src/spg/web/index.html"
    ]
    assert not any(target.path.startswith("tests/") for target in proposal.required_targets)

    fallback = RepositoryAwareChangeProposalProvider().propose(
        RepositoryChangeProposalRequest(
            work_id=uuid4(), refined_code_intent="Improve bounded behavior",
            engineering_resource_id=uuid4(),
            repository_identity="https://example.invalid/source.git",
            repository_location=str(repository), source_baseline_id=uuid4(),
            source_ref="refs/heads/main", source_revision=revision,
            candidate_targets=("src/spg/web/app.js",),
        )
    )
    assert [target.path for target in fallback.required_targets] == [
        "src/spg/web/app.js"
    ]
    assert "Human did not name" in fallback.required_targets[0].rationale
