from pathlib import Path
import subprocess
from uuid import uuid4

from pydantic import ValidationError
import pytest

from spg.domain.change import (
    ChangeOperation,
    ChangeTargetShape,
    CodeChangeContract,
    CodeChangeTarget,
    CodeVerificationKind,
    CodeVerificationObligation,
)
from spg.domain.verification import VerificationResultValue
from spg.providers.repository_code_verifier import RepositoryCodeVerifier


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


@pytest.fixture
def node_repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "node-verification"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Node Verification Test")
    _git(repository, "config", "user.email", "node-test@example.invalid")
    (repository / "src" / "spg" / "web").mkdir(parents=True)
    (repository / "tests" / "js").mkdir(parents=True)
    (repository / "src" / "spg" / "web" / "app.js").write_text(
        'const composerState = "expanded";\n', encoding="utf-8"
    )
    (repository / "tests" / "js" / "test_web_state.cjs").write_text(
        """const test = require("node:test");
const assert = require("node:assert/strict");
test("baseline", () => assert.equal(true, true));
""",
        encoding="utf-8",
    )
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "node baseline")
    return repository, _git(repository, "rev-parse", "HEAD")


def _contract(source_revision: str) -> CodeChangeContract:
    return CodeChangeContract(
        target_shape=ChangeTargetShape.EXACT_TARGET_SET,
        engineering_resource_id=uuid4(),
        repository_identity="test://node-verification",
        source_baseline_id=uuid4(),
        source_revision=source_revision,
        desired_outcome="Persist the Composer state",
        exact_targets=(
            CodeChangeTarget(
                path="src/spg/web/app.js", operation=ChangeOperation.UPDATE
            ),
            CodeChangeTarget(
                path="tests/js/test_web_state.cjs",
                operation=ChangeOperation.UPDATE,
            ),
        ),
        verification_obligations=(
            CodeVerificationObligation(kind=CodeVerificationKind.PATH_SCOPE),
            CodeVerificationObligation(kind=CodeVerificationKind.GIT_DIFF_CHECK),
            CodeVerificationObligation(
                kind=CodeVerificationKind.NODE_TEST_TARGET,
                target="tests/js/test_web_state.cjs",
            ),
        ),
    )


def _proposed_revision(repository: Path, *, passing: bool) -> str:
    (repository / "src" / "spg" / "web" / "app.js").write_text(
        'const composerState = globalThis.localStorage;\n', encoding="utf-8"
    )
    expected = "localStorage" if passing else "sessionStorage"
    (repository / "tests" / "js" / "test_web_state.cjs").write_text(
        f"""const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
test("composer state", () => {{
  const source = fs.readFileSync(path.join(__dirname, "../../src/spg/web/app.js"), "utf8");
  assert.match(source, /{expected}/);
}});
""",
        encoding="utf-8",
    )
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "proposed node change")
    return _git(repository, "rev-parse", "HEAD")


def test_node_01_02_03_typed_contract_contains_no_command() -> None:
    obligation = CodeVerificationObligation(
        kind=CodeVerificationKind.NODE_TEST_TARGET,
        target="tests/js/test_web_state.cjs",
    )

    assert obligation.identity == "NODE_TEST_TARGET:tests/js/test_web_state.cjs"
    assert "command" not in CodeVerificationObligation.model_fields
    assert "args" not in CodeVerificationObligation.model_fields
    with pytest.raises(ValidationError):
        CodeVerificationObligation.model_validate(
            {
                "kind": "NODE_TEST_TARGET",
                "target": "tests/js/test_web_state.cjs",
                "command": "anything",
            }
        )


@pytest.mark.parametrize(
    "target",
    (
        "../outside.cjs",
        "/outside.cjs",
        "C:/outside.cjs",
        ".git/hooks/test.cjs",
        "src/spg/web/app.js",
        "tests/js/not-node.py",
    ),
)
def test_node_03_04_unsafe_or_non_test_target_is_rejected(target: str) -> None:
    with pytest.raises(ValidationError):
        CodeVerificationObligation(
            kind=CodeVerificationKind.NODE_TEST_TARGET,
            target=target,
        )


def test_node_05_target_outside_change_contract_is_rejected() -> None:
    with pytest.raises(ValidationError, match="inside the admitted change boundary"):
        CodeChangeContract(
            target_shape=ChangeTargetShape.EXACT_TARGET_SET,
            engineering_resource_id=uuid4(),
            repository_identity="test://node-verification",
            source_baseline_id=uuid4(),
            source_revision="a" * 40,
            desired_outcome="Change one frontend file",
            exact_targets=(
                CodeChangeTarget(
                    path="src/spg/web/app.js", operation=ChangeOperation.UPDATE
                ),
            ),
            verification_obligations=(
                CodeVerificationObligation(kind=CodeVerificationKind.PATH_SCOPE),
                CodeVerificationObligation(kind=CodeVerificationKind.GIT_DIFF_CHECK),
                CodeVerificationObligation(
                    kind=CodeVerificationKind.NODE_TEST_TARGET,
                    target="tests/js/test_web_state.cjs",
                ),
            ),
        )


@pytest.mark.parametrize(
    ("passing", "expected"),
    (
        (True, VerificationResultValue.PASS),
        (False, VerificationResultValue.FAIL),
    ),
)
def test_node_06_07_10_fixed_node_runner_returns_bounded_evidence(
    node_repository: tuple[Path, str],
    passing: bool,
    expected: VerificationResultValue,
) -> None:
    repository, baseline = node_repository
    proposed = _proposed_revision(repository, passing=passing)
    obligation = _contract(baseline).verification_obligations[-1]

    result, metadata = RepositoryCodeVerifier(None)._evaluate(  # type: ignore[arg-type]
        repository=repository,
        source_revision=baseline,
        proposed_revision=proposed,
        contract=_contract(baseline),
        obligation=obligation,
    )

    assert result is expected
    assert metadata["kind"] == "NODE_TEST_TARGET"
    assert metadata["target"] == "tests/js/test_web_state.cjs"
    assert metadata["exit_code"] == (0 if passing else 1)
    assert isinstance(metadata["duration_ms"], int)
    assert len(str(metadata["output_fingerprint"])) == 64
    assert isinstance(metadata["stdout_bytes"], int)
    assert isinstance(metadata["stderr_bytes"], int)


def test_node_15_verifier_uses_fixed_arguments_without_shell_surface() -> None:
    source = Path("src/spg/providers/repository_code_verifier.py").read_text(
        encoding="utf-8"
    )

    assert '["node", "--test", obligation.target]' in source
    assert "shell=True" not in source
