from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from spg.application.executor_runtime import FairCapacityScheduler
from spg.domain.native_execution import (
    AttemptTerminalOutcome,
    CapabilityGrant,
    CheckpointBundleRecord,
    CheckpointCondition,
    EffectCondition,
    ExecutionBindingV2,
    ExecutionMode,
    ExecutionQueueEntryRecord,
    InferenceAction,
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
from spg.executor.recovery import NativeRecoveryClassifier
from spg.executor.tools import NativeToolRegistry, ToolDefinition
from spg.infrastructure.executor_runtime.inference import (
    InferenceResourceUnavailable,
    OpenAIResponsesInferenceAdapter,
    ScriptedInferenceAdapter,
)
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
from spg.infrastructure.executor_runtime.tool_host import LocalNativeToolHost
from spg.tool_host_api import create_tool_host_application


NOW = datetime(2026, 9, 11, 8, 0, tzinfo=timezone.utc)


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
        InferenceResponse(action=InferenceAction.CONTINUE, summary="make change", working_plan=_plan(2), tool_calls=(ToolCallProposal(proposal_index=0, tool_identity="file.write", arguments={"path": "src/new.py", "content": "ok"}),), residual_obligations=("test",)),
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


def test_tool_host_contracts_cover_bounded_engineering_capabilities() -> None:
    identities = {
        item["identity"]
        for item in LocalNativeToolHost(Path.cwd()).registry().contracts()
    }
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


def test_tool_host_process_environment_filters_secrets_case_insensitively(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SPG_DATABASE_URL", "must-not-cross")
    monkeypatch.setenv("openai_api_key", "must-not-cross-either")
    (tmp_path / "check_env.py").write_text(
        "import os\nprint(any('DATABASE_URL' in k.upper() or 'API_KEY' in k.upper() for k in os.environ))\n",
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
            "argv": ["python", "check_env.py"]
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
    assert result.output["stdout"].strip() == "False"
    assert "must-not-cross" not in str(result.output)


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
