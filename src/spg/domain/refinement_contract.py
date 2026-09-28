"""Shared refinement semantics; domain owners retain candidate and authority ownership."""

from enum import StrEnum
import re
from pathlib import PurePosixPath
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RefinementClass(StrEnum):
    ROUTINE_STOCHASTIC_REFINEMENT = "ROUTINE_STOCHASTIC_REFINEMENT"
    DEGRADING_OR_RECURRING_REFINEMENT = "DEGRADING_OR_RECURRING_REFINEMENT"
    SYSTEMIC_OR_NON_CONVERGING_INCIDENT = "SYSTEMIC_OR_NON_CONVERGING_INCIDENT"
    # Rows created before semantic version 2 were explicitly incident records.
    LEGACY_EXECUTION_INCIDENT = "LEGACY_EXECUTION_INCIDENT"


class RefinementSignalKind(StrEnum):
    AMBIGUITY = "AMBIGUITY"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    CONTRACT_MISMATCH = "CONTRACT_MISMATCH"
    REALITY_MISMATCH = "REALITY_MISMATCH"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    CANDIDATE_INCONSISTENT = "CANDIDATE_INCONSISTENT"
    CAPABILITY_MISMATCH = "CAPABILITY_MISMATCH"
    PROVIDER_TRANSPORT = "PROVIDER_TRANSPORT"
    EXECUTION_FAILURE = "EXECUTION_FAILURE"
    VERIFICATION_CONTRADICTION = "VERIFICATION_CONTRADICTION"
    REPEATED_UNCHANGED_OUTCOME = "REPEATED_UNCHANGED_OUTCOME"
    EXPLICIT_ACTION_LOST_BEFORE_EXECUTION = "EXPLICIT_ACTION_LOST_BEFORE_EXECUTION"
    PRIMARY_INTENT_CLAUSE_LOST = "PRIMARY_INTENT_CLAUSE_LOST"
    SEMANTIC_TYPE_MISMATCH = "SEMANTIC_TYPE_MISMATCH"
    RESPONSE_ACTION_INCONSISTENCY = "RESPONSE_ACTION_INCONSISTENCY"
    EXPECTED_EFFECT_NOT_REALIZED = "EXPECTED_EFFECT_NOT_REALIZED"
    ACTION_ARGUMENT_PROVENANCE_INVALID = "ACTION_ARGUMENT_PROVENANCE_INVALID"
    ACTION_SCOPE_INFLATION = "ACTION_SCOPE_INFLATION"
    PRODUCTION_INTENT_SCOPE_INFLATION = "PRODUCTION_INTENT_SCOPE_INFLATION"
    ACTION_REQUIRES_REALITY_REFRESH = "ACTION_REQUIRES_REALITY_REFRESH"
    ACTION_TERMINAL_BLOCKER = "ACTION_TERMINAL_BLOCKER"
    TURN_NON_CONVERGING = "TURN_NON_CONVERGING"


