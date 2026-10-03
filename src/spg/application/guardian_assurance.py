"""Watt adapter for Guardian-owned software assurance truth.

Watt binds governed Work effects to the exact served Candidate and retains
only a gate projection. Guardian owns the request, observation and Findings.
"""

from __future__ import annotations

from hashlib import sha256
import json
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select

from spg.application.delivery import DeliveryApplicationService
from spg.domain.product import ProductInvariantViolation
from spg.domain.production_environment import CandidatePreviewSessionV1, PreviewRuntimeStatus
from spg.infrastructure.persistence.product_schema import product_works
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore


class GuardianAssuranceClient:
    """Submit immutable governed effects; consume an exact Guardian result."""

    def __init__(self, delivery: DeliveryApplicationService,
        preview_store: JsonProductionEnvironmentStore, guardian_store) -> None:
        self.delivery = delivery
        self.preview_store = preview_store
        self.guardian_store = guardian_store

    def bind_requirements(self, work_id: UUID, effects: list[dict], *,
        authority_identity: str) -> dict:
        from guardian.contracts.software_assurance import EffectRequirement

        if not authority_identity.strip():
            raise ProductInvariantViolation("Assurance requirements need an attributable governor")
        checked = tuple(EffectRequirement.model_validate(item) for item in effects)
        if not checked or len({item.obligation_ref for item in checked}) != len(checked):
            raise ProductInvariantViolation("Assurance requires distinct governed business effects")
        with self.delivery.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            work = product.work(work_id)
            if work is None:
                raise ProductInvariantViolation("Assurance requires an admitted Work")
            scope = product.scope_for_work(work_id)
            if scope is None or scope.id != work.engineering_scope_id:
                raise ProductInvariantViolation("Assurance requires the admitted Work scope")
            binding = product.runtime_binding(work_id)
            if binding is None or binding.governance_record_id is None:
                raise ProductInvariantViolation("Assurance requires Human-approved Runtime admission")
            if binding is not None and product.runtime_summary(binding).candidate_id is not None:
                raise ProductInvariantViolation("Assurance effects must be governed before Candidate sealing")
            basis_id = work.current_work_reality_revision_id or scope.id
            basis_ref = (f"work-reality-revision:{basis_id}"
                if work.current_work_reality_revision_id else f"approved-engineering-scope:{basis_id}")
            payload = {"work_id": str(work_id), "governed_basis_ref": basis_ref,
                "authority_ref": f"engineering-scope:{scope.id}",
                "admitted_by": authority_identity,
                "required_effects": [item.model_dump(mode="json") for item in checked]}
        return self.preview_store.admit_guardian_requirements(work_id, basis_id, payload)

    def assess_ready_preview(self, session: CandidatePreviewSessionV1) -> dict:
        from guardian.contracts.software_assurance import (
            AssuranceRequest, ProtectedContextEvidence,
        )

        if session.status is not PreviewRuntimeStatus.READY or not session.endpoint:
            raise ProductInvariantViolation("Guardian requires an exact READY Candidate Preview")
        existing = self.preview_store.guardian_projection(session.id)
        if existing is not None:
            return existing
        context = self.delivery.candidate_context(session.work_id)
        if (context is None or context["candidate_id"] != str(session.candidate_id)
                or context["candidate_fingerprint"] != session.candidate_fingerprint
                or context["repository_revision"] != session.repository_revision
                or context["tree"] != session.repository_tree):
            raise ProductInvariantViolation("Guardian request differs from the current sealed Candidate")
        with self.delivery.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            work = product.work(session.work_id)
            if work is None:
                raise ProductInvariantViolation("Guardian request lacks admitted Work")
            scope = product.scope_for_work(session.work_id)
            if scope is None or scope.id != work.engineering_scope_id:
                raise ProductInvariantViolation("Guardian request lacks admitted Work scope")
            basis_id = work.current_work_reality_revision_id or scope.id
            product_id = uow.session.execute(select(product_works.c.product_id).where(
                product_works.c.id == session.work_id)).scalar_one_or_none()
            objective, constraints = work.desired_outcome, tuple(work.constraints)
            binding = product.runtime_binding(session.work_id)
            task = None
            verification_records = ()
            if binding is not None and isinstance(getattr(binding, "work_unit_id", None), UUID):
                runtime = RuntimeStore(uow.session)
                work_unit = runtime.work_unit(binding.work_unit_id)
                if work_unit is None:
                    raise ProductInvariantViolation("Guardian requires current Task Contract lineage")
                task = (None if work_unit is None else
                        work_unit.completion_contract.task_contract)
                candidate_record = runtime.baseline_candidate(session.candidate_id)
                if candidate_record is not None:
                    verification_records = tuple(
                        runtime.verification_record(record_id)
                        for record_id in candidate_record.verification_record_ids
                    )
        governed = self.preview_store.guardian_requirements(session.work_id, basis_id)
        if governed is None:
            return {"status": "BLOCKED", "gate": "BLOCKED", "candidate_id": str(session.candidate_id),
                "finding_count": 0, "summary": "No governed business-effect assurance scope is admitted",
                "result_ref": None, "evidence_ref": None}
        prior = [item for item in self.preview_store.candidate_preview_history(session.work_id)
            if item.id != session.id and item.updated_at < session.updated_at]
        prior_findings = []
        for item in prior:
            projection = self.preview_store.guardian_projection(item.id)
            if projection:
                prior_findings.extend(projection.get("finding_ids", []))
        lineage = None if task is None else task.decision_context
        basis = {"preview_id": str(session.id), "candidate_id": str(session.candidate_id),
            "candidate_fingerprint": session.candidate_fingerprint,
            "requirements": governed,
            "decision_context_fingerprint": (None if lineage is None else
                                             lineage.package_fingerprint)}
        request_id = uuid5(NAMESPACE_URL, "watt:guardian-assurance:" + sha256(
            json.dumps(basis, sort_keys=True).encode()).hexdigest())
        protected_context = ()
        if lineage is not None:
            protected_context = tuple(
                ProtectedContextEvidence(
                    context_class=item.context_class,
                    semantic_key=item.semantic_key,
                    source_ref=item.source_ref,
                    source_revision=item.source_revision,
                    package_fingerprint=lineage.package_fingerprint,
                    coverage=("COVERED" if any(
                        record is not None and record.result.value == "PASS"
                        and (context_metadata := record.evidence.metadata.get("decision_context"))
                        and context_metadata.get("package_fingerprint") == lineage.package_fingerprint
                        and any(
                            covered.get("context_class") == item.context_class
                            and covered.get("semantic_key") == item.semantic_key
                            and covered.get("source_revision") == item.source_revision
                            and covered.get("coverage") == "COVERED"
                            for covered in context_metadata.get("protected_obligations", ())
                        ) for record in verification_records
                    ) else "GUARDIAN_REQUIRED"),
                    verification_refs=tuple(
                        f"verification:{record.id}" for record in verification_records
                        if record is not None and record.result.value == "PASS"
                    ),
                )
                for item in lineage.protected_obligations
            )
        request = AssuranceRequest(request_id=request_id,
            product_ref=f"product:{product_id}" if product_id else f"work-product:{session.work_id}",
            work_ref=f"work:{session.work_id}",
            governed_intent_ref=governed["governed_basis_ref"],
            objective=objective, constraints=constraints,
            authority_ref=governed["authority_ref"], candidate_id=session.candidate_id,
            candidate_fingerprint=session.candidate_fingerprint,
            source_revision=session.repository_revision, source_tree=session.repository_tree,
            artifact_refs=tuple(f"artifact:{item}" for item in context["artifacts"]),
            runtime_ref=f"candidate-preview:{session.id}", runtime_url=session.endpoint,
            disposable_preview=True, verification_refs=tuple(context["verification_references"]),
            task_contract_ref=(f"task-contract:{task.task_contract_id}"
                               if lineage is not None and task is not None else None),
            decision_context_fingerprint=(lineage.package_fingerprint
                                          if lineage is not None else None),
            protected_context=protected_context,
            acceptance_state="PENDING", delivery_authorization_state="NOT_AUTHORIZED",
            required_effects=tuple(governed["required_effects"]),
            prior_finding_ids=tuple(dict.fromkeys(prior_findings)),
            submitted_at=session.created_at)
        result = self.guardian_store.assess(request)
        projection = {"status": ("PASS" if result.gate.value == "PASS" else
            "BLOCKED" if result.gate.value == "BLOCKED" else "FINDINGS_PRESENT"),
            "gate": result.gate.value, "candidate_id": str(result.candidate_id),
            "request_id": str(result.request_id),
            "result_ref": f"guardian:assurance-result:{result.request_id}",
            "finding_count": len(result.findings),
            "finding_ids": [str(item.finding_id) for item in result.findings],
            "summary": "; ".join(item.observed_reality for item in result.findings[:3]),
            "evidence_ref": (f"guardian:evidence:{result.evidence[0].evidence_id}"
                if result.evidence else None)}
        return self.preview_store.save_guardian_projection(session.id, projection)

    def projection(self, work_id: UUID) -> dict:
        session = self.preview_store.current_candidate_preview(work_id)
        if session is None:
            return {"status": "NOT_STARTED", "gate": None, "finding_count": 0}
        projection = self.preview_store.guardian_projection(session.id)
        if projection:
            feedback_error = self.preview_store.guardian_feedback_error(session.id)
            if feedback_error:
                return {**projection, "status": "BLOCKED",
                    "failure_attribution": "WATT_PLATFORM_DEFECT",
                    "platform_error_ref": feedback_error["reference"]}
            if projection["gate"] == "FAIL_REPAIRABLE":
                from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
                with self.delivery.database.unit_of_work() as uow:
                    product = ProductStore(uow.session)
                    binding = product.runtime_binding(work_id)
                    facts = None if binding is None else product.runtime_summary(binding)
                    history = NativeExecutionStore(uow.session).work_convergence_history(work_id)
                if history and history[-1].condition == "NON_CONVERGING":
                    return {**projection, "status": "NON_CONVERGING"}
                if facts is not None and facts.candidate_id != session.candidate_id:
                    return {**projection, "status": "REPAIR_IN_PROGRESS"}
            return projection
        earlier = [self.preview_store.guardian_projection(item.id)
            for item in self.preview_store.candidate_preview_history(work_id)
            if item.id != session.id]
        return {"status": "REVERIFYING" if any(item and item["gate"] == "FAIL_REPAIRABLE"
            for item in earlier) else "RUNNING", "gate": None, "finding_count": 0}

    def passed(self, work_id: UUID, candidate_id: UUID) -> bool:
        session = self.preview_store.current_candidate_preview(work_id)
        return bool(session is not None and session.candidate_id == candidate_id
            and self.preview_store.guardian_feedback_error(session.id) is None
            and (projection := self.preview_store.guardian_projection(session.id)) is not None
            and projection["candidate_id"] == str(candidate_id)
            and projection["gate"] == "PASS")
