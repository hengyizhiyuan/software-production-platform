"""Contract-driven Verification Lite for bounded code Work."""

from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from time import perf_counter
from typing import Iterator

from spg.domain.change import (
    ChangeOperation,
    CodeChangeContract,
    CodeVerificationKind,
    CodeVerificationObligation,
    python_module_paths,
)
from spg.domain.execution import ArtifactChangeType
from spg.domain.engineering_semantics import semantic_fact_reference
from spg.domain.verification import (
    VerificationCapabilityRequest,
    VerificationCapabilityResult,
    VerificationEvidence,
    VerificationProviderBinding,
    VerificationResultValue,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.product_store import ProductStore
from spg.providers.static_html_semantic_verifier import (
    StaticHTMLPlanRepair, verify_static_html_semantic_facts,
)


class RepositoryCodeVerifier:
    """Execute only typed checks admitted by one exact Code Change Contract."""

    def __init__(self, database: Database, *, timeout_seconds: float = 120.0, context_verifier=None) -> None:
        self.database = database
        self.context_verifier = context_verifier
        self.plan_repair = (None if context_verifier is None else
                            StaticHTMLPlanRepair(context_verifier.runtime_factory))
        self.timeout_seconds = timeout_seconds
        self._binding = VerificationProviderBinding(
            provider_identity="provider:repository-code-contract",
            provider_version="v1",
        )

    @property
    def binding(self) -> VerificationProviderBinding:
        return self._binding

    def verify(
        self,
        request: VerificationCapabilityRequest,
    ) -> VerificationCapabilityResult:
        target: str | None = None
        try:
            with self.database.unit_of_work() as unit_of_work:
                store = RuntimeStore(unit_of_work.session)
                proposed = store.proposed_snapshot(request.snapshot_id)
                if proposed is None:
                    raise RuntimeError("proposed snapshot unavailable")
                source = store.snapshot(request.source_baseline_id)
                dispatch = store.execution_dispatch_for_attempt(proposed.attempt_id)
                work_unit = store.work_unit(proposed.work_unit_id)
                run = None if work_unit is None else store.run(work_unit.production_run_id)
                admitted_facts = {}
                if request.semantic_fact_obligations and run is None:
                    raise RuntimeError("Semantic Fact production run is unavailable")
                if work_unit is not None and run is not None:
                    product = ProductStore(unit_of_work.session)
                    for reference in request.semantic_fact_obligations:
                        revision = product.work_reality_revision(reference.source_work_revision_id)
                        if (revision is None or not (
                                run.intent_ref == f"work:{revision.work_id}"
                                or run.intent_ref.startswith(f"work:{revision.work_id}:"))):
                            raise RuntimeError("Semantic Fact has no exact Work Reality lineage")
                        admitted = next((item for item in revision.engineering_semantic_facts
                                         if item.id == reference.fact_id), None)
                        if (admitted is None or semantic_fact_reference(
                                admitted, work_revision_id=revision.id) != reference):
                            raise RuntimeError("Semantic Fact differs from admitted Work Reality")
                        admitted_facts[str(reference.fact_id)] = admitted
            if source is None or dispatch is None or work_unit is None:
                raise RuntimeError("code Verification repository lineage unavailable")
            if (
                proposed.proposed_commit_identity != request.proposed_commit_identity
                or proposed.tree_identity != request.tree_identity
            ):
                raise RuntimeError("code Verification subject identity mismatch")
            contract = work_unit.completion_contract.change_contract
            if contract is None:
                raise RuntimeError("PWU has no admitted Code Change Contract")
            if (
                contract.source_baseline_id != source.id
                or contract.source_revision != source.repository_revision
                or contract.repository_identity != source.repository_identity
            ):
                raise RuntimeError("Code Change Contract lineage is incoherent")
            obligation = next(
                (
                    item
                    for item in contract.verification_obligations
                    if item.identity == request.obligation
                ),
                None,
            )
            if obligation is None:
                raise RuntimeError("requested check is not present in the admitted contract")
            if (request.semantic_fact_obligations
                    != work_unit.completion_contract.semantic_fact_obligations):
                raise RuntimeError("Code semantic obligations differ from admitted contract")
            target = obligation.target
            result, metadata = self._evaluate(
                repository=dispatch.workspace.repository_path,
                source_revision=source.repository_revision,
                proposed_revision=request.proposed_commit_identity,
                contract=contract,
                obligation=obligation,
            )
            if (obligation.kind is CodeVerificationKind.PATH_SCOPE
                    and result is VerificationResultValue.PASS):
                semantic_checks = verify_static_html_semantic_facts(
                    dispatch.workspace.repository_path,
                    request.proposed_commit_identity,
                    contract,
                    work_unit.completion_contract.semantic_fact_obligations,
                    admitted_facts=admitted_facts,
                    plan_repair=self.plan_repair,
                )
                if semantic_checks:
                    metadata["static_html_semantic_checks"] = semantic_checks
                    pending = tuple(check["fact_id"] for check in semantic_checks
                        if check["passed"] is None)
                    metadata["semantic_fact_owner_pending"] = pending
                    from spg.application.decision_context import MANAGED_WEB_SURFACE
                    managed_lineage = (work_unit.completion_contract.task_contract is not None
                        and work_unit.completion_contract.task_contract.decision_context is not None
                        and work_unit.completion_contract.task_contract.decision_context.surface
                        == MANAGED_WEB_SURFACE)
                    if (any(check["passed"] is False for check in semantic_checks)
                            or pending and not (managed_lineage
                                and request.protected_context_obligations
                                and self.context_verifier is not None)):
                        result = VerificationResultValue.FAIL
            if (obligation.kind is CodeVerificationKind.PATH_SCOPE
                    and result is VerificationResultValue.PASS
                    and request.protected_context_obligations and self.context_verifier is not None
                    and self.context_verifier.supports(contract)):
                checks = self.context_verifier.verify(
                    request, work_unit.completion_contract.task_contract, contract,
                    dispatch.workspace.repository_path, source.repository_revision)
                metadata["protected_context_checks"] = checks
                if any(item["coverage"] != "COVERED"
                       and item.get("verification_stage") != "DOWNSTREAM_ASSURANCE"
                       for item in checks):
                    result = VerificationResultValue.FAIL

        except Exception as error:
            result = VerificationResultValue.UNKNOWN
            metadata = {
                "mode": "contract-driven-code-verification",
                "target": target,
                "failure_type": type(error).__name__,
            }
            if isinstance(error, ValueError) and str(error).startswith("PROTECTED_CONTEXT_"):
                metadata["failure_code"] = str(error)
        metadata["semantic_fact_ids"] = [
            str(item.fact_id) for item in request.semantic_fact_obligations
        ]
        return VerificationCapabilityResult(
            result=result,
            evidence=VerificationEvidence(
                obligation=request.obligation,
                subject_commit_identity=request.proposed_commit_identity,
                subject_tree_identity=request.tree_identity,
                expected="the exact admitted typed code Verification obligation passes",
                observed=result.value,
                metadata=metadata,
            ),
        )

    def _evaluate(
        self,
        *,
        repository: Path,
        source_revision: str,
        proposed_revision: str,
        contract: CodeChangeContract,
        obligation: CodeVerificationObligation,
    ) -> tuple[VerificationResultValue, dict[str, object]]:
        changes = _changed_paths(repository, source_revision, proposed_revision)
        base = {
            "mode": "contract-driven-code-verification",
            "kind": obligation.kind.value,
            "target": obligation.target,
        }
        if obligation.kind is CodeVerificationKind.PATH_SCOPE:
            unauthorized = tuple(path for path in changes if not contract.allows_path(path))
            expected_operations = {target.path: target.operation for target in contract.exact_targets}
            operation_mismatches = tuple(
                path
                for path, change_type in changes.items()
                if path in expected_operations
                and change_type
                is not (
                    ArtifactChangeType.ADDED
                    if expected_operations[path] is ChangeOperation.CREATE
                    else ArtifactChangeType.MODIFIED
                )
            )
            passed = bool(changes) and not unauthorized and not operation_mismatches
            return _value(passed), {
                **base,
                "changed_paths": tuple(changes),
                "unauthorized_paths": unauthorized,
                "operation_mismatches": operation_mismatches,
            }
        if obligation.kind is CodeVerificationKind.GIT_DIFF_CHECK:
            completed = _run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "diff",
                    "--check",
                    source_revision,
                    proposed_revision,
                    "--",
                ],
                timeout=self.timeout_seconds,
            )
            return _value(completed.returncode == 0), _process_metadata(base, completed)

        with _materialized_snapshot(repository, proposed_revision) as snapshot:
            if obligation.kind is CodeVerificationKind.PYTHON_COMPILE:
                targets = tuple(
                    path
                    for path, change_type in changes.items()
                    if path.endswith(".py")
                    and change_type is not ArtifactChangeType.DELETED
                    and contract.allows_path(path)
                )
                if not targets:
                    return VerificationResultValue.FAIL, {**base, "compiled_targets": ()}
                completed = _run(
                    [sys.executable, "-m", "py_compile", *targets],
                    cwd=snapshot,
                    env=_verification_environment(snapshot),
                    timeout=self.timeout_seconds,
                )
                return _value(completed.returncode == 0), {
                    **_process_metadata(base, completed),
                    "compiled_targets": targets,
                }
            if obligation.kind is CodeVerificationKind.PYTEST_TARGET:
                assert obligation.target is not None
                completed = _run(
                    [sys.executable, "-m", "pytest", "-q", obligation.target],
                    cwd=snapshot,
                    env=_verification_environment(snapshot),
                    timeout=self.timeout_seconds,
                )
                return _value(completed.returncode == 0), _process_metadata(base, completed)
            if obligation.kind is CodeVerificationKind.NODE_TEST_TARGET:
                assert obligation.target is not None
                started = perf_counter()
                completed = _run(
                    ["node", "--test", obligation.target],
                    cwd=snapshot,
                    env=_verification_environment(snapshot),
                    timeout=self.timeout_seconds,
                )
                return _value(completed.returncode == 0), {
                    **_process_metadata(base, completed),
                    "duration_ms": round((perf_counter() - started) * 1000),
                }
            if obligation.kind is CodeVerificationKind.IMPORT_CHECK:
                assert obligation.target is not None
                if not any(
                    contract.allows_path(path)
                    and (snapshot / path).is_file()
                    for path in python_module_paths(obligation.target)
                ):
                    return VerificationResultValue.FAIL, {
                        **base,
                        "module_inside_contract": False,
                    }
                completed = _run(
                    [sys.executable, "-c", f"import {obligation.target}"],
                    cwd=snapshot,
                    env=_verification_environment(snapshot),
                    timeout=self.timeout_seconds,
                )
                return _value(completed.returncode == 0), _process_metadata(base, completed)
        raise RuntimeError("unsupported typed code Verification obligation")


