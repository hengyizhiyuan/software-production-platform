"""Application boundary for persisted long-lived Steering Plan truth."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from uuid import UUID, uuid4

from spg.domain.product import ProductionCycleBindingCondition, WorkCondition
from spg.domain.steering import (
    AdmitSteeringDecisionRequest,
    CreateSteeringPlanRequest,
    ElaborateSteeringStepRequest,
    RealityReference,
    RealityReferenceKind,
    ReviseSteeringPlanRequest,
    SteeringDecisionRecord,
    SteeringDecisionBasis,
    SteeringHistoryEventType,
    SteeringInvariantViolation,
    SteeringOutcome,
    SteeringPlanReconstruction,
    SteeringPlanRevisionCondition,
    SteeringPlanRevisionRecord,
    SteeringPlanRevisionView,
    SteeringRecordNotFound,
    SteeringStepRecord,
    SteeringStepSpec,
    SteeringStepState,
    SteeringStepType,
    TransitionSteeringStepRequest,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.steering_store import SteeringStore


class SteeringApplicationService:
    """Admit and reconstruct Steering truth without invoking a model or SPG."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def create_plan(
        self,
        request: CreateSteeringPlanRequest,
    ) -> SteeringPlanReconstruction:
        self._validate_step_specs(request.steps)
        timestamp = datetime.now(UTC)
        plan_id, revision_id = uuid4(), uuid4()
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            store = SteeringStore(unit_of_work.session)
            work = product.work(request.work_id)
            if work is None:
                raise SteeringRecordNotFound(f"Work not found: {request.work_id}")
            if work.condition is not WorkCondition.READY:
                raise SteeringInvariantViolation(
                    "A Steering Plan requires an admitted READY Work"
                )
            if store.plan_for_work(work.id) is not None:
                raise SteeringInvariantViolation("Work already has a Steering Plan")
            refs = self._normalize_refs(
                (
                    RealityReference(
                        kind=RealityReferenceKind.WORK,
                        identity=work.id,
                    ),
                    *request.reality_refs,
                )
            )
            self._validate_reality_refs(store, refs)
            store.insert_plan(
                {"id": plan_id, "work_id": work.id, "created_at": timestamp}
            )
            store.insert_revision(
                {
                    "id": revision_id,
                    "steering_plan_id": plan_id,
                    "work_id": work.id,
                    "revision_number": 1,
                    "condition": SteeringPlanRevisionCondition.ACTIVE.value,
                    "supersedes_revision_id": None,
                    "rationale": request.rationale,
                    "reality_refs": self._dump_refs(refs),
                    "created_at": timestamp,
                }
            )
            self._insert_steps(store, revision_id, request.steps, timestamp=timestamp)
            unit_of_work.commit()
        return self.reconstruct(request.work_id)

    def decision_basis_fingerprint(
        self,
        steering_plan_revision_id: UUID,
        current_step_id: UUID,
        reality_refs: tuple[RealityReference, ...],
    ) -> str:
        return self.decision_basis(
            steering_plan_revision_id,
            current_step_id,
            reality_refs,
        ).fingerprint

    def decision_basis(
        self,
        steering_plan_revision_id: UUID,
        current_step_id: UUID,
        reality_refs: tuple[RealityReference, ...],
    ) -> SteeringDecisionBasis:
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            store = SteeringStore(unit_of_work.session)
            revision = self._required_active_revision(
                store, steering_plan_revision_id
            )
            step = self._required_step(store, current_step_id)
            self._validate_current_step(revision, step)
            refs = self._normalize_refs(reality_refs)
            self._validate_reality_refs(store, refs)
            work = product.work(revision.work_id)
            if work is None:
                raise SteeringRecordNotFound(f"Work not found: {revision.work_id}")
            scope = product.scope_for_work(work.id)
            return self._basis(work, scope, revision, step, store, refs)

    def admit_decision(
        self,
        request: AdmitSteeringDecisionRequest,
    ) -> SteeringDecisionRecord:
        timestamp = datetime.now(UTC)
        decision_id = uuid4()
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            store = SteeringStore(unit_of_work.session)
            revision = self._required_active_revision(
                store, request.steering_plan_revision_id
            )
            step = self._required_step(store, request.current_step_id)
            self._validate_current_step(revision, step)
            refs = self._normalize_refs(request.reality_refs)
            self._validate_reality_refs(store, refs)
            work = product.work(revision.work_id)
            if work is None:
                raise SteeringRecordNotFound(f"Work not found: {revision.work_id}")
            scope = product.scope_for_work(work.id)
            fingerprint = self._basis(
                work,
                scope,
                revision,
                step,
                store,
                refs,
            ).fingerprint
            if fingerprint != request.expected_basis_fingerprint:
                raise SteeringInvariantViolation(
                    "Steering Decision basis is stale or does not match governed Reality"
                )
            self._validate_outcome(
                request.steering_outcome,
                request.next_step_type,
                request.human_required,
            )
            store.insert_decision(
                {
                    "id": decision_id,
                    "steering_plan_revision_id": revision.id,
                    "current_step_id": step.id,
                    "next_step_type": request.next_step_type.value,
                    "objective": request.objective,
                    "reason": request.reason,
                    "reality_refs": self._dump_refs(refs),
                    "human_required": request.human_required,
                    "completion_condition": request.completion_condition,
                    "steering_outcome": request.steering_outcome.value,
                    "basis_fingerprint": fingerprint,
                    "reasoning_provider_identity": request.reasoning_provider_identity,
                    "attention_reason": (
                        None
                        if request.attention_reason is None
                        else request.attention_reason.value
                    ),
                    "recommendation": request.recommendation,
                    "alternatives": list(request.alternatives),
                    "trade_offs": list(request.trade_offs),
                    "expected_impact": request.expected_impact,
                    "authority_assessment": (
                        None
                        if request.authority_assessment is None
                        else request.authority_assessment.value
                    ),
                    "proposed_engineering_scope_fingerprint": (
                        request.proposed_engineering_scope_fingerprint
                    ),
                    "created_at": timestamp,
                }
            )
            result = store.decision(decision_id)
            unit_of_work.commit()
        if result is None:
            raise SteeringInvariantViolation("Steering Decision was not constructed")
        return result

    def transition_step(
        self,
        request: TransitionSteeringStepRequest,
    ) -> SteeringPlanReconstruction:
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            store = SteeringStore(unit_of_work.session)
            revision = self._required_active_revision(
                store, request.steering_plan_revision_id
            )
            current = self._required_step(store, request.current_step_id)
            next_step = self._required_step(store, request.next_step_id)
            self._validate_current_step(revision, current)
            if (
                next_step.steering_plan_revision_id != revision.id
                or next_step.state is not SteeringStepState.KNOWN
            ):
                raise SteeringInvariantViolation(
                    "Next Steering Step must be KNOWN in the active revision"
                )
            eligible = tuple(
                step
                for step in store.steps(revision.id)
                if step.state is SteeringStepState.KNOWN
                and step.position > current.position
            )
            if not eligible or eligible[0].id != next_step.id:
                raise SteeringInvariantViolation(
                    "Steering transition must select the next ordered Step"
                )
            decision = store.decision(request.steering_decision_id)
            if decision is None:
                raise SteeringRecordNotFound(
                    f"Steering Decision not found: {request.steering_decision_id}"
                )
            allowed_outcome = (
                SteeringOutcome.COMPLETE
                if next_step.type is SteeringStepType.COMPLETE
                else SteeringOutcome.AUTO_CONTINUE
            )
            if (
                decision.steering_plan_revision_id != revision.id
                or decision.current_step_id != current.id
                or decision.next_step_type is not next_step.type
                or decision.objective != next_step.objective
                or decision.completion_condition != next_step.completion_condition
                or decision.steering_outcome is not allowed_outcome
            ):
                raise SteeringInvariantViolation(
                    "Steering Decision does not admit the requested Step transition"
                )
            if current.type is SteeringStepType.PRODUCE:
                binding = product.runtime_binding_for_step(current.id)
                if binding is None:
                    raise SteeringInvariantViolation(
                        "PRODUCE Step has no associated SPG production cycle"
                    )
                required_refs = self._trusted_production_refs(
                    product,
                    runtime,
                    binding,
                )
                if not set(required_refs) <= set(decision.reality_refs):
                    raise SteeringInvariantViolation(
                        "PRODUCE Step close Decision lacks exact trusted production Reality"
                    )
                product.set_runtime_binding_condition(
                    binding.id,
                    ProductionCycleBindingCondition.TRUSTED,
                )
            elif next_step.type is SteeringStepType.COMPLETE:
                binding = product.runtime_binding(revision.work_id)
                if binding is None:
                    raise SteeringInvariantViolation(
                        "COMPLETE transition has no trusted SPG production cycle"
                    )
                required_refs = self._trusted_production_refs(
                    product,
                    runtime,
                    binding,
                )
                if not set(required_refs) <= set(decision.reality_refs):
                    raise SteeringInvariantViolation(
                        "COMPLETE transition lacks exact trusted production Reality"
                    )
            store.set_step_state(current.id, SteeringStepState.CLOSED)
            store.set_step_state(next_step.id, SteeringStepState.CURRENT)
            store.insert_history(
                {
                    "id": uuid4(),
                    "steering_plan_id": revision.steering_plan_id,
                    "steering_plan_revision_id": revision.id,
                    "event_type": SteeringHistoryEventType.STEP_TRANSITION.value,
                    "from_revision_id": None,
                    "to_revision_id": None,
                    "from_step_id": current.id,
                    "to_step_id": next_step.id,
                    "steering_decision_id": decision.id,
                    "related_step_ids": [],
                    "rationale": decision.reason,
                    "reality_refs": self._dump_refs(decision.reality_refs),
                    "created_at": timestamp,
                }
            )
            work_id = revision.work_id
            unit_of_work.commit()
        return self.reconstruct(work_id)

    @staticmethod
    def _trusted_production_refs(product, runtime, binding):
        summary = product.runtime_summary(binding)
        required_values = (
            summary.completion_id,
            summary.candidate_id,
            summary.authorization_id,
            summary.integration_effect_id,
            summary.runtime_commit_id,
        )
        if (
            any(value is None for value in required_values)
            or summary.completion_outcome != "PRODUCED"
            or not summary.verification_results
            or any(result != "PASS" for result in summary.verification_results)
            or summary.integration_state != "CONVERGED"
        ):
            raise SteeringInvariantViolation(
                "PRODUCE Step cannot close without trusted SPG evidence"
            )
        commit = runtime.runtime_commit(summary.runtime_commit_id)
        pointer = runtime.current_pointer()
        if (
            commit is None
            or pointer is None
            or commit.production_run_id != binding.production_run_id
            or commit.plan_revision_id != binding.plan_revision_id
            or binding.work_unit_id not in commit.satisfied_work_unit_ids
            or pointer.snapshot_id != commit.new_baseline_id
        ):
            raise SteeringInvariantViolation(
                "Runtime Commit is not the exact current trusted production result"
            )
        verification = runtime.verification_records_for_snapshot(
            summary.proposed_snapshot_id
        )
        refs = [
            RealityReference(
                kind=RealityReferenceKind.COMPLETION,
                identity=summary.completion_id,
            ),
            *(
                RealityReference(
                    kind=RealityReferenceKind.VERIFICATION,
                    identity=item.id,
                )
                for item in verification
            ),
            RealityReference(
                kind=RealityReferenceKind.CANDIDATE,
                identity=summary.candidate_id,
            ),
            RealityReference(
                kind=RealityReferenceKind.AUTHORIZATION,
                identity=summary.authorization_id,
            ),
            RealityReference(
                kind=RealityReferenceKind.INTEGRATION_EFFECT,
                identity=summary.integration_effect_id,
            ),
            RealityReference(
                kind=RealityReferenceKind.RUNTIME_COMMIT,
                identity=summary.runtime_commit_id,
            ),
            RealityReference(
                kind=RealityReferenceKind.TRUSTED_BASELINE,
                identity=commit.new_baseline_id,
            ),
        ]
        return tuple(refs)

    def elaborate_step(
        self,
        request: ElaborateSteeringStepRequest,
    ) -> SteeringPlanReconstruction:
        self._validate_step_specs(request.replacements, allow_current=False)
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = SteeringStore(unit_of_work.session)
            revision = self._required_active_revision(
                store, request.steering_plan_revision_id
            )
            original = self._required_step(store, request.step_id)
            if (
                original.steering_plan_revision_id != revision.id
                or original.state
                not in {SteeringStepState.KNOWN, SteeringStepState.CURRENT}
            ):
                raise SteeringInvariantViolation(
                    "Only a KNOWN or CURRENT Step in the active revision may be elaborated"
                )
            refs = self._normalize_refs(request.reality_refs)
            self._validate_reality_refs(store, refs)
            store.set_step_state(original.id, SteeringStepState.SUPERSEDED)
            store.shift_active_steps_after(
                revision.id,
                original.position,
                len(request.replacements) - 1,
            )
            child_ids: list[UUID] = []
            for offset, spec in enumerate(request.replacements):
                child_id = uuid4()
                child_ids.append(child_id)
                state = (
                    SteeringStepState.CURRENT
                    if original.state is SteeringStepState.CURRENT and offset == 0
                    else SteeringStepState.KNOWN
                )
                store.insert_step(
                    {
                        "id": child_id,
                        "steering_plan_revision_id": revision.id,
                        "type": spec.type.value,
                        "objective": spec.objective,
                        "completion_condition": spec.completion_condition,
                        "position": original.position + offset,
                        "state": state.value,
                        "elaborates_step_id": original.id,
                        "created_at": timestamp,
                    }
                )
            store.insert_history(
                {
                    "id": uuid4(),
                    "steering_plan_id": revision.steering_plan_id,
                    "steering_plan_revision_id": revision.id,
                    "event_type": SteeringHistoryEventType.STEP_ELABORATION.value,
                    "from_revision_id": None,
                    "to_revision_id": None,
                    "from_step_id": original.id,
                    "to_step_id": child_ids[0],
                    "steering_decision_id": None,
                    "related_step_ids": [str(item) for item in child_ids],
                    "rationale": request.rationale,
                    "reality_refs": self._dump_refs(refs),
                    "created_at": timestamp,
                }
            )
            work_id = revision.work_id
            unit_of_work.commit()
        return self.reconstruct(work_id)

    def revise_plan(
        self,
        request: ReviseSteeringPlanRequest,
    ) -> SteeringPlanReconstruction:
        self._validate_step_specs(request.steps)
        timestamp = datetime.now(UTC)
        new_revision_id = uuid4()
        with self.database.unit_of_work() as unit_of_work:
            store = SteeringStore(unit_of_work.session)
            plan = store.plan(request.steering_plan_id)
            if plan is None:
                raise SteeringRecordNotFound(
                    f"Steering Plan not found: {request.steering_plan_id}"
                )
            active = store.active_revision(plan.id)
            if active is None or active.id != request.superseded_revision_id:
                raise SteeringInvariantViolation(
                    "Material revision must supersede the exact active Steering revision"
                )
            refs = self._normalize_refs(request.reality_refs)
            self._validate_reality_refs(store, refs)
            store.supersede_revision(active.id)
            store.insert_revision(
                {
                    "id": new_revision_id,
                    "steering_plan_id": plan.id,
                    "work_id": plan.work_id,
                    "revision_number": active.revision_number + 1,
                    "condition": SteeringPlanRevisionCondition.ACTIVE.value,
                    "supersedes_revision_id": active.id,
                    "rationale": request.rationale,
                    "reality_refs": self._dump_refs(refs),
                    "created_at": timestamp,
                }
            )
            self._insert_steps(store, new_revision_id, request.steps, timestamp=timestamp)
            store.insert_history(
                {
                    "id": uuid4(),
                    "steering_plan_id": plan.id,
                    "steering_plan_revision_id": new_revision_id,
                    "event_type": SteeringHistoryEventType.PLAN_REVISION.value,
                    "from_revision_id": active.id,
                    "to_revision_id": new_revision_id,
                    "from_step_id": None,
                    "to_step_id": None,
                    "steering_decision_id": None,
                    "related_step_ids": [],
                    "rationale": request.rationale,
                    "reality_refs": self._dump_refs(refs),
                    "created_at": timestamp,
                }
            )
            unit_of_work.commit()
        return self.reconstruct(plan.work_id)

    def reconstruct(self, work_id: UUID) -> SteeringPlanReconstruction:
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            store = SteeringStore(unit_of_work.session)
            work = product.work(work_id)
            if work is None:
                raise SteeringRecordNotFound(f"Work not found: {work_id}")
            plan = store.plan_for_work(work_id)
            if plan is None:
                raise SteeringRecordNotFound(
                    f"Work has no Steering Plan: {work_id}"
                )
            active = store.active_revision(plan.id)
            if active is None:
                raise SteeringInvariantViolation("Steering Plan has no active revision")
            revisions = store.revisions(plan.id)
            lineage = tuple(
                SteeringPlanRevisionView(
                    revision=revision,
                    steps=store.steps(revision.id),
                )
                for revision in revisions
            )
            active_steps = store.steps(active.id)
            current = next(
                (
                    step
                    for step in active_steps
                    if step.state is SteeringStepState.CURRENT
                ),
                None,
            )
            known = tuple(
                step
                for step in active_steps
                if step.state is SteeringStepState.KNOWN
            )
            next_step = next(
                (
                    step
                    for step in known
                    if current is None or step.position > current.position
                ),
                None,
            )
            completed = tuple(
                step
                for view in lineage
                for step in view.steps
                if step.state is SteeringStepState.CLOSED
            )
            objective = (
                work.production_objective
                or work.desired_outcome
                or work.refined_title
                or work.raw_user_requirement
            )
            return SteeringPlanReconstruction(
                work_id=work.id,
                work_objective=objective,
                steering_plan_id=plan.id,
                active_revision=SteeringPlanRevisionView(
                    revision=active,
                    steps=active_steps,
                ),
                revision_lineage=lineage,
                completed_steps=completed,
                current_step=current,
                known_future_steps=known,
                next_step=next_step,
                latest_decision=store.latest_decision_for_plan(plan.id),
                history=store.history(plan.id),
                has_material_revision=len(revisions) > 1,
            )

    @staticmethod
    def _validate_step_specs(
        specs: tuple[SteeringStepSpec, ...],
        *,
        allow_current: bool = True,
    ) -> None:
        current_count = sum(
            spec.state is SteeringStepState.CURRENT for spec in specs
        )
        if current_count > 1:
            raise SteeringInvariantViolation(
                "A Steering Plan Revision may have at most one CURRENT Step"
            )
        if not allow_current and current_count:
            raise SteeringInvariantViolation(
                "Elaboration replacement state is derived from the original Step"
            )
        if any(
            spec.state
            in {SteeringStepState.CLOSED, SteeringStepState.SUPERSEDED}
            for spec in specs
        ):
            raise SteeringInvariantViolation(
                "Newly admitted Steps must be KNOWN or CURRENT"
            )

    @staticmethod
    def _required_active_revision(
        store: SteeringStore,
        revision_id: UUID,
    ) -> SteeringPlanRevisionRecord:
        revision = store.revision(revision_id)
        if revision is None:
            raise SteeringRecordNotFound(
                f"Steering Plan Revision not found: {revision_id}"
            )
        active = store.active_revision(revision.steering_plan_id)
        if (
            revision.condition is not SteeringPlanRevisionCondition.ACTIVE
            or active is None
            or active.id != revision.id
        ):
            raise SteeringInvariantViolation(
                "Steering operation requires the exact active Plan revision"
            )
        return revision

    @staticmethod
    def _required_step(store: SteeringStore, step_id: UUID) -> SteeringStepRecord:
        step = store.step(step_id)
        if step is None:
            raise SteeringRecordNotFound(f"Steering Step not found: {step_id}")
        return step

    @staticmethod
    def _validate_current_step(
        revision: SteeringPlanRevisionRecord,
        step: SteeringStepRecord,
    ) -> None:
        if (
            step.steering_plan_revision_id != revision.id
            or step.state is not SteeringStepState.CURRENT
        ):
            raise SteeringInvariantViolation(
                "Steering Decision requires the exact CURRENT Step"
            )

    @staticmethod
    def _validate_outcome(
        outcome: SteeringOutcome,
        next_step_type: SteeringStepType,
        human_required: bool,
    ) -> None:
        if (outcome is SteeringOutcome.HUMAN_ATTENTION) != human_required:
            raise SteeringInvariantViolation(
                "Human requirement must match the Steering outcome"
            )
        if (outcome is SteeringOutcome.COMPLETE) != (
            next_step_type is SteeringStepType.COMPLETE
        ):
            raise SteeringInvariantViolation(
                "COMPLETE outcome and COMPLETE Next Step must agree"
            )

    @staticmethod
    def _normalize_refs(
        references: tuple[RealityReference, ...],
    ) -> tuple[RealityReference, ...]:
        return tuple(
            RealityReference(kind=kind, identity=identity)
            for kind, identity in sorted(
                {(item.kind, item.identity) for item in references},
                key=lambda item: (item[0].value, str(item[1])),
            )
        )

    @staticmethod
    def _validate_reality_refs(
        store: SteeringStore,
        references: tuple[RealityReference, ...],
    ) -> None:
        missing = tuple(
            reference
            for reference in references
            if not store.reality_reference_exists(reference)
        )
        if missing:
            rendered = ", ".join(
                f"{item.kind.value}:{item.identity}" for item in missing
            )
            raise SteeringInvariantViolation(
                f"Steering Reality reference does not exist: {rendered}"
            )

    @staticmethod
    def _dump_refs(references: tuple[RealityReference, ...]) -> list[dict[str, str]]:
        return [item.model_dump(mode="json") for item in references]

    @staticmethod
    def _insert_steps(
        store: SteeringStore,
        revision_id: UUID,
        specs: tuple[SteeringStepSpec, ...],
        *,
        timestamp: datetime,
    ) -> tuple[UUID, ...]:
        identities: list[UUID] = []
        for position, spec in enumerate(specs, start=1):
            step_id = uuid4()
            identities.append(step_id)
            store.insert_step(
                {
                    "id": step_id,
                    "steering_plan_revision_id": revision_id,
                    "type": spec.type.value,
                    "objective": spec.objective,
                    "completion_condition": spec.completion_condition,
                    "position": position,
                    "state": spec.state.value,
                    "elaborates_step_id": None,
                    "created_at": timestamp,
                }
            )
        return tuple(identities)

    @staticmethod
    def _basis(work, scope, revision, step, store, refs) -> SteeringDecisionBasis:
        """Canonicalize governed facts; exclude decision prose and provider output."""

        resolved = []
        for reference in refs:
            fact = store.resolve_reality_reference(reference)
            if fact is None:
                raise SteeringInvariantViolation(
                    "Steering Reality reference does not exist: "
                    f"{reference.kind.value}:{reference.identity}"
                )
            resolved.append(fact)

        payload = {
            "work": {
                "id": str(work.id),
                "mode": work.mode.value,
                "updated_at": work.updated_at.isoformat(),
                "raw_user_requirement": work.raw_user_requirement,
                "desired_outcome": work.desired_outcome,
                "production_objective": work.production_objective,
                "constraints": list(work.constraints),
            },
            "engineering_scope": (
                None
                if scope is None
                else {
                    "id": str(scope.id),
                    "fingerprint": scope.fingerprint,
                    "condition": scope.condition.value,
                    "bindings": [
                        {
                            "resource_id": str(binding.resource_id),
                            "condition": binding.condition.value,
                        }
                        for binding in scope.bindings
                    ],
                }
            ),
            "steering_plan_revision": {
                "id": str(revision.id),
                "revision_number": revision.revision_number,
            },
            "current_step": {
                "id": str(step.id),
                "type": step.type.value,
                "objective": step.objective,
                "completion_condition": step.completion_condition,
                "position": step.position,
                "state": step.state.value,
            },
            "reality_refs": [
                {
                    "kind": item.reference.kind.value,
                    "identity": str(item.reference.identity),
                    "material_fingerprint": item.material_fingerprint,
                }
                for item in resolved
            ],
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return SteeringDecisionBasis(
            canonical_representation=canonical,
            fingerprint=sha256(canonical.encode("utf-8")).hexdigest(),
            resolved_reality=tuple(resolved),
        )
