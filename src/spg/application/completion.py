"""S3-A exact Completion Evaluation and authoritative Produced transition."""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.preparation import completion_contract_fingerprint
from spg.domain.completion import (
    CompletionEvaluationOutcome,
    CompletionEvaluationRecord,
    CompletionEvaluationResult,
    CompletionObligationResult,
    CompletionObligationResultValue,
    CompletionObligationType,
    CompletionWorkProductLineage,
)
from spg.domain.execution import (
    ArtifactChangeType,
    ExecutionDispatchRecord,
    RepositoryObservationRecord,
    WorkProductReferenceRecord,
)
from spg.domain.runtime import (
    CompletionContract,
    ExecutionAttemptRecord,
    PlanRevisionRecord,
    ProductionRunRecord,
    RuntimeInvariantViolation,
    RuntimeRecordNotFound,
    SnapshotRecord,
    WorkUnitCondition,
    WorkUnitRecord,
)
from spg.infrastructure.git_observation import GitWorkspaceObserver
from spg.infrastructure.git_workspace import GitExactReality
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


COMPLETION_ACTOR = "spg-runtime:completion"


@dataclass(frozen=True, slots=True)
class _CompletionBasis:
    run: ProductionRunRecord
    plan: PlanRevisionRecord
    work_unit: WorkUnitRecord
    attempt: ExecutionAttemptRecord
    snapshot: SnapshotRecord
    dispatch: ExecutionDispatchRecord
    observation: RepositoryObservationRecord
    work_products: tuple[WorkProductReferenceRecord, ...]


