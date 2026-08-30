"""Application composition boundary."""

from spg.application.bootstrap import Application, bootstrap
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

__all__ = [
    "Application",
    "AttemptRecoveryService",
    "CandidateGovernanceService",
    "CompletionService",
    "ExecutionService",
    "ExecutionInputMaterializationService",
    "PreparationService",
    "RepositoryIntegrationService",
    "RecoveryAssessmentService",
    "RecoveryReconciliationService",
    "RuntimeService",
    "RuntimeCommitService",
    "VerificationService",
    "bootstrap",
]
