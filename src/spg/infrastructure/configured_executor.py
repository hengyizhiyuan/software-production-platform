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
    ) -> None:
        if not 0 < provider_timeout_seconds <= 600:
            raise ValueError("provider_timeout_seconds must be within (0, 600]")
        self.database = database
        self.provider_timeout_seconds = provider_timeout_seconds
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
    return (
        "Complete exactly the admitted software-production objective below.\n\n"
        f"Objective:\n{objective.strip()}\n\n"
        f"Authorized output paths:\n{outputs}\n\n"
        f"Authorized changed paths:\n{changes}\n\n"
        "Do not modify any other repository path. Work only inside the supplied "
        "Attempt workspace. Do not commit, push, or change a Git ref."
    )
