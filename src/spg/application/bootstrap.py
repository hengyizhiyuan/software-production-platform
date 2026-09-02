"""Explicit application composition for the S1-A foundation."""

from dataclasses import dataclass
from pathlib import Path

from spg.config import Settings
from spg.application.runtime import RuntimeService
from spg.application.preparation import PreparationService
from spg.application.materialization import ExecutionInputMaterializationService
from spg.application.execution import ExecutionService
from spg.application.completion import CompletionService
from spg.application.verification import VerificationService
from spg.application.governance import CandidateGovernanceService
from spg.application.integration import RepositoryIntegrationService
from spg.application.runtime_commit import RuntimeCommitService
from spg.application.recovery import RecoveryAssessmentService
from spg.application.reconciliation import RecoveryReconciliationService
from spg.application.attempt_recovery import AttemptRecoveryService
from spg.application.maintenance_recovery import VerifiedMaintenanceRecoveryService
from spg.application.work import WorkApplicationService
from spg.domain.executor import ExecutorCapabilityContract
from spg.domain.preparation import ExecutorBinding
from spg.domain.verifier import VerificationCapabilityContract
from spg.infrastructure.persistence import Database


@dataclass(frozen=True, slots=True)
class Application:
    """Minimal application container without external side effects."""

    settings: Settings

    def status(self) -> dict[str, str]:
        """Return foundation metadata without fabricating production state."""

        return {
            "application": self.settings.application_name,
            "foundation": "ready",
            "runtime_profile": self.settings.runtime_profile,
        }

    def persistence(self) -> Database:
        """Compose persistence explicitly without affecting foundation status."""

        return Database.from_settings(self.settings)

    def runtime(self, database: Database | None = None) -> RuntimeService:
        """Compose governed Runtime operations over explicit persistence."""

        return RuntimeService(database or self.persistence())

    def preparation(self, database: Database | None = None) -> PreparationService:
        """Compose S2-A preparation without composing or dispatching an Executor."""

        return PreparationService(database or self.persistence())

    def execution(self, database: Database | None = None) -> ExecutionService:
        """Compose S2-B Runtime orchestration without selecting a real provider."""

        selected_database = database or self.persistence()
        preparation = PreparationService(selected_database)
        return ExecutionService(selected_database, preparation=preparation)

    def execution_input_materialization(
        self,
        database: Database | None = None,
    ) -> ExecutionInputMaterializationService:
        """Compose exact Provider input materialization without selecting a Provider."""

        selected_database = database or self.persistence()
        preparation = PreparationService(selected_database)
        return ExecutionInputMaterializationService(
            selected_database,
            preparation=preparation,
        )

    def completion(self, database: Database | None = None) -> CompletionService:
        """Compose S3-A output evaluation without Verification or Candidate logic."""

        return CompletionService(database or self.persistence())

    def verification(self, database: Database | None = None) -> VerificationService:
        """Compose S3-B without selecting Guardian or creating a Candidate."""

        return VerificationService(database or self.persistence())

    def candidate_governance(
        self,
        database: Database | None = None,
    ) -> CandidateGovernanceService:
        """Compose S3-C without Repository Integration or Runtime Commit."""

        return CandidateGovernanceService(database or self.persistence())

    def repository_integration(
        self,
        database: Database | None = None,
    ) -> RepositoryIntegrationService:
        """Compose S4-A without Runtime Commit or Trusted Baseline advancement."""

        return RepositoryIntegrationService(database or self.persistence())

    def runtime_commit(
        self,
        database: Database | None = None,
    ) -> RuntimeCommitService:
        """Compose S4-B without repository mutation or S5 recovery."""

        return RuntimeCommitService(database or self.persistence())

    def recovery_assessment(
        self,
        database: Database | None = None,
    ) -> RecoveryAssessmentService:
        """Compose S5-A classification without executing recovery."""

        return RecoveryAssessmentService(database or self.persistence())

    def recovery_reconciliation(
        self,
        database: Database | None = None,
    ) -> RecoveryReconciliationService:
        """Compose S5-B without Git mutation or broad automatic recovery."""

        return RecoveryReconciliationService(database or self.persistence())

    def attempt_recovery(
        self,
        database: Database | None = None,
    ) -> AttemptRecoveryService:
        """Compose S5-C salvage/retry preparation without provider dispatch."""

        return AttemptRecoveryService(database or self.persistence())

    def verified_maintenance_recovery(
        self,
        database: Database | None = None,
    ) -> VerifiedMaintenanceRecoveryService:
        """Compose exact R4-B recovery without executing production or mutating Git."""

        return VerifiedMaintenanceRecoveryService(database or self.persistence())

    def work(
        self,
        database: Database | None = None,
        *,
        workspace_root: Path | None = None,
        executor: ExecutorCapabilityContract | None = None,
        verifier: VerificationCapabilityContract | None = None,
        executor_binding: ExecutorBinding | None = None,
    ) -> WorkApplicationService:
        """Compose the goal-centric MVP product flow over governed Runtime services."""

        options = {
            "workspace_root": workspace_root,
            "executor": executor,
            "verifier": verifier,
        }
        if executor_binding is not None:
            options["executor_binding"] = executor_binding
        return WorkApplicationService(
            database or self.persistence(),
            **options,
        )


def bootstrap(settings: Settings | None = None) -> Application:
    """Construct the application explicitly from typed settings."""

    return Application(settings=settings or Settings())