class CompletionService:
    """Evaluate output obligations without performing Verification or Satisfaction."""

    def __init__(
        self,
        database: Database,
        observer: GitWorkspaceObserver | None = None,
        exact_reality: GitExactReality | None = None,
    ) -> None:
        self.database = database
        self.observer = observer or GitWorkspaceObserver()
        self.exact_reality = exact_reality or GitExactReality()

    def evaluate_observation(
        self,
        observation_id: UUID,
        *,
        expected_work_unit_version: int | None = None,
    ) -> CompletionEvaluationResult:
        """Evaluate one exact current-generation observation and append its fact."""

        basis = self._load_basis(observation_id)
        self._revalidate_observation(basis)
        obligation_results = self._evaluate_output_obligations(basis)
        outcome = (
            CompletionEvaluationOutcome.PRODUCED
            if all(
                item.result is CompletionObligationResultValue.PASS
                for item in obligation_results
            )
            else CompletionEvaluationOutcome.NOT_PRODUCED
        )
        lineage = tuple(
            CompletionWorkProductLineage(
                reference_id=item.id,
                artifact_path=item.artifact_path,
                change_type=item.change_type,
                source_fingerprint=item.source_fingerprint,
                observed_fingerprint=item.observed_fingerprint,
            )
            for item in sorted(
                basis.work_products,
                key=lambda record: (record.artifact_path, str(record.id)),
            )
        )
        work_product_set_fingerprint = _fingerprint(
            [item.model_dump(mode="json") for item in lineage]
        )
        contract_fingerprint = completion_contract_fingerprint(
            basis.work_unit.completion_contract
        )
        basis_fingerprint = _fingerprint(
            {
                "production_run_id": str(basis.run.id),
                "work_unit_id": str(basis.work_unit.id),
                "plan_revision_id": str(basis.plan.id),
                "source_baseline_id": str(basis.snapshot.id),
                "attempt_id": str(basis.attempt.id),
                "generation": basis.attempt.generation,
                "completion_contract_fingerprint": contract_fingerprint,
                "repository_observation_id": str(basis.observation.id),
                "repository_observation_fingerprint": (
                    basis.observation.observation_fingerprint
                ),
                "work_product_set_fingerprint": work_product_set_fingerprint,
            }
        )
        evaluation_id = uuid5(
            NAMESPACE_URL,
            f"spg:completion-evaluation:{basis_fingerprint}",
        )
        timestamp = datetime.now(UTC)

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            current = self._required_basis(store, observation_id)
            self._require_same_basis(basis, current)
            existing = store.completion_evaluation_by_basis(basis_fingerprint)
            if existing is not None:
                return CompletionEvaluationResult(
                    evaluation=existing,
                    work_unit=current.work_unit,
                )

            store.insert_completion_evaluation(
                {
                    "id": evaluation_id,
                    "production_run_id": current.run.id,
                    "work_unit_id": current.work_unit.id,
                    "plan_revision_id": current.plan.id,
                    "source_baseline_id": current.snapshot.id,
                    "attempt_id": current.attempt.id,
                    "generation": current.attempt.generation,
                    "completion_contract_fingerprint": contract_fingerprint,
                    "repository_observation_id": current.observation.id,
                    "repository_observation_fingerprint": (
                        current.observation.observation_fingerprint
                    ),
                    "work_product_lineage": [
                        item.model_dump(mode="json") for item in lineage
                    ],
                    "work_product_set_fingerprint": work_product_set_fingerprint,
                    "basis_fingerprint": basis_fingerprint,
                    "outcome": outcome.value,
                    "obligation_results": [
                        item.model_dump(mode="json") for item in obligation_results
                    ],
                    "created_at": timestamp,
                }
            )
            self._append_history(
                store,
                entity_type="COMPLETION_EVALUATION",
                entity_id=evaluation_id,
                from_condition=None,
                to_condition=outcome.value,
                reason="OUTPUT_OBLIGATIONS_EVALUATED",
                correlation=current.attempt.id,
                timestamp=timestamp,
            )
            if outcome is CompletionEvaluationOutcome.PRODUCED:
                expected_version = (
                    current.work_unit.version
                    if expected_work_unit_version is None
                    else expected_work_unit_version
                )
                store.mark_work_unit_produced(
                    current.work_unit.id,
                    expected_version,
                )
                self._append_history(
                    store,
                    entity_type="PRODUCTION_WORK_UNIT",
                    entity_id=current.work_unit.id,
                    from_condition=WorkUnitCondition.PROPOSED.value,
                    to_condition=WorkUnitCondition.PRODUCED.value,
                    reason="COMPLETION_OUTPUT_OBLIGATIONS_SATISFIED",
                    correlation=evaluation_id,
                    timestamp=timestamp,
                )

            evaluation = store.completion_evaluation_by_basis(basis_fingerprint)
            work_unit = store.work_unit(current.work_unit.id)
            if evaluation is None or work_unit is None:
                raise RuntimeInvariantViolation(
                    "Completion Evaluation transaction did not construct its result"
                )
            unit_of_work.commit()
            return CompletionEvaluationResult(
                evaluation=evaluation,
                work_unit=work_unit,
            )

    def _load_basis(self, observation_id: UUID) -> _CompletionBasis:
        with self.database.unit_of_work() as unit_of_work:
            return self._required_basis(RuntimeStore(unit_of_work.session), observation_id)

    @staticmethod
    def _required_basis(
        store: RuntimeStore,
        observation_id: UUID,
    ) -> _CompletionBasis:
        observation = store.repository_observation_by_id(observation_id)
        if observation is None:
            raise RuntimeRecordNotFound(
                f"Repository Observation not found: {observation_id}"
            )
        dispatch = store.execution_dispatch(observation.dispatch_id)
        attempt = store.attempt(observation.attempt_id)
        if dispatch is None or attempt is None:
            raise RuntimeInvariantViolation(
                "Completion Evaluation dispatch/Attempt lineage is incomplete"
            )
        work_unit = store.work_unit(attempt.work_unit_id)
        if work_unit is None:
            raise RuntimeInvariantViolation(
                "Completion Evaluation PWU lineage is incomplete"
            )
        run = store.run(work_unit.production_run_id)
        plan = store.plan_revision(work_unit.plan_revision_id)
        snapshot = store.snapshot(work_unit.source_baseline_id)
        package = store.context_package(dispatch.context_package_id)
        if any(item is None for item in (run, plan, snapshot, package)):
            raise RuntimeInvariantViolation(
                "Completion Evaluation Run/Plan/Baseline/Context lineage is incomplete"
            )
        work_products = store.work_product_references(observation.id)
        if (
            observation.attempt_id != attempt.id
            or observation.generation != attempt.generation
            or observation.source_baseline_id != attempt.source_baseline_id
            or dispatch.attempt_id != attempt.id
            or dispatch.generation != attempt.generation
            or dispatch.source_baseline_id != snapshot.id
            or attempt.work_unit_id != work_unit.id
            or attempt.plan_revision_id != plan.id
            or attempt.source_baseline_id != snapshot.id
            or work_unit.plan_revision_id != plan.id
            or work_unit.source_baseline_id != snapshot.id
            or run.current_plan_revision_id != plan.id
            or run.source_baseline_id != snapshot.id
            or plan.production_run_id != run.id
            or plan.source_baseline_id != snapshot.id
            or observation.repository_identity != snapshot.repository_identity
            or observation.source_revision != snapshot.repository_revision
            or dispatch.workspace.repository_identity != snapshot.repository_identity
            or dispatch.workspace.source_revision != snapshot.repository_revision
            or package.completion_contract_fingerprint
            != completion_contract_fingerprint(work_unit.completion_contract)
        ):
            raise RuntimeInvariantViolation(
                "Completion Evaluation basis is not an exact lineage binding"
            )
        if attempt.generation != work_unit.current_execution_generation:
            raise RuntimeInvariantViolation(
                "stale Attempt generation has no current PWU Produced authority"
            )
        for reference in work_products:
            if (
                reference.production_run_id != run.id
                or reference.work_unit_id != work_unit.id
                or reference.plan_revision_id != plan.id
                or reference.attempt_id != attempt.id
                or reference.generation != attempt.generation
                or reference.source_baseline_id != snapshot.id
                or reference.repository_observation_id != observation.id
            ):
                raise RuntimeInvariantViolation(
                    "Work Product Reference set has inconsistent Completion lineage"
                )
        return _CompletionBasis(
            run=run,
            plan=plan,
            work_unit=work_unit,
            attempt=attempt,
            snapshot=snapshot,
            dispatch=dispatch,
            observation=observation,
            work_products=work_products,
        )

    def _revalidate_observation(self, basis: _CompletionBasis) -> None:
        reality = self.observer.observe(
            basis.dispatch.workspace,
            repository_ref=basis.snapshot.repository_ref,
            expected_authoritative_ref_revision=(
                basis.observation.authoritative_ref_revision
            ),
        )
        if (
            reality.observation_fingerprint
            != basis.observation.observation_fingerprint
            or reality.changes != basis.observation.changes
        ):
            raise RuntimeInvariantViolation(
                "Attempt workspace changed after the bound Repository Observation"
            )

    def _evaluate_output_obligations(
        self,
        basis: _CompletionBasis,
    ) -> tuple[CompletionObligationResult, ...]:
        contract = basis.work_unit.completion_contract
        changes = {
            change.repository_relative_path: change
            for change in basis.observation.changes
        }
        results: list[CompletionObligationResult] = []
        available_content: dict[str, bytes] = {}

        for raw_path in contract.required_outputs:
            path = _repository_path(raw_path)
            content = self._exact_artifact_content(basis, path, changes)
            if content is not None:
                available_content[path] = content
            results.append(
                _obligation(
                    CompletionObligationType.REQUIRED_ARTIFACT,
                    path,
                    "artifact exists in exact observed repository Reality",
                    "present" if content is not None else "absent",
                    content is not None,
                    "required artifact exists"
                    if content is not None
                    else "required artifact is absent",
                )
            )

        for raw_path in contract.required_changes:
            path = _repository_path(raw_path)
            changed = path in changes
            results.append(
                _obligation(
                    CompletionObligationType.REQUIRED_CHANGE,
                    path,
                    "path appears in the exact observed change manifest",
                    changes[path].change_type.value if changed else "UNCHANGED",
                    changed,
                    "required change was independently observed"
                    if changed
                    else "required change was not independently observed",
                )
            )

        marker_paths = tuple(
            dict.fromkeys(
                [
                    *(_repository_path(path) for path in contract.required_outputs),
                    *(
                        path
                        for path, change in changes.items()
                        if change.change_type is not ArtifactChangeType.DELETED
                    ),
                ]
            )
        )
        for marker in contract.required_markers:
            matches: list[str] = []
            for path in marker_paths:
                content = available_content.get(path)
                if content is None:
                    content = self._exact_artifact_content(basis, path, changes)
                    if content is not None:
                        available_content[path] = content
                if content is not None and marker.encode("utf-8") in content:
                    matches.append(path)
            results.append(
                _obligation(
                    CompletionObligationType.REQUIRED_MARKER,
                    marker,
                    "marker exists in an exact required/observed output artifact",
                    ", ".join(matches) if matches else "absent",
                    bool(matches),
                    "required marker found in exact observed content"
                    if matches
                    else "required marker is absent from exact observed content",
                )
            )

        changed_paths = tuple(changes)
        for raw_scope in contract.forbidden_changes:
            scope = _repository_path(raw_scope)
            matches = [
                path for path in changed_paths if _path_matches_scope(path, scope)
            ]
            results.append(
                _obligation(
                    CompletionObligationType.FORBIDDEN_CHANGE,
                    scope,
                    "no observed mutation in the forbidden path scope",
                    ", ".join(matches) if matches else "none",
                    not matches,
                    "no forbidden change observed"
                    if not matches
                    else "forbidden change was independently observed",
                )
            )

        for condition in contract.blocking_conditions:
            results.append(
                _obligation(
                    CompletionObligationType.BLOCKING_CONDITION,
                    condition,
                    "blocking output condition is absent or resolved",
                    "declared active",
                    False,
                    "declared blocking output condition prevents Produced",
                )
            )
        return tuple(results)

    def _exact_artifact_content(
        self,
        basis: _CompletionBasis,
        path: str,
        changes,
    ) -> bytes | None:
        change = changes.get(path)
        if change is not None and change.change_type is ArtifactChangeType.DELETED:
            return None
        if change is None:
            target = _safe_workspace_target(basis.dispatch.workspace.workspace_path, path)
            if not target.is_file():
                return None
            baseline_content, fingerprint = self.exact_reality.read_blob(
                basis.dispatch.workspace.repository_path,
                basis.dispatch.source_revision,
                path,
            )
            content = target.read_bytes()
            if (
                self.exact_reality.identify_blob_content(
                    basis.dispatch.workspace.workspace_path,
                    path,
                    baseline_content,
                )
                != fingerprint
                or self.exact_reality.identify_blob_content(
                    basis.dispatch.workspace.workspace_path,
                    path,
                    content,
                )
                != fingerprint
            ):
                raise RuntimeInvariantViolation(
                    f"workspace content no longer matches exact unchanged Reality: {path}"
                )
            return content

        target = _safe_workspace_target(basis.dispatch.workspace.workspace_path, path)
        if not target.is_file():
            return None
        content = target.read_bytes()
        if (
            self.exact_reality.identify_blob_content(
                basis.dispatch.workspace.workspace_path,
                path,
                content,
            )
            != change.observed_fingerprint
        ):
            raise RuntimeInvariantViolation(
                f"workspace content no longer matches Repository Observation: {path}"
            )
        return content

    @staticmethod
    def _require_same_basis(
        expected: _CompletionBasis,
        current: _CompletionBasis,
    ) -> None:
        if (
            expected.run != current.run
            or expected.plan != current.plan
            or expected.work_unit != current.work_unit
            or expected.attempt != current.attempt
            or expected.snapshot != current.snapshot
            or expected.dispatch != current.dispatch
            or expected.observation != current.observation
            or expected.work_products != current.work_products
        ):
            raise RuntimeInvariantViolation(
                "Completion Evaluation basis changed before persistence"
            )

    @staticmethod
    def _append_history(
        store: RuntimeStore,
        *,
        entity_type: str,
        entity_id: UUID,
        from_condition: str | None,
        to_condition: str,
        reason: str,
        correlation: UUID,
        timestamp: datetime,
    ) -> None:
        store.insert_transition(
            {
                "id": uuid4(),
                "entity_type": entity_type,
                "entity_identity": str(entity_id),
                "from_condition": from_condition,
                "to_condition": to_condition,
                "reason": reason,
                "actor_identity": COMPLETION_ACTOR,
                "correlation_identity": str(correlation),
                "created_at": timestamp,
            }
        )


