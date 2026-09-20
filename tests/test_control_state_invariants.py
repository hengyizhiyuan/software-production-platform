from spg.application.control_state import (
    ControlStateSnapshot,
    project_next_owner,
    validate_control_state,
)


def test_control_state_rejects_human_attention_without_action() -> None:
    violations = validate_control_state(ControlStateSnapshot(
        work_status="NEEDS_ATTENTION",
        next_owner="HUMAN",
        human_attention_required=True,
    ))
    assert "HUMAN_ATTENTION_WITHOUT_ACTION" in violations
    assert "HUMAN_OWNER_WITHOUT_ACTION" in violations


def test_control_state_rejects_blocked_dead_end_and_unowned_finished_attempt() -> None:
    violations = validate_control_state(ControlStateSnapshot(
        work_status="BLOCKED",
        next_owner="",
        attempt_finished_pending_transition=True,
    ))
    assert "NON_TERMINAL_WITHOUT_NEXT_OWNER" in violations
    assert "BLOCKED_WITHOUT_PROGRESS_OWNER" in violations
    assert "FINISHED_ATTEMPT_WITHOUT_TRANSITION_OWNER" in violations


def test_control_state_rejects_running_without_execution_subject() -> None:
    assert validate_control_state(ControlStateSnapshot(
        work_status="RUNNING",
        next_owner="EXECUTOR",
    )) == ("RUNNING_WITHOUT_ACTIVE_SUBJECT",)


def test_control_state_accepts_active_automatic_progression_owner() -> None:
    assert validate_control_state(ControlStateSnapshot(
        work_status="RUNNING",
        next_owner="STEERING",
        automatic_progression_state="ACTIVE",
    )) == ()


def test_control_state_accepts_human_candidate_boundary() -> None:
    assert validate_control_state(ControlStateSnapshot(
        work_status="NEEDS_ATTENTION",
        next_owner="HUMAN",
        human_attention_required=True,
        actionable_human_actions=1,
        attempt_finished_pending_transition=True,
    )) == ()


def test_control_state_detects_duplicate_attention_and_workspace_collapse() -> None:
    violations = validate_control_state(ControlStateSnapshot(
        work_status="READY",
        next_owner="STEERING",
        human_attention_badges=2,
        workspace_engaged=True,
        workspace_visible=False,
    ))
    assert violations == ("DUPLICATE_HUMAN_ATTENTION", "LATCHED_WORKSPACE_ABSENT")


def test_stopped_steering_is_system_owned_without_fabricating_human_attention() -> None:
    next_owner = project_next_owner(
        work_status="READY",
        human_attention_required=False,
        automatic_progression_state="STOPPED",
        active_execution_subject=False,
    )
    violations = validate_control_state(ControlStateSnapshot(
        work_status="READY",
        next_owner=next_owner,
        automatic_progression_state="STOPPED",
    ))

    assert next_owner == "WATT_RECOVERY"
    assert violations == ()
