"""Durable multi-repository CandidateVector convergence and aggregate commit."""

from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update

from spg.domain.native_execution import NativeExecutionConflict, NativeExecutionNotFound, canonical_digest
from spg.domain.native_vector import (
    CandidateVectorAuthorizationRecord,
    CandidateVectorAuthorizationRequest,
    CandidateVectorProjection,
    CandidateVectorRecord,
    CandidateVectorSealRequest,
    CandidateVectorTarget,
    CandidateVectorTargetRecord,
    NativeAggregateRuntimeCommitRecord,
    NativeVectorVerificationRecord,
    VectorCondition,
    VectorTargetCondition,
)
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.git_integration import GitRepositoryIntegrationAdapter
from spg.infrastructure.persistence import Database
from spg.domain.runtime import RepositoryRealityError
from spg.infrastructure.persistence.native_execution_schema import (
    native_aggregate_runtime_commits,
    native_candidate_vector_authorizations,
    native_candidate_vector_targets,
    native_candidate_vectors,
    native_trusted_source_pointers,
    native_vector_verifications,
)
from spg.infrastructure.repository_lock import repository_lock


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NativeCandidateVectorService:
    """Keep per-target physical Reality separate from aggregate trusted state."""

    def __init__(
        self,
        database: Database,
        *,
        git: GitRepositoryIntegrationAdapter | None = None,
        now=_utcnow,
    ) -> None:
        self.database = database
        self.git = git or GitRepositoryIntegrationAdapter()
        self._now = now

    def register_trusted_source(
        self,
        target: CandidateVectorTarget,
        *,
        trusted_vector_digest: str,
    ) -> None:
        observed = self.git.read_ref(
            Path(target.repository_path), target.target_authoritative_ref
        )
        if observed != target.expected_source_revision:
            raise NativeExecutionConflict("trusted source registration differs from Git Reality")
        tree = self.git.read_commit_tree(Path(target.repository_path), observed)
        now = self._now()
        with self.database.unit_of_work() as uow:
            existing = uow.session.execute(
                select(native_trusted_source_pointers).where(
                    native_trusted_source_pointers.c.repository_identity
                    == target.repository_identity,
                    native_trusted_source_pointers.c.target_authoritative_ref
                    == target.target_authoritative_ref,
                )
            ).mappings().one_or_none()
            if existing is not None:
                if (
                    existing["repository_revision"] != observed
                    or existing["tree_identity"] != tree
                    or existing["trusted_vector_digest"] != trusted_vector_digest
                ):
                    raise NativeExecutionConflict("trusted source pointer already differs")
                return
            uow.session.execute(
                insert(native_trusted_source_pointers).values(
                    repository_identity=target.repository_identity,
                    target_authoritative_ref=target.target_authoritative_ref,
                    repository_revision=observed,
                    tree_identity=tree,
                    trusted_vector_digest=trusted_vector_digest,
                    version=1,
                    updated_at=now,
                )
            )
            uow.commit()

    def record_verification(
        self,
        record: NativeVectorVerificationRecord,
        *,
        repository_path: Path,
    ) -> NativeVectorVerificationRecord:
        """Persist an independent exact-subject result without interpreting it as trust."""

        if record.provider_identity.startswith(("executor:", "model:")):
            raise NativeExecutionConflict("Executor/model self-verification is not independent")
        if not self.git.commit_exists(repository_path, record.proposed_revision):
            raise NativeExecutionConflict("verification subject commit is missing")
        if (
            self.git.read_commit_tree(repository_path, record.proposed_revision)
            != record.proposed_tree_identity
        ):
            raise NativeExecutionConflict("verification subject tree differs")
        with self.database.unit_of_work() as uow:
            existing = uow.session.execute(
                select(native_vector_verifications).where(
                    native_vector_verifications.c.id == record.id
                )
            ).mappings().one_or_none()
            if existing is not None:
                loaded = NativeVectorVerificationRecord.model_validate(dict(existing))
                if loaded != record:
                    raise NativeExecutionConflict("verification identity has different meaning")
                return loaded
            uow.session.execute(
                insert(native_vector_verifications).values(**record.model_dump(mode="json"))
            )
            uow.commit()
            return record

    def seal(self, request: CandidateVectorSealRequest) -> CandidateVectorProjection:
        now = self._now()
        with self.database.unit_of_work() as uow:
            native = NativeExecutionStore(uow.session)
            checkpoint = native.checkpoint(request.checkpoint_id)
            if checkpoint is None or checkpoint.source_vector_digest != request.source_vector_digest:
                raise NativeExecutionConflict(
                    "CandidateVector requires its exact committed source checkpoint"
                )
            binding = native.attempt_binding(checkpoint.attempt_id)
            if binding.pwu_id != request.pwu_id:
                raise NativeExecutionConflict("CandidateVector checkpoint belongs to another PWU")
            source_by_mount = {
                member.mount_id: member for member in binding.binding.source_vector.members
            }
            for target in request.targets:
                source = source_by_mount.get(target.mount_id)
                if (
                    source is None
                    or source.repository_identity != target.repository_identity
                    or source.source_commit_oid != target.expected_source_revision
                ):
                    raise NativeExecutionConflict(
                        f"CandidateVector target {target.mount_id} differs from SourceVector"
                    )
                path = Path(target.repository_path)
                if not self.git.commit_exists(path, target.proposed_revision):
                    raise NativeExecutionConflict("CandidateVector proposed commit is missing")
                if self.git.read_commit_tree(path, target.proposed_revision) != target.proposed_tree_identity:
                    raise NativeExecutionConflict("CandidateVector proposed tree differs")
                verification_rows = tuple(
                    uow.session.execute(
                        select(native_vector_verifications).where(
                            native_vector_verifications.c.id.in_(
                                target.verification_evidence_ids
                            )
                        )
                    ).mappings()
                )
                if len(verification_rows) != len(target.verification_evidence_ids):
                    raise NativeExecutionConflict("CandidateVector verification evidence is missing")
                for verification in verification_rows:
                    if (
                        verification["pwu_id"] != request.pwu_id
                        or verification["mount_id"] != target.mount_id
                        or verification["proposed_revision"] != target.proposed_revision
                        or verification["proposed_tree_identity"]
                        != target.proposed_tree_identity
                        or verification["result"] != "PASS"
                    ):
                        raise NativeExecutionConflict(
                            "CandidateVector verification does not PASS its exact target"
                        )
                observed_obligations = {row["obligation"] for row in verification_rows}
                if observed_obligations != set(target.verification_obligations):
                    raise NativeExecutionConflict(
                        "CandidateVector verification does not cover exact obligations"
                    )
            existing = uow.session.execute(
                select(native_candidate_vectors).where(
                    native_candidate_vectors.c.manifest_digest == request.digest
                )
            ).mappings().one_or_none()
            if existing is not None:
                return self._projection(uow.session, existing["id"])
            vector_id = uuid4()
            uow.session.execute(
                insert(native_candidate_vectors).values(
                    id=vector_id,
                    pwu_id=request.pwu_id,
                    source_vector_digest=request.source_vector_digest,
                    checkpoint_id=request.checkpoint_id,
                    manifest=request.model_dump(mode="json"),
                    manifest_digest=request.digest,
                    condition=VectorCondition.SEALED.value,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
            )
            for target in request.targets:
                operation_key = canonical_digest(
                    {
                        "vector_digest": request.digest,
                        "mount_id": target.mount_id,
                        "expected": target.expected_source_revision,
                        "proposed": target.proposed_revision,
                    }
                )
                uow.session.execute(
                    insert(native_candidate_vector_targets).values(
                        id=uuid4(), vector_id=vector_id, mount_id=target.mount_id,
                        target=target.model_dump(mode="json"),
                        condition=VectorTargetCondition.PREPARED.value,
                        observed_revision=None, operation_key=operation_key,
                        version=1, prepared_at=now, settled_at=None,
                    )
                )
            uow.commit()
        return self.projection(vector_id)

    def authorize(
        self, request: CandidateVectorAuthorizationRequest
    ) -> CandidateVectorAuthorizationRecord:
        now = self._now()
        with self.database.unit_of_work() as uow:
            vector = self._vector_row(uow.session, request.vector_id, lock=True)
            if vector["manifest_digest"] != request.manifest_digest:
                raise NativeExecutionConflict("authorization names the wrong CandidateVector")
            existing = uow.session.execute(
                select(native_candidate_vector_authorizations).where(
                    native_candidate_vector_authorizations.c.vector_id == request.vector_id
                )
            ).mappings().one_or_none()
            if existing is not None:
                record = CandidateVectorAuthorizationRecord.model_validate(dict(existing))
                if (
                    record.manifest_digest != request.manifest_digest
                    or record.authority_identity != request.authority_identity
                ):
                    raise NativeExecutionConflict("CandidateVector already has different authority")
                return record
            if vector["condition"] != VectorCondition.SEALED.value:
                raise NativeExecutionConflict("CandidateVector is no longer authorizable")
            record = CandidateVectorAuthorizationRecord(
                id=uuid4(), vector_id=request.vector_id,
                manifest_digest=request.manifest_digest,
                authority_identity=request.authority_identity,
                rationale=request.rationale, authorized_at=now,
            )
            uow.session.execute(
                insert(native_candidate_vector_authorizations).values(
                    **record.model_dump(mode="json")
                )
            )
            self._set_vector_condition(
                uow.session, vector, VectorCondition.AUTHORIZED, now
            )
            uow.commit()
            return record

    def integrate(self, vector_id: UUID) -> CandidateVectorProjection:
        projection = self.projection(vector_id)
        if projection.authorization is None:
            raise NativeExecutionConflict("CandidateVector integration requires authorization")
        if projection.vector.condition is VectorCondition.COMMITTED:
            return projection
        targets = tuple(item.target for item in projection.targets)
        with ExitStack() as stack:
            for target in sorted(
                targets,
                key=lambda item: (item.repository_identity, item.target_authoritative_ref),
            ):
                stack.enter_context(
                    repository_lock(
                        self.database,
                        target.repository_identity,
                        target.target_authoritative_ref,
                    )
                )
            for target_record in projection.targets:
                if not self._integrate_target(vector_id, target_record):
                    break
        return self._refresh_vector_condition(vector_id)

    def commit(self, vector_id: UUID) -> NativeAggregateRuntimeCommitRecord:
        now = self._now()
        with self.database.unit_of_work() as uow:
            vector = self._vector_row(uow.session, vector_id, lock=True)
            existing = uow.session.execute(
                select(native_aggregate_runtime_commits).where(
                    native_aggregate_runtime_commits.c.vector_id == vector_id
                )
            ).mappings().one_or_none()
            if existing is not None:
                return NativeAggregateRuntimeCommitRecord.model_validate(dict(existing))
            projection = self._projection(uow.session, vector_id)
            if (
                projection.authorization is None
                or vector["condition"] != VectorCondition.CONVERGED.value
                or any(
                    item.condition is not VectorTargetCondition.CONVERGED
                    for item in projection.targets
                )
            ):
                raise NativeExecutionConflict(
                    "aggregate Runtime Commit requires every exact target converged"
                )
            pointers = {}
            ordered_targets = sorted(
                projection.targets,
                key=lambda item: (
                    item.target.repository_identity,
                    item.target.target_authoritative_ref,
                ),
            )
            for item in ordered_targets:
                target = item.target
                pointer = uow.session.execute(
                    select(native_trusted_source_pointers)
                    .where(
                        native_trusted_source_pointers.c.repository_identity
                        == target.repository_identity,
                        native_trusted_source_pointers.c.target_authoritative_ref
                        == target.target_authoritative_ref,
                    )
                    .with_for_update()
                ).mappings().one_or_none()
                if pointer is None or pointer["repository_revision"] != target.expected_source_revision:
                    raise NativeExecutionConflict("trusted source vector drifted before aggregate commit")
                if self.git.read_ref(Path(target.repository_path), target.target_authoritative_ref) != target.proposed_revision:
                    raise NativeExecutionConflict("Git target is not converged at aggregate commit")
                pointers[target.mount_id] = (pointer, target)
            trusted_digest = canonical_digest(
                {
                    mount_id: {
                        "repository_identity": target.repository_identity,
                        "repository_revision": target.proposed_revision,
                        "tree_identity": target.proposed_tree_identity,
                    }
                    for mount_id, (_, target) in sorted(pointers.items())
                }
            )
            record = NativeAggregateRuntimeCommitRecord(
                id=uuid4(), vector_id=vector_id,
                manifest_digest=vector["manifest_digest"],
                authorization_id=projection.authorization.id,
                trusted_vector_digest=trusted_digest, committed_at=now,
            )
            uow.session.execute(
                insert(native_aggregate_runtime_commits).values(
                    **record.model_dump(mode="json")
                )
            )
            for pointer, target in pointers.values():
                result = uow.session.execute(
                    update(native_trusted_source_pointers)
                    .where(
                        native_trusted_source_pointers.c.repository_identity
                        == target.repository_identity,
                        native_trusted_source_pointers.c.target_authoritative_ref
                        == target.target_authoritative_ref,
                        native_trusted_source_pointers.c.version == pointer["version"],
                    )
                    .values(
                        repository_revision=target.proposed_revision,
                        tree_identity=target.proposed_tree_identity,
                        trusted_vector_digest=trusted_digest,
                        version=pointer["version"] + 1,
                        updated_at=now,
                    )
                )
                if result.rowcount != 1:
                    raise NativeExecutionConflict("trusted source pointer update raced")
            self._set_vector_condition(uow.session, vector, VectorCondition.COMMITTED, now)
            uow.commit()
            return record

    def projection(self, vector_id: UUID) -> CandidateVectorProjection:
        with self.database.unit_of_work() as uow:
            return self._projection(uow.session, vector_id)

    def _integrate_target(
        self, vector_id: UUID, record: CandidateVectorTargetRecord
    ) -> bool:
        target = record.target
        path = Path(target.repository_path)
        try:
            observed = self.git.read_ref(path, target.target_authoritative_ref)
        except RepositoryRealityError:
            self._settle_target(record.id, VectorTargetCondition.UNKNOWN, None)
            return False
        if observed == target.proposed_revision:
            self._settle_target(record.id, VectorTargetCondition.CONVERGED, observed)
            return True
        if record.condition is VectorTargetCondition.CONVERGED:
            self._settle_target(record.id, VectorTargetCondition.UNKNOWN, observed)
            return False
        if observed != target.expected_source_revision:
            self._settle_target(record.id, VectorTargetCondition.FAILED, observed)
            return False
        try:
            attempted = self.git.compare_and_swap_ref(
                path,
                target.target_authoritative_ref,
                target.expected_source_revision,
                target.proposed_revision,
            )
            observed = self.git.read_ref(path, target.target_authoritative_ref)
        except RepositoryRealityError:
            self._settle_target(record.id, VectorTargetCondition.UNKNOWN, None)
            return False
        condition = (
            VectorTargetCondition.CONVERGED
            if attempted and observed == target.proposed_revision
            else VectorTargetCondition.UNKNOWN
        )
        self._settle_target(record.id, condition, observed)
        return condition is VectorTargetCondition.CONVERGED

    def _settle_target(
        self, target_id: UUID, condition: VectorTargetCondition, observed: str | None
    ) -> None:
        with self.database.unit_of_work() as uow:
            row = uow.session.execute(
                select(native_candidate_vector_targets)
                .where(native_candidate_vector_targets.c.id == target_id)
                .with_for_update()
            ).mappings().one()
            result = uow.session.execute(
                update(native_candidate_vector_targets)
                .where(
                    native_candidate_vector_targets.c.id == target_id,
                    native_candidate_vector_targets.c.version == row["version"],
                )
                .values(
                    condition=condition.value,
                    observed_revision=observed,
                    settled_at=self._now(),
                    version=row["version"] + 1,
                )
            )
            if result.rowcount != 1:
                raise NativeExecutionConflict("CandidateVector target state update raced")
            uow.commit()

    def _refresh_vector_condition(self, vector_id: UUID) -> CandidateVectorProjection:
        with self.database.unit_of_work() as uow:
            vector = self._vector_row(uow.session, vector_id, lock=True)
            projection = self._projection(uow.session, vector_id)
            if vector["condition"] == VectorCondition.COMMITTED.value:
                return projection
            condition = (
                VectorCondition.CONVERGED
                if all(
                    item.condition is VectorTargetCondition.CONVERGED
                    for item in projection.targets
                )
                else VectorCondition.PARTIAL
            )
            if vector["condition"] != condition.value:
                self._set_vector_condition(uow.session, vector, condition, self._now())
            uow.commit()
        return self.projection(vector_id)

    @staticmethod
    def _set_vector_condition(session, vector, condition: VectorCondition, now: datetime) -> None:
        result = session.execute(
            update(native_candidate_vectors)
            .where(
                native_candidate_vectors.c.id == vector["id"],
                native_candidate_vectors.c.version == vector["version"],
            )
            .values(
                condition=condition.value,
                version=vector["version"] + 1,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            raise NativeExecutionConflict("CandidateVector state update raced")

    @staticmethod
    def _vector_row(session, vector_id: UUID, *, lock: bool = False):
        statement = select(native_candidate_vectors).where(
            native_candidate_vectors.c.id == vector_id
        )
        if lock:
            statement = statement.with_for_update()
        row = session.execute(statement).mappings().one_or_none()
        if row is None:
            raise NativeExecutionNotFound(f"CandidateVector not found: {vector_id}")
        return row

    @classmethod
    def _projection(cls, session, vector_id: UUID) -> CandidateVectorProjection:
        vector = cls._vector_row(session, vector_id)
        authorization_row = session.execute(
            select(native_candidate_vector_authorizations).where(
                native_candidate_vector_authorizations.c.vector_id == vector_id
            )
        ).mappings().one_or_none()
        target_rows = session.execute(
            select(native_candidate_vector_targets)
            .where(native_candidate_vector_targets.c.vector_id == vector_id)
            .order_by(native_candidate_vector_targets.c.mount_id)
        ).mappings()
        commit_id = session.scalar(
            select(native_aggregate_runtime_commits.c.id).where(
                native_aggregate_runtime_commits.c.vector_id == vector_id
            )
        )
        return CandidateVectorProjection(
            vector=CandidateVectorRecord(
                id=vector["id"], pwu_id=vector["pwu_id"],
                source_vector_digest=vector["source_vector_digest"],
                checkpoint_id=vector["checkpoint_id"],
                manifest_digest=vector["manifest_digest"],
                condition=vector["condition"], created_at=vector["created_at"],
                updated_at=vector["updated_at"], version=vector["version"],
            ),
            authorization=(
                CandidateVectorAuthorizationRecord.model_validate(dict(authorization_row))
                if authorization_row is not None else None
            ),
            targets=tuple(
                CandidateVectorTargetRecord(
                    id=row["id"], vector_id=row["vector_id"],
                    target=CandidateVectorTarget.model_validate(row["target"]),
                    condition=row["condition"],
                    observed_revision=row["observed_revision"],
                    operation_key=row["operation_key"], prepared_at=row["prepared_at"],
                    settled_at=row["settled_at"], version=row["version"],
                )
                for row in target_rows
            ),
            aggregate_commit_id=commit_id,
        )
