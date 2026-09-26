"""Record an authorized Native production result at existing owner boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from uuid import NAMESPACE_URL, UUID, uuid5

from spg.application.brownfield_delivery import GuardianIntakeGateway, RealityGateway
from spg.application.production_environment_contracts import (
    change_reality_v1_payload,
    delivery_reality_v1_payload,
    guardian_assurance_intake_v1_payload,
)
from spg.domain.production_environment import (
    DeliveryResultReference,
    ProductionChangeReference,
    ProductionChangeType,
    ProductionDeliveryState,
    ProductionRecordV1,
    RepositoryRevisionReference,
    VerificationOutcome,
    VerificationResultReference,
)
from spg.domain.product import ProductInvariantViolation
from spg.domain.verification import VerificationResultValue
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore


@dataclass(frozen=True, slots=True)
class NativeProductionCompletion:
    production_record: ProductionRecordV1
    repository_reality_reference: str
    change_reality_reference: str
    delivery_reality_reference: str
    guardian_intake_reference: str


class NativeProductionRecordService:
    """Project accepted Runtime facts into Production Record, ECF, and Guardian."""

    def __init__(
        self,
        database: Database,
        *,
        store: JsonProductionEnvironmentStore,
        reality: RealityGateway,
        guardian: GuardianIntakeGateway,
    ) -> None:
        self.database = database
        self.store = store
        self.reality = reality
        self.guardian = guardian

    def record_authorized_work(self, work_id: UUID) -> NativeProductionCompletion:
        with self.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            runtime = RuntimeStore(uow.session)
            binding = product.runtime_binding(work_id)
            if binding is None:
                raise ProductInvariantViolation("Work has no admitted Runtime binding")
            summary = product.runtime_summary(binding)
            work_unit = runtime.work_unit(binding.work_unit_id)
            attempt = (
                None if summary.attempt_id is None else runtime.attempt(summary.attempt_id)
            )
            dispatch = (
                None
                if summary.attempt_id is None
                else runtime.execution_dispatch_for_attempt(summary.attempt_id)
            )
            candidate = (
                None
                if summary.candidate_id is None
                else runtime.baseline_candidate(summary.candidate_id)
            )
            snapshot = (
                None if candidate is None
                else runtime.proposed_snapshot(candidate.proposed_snapshot_id)
            )
            observation = (
                None if snapshot is None
                else runtime.repository_observation_by_id(snapshot.repository_observation_id)
            )
            effect = (
                None
                if summary.integration_effect_id is None
                else runtime.repository_integration_effect(summary.integration_effect_id)
            )
            runtime_commit = (
                None
                if summary.runtime_commit_id is None
                else runtime.runtime_commit(summary.runtime_commit_id)
            )
            verification = (
                ()
                if candidate is None
                else tuple(
                    runtime.verification_record(item)
                    for item in candidate.verification_record_ids
                )
            )
            resource = product.resource(binding.resource_id)

        required = {
            "PWU": work_unit,
            "Attempt": attempt,
            "dispatch": dispatch,
            "observation": observation,
            "Candidate": candidate,
            "integration effect": effect,
            "Runtime Commit": runtime_commit,
            "Engineering Resource": resource,
        }
        missing = tuple(name for name, value in required.items() if value is None)
        if missing:
            raise ProductInvariantViolation(
                "Production Record requires authorized completed lineage: "
                + ", ".join(missing)
            )
        assert work_unit is not None
        assert attempt is not None
        assert dispatch is not None
        assert observation is not None
        assert candidate is not None
        assert effect is not None
        assert runtime_commit is not None
        assert resource is not None
        task_contract = work_unit.completion_contract.task_contract
        if task_contract is None:
            raise ProductInvariantViolation("Production Record requires a Task Contract")
        if any(item is None for item in verification):
            raise ProductInvariantViolation("Candidate Verification lineage is incomplete")
        pe_binding = self.store.get_native_execution_binding(attempt.id)
        if pe_binding is None:
            raise ProductInvariantViolation(
                "Native Attempt has no Production Environment binding"
            )
        environment = self.store.get_environment(pe_binding.environment.id)
        if environment is None:
            raise ProductInvariantViolation("Production Environment disappeared")

        record_id = uuid5(
            NAMESPACE_URL,
            f"watt:native-production-record:{runtime_commit.id}",
        )
        # The terminal PWU observation covers only its own effect.  An ECF
        # Production Record describes the entire committed Work graph.
        diff = subprocess.run(
            ["git", "--no-replace-objects", "-C", resource.location_ref,
             "diff", "--no-renames", "--name-status", "-z",
             runtime_commit.expected_source_repository_revision,
             runtime_commit.repository_revision],
            capture_output=True, check=True, timeout=30,
        ).stdout.split(b"\0")
        changes = []
        for index in range(0, len(diff) - 1, 2):
            status = diff[index].decode("ascii")
            path = diff[index + 1].decode("utf-8")
            if status not in {"A", "M", "D", "T"}:
                raise ProductInvariantViolation(
                    "Production Record encountered an unsupported Git change type")
            revision = (runtime_commit.expected_source_repository_revision
                        if status == "D" else runtime_commit.repository_revision)
            object_id = subprocess.run(
                ["git", "--no-replace-objects", "-C", resource.location_ref,
                 "rev-parse", f"{revision}:{path}"],
                capture_output=True, check=True, text=True, timeout=10,
            ).stdout.strip()
            changes.append(ProductionChangeReference(
                repository_identity=runtime_commit.repository_identity,
                path=path,
                change_type=ProductionChangeType({"A": "ADDED", "M": "MODIFIED",
                                                  "D": "DELETED", "T": "MODIFIED"}[status]),
                artifact_reference=f"artifact:git-object:{object_id}",
            ))
        changes = tuple(changes)
        if not changes:
            raise ProductInvariantViolation("Production Record requires observed changes")
        verification_results = tuple(
            VerificationResultReference(
                reference=f"verification:{item.id}:{item.basis_fingerprint}",
                outcome=(
                    VerificationOutcome.PASS
                    if item.result is VerificationResultValue.PASS
                    else VerificationOutcome.FAIL
                    if item.result is VerificationResultValue.FAIL
                    else VerificationOutcome.INCONCLUSIVE
                ),
            )
            for item in verification
            if item is not None
        )
        record = ProductionRecordV1(
            id=record_id,
            work_reference=f"work:{work_id}",
            task_contract_reference=f"task-contract:{task_contract.task_contract_id}",
            repository_revisions=(
                RepositoryRevisionReference(
                    repository_identity=runtime_commit.repository_identity,
                    branch=effect.target_authoritative_ref.removeprefix("refs/heads/"),
                    before_revision=runtime_commit.expected_source_repository_revision,
                    after_revision=runtime_commit.repository_revision,
                    diff_reference=(
                        f"{runtime_commit.expected_source_repository_revision}"
                        f"..{runtime_commit.repository_revision}"
                    ),
                ),
            ),
            environment_reference=f"production-environment:{environment.id}",
            changes=changes,
            verification_results=verification_results,
            delivery_result=DeliveryResultReference(
                reference=f"repository-integration:{effect.id}",
                state=ProductionDeliveryState.AUTHORIZED_FOR_DELIVERY,
            ),
            created_at=runtime_commit.committed_at,
        )
        record = self.store.save_production_record(record)

        repository = self.reality.discover_repository_payload(
            Path(resource.location_ref),
            repository_identity=runtime_commit.repository_identity,
        )
        change_id = uuid5(NAMESPACE_URL, f"watt:change-reality:{record.id}")
        delivery_id = uuid5(NAMESPACE_URL, f"watt:delivery-reality:{record.id}")
        intake_id = uuid5(NAMESPACE_URL, f"watt:guardian-intake:{record.id}")
        source_reference = f"production-record:{record.id}"
        change = self.reality.admit_change_payload(
            change_reality_v1_payload(
                record,
                reality_id=change_id,
                observed_at=record.created_at,
                source_reference=source_reference,
                observed_by="watt:native-production-record:v1",
            )
        )
        delivery = self.reality.admit_delivery_payload(
            delivery_reality_v1_payload(
                record,
                reality_id=delivery_id,
                repository_identity=runtime_commit.repository_identity,
                observed_at=record.created_at,
                source_reference=source_reference,
                observed_by="watt:native-production-record:v1",
            )
        )
        guardian = self.guardian.admit_payload(
            guardian_assurance_intake_v1_payload(
                record,
                intake_id=intake_id,
                submitted_by="watt:native-production-record:v1",
                submitted_at=record.created_at,
            )
        )
        return NativeProductionCompletion(
            production_record=record,
            repository_reality_reference=(
                f"ecf:repository-reality:{repository['reality_id']}"
            ),
            change_reality_reference=f"ecf:change-reality:{change['reality_id']}",
            delivery_reality_reference=f"ecf:delivery-reality:{delivery['reality_id']}",
            guardian_intake_reference=(
                f"guardian:assurance-intake:{guardian['intake_id']}"
            ),
        )
