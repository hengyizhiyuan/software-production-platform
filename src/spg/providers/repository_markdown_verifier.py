"""Narrow read-only Verification Provider for the admitted MVP E2E artifact."""

from dataclasses import dataclass
from pathlib import Path
import subprocess

from spg.domain.verification import (
    VerificationCapabilityRequest,
    VerificationCapabilityResult,
    VerificationEvidence,
    VerificationProviderBinding,
    VerificationResultValue,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


TARGET_PATH = "docs/mvp-e2e/first-real-governed-work.md"
REQUIRED_HEADINGS = (
    "# First Real Governed MVP Work",
    "## Purpose",
    "## Guardrails",
    "## Evidence Boundary",
)
REQUIRED_STATEMENTS = (
    "Provider completion is not Production Truth",
    "Production Reality is determined independently",
    "Human Authority is required before trusted repository integration",
)


@dataclass(frozen=True, slots=True)
class MarkdownVerificationFacts:
    exact_path_only: bool
    headings_present: bool
    statements_present: bool
    readable_non_empty: bool
    diff_valid: bool

    @property
    def passed(self) -> bool:
        return all(
            (
                self.exact_path_only,
                self.headings_present,
                self.statements_present,
                self.readable_non_empty,
                self.diff_valid,
            )
        )


class MvpE2eMarkdownVerifier:
    """Verify one immutable proposed commit without changing repository authority."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self._binding = VerificationProviderBinding(
            provider_identity="provider:mvp-e2e-markdown",
            provider_version="v1",
        )

    @property
    def binding(self) -> VerificationProviderBinding:
        return self._binding

    def verify(
        self,
        request: VerificationCapabilityRequest,
    ) -> VerificationCapabilityResult:
        try:
            with self.database.unit_of_work() as unit_of_work:
                store = RuntimeStore(unit_of_work.session)
                proposed = store.proposed_snapshot(request.snapshot_id)
                if proposed is None:
                    raise RuntimeError("proposed snapshot unavailable")
                source = store.snapshot(request.source_baseline_id)
                dispatch = store.execution_dispatch_for_attempt(proposed.attempt_id)
            if source is None or dispatch is None:
                raise RuntimeError("verification repository lineage unavailable")
            if (
                proposed.proposed_commit_identity != request.proposed_commit_identity
                or proposed.tree_identity != request.tree_identity
            ):
                raise RuntimeError("verification subject identity mismatch")
            facts = evaluate_mvp_e2e_markdown(
                dispatch.workspace.repository_path,
                source.repository_revision,
                request.proposed_commit_identity,
            )
            result = (
                VerificationResultValue.PASS
                if facts.passed
                else VerificationResultValue.FAIL
            )
            metadata = {
                "mode": "targeted-read-only-git",
                "target_path": TARGET_PATH,
                "exact_path_only": facts.exact_path_only,
                "headings_present": facts.headings_present,
                "statements_present": facts.statements_present,
                "readable_non_empty": facts.readable_non_empty,
                "diff_valid": facts.diff_valid,
            }
        except Exception as error:
            result = VerificationResultValue.UNKNOWN
            metadata = {
                "mode": "targeted-read-only-git",
                "target_path": TARGET_PATH,
                "failure_type": type(error).__name__,
            }
        return VerificationCapabilityResult(
            result=result,
            evidence=VerificationEvidence(
                obligation=request.obligation,
                subject_commit_identity=request.proposed_commit_identity,
                subject_tree_identity=request.tree_identity,
                expected="exact admitted Markdown artifact and no other change",
                observed=result.value,
                metadata=metadata,
            ),
        )


def evaluate_mvp_e2e_markdown(
    repository: Path,
    source_revision: str,
    proposed_commit: str,
) -> MarkdownVerificationFacts:
    """Evaluate the exact immutable Git subject without checking out or mutating it."""

    changed = _git(
        repository,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        "--no-renames",
        source_revision,
        proposed_commit,
        "--",
    ).splitlines()
    diff_check = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "diff",
            "--check",
            source_revision,
            proposed_commit,
            "--",
        ],
        check=False,
        capture_output=True,
    )
    raw = subprocess.run(
        ["git", "-C", str(repository), "show", f"{proposed_commit}:{TARGET_PATH}"],
        check=False,
        capture_output=True,
    )
    content = ""
    readable = False
    if raw.returncode == 0:
        try:
            content = raw.stdout.decode("utf-8", errors="strict")
            readable = bool(content.strip())
        except UnicodeDecodeError:
            readable = False
    lines = {line.strip() for line in content.splitlines()}
    normalized = " ".join(content.split()).casefold()
    return MarkdownVerificationFacts(
        exact_path_only=changed == [TARGET_PATH],
        headings_present=all(item in lines for item in REQUIRED_HEADINGS),
        statements_present=all(
            item.casefold() in normalized for item in REQUIRED_STATEMENTS
        ),
        readable_non_empty=readable,
        diff_valid=diff_check.returncode == 0,
    )


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("targeted Git verification command failed")
    return result.stdout.strip()
