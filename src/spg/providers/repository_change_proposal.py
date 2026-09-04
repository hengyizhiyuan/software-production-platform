"""Deterministic read-only repository inspection for Code Work refinement."""

from collections import Counter
from pathlib import Path
import re
import subprocess
from uuid import NAMESPACE_URL, uuid5

from spg.domain.change import (
    ChangeOperation,
    CodeVerificationKind,
    CodeVerificationObligation,
)
from spg.domain.refinement import (
    ProposalConfidence,
    ProposalTargetDisposition,
    RepositoryChangeProposal,
    RepositoryChangeProposalRequest,
    RepositoryChangeProposalTarget,
    RepositoryProposalProvenance,
)


_TEXT_SUFFIXES = {".py", ".js", ".cjs", ".mjs", ".html", ".css", ".ts", ".tsx"}
_TEST_PREFIXES = ("tests/", "test/")
_FRONTEND_MARKERS = ("frontend", "javascript", "browser", "web ui", "前端", "页面", "浏览器")
_SEMANTIC_TERMS = {
    "composer": ("composer",),
    "展开": ("expand", "expanded", "aria-expanded", "toggle"),
    "收缩": ("collapse", "collapsed", "aria-expanded", "toggle"),
    "折叠": ("collapse", "collapsed", "aria-expanded", "toggle"),
    "刷新": ("storage", "localstorage", "sessionstorage", "state"),
    "保持": ("storage", "localstorage", "sessionstorage", "state"),
    "状态": ("state", "storage"),
}


