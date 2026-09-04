"""Read-only Runtime activation projection over Trusted Baseline Reality."""

from spg.config import Settings
from spg.domain.runtime import SnapshotCondition
from spg.domain.runtime_activation import (
    ActiveRuntimeEvidence,
    RuntimeActivationProjection,
    RuntimeActivationState,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.runtime_activation import GitLocalRuntimeActivation


class RuntimeActivationService:
    """Project active-process evidence without creating production authority."""

    def __init__(self, database: Database, settings: Settings) -> None:
        self.database = database
        self.settings = settings

    def project(self) -> RuntimeActivationProjection:
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            pointer = store.current_pointer()
            baseline = None if pointer is None else store.snapshot(pointer.snapshot_id)
        if baseline is None or baseline.condition is not SnapshotCondition.TRUSTED:
            return RuntimeActivationProjection(
                state=RuntimeActivationState.ACTIVATION_BLOCKED,
                reason="Current Trusted Baseline is unavailable.",
            )

        repository = self.settings.repository_path.resolve()
        inspector = GitLocalRuntimeActivation()
        try:
            trusted_tree = inspector.tree_identity(
                repository,
                baseline.repository_revision,
            )
        except RuntimeError as error:
            return RuntimeActivationProjection(
                state=RuntimeActivationState.ACTIVATION_BLOCKED,
                current_trusted_baseline_revision=baseline.repository_revision,
                reason=str(error),
            )
        return inspector.inspect(
            repository_path=repository,
            active=self._active_evidence(),
            trusted_revision=baseline.repository_revision,
            trusted_tree_identity=trusted_tree,
        )

    def _active_evidence(self) -> ActiveRuntimeEvidence | None:
        values = (
            self.settings.active_runtime_revision,
            self.settings.active_runtime_tree_identity,
            self.settings.active_runtime_package_fingerprint,
            self.settings.active_runtime_static_asset_fingerprint,
            self.settings.active_runtime_source_root,
        )
        if not all(values):
            return None
        return ActiveRuntimeEvidence(
            active_application_revision=str(values[0]),
            active_repository_tree_identity=str(values[1]),
            active_source_package_fingerprint=str(values[2]),
            active_static_asset_fingerprint=str(values[3]),
            active_source_root=str(values[4]),
        )
