from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from openai_codex import Sandbox

from spg.domain.execution import (
    ExecutorDispatchRequest,
    ExecutorReturnControl,
    ProviderReportedOutcome,
)
from spg.domain.planning import (
    OnePwuFitClassification,
    PlannedArtifactOperation,
    ProductionPlanArtifactTarget,
    ProductionPlanProposal,
    ProductionPlanStep,
)
from spg.domain.preparation import (
    ExecutorBinding,
    PreparedExecutionRequest,
    WorkspaceBinding,
)
from spg.domain.runtime import ArtifactContract, ArtifactOperation, CompletionContract
from spg.infrastructure.configured_executor import render_governed_instruction
from spg.providers.codex_sdk_executor import CodexSdkExecutor


class _Status:
    def __init__(self, value: str = "completed") -> None:
        self.value = value


class _Turn:
    def __init__(
        self,
        *,
        turn_id: str,
        response: str,
        mutation: Callable[[], None] | None = None,
        status: str = "completed",
    ) -> None:
        self.id = turn_id
        self.response = response
        self.mutation = mutation
        self.status = status

    def run(self):
        if self.mutation is not None:
            self.mutation()
        return SimpleNamespace(
            id=self.id,
            status=_Status(self.status),
            error=None,
            started_at=1,
            completed_at=2,
            duration_ms=1,
            final_response=self.response,
        )

    def interrupt(self):
        return SimpleNamespace()


class _Thread:
    id = "thread-granularity"

    def __init__(self, turns: list[_Turn]) -> None:
        self.turns = turns
        self.calls: list[tuple[str, dict[str, object]]] = []

    def turn(self, input_content: str, **kwargs):
        self.calls.append((input_content, kwargs))
        return self.turns[len(self.calls) - 1]


class _Codex:
    def __init__(self, thread: _Thread) -> None:
        self.thread = thread
        self.thread_start_count = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def thread_start(self, **_kwargs):
        self.thread_start_count += 1
        return self.thread


def _claim(action: str, summary: str) -> str:
    return json.dumps({"action": action, "activity_summary": summary})


def _request(tmp_path: Path):
    repository = tmp_path / "repository"
    workspace = tmp_path / "workspace"
    repository.mkdir()
    workspace.mkdir()
    attempt_id = uuid4()
    execution = PreparedExecutionRequest(
        attempt_id=attempt_id,
        generation=1,
        production_run_id=uuid4(),
        work_unit_id=uuid4(),
        plan_revision_id=uuid4(),
        source_baseline_id=uuid4(),
        context_package_id=uuid4(),
        context_package_version=1,
        completion_contract_fingerprint="c" * 64,
        executor_binding=ExecutorBinding(
            binding_ref="binding:test",
            capability_identity="capability:executor",
            profile_identity="profile:test",
        ),
        workspace=WorkspaceBinding(
            workspace_identity=f"attempt-worktree:{attempt_id}",
            workspace_path=workspace,
            repository_identity="test://granularity",
            repository_path=repository,
            source_revision="a" * 40,
        ),
    )
    materialized = SimpleNamespace(
        id=uuid4(),
        attempt_id=attempt_id,
        generation=1,
        input_fingerprint="i" * 64,
        prepared_execution_request=execution,
        provider_input=lambda: "exact materialized governed input",
    )
    return (
        ExecutorDispatchRequest(dispatch_id=uuid4(), execution=execution),
        materialized,
        workspace,
    )


def _executor(tmp_path: Path, turns: list[_Turn], **kwargs):
    request, materialized, workspace = _request(tmp_path)
    codex = _Codex(_Thread(turns))
    continuation_checks: list[int] = []

    def continuation_validator(_request: ExecutorDispatchRequest) -> None:
        continuation_checks.append(len(codex.thread.calls))

    executor = CodexSdkExecutor(
        materialized,
        codex_factory=lambda: codex,
        workspace_validator=lambda _workspace: None,
        continuation_validator=kwargs.pop(
            "continuation_validator", continuation_validator
        ),
        **kwargs,
    )
    return request, workspace, codex, continuation_checks, executor


