from __future__ import annotations

import asyncio
from contextlib import contextmanager
import errno
from hashlib import sha256
import json
import os
import subprocess
import sys
import tarfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from spg.application.executor_runtime import FairCapacityScheduler
from spg.domain.native_execution import (
    AttemptTerminalOutcome,
    BackendCapabilities,
    CapabilityGrant,
    CheckpointBundleRecord,
    CheckpointCondition,
    ControlAction,
    EffectCondition,
    ExecutionBindingV2,
    ExecutionHandle,
    ExecutionMode,
    ExecutionQueueEntryRecord,
    InferenceAction,
    InferenceDecisionRejected,
    InferenceRequest,
    InferenceResponse,
    KernelCheckpoint,
    NativeExecutionConflict,
    PWUContractVersionRecord,
    QueueCondition,
    RecoveryClassification,
    ResourceEnvelope,
    SourceMember,
    SourceVector,
    ToolCallProposal,
    ToolExecutionRequest,
    ToolExecutionResult,
    WorkerOffer,
    WorkingPlan,
    WorkspaceManifest,
    WorkspaceMount,
    canonical_digest,
)
from spg.executor.kernel import NativeExecutorKernel
from spg.executor.context import NativeContextAssembler, NativeContextCapacityError
from spg.executor.recovery import NativeRecoveryClassifier
from spg.executor.tools import NativeToolRegistry, ToolDefinition
from spg.infrastructure.executor_runtime.inference import (
    InferenceAdapterError,
    InferenceTransportUnknown,
    InferenceResourceUnavailable,
    OpenAIResponsesInferenceAdapter,
    ScriptedInferenceAdapter,
)
from spg.infrastructure.executor_runtime.backends import PinnedExecutionBackendRouter
from spg.infrastructure.executor_runtime.local_storage import (
    ContentAddressedStorage,
    DirtyInputOverlayStore,
    WorkspaceArchiveStore,
)
from spg.infrastructure.executor_runtime.runtime_ports import DurableCheckpointPort
from spg.infrastructure.executor_runtime.tool_host import LocalNativeToolHost
from spg.infrastructure.executor_runtime.worker import NativeExecutionWorker
from spg.tool_host_api import create_tool_host_application


NOW = datetime(2026, 9, 11, 8, 0, tzinfo=timezone.utc)


