"""Contract-driven read-only Verification Provider for governed Markdown artifacts."""

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

from spg.domain.engineering_semantics import SemanticFactAuthority, SemanticRelation
from spg.domain.runtime import ArtifactContract, ArtifactOperation
from spg.domain.verification import (
    VerificationCapabilityRequest,
    VerificationCapabilityResult,
    VerificationEvidence,
    VerificationProviderBinding,
    VerificationResultValue,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


@dataclass(frozen=True, slots=True)
class ArtifactVerificationFacts:
    exact_path_only: bool
    operation_matches: bool
    readable_non_empty: bool
    required_markers_present: bool
    section_order_matches: bool
    diff_valid: bool

    @property
    def passed(self) -> bool:
        return all(
            (
                self.exact_path_only,
                self.operation_matches,
                self.readable_non_empty,
                self.required_markers_present,
                self.section_order_matches,
                self.diff_valid,
            )
        )


class RepositoryArtifactVerifier:
    """Resolve the target only from the exact PWU Completion Contract."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self._binding = VerificationProviderBinding(
            provider_identity="provider:repository-artifact-contract",
            provider_version="v2",
        )

    @property
    def binding(self) -> VerificationProviderBinding:
        return self._binding

    def verify(
        self,
        request: VerificationCapabilityRequest,
    ) -> VerificationCapabilityResult:
        target_path: str | None = None
        try:
            with self.database.unit_of_work() as unit_of_work:
                store = RuntimeStore(unit_of_work.session)
                proposed = store.proposed_snapshot(request.snapshot_id)
                if proposed is None:
                    raise RuntimeError("proposed snapshot unavailable")
                source = store.snapshot(request.source_baseline_id)
                dispatch = store.execution_dispatch_for_attempt(proposed.attempt_id)
                work_unit = store.work_unit(proposed.work_unit_id)
            if source is None or dispatch is None or work_unit is None:
                raise RuntimeError("verification repository lineage unavailable")
            if (
                proposed.proposed_commit_identity != request.proposed_commit_identity
                or proposed.tree_identity != request.tree_identity
            ):
                raise RuntimeError("verification subject identity mismatch")
            artifact = work_unit.completion_contract.artifact_contract
            if artifact is None:
                raise RuntimeError("PWU has no admitted Artifact Contract")
            if (
                artifact.source_baseline_id != source.id
                or artifact.source_revision != source.repository_revision
                or artifact.repository_identity != source.repository_identity
                or artifact.verification_obligation != request.obligation
            ):
                raise RuntimeError("Artifact Contract lineage is incoherent")
            if (request.semantic_fact_obligations
                    != work_unit.completion_contract.semantic_fact_obligations):
                raise RuntimeError("Artifact semantic obligations differ from admitted contract")
            target_path = artifact.artifact_path
            section_facts = tuple(
                item for item in work_unit.completion_contract.semantic_fact_obligations
                if item.subject == "document.sections"
                and item.relation is SemanticRelation.ORDERED_COMPONENT
                and item.authority is SemanticFactAuthority.HUMAN_EXPLICIT
                and item.scope in {None, target_path, Path(target_path).stem}
            )
            if len(section_facts) > 1:
                raise RuntimeError("Conflicting admitted document section obligations")
            required_sections = (
                tuple(str(value) for value in section_facts[0].value)
                if section_facts and isinstance(section_facts[0].value, tuple)
                else ()
            )
            facts = evaluate_repository_artifact(
                dispatch.workspace.repository_path,
                source.repository_revision,
                request.proposed_commit_identity,
                artifact,
                required_markers=work_unit.completion_contract.required_markers,
                required_sections=required_sections,
            )
            result = (
                VerificationResultValue.PASS
                if facts.passed
                else VerificationResultValue.FAIL
            )
            metadata = {
                "mode": "contract-driven-read-only-git",
                "target_path": target_path,
                "operation": artifact.operation.value,
                "exact_path_only": facts.exact_path_only,
                "operation_matches": facts.operation_matches,
                "readable_non_empty": facts.readable_non_empty,
                "required_markers_present": facts.required_markers_present,
                "section_order_matches": facts.section_order_matches,
                "diff_valid": facts.diff_valid,
            }
        except Exception as error:
            result = VerificationResultValue.UNKNOWN
            metadata = {
                "mode": "contract-driven-read-only-git",
                "target_path": target_path,
                "failure_type": type(error).__name__,
            }
        metadata["semantic_fact_ids"] = [
            str(item.fact_id) for item in request.semantic_fact_obligations
        ]
        return VerificationCapabilityResult(
            result=result,
            evidence=VerificationEvidence(
                obligation=request.obligation,
                subject_commit_identity=request.proposed_commit_identity,
                subject_tree_identity=request.tree_identity,
                expected="exact Human-admitted artifact contract",
                observed=result.value,
                metadata=metadata,
            ),
        )


# Configuration compatibility: the adapter name remains stable while behavior is generic.
MvpE2eMarkdownVerifier = RepositoryArtifactVerifier


def evaluate_repository_artifact(
    repository: Path,
    source_revision: str,
    proposed_commit: str,
    artifact: ArtifactContract,
    *,
    required_markers: tuple[str, ...] = (),
    required_sections: tuple[str, ...] = (),
) -> ArtifactVerificationFacts:
    """Evaluate the contract-selected path on one immutable Git subject."""

    changed_rows = _git(
        repository,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        "--no-renames",
        source_revision,
        proposed_commit,
        "--",
    ).splitlines()
    expected_status = "A" if artifact.operation is ArtifactOperation.CREATE else "M"
    expected_row = f"{expected_status}\t{artifact.artifact_path}"
    exact_path_only = (
        len(changed_rows) == 1
        and changed_rows[0].split("\t")[-1] == artifact.artifact_path
    )
    operation_matches = changed_rows == [expected_row]
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
        [
            "git",
            "-C",
            str(repository),
            "show",
            f"{proposed_commit}:{artifact.artifact_path}",
        ],
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
    normalized = " ".join(content.split()).casefold()
    headings = tuple(
        (len(match.group(1)), match.group(2).strip().casefold())
        for match in re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*#*\s*$", content)
    )
    wanted = tuple(section.casefold() for section in required_sections)
    levels = {level for level, title in headings if title in wanted}
    section_order_matches = not wanted or (
        len(levels) == 1
        and tuple(title for level, title in headings if level in levels) == wanted
    )
    identifier = re.compile(
        r"(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{40})"
    )
    def present(marker: str) -> bool:
        if identifier.fullmatch(marker.casefold()):
            return re.search(r"(?<![0-9a-f])" + re.escape(marker.casefold())
                             + r"(?![0-9a-f])", normalized) is not None
        return marker.casefold() in normalized
    return ArtifactVerificationFacts(
        exact_path_only=exact_path_only,
        operation_matches=operation_matches,
        readable_non_empty=readable,
        required_markers_present=all(
            present(marker) for marker in required_markers
        ),
        section_order_matches=section_order_matches,
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
