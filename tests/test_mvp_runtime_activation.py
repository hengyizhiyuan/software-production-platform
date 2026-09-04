"""Focused contracts for Trusted Baseline / active Runtime convergence."""

from pathlib import Path
import subprocess

import pytest

from spg.domain.runtime_activation import ActiveRuntimeEvidence, RuntimeActivationState
from spg.infrastructure.git_checkout import GitTrustedCheckoutSynchronizer
from spg.infrastructure.runtime_activation import (
    GitLocalRuntimeActivation,
    RuntimeActivationError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, str, str, str, str, str]:
    repository = tmp_path / "repository"
    web = repository / "src" / "spg" / "web"
    web.mkdir(parents=True)
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SPG Test")
    _git(repository, "config", "user.email", "spg-test@example.invalid")
    (repository / "src" / "spg" / "__init__.py").write_text("\n", encoding="utf-8")
    (web / "app.js").write_text("const composer = 'expanded';\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline zero")
    baseline_zero = _git(repository, "rev-parse", "HEAD")

    (web / "app.js").write_text(
        "const WORK_COMPOSER_STATE_KEY = 'spg.workComposer.expanded';\n",
        encoding="utf-8",
    )
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "persist composer state")
    baseline_one = _git(repository, "rev-parse", "HEAD")
    baseline_one_tree = _git(repository, "rev-parse", "HEAD^{tree}")
    baseline_zero_tree = _git(repository, "rev-parse", f"{baseline_zero}^{{tree}}")
    _git(repository, "read-tree", "--reset", "-u", baseline_zero)
    return (
        repository,
        "refs/heads/main",
        baseline_zero,
        baseline_zero_tree,
        baseline_one,
        baseline_one_tree,
    )


def _evidence(repository: Path, revision: str, tree: str) -> ActiveRuntimeEvidence:
    return ActiveRuntimeEvidence(
        active_application_revision=revision,
        active_repository_tree_identity=tree,
        active_source_package_fingerprint=_git(
            repository, "rev-parse", f"{revision}:src/spg"
        ),
        active_static_asset_fingerprint=_git(
            repository, "rev-parse", f"{revision}:src/spg/web"
        ),
        active_source_root=str((repository / "src").resolve()),
    )


def test_act_01_02_03_04_08_trust_does_not_imply_activation(tmp_path: Path) -> None:
    repository, _, b0, b0_tree, b1, b1_tree = _repository(tmp_path)

    projection = GitLocalRuntimeActivation().inspect(
        repository_path=repository,
        active=_evidence(repository, b0, b0_tree),
        trusted_revision=b1,
        trusted_tree_identity=b1_tree,
    )

    assert projection.state is RuntimeActivationState.ACTIVATION_REQUIRED
    assert projection.active_application_revision == b0
    assert projection.current_trusted_baseline_revision == b1
    assert "not active" in projection.reason


def test_act_05_06_09_10_12_15_restart_activates_one_exact_revision(
    tmp_path: Path,
) -> None:
    repository, reference, b0, _, b1, b1_tree = _repository(tmp_path)
    synchronizer = GitTrustedCheckoutSynchronizer()
    synchronized = synchronizer.synchronize(
        repository_path=repository,
        authoritative_ref=reference,
        source_revision=b0,
        trusted_revision=b1,
        trusted_tree_identity=b1_tree,
    )

    activation = GitLocalRuntimeActivation().prepare(
        repository_path=repository,
        trusted_revision=b1,
        trusted_tree_identity=b1_tree,
        previous_active_revision=b0,
    )
    repeated = GitLocalRuntimeActivation().prepare(
        repository_path=repository,
        trusted_revision=b1,
        trusted_tree_identity=b1_tree,
        previous_active_revision=b1,
    )
    projection = GitLocalRuntimeActivation().inspect(
        repository_path=repository,
        active=activation,
        trusted_revision=b1,
        trusted_tree_identity=b1_tree,
    )

    assert synchronized.repository_revision == b1
    assert activation == repeated
    assert activation.active_application_revision == b1
    assert activation.active_repository_tree_identity == b1_tree
    assert activation.active_source_package_fingerprint == _git(
        repository, "rev-parse", f"{b1}:src/spg"
    )
    assert activation.active_static_asset_fingerprint == _git(
        repository, "rev-parse", f"{b1}:src/spg/web"
    )
    assert projection.state is RuntimeActivationState.ACTIVE_AT_TRUSTED_BASELINE
    assert _git(repository, "status", "--porcelain=v1") == ""
    assert "WORK_COMPOSER_STATE_KEY" in (
        repository / "src" / "spg" / "web" / "app.js"
    ).read_text(encoding="utf-8")


def test_act_07_dirty_checkout_is_preserved_and_blocked(tmp_path: Path) -> None:
    repository, _, b0, _, b1, b1_tree = _repository(tmp_path)
    target = repository / "src" / "spg" / "web" / "app.js"
    target.write_text("independent operator change\n", encoding="utf-8")

    with pytest.raises(RuntimeActivationError, match="checkout is not clean"):
        GitLocalRuntimeActivation().prepare(
            repository_path=repository,
            trusted_revision=b1,
            trusted_tree_identity=b1_tree,
            previous_active_revision=b0,
        )

    assert target.read_text(encoding="utf-8") == "independent operator change\n"


@pytest.mark.parametrize(
    "path",
    [
        "Dockerfile",
        "pyproject.toml",
        "uv.lock",
        "docker/start_app.py",
        "migrations/versions/change.py",
        "compose.yaml",
    ],
)
def test_act_11_image_or_dependency_changes_require_rebuild(
    tmp_path: Path,
    path: str,
) -> None:
    repository, _, b0, b0_tree, _, _ = _repository(tmp_path)
    target = repository / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("image-bound change\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "image-bound change")
    trusted = _git(repository, "rev-parse", "HEAD")
    trusted_tree = _git(repository, "rev-parse", "HEAD^{tree}")

    projection = GitLocalRuntimeActivation().inspect(
        repository_path=repository,
        active=_evidence(repository, b0, b0_tree),
        trusted_revision=trusted,
        trusted_tree_identity=trusted_tree,
    )

    assert projection.state is RuntimeActivationState.IMAGE_REBUILD_REQUIRED
    assert path in projection.image_rebuild_paths


def test_act_13_14_16_activation_is_not_authority_or_product_acceptance() -> None:
    domain = (PROJECT_ROOT / "src/spg/domain/runtime_activation.py").read_text(
        encoding="utf-8"
    )
    startup = (PROJECT_ROOT / "docker/start_app.py").read_text(encoding="utf-8")
    http = (PROJECT_ROOT / "src/spg/api/http.py").read_text(encoding="utf-8")

    assert "Human" not in domain
    assert "Acceptance" not in domain
    assert "Provider" not in domain
    assert "prepare_local_runtime_activation(repository)" in startup
    assert startup.index("synchronize_repository_checkout(repository)") < startup.index(
        "prepare_local_runtime_activation(repository)"
    )
    assert "os.execvpe(" in startup
    assert 'environment["PYTHONPATH"]' in startup
    assert 'environment["SPG_ACTIVE_RUNTIME_REVISION"]' in startup
    assert '"/api/runtime-activation"' in http
