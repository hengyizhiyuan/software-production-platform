"""Configured local Executor composition over the admitted process boundary."""

from spg.application.materialization import ExecutionInputMaterializationService
from spg.domain.execution import ExecutorDispatchRequest, ExecutorDispatchResult
from spg.domain.runtime import CompletionContract, RuntimeInvariantViolation
from spg.infrastructure.codex_executor_binding import CODEX_REAL_BINDING
from spg.infrastructure.executor_boundary import (
    DedicatedExecutorClient,
    SubprocessExecutorTransport,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


class GovernedDedicatedExecutor:
    """Materialize one admitted PWU instruction, then delegate to the child process."""

    def __init__(
        self,
        database: Database,
        *,
        provider_timeout_seconds: float,
        provider_sandbox_mode: str = "workspace-write",
    ) -> None:
        if not 0 < provider_timeout_seconds <= 600:
            raise ValueError("provider_timeout_seconds must be within (0, 600]")
        self.database = database
        self.provider_timeout_seconds = provider_timeout_seconds
        self.provider_sandbox_mode = provider_sandbox_mode
        self.materialization = ExecutionInputMaterializationService(database)

    def dispatch(self, request: ExecutorDispatchRequest) -> ExecutorDispatchResult:
        with self.database.unit_of_work() as unit_of_work:
            work_unit = RuntimeStore(unit_of_work.session).work_unit(
                request.execution.work_unit_id
            )
        if work_unit is None:
            raise RuntimeInvariantViolation("Executor PWU is unavailable")
        if (
            work_unit.id != request.execution.work_unit_id
            or work_unit.production_run_id != request.execution.production_run_id
            or work_unit.plan_revision_id != request.execution.plan_revision_id
            or work_unit.source_baseline_id != request.execution.source_baseline_id
        ):
            raise RuntimeInvariantViolation("Executor PWU lineage is incoherent")

        materialized = self.materialization.materialize(
            request.execution.attempt_id,
            render_governed_instruction(
                work_unit.objective,
                work_unit.completion_contract,
            ),
        )
        transport = SubprocessExecutorTransport(
            timeout_seconds=self.provider_timeout_seconds + 30,
            provider_binding=CODEX_REAL_BINDING,
            provider_timeout_seconds=self.provider_timeout_seconds,
            provider_sandbox_mode=self.provider_sandbox_mode,
        )
        return DedicatedExecutorClient(
            materialized,
            transport=transport,
        ).dispatch(request)


def render_governed_instruction(
    objective: str,
    completion_contract: CompletionContract,
) -> str:
    """Render only approved Runtime facts into the Provider instruction."""

    outputs = "\n".join(f"- {item}" for item in completion_contract.required_outputs)
    changes = "\n".join(f"- {item}" for item in completion_contract.required_changes)
    artifact = completion_contract.artifact_contract
    plan = completion_contract.production_plan
    plan_section = ""
    if plan is not None:
        steps = "\n".join(
            f"{step.position}. {step.instruction}" for step in plan.ordered_steps
        )
        plan_constraints = "\n".join(
            f"- {item}" for item in plan.inherited_constraints
        )
        plan_section = (
            f"Desired outcome:\n{plan.desired_outcome}\n\n"
            f"Admitted Production Plan objective:\n{plan.objective}\n\n"
            f"Ordered Plan steps:\n{steps}\n\n"
            "Inherited constraints:\n"
            f"{plan_constraints or '- None beyond the admitted contract.'}\n\n"
            f"Verification approach:\n{plan.verification_approach}\n\n"
        )
    artifact_authority = ""
    if artifact is not None:
        constraints = "\n".join(f"- {item}" for item in artifact.constraints)
        artifact_authority = (
            "Artifact Target:\n"
            f"- Path: {artifact.artifact_path}\n"
            f"- Operation: {artifact.operation.value}\n"
            f"- Desired outcome: {artifact.expected_outcome}\n"
            f"- Constraints:\n{constraints or '- None beyond the admitted contract.'}\n\n"
        )
    return (
        "Complete exactly the admitted software-production objective below.\n\n"
        f"Objective:\n{objective.strip()}\n\n"
        f"{plan_section}"
        f"{artifact_authority}"
        f"Authorized output paths:\n{outputs}\n\n"
        f"Authorized changed paths:\n{changes}\n\n"
        "Do not modify any other repository path. Work only inside the supplied "
        "Attempt workspace. Do not commit, push, or change a Git ref."
    )
