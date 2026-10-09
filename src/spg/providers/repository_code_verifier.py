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


def _exact_protected_context_coverage(request: VerificationCapabilityRequest,
                                      checks) -> bool:
    """Reject missing, duplicate or substituted ECF coverage on this Candidate."""
    identity = ("context_class", "semantic_key", "source_ref", "source_revision",
                "authority", "content_digest", "package_fingerprint")
    expected = tuple(tuple(getattr(item, key) for key in identity)
                     for item in request.protected_context_obligations)
    observed = tuple(tuple(item.get(key) for key in identity) for item in checks)
    return (bool(expected) and len(set(expected)) == len(expected)
            and len(observed) == len(expected) and set(observed) == set(expected)
            and all(item.get("coverage") in {"COVERED", "PENDING_CANDIDATE_GATE", "PENDING_HUMAN_GATE", "CONTEXT_RETAINED"}
                    and (item.get("coverage") != "PENDING_CANDIDATE_GATE"
                         or item.get("evidence_method") == "EXACT_CANDIDATE_SEAL_REQUIRED")
                    and (item.get("coverage") != "PENDING_HUMAN_GATE"
                         or item.get("evidence_method") == "EXACT_HUMAN_AUTHORIZATION_REQUIRED")
                    and (item.get("coverage") != "CONTEXT_RETAINED"
                         or item.get("evidence_method") == "EXACT_RETAINED_AUTHORITATIVE_CONTEXT")
                    and item.get("candidate_revision") == request.proposed_commit_identity
                    and item.get("candidate_tree") == request.tree_identity
                    for item in checks))


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
        metadata = {"mode": "contract-driven-code-verification"}
        receipt_recorder = None
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
                admitted_revisions = {}
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
                        admitted_revisions[str(revision.id)] = revision
                gate_bindings = work_unit.completion_contract.fulfillment_bindings if work_unit else ()
                native_binding = None
                admitted_revision = None
                admitted_ir = None
                task_context = (None if work_unit is None or
                    work_unit.completion_contract.task_contract is None else
                    work_unit.completion_contract.task_contract.decision_context)
                if (not admitted_revisions and task_context is not None
                        and task_context.surface == "MANAGED_PRODUCT_WEB_UI"):
                    from uuid import UUID
                    if (run is None or task_context.work_id is None
                            or not run.intent_ref.startswith(f"work:{task_context.work_id}")):
                        raise ValueError("OBLIGATION_MANAGED_WORK_LINEAGE_MISSING")
                    revision = ProductStore(unit_of_work.session).current_work_reality_revision(
                        UUID(task_context.work_id))
                    if revision is not None:
                        admitted_revisions[str(revision.id)] = revision
                if admitted_revisions:
                    from spg.infrastructure.persistence.interaction_store import InteractionStore
                    if len(admitted_revisions) != 1:
                        raise ValueError("OBLIGATION_WORK_REVISION_AMBIGUOUS")
                    admitted_revision = next(iter(admitted_revisions.values()))
                    if task_context is not None and task_context.surface == "MANAGED_PRODUCT_WEB_UI":
                        from spg.domain.engineering_semantics import current_semantic_facts
                        expected_facts = tuple(semantic_fact_reference(
                            fact, work_revision_id=admitted_revision.id)
                            for fact in current_semantic_facts(
                                admitted_revision.engineering_semantic_facts))
                        if expected_facts != request.semantic_fact_obligations:
                            raise ValueError("OBLIGATION_ADMITTED_FACT_COVERAGE_MISMATCH")
                        task = work_unit.completion_contract.task_contract
                        if task is None or task.semantic_fact_references != expected_facts:
                            raise ValueError("OBLIGATION_TASK_FACT_COVERAGE_MISMATCH")
                    assessment = (None if admitted_revision.source_assessment_id is None else
                        InteractionStore(unit_of_work.session).assessment(
                            admitted_revision.source_assessment_id))
                    admitted_ir = None if assessment is None else assessment.semantic_ir
                if admitted_revision is not None and admitted_ir is not None:
                    from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
                    from spg.application.governed_obligations import validate_continuous_gates
                    active_contract = work_unit.completion_contract.change_contract
                    validate_continuous_gates(gate_bindings, admitted_revision,
                        admitted_ir, source_revision=source.repository_revision,
                        exact_target_paths=tuple(target.path for target in active_contract.exact_targets)
                        if active_contract is not None else tuple(
                            artifact.path for artifact in work_unit.completion_contract.artifact_contract))
                    if gate_bindings and proposed is not None:
                        native_binding = NativeExecutionStore(unit_of_work.session).attempt_binding(
                            proposed.attempt_id)
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
            from spg.providers.verification_receipts import VerificationCandidateReceipts
            receipt_recorder = VerificationCandidateReceipts(request, database=self.database,
                work_id=None if admitted_revision is None else admitted_revision.work_id,
                work_revision_id=None if admitted_revision is None else admitted_revision.id,
                pwu_id=work_unit.id, attempt_id=proposed.attempt_id)
            plan_repair = (None if self.context_verifier is None else StaticHTMLPlanRepair(
                self.context_verifier.runtime_factory, receipt_recorder=receipt_recorder))
            result, metadata = self._evaluate(
                repository=dispatch.workspace.repository_path,
                source_revision=source.repository_revision,
                proposed_revision=request.proposed_commit_identity,
                contract=contract,
                obligation=obligation,
            )
            if obligation.kind is CodeVerificationKind.PATH_SCOPE and gate_bindings:
                from spg.application.governed_obligations import canonical_fingerprint
                from spg.domain.governed_obligation import fulfillment_source_ref
                metadata["fulfillment_binding_results"] = tuple({
                    "source_ref": fulfillment_source_ref(binding),
                    "binding_fingerprint": canonical_fingerprint(binding.model_dump(mode="json")),
                    "owner": binding.owner.value, "phase": binding.phase.value,
                    "evidence_method": binding.evidence_method,
                    "disposition": "NOT_EVALUATED_PRIOR_GATE", "current_stage_satisfied": False,
                    "candidate_revision": request.proposed_commit_identity, "candidate_tree": request.tree_identity}
                    for binding in gate_bindings)
            if (obligation.kind is CodeVerificationKind.PATH_SCOPE
                    and result is VerificationResultValue.PASS):
                from spg.providers.managed_context_fulfillment import verify_fulfillment_fact_routes
                semantic_checks = verify_fulfillment_fact_routes(
                    repository=dispatch.workspace.repository_path, request=request, contract=contract,
                    references=work_unit.completion_contract.semantic_fact_obligations,
                    admitted_facts=admitted_facts, revision=admitted_revision, ir=admitted_ir,
                    baseline=source, bindings=gate_bindings, plan_repair=plan_repair)
                if gate_bindings:
                    from spg.application.governed_obligations import evaluate_continuous_gates
                    semantic_checks = evaluate_continuous_gates(
                        semantic_checks, gate_bindings, native_binding,
                        source_revision=contract.source_revision)
                if admitted_facts:
                    from spg.application.governed_obligations import evaluate_candidate_handoffs
                    semantic_checks = evaluate_candidate_handoffs(
                        semantic_checks,
                        references=request.semantic_fact_obligations,
                        admitted_facts=admitted_facts, ir=admitted_ir,
                        source_revision=contract.source_revision,
                        exact_target_paths=tuple(target.path for target in contract.exact_targets),
                        fulfillment_bindings=gate_bindings)
                if gate_bindings:
                    from spg.application.governed_obligations import evaluate_constraint_routes
                    semantic_checks = (*semantic_checks, *evaluate_constraint_routes(
                        gate_bindings, native_binding,
                        source_revision=contract.source_revision,
                        path_scope_passed=result is VerificationResultValue.PASS,
                        exact_target_paths=tuple(
                            target.path for target in contract.exact_targets)))
                if semantic_checks:
                    metadata["static_html_semantic_checks"] = semantic_checks
                    if any(check["passed"] is not True for check in semantic_checks):
                        result = VerificationResultValue.FAIL
            if (obligation.kind is CodeVerificationKind.PATH_SCOPE
                    and result is VerificationResultValue.PASS
                    and request.protected_context_obligations):
                if self.context_verifier is None or not self.context_verifier.supports(contract):
                    metadata["protected_context_failure"] = "PROTECTED_CONTEXT_CONSUMER_UNAVAILABLE"
                    result = VerificationResultValue.FAIL
                else:
                    task = work_unit.completion_contract.task_contract
                    if (task is not None and task.decision_context is not None
                            and task.decision_context.surface == "MANAGED_PRODUCT_WEB_UI"):
                        if admitted_revision is None or admitted_ir is None:
                            raise ValueError("OBLIGATION_MANAGED_SOURCE_BASIS_MISSING")
                        from spg.application.decision_context import assert_task_context_fresh
                        from spg.providers.managed_context_fulfillment import verify_managed_context
                        assert_task_context_fresh(self.database, task)
                        checks = verify_managed_context(
                            request=request, task=task, contract=contract,
                            repository=dispatch.workspace.repository_path,
                            baseline=source.repository_revision,
                            revision=admitted_revision, ir=admitted_ir,
                            semantic_checks=metadata.get("static_html_semantic_checks", ()),
                            static_verifier=self.context_verifier,
                            fulfillment_bindings=gate_bindings,
                            receipt_recorder=receipt_recorder, native_record=native_binding)
                    else:
                        checks = self.context_verifier.verify(
                            request, task, contract,
                            dispatch.workspace.repository_path, source.repository_revision,
                            receipt_recorder=receipt_recorder)
                    metadata["protected_context_checks"] = checks
                    if not _exact_protected_context_coverage(request, checks):
                        metadata["protected_context_failure"] = "PROTECTED_CONTEXT_COVERAGE_INCOMPLETE"
                        result = VerificationResultValue.FAIL

            if (obligation.kind is CodeVerificationKind.PATH_SCOPE and result is VerificationResultValue.PASS
                    and any(binding.projection_inventory_fingerprint for binding in gate_bindings)):
                from spg.providers.managed_context_fulfillment import verify_binding_inventory
                outcomes, derived_checks = verify_binding_inventory(request=request,
                    task=work_unit.completion_contract.task_contract, contract=contract,
                    repository=dispatch.workspace.repository_path, baseline=source.repository_revision,
                    revision=admitted_revision, ir=admitted_ir, bindings=gate_bindings,
                    semantic_checks=metadata.get("static_html_semantic_checks", ()),
                    protected_checks=metadata.get("protected_context_checks", ()),
                    static_verifier=self.context_verifier, receipt_recorder=receipt_recorder,
                    native_record=native_binding)
                metadata["fulfillment_binding_results"] = outcomes
                metadata["fulfillment_binding_checks"] = derived_checks
                if any(outcome["current_stage_satisfied"] is not True for outcome in outcomes):
                    result = VerificationResultValue.FAIL

        except Exception as error:
            result = VerificationResultValue.UNKNOWN
            metadata = {**metadata,
                "mode": "contract-driven-code-verification", "target": target,
                "failure_type": type(error).__name__}
            retained = getattr(error, "verification_metadata", None)
            if isinstance(retained, dict):
                metadata.update(retained)
            if isinstance(error, ValueError) and str(error).startswith((
                    "PROTECTED_CONTEXT_", "VERIFICATION_CANDIDATE_", "OBLIGATION_")):
                metadata["failure_code"] = str(error)
        if receipt_recorder is not None:
            metadata["verification_candidate_receipts"] = receipt_recorder.metadata()
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