def _changed_paths(
    repository: Path,
    source_revision: str,
    proposed_revision: str,
) -> dict[str, ArtifactChangeType]:
    completed = _run(
        [
            "git",
            "-C",
            str(repository),
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            "--no-renames",
            source_revision,
            proposed_revision,
            "--",
        ],
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError("code Verification could not read the exact change manifest")
    result: dict[str, ArtifactChangeType] = {}
    for row in completed.stdout.decode("utf-8", errors="strict").splitlines():
        status, path = row.split("\t", 1)
        result[path] = {
            "A": ArtifactChangeType.ADDED,
            "M": ArtifactChangeType.MODIFIED,
            "D": ArtifactChangeType.DELETED,
        }[status[0]]
    return result


@contextmanager
def _materialized_snapshot(repository: Path, revision: str) -> Iterator[Path]:
    archive = _run(
        ["git", "-C", str(repository), "archive", "--format=tar", revision],
        timeout=30,
    )
    if archive.returncode != 0:
        raise RuntimeError("code Verification could not materialize the exact subject")
    with tempfile.TemporaryDirectory(prefix="spg-code-verification-") as directory:
        root = Path(directory)
        with tarfile.open(fileobj=BytesIO(archive.stdout), mode="r:") as bundle:
            for member in bundle.getmembers():
                member_path = Path(member.name)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise RuntimeError("proposed snapshot contains an unsafe archive path")
                if member.issym() or member.islnk():
                    raise RuntimeError("proposed snapshot links are unsupported by Verification Lite")
            bundle.extractall(root, filter="data")
        yield root


def _verification_environment(snapshot: Path) -> dict[str, str]:
    allowed = {
        key: value
        for key, value in os.environ.items()
        if key.upper()
        in {
            "PATH",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "HOME",
            "USERPROFILE",
            "LANG",
            "LC_ALL",
        }
    }
    python_path = os.pathsep.join(
        str(path) for path in (snapshot / "src", snapshot) if path.exists()
    )
    allowed.update(
        {
            "PYTHONPATH": python_path,
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return allowed


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float,
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=env,
            check=False,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        return subprocess.CompletedProcess(
            command,
            124,
            stdout=error.stdout or b"",
            stderr=error.stderr or b"",
        )


def _process_metadata(
    base: dict[str, object],
    completed: subprocess.CompletedProcess[bytes],
) -> dict[str, object]:
    output = (completed.stdout or b"") + b"\0" + (completed.stderr or b"")
    return {
        **base,
        "exit_code": completed.returncode,
        "output_fingerprint": sha256(output).hexdigest(),
        "stdout_bytes": len(completed.stdout or b""),
        "stderr_bytes": len(completed.stderr or b""),
    }


def _value(passed: bool) -> VerificationResultValue:
    return VerificationResultValue.PASS if passed else VerificationResultValue.FAIL