class WorkConvergenceObservation(BaseModel):
    """Evidence from an owner boundary, never authority to change its scope.

    Missing acceptance obligations describe distance to the Human outcome.
    New attempt/candidate identifiers alone are not acceptance improvement.
    Polling a running stage must not produce observations or spend attempts.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    work_id: UUID
    intent_identity: str
    predecessor_id: UUID | None = None
    sequence: int = Field(ge=1)
    boundary: str
    failure_signature: str | None = None
    candidate_identity: str | None = None
    reality_identity: str
    missing_acceptance: tuple[str, ...]
    attempts: int = Field(ge=1)
    no_progress_count: int = Field(ge=0)
    elapsed_seconds: int = Field(ge=0)
    token_usage: dict = Field(default_factory=dict)
    model_cost: dict = Field(default_factory=dict)
    compute_cost: dict = Field(default_factory=dict)
    human_intervention_count: int = Field(default=0, ge=0)
    previous_repair_class: RefinementClass | None = None
    condition: str
    evidence: dict = Field(default_factory=dict)
    created_at: datetime


def convergence_condition(*, missing_acceptance: tuple[str, ...],
    attempts: int, no_progress_count: int, elapsed_seconds: int,
    authority_required: bool = False, attempt_budget: int = 128,
    no_progress_budget: int = 3, time_budget_seconds: int = 7200,
    owner_budget_exhausted: bool = False) -> str:
    """Govern the whole trajectory independently of local repair success."""
    if authority_required:
        return "ESCALATED"
    if not missing_acceptance:
        return "CONVERGED_FOR_REVIEW"
    if (owner_budget_exhausted or attempts >= attempt_budget or no_progress_count >= no_progress_budget
            or elapsed_seconds >= time_budget_seconds):
        return "NON_CONVERGING"
    return "NOT_YET_CONVERGED"


def test_execution_evidence(output: dict) -> dict:
    """Distinguish executed assertions from collection and missing prerequisites.

    This records deterministic tool observations, not an application oracle.
    """
    logs = str(output.get("stdout", "")) + "\n" + str(output.get("stderr", ""))
    if (output.get("returncode") in {126, 127}
            and "unable to start container process" in logs
            and "executable file not found" in logs):
        return {"diagnostic_code": "TEST_ENVIRONMENT_NOT_READY", "effect_observed": False,
            "test_environment_readiness": "NOT_READY", "verification_evidence": "INCOMPLETE"}
    if "ModuleNotFoundError" in logs or "ImportError while importing test module" in logs:
        return {"diagnostic_code": "TEST_ENVIRONMENT_NOT_READY",
            "test_environment_readiness": "NOT_READY", "verification_evidence": "INCOMPLETE"}
    if any(argument in {"--collect-only", "--co"} for argument in output.get("argv", ())):
        return {"diagnostic_code": "VERIFICATION_EVIDENCE_INCOMPLETE",
            "test_environment_readiness": "COLLECTION_ONLY", "verification_evidence": "INCOMPLETE"}
    return {"test_environment_readiness": "OBSERVED_EXECUTION",
        "verification_evidence": "EXECUTED" if output.get("returncode") == 0 else "FAILED"}


def compilation_execution_evidence(output: dict) -> dict:
    """Bind a real Python compilation diagnostic to its invoked source target."""
    argv = output.get("argv") or ()
    executable = PurePosixPath(str(argv[0]).replace("\\", "/")).name.casefold() if argv else ""
    if (len(argv) != 4 or executable not in {"python", "python3", "python.exe", "python3.exe"}
            or list(argv[1:3]) != ["-m", "py_compile"] or not output.get("returncode")):
        return {}
    target = str(argv[3])
    logs = str(output.get("stderr", ""))
    witness = re.search(r'File "([^"]+)", line \d+', logs)
    if (target.startswith("/") or ".." in PurePosixPath(target).parts
            or "SyntaxError" not in logs or witness is None
            or not (witness[1] == target or witness[1].endswith("/" + target))):
        return {}
    return {"diagnostic_code": "PYTHON_SYNTAX_ERROR", "path": target}


def classify_refinement(
    *, converged: bool, same_signature_count: int = 1,
    prior_occurrences: int = 0, budget_exhausted: bool = False,
    authority_required: bool = False, recurrence_threshold: int = 3,
    nonconvergence_threshold: int = 2,
) -> RefinementClass:
    """Classify evidence, not the mere fact that a retry occurred.

    Authority is an independent hard stop. It cannot be bought with budget.
    A locally recovered event becomes an economic signal when it recurs.
    """
    if (budget_exhausted or authority_required or
            (not converged and same_signature_count >= nonconvergence_threshold)):
        return RefinementClass.SYSTEMIC_OR_NON_CONVERGING_INCIDENT
    if prior_occurrences >= recurrence_threshold or (converged and same_signature_count >= 2):
        return RefinementClass.DEGRADING_OR_RECURRING_REFINEMENT
    return RefinementClass.ROUTINE_STOCHASTIC_REFINEMENT
