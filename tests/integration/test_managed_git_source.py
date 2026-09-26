from pathlib import Path
import shutil
import subprocess

import pytest

from spg.application.managed_git_source import ManagedGitSource


pytestmark = pytest.mark.postgresql


def _git(path: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(path), *args], check=True,
        capture_output=True, text=True).stdout.strip()


def test_managed_source_survives_checkout_loss_and_preserves_history(
    postgres_database, tmp_path: Path,
):
    identity = "watt://repositories/test-managed-source"
    checkout = tmp_path / "worker-a" / "repository"
    checkout.mkdir(parents=True)
    _git(checkout, "init", "-b", "main")
    _git(checkout, "config", "user.name", "Watt test")
    _git(checkout, "config", "user.email", "watt@example.invalid")
    (checkout / "README.md").write_text("initial\n", encoding="utf-8")
    _git(checkout, "add", ".")
    _git(checkout, "commit", "-m", "initial")
    first = _git(checkout, "rev-parse", "HEAD")
    store = ManagedGitSource(postgres_database)
    observed = store.sync(identity, checkout)
    assert observed["revision"] == first
    shutil.rmtree(checkout.parent)

    recovered = tmp_path / "worker-b" / "repository"
    assert store.recover(identity, recovered)["revision"] == first
    assert _git(recovered, "rev-parse", "HEAD") == first
    _git(recovered, "config", "user.name", "Watt test")
    _git(recovered, "config", "user.email", "watt@example.invalid")
    (recovered / "README.md").write_text("second\n", encoding="utf-8")
    _git(recovered, "add", ".")
    _git(recovered, "commit", "-m", "second")
    second = _git(recovered, "rev-parse", "HEAD")
    store.sync(identity, recovered)
    bundle, exported = store.export_bundle(identity)
    assert bundle and exported["revision"] == second
    exported_path = tmp_path / "exported.bundle"
    exported_path.write_bytes(bundle)
    assert subprocess.run(["git", "bundle", "verify", str(exported_path)],
        cwd=recovered, capture_output=True).returncode == 0
    shutil.rmtree(recovered.parent)

    final = tmp_path / "worker-c" / "repository"
    assert store.recover(identity, final)["revision"] == second
    assert _git(final, "rev-list", "--count", "HEAD") == "2"
    assert _git(final, "rev-parse", "HEAD~1") == first


def test_managed_work_branch_has_its_own_recoverable_exact_history(
    postgres_database, tmp_path: Path,
):
    base = tmp_path / "base"
    base.mkdir()
    _git(base, "init", "-b", "main")
    _git(base, "config", "user.name", "Watt test")
    _git(base, "config", "user.email", "watt@example.invalid")
    (base / "README.md").write_text("base\n")
    _git(base, "add", ".")
    _git(base, "commit", "-m", "baseline")
    store = ManagedGitSource(postgres_database)
    store.sync("watt://repositories/branch-base", base)
    branch = tmp_path / "worker-a" / "branch"
    branch.parent.mkdir()
    subprocess.run(["git", "clone", str(base), str(branch)], check=True,
        capture_output=True)
    _git(branch, "switch", "-c", "feature")
    _git(branch, "config", "user.name", "Watt test")
    _git(branch, "config", "user.email", "watt@example.invalid")
    (branch / "feature.py").write_text("print('feature')\n")
    _git(branch, "add", ".")
    _git(branch, "commit", "-m", "feature")
    revision = _git(branch, "rev-parse", "HEAD")
    identity = "watt://work-branches/test-feature"
    store.sync(identity, branch, internal_branch=True)
    shutil.rmtree(branch.parent)
    shutil.rmtree(base)
    recovered = tmp_path / "worker-b" / "branch"
    assert store.recover(identity, recovered)["revision"] == revision
    assert _git(recovered, "branch", "--show-current") == "feature"
    assert _git(recovered, "rev-list", "--count", "HEAD") == "2"
    assert _git(recovered, "show", "HEAD:feature.py") == "print('feature')"
