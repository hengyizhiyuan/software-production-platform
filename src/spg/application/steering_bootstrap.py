"""Provider-neutral initial Steering Plan formation for admitted long-lived Work."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from spg.application.runtime import RuntimeService
from spg.application.guided_design import (
    GuidedDesignApplicationService,
    design_schema_for_work,
    guided_design_step_specs,
)
from spg.application.steering import SteeringApplicationService
from spg.domain.planning import OnePwuFitClassification
from spg.domain.product import ProductInvariantViolation, WorkCondition, WorkMode, WorkRecord
from spg.domain.steering import (
    CreateSteeringPlanRequest,
    RealityReference,
    RealityReferenceKind,
    SteeringPlanReconstruction,
    SteeringStepSpec,
    SteeringStepState,
    SteeringStepType,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.steering_store import SteeringStore


class InitialSteeringPlanFormationCapability(Protocol):
    """Form an advisory initial trajectory without owning persisted Plan truth."""

    identity: str

    def form(self, work: WorkRecord) -> tuple[SteeringStepSpec, ...]:
        ...


class DeterministicInitialSteeringPlanFormation:
    """Select a conservative first semantic phase from explicit Work wording."""

    identity = "capability:deterministic-initial-steering-plan-v1"

    _REFINE_MARKERS = (
        "clarify",
        "explore",
        "investigate",
        "refine",
        "research",
        "澄清",
        "探索",
        "调研",
        "研究",
        "梳理",
    )
    _HUMAN_DECISION_MARKERS = (
        "human decision",
        "human must decide",
        "requires human decision",
        "由人决定",
        "需要人工决定",
        "需要人工决策",
        "需要人决定",
    )

    def form(self, work: WorkRecord) -> tuple[SteeringStepSpec, ...]:
        normalized = " ".join(work.raw_user_requirement.casefold().split())
        production_ready = bool(
            work.production_plan is not None
            and work.production_plan.fit_classification
            is OnePwuFitClassification.ONE_PWU_FIT
        )
        if any(marker in normalized for marker in self._HUMAN_DECISION_MARKERS):
            first = SteeringStepType.HUMAN_DECISION
        elif any(marker in normalized for marker in self._REFINE_MARKERS):
            first = SteeringStepType.REFINE
        elif production_ready:
            first = SteeringStepType.PRODUCE
        else:
            first = SteeringStepType.DESIGN

        objective = work.desired_outcome or work.raw_user_requirement.strip()
        specs: list[SteeringStepSpec] = [self._first(first, objective)]
        if first in {SteeringStepType.REFINE, SteeringStepType.HUMAN_DECISION}:
            specs.append(
                SteeringStepSpec(
                    type=SteeringStepType.DESIGN,
                    objective="Establish the bounded product and solution direction",
                    completion_condition=(
                        "A governed design direction is supported by current Reality"
                    ),
                )
            )
        if first is not SteeringStepType.PRODUCE:
            specs.append(
                SteeringStepSpec(
                    type=SteeringStepType.PRODUCE,
                    objective="Produce the next exact change admitted from current Reality",
                    completion_condition=(
                        "The exact bounded production cycle reaches trusted Runtime Commit"
                    ),
                )
            )
        specs.extend(
            (
                SteeringStepSpec(
                    type=SteeringStepType.VERIFY_ACCEPT,
                    objective="Assess the trusted result against the long-lived outcome",
                    completion_condition="Governed evidence supports product acceptance",
                ),
                SteeringStepSpec(
                    type=SteeringStepType.COMPLETE,
                    objective="Complete the admitted long-lived Work",
                    completion_condition="The admitted Work outcome is satisfied",
                ),
            )
        )
        return tuple(specs)

    @staticmethod
    def _first(step_type: SteeringStepType, objective: str) -> SteeringStepSpec:
        completion = {
            SteeringStepType.REFINE: (
                "The Work understanding is sufficient to choose a governed direction"
            ),
            SteeringStepType.HUMAN_DECISION: (
                "A governed Human decision resolves the material direction"
            ),
            SteeringStepType.DESIGN: (
                "A bounded design direction is supported by current Reality"
            ),
            SteeringStepType.PRODUCE: (
                "The exact bounded production cycle reaches trusted Runtime Commit"
            ),
        }[step_type]
        return SteeringStepSpec(
            type=step_type,
            objective=objective,
            completion_condition=completion,
            state=SteeringStepState.CURRENT,
        )


class SteeringBootstrapService:
    """Create the first reconstructable Plan after Work-envelope admission."""

    def __init__(
        self,
        database: Database,
        *,
        capability: InitialSteeringPlanFormationCapability | None = None,
    ) -> None:
        self.database = database
        self.capability = capability or DeterministicInitialSteeringPlanFormation()
        self.steering = SteeringApplicationService(database)
        self.runtime = RuntimeService(database)
        self.guided_design = GuidedDesignApplicationService(database)

    def bootstrap(self, work_id: UUID) -> SteeringPlanReconstruction:
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            steering = SteeringStore(unit_of_work.session)
            work = product.work(work_id)
            if work is None:
                raise ProductInvariantViolation(f"Work not found: {work_id}")
            if work.mode is not WorkMode.LONG_LIVED_STEERING:
                raise ProductInvariantViolation(
                    "Initial Steering bootstrap requires long-lived Work mode"
                )
            if work.condition is not WorkCondition.READY:
                raise ProductInvariantViolation(
                    "Initial Steering bootstrap requires admitted READY Work"
                )
            existing = steering.plan_for_work(work_id)
            if existing is not None:
                reconstruction = self.steering.reconstruct(work_id)
                self.guided_design.bootstrap(work, reconstruction)
                return reconstruction
            resource = product.resource_for_work(work_id)
            steps = (
                guided_design_step_specs(design_schema_for_work(work)[0].issues)
                if self.guided_design.eligible(work)
                else self.capability.form(work)
            )

        baseline = None if resource is None else self.runtime.current_baseline(repository_identity=resource.repository_identity, repository_ref=resource.authoritative_ref)
        work_reference = RealityReference(
            kind=(
                RealityReferenceKind.WORK_REALITY_REVISION
                if work.current_work_reality_revision_id is not None
                else RealityReferenceKind.WORK
            ),
            identity=(
                work.current_work_reality_revision_id
                if work.current_work_reality_revision_id is not None
                else work.id
            ),
        )
        reconstruction = self.steering.create_plan(
            CreateSteeringPlanRequest(
                work_id=work_id,
                rationale=(
                    "Initial provider-neutral Steering trajectory formed from the "
                    f"Human-admitted Work envelope by {self.capability.identity}"
                ),
                reality_refs=(work_reference,) if baseline is None else (
                    work_reference,
                    RealityReference(
                        kind=RealityReferenceKind.TRUSTED_BASELINE,
                        identity=baseline.id,
                    ),
                ),
                steps=steps,
            )
        )
        self.guided_design.bootstrap(work, reconstruction)
        return reconstruction
