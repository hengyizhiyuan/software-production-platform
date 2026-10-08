"""N1 G4: every admitted ordered item is checked against an exact Candidate blob."""

from pathlib import Path
import subprocess
from uuid import uuid4

import pytest

from spg.domain.change import (
    ChangeOperation, ChangeTargetShape, CodeChangeContract, CodeChangeTarget,
    CodeVerificationKind, CodeVerificationObligation,
)
from spg.domain.engineering_semantics import (
    SemanticEpistemicStatus, SemanticFactAuthority, SemanticFactReference,
    SemanticRelation,
)
from spg.providers.static_html_semantic_verifier import verify_static_html_semantic_facts


ITEMS = tuple(f"F{index:02d}: N1 protected fact {index:02d}" for index in range(1, 15))


def _git(repository: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repository), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def _fixture(tmp_path: Path) -> tuple[Path, CodeChangeContract]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "N1 Test")
    _git(repository, "config", "user.email", "n1@example.invalid")
    (repository / "README.md").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "baseline")
    contract = CodeChangeContract(
        target_shape=ChangeTargetShape.EXACT_TARGET_SET,
        engineering_resource_id=uuid4(), repository_identity="watt://n1-test",
        source_baseline_id=uuid4(), source_revision=_git(repository, "rev-parse", "HEAD"),
        desired_outcome="Create the exact fourteen-item page",
        exact_targets=(CodeChangeTarget(path="index.html", operation=ChangeOperation.CREATE),),
        verification_obligations=(
            CodeVerificationObligation(kind=CodeVerificationKind.PATH_SCOPE),
            CodeVerificationObligation(kind=CodeVerificationKind.GIT_DIFF_CHECK),
        ),
    )
    return repository, contract


def _facts() -> tuple[SemanticFactReference, ...]:
    common = dict(scope="index.html", authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4())
    return (
        SemanticFactReference(fact_id=uuid4(), subject="page.heading.text",
                              relation=SemanticRelation.EQUALITY, value="N1 Budget",
                              qualifiers={"heading_level": 1}, **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.ordered_list.items",
                              relation=SemanticRelation.ORDERED_COMPONENT, value=ITEMS,
                              qualifiers={"count": 14}, **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.ordered_list.items",
                              relation=SemanticRelation.ACCEPTANCE_ASSERTION,
                              value="each text appears exactly once, in order", **common),
    )


def _candidate(repository: Path, items: tuple[str, ...], *, extra: str = "") -> str:
    content = "<!doctype html><html><body><h1>N1 Budget</h1><ol>" + "".join(
        f"<li>{item}</li>" for item in items
    ) + "</ol>" + extra + "</body></html>"
    (repository / "index.html").write_text(content, encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "candidate")
    return _git(repository, "rev-parse", "HEAD")


def test_exact_fourteen_items_receive_three_mechanical_checks(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    checks = verify_static_html_semantic_facts(repository, candidate, contract, _facts())
    assert len(checks) == 3
    assert all(check["passed"] for check in checks)


@pytest.mark.parametrize("items,extra", [
    (ITEMS[:6] + ITEMS[7:], ""),
    (ITEMS[:6] + (ITEMS[7], ITEMS[6]) + ITEMS[8:], ""),
    (ITEMS, f"<p>{ITEMS[0]}</p>"),
    (ITEMS + (ITEMS[0],), ""),
])
def test_missing_swapped_or_duplicated_protected_item_fails(
    tmp_path: Path, items: tuple[str, ...], extra: str,
) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, items, extra=extra)
    checks = verify_static_html_semantic_facts(repository, candidate, contract, _facts())
    assert not all(check["passed"] for check in checks)
    assert not checks[1]["passed"]
    assert not checks[2]["passed"]


def test_assertion_without_ordered_source_fact_cannot_pass(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    heading, _, assertion = _facts()
    checks = verify_static_html_semantic_facts(
        repository, candidate, contract, (heading, assertion))
    assert not checks[-1]["passed"]
    assert checks[-1]["reason"] == "ORDERED_FACT_MISSING"
