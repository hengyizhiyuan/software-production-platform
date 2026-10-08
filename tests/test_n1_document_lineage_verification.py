"""N1: admitted exact document lineage must survive into independent Verification."""

from pathlib import Path
import subprocess
from types import SimpleNamespace
from uuid import uuid4

import pytest

from spg.application.steering_production import SteeringProductionService
from spg.domain.product import ProductInvariantViolation
from spg.domain.runtime import ArtifactContract, ArtifactOperation
from spg.providers.repository_markdown_verifier import evaluate_repository_artifact


OBJECTIVE = (
    "Create docs/n1-qualification.md and keep the exact source and Work lineage "
    "visible (Work ae8530f0-1f28-55f7-aea6-e79b13c7fabd, Semantic IR "
    "9a88e343-6c62-5b30-af81-83594b03e171, governance decisions "
    "f4a91c10-1d27-57c5-9617-2220b916b33b and "
    "efb0a35b-a549-4f3e-ae94-9fcf75d68724, trusted baseline "
    "a2156420-503d-403a-9d56-d149313449b9, source revision "
    "b8dcb6327108507b1a345e01c196e02260717226, source tree "
    "d9299264976c0a381a9fecc4158524bed5e065a2)."
)
EXPECTATION = "Confirm the exact source and Work lineage identifiers appear in the document."


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repository), *args], check=True,
                            capture_output=True, text=True)
    return result.stdout.strip()


def _fixture(tmp_path: Path) -> tuple[Path, str, ArtifactContract]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "N1 Test")
    _git(repository, "config", "user.email", "n1@example.invalid")
    (repository / "README.md").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "baseline")
    source = _git(repository, "rev-parse", "HEAD")
    artifact = ArtifactContract(
        engineering_resource_id=uuid4(), repository_identity="watt://n1-test",
        source_baseline_id=uuid4(), source_revision=source,
        artifact_path="docs/n1-qualification.md", operation=ArtifactOperation.CREATE,
        expected_outcome=OBJECTIVE, verification_obligation=EXPECTATION,
    )
    return repository, source, artifact


def _candidate(repository: Path, content: str) -> str:
    target = repository / "docs/n1-qualification.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(repository, "add", "docs/n1-qualification.md")
    _git(repository, "commit", "-m", "candidate")
    return _git(repository, "rev-parse", "HEAD")


def test_exact_admitted_lineage_becomes_nonempty_verification_markers() -> None:
    markers = SteeringProductionService._exact_document_lineage_markers(
        SimpleNamespace(verification_expectation=EXPECTATION),
        admitted_objective=OBJECTIVE)
    assert len(markers) == 7
    assert "9a88e343-6c62-5b30-af81-83594b03e171" in markers
    assert "efb0a35b-a549-4f3e-ae94-9fcf75d68724" in markers
    with pytest.raises(ProductInvariantViolation, match="literal identifiers"):
        SteeringProductionService._exact_document_lineage_markers(
            SimpleNamespace(verification_expectation=EXPECTATION),
            admitted_objective="Write a document")


def test_exact_identifiers_in_admitted_verification_expectation_are_consumed() -> None:
    expectation = (
        "Confirm the exact source and Work lineage identifiers appear in the "
        "document (source lineage identifier 17fa255, source revision "
        "7513e0a634d8d7148da27ac028d28b8525d3b97b, Work id "
        "d1c7515c-9ff2-585c-80d2-c086968f258b)."
    )
    markers = SteeringProductionService._exact_document_lineage_markers(
        SimpleNamespace(verification_expectation=expectation),
        admitted_objective="Produce the document with exact lineage identifiers")
    assert markers == (
        "7513e0a634d8d7148da27ac028d28b8525d3b97b",
        "d1c7515c-9ff2-585c-80d2-c086968f258b", "17fa255")


def test_new_candidate_missing_one_lineage_id_fails_verification(tmp_path: Path) -> None:
    repository, source, artifact = _fixture(tmp_path)
    markers = SteeringProductionService._exact_document_lineage_markers(
        SimpleNamespace(verification_expectation=EXPECTATION),
        admitted_objective=OBJECTIVE)
    missing = "9a88e343-6c62-5b30-af81-83594b03e171"
    content = (
        "# Qualification\n\n## Purpose\n\nLineage: "
        + ", ".join(item for item in markers if item != missing)
        + "\n\n## Assumptions\n\nIsolated.\n\n"
        "## Verification Checklist\n\n- [ ] Inspect document.\n"
    )
    candidate = _candidate(repository, content)
    facts = evaluate_repository_artifact(
        repository, source, candidate, artifact, required_markers=markers,
        required_sections=("purpose", "assumptions", "verification checklist"))
    assert not facts.passed
    assert not facts.required_markers_present
    assert facts.section_order_matches


def test_new_candidate_exact_lineage_and_sections_pass_then_wrong_order_fails(
    tmp_path: Path,
) -> None:
    repository, source, artifact = _fixture(tmp_path)
    markers = SteeringProductionService._exact_document_lineage_markers(
        SimpleNamespace(verification_expectation=EXPECTATION),
        admitted_objective=OBJECTIVE)
    lineage = ", ".join(markers)
    good = _candidate(repository, "# Qualification\n\n## Purpose\n\n" + lineage
                      + "\n\n## Assumptions\n\nIsolated.\n\n"
                      "## Verification Checklist\n\n- [ ] Inspect document.\n")
    assert evaluate_repository_artifact(
        repository, source, good, artifact, required_markers=markers,
        required_sections=("purpose", "assumptions", "verification checklist")).passed
    bad = _candidate(repository, "# Qualification\n\n## Assumptions\n\n" + lineage
                     + "\n\n## Purpose\n\nIsolated.\n\n"
                     "## Verification Checklist\n\n- [ ] Inspect document.\n")
    facts = evaluate_repository_artifact(
        repository, source, bad, artifact, required_markers=markers,
        required_sections=("purpose", "assumptions", "verification checklist"))
    assert not facts.passed
    assert not facts.section_order_matches
