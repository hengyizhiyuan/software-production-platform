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
from spg.domain.production_environment import CandidatePreviewMode, CandidatePreviewSessionV1, PreviewRuntimeStatus
from spg.domain.runtime import WorkUnitCondition
from spg.infrastructure.persistence.product_schema import product_works
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore


def _protected_context_for_guardian(task, verification_records) -> tuple:
    """Project only exact covered obligations from persisted verification evidence."""
    from guardian.contracts.software_assurance import ProtectedContextEvidence

    lineage = None if task is None else task.decision_context
    if lineage is None:
        return ()
    projected = []
    for obligation in lineage.protected_obligations:
        matching_refs = []
        for record in verification_records:
            if record is None or record.result.value != "PASS":
                continue
            context = record.evidence.metadata.get("decision_context")
            if not context or context.get("package_fingerprint") != lineage.package_fingerprint:
                continue
            if any(
                item.get("context_class") == obligation.context_class
                and item.get("semantic_key") == obligation.semantic_key
                and item.get("source_ref") == obligation.source_ref
                and item.get("source_revision") == obligation.source_revision
                and item.get("coverage") == "COVERED"
                for item in context.get("protected_obligations", ())
            ):
                matching_refs.append(f"verification:{record.id}")
        projected.append(ProtectedContextEvidence(
            context_class=obligation.context_class,
            semantic_key=obligation.semantic_key,
            source_ref=obligation.source_ref,
            source_revision=obligation.source_revision,
            package_fingerprint=lineage.package_fingerprint,
            coverage="COVERED" if matching_refs else "GUARDIAN_REQUIRED",
            verification_refs=tuple(matching_refs),
        ))
    return tuple(projected)


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
        from guardian.contracts.software_assurance import AssuranceRequest

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
            units = ()
            unit_evidence = []
            verification_records = ()
            if binding is not None and isinstance(getattr(binding, "work_unit_id", None), UUID):
                runtime = RuntimeStore(uow.session)
                candidate_record = runtime.baseline_candidate(session.candidate_id)
                plan = None if candidate_record is None or candidate_record.plan_revision_id != binding.plan_revision_id else runtime.plan_revision(candidate_record.plan_revision_id)
                if candidate_record is None or plan is None:
                    raise ProductInvariantViolation("Guardian requires current Task Contract lineage")
                units = runtime.work_units_for_plan(plan.id)
                if (not units or set(candidate_record.satisfied_work_unit_ids) != {unit.id for unit in units}
                        or any(unit.condition is not WorkUnitCondition.SATISFIED for unit in units)):
                    raise ProductInvariantViolation("Guardian requires all required PWUs satisfied")
                for unit in units:
                    task = unit.completion_contract.task_contract
                    if task is None or unit.source_baseline_id is None:
                        raise ProductInvariantViolation("Guardian requires every exact PWU Task and input")
                    output = (None if unit.verified_output_baseline_id is None else
                        runtime.snapshot(unit.verified_output_baseline_id))
                    revision = session.repository_revision if output is None else output.repository_revision
                    tree = session.repository_tree if output is None else output.repository_tree_identity
                    records = tuple(record for record in runtime.verification_records_for_work_unit(unit.id)
                        if record.proposed_commit_identity == revision and record.tree_identity == tree
                        and record.plan_revision_id == plan.id
                        and record.source_baseline_id == unit.source_baseline_id)
                    if not records or any(record.result.value != "PASS" for record in records):
                        raise ProductInvariantViolation("Guardian requires exact qualified PWU Verification")
                    refs = [f"production-plan:{plan.id}:version:{plan.revision_number}",
                        f"pwu:{unit.id}", f"source-baseline:{unit.source_baseline_id}",
                        f"task-contract:{task.task_contract_id}",
                        f"qualified-result:{revision}:tree:{tree}",
                        *(f"parent-baseline:{item}" for item in (unit.parent_baseline_ids or ()))]
                    for attempt in runtime.attempts_for_work_unit(unit.id):
                        if attempt.generation != unit.current_execution_generation:
                            continue
                        refs.append(f"execution-attempt:{attempt.id}")
                        dispatch = runtime.execution_dispatch_for_attempt(attempt.id)
                        if dispatch is not None:
                            refs.append(f"execution-dispatch:{dispatch.id}")
                    if unit.reconciliation_evidence is not None:
                        refs.append(f"pwu-reconciliation:{unit.id}:" + sha256(json.dumps(
                            unit.reconciliation_evidence, sort_keys=True).encode()).hexdigest())
                    unit_evidence.append((unit, task, records, tuple(refs)))
        governed = self.preview_store.guardian_requirements(session.work_id, basis_id)
        if governed is None and units:
            # These paths are approved production obligations, never inferred
            # from arbitrary Candidate prose or a new Human interpretation.
            paths = sorted({path for unit in units for path in
                (*unit.completion_contract.required_outputs, *unit.completion_contract.required_changes)
                if session.mode is CandidatePreviewMode.STATIC_PREVIEW
                and path.endswith(".html") and path in context["paths"]})
            effects = [{"obligation_ref": f"work-route:{path}", "kind": "HTTP_ROUTE",
                "expected_behavior": f"Approved static result {path} is served from the exact Candidate",
                "path": "/" + path} for path in paths]
            if not effects:
                effects = [{"obligation_ref": "work-runtime-entry", "kind": "HTTP_ROUTE",
                    "expected_behavior": objective, "path": "/"}]
            governed = self.preview_store.admit_guardian_requirements(session.work_id, basis_id, {
                "work_id": str(session.work_id), "governed_basis_ref": f"work-reality-revision:{basis_id}",
                "authority_ref": f"engineering-scope:{scope.id}",
                "admitted_by": "system:admitted-production-plan",
                "plan_revision_id": str(binding.plan_revision_id),
                "required_effects": effects})
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
        # Guardian's v1 request is scoped to one ECF package. Submit each exact
        # required PWU separately rather than inventing a merged ECF fingerprint.
        results = []
        for unit, task, records, refs in unit_evidence or [(None, None, verification_records, ())]:
            lineage = None if task is None else task.decision_context
            basis = {"preview_id": str(session.id), "candidate_id": str(session.candidate_id),
                "candidate_fingerprint": session.candidate_fingerprint, "requirements": governed,
                "pwu_id": None if unit is None else str(unit.id), "lineage_refs": refs,
                "verification_ids": [str(record.id) for record in records],
                "task_fingerprint": None if task is None else task.content_fingerprint}
            request_id = uuid5(NAMESPACE_URL, "watt:guardian-assurance:" + sha256(
                json.dumps(basis, sort_keys=True).encode()).hexdigest())
            protected_context = _protected_context_for_guardian(task, records)
            request = AssuranceRequest(request_id=request_id,
            product_ref=f"product:{product_id}" if product_id else f"work-product:{session.work_id}",
            work_ref=f"work:{session.work_id}",
            governed_intent_ref=governed["governed_basis_ref"],
            objective=objective, constraints=constraints,
            authority_ref=governed["authority_ref"], candidate_id=session.candidate_id,
            candidate_fingerprint=session.candidate_fingerprint,
            source_revision=session.repository_revision, source_tree=session.repository_tree,
            artifact_refs=tuple(f"artifact:{item}" for item in context["artifacts"]) + refs,
            runtime_ref=f"candidate-preview:{session.id}", runtime_url=session.endpoint,
            disposable_preview=True, verification_refs=tuple(dict.fromkeys((
                *context["verification_references"], *(f"verification:{record.id}" for record in records)))),
            task_contract_ref=(f"task-contract:{task.task_contract_id}"
                               if task is not None else None),
            decision_context_fingerprint=(lineage.package_fingerprint
                if lineage is not None and protected_context else None),
            protected_context=protected_context,
            acceptance_state="PENDING", delivery_authorization_state="NOT_AUTHORIZED",
            required_effects=tuple(governed["required_effects"]),
            prior_finding_ids=tuple(dict.fromkeys(prior_findings)),
            submitted_at=session.created_at)
            results.append(self.guardian_store.assess(request))
        gate = ("BLOCKED" if any(item.gate.value == "BLOCKED" for item in results)
            else "FAIL_REPAIRABLE" if any(item.gate.value == "FAIL_REPAIRABLE" for item in results)
            else "PASS")
        result = results[0]
        findings = tuple(item for result in results for item in result.findings)
        projection = {"status": ("PASS" if gate == "PASS" else
            "BLOCKED" if gate == "BLOCKED" else "FINDINGS_PRESENT"),
            "gate": gate, "candidate_id": str(result.candidate_id),
            "request_id": str(result.request_id),
            "result_ref": f"guardian:assurance-result:{result.request_id}",
            "result_refs": [f"guardian:assurance-result:{item.request_id}" for item in results],
            "required_pwu_ids": [str(unit.id) for unit in units],
            "finding_count": len(findings),
            "finding_ids": [str(item.finding_id) for item in findings],
            "summary": "; ".join(item.observed_reality for item in findings[:3]),
            "evidence_ref": (f"guardian:evidence:{result.evidence[0].evidence_id}"
                if result.evidence else None)}
        return self.preview_store.save_guardian_projection(session.id, projection)

    def projection(self, work_id: UUID) -> dict:
        session = self.preview_store.current_candidate_preview(work_id)
        if session is None:
            from spg.application.candidate_preview import CandidatePreviewApplicationService
            context = self.delivery.candidate_context(work_id)
            required = bool(context is not None and CandidatePreviewApplicationService.mode_for(context) is not None)
            return {"status": "NOT_STARTED", "gate": None, "finding_count": 0,
                "required": required}
        projection = self.preview_store.guardian_projection(session.id)
        if projection:
            feedback_error = self.preview_store.guardian_feedback_error(session.id)
            if feedback_error:
                return {**projection, "required": True, "status": "BLOCKED",
                    "failure_attribution": "WATT_PLATFORM_DEFECT",
                    "platform_error_ref": feedback_error["reference"]}
            if projection["gate"] == "PASS" and not self.passed(work_id, session.candidate_id):
                return {**projection, "required": True, "status": "BLOCKED", "gate": "BLOCKED",
                    "summary": "Exact Guardian owner result is unavailable; acceptance is blocked"}
            if projection["gate"] == "FAIL_REPAIRABLE":
                from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
                with self.delivery.database.unit_of_work() as uow:
                    product = ProductStore(uow.session)
                    binding = product.runtime_binding(work_id)
                    facts = None if binding is None else product.runtime_summary(binding)
                    history = NativeExecutionStore(uow.session).work_convergence_history(work_id)
                if history and history[-1].condition == "NON_CONVERGING":
                    return {**projection, "required": True, "status": "NON_CONVERGING"}
                if facts is not None and facts.candidate_id != session.candidate_id:
                    return {**projection, "required": True, "status": "REPAIR_IN_PROGRESS"}
            return {**projection, "required": True}
        earlier = [self.preview_store.guardian_projection(item.id)
            for item in self.preview_store.candidate_preview_history(work_id)
            if item.id != session.id]
        return {"status": "REVERIFYING" if any(item and item["gate"] == "FAIL_REPAIRABLE"
            for item in earlier) else "RUNNING", "gate": None, "finding_count": 0,
            "required": True}

    def passed(self, work_id: UUID, candidate_id: UUID) -> bool:
        session = self.preview_store.current_candidate_preview(work_id)
        ready = bool(session is not None and session.status is PreviewRuntimeStatus.READY
            and session.candidate_id == candidate_id
            and self.preview_store.guardian_feedback_error(session.id) is None
            and (projection := self.preview_store.guardian_projection(session.id)) is not None
            and projection["candidate_id"] == str(candidate_id)
            and projection["gate"] == "PASS")
        if not ready:
            return False
        references = projection.get("result_refs", [projection["result_ref"]])
        if not references:
            return False
        for reference in references:
            result = self.guardian_store.get_result(UUID(reference.removeprefix("guardian:assurance-result:")))
            if (result is None or result.gate.value != "PASS" or result.candidate_id != candidate_id
                    or result.candidate_fingerprint != session.candidate_fingerprint
                    or result.source_revision != session.repository_revision
                    or result.source_tree != session.repository_tree
                    or result.runtime_ref != f"candidate-preview:{session.id}"):
                return False
        return True