def test_gran_01_05_three_internal_turns_share_one_attempt_and_aggregate_result(
    tmp_path: Path,
) -> None:
    target = tmp_path / "workspace" / "result.txt"
    turns = [
        _Turn(turn_id="turn-1", response=_claim("CONTINUE", "inspected incompatibility")),
        _Turn(
            turn_id="turn-2",
            response=_claim("CONTINUE", "applied bounded correction"),
            mutation=lambda: target.write_text("candidate", encoding="utf-8"),
        ),
        _Turn(turn_id="turn-3", response=_claim("RESULT_READY", "revalidation passed")),
    ]
    request, workspace, codex, checks, executor = _executor(
        tmp_path, turns, max_internal_turns=3
    )

    result = executor.dispatch(request)

    assert target == workspace / "result.txt"
    assert target.read_text(encoding="utf-8") == "candidate"
    assert codex.thread_start_count == 1
    assert len(codex.thread.calls) == 3
    assert checks == [1, 2]
    assert result.return_control is ExecutorReturnControl.RESULT_READY
    assert result.outcome is ProviderReportedOutcome.SUCCESS
    assert result.metadata["internal_turn_count"] == 3
    assert result.metadata["self_refine_occurred"] is True
    assert result.metadata["terminal_executor_outcome"] == "RESULT_READY"
    assert result.metadata["internal_turn_ids"] == ["turn-1", "turn-2", "turn-3"]


def test_gran_10_maximum_turn_bound_stops_unlimited_continuation(
    tmp_path: Path,
) -> None:
    turns = [
        _Turn(turn_id="turn-1", response=_claim("CONTINUE", "first diagnosis")),
        _Turn(turn_id="turn-2", response=_claim("CONTINUE", "second diagnosis")),
    ]
    request, _, codex, _, executor = _executor(
        tmp_path, turns, max_internal_turns=2
    )

    result = executor.dispatch(request)

    assert len(codex.thread.calls) == 2
    assert result.return_control is ExecutorReturnControl.BUDGET_EXHAUSTED
    assert result.outcome is ProviderReportedOutcome.UNKNOWN
    assert result.metadata["executor_stop_reason"] == "MAX_INTERNAL_TURNS_EXHAUSTED"


def test_gran_10_repeated_no_progress_stops_before_another_turn(tmp_path: Path) -> None:
    turns = [
        _Turn(turn_id="turn-1", response=_claim("CONTINUE", "same failure")),
        _Turn(turn_id="turn-2", response=_claim("CONTINUE", "same failure")),
    ]
    request, _, codex, _, executor = _executor(
        tmp_path, turns, max_internal_turns=3
    )

    result = executor.dispatch(request)

    assert len(codex.thread.calls) == 2
    assert result.return_control is ExecutorReturnControl.BUDGET_EXHAUSTED
    assert result.metadata["executor_stop_reason"] == "REPEATED_NO_PROGRESS"


def test_gran_11_boundary_crossing_claim_stops_without_followup_action(
    tmp_path: Path,
) -> None:
    request, workspace, codex, checks, executor = _executor(
        tmp_path,
        [
            _Turn(
                turn_id="turn-1",
                response=_claim(
                    "BOUNDARY_CROSSING_REQUIRED",
                    "a forbidden repository area would be required",
                ),
            )
        ],
    )

    result = executor.dispatch(request)

    assert len(codex.thread.calls) == 1
    assert checks == []
    assert list(workspace.iterdir()) == []
    assert result.return_control is ExecutorReturnControl.BOUNDARY_CROSSING_REQUIRED
    assert result.outcome is ProviderReportedOutcome.UNKNOWN


def test_gran_12_continuity_loss_stops_same_attempt_before_second_turn(
    tmp_path: Path,
) -> None:
    def lost(_request: ExecutorDispatchRequest) -> None:
        raise RuntimeError("generation fenced")

    request, _, codex, _, executor = _executor(
        tmp_path,
        [_Turn(turn_id="turn-1", response=_claim("CONTINUE", "first edit done"))],
        continuation_validator=lost,
    )

    result = executor.dispatch(request)

    assert len(codex.thread.calls) == 1
    assert result.return_control is ExecutorReturnControl.EXECUTION_CONTINUITY_LOST
    assert result.metadata["executor_stop_reason"] == "CONTINUITY_RuntimeError"


