"""Small, reusable Control Room ownership invariant projection.

This module does not own Work or execution truth.  It checks that existing
projections always identify who or what can make the next meaningful move.
"""

from __future__ import annotations

from dataclasses import dataclass


TERMINAL_WORK_STATES = frozenset({"COMPLETED"})


@dataclass(frozen=True)
class ControlStateSnapshot:
    work_status: str
    next_owner: str
    human_attention_required: bool = False
    actionable_human_actions: int = 0
    automatic_progression_state: str | None = None
    active_execution_subject: bool = False
    attempt_finished_pending_transition: bool = False
    external_wait_reason: str | None = None
    workspace_engaged: bool = True
    workspace_visible: bool = True
    human_attention_badges: int = 0


def validate_control_state(snapshot: ControlStateSnapshot) -> tuple[str, ...]:
    """Return stable invariant codes for an impossible/dead-end projection."""

    violations: list[str] = []
    terminal = snapshot.work_status in TERMINAL_WORK_STATES
    if not terminal and not snapshot.next_owner:
        violations.append("NON_TERMINAL_WITHOUT_NEXT_OWNER")
    if snapshot.human_attention_required and snapshot.actionable_human_actions < 1:
        violations.append("HUMAN_ATTENTION_WITHOUT_ACTION")
    if snapshot.next_owner == "HUMAN" and snapshot.actionable_human_actions < 1:
        violations.append("HUMAN_OWNER_WITHOUT_ACTION")
    if snapshot.work_status == "RUNNING" and not (
        snapshot.active_execution_subject
        or snapshot.automatic_progression_state in {"ACTIVE", "RUNNING"}
    ):
        violations.append("RUNNING_WITHOUT_ACTIVE_SUBJECT")
    if snapshot.work_status == "BLOCKED" and not (
        snapshot.actionable_human_actions
        or snapshot.external_wait_reason
        or snapshot.automatic_progression_state in {"ACTIVE", "RUNNING", "RECOVERING"}
    ):
        violations.append("BLOCKED_WITHOUT_PROGRESS_OWNER")
    if (
        not terminal
        and snapshot.automatic_progression_state == "STOPPED"
        and not snapshot.actionable_human_actions
        and not snapshot.external_wait_reason
        and not snapshot.active_execution_subject
        and snapshot.next_owner != "WATT_RECOVERY"
    ):
        violations.append("STOPPED_AUTOMATION_WITHOUT_RECOVERY_ACTION")
    if snapshot.attempt_finished_pending_transition and snapshot.next_owner not in {
        "VERIFICATION",
        "STEERING",
        "WATT_RECOVERY",
        "HUMAN",
    }:
        violations.append("FINISHED_ATTEMPT_WITHOUT_TRANSITION_OWNER")
    if snapshot.human_attention_badges > 1:
        violations.append("DUPLICATE_HUMAN_ATTENTION")
    if snapshot.workspace_engaged and not snapshot.workspace_visible:
        violations.append("LATCHED_WORKSPACE_ABSENT")
    return tuple(violations)


def project_next_owner(
    *,
    work_status: str,
    human_attention_required: bool,
    automatic_progression_state: str | None,
    active_execution_subject: bool,
    external_wait_reason: str | None = None,
) -> str:
    if work_status in TERMINAL_WORK_STATES:
        return ""
    if human_attention_required:
        return "HUMAN"
    if external_wait_reason:
        return "EXTERNAL_RESOURCE"
    if active_execution_subject:
        return "EXECUTOR"
    if automatic_progression_state in {
        "ACTIVE",
        "RUNNING",
        "RECOVERING",
        "WAITING_RESOURCE",
    }:
        return "STEERING"
    if automatic_progression_state == "STOPPED":
        return "WATT_RECOVERY"
    if work_status == "BLOCKED":
        return "WATT_RECOVERY"
    return "STEERING"
