"""Action admission policy, consumed by existing owners; no lifecycle coordinator.

Subsystem states are evidence. None substitutes for intent, resource authority,
capability, or delivery authorization. Owners provide independently verified facts.
"""
from dataclasses import dataclass
from enum import StrEnum

from spg.domain.connectors import SideEffectLevel

POLICY_VERSION = "lifecycle-action-admission-v1"


class ActionFamily(StrEnum):
    INSPECT = "INSPECT"
    ACQUIRE_REPOSITORY = "ACQUIRE_REPOSITORY"
    LOCAL_BRANCH = "LOCAL_BRANCH"
    RESEARCH = "RESEARCH"
    PREPARE = "PREPARE"
    PLAN = "PLAN"
    PRODUCE = "PRODUCE"
    VERIFY = "VERIFY"
    PREVIEW = "PREVIEW"
    HUMAN_ACCEPTANCE = "HUMAN_ACCEPTANCE"
    DELIVERY = "DELIVERY"
    RELEASE = "RELEASE"
    NEW_WORK = "NEW_WORK"


class ActionEligibility(StrEnum):
    AUTO_ALLOWED = "AUTO_ALLOWED"
    ALLOWED_IF_EXPLICIT = "ALLOWED_IF_EXPLICIT"
    ALLOWED_IF_AUTHORIZED = "ALLOWED_IF_AUTHORIZED"
    REQUIRES_HUMAN = "REQUIRES_HUMAN"
    REQUIRES_WORK_ADMISSION = "REQUIRES_WORK_ADMISSION"
    REQUIRES_CANDIDATE = "REQUIRES_CANDIDATE"
    REQUIRES_ACCEPTANCE = "REQUIRES_ACCEPTANCE"
    REQUIRES_DELIVERY_AUTHORIZATION = "REQUIRES_DELIVERY_AUTHORIZATION"
    BLOCKED = "BLOCKED"
    SELF_REFINE_FIRST = "SELF_REFINE_FIRST"


SIDE_EFFECTS = {
    ActionFamily.INSPECT: SideEffectLevel.READ,
    ActionFamily.RESEARCH: SideEffectLevel.READ,
    ActionFamily.ACQUIRE_REPOSITORY: SideEffectLevel.WORKSPACE_MUTATION,
    ActionFamily.LOCAL_BRANCH: SideEffectLevel.WORKSPACE_MUTATION,
    ActionFamily.PREPARE: SideEffectLevel.WORKSPACE_MUTATION,
    ActionFamily.PLAN: SideEffectLevel.READ,
    ActionFamily.PRODUCE: SideEffectLevel.WORKSPACE_MUTATION,
    ActionFamily.VERIFY: SideEffectLevel.WORKSPACE_MUTATION,
    ActionFamily.PREVIEW: SideEffectLevel.WORKSPACE_MUTATION,
    ActionFamily.HUMAN_ACCEPTANCE: SideEffectLevel.READ,
    ActionFamily.NEW_WORK: SideEffectLevel.READ,
    ActionFamily.DELIVERY: SideEffectLevel.EXTERNAL_WRITE,
    ActionFamily.RELEASE: SideEffectLevel.DESTRUCTIVE,
}


@dataclass(frozen=True)
class ActionFacts:
    explicit: bool = False
    authority: bool = False
    capability: bool = False
    credential: bool = True  # True means no credential needed or verified available.
    work_admitted: bool = False
    production_intent_sufficient: bool = False
    repository_ready: bool = False
    candidate: bool = False
    candidate_sealed: bool = False
    correction_authorized: bool = False
    preview_required: bool = False
    served_verified: bool = False
    human_accepted: bool = False
    delivery_authorized: bool = False
    system_obligation: bool = False
    already_completed: bool = False
    retryable: bool = False
    terminal: bool = False
    attempts: int = 0
    attempt_budget: int = 3
    side_effect: SideEffectLevel | None = None


@dataclass(frozen=True)
class ActionDecision:
    eligibility: ActionEligibility
    execute: bool
    signal: str
    policy_version: str = POLICY_VERSION


def admit_action(action: ActionFamily, facts: ActionFacts) -> ActionDecision:
    """Evaluate independent obligations; never infer authority from coarse state."""
    def stop(status, signal):
        return ActionDecision(status, False, signal)

    if not facts.authority:
        return stop(ActionEligibility.BLOCKED, "ACTION_AUTHORITY_MISSING")
    if facts.side_effect is not None and facts.side_effect != SIDE_EFFECTS[action]:
        return stop(ActionEligibility.BLOCKED, "ACTION_SIDE_EFFECT_CLASS_MISMATCH")
    if facts.terminal or (facts.retryable and facts.attempts >= facts.attempt_budget):
        return stop(ActionEligibility.BLOCKED, "ACTION_TERMINAL")
    if facts.already_completed:
        return stop(ActionEligibility.AUTO_ALLOWED, "ACTION_ALREADY_COMPLETED")
    if not (facts.explicit or facts.system_obligation):
        return stop(ActionEligibility.ALLOWED_IF_EXPLICIT, "ACTION_NOT_EXPLICIT")
    if not facts.capability:
        return stop(ActionEligibility.BLOCKED, "CAPABILITY_MISSING")
    if not facts.credential:
        return stop(ActionEligibility.REQUIRES_HUMAN, "CREDENTIAL_REQUIRED")
    if action in {ActionFamily.PLAN, ActionFamily.PRODUCE, ActionFamily.PREPARE}:
        if not facts.work_admitted or not facts.production_intent_sufficient:
            return stop(ActionEligibility.REQUIRES_WORK_ADMISSION, "ACTION_REQUIRES_WORK_ADMISSION")
    if action is ActionFamily.PRODUCE and facts.candidate_sealed and not facts.correction_authorized:
        return stop(ActionEligibility.SELF_REFINE_FIRST, "SEALED_CANDIDATE_REQUIRES_CORRECTION")
    if action is ActionFamily.LOCAL_BRANCH and not facts.repository_ready:
        return stop(ActionEligibility.SELF_REFINE_FIRST, "REPOSITORY_REALITY_REQUIRED")
    if action in {ActionFamily.PREVIEW, ActionFamily.HUMAN_ACCEPTANCE, ActionFamily.DELIVERY, ActionFamily.RELEASE}:
        if not facts.candidate:
            return stop(ActionEligibility.REQUIRES_CANDIDATE, "ACTION_REQUIRES_CANDIDATE")
    if action is ActionFamily.HUMAN_ACCEPTANCE and facts.preview_required and not facts.served_verified:
        return stop(ActionEligibility.SELF_REFINE_FIRST, "PREVIEW_NOT_VERIFIED")
    if action in {ActionFamily.DELIVERY, ActionFamily.RELEASE}:
        if not facts.human_accepted:
            return stop(ActionEligibility.REQUIRES_ACCEPTANCE, "ACTION_REQUIRES_HUMAN_ACCEPTANCE")
        if not facts.delivery_authorized:
            return stop(ActionEligibility.REQUIRES_DELIVERY_AUTHORIZATION, "ACTION_REQUIRES_DELIVERY_AUTHORIZATION")
    status = (ActionEligibility.ALLOWED_IF_AUTHORIZED
        if action in {ActionFamily.DELIVERY, ActionFamily.RELEASE}
        else ActionEligibility.AUTO_ALLOWED if facts.system_obligation
        else ActionEligibility.ALLOWED_IF_EXPLICIT)
    return ActionDecision(status, True, "ACTION_RETRYABLE" if facts.retryable else "ACTION_ADMITTED")
