"""N1 G4: every admitted ordered item is checked against an exact Candidate blob."""

from pathlib import Path
from datetime import UTC, datetime
from hashlib import sha256
import subprocess
from uuid import uuid4

import pytest

from spg.domain.change import (
    ChangeOperation, ChangeTargetShape, CodeChangeContract, CodeChangeTarget,
    CodeVerificationKind, CodeVerificationObligation,
)
from spg.domain.engineering_semantics import (
    EngineeringSemanticFactCandidate, SemanticEpistemicStatus,
    SemanticFactAuthority, SemanticFactReference, SemanticRelation,
    SemanticRoleOrigin,
)
from spg.providers.static_html_semantic_verifier import verify_static_html_semantic_facts
from spg.application.interaction import WorkInteractionService
from spg.domain.interaction import (
    InteractionActor, InteractionAssessmentCandidate, InteractionInvariantViolation,
    InteractionRecord,
)


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


def _alternate_facts() -> tuple[SemanticFactReference, ...]:
    """The second WIC shape observed in isolated G4 Work f00999f9."""
    common = dict(authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4())
    return (
        SemanticFactReference(fact_id=uuid4(), subject="page.h1.text",
                              relation=SemanticRelation.EQUALITY, value="N1 Budget",
                              scope="index.html", qualifiers={"exact":"true"}, **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.ordered_list.item_texts",
                              relation=SemanticRelation.ORDERED_COMPONENT, value=ITEMS,
                              scope=None, qualifiers={"ordered":"true"}, **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.ordered_list.item_occurrence",
                              relation=SemanticRelation.CARDINALITY, value=1,
                              scope="index.html", qualifiers={"exact":"true"}, **common),
        SemanticFactReference(fact_id=uuid4(), subject="repository.changed_files",
                              relation=SemanticRelation.SCOPE, value=("index.html",),
                              scope=None, qualifiers={"exclusive":"true"}, **common),
        SemanticFactReference(fact_id=uuid4(), subject="acceptance.ordered_list_texts",
                              relation=SemanticRelation.ACCEPTANCE_ASSERTION, value=True,
                              scope="index.html",
                              qualifiers={"count":14,"order":"fixed","occurrence":"once"},
                              **common),
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


def test_alternate_wic_fact_shape_consumes_all_five_obligations(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    checks = verify_static_html_semantic_facts(repository, candidate, contract,
                                               _alternate_facts())
    assert len(checks) == 5
    assert all(check["passed"] for check in checks)


@pytest.mark.parametrize("items", [ITEMS[:6] + ITEMS[7:],
                                      ITEMS[:6] + (ITEMS[7], ITEMS[6]) + ITEMS[8:]])
def test_alternate_wic_missing_or_swapped_item_fails_all_bound_assertions(
    tmp_path: Path, items: tuple[str, ...],
) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, items)
    checks = verify_static_html_semantic_facts(repository, candidate, contract,
                                               _alternate_facts())
    assert not checks[1]["passed"]
    assert not checks[2]["passed"]
    assert not checks[4]["passed"]


def test_alternate_wic_changed_file_scope_and_unknown_page_fact_fail(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    (repository / "other.txt").write_text("unexpected\n", encoding="utf-8")
    _git(repository, "add", "other.txt")
    _git(repository, "commit", "-m", "unexpected file")
    candidate = _git(repository, "rev-parse", "HEAD")
    facts = (*_alternate_facts(), SemanticFactReference(
        fact_id=uuid4(), subject="page.unsupported.required",
        relation=SemanticRelation.EQUALITY, value="must exist", scope="index.html",
        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
        source_work_revision_id=uuid4()))
    checks = verify_static_html_semantic_facts(repository, candidate, contract, facts)
    assert not checks[3]["passed"]
    assert not checks[5]["passed"]


def test_existing_g0_g3_heading_and_paragraph_shapes_are_mechanical(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    (repository / "index.html").write_text(
        "<!doctype html><h1>N1 Budget</h1><p>Existing Product bounded Work</p>",
        encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "simple candidate")
    candidate = _git(repository, "rev-parse", "HEAD")
    common = dict(scope="index.html", authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4())
    facts = (
        SemanticFactReference(fact_id=uuid4(), subject="index.html.h1.text",
                              relation=SemanticRelation.EQUALITY, value="N1 Budget", **common),
        SemanticFactReference(fact_id=uuid4(), subject="index.html.h1.count",
                              relation=SemanticRelation.CARDINALITY, value=1, **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.paragraph.text",
                              relation=SemanticRelation.EQUALITY,
                              value="Existing Product bounded Work", **common),
        SemanticFactReference(fact_id=uuid4(), subject="index.html.paragraph.count",
                              relation=SemanticRelation.CARDINALITY, value=1, **common),
    )
    assert all(item["passed"] for item in verify_static_html_semantic_facts(
        repository, candidate, contract, facts))
    (repository / "index.html").write_text(
        "<!doctype html><h1>N1 Budget</h1><p>Existing Product bounded Work</p>"
        "<p>Unexpected duplicate</p>", encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "duplicate paragraph")
    candidate = _git(repository, "rev-parse", "HEAD")
    checks = verify_static_html_semantic_facts(repository, candidate, contract, facts)
    assert not checks[2]["passed"] and not checks[3]["passed"]


def test_explicit_fourteen_items_survive_wic_count_only_candidate() -> None:
    source = (
        "Create index.html with one ordered list. The following fourteen list-item "
        "texts are separate mandatory acceptance constraints; every one must "
        "appear exactly once, in order: " + "; ".join(ITEMS) +
        ". Verify all fourteen exact texts."
    )
    record = InteractionRecord(
        id=uuid4(), interaction_id=uuid4(), sequence=1,
        actor=InteractionActor.HUMAN, source="human:test", content=source,
        content_fingerprint=sha256(source.encode()).hexdigest(),
        created_at=datetime.now(UTC))
    candidate = InteractionAssessmentCandidate(
        natural_response="I will produce the page.", provider_identity="test")
    preserved = WorkInteractionService._preserve_explicit_ordered_page_items(
        candidate, record)
    assert len(preserved.semantic_fact_candidates) == 1
    fact = preserved.semantic_fact_candidates[0]
    assert fact.value == ITEMS and fact.scope == "index.html"
    assert fact.source_record_ids == (record.id,) and fact.source_text == source
    assert fact.qualifiers["count"] == 14

    already_exact = candidate.model_copy(update={"semantic_fact_candidates": (
        EngineeringSemanticFactCandidate(
            candidate_id="wic-exact-list", subject="page.list.item_text",
            relation=SemanticRelation.ORDERED_COMPONENT, value=ITEMS,
            scope="index.html", authority=SemanticFactAuthority.HUMAN_EXPLICIT,
            epistemic_status=SemanticEpistemicStatus.CONFIRMED,
            source_record_ids=(record.id,), source_text=source,
            role_origin=SemanticRoleOrigin.EXPLICIT),)})
    preserved_exact = WorkInteractionService._preserve_explicit_ordered_page_items(
        already_exact, record)
    assert preserved_exact.semantic_fact_candidates == already_exact.semantic_fact_candidates

    malformed = record.model_copy(update={"content": source.replace("F07:", "F08:")})
    with pytest.raises(InteractionInvariantViolation):
        WorkInteractionService._preserve_explicit_ordered_page_items(candidate, malformed)


def test_count_only_g4_fact_cannot_pass_without_exact_ordered_values(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    common = dict(authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4())
    count = SemanticFactReference(
        fact_id=uuid4(), subject="index.ordered_list_items",
        relation=SemanticRelation.CARDINALITY, value=14,
        scope="index.html ordered list", **common)
    assert not verify_static_html_semantic_facts(
        repository, candidate, contract, (count,))[0]["passed"]
    exact = SemanticFactReference(
        fact_id=uuid4(), subject="page.ordered_list.items",
        relation=SemanticRelation.ORDERED_COMPONENT, value=ITEMS,
        scope="index.html", qualifiers={"count": 14}, **common)
    checks = verify_static_html_semantic_facts(
        repository, candidate, contract, (count, exact))
    assert len(checks) == 2 and all(check["passed"] for check in checks)


def test_third_observed_g4_wic_profile_checks_every_exact_item(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    common = dict(scope="index.html", authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4())
    facts = (
        SemanticFactReference(fact_id=uuid4(), subject="page.heading.text",
                              relation=SemanticRelation.EQUALITY, value="N1 Budget",
                              qualifiers={"exact": True}, **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.list.item_text",
                              relation=SemanticRelation.ORDERED_COMPONENT, value=ITEMS,
                              qualifiers={"ordered": True, "exactly_once_each": True}, **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.list.item_count",
                              relation=SemanticRelation.CARDINALITY, value=14, **common),
        SemanticFactReference(fact_id=uuid4(), subject="change.file_scope",
                              relation=SemanticRelation.SCOPE, value=("index.html",),
                              scope="managed product source", qualifiers={"only": True},
                              authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                              epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                              source_work_revision_id=uuid4()),
    )
    checks = verify_static_html_semantic_facts(repository, candidate, contract, facts)
    assert len(checks) == 4 and all(check["passed"] for check in checks)
    swapped = ITEMS[:6] + (ITEMS[7], ITEMS[6]) + ITEMS[8:]
    candidate = _candidate(repository, swapped)
    checks = verify_static_html_semantic_facts(repository, candidate, contract, facts)
    assert not checks[1]["passed"] and not checks[2]["passed"]


def test_g0_page_count_and_g3_wic_text_aliases(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    (repository / "index.html").write_text(
        "<!doctype html><h1>N1 Software Control</h1>"
        "<p>Isolated qualification only</p>", encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "page")
    candidate = _git(repository, "rev-parse", "HEAD")
    common = dict(scope="index.html", authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4())
    facts = (
        SemanticFactReference(fact_id=uuid4(), subject="page.count",
                              relation=SemanticRelation.CARDINALITY, value=1, **common),
        SemanticFactReference(fact_id=uuid4(), subject="index.html.h1_text",
                              relation=SemanticRelation.EQUALITY,
                              value="N1 Software Control", **common),
        SemanticFactReference(fact_id=uuid4(), subject="index.html.paragraph_text",
                              relation=SemanticRelation.EQUALITY,
                              value="Isolated qualification only", **common),
    )
    assert all(check["passed"] for check in verify_static_html_semantic_facts(
        repository, candidate, contract, facts))
    (repository / "other.html").write_text("<!doctype html><p>Extra</p>", encoding="utf-8")
    _git(repository, "add", "other.html")
    _git(repository, "commit", "-m", "extra page")
    candidate = _git(repository, "rev-parse", "HEAD")
    assert not verify_static_html_semantic_facts(
        repository, candidate, contract, facts)[0]["passed"]


def test_g3_observed_aliases_bind_exact_new_file_and_text(tmp_path: Path) -> None:
    repository, original = _fixture(tmp_path)
    contract = original.model_copy(update={"exact_targets": (
        CodeChangeTarget(path="status-v0.html", operation=ChangeOperation.CREATE),)})
    (repository / "status-v0.html").write_text(
        "<!doctype html><h1>N1 Status</h1>"
        "<p>Existing Product bounded Work</p>", encoding="utf-8")
    _git(repository, "add", "status-v0.html")
    _git(repository, "commit", "-m", "status page")
    candidate = _git(repository, "rev-parse", "HEAD")
    common = dict(authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4())
    facts = (
        SemanticFactReference(fact_id=uuid4(), subject="status_v0_page.h1_text",
                              relation=SemanticRelation.EQUALITY, value="N1 Status",
                              scope="status-v0.html", **common),
        SemanticFactReference(fact_id=uuid4(), subject="status_v0_page.paragraph_text",
                              relation=SemanticRelation.EQUALITY,
                              value="Existing Product bounded Work",
                              scope="status-v0.html", **common),
        SemanticFactReference(fact_id=uuid4(), subject="work.modifiable_files",
                              relation=SemanticRelation.SCOPE,
                              value=("status-v0.html",), scope=None, **common),
        SemanticFactReference(fact_id=uuid4(), subject="work.new_file_count",
                              relation=SemanticRelation.CARDINALITY,
                              value=1, scope=None, **common),
    )
    checks = verify_static_html_semantic_facts(repository, candidate, contract, facts)
    assert len(checks) == 4 and all(check["passed"] for check in checks)
    (repository / "status-v0.html").write_text(
        "<!doctype html><h1>N1 Status</h1><p>Wrong</p>", encoding="utf-8")
    _git(repository, "add", "status-v0.html")
    _git(repository, "commit", "-m", "wrong paragraph")
    candidate = _git(repository, "rev-parse", "HEAD")
    checks = verify_static_html_semantic_facts(repository, candidate, contract, facts)
    assert not checks[1]["passed"]
