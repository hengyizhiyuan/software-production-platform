"""Crash-resumable workspace hibernation and retention pin ownership."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update

from spg.domain.native_execution import (
    ExecutionRecoveryCaseRecord,
    NativeExecutionConflict,
    NativeExecutionNotFound,
    RecoveryClassification,
    WorkspaceCondition,
    canonical_digest,
)
from spg.domain.native_retention import (
    ResourcePinRecord,
    RetentionActionCondition,
    RetentionActionKind,
    RetentionActionRecord,
)
from spg.infrastructure.executor_runtime.local_storage import WorkspaceArchiveStore
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.native_execution_schema import (
    checkpoint_bundles,
    execution_allocations,
    execution_recovery_cases,
    execution_workspaces,
    native_attempt_bindings,
    native_candidate_vectors,
    native_resource_pins,
    native_retention_actions,
    native_workspace_tombstones,
    native_attempt_states, execution_evidence,
)
from spg.infrastructure.persistence.runtime_schema import (
    production_work_units, baseline_candidates, human_authorizations,
)
from spg.infrastructure.persistence.product_schema import work_runtime_bindings
from spg.infrastructure.persistence.delivery_schema import work_delivery_manifests, work_delivery_acceptances


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NativeRetentionService:
    """Keep hot deletion behind durable plans, verified bundles, and pin locks."""

    def __init__(
        self,
        database: Database,
        archive_store: WorkspaceArchiveStore,
        *,
        now=_utcnow,
    ) -> None:
        self.database = database
        self.archives = archive_store
        self._now = now

    def pin_workspace(
        self,
        workspace_id: UUID,
        *,
        owner_kind: str,
        owner_id: str,
        reason: str,
    ) -> ResourcePinRecord:
        now = self._now()
        with self.database.unit_of_work() as uow:
            self._workspace_row(uow.session, workspace_id, lock=True)
            existing = uow.session.execute(
                select(native_resource_pins).where(
                    native_resource_pins.c.resource_kind == "WORKSPACE",
                    native_resource_pins.c.resource_id == str(workspace_id),
                    native_resource_pins.c.owner_kind == owner_kind,
                    native_resource_pins.c.owner_id == owner_id,
                )
            ).mappings().one_or_none()
            if existing is not None:
                if existing["reason"] != reason:
                    raise NativeExecutionConflict("retention pin identity has different meaning")
                if not existing["active"]:
                    raise NativeExecutionConflict("released retention pin cannot be resurrected")
                return ResourcePinRecord.model_validate(dict(existing))
            record = ResourcePinRecord(
                id=uuid4(), resource_kind="WORKSPACE", resource_id=str(workspace_id),
                owner_kind=owner_kind, owner_id=owner_id, reason=reason,
                active=True, created_at=now,
            )
            uow.session.execute(
                insert(native_resource_pins).values(**record.model_dump(mode="json"))
            )
            uow.commit()
            return record

    def release_pin(self, pin_id: UUID) -> ResourcePinRecord:
        now = self._now()
        with self.database.unit_of_work() as uow:
            pin = uow.session.execute(
                select(native_resource_pins)
                .where(native_resource_pins.c.id == pin_id)
                .with_for_update()
            ).mappings().one_or_none()
            if pin is None:
                raise NativeExecutionNotFound(f"retention pin not found: {pin_id}")
            self._workspace_row(uow.session, UUID(pin["resource_id"]), lock=True)
            if pin["active"]:
                uow.session.execute(
                    update(native_resource_pins)
                    .where(native_resource_pins.c.id == pin_id)
                    .values(active=False, released_at=now)
                )
            uow.commit()
        return self.pin(pin_id)

    def pin(self, pin_id: UUID) -> ResourcePinRecord:
        with self.database.unit_of_work() as uow:
            row = uow.session.execute(
                select(native_resource_pins).where(native_resource_pins.c.id == pin_id)
            ).mappings().one_or_none()
            if row is None:
                raise NativeExecutionNotFound(f"retention pin not found: {pin_id}")
            return ResourcePinRecord.model_validate(dict(row))

    def eligibility(self, workspace_id: UUID, *,
                    hot_retention: timedelta = timedelta(days=30),
                    cold_retention: timedelta = timedelta(days=180)) -> dict:
        """Explain a reference-aware decision before any physical cleanup."""
        now = self._now()
        with self.database.unit_of_work() as uow:
            workspace = self._workspace_row(uow.session, workspace_id)
            reasons = self._blockers(uow.session, workspace)
            condition = workspace["condition"]
            age = now - workspace["updated_at"]
            if reasons:
                classification = "REFERENCED" if any("reference" in reason or "pin" in reason
                                                 for reason in reasons) else "ACTIVE"
            elif condition == WorkspaceCondition.HIBERNATED.value:
                classification = "ELIGIBLE_FOR_CLEANUP" if age >= cold_retention else "ARCHIVED"
            elif condition in {WorkspaceCondition.READY.value, WorkspaceCondition.SEALED.value}:
                classification = "ELIGIBLE_FOR_CLEANUP" if age >= hot_retention else "RETAINED_FOR_REVIEW"
            elif condition in {WorkspaceCondition.DELETED.value, WorkspaceCondition.RETIRED.value}:
                classification = "RELEASED"
            else:
                classification = "ACTIVE"
            return {"workspace_id": str(workspace_id), "classification": classification,
                    "condition": condition, "reasons": reasons,
                    "eligible_action": ("DELETE" if condition == WorkspaceCondition.HIBERNATED.value
                                        else "HIBERNATE") if classification == "ELIGIBLE_FOR_CLEANUP" else None,
                    "hot_retention_seconds": int(hot_retention.total_seconds()),
                    "cold_retention_seconds": int(cold_retention.total_seconds())}

    def cleanup_expired(self, *, hot_retention: timedelta = timedelta(days=30),
                        cold_retention: timedelta = timedelta(days=180),
                        limit: int = 100) -> list[dict]:
        if limit < 1 or limit > 1000:
            raise ValueError("Cleanup limit must be between 1 and 1000")
        with self.database.unit_of_work() as uow:
            ids = uow.session.execute(select(execution_workspaces.c.id).where(
                execution_workspaces.c.condition.in_((WorkspaceCondition.READY.value,
                    WorkspaceCondition.SEALED.value, WorkspaceCondition.HIBERNATED.value)),
            ).order_by(execution_workspaces.c.updated_at).limit(limit)).scalars().all()
        results = []
        for workspace_id in ids:
            decision = self.eligibility(workspace_id, hot_retention=hot_retention,
                                        cold_retention=cold_retention)
            if decision["eligible_action"] is None:
                results.append(decision)
                continue
            try:
                action = (self.retire(workspace_id, minimum_hibernated=cold_retention)
                          if decision["eligible_action"] == "DELETE" else
                          self.hibernate(workspace_id, minimum_idle=hot_retention))
            except (NativeExecutionConflict, OSError) as error:
                results.append({**decision, "cleanup_result": "DEFERRED",
                                "reason": str(error)})
            else:
                results.append({**decision, "cleanup_result": "COMPLETED",
                                "action_id": str(action.id),
                                "audit": "native_retention_actions"})
        return results

    def hibernate(
        self,
        workspace_id: UUID,
        *,
        minimum_idle: timedelta = timedelta(days=30),
    ) -> RetentionActionRecord:
        action = self._plan(workspace_id, RetentionActionKind.HIBERNATE, minimum_idle)
        if action.condition is RetentionActionCondition.COMPLETED:
            return action
        workspace_path = self._workspace_path(workspace_id)
        if action.condition is RetentionActionCondition.PLANNED:
            digest, bundle_path = self.archives.archive(workspace_path)
            self._advance_action(
                action.id,
                RetentionActionCondition.BUNDLE_VERIFIED,
                bundle_digest=digest,
                bundle_path=str(bundle_path),
            )
            action = self.action(action.id)
        if action.condition is RetentionActionCondition.BUNDLE_VERIFIED:
            if action.bundle_digest is None or action.bundle_path is None:
                raise NativeExecutionConflict("verified retention action has no bundle")
            self.archives.verify(action.bundle_digest, Path(action.bundle_path))
            self._recheck_before_physical_change(workspace_id)
            retiring = workspace_path.with_name(
                f".{workspace_path.name}.retiring-{action.id}"
            )
            if workspace_path.is_symlink():
                raise NativeExecutionConflict("workspace path became a symbolic link")
            if workspace_path.exists():
                workspace_path.rename(retiring)
            if retiring.exists():
                if retiring.is_symlink():
                    if not workspace_path.exists():
                        retiring.rename(workspace_path)
                    raise NativeExecutionConflict("retiring workspace is a symbolic link")
                shutil.rmtree(retiring)
            self._advance_action(
                action.id,
                RetentionActionCondition.PHYSICAL_COMPLETE,
                physical_receipt={"hot_materialization_removed": True},
            )
            action = self.action(action.id)
        if action.condition is RetentionActionCondition.PHYSICAL_COMPLETE:
            now = self._now()
            with self.database.unit_of_work() as uow:
                workspace = self._workspace_row(uow.session, workspace_id, lock=True)
                self._assert_no_blockers(uow.session, workspace)
                uow.session.execute(
                    update(execution_workspaces)
                    .where(
                        execution_workspaces.c.id == workspace_id,
                        execution_workspaces.c.version == workspace["version"],
                    )
                    .values(
                        condition=WorkspaceCondition.HIBERNATED.value,
                        version=workspace["version"] + 1,
                        updated_at=now,
                    )
                )
                uow.session.execute(
                    update(native_retention_actions)
                    .where(native_retention_actions.c.id == action.id)
                    .values(
                        condition=RetentionActionCondition.COMPLETED.value,
                        updated_at=now,
                        completed_at=now,
                    )
                )
                uow.commit()
        return self.action(action.id)

    def restore(self, workspace_id: UUID) -> None:
        with self.database.unit_of_work() as uow:
            workspace = self._workspace_row(uow.session, workspace_id, lock=True)
            if workspace["condition"] != WorkspaceCondition.HIBERNATED.value:
                raise NativeExecutionConflict("only a hibernated workspace can be restored")
            action = uow.session.execute(
                select(native_retention_actions)
                .where(
                    native_retention_actions.c.workspace_id == workspace_id,
                    native_retention_actions.c.action_kind == RetentionActionKind.HIBERNATE.value,
                    native_retention_actions.c.condition == RetentionActionCondition.COMPLETED.value,
                )
                .order_by(native_retention_actions.c.completed_at.desc())
            ).mappings().first()
            if action is None or action["bundle_digest"] is None:
                raise NativeExecutionConflict("hibernated workspace has no verified bundle")
            path = Path(workspace["materialization_path"])
            digest = action["bundle_digest"]
            version = workspace["version"]
        self.archives.restore(digest, path)
        now = self._now()
        with self.database.unit_of_work() as uow:
            result = uow.session.execute(
                update(execution_workspaces)
                .where(
                    execution_workspaces.c.id == workspace_id,
                    execution_workspaces.c.version == version,
                    execution_workspaces.c.condition == WorkspaceCondition.HIBERNATED.value,
                )
                .values(
                    condition=WorkspaceCondition.READY.value,
                    version=version + 1,
                    updated_at=now,
                )
            )
            if result.rowcount != 1:
                shutil.rmtree(path, ignore_errors=True)
                raise NativeExecutionConflict("workspace changed during restore")
            uow.commit()

    def recover_lost_workspace(
        self,
        lost_workspace_id: UUID,
        successor_workspace_id: UUID,
    ) -> ExecutionRecoveryCaseRecord:
        """Restore exact pinned content into a distinct successor or fail explicitly."""

        if lost_workspace_id == successor_workspace_id:
            raise NativeExecutionConflict("lost workspace recovery requires a successor")
        now = self._now()
        with self.database.unit_of_work() as uow:
            lost = self._workspace_row(uow.session, lost_workspace_id, lock=True)
            successor = self._workspace_row(
                uow.session, successor_workspace_id, lock=True
            )
            if lost["pwu_id"] != successor["pwu_id"]:
                raise NativeExecutionConflict("successor workspace belongs to another PWU")
            lost_path = Path(lost["materialization_path"])
            successor_path = Path(successor["materialization_path"])
            if lost_path.exists():
                raise NativeExecutionConflict("workspace is present; lost recovery is invalid")
            if successor_path.exists():
                raise NativeExecutionConflict(
                    "successor workspace must be empty before exact recovery"
                )
            action = uow.session.execute(
                select(native_retention_actions)
                .where(
                    native_retention_actions.c.workspace_id == lost_workspace_id,
                    native_retention_actions.c.action_kind
                    == RetentionActionKind.HIBERNATE.value,
                    native_retention_actions.c.condition
                    == RetentionActionCondition.COMPLETED.value,
                )
                .order_by(native_retention_actions.c.completed_at.desc())
            ).mappings().first()
            checkpoint = uow.session.execute(
                select(checkpoint_bundles.c.id)
                .where(
                    checkpoint_bundles.c.attempt_id == lost["attempt_id"],
                    checkpoint_bundles.c.condition == "COMMITTED",
                )
                .order_by(checkpoint_bundles.c.step_sequence.desc())
            ).first()
            binding = uow.session.execute(
                select(native_attempt_bindings.c.binding_payload).where(
                    native_attempt_bindings.c.attempt_id == successor["attempt_id"]
                )
            ).scalar_one()
            residual = tuple(binding.get("obligation_references", ()))
            lost_version = lost["version"]
            successor_version = successor["version"]
            recovery = ExecutionRecoveryCaseRecord(
                id=uuid4(), pwu_id=lost["pwu_id"],
                attempt_id=successor["attempt_id"],
                classification=(
                    RecoveryClassification.COMPLETE
                    if action is not None
                    and action["bundle_digest"]
                    and action["bundle_path"]
                    else RecoveryClassification.LOST
                ),
                basis_checkpoint_id=checkpoint.id if checkpoint else None,
                observed_reality={
                    "lost_workspace_id": str(lost_workspace_id),
                    "lost_materialization_absent": True,
                    "successor_workspace_id": str(successor_workspace_id),
                    "verified_bundle_available": bool(
                        action is not None
                        and action["bundle_digest"]
                        and action["bundle_path"]
                    ),
                },
                residual_obligations=residual,
                effect_uncertainty=False,
                resolution=(
                    "exact verified workspace bundle restored into successor"
                    if action is not None
                    and action["bundle_digest"]
                    and action["bundle_path"]
                    else "RECOVERY_PROMISE_FAILED: no complete verified workspace bundle"
                ),
                created_at=now,
                resolved_at=now,
            )
            if action is None or not action["bundle_digest"] or not action["bundle_path"]:
                uow.session.execute(
                    update(execution_workspaces)
                    .where(
                        execution_workspaces.c.id.in_(
                            (lost_workspace_id, successor_workspace_id)
                        )
                    )
                    .values(condition=WorkspaceCondition.QUARANTINED.value, updated_at=now)
                )
                uow.session.execute(
                    insert(execution_recovery_cases).values(
                        **recovery.model_dump(mode="json")
                    )
                )
                uow.commit()
                return recovery
            digest = action["bundle_digest"]
            bundle_path = Path(action["bundle_path"])

        try:
            self.archives.verify(digest, bundle_path)
            self.archives.restore(digest, successor_path)
        except Exception as error:
            failed = recovery.model_copy(update={
                "classification": RecoveryClassification.LOST,
                "resolution": (
                    "RECOVERY_PROMISE_FAILED: verified workspace bundle could not be "
                    f"restored ({type(error).__name__})"
                ),
            })
            with self.database.unit_of_work() as uow:
                uow.session.execute(
                    update(execution_workspaces)
                    .where(
                        execution_workspaces.c.id.in_(
                            (lost_workspace_id, successor_workspace_id)
                        )
                    )
                    .values(condition=WorkspaceCondition.QUARANTINED.value, updated_at=now)
                )
                uow.session.execute(
                    insert(execution_recovery_cases).values(
                        **failed.model_dump(mode="json")
                    )
                )
                uow.commit()
            shutil.rmtree(successor_path, ignore_errors=True)
            return failed

        with self.database.unit_of_work() as uow:
            lost_result = uow.session.execute(
                update(execution_workspaces)
                .where(
                    execution_workspaces.c.id == lost_workspace_id,
                    execution_workspaces.c.version == lost_version,
                )
                .values(
                    condition=WorkspaceCondition.QUARANTINED.value,
                    version=lost_version + 1,
                    updated_at=now,
                )
            )
            successor_result = uow.session.execute(
                update(execution_workspaces)
                .where(
                    execution_workspaces.c.id == successor_workspace_id,
                    execution_workspaces.c.version == successor_version,
                )
                .values(
                    condition=WorkspaceCondition.READY.value,
                    version=successor_version + 1,
                    updated_at=now,
                )
            )
            if lost_result.rowcount != 1 or successor_result.rowcount != 1:
                shutil.rmtree(successor_path, ignore_errors=True)
                raise NativeExecutionConflict("workspace changed during lost recovery")
            uow.session.execute(
                insert(execution_recovery_cases).values(
                    **recovery.model_dump(mode="json")
                )
            )
            uow.commit()
        return recovery

    def retire(
        self,
        workspace_id: UUID,
        *,
        minimum_hibernated: timedelta = timedelta(days=180),
    ) -> RetentionActionRecord:
        """Tombstone a cold workspace while retaining its last recovery bundle."""

        now = self._now()
        with self.database.unit_of_work() as uow:
            workspace = self._workspace_row(uow.session, workspace_id, lock=True)
            existing = uow.session.execute(
                select(native_workspace_tombstones).where(
                    native_workspace_tombstones.c.workspace_id == workspace_id
                )
            ).mappings().one_or_none()
            if existing is not None:
                action = uow.session.execute(
                    select(native_retention_actions).where(
                        native_retention_actions.c.id == existing["retention_action_id"]
                    )
                ).mappings().one()
                return RetentionActionRecord.model_validate(dict(action))
            if workspace["condition"] != WorkspaceCondition.HIBERNATED.value:
                raise NativeExecutionConflict("only a hibernated workspace can be retired")
            if now - workspace["updated_at"] < minimum_hibernated:
                raise NativeExecutionConflict("cold-retention interval has not elapsed")
            self._assert_no_blockers(uow.session, workspace)
            hibernation = uow.session.execute(
                select(native_retention_actions).where(
                    native_retention_actions.c.workspace_id == workspace_id,
                    native_retention_actions.c.action_kind == RetentionActionKind.HIBERNATE.value,
                    native_retention_actions.c.condition == RetentionActionCondition.COMPLETED.value,
                ).order_by(native_retention_actions.c.completed_at.desc())
            ).mappings().first()
            if hibernation is None or hibernation["bundle_digest"] is None:
                raise NativeExecutionConflict("retirement cannot erase the only recovery bundle")
            self.archives.verify(
                hibernation["bundle_digest"], Path(hibernation["bundle_path"])
            )
            action_id = uuid4()
            action_key = canonical_digest(
                {
                    "workspace_id": str(workspace_id),
                    "kind": RetentionActionKind.DELETE.value,
                    "manifest_digest": workspace["manifest_digest"],
                    "workspace_version": workspace["version"],
                }
            )
            action = RetentionActionRecord(
                id=action_id, workspace_id=workspace_id, action_key=action_key,
                action_kind=RetentionActionKind.DELETE,
                condition=RetentionActionCondition.COMPLETED,
                bundle_digest=hibernation["bundle_digest"],
                bundle_path=hibernation["bundle_path"],
                physical_receipt={
                    "hot_materialization_absent": True,
                    "last_recovery_bundle_retained": True,
                },
                created_at=now, updated_at=now, completed_at=now,
            )
            uow.session.execute(
                insert(native_retention_actions).values(**action.model_dump(mode="json"))
            )
            uow.session.execute(
                insert(native_workspace_tombstones).values(
                    workspace_id=workspace_id,
                    pwu_id=workspace["pwu_id"],
                    attempt_id=workspace["attempt_id"],
                    manifest_digest=workspace["manifest_digest"],
                    last_bundle_digest=hibernation["bundle_digest"],
                    retention_action_id=action_id,
                    deleted_at=now,
                )
            )
            result = uow.session.execute(
                update(execution_workspaces)
                .where(
                    execution_workspaces.c.id == workspace_id,
                    execution_workspaces.c.version == workspace["version"],
                )
                .values(
                    condition=WorkspaceCondition.DELETED.value,
                    version=workspace["version"] + 1,
                    updated_at=now,
                )
            )
            if result.rowcount != 1:
                raise NativeExecutionConflict("workspace retirement raced")
            uow.commit()
            return action

    def action(self, action_id: UUID) -> RetentionActionRecord:
        with self.database.unit_of_work() as uow:
            row = uow.session.execute(
                select(native_retention_actions).where(native_retention_actions.c.id == action_id)
            ).mappings().one_or_none()
            if row is None:
                raise NativeExecutionNotFound(f"retention action not found: {action_id}")
            return RetentionActionRecord.model_validate(dict(row))

    def _plan(
        self, workspace_id: UUID, kind: RetentionActionKind, minimum_idle: timedelta
    ) -> RetentionActionRecord:
        now = self._now()
        with self.database.unit_of_work() as uow:
            workspace = self._workspace_row(uow.session, workspace_id, lock=True)
            if workspace["condition"] == WorkspaceCondition.HIBERNATED.value:
                existing = uow.session.execute(
                    select(native_retention_actions).where(
                        native_retention_actions.c.workspace_id == workspace_id,
                        native_retention_actions.c.action_kind == kind.value,
                        native_retention_actions.c.condition == RetentionActionCondition.COMPLETED.value,
                    )
                ).mappings().first()
                if existing is not None:
                    return RetentionActionRecord.model_validate(dict(existing))
            if workspace["condition"] not in {
                WorkspaceCondition.READY.value,
                WorkspaceCondition.SEALED.value,
            }:
                raise NativeExecutionConflict("workspace condition is not hibernation eligible")
            if now - workspace["updated_at"] < minimum_idle:
                raise NativeExecutionConflict("workspace hot-retention interval has not elapsed")
            self._assert_no_blockers(uow.session, workspace)
            latest_checkpoint = uow.session.execute(
                select(checkpoint_bundles.c.id).where(
                    checkpoint_bundles.c.attempt_id == workspace["attempt_id"],
                    checkpoint_bundles.c.condition == "COMMITTED",
                ).order_by(checkpoint_bundles.c.step_sequence.desc())
            ).first()
            if latest_checkpoint is None:
                raise NativeExecutionConflict("workspace has no committed recovery bundle")
            action_key = canonical_digest(
                {
                    "workspace_id": str(workspace_id),
                    "kind": kind.value,
                    "manifest_digest": workspace["manifest_digest"],
                    "workspace_version": workspace["version"],
                }
            )
            existing = uow.session.execute(
                select(native_retention_actions).where(
                    native_retention_actions.c.action_key == action_key
                )
            ).mappings().one_or_none()
            if existing is not None:
                return RetentionActionRecord.model_validate(dict(existing))
            record = RetentionActionRecord(
                id=uuid4(), workspace_id=workspace_id, action_key=action_key,
                action_kind=kind, condition=RetentionActionCondition.PLANNED,
                created_at=now, updated_at=now,
            )
            uow.session.execute(
                insert(native_retention_actions).values(**record.model_dump(mode="json"))
            )
            uow.commit()
            return record

    def _recheck_before_physical_change(self, workspace_id: UUID) -> None:
        with self.database.unit_of_work() as uow:
            workspace = self._workspace_row(uow.session, workspace_id, lock=True)
            self._assert_no_blockers(uow.session, workspace)

    def _assert_no_blockers(self, session, workspace) -> None:
        reasons = self._blockers(session, workspace)
        if reasons:
            raise NativeExecutionConflict(reasons[0])

    @staticmethod
    def _references_workspace(value, workspace_id: str, path: str) -> bool:
        if isinstance(value, str):
            return value in {workspace_id, path}
        if isinstance(value, list):
            return any(NativeRetentionService._references_workspace(item, workspace_id, path)
                       for item in value)
        if isinstance(value, dict):
            return any(NativeRetentionService._references_workspace(item, workspace_id, path)
                       for item in value.values())
        return False

    def _blockers(self, session, workspace) -> tuple[str, ...]:
        reasons: list[str] = []
        if session.execute(
            select(execution_allocations.c.id).where(
                execution_allocations.c.attempt_id == workspace["attempt_id"],
                execution_allocations.c.condition.in_(("ISSUED", "ACTIVE")),
            )
        ).first() is not None:
            reasons.append("active allocation pins workspace")
        if session.execute(
            select(execution_recovery_cases.c.id).where(
                execution_recovery_cases.c.attempt_id == workspace["attempt_id"],
                execution_recovery_cases.c.resolved_at.is_(None),
            )
        ).first() is not None:
            reasons.append("unresolved recovery pins workspace")
        if session.execute(
            select(native_candidate_vectors.c.id).where(
                native_candidate_vectors.c.pwu_id == workspace["pwu_id"],
                native_candidate_vectors.c.condition != "COMMITTED",
            )
        ).first() is not None:
            reasons.append("uncommitted CandidateVector pins workspace")
        if session.execute(
            select(native_resource_pins.c.id).where(
                native_resource_pins.c.resource_kind == "WORKSPACE",
                native_resource_pins.c.resource_id == str(workspace["id"]),
                native_resource_pins.c.active.is_(True),
            )
        ).first() is not None:
            reasons.append("active retention pin protects workspace")
        state = session.execute(select(native_attempt_states.c.runtime_mode).where(
            native_attempt_states.c.attempt_id == workspace["attempt_id"],
        )).scalar_one_or_none()
        if state is not None and state not in {"FINISHED", "STOPPED"}:
            reasons.append("active or recoverable Attempt pins workspace")
        run_id = session.execute(select(production_work_units.c.production_run_id).where(
            production_work_units.c.id == workspace["pwu_id"],
        )).scalar_one_or_none()
        if run_id is not None:
            candidates = session.execute(select(baseline_candidates.c.id).where(
                baseline_candidates.c.production_run_id == run_id,
            )).scalars().all()
            for candidate_id in candidates:
                authorized = session.execute(select(human_authorizations.c.id).where(
                    human_authorizations.c.candidate_id == candidate_id,
                )).first()
                if authorized is None:
                    reasons.append("Human authorization pending; retain workspace for review")
                    break
            work_id = session.execute(select(work_runtime_bindings.c.work_id).where(
                work_runtime_bindings.c.production_run_id == run_id,
            )).scalar_one_or_none()
            if work_id is not None:
                manifests = session.execute(select(work_delivery_manifests.c.id).where(
                    work_delivery_manifests.c.work_id == work_id,
                )).scalars().all()
                for manifest_id in manifests:
                    accepted = session.execute(select(work_delivery_acceptances.c.id).where(
                        work_delivery_acceptances.c.manifest_id == manifest_id,
                    )).first()
                    if accepted is None:
                        reasons.append("Human delivery acceptance pending; retain workspace for review")
                        break
        evidence = session.execute(select(execution_evidence.c.payload).where(
            execution_evidence.c.attempt_id == workspace["attempt_id"],
        )).scalars().all()
        if any(self._references_workspace(payload, str(workspace["id"]),
                                          workspace["materialization_path"])
               for payload in evidence):
            reasons.append("Evidence reference protects workspace")
        return tuple(reasons)

    def _advance_action(
        self,
        action_id: UUID,
        condition: RetentionActionCondition,
        **values,
    ) -> None:
        with self.database.unit_of_work() as uow:
            action = uow.session.execute(
                select(native_retention_actions)
                .where(native_retention_actions.c.id == action_id)
                .with_for_update()
            ).mappings().one()
            uow.session.execute(
                update(native_retention_actions)
                .where(native_retention_actions.c.id == action_id)
                .values(condition=condition.value, updated_at=self._now(), **values)
            )
            uow.commit()

    def _workspace_path(self, workspace_id: UUID) -> Path:
        with self.database.unit_of_work() as uow:
            workspace = self._workspace_row(uow.session, workspace_id)
            return Path(workspace["materialization_path"])

    @staticmethod
    def _workspace_row(session, workspace_id: UUID, *, lock: bool = False):
        statement = select(execution_workspaces).where(execution_workspaces.c.id == workspace_id)
        if lock:
            statement = statement.with_for_update()
        row = session.execute(statement).mappings().one_or_none()
        if row is None:
            raise NativeExecutionNotFound(f"workspace not found: {workspace_id}")
        return row
