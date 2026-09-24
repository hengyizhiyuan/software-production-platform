"""Deterministic context reconstruction for native execution."""

from __future__ import annotations

import json

from spg.domain.native_execution import (
    CheckpointBundleRecord,
    ExecutionBindingV2,
    InferenceRequest,
    PWUContractVersionRecord,
    ToolExecutionResult,
    WorkingPlan,
    canonical_digest,
)


class NativeContextCapacityError(RuntimeError):
    """Exact invariant context cannot fit the admitted request envelope."""


class NativeContextAssembler:
    """Build inference context only from admitted contracts and durable Reality."""

    def __init__(self, *, max_request_bytes: int = 512 * 1024) -> None:
        if max_request_bytes < 1024:
            raise ValueError("native context byte limit is too small")
        self.max_request_bytes = max_request_bytes

    def assemble(
        self,
        *,
        binding: ExecutionBindingV2,
        contract: PWUContractVersionRecord,
        working_plan: WorkingPlan,
        step_sequence: int,
        available_tools: tuple[dict[str, object], ...],
        residual_obligations: tuple[str, ...] | None = None,
        previous_results: tuple[ToolExecutionResult, ...] = (),
        checkpoint: CheckpointBundleRecord | None = None,
        repair_history: tuple[dict[str, object], ...] = (),
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
                        "container_path": member.container_path,
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
            {
                "fact_type": "TOOL_PATH_CONVENTION",
                "workspace_root": ".",
                "mounts": [
                    {
                        "mount_id": mount.mount_id,
                        "tool_path_prefix": (
                            "." if len(binding.workspace.mounts) == 1 else mount.mount_id
                        ),
                    }
                    for mount in binding.workspace.mounts
                ],
                "rule": (
                    "All Tool path and cwd arguments are relative to the Watt workspace. "
                    "For one mount use '.' as cwd and do not prefix file paths with the "
                    "mount id. For multiple mounts use the listed tool_path_prefix. "
                    "SOURCE_VECTOR container_path is identity metadata, not a Tool path."
                ),
            },
        ]
        if repair_history:
            facts.append({
                "fact_type": "RECENT_SELF_REFINE",
                "events": list(repair_history[:3]),
                "rule": (
                    "Historical failures are evidence, not permission to change Work intent "
                    "or repeat an uncertain side effect."
                ),
            })
        if checkpoint is not None:
            facts.append(
                {
                    "fact_type": "RECOVERY_CHECKPOINT",
                    "checkpoint_id": str(checkpoint.id),
                    "content_digest": checkpoint.content_digest,
                    "semantic_manifest": checkpoint.semantic_manifest,
                }
            )
        request = InferenceRequest(
            attempt_id=binding.attempt_id,
            session_id=binding.session_id,
            step_sequence=step_sequence,
            objective=contract.objective,
            working_plan=working_plan,
            context_facts=tuple(facts),
            available_tools=available_tools,
            residual_obligations=(
                tuple(binding.obligation_references)
                if residual_obligations is None
                else residual_obligations
            ),
            previous_results=tuple(self._select_diagnostic_result(item) for item in previous_results),
        )
        if self._size(request) <= self.max_request_bytes:
            return request

        compact_facts = []
        for fact in facts:
            if fact.get("fact_type") == "RECENT_SELF_REFINE":
                latest = fact["events"][0]
                compact_facts.append({
                    "fact_type": "RECENT_SELF_REFINE",
                    "events": [{
                        key: latest[key] for key in (
                            "event_id", "failure_family", "failure_signature",
                            "status", "result",
                        ) if key in latest
                    }],
                    "compacted": True,
                    "rule": fact["rule"],
                })
                continue
            if fact.get("fact_type") != "RECOVERY_CHECKPOINT":
                compact_facts.append(fact)
                continue
            semantic = fact.get("semantic_manifest", {})
            compact_facts.append(
                {
                    "fact_type": "RECOVERY_CHECKPOINT",
                    "checkpoint_id": fact["checkpoint_id"],
                    "content_digest": fact["content_digest"],
                    "semantic_manifest": {
                        "compacted": True,
                        "working_plan_version": (
                            semantic.get("working_plan", {}).get("version")
                            if isinstance(semantic, dict)
                            else None
                        ),
                        "residual_obligations": list(
                            residual_obligations
                            if residual_obligations is not None
                            else binding.obligation_references
                        ),
                    },
                }
            )
        compact_results = []
        for item in previous_results:
            payload = item.model_dump(mode="json")
            encoded_output = json.dumps(
                payload["output"], ensure_ascii=False, sort_keys=True
            ).encode("utf-8")
            payload["output"] = {
                "compacted": True,
                "original_bytes": len(encoded_output),
                "output_digest": item.output_digest,
                "output_keys": sorted(item.output),
            }
            compact_results.append(payload)
        compacted = request.model_copy(
            update={
                "context_facts": tuple(compact_facts),
                "previous_results": tuple(compact_results),
            }
        )
        if self._size(compacted) <= self.max_request_bytes:
            return compacted
        # Repair history is relevant orientation, but it cannot displace the
        # exact admitted contract or make an otherwise valid request fail.
        without_history = compacted.model_copy(update={
            "context_facts": tuple(
                fact for fact in compacted.context_facts
                if fact.get("fact_type") != "RECENT_SELF_REFINE"
            ),
        })
        if self._size(without_history) <= self.max_request_bytes:
            return without_history
        raise NativeContextCapacityError(
            "exact PWU contract and invariant capsule exceed native context capacity"
        )

    @staticmethod
    def _size(request: InferenceRequest) -> int:
        return len(request.model_dump_json().encode("utf-8"))

    @staticmethod
    def _select_diagnostic_result(result: ToolExecutionResult) -> dict[str, object]:
        """Keep an actionable excerpt while the durable receipt owns complete logs."""

        payload = result.model_dump(mode="json")
        output = dict(payload["output"])
        for field in ("stdout", "stderr", "stack_trace", "compiler_diagnostics", "runtime_logs"):
            raw = output.get(field)
            if isinstance(raw, str) and len(raw.encode("utf-8")) > 4096:
                output[field] = {
                    "selected_tail": raw[-2048:],
                    "original_bytes": len(raw.encode("utf-8")),
                    "content_digest": canonical_digest(raw),
                    "full_receipt_digest": result.output_digest,
                }
        payload["output"] = output
        return payload
