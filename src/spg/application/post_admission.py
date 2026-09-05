"""Mode-aware downstream activation after governed Work admission."""

from __future__ import annotations

from uuid import UUID

from spg.application.orchestration import ProductionOrchestrator
from spg.application.steering_bootstrap import SteeringBootstrapService
from spg.application.steering_driver import PlanSteeringDriver
from spg.application.work import WorkApplicationService
from spg.domain.product import (
    ProductInvariantViolation,
    WorkMode,
    WorkProjection,
    WorkStatus,
)


class WorkPostAdmissionService:
    """Route admitted Work without owning Work, Plan, or Runtime truth."""

    def __init__(
        self,
        work_service: WorkApplicationService,
        steering_bootstrap: SteeringBootstrapService,
        steering_driver: PlanSteeringDriver,
        production_orchestrator: ProductionOrchestrator,
    ) -> None:
        self.work_service = work_service
        self.steering_bootstrap = steering_bootstrap
        self.steering_driver = steering_driver
        self.production_orchestrator = production_orchestrator

    def activate(self, work_id: UUID) -> WorkProjection:
        """Activate exactly the lifecycle selected by persisted Work mode."""

        work = self.work_service.get_work(work_id)
        if work.status not in {WorkStatus.READY, WorkStatus.RUNNING}:
            raise ProductInvariantViolation(
                "Post-admission activation requires an admitted Work"
            )
        if work.mode is WorkMode.IMMEDIATE_PRODUCTION:
            self.production_orchestrator.schedule(work_id)
            return self.work_service.get_work(work_id)

        reconstruction = self.steering_bootstrap.bootstrap(work_id)
        if reconstruction.current_step is None:
            raise ProductInvariantViolation(
                "Long-lived Work bootstrap produced no CURRENT Steering Step"
            )
        scheduled = self.steering_driver.schedule(work_id)
        if not scheduled and not self.steering_driver.is_active(work_id):
            raise ProductInvariantViolation(
                "Steering Plan persisted but automatic driver scheduling is unavailable"
            )
        return self.work_service.get_work(work_id)

    def bootstrap_incomplete_ready_long_lived(self) -> tuple[UUID, ...]:
        """Repair only the durable admission-to-bootstrap interruption window."""

        recovered: list[UUID] = []
        for work in self.work_service.list_works():
            if (
                work.mode is WorkMode.LONG_LIVED_STEERING
                and work.status is WorkStatus.READY
                and not work.steering_enabled
            ):
                reconstruction = self.steering_bootstrap.bootstrap(work.work_id)
                if reconstruction.current_step is None:
                    raise ProductInvariantViolation(
                        "Recovered Steering Plan has no CURRENT Step"
                    )
                recovered.append(work.work_id)
        return tuple(recovered)
