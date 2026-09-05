"""Authority-safe bridge from one Steering PRODUCE Step to one SPG cycle."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import subprocess
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.planning import ProductionPlanningService
from spg.application.runtime import RuntimeService
from spg.application.steering import SteeringApplicationService
from spg.application.steering_decision import (
    DeterministicPlanSteeringCapability,
    PlanFrameAssembler,
    SteeringDecisionApplicationService,
)
from spg.application.work import WorkApplicationService
from spg.domain.change import ChangeOperation, CodeChangeTarget, ProductionTargetKind
from spg.domain.planning import (
    OnePwuFitClassification,
    PlannedArtifactOperation,
    ProductionPlanArtifactTarget,
    ProductionPlanningRequest,
)
from spg.domain.product import (
    EngineeringScopeCondition,
    ProductInvariantViolation,
    ProductionCycleBindingCondition,
    SteeringProductionAdmission,
    SteeringProductionRequest,
)
from spg.domain.runtime import (
    ArtifactContract,
    ArtifactOperation,
    CompletionContract,
    InitialRunRequest,
    ProductionHorizon,
)
from spg.domain.steering import (
    NextStepCandidate,
    SteeringAttentionReason,
    SteeringAuthorityAssessment,
    SteeringInvariantViolation,
    SteeringOutcome,
    SteeringStepState,
    SteeringStepType,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.steering_store import SteeringStore
from spg.providers.rule_based_planner import RuleBasedProductionPlanner


class SteeringProductionService:
    """Materialize and admit independent one-PWU cycles without steering them."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.runtime = RuntimeService(database)
        self.planning = ProductionPlanningService(RuleBasedProductionPlanner())

    def materialize_request(self, work_id: UUID) -> SteeringProductionRequest:
        reconstruction = SteeringApplicationService(self.database).reconstruct(work_id)
        step = reconstruction.current_step
        if step is None or step.type is not SteeringStepType.PRODUCE:
            raise SteeringInvariantViolation(
                "Production admission requires the current Steering Step to be PRODUCE"
            )
        if (
            reconstruction.latest_decision is not None
            and reconstruction.latest_decision.current_step_id == step.id
            and reconstruction.latest_decision.steering_outcome
            is SteeringOutcome.HUMAN_ATTENTION
        ):
            raise SteeringInvariantViolation(
                "Current PRODUCE Step is stopped at unresolved Human Attention"
            )
        inbound = next(
            (
                event
                for event in reversed(reconstruction.history)
                if event.to_step_id == step.id and event.steering_decision_id is not None
            ),
            None,
        )
        if (
            (inbound is None or inbound.steering_decision_id is None)
            and step.position != 1
        ):
            raise SteeringInvariantViolation(
                "Current PRODUCE Step has no admitted Steering Decision provenance"
            )
        steering_decision_id = (
            None if inbound is None else inbound.steering_decision_id
        )

        baseline = self.runtime.current_baseline()
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            work = product.work(work_id)
            scope = product.scope_for_work(work_id)
            if work is None or scope is None:
                raise ProductInvariantViolation("Work authority envelope is incomplete")
            if (
                scope.condition is not EngineeringScopeCondition.ADMITTED
                or len(scope.bindings) != 1
            ):
                raise ProductInvariantViolation(
                    "Steering production requires one admitted Engineering Resource"
                )
            resource = product.resource(scope.bindings[0].resource_id)
            if resource is None:
                raise ProductInvariantViolation("Admitted Engineering Resource is missing")
            if (
                baseline.repository_identity != resource.repository_identity
                or baseline.repository_ref != resource.authoritative_ref
            ):
                raise ProductInvariantViolation(
                    "Current Trusted Baseline is outside the admitted Engineering Resource"
                )
            plan = work.production_plan
            if plan is None:
                raise ProductInvariantViolation("Admitted Work has no Production Plan")

            artifact_targets: tuple[ProductionPlanArtifactTarget, ...] = ()
            change_contract = None
            if plan.target_kind is ProductionTargetKind.DOCUMENTATION_WORK:
                admitted = plan.artifact_targets
                if len(admitted) != 1:
                    raise ProductInvariantViolation(
                        "Documentation Work requires one exact admitted artifact"
                    )
                target = admitted[0]
                artifact_targets = (
                    ProductionPlanArtifactTarget(
                        path=target.path,
                        operation=(
                            PlannedArtifactOperation.UPDATE
                            if self._path_exists(resource.location_ref, baseline.repository_revision, target.path)
                            else PlannedArtifactOperation.CREATE
                        ),
                    ),
                )
            else:
                admitted_contract = plan.change_contract
                if admitted_contract is None and plan.change_proposal is not None:
                    admitted_contract = WorkApplicationService._admit_change_contract(
                        plan.change_proposal,
                        desired_outcome=(
                            work.desired_outcome or work.raw_user_requirement
                        ),
                        constraints=work.constraints,
                    )
                if admitted_contract is None:
                    raise ProductInvariantViolation(
                        "Code Work has no Human-admitted Change Contract"
                    )
                targets = tuple(
                    CodeChangeTarget(
                        path=target.path,
                        operation=(
                            ChangeOperation.UPDATE
                            if self._path_exists(
                                resource.location_ref,
                                baseline.repository_revision,
                                target.path,
                            )
                            else ChangeOperation.CREATE
                        ),
                    )
                    for target in admitted_contract.exact_targets
                )
                change_contract = admitted_contract.model_copy(
                    update={
                        "source_baseline_id": baseline.id,
                        "source_revision": baseline.repository_revision,
                        "exact_targets": targets,
                    }
                )

            return SteeringProductionRequest(
                work_id=work.id,
                steering_step_id=step.id,
                steering_decision_id=steering_decision_id,
                production_objective=step.objective,
                target_kind=plan.target_kind,
                engineering_scope_id=scope.id,
                engineering_resource_id=resource.id,
                repository_identity=resource.repository_identity,
                source_baseline_id=baseline.id,
                source_revision=baseline.repository_revision,
                artifact_targets=artifact_targets,
                change_contract=change_contract,
                constraints=work.constraints,
                verification_expectation=work.verification_expectation or "",
            )

    def admit_cycle(
        self,
        request: SteeringProductionRequest,
        *,
        authority_identity: str = "steering:auto-within-work-authority",
    ) -> SteeringProductionAdmission:
        expected = self.materialize_request(request.work_id)
        violations = self._authority_violations(expected, request)
        if violations:
            decision = self._record_authority_attention(request.work_id, violations)
            return SteeringProductionAdmission(
                request=request,
                attention_decision_id=decision.id,
            )

        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            existing = product.runtime_binding_for_step(request.steering_step_id)
            if existing is not None:
                return SteeringProductionAdmission(request=request, binding=existing)
            bindings = product.runtime_bindings(request.work_id)
            adoptable = (
                bindings[0]
                if len(bindings) == 1
                and bindings[0].cycle_number == 1
                and bindings[0].steering_step_id is None
                else None
            )
            if adoptable is not None:
                run = RuntimeStore(unit_of_work.session).run(adoptable.production_run_id)
                if (
                    run is not None
                    and run.source_baseline_id == request.source_baseline_id
                    and adoptable.engineering_scope_id == request.engineering_scope_id
                    and adoptable.resource_id == request.engineering_resource_id
                ):
                    product.associate_runtime_binding(
                        adoptable.id,
                        steering_step_id=request.steering_step_id,
                        steering_decision_id=request.steering_decision_id,
                    )
                    unit_of_work.commit()
                    with self.database.unit_of_work() as refreshed:
                        binding = ProductStore(refreshed.session).runtime_binding_for_step(
                            request.steering_step_id
                        )
                    assert binding is not None
                    return SteeringProductionAdmission(request=request, binding=binding)

        plan, completion_contract, horizon, objective = self._production_contract(request)
        spine = self.runtime.create_initial_runtime_spine(
            InitialRunRequest(
                intent_ref=f"work:{request.work_id}:steering-step:{request.steering_step_id}",
                goal=request.production_objective,
                production_horizon=horizon,
                initial_work_unit_objective=objective,
                completion_contract=completion_contract,
            )
        )
        timestamp = datetime.now(UTC)
        governance_id = uuid5(
            NAMESPACE_URL,
            f"spg:steering-production:{request.steering_step_id}:{spine.run.id}",
        )
        binding_id = uuid4()
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            if product.runtime_binding_for_step(request.steering_step_id) is not None:
                raise SteeringInvariantViolation(
                    "Steering PRODUCE Step already has an admitted production cycle"
                )
            cycle_number = len(product.runtime_bindings(request.work_id)) + 1
            runtime.insert_governance(
                {
                    "id": governance_id,
                    "decision_type": "AUTO_ADMIT_STEERING_PRODUCE",
                    "authority_identity": authority_identity,
                    "subject_type": "STEERING_PRODUCE_STEP",
                    "subject_identity": str(request.steering_step_id),
                    "scope": {
                        "work_id": str(request.work_id),
                        "steering_decision_id": (
                            None
                            if request.steering_decision_id is None
                            else str(request.steering_decision_id)
                        ),
                        "production_run_id": str(spine.run.id),
                        "plan_revision_id": str(spine.plan_revision.id),
                        "work_unit_id": str(spine.work_unit.id),
                        "production_plan_proposal_id": str(plan.proposal_id),
                    },
                    "rationale": "Exact production request remained inside admitted Work authority",
                    "created_at": timestamp,
                }
            )
            product.insert_runtime_binding(
                {
                    "id": binding_id,
                    "work_id": request.work_id,
                    "cycle_number": cycle_number,
                    "steering_step_id": request.steering_step_id,
                    "steering_decision_id": request.steering_decision_id,
                    "engineering_scope_id": request.engineering_scope_id,
                    "resource_id": request.engineering_resource_id,
                    "production_run_id": spine.run.id,
                    "plan_revision_id": spine.plan_revision.id,
                    "work_unit_id": spine.work_unit.id,
                    "governance_record_id": governance_id,
                    "admitted_by": authority_identity,
                    "condition": ProductionCycleBindingCondition.ADMITTED.value,
                    "created_at": timestamp,
                }
            )
            unit_of_work.commit()
        with self.database.unit_of_work() as unit_of_work:
            binding = ProductStore(unit_of_work.session).runtime_binding_for_step(
                request.steering_step_id
            )
        assert binding is not None
        return SteeringProductionAdmission(request=request, binding=binding)

    def _production_contract(self, request: SteeringProductionRequest):
        baseline = self.runtime.current_baseline()
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            work = product.work(request.work_id)
            scope = product.scope_for_work(request.work_id)
            resource = product.resource(request.engineering_resource_id)
        if work is None or scope is None or resource is None:
            raise ProductInvariantViolation("Work authority envelope disappeared")
        plan = self.planning.propose(
            ProductionPlanningRequest(
                work_id=work.id,
                target_kind=request.target_kind,
                admitted_requirement=request.production_objective,
                desired_outcome=work.desired_outcome or work.raw_user_requirement,
                production_objective=request.production_objective,
                artifact_targets=request.artifact_targets,
                change_contract=request.change_contract,
                constraints=request.constraints,
                verification_expectation=request.verification_expectation,
                engineering_scope_summary=scope.summary,
                engineering_resource_id=resource.id,
                repository_identity=resource.repository_identity,
                source_baseline_id=baseline.id,
                source_revision=baseline.repository_revision,
                context_references=tuple(
                    item.repository_relative_path for item in resource.context_references
                ),
            )
        )
        if plan.fit_classification is not OnePwuFitClassification.ONE_PWU_FIT:
            raise ProductInvariantViolation(
                "Individual Steering PRODUCE Step is not ONE_PWU_FIT"
            )
        if request.target_kind is ProductionTargetKind.DOCUMENTATION_WORK:
            target = request.artifact_targets[0]
            artifact = ArtifactContract(
                engineering_resource_id=resource.id,
                repository_identity=resource.repository_identity,
                source_baseline_id=baseline.id,
                source_revision=baseline.repository_revision,
                artifact_path=target.path,
                operation=ArtifactOperation(target.operation.value),
                constraints=request.constraints,
                expected_outcome=work.desired_outcome or work.raw_user_requirement,
                verification_obligation=request.verification_expectation,
            )
            completion = CompletionContract(
                required_outputs=(target.path,),
                required_changes=(target.path,),
                verification_obligations=(request.verification_expectation,),
                artifact_contract=artifact,
                production_plan=plan,
            )
            return (
                plan,
                completion,
                ProductionHorizon.DOCUMENTATION,
                WorkApplicationService._artifact_objective(artifact),
            )
        contract = request.change_contract
        assert contract is not None
        paths = tuple(target.path for target in contract.exact_targets)
        completion = CompletionContract(
            required_outputs=paths,
            required_changes=paths,
            verification_obligations=contract.verification_identities,
            change_contract=contract,
            production_plan=plan,
        )
        return (
            plan,
            completion,
            ProductionHorizon.CODE,
            WorkApplicationService._code_change_objective(contract),
        )

    @staticmethod
    def _authority_violations(
        expected: SteeringProductionRequest,
        proposed: SteeringProductionRequest,
    ) -> tuple[str, ...]:
        expected_payload = expected.model_dump(mode="json")
        proposed_payload = proposed.model_dump(mode="json")
        return tuple(
            f"{field} differs from the persisted Work authority envelope"
            for field in expected_payload
            if expected_payload[field] != proposed_payload.get(field)
        )

    def _record_authority_attention(
        self,
        work_id: UUID,
        violations: tuple[str, ...],
    ):
        frame = PlanFrameAssembler(self.database).assemble(work_id)
        refs = tuple(item.reference for item in frame.basis.resolved_reality)
        candidate = NextStepCandidate(
            type=SteeringStepType.HUMAN_DECISION,
            objective="Resolve the requested production authority expansion",
            reason="; ".join(violations),
            reality_refs=refs,
            human_required=True,
            completion_condition="Human Authority explicitly admits or narrows the production boundary",
            proposed_outcome=SteeringOutcome.HUMAN_ATTENTION,
            basis_fingerprint=frame.basis.fingerprint,
            authority_assessment=SteeringAuthorityAssessment.EXPANDS_AUTHORITY,
            proposed_engineering_scope_fingerprint=frame.engineering_scope_fingerprint,
            attention_reason=SteeringAttentionReason.SCOPE_OR_AUTHORITY_EXPANSION,
            recommendation="Keep production inside the existing admitted Work envelope",
            alternatives=("Revise the governed Work authority explicitly",),
            trade_offs=("Expanded authority requires a new explicit Human decision",),
            expected_impact="No SPG production lineage is created before authority is explicit",
            reasoning_provider_identity="provider-free:authority-validator",
        )
        return SteeringDecisionApplicationService(
            self.database,
            DeterministicPlanSteeringCapability(),
        ).admit(work_id, candidate)

    @staticmethod
    def _path_exists(location_ref: str, revision: str, path: str) -> bool:
        result = subprocess.run(
            ["git", "-C", str(Path(location_ref).resolve()), "cat-file", "-e", f"{revision}:{path}"],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