def test_workspace_archive_rejects_links_and_detects_tampering(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "source.txt"
    source.write_text("recoverable\n", encoding="utf-8")
    archives = WorkspaceArchiveStore(tmp_path / "archives")

    (workspace / "escape").symlink_to("/etc/passwd")
    with pytest.raises(RuntimeError, match="refuses links"):
        archives.archive(workspace)
    (workspace / "escape").unlink()

    os.link(source, workspace / "hardlink.txt")
    with pytest.raises(RuntimeError, match="hard-linked"):
        archives.archive(workspace)
    (workspace / "hardlink.txt").unlink()

    digest, archive = archives.archive(workspace)
    archive.write_bytes(archive.read_bytes() + b"tamper")
    with pytest.raises(RuntimeError, match="digest differs"):
        archives.verify(digest, archive)


def test_workspace_archive_rejects_escape_member_before_restore(tmp_path: Path) -> None:
    archives = WorkspaceArchiveStore(tmp_path / "archives")
    staged = tmp_path / "malicious.tar"
    with tarfile.open(staged, "w") as stream:
        payload = b"escape"
        member = tarfile.TarInfo("../outside.txt")
        member.size = len(payload)
        stream.addfile(member, BytesIO(payload))
    digest = sha256(staged.read_bytes()).hexdigest()
    stored = archives.root / digest[:2] / f"{digest}.tar"
    stored.parent.mkdir(parents=True)
    stored.write_bytes(staged.read_bytes())

    with pytest.raises(RuntimeError, match="unsafe member"):
        archives.restore(digest, tmp_path / "restore")

    assert not (tmp_path / "outside.txt").exists()
    assert not (tmp_path / "restore").exists()


def test_dirty_input_overlay_preserves_binary_untracked_ignored_and_deletions(
    tmp_path: Path,
) -> None:
    source = tmp_path / "human-source"
    source.mkdir()

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", "-C", str(source), *arguments],
            check=True, capture_output=True,
        )

    git("init", "-b", "main")
    git("config", "user.name", "Q08 Qualification")
    git("config", "user.email", "q08@example.invalid")
    (source / ".gitignore").write_text("*.generated\n.cache/\n", encoding="utf-8")
    (source / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    (source / "deleted.txt").write_text("remove later\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "baseline")
    (source / "tracked.txt").write_text("human change\n", encoding="utf-8")
    (source / "deleted.txt").unlink()
    (source / "binary.dat").write_bytes(b"\x00\xff\x10WATT")
    (source / "useful.generated").write_bytes(b"generated-but-useful\x00")
    (source / ".cache").mkdir()
    (source / ".cache/rebuild.bin").write_bytes(b"reproducible-cache")
    before = {
        path.relative_to(source).as_posix(): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(source).parts
    }
    overlays = DirtyInputOverlayStore(tmp_path / "overlay-store")

    reference, manifest = overlays.capture(
        source,
        excluded_cache_recipes={".cache": "python -m build_cache"},
    )

    after = {
        path.relative_to(source).as_posix(): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(source).parts
    }
    assert after == before
    entries = {entry["path"]: entry for entry in manifest["entries"]}
    assert entries["tracked.txt"]["category"] == "TRACKED_CHANGE"
    assert entries["deleted.txt"]["type"] == "ABSENT"
    assert entries["binary.dat"]["category"] == "UNTRACKED"
    assert entries["useful.generated"]["category"] == "IGNORED_USEFUL"
    assert ".cache/rebuild.bin" not in entries
    assert manifest["excluded_caches"] == [{
        "path": ".cache", "recreation_recipe": "python -m build_cache",
    }]

    restored = tmp_path / "restored-overlay"
    overlays.restore(reference, restored)
    assert (restored / "tracked.txt").read_text(encoding="utf-8") == "human change\n"
    assert (restored / "binary.dat").read_bytes() == b"\x00\xff\x10WATT"
    assert (restored / "useful.generated").read_bytes() == b"generated-but-useful\x00"
    assert not (restored / "deleted.txt").exists()
    assert not (restored / ".cache").exists()


def test_checkpoint_disk_full_cannot_publish_a_durable_pointer() -> None:
    class FullStorage:
        def put_json(self, namespace, payload):
            del namespace, payload
            raise OSError(errno.ENOSPC, "qualification injected disk full")

    class DatabaseMustNotBeReached:
        def unit_of_work(self):
            raise AssertionError("database pointer must not advance after storage failure")

    checkpoint = KernelCheckpoint(
        step_sequence=1,
        working_plan=_plan(),
        tool_results=(),
        source_vector_digest="a" * 64,
        residual_obligations=("persist output",),
    )
    port = DurableCheckpointPort(
        DatabaseMustNotBeReached(),
        FullStorage(),
        attempt_id=uuid4(),
        session_id=uuid4(),
        worker_epoch=1,
    )

    with pytest.raises(OSError) as caught:
        asyncio.run(port.commit(checkpoint))

    assert caught.value.errno == errno.ENOSPC


def _plan(version: int = 1) -> WorkingPlan:
    return WorkingPlan(
        version=version,
        objective_reference="contract:test",
        chosen_approach="inspect, change, verify",
        approach_rationale="bounded contract requires observable evidence",
        obligation_ids=("test",),
    )


def _binding(*, with_repository: bool = True) -> tuple[ExecutionBindingV2, PWUContractVersionRecord]:
    work_id, pwu_id, attempt_id, session_id = uuid4(), uuid4(), uuid4(), uuid4()
    members = ()
    if with_repository:
        members = (
            SourceMember(
                mount_id="primary",
                repository_identity="test://repository",
                source_baseline_ref="refs/heads/main",
                source_commit_oid="a" * 40,
                source_tree_oid="b" * 40,
                container_path="/workspace/primary",
                read_scope=("src", "tests"),
                write_scope=("src", "tests"),
                forbidden_paths=(".git",),
            ),
        )
    vector = SourceVector(
        members=members,
        non_repository_assets=() if members else ({"kind": "requirement", "content": "build"},),
    )
    workspace = WorkspaceManifest(
        workspace_id=uuid4(),
        work_id=work_id,
        pwu_id=pwu_id,
        attempt_id=attempt_id,
        source_vector_digest=vector.digest or "",
        host_storage_id="private-host",
        environment_profile_digest="c" * 64,
        mounts=(
            WorkspaceMount(
                mount_id="generated" if not members else "primary",
                host_path="/private/workspace",
                container_path="/workspace/generated" if not members else "/workspace/primary",
                writable=True,
                write_scope=("src", "tests"),
                forbidden_paths=(".git",),
            ),
        ),
        generated_roots=("generated",),
        evidence_namespace="native-test",
        retention_policy="qualification",
    )
    payload = {"objective": "implement bounded behavior", "obligations": ["test"]}
    contract = PWUContractVersionRecord(
        id=uuid4(),
        pwu_id=pwu_id,
        revision=1,
        objective="implement bounded behavior",
        contract_payload=payload,
        contract_digest=canonical_digest(payload),
        created_at=NOW,
    )
    envelope = ResourceEnvelope(
        envelope_id=uuid4(),
        policy_version="qualification-v1",
        max_inference_submissions=3,
        max_tool_effects=3,
        max_active_seconds=60,
        provider_profile="openai-responses",
    )
    binding = ExecutionBindingV2(
        work_id=work_id,
        steering_decision_id=uuid4(),
        pwu_id=pwu_id,
        pwu_contract_version_id=contract.id,
        pwu_contract_digest=contract.contract_digest,
        attempt_id=attempt_id,
        generation=1,
        session_id=session_id,
        source_vector=vector,
        workspace=workspace,
        context_package_ref="context:test",
        materialized_input_digest="d" * 64,
        backend_implementation="watt-native",
        backend_version="1",
        inference_profile="openai-responses:test",
        capability_grants=(
            CapabilityGrant(identity="file.write", version="1", scope={"paths": ["src", "tests"], "forbidden_paths": [".git"]}),
        ),
        resource_envelope=envelope,
        obligation_references=("test",),
    )
    return binding, contract


def _queue(group: str, minute: int, *, capability: str = "file.write") -> ExecutionQueueEntryRecord:
    return ExecutionQueueEntryRecord(
        id=uuid4(), command_id=uuid4(), request_digest="a" * 64,
        actor_identity="human:test", work_id=uuid4(), pwu_id=uuid4(), attempt_id=uuid4(),
        grant_revision=1, fairness_group=group, condition=QueueCondition.QUEUED,
        required_capabilities=(capability,), required_provider_profile="openai-responses",
        required_resource_profile="standard", enqueued_at=NOW + timedelta(minutes=minute),
        available_at=NOW, version=1,
    )


def _offer() -> WorkerOffer:
    return WorkerOffer(
        worker_id="worker-1", worker_profile="local-container-v1",
        provider_profiles=("openai-responses",), resource_profiles=("standard",),
        capability_identities=("file.write",),
    )


def test_source_vector_is_deterministic_multi_repository_and_repository_optional() -> None:
    binding, _ = _binding()
    assert binding.source_vector.digest == canonical_digest({
        "schema_version": 1,
        "members": [item.model_dump(mode="json") for item in binding.source_vector.members],
        "non_repository_assets": [],
    })
    repository_free, _ = _binding(with_repository=False)
    assert repository_free.source_vector.members == ()
    assert repository_free.workspace.mounts[0].writable is True


def test_source_vector_rejects_ambiguous_mounts_and_unsafe_paths() -> None:
    binding, _ = _binding()
    member = binding.source_vector.members[0]
    with pytest.raises(ValueError, match="unique"):
        SourceVector(members=(member, member))
    with pytest.raises(ValueError, match="safe"):
        SourceMember(**{
            **member.model_dump(),
            "write_scope": ("../escape",),
        })


def test_scheduler_is_round_robin_fifo_and_aging_prevents_starvation() -> None:
    scheduler = FairCapacityScheduler(aging_threshold=timedelta(minutes=10))
    a1, a2, b1 = _queue("user-a", 0), _queue("user-a", 1), _queue("user-b", 2)
    decision = scheduler.choose([a1, a2, b1], _offer(), now=NOW + timedelta(minutes=3), last_fairness_group="user-a")
    assert decision.selected_queue_entry_id == b1.id
    assert "round-robin" in decision.reason
    fifo = scheduler.choose([a2, a1], _offer(), now=NOW + timedelta(minutes=3), last_fairness_group=None)
    assert fifo.selected_queue_entry_id == a1.id
    aged = scheduler.choose([b1, a1], _offer(), now=NOW + timedelta(minutes=20), last_fairness_group="user-a")
    assert aged.selected_queue_entry_id == a1.id
    assert "aging" in aged.reason


def test_scheduler_does_not_allocate_ineligible_capacity() -> None:
    decision = FairCapacityScheduler().choose(
        [_queue("user-a", 0, capability="network.egress")],
        _offer(), now=NOW, last_fairness_group=None,
    )
    assert decision.selected_queue_entry_id is None


def test_content_addressed_storage_is_atomic_and_detects_corruption(tmp_path: Path) -> None:
    storage = ContentAddressedStorage(tmp_path / "evidence")
    digest, path = storage.put_json("attempts/test", {"你好": "Watt", "n": 1})
    same_digest, same_path = storage.put_json("attempts/test", {"n": 1, "你好": "Watt"})
    assert (digest, path) == (same_digest, same_path)
    assert storage.get_json("attempts/test", digest) == {"n": 1, "你好": "Watt"}
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="digest"):
        storage.get_json("attempts/test", digest)


def test_tool_registry_requires_grant_and_enforces_path_scope() -> None:
    binding, _ = _binding()
    calls = []

    async def handler(request: ToolExecutionRequest) -> ToolExecutionResult:
        calls.append(request)
        return ToolExecutionResult(
            delivery_id=request.delivery_id,
            tool_identity="file.write",
            condition=EffectCondition.SETTLED,
            output={"ok": True},
            output_digest=canonical_digest({"ok": True}),
        )

    registry = NativeToolRegistry((ToolDefinition("file.write", "1", "write", {}, "LOCAL_MUTATION", handler),))
    proposal = ToolCallProposal(proposal_index=0, tool_identity="file.write", arguments={"path": "src/new.py"})
    request = ToolExecutionRequest(delivery_id=uuid4(), attempt_id=binding.attempt_id, worker_epoch=1, step_id=uuid4(), proposal=proposal, capability_grants=binding.capability_grants, workspace=binding.workspace)
    asyncio.run(registry.execute(request))
    assert len(calls) == 1
    denied = request.model_copy(update={"proposal": proposal.model_copy(update={"arguments": {"path": "docs/out.md"}})})
    with pytest.raises(NativeExecutionConflict, match="outside"):
        asyncio.run(registry.execute(denied))


class _Checkpoints:
    def __init__(self) -> None:
        self.items: list[KernelCheckpoint] = []

    async def commit(self, checkpoint: KernelCheckpoint) -> CheckpointBundleRecord:
        self.items.append(checkpoint)
        return CheckpointBundleRecord(
            id=uuid4(), session_id=uuid4(), attempt_id=uuid4(),
            step_sequence=checkpoint.step_sequence, worker_epoch=1,
            condition=CheckpointCondition.COMMITTED,
            source_vector_digest=checkpoint.source_vector_digest,
            repository_manifest={}, execution_manifest={},
            semantic_manifest={"working_plan": checkpoint.working_plan.model_dump(mode="json")},
            content_digest=canonical_digest(checkpoint), consistency_class="TEST",
            created_at=NOW, committed_at=NOW,
        )


def test_native_kernel_runs_multiple_inference_tool_cycles_and_claims_result() -> None:
    binding, contract = _binding()
    tool_results = []

    async def write(request: ToolExecutionRequest) -> ToolExecutionResult:
        result = ToolExecutionResult(
            delivery_id=request.delivery_id, tool_identity="file.write",
            condition=EffectCondition.SETTLED, output={"path": "src/new.py"},
            output_digest=canonical_digest({"path": "src/new.py"}),
        )
        tool_results.append(result)
        return result

    inference = ScriptedInferenceAdapter((
        InferenceResponse(action=InferenceAction.CONTINUE, summary="make change", working_plan=_plan(2), tool_calls=(ToolCallProposal(proposal_index=0, tool_identity="file.write", arguments={"path": "src/new.py", "content": "ok"}),), residual_obligations=("remaining",)),
        InferenceResponse(action=InferenceAction.RESULT_READY, summary="verified", working_plan=_plan(3), result_claim={"output_vector": {"files": ["src/new.py"]}, "evidence_ids": []}, residual_obligations=()),
    ))
    checkpoints = _Checkpoints()
    kernel = NativeExecutorKernel(inference=inference, tools=NativeToolRegistry((ToolDefinition("file.write", "1", "write", {}, "LOCAL_MUTATION", write),)), checkpoints=checkpoints)
    result = asyncio.run(kernel.run(binding=binding, contract=contract, worker_epoch=1, working_plan=_plan()))
    assert result.runtime_mode is ExecutionMode.FINISHED
    assert result.terminal_outcome is AttemptTerminalOutcome.RESULT_READY
    assert result.inference_submissions == 2
    assert result.tool_effects == 1
    assert len(checkpoints.items) == 2
    assert inference.requests[1].residual_obligations == ("remaining",)


def test_kernel_keeps_tools_after_continue_clears_residuals() -> None:
    binding, contract = _binding()

    async def write(request: ToolExecutionRequest) -> ToolExecutionResult:
        output = {"path": "src/new.py", "content": "ok"}
        return ToolExecutionResult(
            delivery_id=request.delivery_id, tool_identity="file.write",
            condition=EffectCondition.SETTLED, output=output,
            output_digest=canonical_digest(output),
        )

    inference = ScriptedInferenceAdapter((
        InferenceResponse(
            action=InferenceAction.CONTINUE, summary="verification complete",
            working_plan=_plan(2),
            tool_calls=(ToolCallProposal(
                proposal_index=0, tool_identity="file.write",
                arguments={"path": "src/new.py", "content": "ok"},
            ),),
            residual_obligations=(),
        ),
        InferenceResponse(
            action=InferenceAction.RESULT_READY, summary="submit result",
            working_plan=_plan(3),
            result_claim={"output_vector": {"files": ["src/new.py"]}, "evidence_ids": []},
            residual_obligations=(),
        ),
    ))
    kernel = NativeExecutorKernel(
        inference=inference,
        tools=NativeToolRegistry((
            ToolDefinition("file.write", "1", "write", {}, "LOCAL_MUTATION", write),
        )),
        checkpoints=_Checkpoints(),
    )

    result = asyncio.run(kernel.run(
        binding=binding, contract=contract, worker_epoch=1, working_plan=_plan(),
    ))

    assert result.terminal_outcome is AttemptTerminalOutcome.RESULT_READY
    assert inference.requests[1].available_tools


def test_kernel_requires_terminal_decision_after_three_ineffective_rounds() -> None:
    binding, contract = _binding()
    binding = binding.model_copy(update={
        "capability_grants": (
            CapabilityGrant(identity="test.run", version="1", scope={}),
        ),
        "resource_envelope": binding.resource_envelope.model_copy(update={
            "max_inference_submissions": 4,
            "max_tool_effects": 4,
        }),
    })

    async def run_test(request: ToolExecutionRequest) -> ToolExecutionResult:
        output = {"returncode": 0, "summary": "already passing"}
        return ToolExecutionResult(
            delivery_id=request.delivery_id,
            tool_identity="test.run",
            condition=EffectCondition.SETTLED,
            output=output,
            output_digest=canonical_digest(output),
        )

    repeated = tuple(
        InferenceResponse(
            action=InferenceAction.CONTINUE,
            summary="repeat verification",
            working_plan=_plan(version),
            tool_calls=(ToolCallProposal(
                proposal_index=0,
                tool_identity="test.run",
                arguments={"command": "pytest -q"},
            ),),
            residual_obligations=("submit the verified result",),
        )
        for version in (2, 3, 4)
    )
    inference = ScriptedInferenceAdapter((*repeated, InferenceResponse(
        action=InferenceAction.RESULT_READY,
        summary="submit result",
        working_plan=_plan(5),
        result_claim={"output_vector": {"files": []}, "evidence_ids": []},
        residual_obligations=(),
    )))
    kernel = NativeExecutorKernel(
        inference=inference,
        tools=NativeToolRegistry((
            ToolDefinition("test.run", "1", "run tests", {}, "READ_ONLY_PROCESS", run_test),
        )),
        checkpoints=_Checkpoints(),
    )

    result = asyncio.run(kernel.run(
        binding=binding, contract=contract, worker_epoch=1, working_plan=_plan(),
    ))

    assert result.terminal_outcome is AttemptTerminalOutcome.RESULT_READY
    assert all(request.available_tools for request in inference.requests[:3])
    assert inference.requests[3].available_tools == ()
    assert len(inference.requests[3].previous_results) == 3


def test_kernel_repairs_one_observed_rejected_provider_decision_without_replay() -> None:
    binding, contract = _binding()

    class RepairingInference:
        requests = []

        async def infer(self, request):
            self.requests.append(request)
            if len(self.requests) == 1:
                raise InferenceDecisionRejected(
                    "TOOL_ARGUMENTS_NOT_OBJECT",
                    "observed tool arguments were rejected",
                )
            return InferenceResponse(
                action=InferenceAction.RESULT_READY,
                summary="repaired from the rejection receipt",
                working_plan=_plan(2),
                result_claim={"output_vector": {"files": []}, "evidence_ids": []},
                residual_obligations=(),
            )

    inference = RepairingInference()
    checkpoints = _Checkpoints()
    result = asyncio.run(NativeExecutorKernel(
        inference=inference,
        tools=NativeToolRegistry(()),
        checkpoints=checkpoints,
    ).run(binding=binding, contract=contract, worker_epoch=1, working_plan=_plan()))

    assert result.terminal_outcome is AttemptTerminalOutcome.RESULT_READY
    assert len(inference.requests) == 2
    assert inference.requests[1].previous_results[0]["tool_identity"] == "inference.decision"
    assert inference.requests[1].previous_results[0]["output"] == {
        "error_type": "InferenceDecisionRejected",
        "reason_code": "TOOL_ARGUMENTS_NOT_OBJECT",
        "response_observed": True,
        "effect_observed": False,
    }
    assert len(checkpoints.items) == 2


def test_kernel_checkpoints_safe_provider_validation_fingerprint() -> None:
    binding, contract = _binding()

    class RejectingInference:
        async def infer(self, request):
            del request
            error = InferenceDecisionRejected(
                "NATIVE_DECISION_SCHEMA_REJECTED",
                "provider output rejected",
            )
            error.validation_issues = (
                {"location": ["result_claim"], "type": "missing"},
            )
            raise error

    checkpoints = _Checkpoints()
    result = asyncio.run(NativeExecutorKernel(
        inference=RejectingInference(),
        tools=NativeToolRegistry(()),
        checkpoints=checkpoints,
    ).run(binding=binding, contract=contract, worker_epoch=1, working_plan=_plan()))

    assert result.terminal_outcome is AttemptTerminalOutcome.UNABLE_TO_COMPLETE
    receipt = checkpoints.items[-1].tool_results[-1]
    assert receipt.output["validation_issues"] == [
        {"location": ["result_claim"], "type": "missing"},
    ]


def test_native_kernel_checkpoints_before_pause_and_before_budget_exhaustion() -> None:
    binding, contract = _binding()
    checkpoints = _Checkpoints()
    kernel = NativeExecutorKernel(
        inference=ScriptedInferenceAdapter(()),
        tools=NativeToolRegistry(()),
        checkpoints=checkpoints,
    )

    async def pause():
        from spg.domain.native_execution import ControlAction
        return ControlAction.PAUSE

    result = asyncio.run(kernel.run(binding=binding, contract=contract, worker_epoch=1, working_plan=_plan(), control_probe=pause))
    assert result.runtime_mode is ExecutionMode.PAUSED
    assert result.terminal_outcome is None
    assert len(checkpoints.items) == 1


def test_kernel_rehydrates_checkpoint_and_committed_receipt_suffix() -> None:
    binding, contract = _binding()
    old_output = {"path": "src/old.py", "bytes": 1}
    suffix_output = {"argv": ["pytest"], "returncode": 0}
    old = ToolExecutionResult(
        delivery_id=uuid4(), tool_identity="file.write",
        condition=EffectCondition.SETTLED, output=old_output,
        output_digest=canonical_digest(old_output),
    )
    suffix = ToolExecutionResult(
        delivery_id=uuid4(), tool_identity="test.run",
        condition=EffectCondition.SETTLED, output=suffix_output,
        output_digest=canonical_digest(suffix_output),
    )
    checkpoint = CheckpointBundleRecord(
        id=uuid4(), session_id=binding.session_id, attempt_id=binding.attempt_id,
        step_sequence=2, worker_epoch=1, condition=CheckpointCondition.COMMITTED,
        source_vector_digest=binding.source_vector.digest or "",
        repository_manifest={},
        execution_manifest={"tool_results": [old.model_dump(mode="json")]},
        semantic_manifest={
            "working_plan": _plan(2).model_dump(mode="json"),
            "residual_obligations": ["finish"],
        },
        content_digest="a" * 64, consistency_class="APPLICATION_CONSISTENT",
        created_at=NOW, committed_at=NOW,
    )
    inference = ScriptedInferenceAdapter((
        InferenceResponse(
            action=InferenceAction.RESULT_READY, summary="recovered",
            working_plan=_plan(3), result_claim={"output_vector": {"files": []}},
            residual_obligations=(),
        ),
    ))

    result = asyncio.run(
        NativeExecutorKernel(
            inference=inference,
            tools=NativeToolRegistry(()),
            checkpoints=_Checkpoints(),
        ).run(
            binding=binding, contract=contract, worker_epoch=2,
            working_plan=_plan(2), prior_checkpoint=checkpoint,
            recovered_results=(suffix,),
        )
    )

    assert result.terminal_outcome is AttemptTerminalOutcome.RESULT_READY
    assert inference.requests[0].step_sequence == 3
    assert tuple(
        item["delivery_id"] for item in inference.requests[0].previous_results
    ) == (str(old.delivery_id), str(suffix.delivery_id))


def test_successor_attempt_keeps_session_step_sequence_monotonic() -> None:
    binding, contract = _binding()
    checkpoint = CheckpointBundleRecord(
        id=uuid4(), session_id=binding.session_id, attempt_id=uuid4(),
        step_sequence=10, worker_epoch=1, condition=CheckpointCondition.COMMITTED,
        source_vector_digest=binding.source_vector.digest or "",
        repository_manifest={}, execution_manifest={},
        semantic_manifest={"working_plan": _plan(10).model_dump(mode="json")},
        content_digest="b" * 64, consistency_class="APPLICATION_CONSISTENT",
        created_at=NOW, committed_at=NOW,
    )
    inference = ScriptedInferenceAdapter((
        InferenceResponse(
            action=InferenceAction.RESULT_READY, summary="successor complete",
            working_plan=_plan(12), result_claim={"output_vector": {"files": []}},
            residual_obligations=(),
        ),
    ))

    asyncio.run(
        NativeExecutorKernel(
            inference=inference, tools=NativeToolRegistry(()), checkpoints=_Checkpoints(),
        ).run(
            binding=binding, contract=contract, worker_epoch=2,
            working_plan=_plan(10), prior_checkpoint=checkpoint,
            session_step_frontier=11,
        )
    )

    assert inference.requests[0].step_sequence == 12


def test_recovery_classifier_never_hides_unknown_effect() -> None:
    binding, _ = _binding()
    from spg.domain.native_execution import EffectClassification, ExecutionEffectRecord
    effect = ExecutionEffectRecord(
        id=uuid4(), step_id=uuid4(), proposal_index=0, tool_identity="file.write", tool_version="1",
        semantic_input={}, semantic_input_digest=canonical_digest({}), classification=EffectClassification.LOCAL_MUTATION,
        condition=EffectCondition.UNKNOWN, created_at=NOW,
    )
    classification = NativeRecoveryClassifier().classify(
        checkpoint=None, effects=(effect,), workspace_available=True, contract_satisfied=False
    )
    assert classification is RecoveryClassification.EFFECT_UNRESOLVED


def test_context_compaction_preserves_exact_invariants_and_evidence_identity() -> None:
    binding, contract = _binding()
    checkpoint = CheckpointBundleRecord(
        id=uuid4(), session_id=binding.session_id, attempt_id=binding.attempt_id,
        step_sequence=3, worker_epoch=1, condition=CheckpointCondition.COMMITTED,
        source_vector_digest=binding.source_vector.digest or "",
        repository_manifest={}, execution_manifest={},
        semantic_manifest={
            "working_plan": _plan(3).model_dump(mode="json"),
            "large_history": "h" * 20000,
            "residual_obligations": ["verify"],
        },
        content_digest="a" * 64, consistency_class="APPLICATION_CONSISTENT",
        created_at=NOW, committed_at=NOW,
    )
    output = {"stdout": "x" * 20000}
    previous = ToolExecutionResult(
        delivery_id=uuid4(), tool_identity="test.run",
        condition=EffectCondition.SETTLED, output=output,
        output_digest=canonical_digest(output),
        evidence=({"type": "TOOL_RECEIPT", "digest": canonical_digest(output)},),
    )

    request = NativeContextAssembler(max_request_bytes=6000).assemble(
        binding=binding, contract=contract, working_plan=_plan(3),
        step_sequence=4, available_tools=(), residual_obligations=("verify",),
        previous_results=(previous,), checkpoint=checkpoint,
    )

    contract_fact = next(
        item for item in request.context_facts if item["fact_type"] == "PWU_CONTRACT"
    )
    checkpoint_fact = next(
        item for item in request.context_facts
        if item["fact_type"] == "RECOVERY_CHECKPOINT"
    )
    assert contract_fact["payload"] == contract.contract_payload
    assert checkpoint_fact["content_digest"] == checkpoint.content_digest
    assert checkpoint_fact["semantic_manifest"]["compacted"] is True
    assert request.previous_results[0]["output"]["compacted"] is True
    assert request.previous_results[0]["output_digest"] == previous.output_digest


def test_context_declares_single_mount_tool_paths_without_mount_prefix() -> None:
    binding, contract = _binding()

    request = NativeContextAssembler().assemble(
        binding=binding,
        contract=contract,
        working_plan=_plan(),
        step_sequence=1,
        available_tools=(),
    )

    convention = next(
        item for item in request.context_facts
        if item["fact_type"] == "TOOL_PATH_CONVENTION"
    )
    assert convention["workspace_root"] == "."
    assert convention["mounts"] == [
        {"mount_id": "primary", "tool_path_prefix": "."},
    ]
    assert "container_path is identity metadata" in convention["rule"]


def test_context_fit_failure_fails_closed_without_dropping_contract() -> None:
    binding, contract = _binding()
    oversized = contract.model_copy(
        update={
            "objective": "x" * 10000,
            "contract_payload": {"objective": "x" * 10000},
        }
    )
    with pytest.raises(NativeContextCapacityError, match="cannot fit|cannot|fit|byte|context"):
        NativeContextAssembler(max_request_bytes=1024).assemble(
            binding=binding, contract=oversized, working_plan=_plan(),
            step_sequence=1, available_tools=(),
        )


def test_tool_host_contracts_cover_bounded_engineering_capabilities() -> None:
    contracts = LocalNativeToolHost(Path.cwd()).registry().contracts()
    identities = {item["identity"] for item in contracts}
    assert identities == {
        "file.read",
        "file.write",
        "process.run",
        "git.status",
        "git.diff",
        "test.run",
        "build.run",
        "dependency.sync",
        "preview.inspect",
    }
    process = next(item for item in contracts if item["identity"] == "process.run")
    assert "python -c are rejected" in process["description"]


def test_tool_host_process_environment_filters_secrets_case_insensitively(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SPG_DATABASE_URL", "must-not-cross")
    monkeypatch.setenv("openai_api_key", "must-not-cross-either")
    (tmp_path / "check_env.py").write_text(
        "import os\n"
        "print(any('DATABASE_URL' in k.upper() or 'API_KEY' in k.upper() for k in os.environ))\n"
        "print(os.environ.get('PYTHONPATH'))\n",
        encoding="utf-8",
    )
    binding, _ = _binding()
    workspace = binding.workspace.model_copy(
        update={
            "host_storage_id": str(tmp_path),
            "mounts": (
                binding.workspace.mounts[0].model_copy(
                    update={"host_path": str(tmp_path)}
                ),
            ),
        }
    )
    proposal = ToolCallProposal(
        proposal_index=0,
        tool_identity="process.run",
        arguments={
            "argv": ["python3", "check_env.py"]
        },
    )
    request = ToolExecutionRequest(
        delivery_id=uuid4(),
        attempt_id=binding.attempt_id,
        worker_epoch=1,
        step_id=uuid4(),
        proposal=proposal,
        capability_grants=(CapabilityGrant(identity="process.run", version="1"),),
        workspace=workspace,
    )
    result = asyncio.run(LocalNativeToolHost(tmp_path).registry().execute(request))
    assert result.condition is EffectCondition.SETTLED
    assert result.output["stdout"].splitlines() == [
        "False",
        str(tmp_path / "src"),
    ]
    assert "must-not-cross" not in str(result.output)


def test_tool_host_observes_missing_file_without_ambiguous_failure(tmp_path: Path) -> None:
    binding, _ = _binding()
    workspace = binding.workspace.model_copy(
        update={
            "host_storage_id": str(tmp_path),
            "mounts": (
                binding.workspace.mounts[0].model_copy(
                    update={"host_path": str(tmp_path)}
                ),
            ),
        }
    )
    request = ToolExecutionRequest(
        delivery_id=uuid4(),
        attempt_id=binding.attempt_id,
        worker_epoch=1,
        step_id=uuid4(),
        proposal=ToolCallProposal(
            proposal_index=0,
            tool_identity="file.read",
            arguments={"path": "src/new.py"},
        ),
        capability_grants=(
            CapabilityGrant(
                identity="file.read", version="1", scope={"paths": ["src/new.py"]}
            ),
        ),
        workspace=workspace,
    )

    result = asyncio.run(LocalNativeToolHost(tmp_path).registry().execute(request))

    assert result.condition is EffectCondition.SETTLED
    assert result.output == {
        "path": "src/new.py",
        "exists": False,
        "content": None,
        "bytes": 0,
        "truncated": False,
    }


def test_tool_host_accepts_python3_pytest_recipe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binding, _ = _binding()
    workspace = binding.workspace.model_copy(
        update={
            "host_storage_id": str(tmp_path),
            "mounts": (
                binding.workspace.mounts[0].model_copy(
                    update={"host_path": str(tmp_path)}
                ),
            ),
        }
    )
    request = ToolExecutionRequest(
        delivery_id=uuid4(),
        attempt_id=binding.attempt_id,
        worker_epoch=1,
        step_id=uuid4(),
        proposal=ToolCallProposal(
            proposal_index=0,
            tool_identity="test.run",
            arguments={
                "argv": ["python3", "-m", "pytest", "tests/test_example.py"],
                "cwd": ".",
            },
        ),
        capability_grants=(CapabilityGrant(identity="test.run", version="1"),),
        workspace=workspace,
    )
    host = LocalNativeToolHost(tmp_path)

    async def accepted(tool_request, identity, *, argv=None, cwd_value=None):
        return ToolExecutionResult(
            delivery_id=tool_request.delivery_id,
            tool_identity=identity,
            condition=EffectCondition.SETTLED,
            output={"argv": argv},
            output_digest=canonical_digest({"argv": argv}),
        )

    monkeypatch.setattr(host, "_run_argv", accepted)

    result = asyncio.run(host.registry().execute(request))

    assert result.condition is EffectCondition.SETTLED
    assert result.output["argv"] == [
        "python3", "-m", "pytest", "tests/test_example.py"
    ]


def test_tool_host_rejects_direct_git_metadata_access(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("secret", encoding="utf-8")
    binding, _ = _binding()
    workspace = binding.workspace.model_copy(
        update={
            "host_storage_id": str(tmp_path),
            "mounts": (
                binding.workspace.mounts[0].model_copy(
                    update={"host_path": str(tmp_path)}
                ),
            ),
        }
    )
    request = ToolExecutionRequest(
        delivery_id=uuid4(), attempt_id=binding.attempt_id, worker_epoch=1,
        step_id=uuid4(),
        proposal=ToolCallProposal(
            proposal_index=0, tool_identity="file.read",
            arguments={"path": ".git/config"},
        ),
        capability_grants=(
            CapabilityGrant(
                identity="file.read", version="1", scope={"paths": [".git/config"]}
            ),
        ),
        workspace=workspace,
    )
    with pytest.raises(ValueError, match="Git metadata"):
        asyncio.run(LocalNativeToolHost(tmp_path).registry().execute(request))


def test_process_tool_routes_through_current_attempt_sandbox(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspaces"
    first = root / "attempt-a"
    second = root / "attempt-b"
    first.mkdir(parents=True)
    second.mkdir()
    (first / "private.txt").write_text("private", encoding="utf-8")
    (second / "check.py").write_text("print('sandboxed')\n", encoding="utf-8")
    binding, _ = _binding()
    manifest = binding.workspace.model_copy(update={
        "host_storage_id": str(second),
        "mounts": (
            binding.workspace.mounts[0].model_copy(update={"host_path": str(second)}),
        ),
    })
    request = ToolExecutionRequest(
        delivery_id=uuid4(), attempt_id=binding.attempt_id, worker_epoch=1,
        step_id=uuid4(),
        proposal=ToolCallProposal(
            proposal_index=0, tool_identity="process.run",
            arguments={"argv": [sys.executable, "check.py"], "cwd": "."},
        ),
        capability_grants=(CapabilityGrant(identity="process.run", version="1"),),
        workspace=manifest,
    )

    class Sandbox:
        invocation = None
        cleaned = None

        def command(self, delivery_id, workspace, cwd, argv):
            self.invocation = (delivery_id, workspace, cwd, argv)
            scratch = root / "scratch"
            scratch.mkdir()
            return argv, scratch

        def cleanup(self, scratch):
            self.cleaned = scratch
            scratch.rmdir()

    sandbox = Sandbox()
    result = asyncio.run(
        LocalNativeToolHost(second, process_sandbox=sandbox).registry().execute(request)
    )

    assert result.condition is EffectCondition.SETTLED
    assert result.output["isolation"] == "landlock-per-delivery"
    assert result.output["stdout"] == "sandboxed\n"
    assert sandbox.invocation == (
        request.delivery_id, second, second, [sys.executable, "check.py"]
    )
    assert sandbox.cleaned == root / "scratch"
    assert "attempt-a" not in str(sandbox.invocation)


def test_tool_host_rejects_hardlink_and_symlink_file_attacks(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("must not cross", encoding="utf-8")
    os.link(secret, workspace / "hardlink.txt")
    (workspace / "escape").symlink_to(outside, target_is_directory=True)
    binding, _ = _binding()
    manifest = binding.workspace.model_copy(
        update={
            "host_storage_id": str(workspace),
            "mounts": (
                binding.workspace.mounts[0].model_copy(
                    update={"host_path": str(workspace)}
                ),
            ),
        }
    )

    def request(path: str) -> ToolExecutionRequest:
        return ToolExecutionRequest(
            delivery_id=uuid4(), attempt_id=binding.attempt_id, worker_epoch=1,
            step_id=uuid4(),
            proposal=ToolCallProposal(
                proposal_index=0, tool_identity="file.read", arguments={"path": path}
            ),
            capability_grants=(
                CapabilityGrant(identity="file.read", version="1", scope={"paths": [path]}),
            ),
            workspace=manifest,
        )

    with pytest.raises(ValueError, match="hard-linked"):
        asyncio.run(LocalNativeToolHost(workspace).registry().execute(request("hardlink.txt")))
    with pytest.raises(OSError):
        asyncio.run(LocalNativeToolHost(workspace).registry().execute(request("escape/secret.txt")))
    assert secret.read_text(encoding="utf-8") == "must not cross"


def test_tool_host_write_is_descriptor_anchored_across_symlink_race(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    inside = workspace / "safe"
    held = workspace / "safe-held"
    inside.mkdir(parents=True)
    outside.mkdir()
    (outside / "value.txt").write_text("outside", encoding="utf-8")
    binding, _ = _binding()
    manifest = binding.workspace.model_copy(update={
        "host_storage_id": str(workspace),
        "mounts": (
            binding.workspace.mounts[0].model_copy(
                update={"host_path": str(workspace)}
            ),
        ),
    })
    request = ToolExecutionRequest(
        delivery_id=uuid4(), attempt_id=binding.attempt_id, worker_epoch=1,
        step_id=uuid4(),
        proposal=ToolCallProposal(
            proposal_index=0, tool_identity="file.write",
            arguments={"path": "safe/value.txt", "content": "inside"},
        ),
        capability_grants=(CapabilityGrant(
            identity="file.write", version="1",
            scope={"paths": ["safe/value.txt"]},
        ),),
        workspace=manifest,
    )
    host = LocalNativeToolHost(workspace)
    original = host._parent_directory

    @contextmanager
    def race(relative: str, *, create: bool):
        with original(relative, create=create) as opened:
            inside.rename(held)
            inside.symlink_to(outside, target_is_directory=True)
            yield opened

    host._parent_directory = race
    result = asyncio.run(host.registry().execute(request))

    assert result.condition is EffectCondition.SETTLED
    assert (outside / "value.txt").read_text(encoding="utf-8") == "outside"
    assert (held / "value.txt").read_text(encoding="utf-8") == "inside"


def test_tool_host_api_accepts_multiple_mounts_under_one_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_root = tmp_path / "workspaces"
    workspace = workspace_root / "attempt-1"
    first = workspace / "api"
    second = workspace / "client"
    first.mkdir(parents=True)
    second.mkdir()
    (second / "README.md").write_text("client", encoding="utf-8")
    monkeypatch.setenv("SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT", str(workspace_root))
    monkeypatch.setenv("SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN", "test-internal-token")
    binding, _ = _binding()
    manifest = binding.workspace.model_copy(
        update={
            "host_storage_id": str(workspace),
            "mounts": (
                WorkspaceMount(
                    mount_id="api", host_path=str(first), container_path="/workspace/api",
                    writable=True, write_scope=("src",), forbidden_paths=(".git",),
                ),
                WorkspaceMount(
                    mount_id="client", host_path=str(second), container_path="/workspace/client",
                    writable=True, write_scope=("README.md",), forbidden_paths=(".git",),
                ),
            ),
        }
    )
    request = ToolExecutionRequest(
        delivery_id=uuid4(), attempt_id=binding.attempt_id, worker_epoch=1,
        step_id=uuid4(),
        proposal=ToolCallProposal(
            proposal_index=0, tool_identity="file.read",
            arguments={"path": "client/README.md"},
        ),
        capability_grants=(
            CapabilityGrant(identity="file.read", version="1", scope={"paths": ["client"]}),
        ),
        workspace=manifest,
    )
    with TestClient(create_tool_host_application()) as client:
        response = client.post(
            "/internal/native-tools/execute",
            headers={
                "X-Watt-Internal-Token": "test-internal-token",
                "Content-Type": "application/json",
            },
            content=request.model_dump_json(),
        )
    assert response.status_code == 200, response.text
    assert response.json()["output"]["content"] == "client"


def test_tool_host_spools_receipt_across_restart_and_rejects_delivery_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_root = tmp_path / "workspaces"
    workspace = workspace_root / "attempt-1"
    workspace.mkdir(parents=True)
    spool = tmp_path / "receipts"
    binding, _ = _binding()
    manifest = binding.workspace.model_copy(
        update={
            "host_storage_id": str(workspace),
            "mounts": (
                binding.workspace.mounts[0].model_copy(
                    update={"host_path": str(workspace), "write_scope": ("result.txt",)}
                ),
            ),
        }
    )
    request = ToolExecutionRequest(
        delivery_id=uuid4(), attempt_id=binding.attempt_id, worker_epoch=1,
        step_id=uuid4(),
        proposal=ToolCallProposal(
            proposal_index=0, tool_identity="file.write",
            arguments={"path": "result.txt", "content": "durable"},
        ),
        capability_grants=(CapabilityGrant(
            identity="file.write", version="1", scope={"paths": ["result.txt"]},
        ),),
        workspace=manifest,
    )

    def application():
        monkeypatch.setenv("SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT", str(workspace_root))
        monkeypatch.setenv("SPG_NATIVE_EXECUTOR_RECEIPT_SPOOL_ROOT", str(spool))
        monkeypatch.setenv("SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN", "test-internal-token")
        return create_tool_host_application()

    headers={
        "X-Watt-Internal-Token": "test-internal-token",
        "Content-Type": "application/json",
    }
    with TestClient(application()) as client:
        first = client.post(
            "/internal/native-tools/execute", headers=headers,
            content=request.model_dump_json(),
        )
    assert first.status_code == 200
    assert (workspace / "result.txt").read_text(encoding="utf-8") == "durable"

    with TestClient(application()) as restarted:
        recovered = restarted.get(
            f"/internal/native-tools/executions/{request.delivery_id}/receipt",
            headers=headers,
        )
        replay = restarted.post(
            "/internal/native-tools/execute", headers=headers,
            content=request.model_dump_json(),
        )
        collision = restarted.post(
            "/internal/native-tools/execute", headers=headers,
            content=request.model_copy(update={
                "proposal": request.proposal.model_copy(update={
                    "arguments": {"path": "result.txt", "content": "different"},
                })
            }).model_dump_json(),
        )

    assert recovered.status_code == 200
    assert replay.json() == first.json()
    assert collision.status_code == 409
    assert (workspace / "result.txt").read_text(encoding="utf-8") == "durable"


def test_tool_host_backpressures_before_effect_when_receipt_spool_is_full(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_root = tmp_path / "workspaces"
    workspace = workspace_root / "attempt-1"
    workspace.mkdir(parents=True)
    binding, _ = _binding()
    request = ToolExecutionRequest(
        delivery_id=uuid4(), attempt_id=binding.attempt_id, worker_epoch=1,
        step_id=uuid4(),
        proposal=ToolCallProposal(
            proposal_index=0, tool_identity="file.write",
            arguments={"path": "must-not-exist.txt", "content": "no effect"},
        ),
        capability_grants=(CapabilityGrant(
            identity="file.write", version="1", scope={"paths": ["must-not-exist.txt"]},
        ),),
        workspace=binding.workspace.model_copy(update={
            "host_storage_id": str(workspace),
            "mounts": (binding.workspace.mounts[0].model_copy(update={
                "host_path": str(workspace), "write_scope": ("must-not-exist.txt",),
            }),),
        }),
    )
    monkeypatch.setenv("SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT", str(workspace_root))
    monkeypatch.setenv("SPG_NATIVE_EXECUTOR_RECEIPT_SPOOL_ROOT", str(tmp_path / "receipts"))
    monkeypatch.setenv("SPG_NATIVE_EXECUTOR_RECEIPT_SPOOL_MAX_BYTES", "1024")
    monkeypatch.setenv("SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN", "test-internal-token")
    headers = {
        "X-Watt-Internal-Token": "test-internal-token",
        "Content-Type": "application/json",
    }

    with TestClient(create_tool_host_application()) as client:
        response = client.post(
            "/internal/native-tools/execute", headers=headers,
            content=request.model_dump_json(),
        )
        receipt = client.get(
            f"/internal/native-tools/executions/{request.delivery_id}/receipt",
            headers=headers,
        )

    assert response.status_code == 507
    assert response.json()["detail"]["durable_ack"] is False
    assert response.json()["detail"]["effect_admitted"] is False
    assert receipt.status_code == 404
    assert not (workspace / "must-not-exist.txt").exists()


def test_tool_host_api_returns_failed_receipt_for_rejected_recipe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_root = tmp_path / "workspaces"
    workspace = workspace_root / "attempt-1"
    workspace.mkdir(parents=True)
    monkeypatch.setenv("SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT", str(workspace_root))
    monkeypatch.setenv("SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN", "test-internal-token")
    binding, _ = _binding()
    manifest = binding.workspace.model_copy(
        update={
            "host_storage_id": str(workspace),
            "mounts": (
                binding.workspace.mounts[0].model_copy(
                    update={"host_path": str(workspace)}
                ),
            ),
        }
    )
    request = ToolExecutionRequest(
        delivery_id=uuid4(),
        attempt_id=binding.attempt_id,
        worker_epoch=1,
        step_id=uuid4(),
        proposal=ToolCallProposal(
            proposal_index=0,
            tool_identity="process.run",
            arguments={"argv": ["python", "-c", "print('denied')"], "cwd": "."},
        ),
        capability_grants=(CapabilityGrant(identity="process.run", version="1"),),
        workspace=manifest,
    )

    with TestClient(create_tool_host_application()) as client:
        response = client.post(
            "/internal/native-tools/execute",
            headers={"X-Watt-Internal-Token": "test-internal-token"},
            json=request.model_dump(mode="json"),
        )

    assert response.status_code == 200
    assert response.json()["condition"] == "FAILED"
    assert response.json()["output"]["effect_observed"] is False
    assert response.json()["output"]["error_type"] == "ValueError"


def test_openai_capacity_response_is_typed_and_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args, **kwargs):
        del args, kwargs
        raise HTTPError(
            "https://api.openai.com/v1/responses", 429, "capacity", {},
            BytesIO(b'{"error":{"message":"capacity unavailable"}}'),
        )

    monkeypatch.setattr(
        "spg.infrastructure.executor_runtime.inference.urlopen", fail
    )
    adapter = OpenAIResponsesInferenceAdapter(
        model="admitted-test-model", api_key=lambda: "not-a-real-key"
    )
    request = InferenceRequest(
        attempt_id=uuid4(), session_id=uuid4(), step_sequence=1,
        objective="bounded test", working_plan=_plan(), context_facts=(),
        available_tools=(), residual_obligations=(),
    )
    with pytest.raises(InferenceResourceUnavailable) as caught:
        asyncio.run(adapter.infer(request))
    assert caught.value.retryable is True
    assert "not-a-real-key" not in str(caught.value)


def test_openai_response_schema_allows_dynamic_tool_arguments_and_validates_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            del args

        def read(self) -> bytes:
            decision = {
                "action": "CONTINUE",
                "summary": "Inspect the admitted file.",
                "working_plan": _plan().model_dump(mode="json"),
                "tool_calls": [{
                    "proposal_index": 0,
                    "tool_identity": "file.read",
                    "arguments": {"path": "src/example.py"},
                }],
                "result_claim": None,
                "residual_obligations": [],
            }
            return json.dumps({"output_text": json.dumps(decision)}).encode("utf-8")

    def succeed(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(
        "spg.infrastructure.executor_runtime.inference.urlopen", succeed
    )
    adapter = OpenAIResponsesInferenceAdapter(
        model="admitted-test-model", api_key=lambda: "not-a-real-key"
    )
    request = InferenceRequest(
        attempt_id=uuid4(), session_id=uuid4(), step_sequence=1,
        objective="bounded test", working_plan=_plan(), context_facts=(),
        available_tools=(), residual_obligations=(),
    )

    result = asyncio.run(adapter.infer(request))

    payload = captured["payload"]
    assert payload["text"]["format"]["strict"] is False
    assert result.tool_calls[0].arguments == {"path": "src/example.py"}
    assert "not-a-real-key" not in json.dumps(payload)


def test_openai_quota_response_is_typed_and_parked_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args, **kwargs):
        del args, kwargs
        raise HTTPError(
            "https://api.openai.com/v1/responses", 402, "quota", {},
            BytesIO(b'{"error":{"message":"quota unavailable"}}'),
        )

    monkeypatch.setattr(
        "spg.infrastructure.executor_runtime.inference.urlopen", fail
    )
    adapter = OpenAIResponsesInferenceAdapter(
        model="admitted-test-model", api_key=lambda: "not-a-real-key"
    )
    request = InferenceRequest(
        attempt_id=uuid4(), session_id=uuid4(), step_sequence=1,
        objective="bounded test", working_plan=_plan(), context_facts=(),
        available_tools=(), residual_obligations=(),
    )
    with pytest.raises(InferenceResourceUnavailable) as caught:
        asyncio.run(adapter.infer(request))
    assert caught.value.retryable is False
    assert "not-a-real-key" not in str(caught.value)


def test_native_queue_and_controls_are_human_visible_without_claiming_trust() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "src" / "spg" / "web" / "index.html").read_text(encoding="utf-8")
    javascript = (root / "src" / "spg" / "web" / "app.js").read_text(encoding="utf-8")
    for identity in (
        "execution-queue-state",
        "execution-queue-history",
        "native-pause-control",
        "native-resume-control",
        "native-stop-control",
        "native-cancel-control",
        "native-execution-evidence",
    ):
        assert f'id="{identity}"' in html
    assert "/api/native-execution/queue" in javascript
    assert "/api/native-execution/attempts/" in javascript
    assert 'controlNativeExecution("PAUSE")' in javascript
    assert 'controlNativeExecution("RESUME")' in javascript
    assert 'controlNativeExecution("STOP")' in javascript
    assert 'controlNativeExecution("CANCEL")' in javascript
    queue_projection = javascript[
        javascript.index("function renderExecutionQueue"):
        javascript.index("function renderUnderstandingAlignment")
    ]
    assert "trusted_result" not in queue_projection
    assert "Verification" not in queue_projection


def test_process_timeout_terminates_owned_process_group_and_bounds_output(
    tmp_path: Path,
) -> None:
    (tmp_path / "slow_process.py").write_text(
        "import sys, time\n"
        "sys.stdout.write('x' * 40000)\n"
        "sys.stdout.flush()\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    binding, _ = _binding()
    workspace = binding.workspace.model_copy(
        update={
            "host_storage_id": str(tmp_path),
            "mounts": (
                binding.workspace.mounts[0].model_copy(
                    update={"host_path": str(tmp_path)}
                ),
            ),
        }
    )
    request = ToolExecutionRequest(
        delivery_id=uuid4(),
        attempt_id=binding.attempt_id,
        worker_epoch=1,
        step_id=uuid4(),
        proposal=ToolCallProposal(
            proposal_index=0,
            tool_identity="process.run",
            arguments={"argv": [sys.executable, "slow_process.py"], "cwd": "."},
        ),
        capability_grants=(
            CapabilityGrant(identity="process.run", version="1", scope={}),
        ),
        workspace=workspace,
    )

    result = asyncio.run(
        LocalNativeToolHost(tmp_path, timeout_seconds=1).registry().execute(request)
    )

    assert result.condition is EffectCondition.FAILED
    assert result.output["timed_out"] is True
    assert result.output["process_group_terminated"] is True
    assert result.output["returncode"] is not None
    assert result.output["stdout_truncated"] is True
    assert len(result.output["stdout"].encode("utf-8")) == 32 * 1024


def test_mid_tool_pause_cancels_process_before_checkpoint() -> None:
    binding, contract = _binding()
    binding = binding.model_copy(
        update={
            "capability_grants": (
                CapabilityGrant(identity="process.run", version="1", scope={}),
            )
        }
    )
    cancelled = asyncio.Event()

    async def long_process(request: ToolExecutionRequest) -> ToolExecutionResult:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            cancelled.set()
            raise
        raise AssertionError("process should have been interrupted")

    inference = ScriptedInferenceAdapter((
        InferenceResponse(
            action=InferenceAction.CONTINUE,
            summary="run bounded check",
            working_plan=_plan(2),
            tool_calls=(
                ToolCallProposal(
                    proposal_index=0,
                    tool_identity="process.run",
                    arguments={"argv": ["python", "check.py"], "cwd": "."},
                ),
            ),
            residual_obligations=("finish check",),
        ),
    ))
    checkpoints = _Checkpoints()
    kernel = NativeExecutorKernel(
        inference=inference,
        tools=NativeToolRegistry((
            ToolDefinition("process.run", "1", "run", {}, "PROCESS", long_process),
        )),
        checkpoints=checkpoints,
    )
    probes = 0

    async def pause_during_tool():
        nonlocal probes
        probes += 1
        return None if probes == 1 else ControlAction.PAUSE

    result = asyncio.run(
        kernel.run(
            binding=binding,
            contract=contract,
            worker_epoch=1,
            working_plan=_plan(),
            control_probe=pause_during_tool,
        )
    )

    assert cancelled.is_set()
    assert result.runtime_mode is ExecutionMode.PAUSED
    assert result.terminal_outcome is None
    assert result.tool_effects == 1
    assert result.residual_obligations == ("finish check",)
    assert checkpoints.items[-1].tool_results[0].condition is EffectCondition.FAILED
    assert checkpoints.items[-1].tool_results[0].output["process_tree_terminated"] is True


def test_worker_releases_lease_when_provider_decision_is_not_admissible() -> None:
    binding, contract = _binding()
    grant = SimpleNamespace(
        allocation=SimpleNamespace(attempt_id=binding.attempt_id, lease_epoch=1)
    )

    class Runtime:
        result = None

        def allocate(self, offer):
            del offer
            return grant

        def activate_allocation(self, received):
            assert received is grant

        def finish_allocation(self, received, result):
            assert received is grant
            self.result = result

    class Kernel:
        async def run(self, **kwargs):
            del kwargs
            raise InferenceAdapterError("provider response violated the contract")

    runtime = Runtime()
    worker = NativeExecutionWorker(runtime, lambda received: Kernel())
    worker._load_execution_reality = lambda received: (
        SimpleNamespace(binding=binding),
        contract,
        None,
        0,
    )
    worker._latest_checkpoint = lambda attempt_id: None
    worker._uncheckpointed_results = lambda attempt_id, after: ()

    assert asyncio.run(worker.run_once(object())) is True
    assert runtime.result.runtime_mode is ExecutionMode.FINISHED
    assert runtime.result.terminal_outcome is AttemptTerminalOutcome.UNABLE_TO_COMPLETE
    assert "no admissible native execution decision" in runtime.result.summary


def test_worker_parks_response_unknown_without_retrying_or_discarding_checkpoint() -> None:
    binding, contract = _binding()
    grant = SimpleNamespace(
        allocation=SimpleNamespace(attempt_id=binding.attempt_id, lease_epoch=1)
    )
    checkpoint = CheckpointBundleRecord(
        id=uuid4(), session_id=binding.session_id, attempt_id=binding.attempt_id,
        step_sequence=2, worker_epoch=1, condition=CheckpointCondition.COMMITTED,
        source_vector_digest=binding.source_vector.digest or "",
        repository_manifest={}, execution_manifest={},
        semantic_manifest={
            "working_plan": _plan(2).model_dump(mode="json"),
            "residual_obligations": ["repair failing lowercase case"],
        },
        content_digest="f" * 64, consistency_class="APPLICATION_CONSISTENT",
        created_at=NOW, committed_at=NOW,
    )

    class Runtime:
        result = None

        def allocate(self, offer):
            del offer
            return grant

        def activate_allocation(self, received):
            assert received is grant

        def finish_allocation(self, received, result):
            assert received is grant
            self.result = result

    class Kernel:
        async def run(self, **kwargs):
            del kwargs
            raise InferenceTransportUnknown("response boundary became unknown")

    runtime = Runtime()
    worker = NativeExecutionWorker(runtime, lambda received: Kernel())
    worker._load_execution_reality = lambda received: (
        SimpleNamespace(binding=binding), contract, checkpoint, checkpoint.step_sequence,
    )
    worker._latest_checkpoint = lambda attempt_id: checkpoint
    worker._uncheckpointed_results = lambda attempt_id, after: ()

    assert asyncio.run(worker.run_once(object())) is True
    assert runtime.result.runtime_mode is ExecutionMode.WAITING_RESOURCE
    assert runtime.result.terminal_outcome is None
    assert runtime.result.resource_retryable is False
    assert runtime.result.final_checkpoint_id == checkpoint.id
    assert runtime.result.residual_obligations == ("repair failing lowercase case",)


def test_backend_cutover_keeps_active_handle_pinned_and_rollback_is_additive() -> None:
    binding, _ = _binding()

    class Backend:
        def __init__(self, identity: str, *, multi: bool) -> None:
            self.identity = identity
            self.multi = multi
            self.started = []
            self.observed = []

        def capabilities(self):
            return BackendCapabilities(
                backend_identity=self.identity,
                backend_version="1",
                binding_schema_versions=(2,),
                supports_pause=self.identity == "watt-native",
                supports_native_checkpoint=self.identity == "watt-native",
                supports_multi_repository=self.multi,
                max_writable_repositories=16 if self.multi else 1,
                environment_profiles=("qualification",),
            )

        async def start(self, admission):
            self.started.append(admission.binding.attempt_id)
            return ExecutionHandle(
                backend_identity=self.identity,
                dispatch_id=uuid4(),
                attempt_id=admission.binding.attempt_id,
                generation=admission.binding.generation,
                opaque_reference=f"{self.identity}:qualification",
            )

        async def observe(self, handle):
            self.observed.append(handle.attempt_id)
            return self.identity

        async def control(self, command):
            return self.identity

    native = Backend("watt-native", multi=True)
    legacy = Backend("legacy-codex", multi=False)
    router = PinnedExecutionBackendRouter((native, legacy), default_backend="watt-native")
    native_admission = SimpleNamespace(binding=binding)
    native_handle = asyncio.run(router.start(native_admission))

    router.set_default("legacy-codex")
    assert asyncio.run(router.observe(native_handle)) == "watt-native"
    with pytest.raises(NativeExecutionConflict, match="pinned"):
        asyncio.run(router.start(native_admission))

    legacy_binding = binding.model_copy(
        update={"backend_implementation": "legacy-codex", "attempt_id": uuid4()}
    )
    legacy_handle = asyncio.run(
        router.start(SimpleNamespace(binding=legacy_binding))
    )
    assert legacy_handle.backend_identity == "legacy-codex"

    router.set_default("watt-native")
    assert asyncio.run(router.observe(legacy_handle)) == "legacy-codex"
    assert asyncio.run(router.observe(native_handle)) == "watt-native"


def test_worker_shutdown_stale_heartbeat_does_not_mask_kernel_failure() -> None:
    stop = asyncio.Event()

    class Runtime:
        def heartbeat(self, grant, *, lease_seconds):
            del grant, lease_seconds
            stop.set()
            raise NativeExecutionConflict("lease was fenced during shutdown")

    worker = NativeExecutionWorker(Runtime(), lambda grant: None, heartbeat_seconds=1)

    asyncio.run(worker._heartbeat(SimpleNamespace(), stop))


def test_worker_rejects_incompatible_checkpoint_before_provider_or_tool_recovery() -> None:
    binding, contract = _binding()
    grant = SimpleNamespace(
        allocation=SimpleNamespace(attempt_id=binding.attempt_id, lease_epoch=2)
    )
    checkpoint = CheckpointBundleRecord(
        id=uuid4(),
        schema_version=2,
        session_id=binding.session_id,
        attempt_id=binding.attempt_id,
        step_sequence=7,
        worker_epoch=1,
        condition=CheckpointCondition.COMMITTED,
        source_vector_digest=binding.source_vector.digest or "",
        repository_manifest={},
        execution_manifest={},
        semantic_manifest={
            "working_plan": _plan(7).model_dump(mode="json"),
            "residual_obligations": ["preserve incompatible work"],
        },
        content_digest="c" * 64,
        consistency_class="APPLICATION_CONSISTENT",
        created_at=NOW,
        committed_at=NOW,
    )

    class Runtime:
        result = None

        def allocate(self, offer):
            del offer
            return grant

        def activate_allocation(self, received):
            assert received is grant

        def finish_allocation(self, received, result):
            assert received is grant
            self.result = result

    runtime = Runtime()

    def kernel_must_not_be_created(received):
        del received
        raise AssertionError("provider kernel must not be created")

    worker = NativeExecutionWorker(runtime, kernel_must_not_be_created)
    worker._load_execution_reality = lambda received: (
        SimpleNamespace(binding=binding),
        contract,
        checkpoint,
        checkpoint.step_sequence,
    )
    worker._uncheckpointed_results = lambda attempt_id, after: (_ for _ in ()).throw(
        AssertionError("tool receipt recovery must not run")
    )

    assert asyncio.run(worker.run_once(object())) is True
    assert runtime.result.runtime_mode is ExecutionMode.WAITING_RESOURCE
    assert runtime.result.terminal_outcome is None
    assert runtime.result.resource_retryable is False
    assert runtime.result.final_checkpoint_id == checkpoint.id
    assert runtime.result.inference_submissions == 0
    assert runtime.result.tool_effects == 0
    assert runtime.result.residual_obligations == ("preserve incompatible work",)
    assert "schema version 2" in runtime.result.summary


def test_worker_parks_quota_failure_with_checkpoint_residual_work() -> None:
    binding, contract = _binding()
    grant = SimpleNamespace(
        allocation=SimpleNamespace(attempt_id=binding.attempt_id, lease_epoch=1)
    )
    checkpoint = CheckpointBundleRecord(
        id=uuid4(),
        session_id=binding.session_id,
        attempt_id=binding.attempt_id,
        step_sequence=4,
        worker_epoch=1,
        condition=CheckpointCondition.COMMITTED,
        source_vector_digest=binding.source_vector.digest or "",
        repository_manifest={},
        execution_manifest={},
        semantic_manifest={
            "working_plan": _plan(4).model_dump(mode="json"),
            "residual_obligations": ["run only the stale verification"],
        },
        content_digest="a" * 64,
        consistency_class="APPLICATION_CONSISTENT",
        created_at=NOW,
        committed_at=NOW,
    )

    class Runtime:
        result = None

        def allocate(self, offer):
            del offer
            return grant

        def activate_allocation(self, received):
            assert received is grant

        def finish_allocation(self, received, result):
            assert received is grant
            self.result = result

    class Kernel:
        async def run(self, **kwargs):
            del kwargs
            raise InferenceResourceUnavailable("quota unavailable", retryable=False)

    runtime = Runtime()
    worker = NativeExecutionWorker(runtime, lambda received: Kernel())
    worker._load_execution_reality = lambda received: (
        SimpleNamespace(binding=binding),
        contract,
        checkpoint,
        checkpoint.step_sequence,
    )
    worker._latest_checkpoint = lambda attempt_id: checkpoint
    worker._uncheckpointed_results = lambda attempt_id, after: ()

    assert asyncio.run(worker.run_once(object())) is True
    assert runtime.result.runtime_mode is ExecutionMode.WAITING_RESOURCE
    assert runtime.result.resource_retryable is False
    assert runtime.result.final_checkpoint_id == checkpoint.id
    assert runtime.result.step_count == 4
    assert runtime.result.residual_obligations == (
        "run only the stale verification",
    )