class RepositoryAwareChangeProposalProvider:
    """Inspect one exact Git commit without checking out or modifying it."""

    identity = "provider:repository-aware-change-proposal-lite"
    version = "v1"

    def propose(
        self,
        request: RepositoryChangeProposalRequest,
    ) -> RepositoryChangeProposal:
        repository = Path(request.repository_location).resolve()
        self._require_revision(repository, request.source_revision)
        paths = self._tree_paths(repository, request.source_revision)
        path_set = set(paths)
        explicit = tuple(dict.fromkeys(request.explicit_targets))
        targets: list[RepositoryChangeProposalTarget] = [
            self._target(
                path=path,
                paths=path_set,
                disposition=ProposalTargetDisposition.REQUIRED,
                rationale="The Human explicitly named this repository target.",
                evidence=f"Explicit path in refined intent; inspected at {request.source_revision[:12]}.",
                confidence=ProposalConfidence.HIGH,
            )
            for path in explicit
        ]
        unresolved: list[str] = []

        if not explicit and not request.explicit_allowed_areas:
            discovered, discovery_questions = self._discover(
                repository,
                request.source_revision,
                paths,
                request.refined_code_intent,
                request.constraints,
            )
            targets.extend(discovered)
            unresolved.extend(discovery_questions)

        obligations = self._verification_obligations(
            tuple(target for target in targets if target.disposition is ProposalTargetDisposition.REQUIRED),
            request.explicit_allowed_areas,
            request.requested_verification,
            unresolved,
        )
        if not any(
            target.disposition is ProposalTargetDisposition.REQUIRED for target in targets
        ) and not request.explicit_allowed_areas:
            unresolved.append(
                "Repository inspection could not establish a bounded required target; Human refinement is required."
            )

        confidence = (
            ProposalConfidence.HIGH
            if explicit
            else ProposalConfidence.MEDIUM
            if any(target.disposition is ProposalTargetDisposition.REQUIRED for target in targets)
            else ProposalConfidence.LOW
        )
        identity_material = "|".join(
            (
                str(request.work_id),
                request.source_revision,
                *(f"{target.disposition.value}:{target.path}" for target in targets),
                *request.explicit_allowed_areas,
                *unresolved,
            )
        )
        return RepositoryChangeProposal(
            proposal_id=uuid5(NAMESPACE_URL, f"spg:change-proposal:{identity_material}"),
            engineering_resource_id=request.engineering_resource_id,
            repository_identity=request.repository_identity,
            source_baseline_id=request.source_baseline_id,
            source_ref=request.source_ref,
            source_revision=request.source_revision,
            proposed_targets=tuple(targets),
            allowed_areas=request.explicit_allowed_areas,
            forbidden_areas=self._forbidden_areas(
                paths,
                request.refined_code_intent,
                request.constraints,
                request.explicit_forbidden_areas,
            ),
            rationale=(
                "Proposed from explicit Human paths and exact-baseline inspection."
                if explicit
                else "Proposed from exact-baseline path, symbol, and adjacent-test evidence."
            ),
            confidence=confidence,
            verification_obligations=obligations,
            provenance=RepositoryProposalProvenance(
                provider_identity=self.identity,
                provider_version=self.version,
                inspection_method="git-object-read-only:path-enumeration+text-search",
            ),
            unresolved_scope_questions=tuple(dict.fromkeys(unresolved)),
        )

    def _discover(
        self,
        repository: Path,
        revision: str,
        paths: tuple[str, ...],
        intent: str,
        constraints: tuple[str, ...],
    ) -> tuple[list[RepositoryChangeProposalTarget], list[str]]:
        terms = self._search_terms(intent)
        if not terms:
            return [], []
        scores: Counter[str] = Counter()
        matched_terms: dict[str, list[str]] = {}
        for term in terms:
            for path in self._grep_paths(repository, revision, term):
                if Path(path).suffix.casefold() not in _TEXT_SUFFIXES:
                    continue
                scores[path] += 1
                matched_terms.setdefault(path, []).append(term)

        frontend_only = self._frontend_only(intent, constraints)
        if frontend_only:
            scores = Counter(
                {
                    path: score
                    for path, score in scores.items()
                    if self._is_frontend_path(path)
                }
            )
        source_candidates = [
            path for path, _score in scores.most_common() if not path.startswith(_TEST_PREFIXES)
        ]
        if not source_candidates:
            return [], []
        primary = source_candidates[0]
        result = [
            self._target(
                path=primary,
                paths=set(paths),
                disposition=ProposalTargetDisposition.REQUIRED,
                rationale="This file contains the strongest matching implementation behavior.",
                evidence=f"Exact-baseline {revision[:12]} matches: "
                + ", ".join(tuple(dict.fromkeys(matched_terms[primary]))[:4]),
                confidence=ProposalConfidence.HIGH,
            )
        ]

        tests = [
            path
            for path in paths
            if path.startswith(_TEST_PREFIXES)
            and Path(path).suffix.casefold() in _TEXT_SUFFIXES
            and (not frontend_only or self._is_frontend_path(path))
            and self._file_mentions(repository, revision, path, Path(primary).name)
        ]
        if tests:
            test_path = tests[0]
            result.append(
                self._target(
                    path=test_path,
                    paths=set(paths),
                    disposition=ProposalTargetDisposition.REQUIRED,
                    rationale="This adjacent test directly loads or references the selected implementation file.",
                    evidence=(
                        f"{test_path} references {Path(primary).name} "
                        f"at exact Source Baseline {revision[:12]}."
                    ),
                    confidence=ProposalConfidence.HIGH,
                )
            )

        for path in source_candidates[1:]:
            if path == primary or scores[path] < 2:
                continue
            result.append(
                self._target(
                    path=path,
                    paths=set(paths),
                    disposition=ProposalTargetDisposition.CONDITIONAL,
                    rationale="This related file matches the same UI concept but is not proven necessary.",
                    evidence=f"Exact-baseline {revision[:12]} matches: "
                    + ", ".join(tuple(dict.fromkeys(matched_terms[path]))[:4]),
                    confidence=ProposalConfidence.MEDIUM,
                )
            )
            break
        return result, []

    @staticmethod
    def _search_terms(intent: str) -> tuple[str, ...]:
        normalized = intent.casefold()
        terms = {
            token
            for token in re.findall(r"[a-z][a-z0-9_-]{3,}", normalized)
            if token not in {"only", "with", "from", "that", "this", "change", "modify"}
        }
        for marker, expansions in _SEMANTIC_TERMS.items():
            if marker in normalized:
                terms.update(expansions)
        return tuple(sorted(terms))

    @staticmethod
    def _frontend_only(intent: str, constraints: tuple[str, ...]) -> bool:
        text = " ".join((intent, *constraints)).casefold()
        return any(marker in text for marker in _FRONTEND_MARKERS) and any(
            marker in text
            for marker in ("only", "only modify", "不要改动其他", "只修改", "仅修改")
        )

    @staticmethod
    def _is_frontend_path(path: str) -> bool:
        suffix = Path(path).suffix.casefold()
        return (
            path.startswith(("src/spg/web/", "web/", "frontend/", "tests/js/"))
            or suffix in {".js", ".cjs", ".mjs", ".html", ".css", ".ts", ".tsx"}
        )

    @classmethod
    def _forbidden_areas(
        cls,
        paths: tuple[str, ...],
        intent: str,
        constraints: tuple[str, ...],
        explicit: tuple[str, ...],
    ) -> tuple[str, ...]:
        result = list(explicit)
        if cls._frontend_only(intent, constraints):
            available_roots = {path.split("/", 1)[0] for path in paths if "/" in path}
            for area in (
                "src/spg/application/**",
                "src/spg/domain/**",
                "src/spg/infrastructure/**",
                "migrations/**",
            ):
                root = area.split("/", 1)[0]
                if root in available_roots:
                    result.append(area)
        return tuple(dict.fromkeys(result))

    @staticmethod
    def _verification_obligations(
        targets: tuple[RepositoryChangeProposalTarget, ...],
        allowed_areas: tuple[str, ...],
        requested: tuple[CodeVerificationObligation, ...],
        unresolved: list[str],
    ) -> tuple[CodeVerificationObligation, ...]:
        obligations = [
            CodeVerificationObligation(kind=CodeVerificationKind.PATH_SCOPE),
            CodeVerificationObligation(kind=CodeVerificationKind.GIT_DIFF_CHECK),
        ]
        if requested:
            obligations.extend(requested)
        else:
            paths = tuple(target.path for target in targets)
            if any(path.endswith(".py") for path in paths):
                obligations.append(
                    CodeVerificationObligation(kind=CodeVerificationKind.PYTHON_COMPILE)
                )
            for path in paths:
                module = RepositoryAwareChangeProposalProvider._python_module_for_path(
                    path
                )
                if module is not None:
                    obligations.append(
                        CodeVerificationObligation(
                            kind=CodeVerificationKind.IMPORT_CHECK,
                            target=module,
                        )
                    )
                if path.startswith("tests/") and path.endswith(".py"):
                    obligations.append(
                        CodeVerificationObligation(
                            kind=CodeVerificationKind.PYTEST_TARGET,
                            target=path,
                        )
                    )
            if any(
                path.startswith("tests/") and Path(path).suffix.casefold() in {".js", ".cjs", ".mjs"}
                for path in paths
            ):
                unresolved.append(
                    "FRONTEND_VERIFICATION_CONTRACT_GAP: current typed verifier cannot execute the discovered Node test target."
                )
        return tuple({item.identity: item for item in obligations}.values())

    @staticmethod
    def _python_module_for_path(path: str) -> str | None:
        if not path.startswith("src/") or not path.endswith(".py"):
            return None
        stem = path[4:-3].replace("/", ".")
        if stem.endswith(".__init__"):
            stem = stem[: -len(".__init__")]
        return stem or None

    @staticmethod
    def _target(
        *,
        path: str,
        paths: set[str],
        disposition: ProposalTargetDisposition,
        rationale: str,
        evidence: str,
        confidence: ProposalConfidence,
    ) -> RepositoryChangeProposalTarget:
        return RepositoryChangeProposalTarget(
            path=path,
            operation=ChangeOperation.UPDATE if path in paths else ChangeOperation.CREATE,
            disposition=disposition,
            rationale=rationale,
            evidence=evidence,
            confidence=confidence,
        )

    @staticmethod
    def _require_revision(repository: Path, revision: str) -> None:
        completed = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "--verify", f"{revision}^{{commit}}"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0 or completed.stdout.strip() != revision:
            raise RuntimeError("exact Source Baseline revision is unavailable")

    @staticmethod
    def _tree_paths(repository: Path, revision: str) -> tuple[str, ...]:
        completed = subprocess.run(
            ["git", "-C", str(repository), "ls-tree", "-r", "--name-only", revision],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError("exact Source Baseline tree cannot be inspected")
        return tuple(line for line in completed.stdout.splitlines() if line)

    @staticmethod
    def _grep_paths(repository: Path, revision: str, term: str) -> tuple[str, ...]:
        completed = subprocess.run(
            ["git", "-C", str(repository), "grep", "-I", "-l", "-i", "-e", term, revision, "--"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError("exact Source Baseline text search failed")
        prefix = f"{revision}:"
        return tuple(
            line[len(prefix):] if line.startswith(prefix) else line
            for line in completed.stdout.splitlines()
            if line
        )

    @staticmethod
    def _file_mentions(repository: Path, revision: str, path: str, value: str) -> bool:
        completed = subprocess.run(
            ["git", "-C", str(repository), "show", f"{revision}:{path}"],
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0 or len(completed.stdout) > 262_144:
            return False
        return value.casefold() in completed.stdout.decode("utf-8", errors="ignore").casefold()
