"""Read-only Runtime activation projection over Trusted Baseline Reality."""

from pathlib import Path
import spg

from spg.config import Settings
from spg.domain.runtime import SnapshotCondition
from spg.domain.runtime_activation import (
    ActiveRuntimeEvidence,
    HumanReviewRuntimeVersion,
    RuntimeActivationProjection,
    RuntimeActivationState,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.runtime_activation import GitLocalRuntimeActivation


class RuntimeActivationService:
    """Project active-process evidence without creating production authority."""

    def __init__(self, database: Database, settings: Settings) -> None:
        self.database = database
        self.settings = settings

    def project(self) -> RuntimeActivationProjection:
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            resource = ProductStore(unit_of_work.session).default_resource()
            pointer = None if resource is None else store.current_pointer(repository_identity=resource.repository_identity, repository_ref=resource.authoritative_ref)
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
        if self.settings.runtime_activation_mode == "HUMAN_REVIEW":
            return self._review_projection(inspector, repository, baseline.repository_revision, trusted_tree)
        return inspector.inspect(
            repository_path=repository,
            active=self._active_evidence(),
            trusted_revision=baseline.repository_revision,
            trusted_tree_identity=trusted_tree,
        )

    def _review_projection(
        self, inspector: GitLocalRuntimeActivation, repository: Path,
        revision: str, tree: str,
    ) -> RuntimeActivationProjection:
        path = self.settings.human_review_version_file
        expected = self.settings.human_review_version_id
        version = None
        if path is not None and expected and path.is_file() and not path.is_symlink():
            try:
                version = HumanReviewRuntimeVersion.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
        if version is not None and (
            version.version_id != expected
            or not Path(spg.__file__).resolve().is_relative_to(Path(version.source_root).resolve())
        ):
            version = None
        return inspector.inspect_review(
            repository_path=repository, version=version,
            trusted_revision=revision, trusted_tree_identity=tree,
            settings=self.settings,
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
