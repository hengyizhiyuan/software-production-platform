"""Shared refinement semantics; domain owners retain candidate and authority ownership."""

from enum import StrEnum


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
