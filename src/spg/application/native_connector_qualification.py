"""Qualify a generic connector inside the Work's existing Production Environment.

This is a bounded Native PWU, not a second executor or an authority source.  It
exercises only an installed read-only provider probe before an interrupted PWU
is admitted with the newly resolved capability.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select

from spg.application.connectors import ConnectorResolver
from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.application.production_intelligence import TaskContractRequest, default_task_contract_builder
from spg.application.runtime import RuntimeService
from spg.domain.connectors import ConnectorCandidate
from spg.domain.native_execution import (
    AttemptTerminalOutcome, CapabilityGrant, ExecutionBindingV2,
    ExecutionHandle, ExecutionMode, NativeExecutionAdmission,
    NativeExecutionNotFound, PWUContractVersionRecord, ResourceEnvelope,
    WorkerOffer, WorkspaceManifest, canonical_digest,
)
from spg.domain.runtime import CompletionContract, InitialRunRequest, ProductionHorizon
from spg.domain.production_intelligence import EngineeringActivity
from spg.executor.kernel import NativeExecutorKernel
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.executor_runtime.production_environment_tool_host import ProductionEnvironmentNativeToolHost
from spg.infrastructure.executor_runtime.runtime_ports import DurableCheckpointPort, DurableKernelAudit
from spg.infrastructure.executor_runtime.worker import NativeExecutionWorker
from spg.infrastructure.persistence.runtime_schema import production_runs, production_work_units
from spg.infrastructure.persistence.runtime_store import RuntimeStore


class _GenericProviderProbe:
    """A deterministic, non-mutating check of one installed generic provider."""

    async def infer(self, request):
        from spg.domain.native_execution import (
            InferenceAction, InferenceResponse, ToolCallProposal, WorkingPlan,
        )

        plan = WorkingPlan(
            version=request.working_plan.version + 1,
            objective_reference=request.working_plan.objective_reference,
            chosen_approach="Probe the generic process provider in the assigned sandbox.",
            approach_rationale="A Work-local connector needs observed Native execution evidence.",
        )
        if not request.previous_results:
            return InferenceResponse(
                action=InferenceAction.CONTINUE,
                summary="Run the bounded provider health probe.",
                working_plan=plan,
                tool_calls=(ToolCallProposal(
                    proposal_index=0, tool_identity="process.run",
                    arguments={"argv": ["python", "--version"], "cwd": "."},
                ),),
                residual_obligations=("Observe a settled zero-exit process result",),
            )
        receipt = request.previous_results[-1]
        output = receipt.get("output") or {}
        if (
            receipt.get("tool_identity") == "process.run"
            and receipt.get("condition") == "SETTLED"
            and output.get("returncode") == 0
            and output.get("argv") == ["python", "--version"]
        ):
            return InferenceResponse(
                action=InferenceAction.RESULT_READY,
                summary="The generic process provider is executable in this Work sandbox.",
                working_plan=plan,
                result_claim={"provider": "process.run", "tool_output_digest": receipt.get("output_digest")},
            )
        return InferenceResponse(
            action=InferenceAction.UNABLE_TO_COMPLETE,
            summary="The generic provider probe did not establish executable capability.",
            working_plan=plan,
            residual_obligations=("Inspect the Native probe failure evidence",),
        )


class NativeConnectorQualificationService:
    """Qualify safe process-backed candidates and resume their original Work caller."""

    provider_profile = "watt-connector-qualification-v1"

    def __init__(self, database, runtime: NativeExecutorRuntimeService, *, provider, checkpoint_root: Path) -> None:
        self.database = database
        self.runtime = runtime
        self.provider = provider
        self.checkpoint_root = checkpoint_root

    def qualify(
        self,
        candidate: ConnectorCandidate,
        *, source_baseline_id: UUID,
        source_vector,
        workspace: WorkspaceManifest,
        authority_identity: str,
        admitted_permissions: tuple[str, ...],
    ) -> bool:
        requirement = candidate.requirement
        if (
            candidate.execution_provider != "native-tool:process.run"
            or candidate.qualification_tool_identity != "process.run"
            or requirement.capability_id != "quality.run"
            or any(permission not in admitted_permissions for permission in candidate.permissions_required)
            or not workspace.service_resources
        ):
            return False
        task = default_task_contract_builder().build(TaskContractRequest(
            activity=EngineeringActivity.FEATURE_DELIVERY,
            objective=f"Qualify generic provider for {requirement.capability_id}",
            scope=("read-only-provider-probe:python --version",),
            acceptance_meaning=("Native process.run settles with exit code zero in the assigned Workspace.",),
            out_of_scope=("No workspace mutation", "No external network or credentials"),
            authority_lineage=(
                f"work:{requirement.work_id}",
                f"interrupted-operation:{requirement.operation_ref}",
                f"human-authority:{authority_identity}",
            ),
            work_reality_references=(f"work:{requirement.work_id}",),
            ecf_references=(f"source-baseline:{source_baseline_id}",),
            decision_reference=requirement.operation_ref,
            required_capabilities=("shell.execute",),
        ))
        intent_ref = f"connector-qualification:{candidate.gap_id}"
        with self.database.unit_of_work() as uow:
            run_id = uow.session.execute(
                select(production_runs.c.id).where(production_runs.c.intent_ref == intent_ref)
            ).scalar_one_or_none()
            unit_id = None if run_id is None else uow.session.execute(
                select(production_work_units.c.id).where(
                    production_work_units.c.production_run_id == run_id
                )
            ).scalar_one()
            unit = None if unit_id is None else RuntimeStore(uow.session).work_unit(unit_id)
        if unit is None:
            spine = RuntimeService(self.database).create_initial_runtime_spine(InitialRunRequest(
                source_baseline_id=source_baseline_id,
                intent_ref=intent_ref,
                goal=f"Qualify generic provider for {requirement.capability_id}",
                production_horizon=ProductionHorizon.CODE,
                initial_work_unit_objective=f"Probe {candidate.execution_provider} in the Work sandbox",
                completion_contract=CompletionContract(
                    required_outputs=(f"qualified-provider:{candidate.execution_provider}",),
                    verification_obligations=("Settled zero-exit Native process effect",),
                    task_contract=task,
                ),
            ))
            unit = spine.work_unit
        with self.database.unit_of_work() as uow:
            attempts = RuntimeStore(uow.session).attempts_for_work_unit(unit.id)
        attempt = attempts[-1] if attempts else RuntimeService(self.database).create_initial_attempt(unit.id)
        session_id = uuid5(NAMESPACE_URL, f"watt:connector-qualification-session:{candidate.gap_id}")
        payload = {
            "task_contract": task.model_dump(mode="json"),
            "required_capability": requirement.capability_id,
            "generic_provider": candidate.execution_provider,
            "probe": ["python", "--version"],
            "interrupted_operation": requirement.operation_ref,
            "resume_point": requirement.resume_point,
        }
        digest = canonical_digest(payload)
        contract_id = uuid5(NAMESPACE_URL, f"watt:connector-qualification-contract:{unit.id}:{digest}")
        with self.database.unit_of_work() as uow:
            try:
                contract = NativeExecutionStore(uow.session).contract(contract_id)
            except NativeExecutionNotFound:
                contract = PWUContractVersionRecord(
                    id=contract_id, pwu_id=unit.id, revision=1,
                    objective=unit.objective, contract_payload=payload,
                    contract_digest=digest, created_at=datetime.now(UTC),
                )
        manifest = workspace.model_copy(update={
            "workspace_id": uuid5(NAMESPACE_URL, f"watt:connector-qualification-workspace:{attempt.id}"),
            "pwu_id": unit.id, "attempt_id": attempt.id,
            "evidence_namespace": f"connector-qualification:{attempt.id}",
        })
        envelope = ResourceEnvelope(
            envelope_id=uuid5(NAMESPACE_URL, f"watt:connector-qualification-envelope:{attempt.id}"),
            policy_version="connector-qualification-v1",
            max_inference_submissions=3, max_tool_effects=1, max_active_seconds=120,
            provider_profile=self.provider_profile,
        )
        binding = ExecutionBindingV2(
            work_id=requirement.work_id,
            steering_decision_id=unit.plan_revision_id,
            pwu_id=unit.id,
            pwu_contract_version_id=contract.id,
            pwu_contract_digest=digest,
            attempt_id=attempt.id, generation=attempt.generation,
            session_id=session_id,
            source_vector=source_vector, workspace=manifest,
            context_package_ref=f"capability-gap:{candidate.gap_id}",
            materialized_input_digest=digest,
            backend_implementation="watt-native", backend_version="2",
            inference_profile=self.provider_profile,
            capability_grants=(CapabilityGrant(
                identity="process.run", version="1",
                scope={"paths": [], "forbidden_paths": [".git"], "permissions": list(admitted_permissions)},
            ),),
            resource_envelope=envelope,
            obligation_references=(
                f"capability-gap:{candidate.gap_id}",
                f"interrupted-operation:{requirement.operation_ref}",
            ),
        )
        entry = self.runtime.admit(NativeExecutionAdmission(
            command_id=uuid5(NAMESPACE_URL, f"watt:connector-qualification-command:{candidate.gap_id}"),
            actor_identity=authority_identity,
            fairness_group=f"work:{requirement.work_id}",
            binding=binding, contract=contract,
            materialization_path=manifest.host_storage_id,
            required_resource_profile="standard",
            available_at=datetime.now(UTC),
        ))

        def kernel_factory(grant):
            tools = ProductionEnvironmentNativeToolHost.from_manifest(manifest, provider=self.provider)
            if tools is None:
                raise RuntimeError("Qualification requires the assigned Production Environment")
            return NativeExecutorKernel(
                inference=_GenericProviderProbe(),
                tools=tools.registry(),
                checkpoints=DurableCheckpointPort(
                    self.database, ContentAddressedStorage(self.checkpoint_root),
                    attempt_id=attempt.id, session_id=session_id,
                    worker_epoch=grant.allocation.lease_epoch,
                ),
                audit=DurableKernelAudit(
                    self.database, attempt_id=attempt.id, session_id=session_id,
                    pwu_id=unit.id, envelope_id=envelope.envelope_id,
                ),
            )

        handle = ExecutionHandle(
            backend_identity="watt-native", dispatch_id=entry.id,
            attempt_id=attempt.id, generation=attempt.generation,
            opaque_reference=f"queue:{entry.id}",
        )
        observed = self.runtime.observe(handle)
        if observed.runtime_mode is not ExecutionMode.FINISHED:
            offer = WorkerOffer(
                worker_id=f"connector-qualification:{requirement.work_id}",
                worker_profile="local-container-v1",
                provider_profiles=(self.provider_profile,), resource_profiles=("standard",),
                capability_identities=("process.run",), lease_seconds=30,
            )
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="watt-connector-qualification") as pool:
                pool.submit(lambda: asyncio.run(
                    NativeExecutionWorker(self.runtime, kernel_factory).run_once(offer)
                )).result()
            observed = self.runtime.observe(handle)
        if observed.terminal_outcome is not AttemptTerminalOutcome.RESULT_READY:
            return False
        ConnectorResolver(self.database).admit_qualified_candidate(
            candidate, qualification_attempt_id=attempt.id,
        )
        return True
