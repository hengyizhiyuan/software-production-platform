"""Deterministic context reconstruction for native execution."""

from __future__ import annotations

from spg.domain.native_execution import (
    CheckpointBundleRecord,
    ExecutionBindingV2,
    InferenceRequest,
    PWUContractVersionRecord,
    ToolExecutionResult,
    WorkingPlan,
)


class NativeContextAssembler:
    """Build inference context only from admitted contracts and durable Reality."""

    def assemble(
        self,
        *,
        binding: ExecutionBindingV2,
        contract: PWUContractVersionRecord,
        working_plan: WorkingPlan,
        step_sequence: int,
        available_tools: tuple[dict[str, object], ...],
        previous_results: tuple[ToolExecutionResult, ...] = (),
        checkpoint: CheckpointBundleRecord | None = None,
    ) -> InferenceRequest:
        facts: list[dict[str, object]] = [
            {
                "fact_type": "PWU_CONTRACT",
                "contract_version_id": str(contract.id),
                "contract_digest": contract.contract_digest,
                "payload": contract.contract_payload,
            },
            {
                "fact_type": "SOURCE_VECTOR",
                "digest": binding.source_vector.digest or "",
                "members": [
                    {
                        "mount_id": member.mount_id,
                        "repository_identity": member.repository_identity,
                        "commit": member.source_commit_oid,
                        "tree": member.source_tree_oid,
                        "read_scope": list(member.read_scope),
                        "write_scope": list(member.write_scope),
                        "forbidden_paths": list(member.forbidden_paths),
                    }
                    for member in binding.source_vector.members
                ],
                "non_repository_assets": list(binding.source_vector.non_repository_assets),
            },
            {
                "fact_type": "EXECUTION_ENVELOPE",
                "capability_grants": [grant.model_dump(mode="json") for grant in binding.capability_grants],
                "stop_conditions": list(binding.stop_conditions),
                "obligation_references": list(binding.obligation_references),
            },
        ]
        if checkpoint is not None:
            facts.append(
                {
                    "fact_type": "RECOVERY_CHECKPOINT",
                    "checkpoint_id": str(checkpoint.id),
                    "content_digest": checkpoint.content_digest,
                    "semantic_manifest": checkpoint.semantic_manifest,
                }
            )
        return InferenceRequest(
            attempt_id=binding.attempt_id,
            session_id=binding.session_id,
            step_sequence=step_sequence,
            objective=contract.objective,
            working_plan=working_plan,
            context_facts=tuple(facts),
            available_tools=available_tools,
            residual_obligations=tuple(binding.obligation_references),
            previous_results=tuple(item.model_dump(mode="json") for item in previous_results),
        )
