"""N1 G4: every admitted ordered item is checked against an exact Candidate blob."""

from pathlib import Path
from types import SimpleNamespace
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
    EngineeringSemanticFact, EngineeringSemanticFactCandidate,
    SemanticFactProvenance, SemanticEpistemicStatus,
    SemanticFactAuthority, SemanticFactReference, SemanticRelation,
    SemanticRoleOrigin,
)
from spg.domain.model_runtime import (
    ModelProvider, ModelTiming, ModelUsage, StructuredModelResult,
)
from spg.providers.static_html_semantic_verifier import (
    StaticHTMLPlanRepair, verify_static_html_semantic_facts,
)
from spg.application.interaction import WorkInteractionService
from spg.domain.interaction import (
    InteractionActor, InteractionAssessmentCandidate, InteractionInvariantViolation,
    InteractionRecord,
)


ITEMS = tuple(f"F{index:02d}: N1 protected fact {index:02d}" for index in range(1, 15))


def test_observed_g0_page_profile_checks_exact_heading_and_path(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    (repository / "index.html").write_text(
        "<html><body><h1>N1 Software Control</h1>"
        "<p>Isolated qualification only</p></body></html>", encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "candidate")
    revision = _git(repository, "rev-parse", "HEAD")
    common = dict(scope=None, authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4(), qualifiers={})
    facts = tuple(SemanticFactReference(fact_id=uuid4(), subject=subject,
                                        relation=relation, value=value, **common)
                  for subject, relation, value in (
                      ("page.path", SemanticRelation.EQUALITY, "index.html"),
                      ("page.heading.count", SemanticRelation.CARDINALITY, 1),
                      ("page.heading.text", SemanticRelation.EQUALITY,
                       "N1 Software Control"),
                      ("page.paragraph.text", SemanticRelation.EQUALITY,
                       "Isolated qualification only")))
    checks = verify_static_html_semantic_facts(repository, revision, contract, facts)
    assert len(checks) == 4 and all(check["passed"] for check in checks)
    (repository / "index.html").write_text(
        "<html><body><h1>N1 Software Control</h1><h2>Extra</h2>"
        "<p>Isolated qualification only</p></body></html>", encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "extra heading")
    checks = verify_static_html_semantic_facts(
        repository, _git(repository, "rev-parse", "HEAD"), contract, facts)
    assert {check["subject"] for check in checks if not check["passed"]} == {
        "page.heading.count", "page.heading.text"}


def test_observed_g3_artifact_file_profile_requires_exact_blob(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    (repository / "index.html").write_text(
        "<html><body><h1>N1 Status</h1>"
        "<p>Existing Product bounded Work</p></body></html>", encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "candidate")
    common = dict(scope="work", authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4(), qualifiers={})
    facts = tuple(SemanticFactReference(fact_id=uuid4(), subject=subject,
                                        relation=relation, value=value, **common)
                  for subject, relation, value in (
                      ("artifact.file.change_scope", SemanticRelation.SCOPE,
                       "index.html"),
                      ("artifact.file.count", SemanticRelation.CARDINALITY, 1),
                      ("artifact.file.h1_text", SemanticRelation.EQUALITY,
                       "N1 Status"),
                      ("artifact.file.paragraph_text", SemanticRelation.EQUALITY,
                       "Existing Product bounded Work")))
    checks = verify_static_html_semantic_facts(
        repository, _git(repository, "rev-parse", "HEAD"), contract, facts)
    assert len(checks) == 4 and all(check["passed"] for check in checks)
    (repository / "index.html").write_text(
        "<html><body><h1>N1 Status</h1><p>Wrong</p></body></html>",
        encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "wrong paragraph")
    checks = verify_static_html_semantic_facts(
        repository, _git(repository, "rev-parse", "HEAD"), contract, facts)
    assert next(check for check in checks if check["subject"] ==
                "artifact.file.paragraph_text")["passed"] is False


def test_observed_g4_index_html_profile_binds_each_item(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    common = dict(scope="index.html",
                  authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4())
    facts = tuple(SemanticFactReference(
        fact_id=uuid4(), subject=subject, relation=relation, value=value,
        qualifiers=qualifiers, **common)
        for subject, relation, value, qualifiers in (
            ("index_html.h1_text", SemanticRelation.EQUALITY, "N1 Budget",
             {"element": "h1", "exactness": "exact"}),
            ("index_html.ordered_list_count", SemanticRelation.CARDINALITY,
             1, {}),
            ("page.ordered_list.items", SemanticRelation.ORDERED_COMPONENT,
             ITEMS, {"count": 14}),
            ("index_html.list_item_acceptance_count",
             SemanticRelation.CARDINALITY, 14,
             {"role": "mandatory acceptance constraints"}),
            ("index_html.list_item_occurrence",
             SemanticRelation.ACCEPTANCE_ASSERTION,
             "each of the fourteen texts appears exactly once, in order",
             {"verification": "all fourteen exact texts verified"}),
            ("repository.change_scope_file_count", SemanticRelation.SCOPE,
             "only index.html is created or changed",
             {"verification": "no other file changes"}),
            ("index_html.file_scope", SemanticRelation.SCOPE,
             "index.html only", {"no_other_file_changes": True})))
    facts += (
        SemanticFactReference(fact_id=uuid4(),
                              subject="acceptance.index_html.list_constraints",
                              relation=SemanticRelation.ACCEPTANCE_ASSERTION,
                              value="each_text_appears_exactly_once_in_order",
                              scope="index.html", qualifiers={},
                              **{k: v for k, v in common.items() if k != "scope"}),
        SemanticFactReference(fact_id=uuid4(), subject="workspace.changed_files",
                              relation=SemanticRelation.SCOPE,
                              value=("index.html",), scope="managed product source",
                              qualifiers={},
                              **{k: v for k, v in common.items() if k != "scope"}),
    )
    good = _candidate(repository, ITEMS)
    checks = verify_static_html_semantic_facts(repository, good, contract, facts)
    assert len(checks) == 9 and all(check["passed"] for check in checks)
    bad = _candidate(repository, tuple(item for item in ITEMS if not
                                       item.startswith("F07:")))
    checks = verify_static_html_semantic_facts(repository, bad, contract, facts)
    assert {check["subject"] for check in checks if not check["passed"]} >= {
        "page.ordered_list.items", "index_html.list_item_acceptance_count",
        "index_html.list_item_occurrence",
        "acceptance.index_html.list_constraints"}


def test_observed_g0_index_html_assertions_are_exact(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    (repository / "index.html").write_text(
        "<html><body><h1>N1 Software Control</h1>"
        "<p>Isolated qualification only</p></body></html>", encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "candidate")
    common = dict(authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4(), qualifiers={})
    facts = tuple(SemanticFactReference(
        fact_id=uuid4(), subject=subject, relation=relation, value=value,
        scope=scope, **common)
        for subject, relation, value, scope in (
            ("index_html.page_count", SemanticRelation.CARDINALITY,
             1, "index.html"),
            ("index_html.h1.text", SemanticRelation.ACCEPTANCE_ASSERTION,
             "N1 Software Control", "index.html"),
            ("index_html.paragraph.text", SemanticRelation.ACCEPTANCE_ASSERTION,
             "Isolated qualification only", "index.html"),
            ("work.change_scope", SemanticRelation.SCOPE,
             "index.html", "current Work revision"),
            ("index_html.markup.semantics", SemanticRelation.BEHAVIOR,
             "semantic HTML", "index.html")))
    good = _git(repository, "rev-parse", "HEAD")
    checks = verify_static_html_semantic_facts(repository, good, contract, facts)
    assert len(checks) == 5 and all(check["passed"] for check in checks)
    (repository / "index.html").write_text(
        "<html><body><h1>N1 Software Control</h1><p>Wrong</p></body></html>",
        encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "wrong paragraph")
    bad = _git(repository, "rev-parse", "HEAD")
    checks = verify_static_html_semantic_facts(repository, bad, contract, facts)
    assert next(check for check in checks if check["subject"] ==
                "index_html.paragraph.text")["passed"] is False


def test_observed_g0_path_heading_requires_exact_h1_qualifiers(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    (repository / "index.html").write_text(
        "<html><body><h1>N1 Software Control</h1></body></html>",
        encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "candidate")
    candidate = _git(repository, "rev-parse", "HEAD")
    common = dict(authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4(), scope="index.html")
    fact = SemanticFactReference(
        fact_id=uuid4(), subject="index.html.heading.text",
        relation=SemanticRelation.EQUALITY, value="N1 Software Control",
        qualifiers={"element": "h1", "count": 1}, **common)
    checks = verify_static_html_semantic_facts(repository, candidate, contract,
                                                (fact,))
    assert len(checks) == 1 and checks[0]["passed"]
    unsafe = fact.model_copy(update={"qualifiers": {"element": "h2", "count": 1}})
    checks = verify_static_html_semantic_facts(repository, candidate, contract,
                                                (unsafe,))
    assert not checks[0]["passed"]


def test_observed_g0_page_index_profile_binds_full_assertion(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    (repository / "index.html").write_text(
        "<html><body><h1>N1 Software Control</h1>"
        "<p>Isolated qualification only</p></body></html>", encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "candidate")
    common = dict(authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4(), qualifiers={})
    facts = tuple(SemanticFactReference(
        fact_id=uuid4(), subject=subject, relation=relation, value=value,
        scope=scope, **common)
        for subject, relation, value, scope in (
            ("page.index_html.h1.text", SemanticRelation.EQUALITY,
             "N1 Software Control", "index.html"),
            ("page.index_html.paragraph.text", SemanticRelation.EQUALITY,
             "Isolated qualification only", "index.html"),
            ("page.count", SemanticRelation.CARDINALITY,
             1, "managed Product repository"),
            ("artifact.change_scope", SemanticRelation.SCOPE,
             "index.html", "N1 qualification work"),
            ("acceptance.artifact_content", SemanticRelation.ACCEPTANCE_ASSERTION,
             "exact heading and paragraph verified and reviewable Candidate left",
             "N1 qualification work")))
    candidate = _git(repository, "rev-parse", "HEAD")
    checks = verify_static_html_semantic_facts(repository, candidate, contract, facts)
    assert len(checks) == 5 and all(check["passed"] for check in checks[:4])
    assert checks[4]["disposition"] == "UNVERIFIABLE_CURRENT"
    # A future reviewable Candidate cannot be proved by an HTML blob before
    # the Candidate Owner seals one after current Verification.
    (repository / "index.html").write_text(
        "<html><body><h1>N1 Software Control</h1><p>Wrong</p></body></html>",
        encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "wrong paragraph")
    checks = verify_static_html_semantic_facts(
        repository, _git(repository, "rev-parse", "HEAD"), contract, facts)
    assert not next(check for check in checks if check["subject"] ==
                    "acceptance.artifact_content")["passed"]


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
    assert len(preserved_exact.semantic_fact_candidates) == 1
    assert preserved_exact.semantic_fact_candidates[0].subject == "page.ordered_list.items"
    assert preserved_exact.semantic_fact_candidates[0].value == ITEMS

    document_shape = already_exact.semantic_fact_candidates[0].model_copy(update={
        "subject": "document.ordered_list.items.text"})
    preserved_document = WorkInteractionService._preserve_explicit_ordered_page_items(
        candidate.model_copy(update={"semantic_fact_candidates": (document_shape,)}),
        record)
    assert len(preserved_document.semantic_fact_candidates) == 1
    assert preserved_document.semantic_fact_candidates[0].subject == "page.ordered_list.items"

    scoped_wic = already_exact.semantic_fact_candidates[0].model_copy(update={
        "subject": "index_html.list_item_texts",
        "scope": "index.html ordered list",
        "qualifiers": {"ordering": "in order", "uniqueness": "exactly once",
                       "cardinality": 14},
    })
    preserved_scoped = WorkInteractionService._preserve_explicit_ordered_page_items(
        candidate.model_copy(update={"semantic_fact_candidates": (scoped_wic,)}),
        record)
    assert len(preserved_scoped.semantic_fact_candidates) == 1
    assert preserved_scoped.semantic_fact_candidates[0].subject == "page.ordered_list.items"
    assert preserved_scoped.semantic_fact_candidates[0].value == ITEMS

    stripped = already_exact.semantic_fact_candidates[0].model_copy(update={
        "subject": "index.html.ordered_list.item_texts",
        "value": tuple(item.split(": ", 1)[1] for item in ITEMS),
    })
    stripped_candidate = candidate.model_copy(update={
        "semantic_fact_candidates": (stripped,)})
    corrected = WorkInteractionService._preserve_explicit_ordered_page_items(
        stripped_candidate, record)
    assert len(corrected.semantic_fact_candidates) == 1
    assert corrected.semantic_fact_candidates[0].value == ITEMS
    assert corrected.semantic_fact_candidates[0].subject == "page.ordered_list.items"

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
    alternate = (
        SemanticFactReference(fact_id=uuid4(), subject="artifact.target_file",
                              relation=SemanticRelation.EQUALITY,
                              value="status-v0.html", scope="interaction", **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.heading_text",
                              relation=SemanticRelation.EQUALITY, value="N1 Status",
                              scope="status-v0.html", **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.paragraph_text",
                              relation=SemanticRelation.EQUALITY,
                              value="Existing Product bounded Work",
                              scope="status-v0.html", **common),
        SemanticFactReference(fact_id=uuid4(), subject="work.change_scope",
                              relation=SemanticRelation.SCOPE,
                              value="status-v0.html only", scope="interaction", **common),
    )
    assert all(check["passed"] for check in verify_static_html_semantic_facts(
        repository, candidate, contract, alternate))
    (repository / "status-v0.html").write_text(
        "<!doctype html><h1>N1 Status</h1><p>Wrong</p>", encoding="utf-8")
    _git(repository, "add", "status-v0.html")
    _git(repository, "commit", "-m", "wrong paragraph")
    candidate = _git(repository, "rev-parse", "HEAD")
    checks = verify_static_html_semantic_facts(repository, candidate, contract, facts)
    assert not checks[1]["passed"]


def test_g0_semantic_markup_and_exact_deliverable_are_checked(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    (repository / "index.html").write_text(
        "<!doctype html><html><body><h1>N1 Software Control</h1>"
        "<p>Isolated qualification only</p></body></html>", encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "semantic page")
    candidate = _git(repository, "rev-parse", "HEAD")
    common = dict(authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4())
    facts = (
        SemanticFactReference(fact_id=uuid4(), subject="deliverable.page",
                              relation=SemanticRelation.CARDINALITY, value=1,
                              qualifiers={"path": "index.html"}, **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.markup",
                              relation=SemanticRelation.BEHAVIOR,
                              value="semantic HTML", **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.h1.count",
                              relation=SemanticRelation.CARDINALITY, value=1,
                              scope="index.html", **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.paragraph.count",
                              relation=SemanticRelation.CARDINALITY, value=1,
                              scope="index.html", **common),
    )
    assert all(check["passed"] for check in verify_static_html_semantic_facts(
        repository, candidate, contract, facts))
    (repository / "index.html").write_text(
        "<h1>N1 Software Control</h1><p>Isolated qualification only</p>",
        encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "remove semantic structure")
    candidate = _git(repository, "rev-parse", "HEAD")
    assert not verify_static_html_semantic_facts(
        repository, candidate, contract, facts)[1]["passed"]


def test_g0_observed_underscore_profile_and_bound_assertion(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    (repository / "index.html").write_text(
        "<!doctype html><html><body><h1>N1 Software Control</h1>"
        "<p>Isolated qualification only</p></body></html>", encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "page")
    candidate = _git(repository, "rev-parse", "HEAD")
    common = dict(scope="index.html", authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4())
    facts = (
        SemanticFactReference(fact_id=uuid4(), subject="page.entry_file",
                              relation=SemanticRelation.EQUALITY,
                              value="index.html", **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.h1_count",
                              relation=SemanticRelation.CARDINALITY, value=1, **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.h1_text",
                              relation=SemanticRelation.EQUALITY,
                              value="N1 Software Control", **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.paragraph_count",
                              relation=SemanticRelation.CARDINALITY, value=1, **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.paragraph_text",
                              relation=SemanticRelation.EQUALITY,
                              value="Isolated qualification only", **common),
        SemanticFactReference(fact_id=uuid4(), subject="change.allowed_paths",
                              relation=SemanticRelation.SCOPE,
                              value="index.html", **common),
        SemanticFactReference(fact_id=uuid4(), subject="acceptance.verification",
                              relation=SemanticRelation.ACCEPTANCE_ASSERTION,
                              value="exact heading and paragraph verified", **common),
    )
    checks = verify_static_html_semantic_facts(repository, candidate, contract, facts)
    assert len(checks) == 7 and all(check["passed"] for check in checks)
    (repository / "index.html").write_text(
        "<!doctype html><html><body><h1>Wrong</h1>"
        "<p>Isolated qualification only</p></body></html>", encoding="utf-8")
    _git(repository, "add", "index.html")
    _git(repository, "commit", "-m", "wrong heading")
    candidate = _git(repository, "rev-parse", "HEAD")
    checks = verify_static_html_semantic_facts(repository, candidate, contract, facts)
    assert not checks[2]["passed"] and not checks[6]["passed"]


def test_fourth_observed_g4_profile_binds_count_to_exact_values(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    common = dict(authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4())
    facts = (
        SemanticFactReference(fact_id=uuid4(), subject="index_html.heading_text",
                              relation=SemanticRelation.EQUALITY, value="N1 Budget",
                              scope="index.html semantic HTML page", **common),
        SemanticFactReference(fact_id=uuid4(), subject="index_html.ordered_list.item_count",
                              relation=SemanticRelation.CARDINALITY, value=14,
                              scope="the single ordered list in index.html", **common),
        SemanticFactReference(fact_id=uuid4(), subject="change.file_scope",
                              relation=SemanticRelation.SCOPE, value="index.html",
                              scope="files changed by this production", **common),
        SemanticFactReference(fact_id=uuid4(), subject="page.ordered_list.items",
                              relation=SemanticRelation.ORDERED_COMPONENT,
                              value=ITEMS, scope="index.html",
                              qualifiers={"count": 14}, **common),
    )
    checks = verify_static_html_semantic_facts(repository, candidate, contract, facts)
    assert len(checks) == 4 and all(check["passed"] for check in checks)
    candidate = _candidate(repository, ITEMS[:6] + ITEMS[7:])
    checks = verify_static_html_semantic_facts(repository, candidate, contract, facts)
    assert not checks[1]["passed"] and not checks[3]["passed"]


def test_unlisted_file_expressions_materialize_without_subject_aliases(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    revision = uuid4()
    facts = tuple(SemanticFactReference(
        fact_id=uuid4(), subject=subject, relation=SemanticRelation.EQUALITY,
        value="index.html", scope=scope, qualifiers={},
        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
        source_work_revision_id=revision,
    ) for subject, scope in (
        ("landing.asset.location", "index.html"),
        ("product.output.entry", "the index.html page"),
        ("site.root.document", "page index.html"),
    ))
    original = tuple(fact.model_dump(mode="json") for fact in facts)
    checks = verify_static_html_semantic_facts(repository, candidate, contract, facts)
    assert len(checks) == 3 and all(check["passed"] for check in checks)
    assert all(check["materialization"]["method"] == "EXACT_TARGET_FILE"
               and check["materialization"]["repair_attempts"] == 0
               and check["materialization"]["work_reality_revision_id"] == str(revision)
               for check in checks)
    assert tuple(fact.model_dump(mode="json") for fact in facts) == original
    wrong_file = facts[0].model_copy(update={"scope": "other.html"})
    assert verify_static_html_semantic_facts(
        repository, candidate, contract, (wrong_file,))[0]["reason"] == "UNVERIFIABLE_FACT_PLAN"


def test_unlisted_paragraph_qualifier_checks_exact_blob(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS, extra="<p>Existing Product bounded Work</p>")
    fact = SemanticFactReference(
        fact_id=uuid4(), subject="copy.body.line",
        relation=SemanticRelation.EQUALITY,
        value="Existing Product bounded Work", scope="index.html",
        qualifiers={"element": "paragraph"},
        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
        source_work_revision_id=uuid4())
    check = verify_static_html_semantic_facts(
        repository, candidate, contract, (fact,))[0]
    assert check["passed"] is True
    assert check["materialization"]["method"] == "EXACT_PARAGRAPH"
    wrong = fact.model_copy(update={"value": "different copy"})
    assert verify_static_html_semantic_facts(
        repository, candidate, contract, (wrong,))[0]["passed"] is False


def test_unlisted_ordered_assertion_binds_exact_fact_and_rejects_drift(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    common = dict(authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                  epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                  source_work_revision_id=uuid4())
    ordered = SemanticFactReference(
        fact_id=uuid4(), subject="product.mandatory.sequence",
        relation=SemanticRelation.ORDERED_COMPONENT, value=ITEMS,
        scope="index.html", qualifiers={"element": "ol", "count": 14}, **common)
    assertion = SemanticFactReference(
        fact_id=uuid4(), subject="quality.sequence.conformance",
        relation=SemanticRelation.ACCEPTANCE_ASSERTION, value=True,
        scope="the ordered list in index.html",
        qualifiers={"cardinality": 14, "occurrences_each": 1,
                    "order": "as listed F01..F14"}, **common)
    checks = verify_static_html_semantic_facts(repository, candidate, contract,
                                               (ordered, assertion))
    assert all(check["passed"] for check in checks)
    assert checks[1]["materialization"]["linked_fact_id"] == str(ordered.fact_id)
    candidate = _candidate(repository, ITEMS[:6] + (ITEMS[7], ITEMS[6]) + ITEMS[8:])
    checks = verify_static_html_semantic_facts(repository, candidate, contract,
                                               (ordered, assertion))
    assert not checks[0]["passed"] and not checks[1]["passed"]
    candidate = _candidate(repository, ITEMS[:6] + ("F07: wrong value",) + ITEMS[7:])
    checks = verify_static_html_semantic_facts(repository, candidate, contract,
                                               (ordered, assertion))
    assert not checks[0]["passed"] and not checks[1]["passed"]
    wrong_scope = assertion.model_copy(update={"scope": "other.html ordered list"})
    checks = verify_static_html_semantic_facts(repository, _git(repository, "rev-parse", "HEAD"),
                                               contract, (ordered, wrong_scope))
    assert checks[1]["reason"] == "UNVERIFIABLE_FACT_PLAN"
    wrong_order = assertion.model_copy(update={"qualifiers": {
        **assertion.qualifiers, "order": "as listed F14..F01"}})
    checks = verify_static_html_semantic_facts(repository, candidate, contract,
                                               (ordered, wrong_order))
    assert checks[1]["reason"] == "UNVERIFIABLE_FACT_PLAN"


def test_unmaterialized_fact_is_visible_and_never_silently_passes(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    unknown = SemanticFactReference(
        fact_id=uuid4(), subject="product.unrelated.future_effect",
        relation=SemanticRelation.BEHAVIOR, value="must be observed",
        scope="external service", qualifiers={},
        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
        source_work_revision_id=uuid4())
    checks = verify_static_html_semantic_facts(repository, candidate, contract, (unknown,))
    assert len(checks) == 1
    assert checks[0]["passed"] is False
    assert checks[0]["reason"] == "UNVERIFIABLE_FACT_PLAN"


def test_exact_new_file_count_and_lifecycle_owner_are_distinct(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    revision = uuid4()
    count_id, guard_id = uuid4(), uuid4()
    count = EngineeringSemanticFact(
        id=count_id, subject="new.static.asset", relation=SemanticRelation.CARDINALITY,
        value=1, scope=None, qualifiers={},
        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
        provenance=SemanticFactProvenance(source_record_ids=(uuid4(),),
            source_text="Create exactly one new static file index.html",
            role_origin=SemanticRoleOrigin.EXPLICIT),
        admitted_work_revision_id=revision)
    guard = EngineeringSemanticFact(
        id=guard_id, subject="release.boundary", relation=SemanticRelation.EQUALITY,
        value=False, scope="index.html", qualifiers={},
        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
        provenance=SemanticFactProvenance(source_record_ids=(uuid4(),),
            source_text="Do not deploy or publish.",
            role_origin=SemanticRoleOrigin.EXPLICIT),
        admitted_work_revision_id=revision)
    from spg.domain.engineering_semantics import semantic_fact_reference
    refs = tuple(semantic_fact_reference(item, work_revision_id=revision)
                 for item in (count, guard))
    checks = verify_static_html_semantic_facts(
        repository, candidate, contract, refs,
        admitted_facts={str(item.id): item for item in (count, guard)})
    # A filename and value=1 do not identify the counted object. The former
    # shortcut would also accept an element count without inspecting the blob.
    assert checks[0]["passed"] is False
    assert checks[0]["reason"] == "UNVERIFIABLE_FACT_PLAN"
    runtime, calls = _count_plan_runtime("EXACT_NEW_FILE_COUNT", count.provenance.source_text)
    checks = verify_static_html_semantic_facts(
        repository, candidate, contract, refs,
        admitted_facts={str(item.id): item for item in (count, guard)},
        plan_repair=StaticHTMLPlanRepair(lambda: runtime))
    assert checks[0]["passed"] is True
    assert checks[0]["reason"] == "EXACT_NEW_FILE_COUNT"
    assert len(calls) == 2
    assert checks[1]["passed"] is False
    assert checks[1]["disposition"] == "UNVERIFIABLE_CURRENT"
    assert checks[1]["materialization"]["fact_id"] == str(guard_id)
    unknown = guard.model_copy(update={"value": "make the page blue"})
    unknown_ref = semantic_fact_reference(unknown, work_revision_id=revision)
    check = verify_static_html_semantic_facts(
        repository, candidate, contract, (unknown_ref,),
        admitted_facts={str(guard_id): unknown})[0]
    assert check["passed"] is False
    assert check["disposition"] == "UNVERIFIABLE_CURRENT"

    # Relation/value alone cannot prove which owner or lifecycle gate owns a
    # negative statement. A content absence must never inherit delivery proof.
    unrelated = guard.model_copy(update={"subject": "page.has_footer",
                                        "provenance": guard.provenance.model_copy(
                                            update={"source_text": "The page must have no footer."})})
    unrelated_ref = semantic_fact_reference(unrelated, work_revision_id=revision)
    check = verify_static_html_semantic_facts(
        repository, candidate, contract, (unrelated_ref,),
        admitted_facts={str(guard_id): unrelated})[0]
    assert check["passed"] is False
    assert check["disposition"] == "UNVERIFIABLE_CURRENT"


def test_page_assertion_rejects_value_count_and_scope_drift(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    fact = SemanticFactReference(
        fact_id=uuid4(), subject="product.page.acceptance",
        relation=SemanticRelation.ACCEPTANCE_ASSERTION,
        value="h1 contains exactly 'N1 Budget'; one ordered list with 14 items",
        scope="index.html", qualifiers={"page_count": 1,
            "heading_text": "N1 Budget", "ordered_list_count": 1,
            "ordered_list_item_count": 14},
        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
        source_work_revision_id=uuid4())
    assert verify_static_html_semantic_facts(
        repository, candidate, contract, (fact,))[0]["passed"] is True
    variants = (
        fact.model_copy(update={"value": "h1 contains exactly 'Wrong'; one ordered list with 14 items"}),
        fact.model_copy(update={"value": "h1 contains exactly 'N1 Budget'; one ordered list with 13 items"}),
        fact.model_copy(update={"scope": "other.html"}),
        fact.model_copy(update={"qualifiers": {**fact.qualifiers, "ordered_list_item_count": 13}}),
    )
    for variant in variants:
        check = verify_static_html_semantic_facts(
            repository, candidate, contract, (variant,))[0]
        assert check["passed"] is False
        assert check["reason"] == "UNVERIFIABLE_FACT_PLAN"


def test_model_repairs_only_derived_method_against_exact_human_source(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    revision, fact_id, record_id = uuid4(), uuid4(), uuid4()
    provenance = SemanticFactProvenance(
        source_record_ids=(record_id,),
        source_text="The h1 must read exactly N1 Budget on index.html.",
        role_origin=SemanticRoleOrigin.EXPLICIT)
    admitted = EngineeringSemanticFact(
        id=fact_id, subject="marketing.lead", relation=SemanticRelation.EQUALITY,
        value="N1 Budget", scope="index.html", qualifiers={},
        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
        provenance=provenance, admitted_work_revision_id=revision)
    reference = SemanticFactReference(
        fact_id=fact_id, subject=admitted.subject, relation=admitted.relation,
        value=admitted.value, scope=admitted.scope, qualifiers={},
        authority=admitted.authority, epistemic_status=admitted.epistemic_status,
        source_work_revision_id=revision)
    outputs = [
        '{"method":"EXACT_H1","target_path":"other.html","source_quote":"The h1 must read exactly N1 Budget"}',
        '{"method":"EXACT_H1","target_path":"index.html","source_quote":"The h1 must read exactly N1 Budget"}',
    ]
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        return StructuredModelResult(
            output_text=outputs[len(calls) - 1],
            provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-static-html-fixture",
            effective_model="controlled-static-html-fixture",
            request_id=f"plan-{len(calls)}",
            usage=ModelUsage(unknown=True), timing=ModelTiming())
    runtime = SimpleNamespace(generate=generate,
                              registry=SimpleNamespace(close=lambda: None))
    checks = verify_static_html_semantic_facts(
        repository, candidate, contract, (reference,),
        admitted_facts={str(fact_id): admitted},
        plan_repair=StaticHTMLPlanRepair(lambda: runtime))
    assert checks[0]["passed"] is True
    plan = checks[0]["materialization"]
    assert plan["method"] == "EXACT_H1"
    assert plan["repair_attempts"] == 2
    assert [row["request_id"] for row in plan["model_repair"]["attempts"]] == [
        "plan-1", "plan-2"]
    assert all(row["usage"]["unknown"] is True
               and row["usage"]["total_tokens"] is None
               for row in plan["model_repair"]["attempts"])
    assert plan["provenance_checked"] is True
    assert plan["source_record_ids"] == [str(record_id)]
    assert calls[1]["input_text"].find("target path differs") >= 0
    assert reference.value == "N1 Budget" and reference.scope == "index.html"
    with pytest.raises(ValueError, match="differs from admitted fact"):
        verify_static_html_semantic_facts(
            repository, candidate, contract,
            (reference.model_copy(update={"value": "fabricated value"}),),
            admitted_facts={str(fact_id): admitted})
    candidate = _candidate(repository, ITEMS, extra="<h2>Unexpected</h2>")
    calls.clear()
    checks = verify_static_html_semantic_facts(
        repository, candidate, contract, (reference,),
        admitted_facts={str(fact_id): admitted},
        plan_repair=StaticHTMLPlanRepair(lambda: runtime))
    assert checks[0]["passed"] is False
    assert checks[0]["reason"] == "EXACT_H1_MISMATCH"


def test_model_plan_exhaustion_cannot_invent_source_or_pass(tmp_path: Path) -> None:
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    fact_id, revision = uuid4(), uuid4()
    admitted = EngineeringSemanticFact(
        id=fact_id, subject="marketing.lead", relation=SemanticRelation.EQUALITY,
        value="N1 Budget", scope="index.html", qualifiers={},
        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
        provenance=SemanticFactProvenance(source_record_ids=(uuid4(),),
            source_text="The h1 must read exactly N1 Budget on index.html.",
            role_origin=SemanticRoleOrigin.EXPLICIT),
        admitted_work_revision_id=revision)
    reference = SemanticFactReference(
        fact_id=fact_id, subject=admitted.subject, relation=admitted.relation,
        value=admitted.value, scope=admitted.scope, qualifiers={},
        authority=admitted.authority, epistemic_status=admitted.epistemic_status,
        source_work_revision_id=revision)
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        return StructuredModelResult(output_text=(
            '{"method":"EXACT_H1","target_path":"index.html",'
            '"source_quote":"invented Human approval"}'),
            provider=ModelProvider.DEEPSEEK,
            requested_model="controlled-static-html-fixture",
            effective_model="controlled-static-html-fixture",
            request_id=f"invalid-{len(calls)}",
            usage=ModelUsage(unknown=True), timing=ModelTiming())
    runtime = SimpleNamespace(generate=generate,
                              registry=SimpleNamespace(close=lambda: None))
    checks = verify_static_html_semantic_facts(
        repository, candidate, contract, (reference,),
        admitted_facts={str(fact_id): admitted},
        plan_repair=StaticHTMLPlanRepair(lambda: runtime))
    assert len(calls) == 2
    assert checks[0]["reason"] == "UNVERIFIABLE_FACT_PLAN"
    repair = checks[0]["materialization"]["model_repair"]
    assert repair["converged"] is False
    assert [row["request_id"] for row in repair["attempts"]] == [
        "invalid-1", "invalid-2"]
    assert all(row["usage"]["unknown"] is True
               and row["usage"]["total_tokens"] is None
               for row in repair["attempts"])


def _count_plan_runtime(method, quote, *, target='index.html'):
    import json
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        return StructuredModelResult(
            output_text=json.dumps({'method': method, 'target_path': target, 'source_quote': quote}),
            provider=ModelProvider.DEEPSEEK, requested_model='controlled-count-fixture',
            effective_model='controlled-count-fixture', request_id=f'count-{len(calls)}',
            usage=ModelUsage(unknown=True), timing=ModelTiming())
    return SimpleNamespace(generate=generate, registry=SimpleNamespace(close=lambda: None)), calls


def _admitted_count(source, *, qualifiers=None, value=1, scope=None, subject='not.prelisted.cardinality'):
    return EngineeringSemanticFact(
        id=uuid4(), subject=subject, relation=SemanticRelation.CARDINALITY,
        value=value, scope=scope, qualifiers=qualifiers or {},
        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
        provenance=SemanticFactProvenance(source_record_ids=(uuid4(),), source_text=source,
            role_origin=SemanticRoleOrigin.EXPLICIT), admitted_work_revision_id=uuid4())


@pytest.mark.parametrize('method,source,qualifiers,extra', [
    ('EXACT_H1_COUNT', 'Only one h1 element is required.', {'level': 'h1'}, ''),
    ('EXACT_PARAGRAPH_COUNT', 'The page shall contain exactly one paragraph.', {}, '<p>copy</p>'),
    ('EXACT_PARAGRAPH_COUNT', '正文必须有一个段落。', {}, '<p>copy</p>'),
    ('EXACT_PARAGRAPH_COUNT', 'Create an HTML file with one h1 and one paragraph.', {}, '<p>copy</p>'),
    ('EXACT_PARAGRAPH_COUNT', 'Only one introductory text block is needed.', {'element':'p'}, '<p>copy</p>'),
])
def test_cardinality_materializes_existing_check_without_subject_alias(tmp_path, method, source, qualifiers, extra):
    from spg.domain.engineering_semantics import semantic_fact_reference
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS, extra=extra)
    admitted = _admitted_count(source, qualifiers=qualifiers)
    reference = semantic_fact_reference(admitted, work_revision_id=admitted.admitted_work_revision_id)
    original = admitted.model_dump(mode='json')
    runtime, calls = _count_plan_runtime(method, source)
    check = verify_static_html_semantic_facts(repository, candidate, contract, (reference,),
        admitted_facts={str(admitted.id): admitted}, plan_repair=StaticHTMLPlanRepair(lambda: runtime))[0]
    assert check['passed'] and check['materialization']['method'] == method
    assert check['materialization']['provenance_checked']
    assert len(calls) == 2 and admitted.model_dump(mode='json') == original
    extra = '<h1>wrong second heading</h1>' if method == 'EXACT_H1_COUNT' else '<p>copy</p><p>extra</p>'
    wrong = _candidate(repository, ITEMS, extra=extra)
    runtime, calls = _count_plan_runtime(method, source)
    check = verify_static_html_semantic_facts(repository, wrong, contract, (reference,),
        admitted_facts={str(admitted.id): admitted}, plan_repair=StaticHTMLPlanRepair(lambda: runtime))[0]
    assert check['reason'] == method + '_MISMATCH' and check['disposition'] == 'FAILED_CURRENT'
    assert len(calls) == 2  # A real artifact mismatch is not a plan-repair retry.


@pytest.mark.parametrize('method,source,qualifiers,scope,value,quote,target,code', [
    ('EXACT_NEW_FILE_COUNT', 'One h1 on index.html.', {'level':'h1'}, None, 1, None, 'index.html', 'COUNT_OBJECT_QUALIFIER_MISMATCH'),
    ('EXACT_H1_COUNT', 'One h1 and one paragraph.', {'element':'p'}, None, 1, None, 'index.html', 'COUNT_OBJECT_QUALIFIER_MISMATCH'),
    ('EXACT_PARAGRAPH_COUNT', 'One paragraph.', {'level':'h1'}, None, 1, None, 'index.html', 'COUNT_OBJECT_QUALIFIER_MISMATCH'),
    ('EXACT_PARAGRAPH_COUNT', 'One paragraph.', {'within':'footer'}, None, 1, None, 'index.html', 'COUNT_QUALIFIER_NOT_REPRESENTABLE'),
    ('EXACT_PARAGRAPH_COUNT', 'One paragraph.', {}, 'footer in index.html', 1, None, 'index.html', 'COUNT_SCOPE_NOT_REPRESENTABLE'),
    ('EXACT_PARAGRAPH_COUNT', 'Only one paragraph is permitted.', {}, None, 1, 'one paragraph', 'index.html', 'COUNT_SOURCE_COVERAGE_MISMATCH'),
    ('EXACT_PARAGRAPH_COUNT', 'One paragraph.', {}, None, 1, 'invented approval', 'index.html', 'exact Human source quote'),
    ('EXACT_PARAGRAPH_COUNT', 'One paragraph.', {}, None, True, None, 'index.html', 'COUNT_RELATION_VALUE_MISMATCH'),
    ('EXACT_PARAGRAPH_COUNT', 'One paragraph.', {}, None, -1, None, 'index.html', 'COUNT_RELATION_VALUE_MISMATCH'),
    ('EXACT_PARAGRAPH_COUNT', 'One paragraph.', {}, None, 1, None, 'other.html', 'target path differs'),
])
def test_count_plan_rejects_wrong_object_missing_qualifiers_and_source(method, source, qualifiers, scope, value, quote, target, code):
    from spg.domain.engineering_semantics import semantic_fact_reference
    from spg.providers.static_html_semantic_verifier import _HTMLPlanCandidate
    admitted = _admitted_count(source, qualifiers=qualifiers, scope=scope, value=value)
    reference = semantic_fact_reference(admitted, work_revision_id=admitted.admitted_work_revision_id)
    plan = _HTMLPlanCandidate(method=method, target_path=target, source_quote=source if quote is None else quote)
    assert code in StaticHTMLPlanRepair._candidate_problem(plan, reference, source, 'index.html')


def test_element_count_never_inherits_one_new_file_success(tmp_path):
    from spg.domain.engineering_semantics import semantic_fact_reference
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS, extra='<h1>extra</h1>')
    admitted = _admitted_count('Create index.html with exactly one h1.', qualifiers={'level':'h1'})
    reference = semantic_fact_reference(admitted, work_revision_id=admitted.admitted_work_revision_id)
    check = verify_static_html_semantic_facts(repository, candidate, contract, (reference,),
        admitted_facts={str(admitted.id): admitted})[0]
    assert check['reason'] == 'UNVERIFIABLE_FACT_PLAN' and not check['passed']
    runtime, calls = _count_plan_runtime('EXACT_NEW_FILE_COUNT', admitted.provenance.source_text)
    check = verify_static_html_semantic_facts(repository, candidate, contract, (reference,),
        admitted_facts={str(admitted.id): admitted}, plan_repair=StaticHTMLPlanRepair(lambda: runtime))[0]
    assert check['reason'] == 'UNVERIFIABLE_FACT_PLAN' and len(calls) == 2
    assert 'COUNT_OBJECT_QUALIFIER_MISMATCH' in calls[1]['input_text']


def test_count_model_cannot_change_admitted_fact_identity(tmp_path):
    from spg.domain.engineering_semantics import semantic_fact_reference
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    admitted = _admitted_count('One h1.', qualifiers={'level':'h1'})
    reference = semantic_fact_reference(admitted, work_revision_id=admitted.admitted_work_revision_id).model_copy(update={"subject": "changed.subject"})
    runtime, calls = _count_plan_runtime('EXACT_H1_COUNT', admitted.provenance.source_text)
    with pytest.raises(ValueError, match='differs from admitted fact'):
        verify_static_html_semantic_facts(repository, candidate, contract, (reference,),
            admitted_facts={str(admitted.id):admitted}, plan_repair=StaticHTMLPlanRepair(lambda: runtime))


def test_count_unrepresented_unit_and_boolean_qualifier_are_rejected():
    from spg.domain.engineering_semantics import semantic_fact_reference
    from spg.providers.static_html_semantic_verifier import _HTMLPlanCandidate
    admitted = _admitted_count('One h1.', qualifiers={'heading_level': True})
    ref = semantic_fact_reference(admitted, work_revision_id=admitted.admitted_work_revision_id)
    plan = _HTMLPlanCandidate(method='EXACT_H1_COUNT', target_path='index.html', source_quote='One h1.')
    assert StaticHTMLPlanRepair._candidate_problem(plan, ref, 'One h1.', 'index.html') == 'COUNT_OBJECT_QUALIFIER_MISMATCH'
    ref = ref.model_copy(update={'unit':'words', 'qualifiers':{}})
    assert StaticHTMLPlanRepair._candidate_problem(plan, ref, 'One h1.', 'index.html') == 'COUNT_UNIT_NOT_REPRESENTABLE'


@pytest.mark.parametrize('source,subject,proposal', [
    ('Exactly one existing file must remain present.', 'retained.asset.count', 'EXACT_NEW_FILE_COUNT'),
    ('Only one word is required; h1 is merely an example.', 'word.quantity', 'EXACT_H1_COUNT'),
])
def test_independent_count_review_refuses_lifecycle_or_example_object_error(tmp_path, source, subject, proposal):
    import json
    from spg.domain.engineering_semantics import semantic_fact_reference
    repository, contract = _fixture(tmp_path)
    candidate = _candidate(repository, ITEMS)
    admitted = _admitted_count(source, subject=subject)
    ref = semantic_fact_reference(admitted, work_revision_id=admitted.admitted_work_revision_id)
    calls=[]
    def generate(**kwargs):
        calls.append(kwargs)
        method=proposal if len(calls)==1 else 'UNVERIFIABLE'
        return StructuredModelResult(output_text=json.dumps({'method':method,'target_path':'index.html','source_quote':source}),
            provider=ModelProvider.DEEPSEEK, requested_model='controlled-independent-count-review',
            effective_model='controlled-independent-count-review', request_id=f'object-review-{len(calls)}',
            usage=ModelUsage(unknown=True), timing=ModelTiming())
    runtime=SimpleNamespace(generate=generate, registry=SimpleNamespace(close=lambda:None))
    check=verify_static_html_semantic_facts(repository,candidate,contract,(ref,),
        admitted_facts={str(admitted.id):admitted},plan_repair=StaticHTMLPlanRepair(lambda:runtime))[0]
    assert check['reason']=='UNVERIFIABLE_FACT_PLAN' and not check['passed'] and len(calls)==2
    assert 'Independently review' in calls[1]['instructions']
    assert json.loads(calls[1]['input_text'])['subject']==subject
    assert check['materialization']['model_repair']['independent_plan_review']


@pytest.mark.parametrize("drift", ("basis-wire", "observed-wire", "decoded-proposal", "review-wire", "review-result", "review-attempt", "missing-proposal", "failed-proposal", "fact", "source"))
def test_count_review_corrects_derived_plan_with_original_receipt_budget(tmp_path, drift):
    import json
    from spg.domain.engineering_semantics import semantic_fact_reference
    from spg.providers.verification_receipts import VerificationCandidateReceipts
    repository,contract=_fixture(tmp_path);candidate=_candidate(repository,ITEMS,extra='<p>copy</p>')
    admitted=_admitted_count('One paragraph.');ref=semantic_fact_reference(admitted,work_revision_id=admitted.admitted_work_revision_id)
    request=SimpleNamespace(verification_identity=uuid4(),snapshot_id=uuid4(),source_baseline_id=contract.source_baseline_id,
        proposed_commit_identity=candidate,tree_identity=_git(repository,'rev-parse',candidate+'^{tree}'),
        decision_context_fingerprint='a'*64,semantic_fact_obligations=(ref,),protected_context_obligations=())
    recorder=VerificationCandidateReceipts(request);calls=[]
    def generate(**kwargs):
        calls.append(kwargs)
        return StructuredModelResult(output_text=json.dumps({'method':'EXACT_NEW_FILE_COUNT' if len(calls)==1 else 'EXACT_PARAGRAPH_COUNT',
            'target_path':'index.html','source_quote':admitted.provenance.source_text}),
            provider=ModelProvider.DEEPSEEK,requested_model='controlled-count-review',effective_model='controlled-count-review',
            request_id=f'bounded-count-{len(calls)}',usage=ModelUsage(unknown=True),timing=ModelTiming())
    runtime=SimpleNamespace(generate=generate,registry=SimpleNamespace(close=lambda:None))
    repair=StaticHTMLPlanRepair(lambda:runtime,receipt_recorder=recorder)
    check=verify_static_html_semantic_facts(repository,candidate,contract,(ref,),
        admitted_facts={str(admitted.id):admitted},plan_repair=repair)[0]
    assert check['passed'] and len(calls)==2
    assert 'Independently review' in calls[1]['instructions']
    assert [r['attempt'] for r in recorder.records if r['stage']=='MODEL_REQUEST_PENDING']==[1,2]
    assert all(r['budget_limit']==2 and r['candidate_is_authority'] is False for r in recorder.records)
    assert recorder.records[-1]['plan_review_role']=='INDEPENDENT_COUNT_PLAN_REVIEW'
    original=json.dumps(recorder.records,sort_keys=True)
    repair.runtime_factory=lambda:(_ for _ in ()).throw(AssertionError('no replay calls'))
    replay=verify_static_html_semantic_facts(repository,candidate,contract,(ref,),
        admitted_facts={str(admitted.id):admitted},plan_repair=repair)[0]
    assert replay['passed'] and replay['materialization']['model_repair']['replayed']
    assert json.dumps(recorder.records,sort_keys=True)==original
    if drift=='basis-wire':recorder.records[-1]['plan_review_basis']['proposal_wire_sha256']='f'*64
    elif drift=='observed-wire':recorder.records[1]['candidate_output']+=' '
    elif drift=='decoded-proposal':recorder.records[2]['candidate_checks'][0]['method']='EXACT_H1_COUNT'
    elif drift=='review-wire':recorder.records[4]['candidate_output']+=' '
    elif drift=='review-result':recorder.records[-1]['candidate_checks'][0]['method']='EXACT_NEW_FILE_COUNT'
    elif drift=='review-attempt':recorder.records[-1]['attempt']=1
    elif drift=='missing-proposal':recorder.records.pop(2)
    elif drift=='failed-proposal':recorder.records[2]['failed_predicate']='controlled-failure'
    elif drift=='fact':ref=ref.model_copy(update={'subject':'changed.fact'})
    else:admitted=admitted.model_copy(update={'provenance':admitted.provenance.model_copy(update={'source_text':'changed source'})})
    with pytest.raises(ValueError,match='VERIFICATION_REPLAY_BASIS_MISMATCH'):
        repair.repair(ref,admitted,'index.html')
