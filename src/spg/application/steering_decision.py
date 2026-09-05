"""Provider-neutral Plan Frame assembly and Steering decision admission."""

from __future__ import annotations

from uuid import UUID

from spg.application.steering import SteeringApplicationService
from spg.domain.product import EngineeringScopeCondition, WorkCondition
from spg.domain.steering import (
    AdmitSteeringDecisionRequest,
    NextStepCandidate,
    PlanFrame,
    PlanFrameBlocker,
    PlanFrameBlockerKind,
    PlanSteeringCapability,
    RealityReference,
    RealityReferenceKind,
    StaleSteeringCandidate,
    SteeringAttentionReason,
    SteeringAuthorityAssessment,
    SteeringDecisionRecord,
    SteeringInvariantViolation,
    SteeringOutcome,
    SteeringRecordNotFound,
    SteeringStepType,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore


class PlanFrameAssembler:
    """Assemble an ephemeral frame from existing authoritative stores."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.steering = SteeringApplicationService(database)

    def assemble(self, work_id: UUID) -> PlanFrame:
        reconstruction = self.steering.reconstruct(work_id)
        current = reconstruction.current_step
        if current is None:
            raise SteeringInvariantViolation(
                "Plan Frame requires one authoritative CURRENT Steering Step"
            )

        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            work = product.work(work_id)
            if work is None:
                raise SteeringRecordNotFound(f"Work not found: {work_id}")
            if work.condition is not WorkCondition.READY:
                raise SteeringInvariantViolation(
                    "Plan Frame requires the admitted READY Work Reality"
                )
            scope = product.scope_for_work(work_id)
            if (
                scope is None
                or work.engineering_scope_id != scope.id
                or scope.condition is not EngineeringScopeCondition.ADMITTED
                or len(scope.bindings) != 1
            ):
                raise SteeringInvariantViolation(
                    "Plan Frame requires the exact admitted Engineering Scope"
                )

            references = list(
                reconstruction.active_revision.revision.reality_refs
            )
            references.append(
                RealityReference(kind=RealityReferenceKind.WORK, identity=work.id)
            )
            if reconstruction.latest_decision is not None:
                references.extend(reconstruction.latest_decision.reality_refs)
            if reconstruction.history:
                references.extend(reconstruction.history[-1].reality_refs)

            governance_refs = tuple(
                RealityReference(
                    kind=RealityReferenceKind.GOVERNANCE_DECISION,
                    identity=record.id,
                )
                for record in runtime.governance_for_subject(str(work_id))
            )
            references.extend(governance_refs)

            pointer = runtime.current_pointer()
            if pointer is None:
                raise SteeringInvariantViolation(
                    "Plan Frame requires current Trusted Baseline Reality"
                )
            snapshot = runtime.snapshot(pointer.snapshot_id)
            resource = product.resource(scope.bindings[0].resource_id)
            if (
                snapshot is None
                or resource is None
                or snapshot.repository_identity != resource.repository_identity
                or snapshot.repository_ref != resource.authoritative_ref
            ):
                raise SteeringInvariantViolation(
                    "Plan Frame Trusted Baseline and Engineering Resource are inconsistent"
                )
            trusted_baseline_ref = RealityReference(
                kind=RealityReferenceKind.TRUSTED_BASELINE,
                identity=snapshot.id,
            )
            references.append(trusted_baseline_ref)

            runtime_refs: list[RealityReference] = []
            blockers: list[PlanFrameBlocker] = []
            completion_evidence_sufficient = False
            binding = product.runtime_binding(work_id)
            if binding is not None:
                summary = product.runtime_summary(binding)
                self._append_optional_ref(
                    runtime_refs,
                    RealityReferenceKind.REPOSITORY_OBSERVATION,
                    summary.observation_id,
                )
                completion_ref = self._append_optional_ref(
                    runtime_refs,
                    RealityReferenceKind.COMPLETION,
                    summary.completion_id,
                )
                verification_refs: tuple[RealityReference, ...] = ()
                if summary.proposed_snapshot_id is not None:
                    verification_refs = tuple(
                        RealityReference(
                            kind=RealityReferenceKind.VERIFICATION,
                            identity=record.id,
                        )
                        for record in runtime.verification_records_for_snapshot(
                            summary.proposed_snapshot_id
                        )
                    )
                    runtime_refs.extend(verification_refs)
                self._append_optional_ref(
                    runtime_refs,
                    RealityReferenceKind.CANDIDATE,
                    summary.candidate_id,
                )
                self._append_optional_ref(
                    runtime_refs,
                    RealityReferenceKind.AUTHORIZATION,
                    summary.authorization_id,
                )
                integration_ref = self._append_optional_ref(
                    runtime_refs,
                    RealityReferenceKind.INTEGRATION_EFFECT,
                    summary.integration_effect_id,
                )
                self._append_optional_ref(
                    runtime_refs,
                    RealityReferenceKind.RUNTIME_COMMIT,
                    summary.runtime_commit_id,
                )

                if summary.completion_outcome == "NOT_PRODUCED" and completion_ref:
                    blockers.append(
                        PlanFrameBlocker(
                            kind=PlanFrameBlockerKind.PRODUCTION_NOT_PRODUCED,
                            reason="Persisted Completion Reality is NOT_PRODUCED",
                            reality_refs=(completion_ref,),
                        )
                    )
                failing_verification_refs = tuple(
                    reference
                    for reference, result in zip(
                        verification_refs,
                        summary.verification_results,
                        strict=True,
                    )
                    if result != "PASS"
                )
                if failing_verification_refs:
                    blockers.append(
                        PlanFrameBlocker(
                            kind=PlanFrameBlockerKind.VERIFICATION_NOT_PASSING,
                            reason="Persisted Verification Reality is not fully PASS",
                            reality_refs=failing_verification_refs,
                        )
                    )
                if integration_ref and summary.integration_state != "CONVERGED":
                    blockers.append(
                        PlanFrameBlocker(
                            kind=(
                                PlanFrameBlockerKind.REPOSITORY_INTEGRATION_NOT_CONVERGED
                            ),
                            reason="Repository Integration Reality is not CONVERGED",
                            reality_refs=(integration_ref,),
                        )
                    )
                completion_evidence_sufficient = bool(
                    completion_ref
                    and summary.completion_outcome == "PRODUCED"
                    and verification_refs
                    and all(result == "PASS" for result in summary.verification_results)
                )
            references.extend(runtime_refs)

        normalized_refs = self._normalize_refs(tuple(references))
        basis = self.steering.decision_basis(
            reconstruction.active_revision.revision.id,
            current.id,
            normalized_refs,
        )
        return PlanFrame(
            work_id=work.id,
            work_objective=(
                work.production_objective
                or work.desired_outcome
                or work.refined_title
                or work.raw_user_requirement
            ),
            work_condition=work.condition.value,
            constraints=work.constraints,
            engineering_scope_id=scope.id,
            engineering_scope_condition=scope.condition.value,
            engineering_scope_fingerprint=scope.fingerprint,
            reconstruction=reconstruction,
            governance_decision_refs=governance_refs,
            trusted_baseline_ref=trusted_baseline_ref,
            runtime_reality_refs=self._normalize_refs(tuple(runtime_refs)),
            open_blocking_reality=tuple(blockers),
            completion_evidence_sufficient=completion_evidence_sufficient,
            basis=basis,
        )

    @staticmethod
    def _append_optional_ref(
        target: list[RealityReference],
        kind: RealityReferenceKind,
        identity: UUID | None,
    ) -> RealityReference | None:
        if identity is None:
            return None
        reference = RealityReference(kind=kind, identity=identity)
        target.append(reference)
        return reference

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


class DeterministicPlanSteeringCapability:
    """Narrow rule-assisted MVP capability for structurally obvious directions."""

    def evaluate(self, plan_frame: PlanFrame) -> NextStepCandidate:
        reconstruction = plan_frame.reconstruction
        current = reconstruction.current_step
        if current is None:
            raise SteeringInvariantViolation("Steering evaluation has no CURRENT Step")
        refs = tuple(item.reference for item in plan_frame.basis.resolved_reality)

        if (
            plan_frame.engineering_scope_condition
            != EngineeringScopeCondition.ADMITTED.value
        ):
            return self._attention(
                plan_frame,
                refs,
                reason=SteeringAttentionReason.SCOPE_OR_AUTHORITY_EXPANSION,
                objective="Resolve the governing authority for continued activity",
                rationale="The current Engineering Scope authority is uncertain",
                recommendation="Confirm or narrow the permitted Engineering Scope",
                impact="No production direction is admitted until authority is explicit",
                authority=SteeringAuthorityAssessment.UNCERTAIN,
            )

        next_step = reconstruction.next_step
        if plan_frame.completion_evidence_sufficient and (
            current.type is SteeringStepType.COMPLETE
            or (next_step is not None and next_step.type is SteeringStepType.COMPLETE)
        ):
            target = current if current.type is SteeringStepType.COMPLETE else next_step
            assert target is not None
            return NextStepCandidate(
                type=SteeringStepType.COMPLETE,
                objective=target.objective,
                reason=(
                    "Persisted Completion and Verification Reality prove the admitted "
                    "completion obligations"
                ),
                reality_refs=refs,
                human_required=False,
                completion_condition=target.completion_condition,
                proposed_outcome=SteeringOutcome.COMPLETE,
                basis_fingerprint=plan_frame.basis.fingerprint,
                authority_assessment=SteeringAuthorityAssessment.WITHIN_AUTHORITY,
            )

        if current.type is SteeringStepType.HUMAN_DECISION:
            return self._attention(
                plan_frame,
                refs,
                reason=SteeringAttentionReason.MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION,
                objective=current.objective,
                rationale=(
                    "The current admitted Step assigns a material direction choice to Human Authority"
                ),
                recommendation="Select the bounded direction that preserves the admitted Work objective",
                impact="The selected direction controls subsequent Steering",
                authority=SteeringAuthorityAssessment.UNCERTAIN,
            )

        if plan_frame.open_blocking_reality:
            return NextStepCandidate(
                type=current.type,
                objective=current.objective,
                reason=(
                    "Persisted blocking Reality identifies a bounded defect that can be "
                    "addressed inside the admitted authority"
                ),
                reality_refs=refs,
                human_required=False,
                completion_condition=current.completion_condition,
                proposed_outcome=SteeringOutcome.AUTO_CONTINUE,
                basis_fingerprint=plan_frame.basis.fingerprint,
                authority_assessment=SteeringAuthorityAssessment.WITHIN_AUTHORITY,
                proposed_engineering_scope_fingerprint=(
                    plan_frame.engineering_scope_fingerprint
                ),
            )

        if next_step is None:
            return self._attention(
                plan_frame,
                refs,
                reason=SteeringAttentionReason.PRODUCT_ACCEPTANCE_REQUIRED,
                objective="Decide whether the long-lived product outcome is accepted",
                rationale="No further admitted Step exists and completion is not yet proven",
                recommendation="Review the governed result against the Work outcome",
                impact="Acceptance determines whether Watt may form a COMPLETE decision",
                authority=SteeringAuthorityAssessment.WITHIN_AUTHORITY,
            )

        return NextStepCandidate(
            type=next_step.type,
            objective=next_step.objective,
            reason=(
                "The current governed Step is ready to yield to the next admitted ordered Step"
            ),
            reality_refs=refs,
            human_required=False,
            completion_condition=next_step.completion_condition,
            proposed_outcome=SteeringOutcome.AUTO_CONTINUE,
            basis_fingerprint=plan_frame.basis.fingerprint,
            authority_assessment=SteeringAuthorityAssessment.WITHIN_AUTHORITY,
            proposed_engineering_scope_fingerprint=(
                plan_frame.engineering_scope_fingerprint
                if next_step.type is SteeringStepType.PRODUCE
                else None
            ),
        )

    @staticmethod
    def _attention(
        plan_frame: PlanFrame,
        refs: tuple[RealityReference, ...],
        *,
        reason: SteeringAttentionReason,
        objective: str,
        rationale: str,
        recommendation: str,
        impact: str,
        authority: SteeringAuthorityAssessment,
    ) -> NextStepCandidate:
        return NextStepCandidate(
            type=SteeringStepType.HUMAN_DECISION,
            objective=objective,
            reason=rationale,
            reality_refs=refs,
            human_required=True,
            completion_condition="A governed Human decision resolves the material question",
            proposed_outcome=SteeringOutcome.HUMAN_ATTENTION,
            basis_fingerprint=plan_frame.basis.fingerprint,
            authority_assessment=authority,
            attention_reason=reason,
            recommendation=recommendation,
            expected_impact=impact,
        )


class SteeringDecisionApplicationService:
    """Validate advisory candidates and admit only current governed decisions."""

    def __init__(
        self,
        database: Database,
        capability: PlanSteeringCapability,
    ) -> None:
        self.database = database
        self.capability = capability
        self.frames = PlanFrameAssembler(database)
        self.steering = SteeringApplicationService(database)

    def evaluate(self, work_id: UUID) -> tuple[PlanFrame, NextStepCandidate]:
        frame = self.frames.assemble(work_id)
        candidate = self.capability.evaluate(frame)
        self._validate_candidate(frame, candidate)
        return frame, candidate

    def admit(
        self,
        work_id: UUID,
        candidate: NextStepCandidate,
    ) -> SteeringDecisionRecord:
        frame = self.frames.assemble(work_id)
        self._validate_candidate(frame, candidate)
        current = frame.reconstruction.current_step
        assert current is not None
        revision = frame.reconstruction.active_revision.revision
        return self.steering.admit_decision(
            AdmitSteeringDecisionRequest(
                steering_plan_revision_id=revision.id,
                current_step_id=current.id,
                next_step_type=candidate.type,
                objective=candidate.objective,
                reason=candidate.reason,
                reality_refs=candidate.reality_refs,
                human_required=candidate.human_required,
                completion_condition=candidate.completion_condition,
                steering_outcome=candidate.proposed_outcome,
                expected_basis_fingerprint=candidate.basis_fingerprint,
                reasoning_provider_identity=candidate.reasoning_provider_identity,
                attention_reason=candidate.attention_reason,
                recommendation=candidate.recommendation,
                alternatives=candidate.alternatives,
                trade_offs=candidate.trade_offs,
                expected_impact=candidate.expected_impact,
                authority_assessment=candidate.authority_assessment,
                proposed_engineering_scope_fingerprint=(
                    candidate.proposed_engineering_scope_fingerprint
                ),
            )
        )

    @staticmethod
    def _validate_candidate(frame: PlanFrame, candidate: NextStepCandidate) -> None:
        if candidate.basis_fingerprint != frame.basis.fingerprint:
            raise StaleSteeringCandidate("STALE_STEERING_CANDIDATE")
        expected_refs = tuple(item.reference for item in frame.basis.resolved_reality)
        if candidate.reality_refs != expected_refs:
            raise SteeringInvariantViolation(
                "Candidate must cite the exact governed Plan Frame Reality"
            )
        lowered_reason = " ".join(candidate.reason.casefold().split())
        if lowered_reason in {
            "the model thinks this is better",
            "the provider recommends this",
        }:
            raise SteeringInvariantViolation(
                "No material Next Step without Reality-grounded rationale"
            )

        current = frame.reconstruction.current_step
        next_step = frame.reconstruction.next_step
        assert current is not None
        if candidate.proposed_outcome is SteeringOutcome.AUTO_CONTINUE:
            expected_type = current.type if frame.open_blocking_reality else (
                None if next_step is None else next_step.type
            )
            if expected_type is None or candidate.type is not expected_type:
                raise SteeringInvariantViolation(
                    "AUTO_CONTINUE candidate contradicts the current linear Step lineage"
                )
        if candidate.proposed_outcome is SteeringOutcome.COMPLETE:
            if not frame.completion_evidence_sufficient:
                raise SteeringInvariantViolation(
                    "COMPLETE requires sufficient persisted Completion and Verification Reality"
                )
            if current.type is not SteeringStepType.COMPLETE and (
                next_step is None or next_step.type is not SteeringStepType.COMPLETE
            ):
                raise SteeringInvariantViolation(
                    "COMPLETE candidate contradicts the admitted Step lineage"
                )

        scope_mismatch = (
            candidate.proposed_engineering_scope_fingerprint is not None
            and candidate.proposed_engineering_scope_fingerprint
            != frame.engineering_scope_fingerprint
        )
        if scope_mismatch and candidate.proposed_outcome is not SteeringOutcome.HUMAN_ATTENTION:
            raise SteeringInvariantViolation(
                "Engineering Scope expansion cannot AUTO_CONTINUE"
            )
        if (
            candidate.type is SteeringStepType.PRODUCE
            and candidate.proposed_outcome is SteeringOutcome.AUTO_CONTINUE
            and candidate.proposed_engineering_scope_fingerprint
            != frame.engineering_scope_fingerprint
        ):
            raise SteeringInvariantViolation(
                "PRODUCE direction must bind the exact admitted Engineering Scope"
            )
        if (
            candidate.authority_assessment
            is SteeringAuthorityAssessment.EXPANDS_AUTHORITY
            and candidate.attention_reason
            is not SteeringAttentionReason.SCOPE_OR_AUTHORITY_EXPANSION
        ):
            raise SteeringInvariantViolation(
                "Authority expansion requires typed Scope/Authority Attention"
            )