def test_gran_16_plain_legacy_one_turn_result_remains_compatible(tmp_path: Path) -> None:
    request, _, codex, checks, executor = _executor(
        tmp_path,
        [_Turn(turn_id="turn-legacy", response="legacy provider result")],
    )

    result = executor.dispatch(request)

    assert len(codex.thread.calls) == 1
    assert checks == []
    assert result.return_control is ExecutorReturnControl.RESULT_READY
    assert result.outcome is ProviderReportedOutcome.SUCCESS
    assert result.summary == "legacy provider result"
    assert result.metadata["self_refine_occurred"] is False


def test_gran_06_09_complete_governed_envelope_and_plan_hint_rendering(
    tmp_path: Path,
) -> None:
    request, _, _ = _request(tmp_path)
    resource_id = uuid4()
    artifact = ArtifactContract(
        engineering_resource_id=resource_id,
        repository_identity="test://granularity",
        source_baseline_id=request.execution.source_baseline_id,
        source_revision=request.execution.workspace.source_revision,
        artifact_path="docs/result.md",
        operation=ArtifactOperation.CREATE,
        constraints=("stay inside the admitted documentation scope",),
        expected_outcome="Record the bounded result",
        verification_obligation="Verify the exact artifact",
    )
    plan = ProductionPlanProposal(
        proposal_id=uuid4(),
        objective="Create the bounded artifact",
        desired_outcome="Record the bounded result",
        ordered_steps=(
            ProductionPlanStep(position=1, instruction="Inspect relevant context"),
            ProductionPlanStep(position=2, instruction="Create the artifact"),
        ),
        artifact_targets=(
            ProductionPlanArtifactTarget(
                path="docs/result.md",
                operation=PlannedArtifactOperation.CREATE,
            ),
        ),
        inherited_constraints=("do not widen scope",),
        verification_approach="Run independent artifact verification",
        fit_classification=OnePwuFitClassification.ONE_PWU_FIT,
        engineering_resource_id=resource_id,
        repository_identity="test://granularity",
        source_baseline_id=request.execution.source_baseline_id,
        source_revision=request.execution.workspace.source_revision,
    )
    contract = CompletionContract(
        required_outputs=("docs/result.md",),
        required_changes=("docs/result.md",),
        required_markers=("bounded-result",),
        forbidden_changes=("src/**",),
        verification_obligations=("GIT_DIFF_CHECK",),
        blocking_conditions=("Human architecture decision required",),
        artifact_contract=artifact,
        production_plan=plan,
    )

    rendered = render_governed_instruction(
        "Create the admitted result",
        contract,
        execution=request.execution,
        repository_ref="refs/heads/main",
        sandbox_policy=Sandbox.workspace_write.value,
        max_internal_turns=3,
        time_budget_seconds=120,
    )

    for expected in (
        str(resource_id),
        "test://granularity",
        "refs/heads/main",
        request.execution.workspace.source_revision,
        "docs/result.md",
        "stay inside the admitted documentation scope",
        "bounded-result",
        "src/**",
        "Human architecture decision required",
        "GIT_DIFF_CHECK",
        "workspace-write",
        "Maximum internal Provider Turns: 3",
        "Total Provider time budget seconds: 120",
        "BOUNDARY_CROSSING_REQUIRED",
        "Non-authoritative strategy hints; Executor owns HOW",
        "only SPG independent Verification can establish trusted satisfaction",
    ):
        assert expected in rendered


def test_gran_turn_control_schema_is_strict_and_complete() -> None:
    schema = CodexSdkExecutor.turn_output_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert set(schema["properties"]["action"]["enum"]) == {
        "CONTINUE",
        "RESULT_READY",
        "UNABLE_TO_COMPLETE",
        "BOUNDARY_CROSSING_REQUIRED",
        "BUDGET_EXHAUSTED",
        "EXECUTION_CONTINUITY_LOST",
    }