def _repository_path(value: str) -> str:
    if "\\" in value:
        raise RuntimeInvariantViolation(
            "Completion Contract repository paths must use POSIX separators"
        )
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value in {"", "."}:
        raise RuntimeInvariantViolation(
            f"invalid Completion Contract repository path: {value}"
        )
    return str(path)


def _safe_workspace_target(workspace: Path, repository_relative_path: str) -> Path:
    root = workspace.resolve()
    target = (root / repository_relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as error:
        raise RuntimeInvariantViolation(
            "Completion artifact path escapes the Attempt workspace"
        ) from error
    return target


def _path_matches_scope(path: str, scope: str) -> bool:
    normalized = scope.rstrip("/")
    return path == normalized or path.startswith(f"{normalized}/")


def _fingerprint(value: object) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return sha256(canonical).hexdigest()


def _obligation(
    obligation_type: CompletionObligationType,
    subject: str,
    expected: str,
    observed: str,
    passed: bool,
    reason: str,
) -> CompletionObligationResult:
    return CompletionObligationResult(
        obligation_type=obligation_type,
        subject=subject,
        expected=expected,
        observed=observed,
        result=(
            CompletionObligationResultValue.PASS
            if passed
            else CompletionObligationResultValue.FAIL
        ),
        reason=reason,
    )
