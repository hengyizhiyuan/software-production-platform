"""Materialize complete Provider input without granting persistence access."""

from datetime import UTC, datetime
from hashlib import sha256
import json
from uuid import NAMESPACE_URL, UUID, uuid5

from spg.application.preparation import PreparationService
from spg.domain.materialization import (
    MaterializedContextArtifact,
    MaterializedExecutionInputRecord,
)
from spg.domain.runtime import RuntimeInvariantViolation
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


class ExecutionInputMaterializationService:
    """Own exact input assembly and durability before Executor dispatch."""

    def __init__(
        self,
        database: Database,
        preparation: PreparationService | None = None,
    ) -> None:
        self.database = database
        self.preparation = preparation or PreparationService(database)

    def materialize(
        self,
        attempt_id: UUID,
        instruction_content: str,
    ) -> MaterializedExecutionInputRecord:
        instruction = instruction_content.strip()
        if not instruction:
            raise RuntimeInvariantViolation(
                "materialized execution instruction cannot be empty"
            )

        request = self.preparation.prepared_execution_request(attempt_id)
        package = self.preparation.context_package(request.context_package_id)
        context_projection: list[MaterializedContextArtifact] = []
        for entry in package.manifest.artifacts:
            content, blob_fingerprint = self.preparation.exact_reality.read_blob(
                request.workspace.repository_path,
                entry.source_revision,
                entry.repository_relative_path,
            )
            if blob_fingerprint != entry.blob_fingerprint:
                raise RuntimeInvariantViolation(
                    "Context Package blob identity changed during input materialization"
                )
            try:
                decoded_content = content.decode("utf-8")
            except UnicodeDecodeError as error:
                raise RuntimeInvariantViolation(
                    "FVS materialized context must be UTF-8 text"
                ) from error
            context_projection.append(
                MaterializedContextArtifact(
                    semantic_role=entry.semantic_role,
                    repository_relative_path=entry.repository_relative_path,
                    source_revision=entry.source_revision,
                    blob_fingerprint=blob_fingerprint,
                    content=decoded_content,
                )
            )

        fingerprint_basis = {
            "attempt_id": str(request.attempt_id),
            "generation": request.generation,
            "production_run_id": str(request.production_run_id),
            "work_unit_id": str(request.work_unit_id),
            "plan_revision_id": str(request.plan_revision_id),
            "source_baseline_id": str(request.source_baseline_id),
            "context_package_id": str(package.id),
            "context_package_version": package.version,
            "context_package_content_fingerprint": package.content_fingerprint,
            "completion_contract_fingerprint": (
                request.completion_contract_fingerprint
            ),
            "prepared_execution_request": request.model_dump(mode="json"),
            "instruction_content": instruction,
            "context_projection": [
                item.model_dump(mode="json") for item in context_projection
            ],
        }
        input_fingerprint = _fingerprint(fingerprint_basis)
        record_id = uuid5(
            NAMESPACE_URL,
            f"spg:materialized-execution-input:{input_fingerprint}",
        )

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            existing = store.materialized_execution_input_for_attempt(attempt_id)
            if existing is not None:
                if existing.input_fingerprint != input_fingerprint:
                    raise RuntimeInvariantViolation(
                        "Attempt already has a different exact materialized execution input"
                    )
                return existing

            timestamp = datetime.now(UTC)
            store.insert_materialized_execution_input(
                {
                    "id": record_id,
                    **fingerprint_basis,
                    "input_fingerprint": input_fingerprint,
                    "created_at": timestamp,
                }
            )
            record = store.materialized_execution_input(record_id)
            if record is None:
                raise RuntimeInvariantViolation(
                    "Materialized Execution Input was not constructed"
                )
            unit_of_work.commit()
            return record


def _fingerprint(value: object) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return sha256(canonical).hexdigest()
