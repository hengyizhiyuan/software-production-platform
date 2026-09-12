"""Sequential real-provider runner for Qualification Contract section 7."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys
import time
from uuid import UUID, uuid4

from sqlalchemy import text

from spg.application.bootstrap import bootstrap
from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.application.runtime import RuntimeService
from spg.config import Settings
from spg.domain.native_execution import (
    BackendControlCommand, CapabilityGrant, ControlAction, ExecutionBindingV2,
    ExecutionHandle, ExecutionMode, InferenceAction,
    NativeExecutionAdmission, PWUContractVersionRecord, ResourceEnvelope,
    SourceMember, SourceVector, WorkerOffer, WorkspaceManifest, WorkspaceMount,
    canonical_digest,
)
from spg.domain.runtime import AttemptRequest, CompletionContract, InitialRunRequest, ProductionHorizon
from spg.executor.context import NativeContextAssembler, NativeContextCapacityError
from spg.executor.kernel import NativeExecutorKernel
from spg.infrastructure.executor_runtime.inference import (
    DeepSeekResponsesInferenceAdapter, InferenceResourceUnavailable,
)
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.executor_runtime.remote_tool_host import RemoteNativeToolHost
from spg.infrastructure.executor_runtime.runtime_ports import DurableCheckpointPort, DurableKernelAudit
from spg.infrastructure.executor_runtime.worker import NativeExecutionWorker

try:
    from .evaluator import evaluate
except ImportError:  # Direct execution from the bind-mounted benchmark directory.
    from evaluator import evaluate


ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "spec.json"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def exact_profile(model: str) -> str:
    return f"deepseek-responses:{model}:high"


class BudgetLedger:
    def __init__(self, path: Path, spec: dict):
        self.path, self.spec = path, spec
        self.data = json.loads(path.read_text()) if path.exists() else {
            "schema_version": 1, "spec_digest": canonical_digest(spec),
            "started_at": datetime.now(UTC).isoformat(), "trials": [],
            "provider_requests": [], "actual_cost_rmb": 0.0,
            "prior_conservative_cost_rmb": spec["prior_conservative_provider_spend_rmb"],
            "in_progress": None, "recovery_history": [],
        }
        self.data.setdefault("in_progress", None)
        self.data.setdefault("recovery_history", [])
        self.data.setdefault("pending_provider_requests", [])
        self.data.setdefault("reserved_uncertain_cost_rmb", 0.0)
        self.data.setdefault("provider_request_failures", [])

    def begin_trial(self, trial: dict) -> None:
        current = self.data.get("in_progress")
        if current is not None and current.get("execution_id") != trial["execution_id"]:
            raise RuntimeError("ANOTHER_BENCHMARK_EXECUTION_IS_IN_PROGRESS")
        if current is None:
            self.data["in_progress"] = {
                **trial,
                "started_at": datetime.now(UTC).isoformat(),
                "attempts": [],
                "injection_events": [],
                "consumed_injections": [],
                "human_technical_intervention_count": 0,
            }
            self.flush()

    def add_attempt(self, attempt_id: UUID, pwu_id: UUID, session_id: UUID, model: str, root: Path, *, reason: str) -> None:
        current = self.data["in_progress"]
        identity = str(attempt_id)
        if any(item["attempt_id"] == identity for item in current["attempts"]):
            return
        current["attempts"].append({
            "attempt_id": identity, "pwu_id": str(pwu_id), "session_id": str(session_id),
            "provider_profile": exact_profile(model), "workspace": str(root),
            "reason": reason, "recorded_at": datetime.now(UTC).isoformat(),
        })
        self.flush()

    def event(self, event_type: str, **details) -> None:
        current = self.data.get("in_progress")
        target = current["injection_events"] if current is not None else self.data["recovery_history"]
        target.append({"type": event_type, "at": datetime.now(UTC).isoformat(), **details})
        self.flush()

    def consume_injection(self, name: str) -> None:
        current = self.data["in_progress"]
        if name not in current["consumed_injections"]:
            current["consumed_injections"].append(name)
            self.flush()

    def injection_consumed(self, name: str) -> bool:
        current = self.data.get("in_progress") or {}
        return name in current.get("consumed_injections", [])

    def before_request(self, model: str, request) -> str:
        # A deliberately conservative per-request reserve: 20k uncached input and
        # 20k output tokens at peak price, with an 8 RMB/USD conversion reserve.
        price = self.spec["pricing_usd_per_million_tokens"][model]
        reserve = (20_000 * price["cache_miss_input"] + 20_000 * price["output"]) / 1_000_000 * self.spec["usd_to_rmb_reservation_rate"]
        aggregate = (
            self.data["prior_conservative_cost_rmb"]
            + self.data["actual_cost_rmb"]
            + self.data["reserved_uncertain_cost_rmb"]
            + reserve
        )
        if aggregate > self.spec["hard_cost_limit"]:
            self.flush()
            raise RuntimeError("BENCHMARK_COST_LIMIT_PREDICTED")
        local_request_id=str(uuid4())
        self.data["pending_provider_requests"].append({
            "local_request_id":local_request_id,
            "execution_id":(self.data.get("in_progress") or {}).get("execution_id"),
            "attempt_id":str(request.attempt_id),
            "step_sequence":request.step_sequence,
            "model":model,"provider_profile":exact_profile(model),
            "reserved_cost_rmb":round(reserve,8),
            "started_at":datetime.now(UTC).isoformat(),
            "certainty":"REQUEST_SENT_RESPONSE_UNKNOWN",
        })
        self.data["reserved_uncertain_cost_rmb"]=round(self.data["reserved_uncertain_cost_rmb"]+reserve,8)
        self.flush()
        return local_request_id

    def record(self, model: str, observation, *, request, elapsed_seconds: float, local_request_id: str) -> None:
        usage = observation.usage
        price = self.spec["pricing_usd_per_million_tokens"][model]
        if usage is None:
            cost = (20_000 * price["cache_miss_input"] + 20_000 * price["output"]) / 1_000_000 * self.spec["usd_to_rmb_reservation_rate"]
            usage_payload = None
            certainty = "RESERVED_UNKNOWN"
        else:
            cached = usage.cached_input_tokens or 0
            uncached = max(usage.input_tokens - cached, 0)
            usd = (cached * price["cache_hit_input"] + uncached * price["cache_miss_input"] + usage.output_tokens * price["output"]) / 1_000_000
            cost = usd * self.spec["usd_to_rmb_reservation_rate"]
            usage_payload = usage.model_dump(mode="json")
            certainty = "ESTIMATED_FROM_PROVIDER_USAGE"
        self.data["actual_cost_rmb"] = round(self.data["actual_cost_rmb"] + cost, 8)
        pending=next((item for item in self.data["pending_provider_requests"] if item["local_request_id"]==local_request_id),None)
        if pending is None:
            raise RuntimeError("PROVIDER_REQUEST_RESERVATION_IS_MISSING")
        self.data["pending_provider_requests"].remove(pending)
        self.data["reserved_uncertain_cost_rmb"]=round(max(self.data["reserved_uncertain_cost_rmb"]-pending["reserved_cost_rmb"],0.0),8)
        self.data["provider_requests"].append({
            "request_id": observation.provider_request_id, "model": model,
            "provider_profile": exact_profile(model),
            "execution_id": (self.data.get("in_progress") or {}).get("execution_id"),
            "attempt_id": str(request.attempt_id), "step_sequence": request.step_sequence,
            "usage": usage_payload, "cost_rmb": round(cost, 8), "certainty": certainty,
            "elapsed_seconds": round(elapsed_seconds, 6),
        })
        self.flush()

    def flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n")
        temp.replace(self.path)


class MeteredAdapter:
    def __init__(self, adapter, ledger: BudgetLedger, model: str, injections: set[str], runtime, attempt_id):
        self.adapter, self.ledger, self.model = adapter, ledger, model
        self.injections, self.runtime, self.attempt_id = injections, runtime, attempt_id
        self.calls = 0
        self.useful_edit_observed = False

    async def infer(self, request):
        self.calls += 1
        if "ui_disconnect" in self.injections and not self.ledger.injection_consumed("ui_disconnect"):
            self.ledger.consume_injection("ui_disconnect")
            self.ledger.event("UI_DISCONNECTED_WITH_PRODUCTION_CONTINUING", attempt_id=str(self.attempt_id), before_provider_request=True)
        if "simulated_provider_capacity_before_request" in self.injections and not self.ledger.injection_consumed("simulated_provider_capacity_before_request"):
            self.ledger.consume_injection("simulated_provider_capacity_before_request")
            self.ledger.event("SIMULATED_PROVIDER_CAPACITY", attempt_id=str(self.attempt_id), before_provider_request=True)
            raise InferenceResourceUnavailable("benchmark injected capacity before send", retryable=True)
        if "quota_after_useful_edit" in self.injections and self.useful_edit_observed and not self.ledger.injection_consumed("quota_after_useful_edit"):
            self.ledger.consume_injection("quota_after_useful_edit")
            self.ledger.event("SIMULATED_QUOTA_AFTER_USEFUL_EDIT", attempt_id=str(self.attempt_id), before_provider_request=True)
            raise InferenceResourceUnavailable("benchmark injected quota after useful edit", retryable=False)
        local_request_id=self.ledger.before_request(self.model,request)
        started = time.monotonic()
        try:
            response = await self.adapter.infer(request)
        except BaseException as error:
            observed=self.adapter.last_observation
            if observed is not None:
                self.ledger.record(
                    self.model,observed,request=request,
                    elapsed_seconds=time.monotonic()-started,
                    local_request_id=local_request_id,
                )
            self.ledger.data["provider_request_failures"].append({
                "local_request_id":local_request_id,
                "execution_id":(self.ledger.data.get("in_progress") or {}).get("execution_id"),
                "attempt_id":str(request.attempt_id),"step_sequence":request.step_sequence,
                # Provider exception text may contain request metadata.  The
                # benchmark only needs the stable failure class; keep arbitrary
                # exception bodies out of durable evidence.
                "error_type":type(error).__name__,
                "response_observed":observed is not None,
                "elapsed_seconds":round(time.monotonic()-started,6),
            })
            self.ledger.flush()
            raise
        if response.provider_observation is not None:
            self.ledger.record(
                self.model, response.provider_observation, request=request,
                elapsed_seconds=time.monotonic() - started,
                local_request_id=local_request_id,
            )
        if "worker_loss_before_effect" in self.injections and not self.ledger.injection_consumed("worker_loss_before_effect") and response.action is InferenceAction.CONTINUE:
            self.ledger.consume_injection("worker_loss_before_effect")
            self.ledger.event("WORKER_LOSS_BEFORE_EFFECT", attempt_id=str(self.attempt_id), step_sequence=request.step_sequence)
            raise RuntimeError("BENCHMARK_WORKER_LOSS_BEFORE_EFFECT")
        pause_names = ("graceful_pause_after_first_checkpoint", "model_replacement", "material_human_correction")
        pending_pause = next((name for name in pause_names if name in self.injections and not self.ledger.injection_consumed(name)), None)
        if pending_pause is not None and self.calls == 1:
            self.ledger.consume_injection(pending_pause)
            self.ledger.event("PAUSE_SEGMENT_REQUESTED", injection=pending_pause, attempt_id=str(self.attempt_id))
            state = attempt_state(self.runtime, self.attempt_id)
            self.runtime.control(BackendControlCommand(
                command_id=uuid4(), handle=ExecutionHandle(backend_identity="watt-native", dispatch_id=self.attempt_id, attempt_id=self.attempt_id, generation=state.generation, opaque_reference=f"attempt:{self.attempt_id}"),
                action=ControlAction.PAUSE, expected_control_version=state.control_version,
                actor_identity="human:continuity-benchmark-authorized", reason="preassigned benchmark segmentation",
            ))
        return response


class BenchmarkAudit:
    """Record useful work and crash only after the durable tool receipt exists."""

    def __init__(self, delegate, adapter: MeteredAdapter, ledger: BudgetLedger, injections: set[str]):
        self.delegate, self.adapter, self.ledger, self.injections = delegate, adapter, ledger, injections
        self.tools: dict[UUID, str] = {}

    async def begin_inference(self, request):
        return await self.delegate.begin_inference(request)

    async def finish_inference(self, step_id, response, error):
        return await self.delegate.finish_inference(step_id, response, error)

    async def begin_tool(self, step_id, request):
        effect_id = await self.delegate.begin_tool(step_id, request)
        self.tools[effect_id] = request.proposal.tool_identity
        return effect_id

    async def finish_tool(self, effect_id, request, result, error):
        await self.delegate.finish_tool(effect_id, request, result, error)
        identity = self.tools.get(effect_id, request.proposal.tool_identity)
        if result is not None and result.condition.value == "SETTLED" and identity == "file.write":
            self.adapter.useful_edit_observed = True
        crash_name = None
        if identity == "test.run" and "worker_loss_during_test" in self.injections:
            crash_name = "worker_loss_during_test"
        elif identity == "file.write" and "two_repo_partial_convergence" in self.injections:
            crash_name = "two_repo_partial_convergence"
        if crash_name and not self.ledger.injection_consumed(crash_name):
            self.ledger.consume_injection(crash_name)
            self.ledger.event(
                "WORKER_LOSS_AFTER_DURABLE_RECEIPT",
                injection=crash_name,
                attempt_id=str(self.adapter.attempt_id),
                effect_id=str(effect_id),
            )
            raise RuntimeError(f"BENCHMARK_{crash_name.upper()}")


class CrashAfterReceiptCheckpoint:
    def __init__(self, delegate, ledger: BudgetLedger, injections: set[str], attempt_id: UUID):
        self.delegate, self.ledger, self.injections, self.attempt_id = delegate, ledger, injections, attempt_id

    async def commit(self, checkpoint):
        name = "worker_loss_after_effect_before_checkpoint"
        if name in self.injections and not self.ledger.injection_consumed(name) and checkpoint.tool_results:
            self.ledger.consume_injection(name)
            self.ledger.event("WORKER_LOSS_AFTER_EFFECT_BEFORE_CHECKPOINT", attempt_id=str(self.attempt_id), step_sequence=checkpoint.step_sequence)
            raise RuntimeError("BENCHMARK_WORKER_LOSS_AFTER_RECEIPT")
        record = await self.delegate.commit(checkpoint)
        stale = "stale_worker_late_publication"
        if stale in self.injections and not self.ledger.injection_consumed(stale):
            self.ledger.consume_injection(stale)
            self.ledger.event("WORKER_LOSS_AFTER_CHECKPOINT", attempt_id=str(self.attempt_id), checkpoint_id=str(record.id))
            raise RuntimeError("BENCHMARK_STALE_WORKER_AFTER_CHECKPOINT")
        return record


class BenchmarkContext(NativeContextAssembler):
    def __init__(self, ledger: BudgetLedger, injections: set[str]):
        super().__init__()
        self.ledger, self.injections = ledger, injections

    def assemble(self, **kwargs):
        name = "compaction_failure"
        if kwargs.get("checkpoint") is not None and name in self.injections and not self.ledger.injection_consumed(name):
            self.ledger.consume_injection(name)
            self.ledger.event("SIMULATED_COMPACTION_FAILURE", before_provider_request=True)
            raise NativeContextCapacityError("benchmark injected compaction failure")
        return super().assemble(**kwargs)


class BenchmarkTools:
    def __init__(self, delegate, ledger: BudgetLedger, injections: set[str], runtime, attempt_id: UUID):
        self.delegate, self.ledger, self.injections = delegate, ledger, injections
        self.runtime, self.attempt_id = runtime, attempt_id

    def contracts(self):
        return self.delegate.contracts()

    async def execute(self, request):
        name = "graceful_pause_during_test"
        if request.proposal.tool_identity == "test.run" and name in self.injections and not self.ledger.injection_consumed(name):
            self.ledger.consume_injection(name)
            state = attempt_state(self.runtime, self.attempt_id)
            self.runtime.control(BackendControlCommand(
                command_id=uuid4(),
                handle=ExecutionHandle(
                    backend_identity="watt-native", dispatch_id=self.attempt_id,
                    attempt_id=self.attempt_id, generation=state.generation,
                    opaque_reference=f"attempt:{self.attempt_id}",
                ),
                action=ControlAction.PAUSE,
                expected_control_version=state.control_version,
                actor_identity="human:continuity-benchmark-authorized",
                reason="preassigned graceful pause during test dispatch",
            ))
            self.ledger.event("GRACEFUL_PAUSE_DURING_TEST", attempt_id=str(self.attempt_id))
            # Give the kernel control probe a deterministic cancellation window.
            await asyncio.sleep(0.25)
        return await self.delegate.execute(request)


def attempt_state(runtime, attempt_id):
    with runtime.database.unit_of_work() as uow:
        return NativeExecutionStore(uow.session).attempt_state(attempt_id)


def prepare_repositories(root: Path, task: dict) -> tuple[Path, dict[str, Path]]:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    repos = {}
    repository_specs = task["repositories"]
    single_primary = tuple(repository_specs) == ("primary",)
    for mount_id, repo_spec in sorted(repository_specs.items()):
        repo = root if single_primary else root / mount_id
        if not single_primary:
            repo.mkdir()
        for relative, content in repo_spec["initial_files"].items():
            target = repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        git(repo, "init", "-b", "main")
        git(repo, "config", "user.name", "Watt Continuity Benchmark")
        git(repo, "config", "user.email", "continuity@example.invalid")
        git(repo, "add", ".")
        git(repo, "commit", "-m", "frozen benchmark fixture")
        repos[mount_id] = repo
    return root, repos


def verification_labels(task: dict) -> tuple[str, ...]:
    return tuple(
        item if isinstance(item, str) else f"{item['cwd']}: {item['command']}"
        for item in task["verification"]
    )


def admission_for(runtime_service: RuntimeService, task: dict, root: Path, repos: dict[str, Path], model: str, permitted: tuple[str, ...], *, prior_attempt=None, attempt_override=None, session_id=None, revision=1, contract_additions: dict | None = None):
    multi_repository = len(repos) > 1

    def workspace_path(mount_id: str, relative: str) -> str:
        return f"{mount_id}/{relative}" if multi_repository else relative

    completion = CompletionContract(
        required_outputs=tuple(
            workspace_path(mount_id, path)
            for mount_id, repo in task["repositories"].items()
            for path in repo["write_scope"]
        ),
        required_changes=(task["objective"],), forbidden_changes=("outside exact write scopes",),
        verification_obligations=verification_labels(task),
    )
    if prior_attempt is None:
        spine = runtime_service.create_initial_runtime_spine(InitialRunRequest(
            intent_ref=f"continuity:{task['id']}", goal="qualify PWU continuity",
            production_horizon=ProductionHorizon.CODE,
            initial_work_unit_objective=task["objective"], completion_contract=completion,
        ))
        attempt = runtime_service.create_initial_attempt(spine.work_unit.id, AttemptRequest(provider_ref=exact_profile(model)))
        pwu_id, work_id = spine.work_unit.id, spine.run.id
        session_id = uuid4()
    else:
        with runtime_service.database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            prior_binding = store.attempt_binding(prior_attempt.id).binding
            prior_contract = store.contract(prior_binding.pwu_contract_version_id)
        attempt = attempt_override or runtime_service.retry_attempt(prior_attempt.id, AttemptRequest(provider_ref=exact_profile(model)))
        pwu_id = prior_attempt.work_unit_id
        work_id = prior_binding.work_id
    members, mounts = [], []
    for mount_id, repo in sorted(repos.items()):
        spec = task["repositories"][mount_id]
        commit, tree = git(repo, "rev-parse", "HEAD"), git(repo, "rev-parse", "HEAD^{tree}")
        members.append(SourceMember(mount_id=mount_id, repository_identity=str(repo), source_baseline_ref="refs/heads/main", source_commit_oid=commit, source_tree_oid=tree, container_path=f"/workspace/{mount_id}", read_scope=tuple(spec["initial_files"]), write_scope=tuple(spec["write_scope"]), forbidden_paths=(".git",)))
        mounts.append(WorkspaceMount(mount_id=mount_id, host_path=str(repo), container_path=f"/workspace/{mount_id}", writable=True, write_scope=tuple(spec["write_scope"]), forbidden_paths=(".git",)))
    vector = SourceVector(members=tuple(members))
    workspace = WorkspaceManifest(workspace_id=uuid4(), work_id=work_id, pwu_id=pwu_id, attempt_id=attempt.id, source_vector_digest=vector.digest or "", host_storage_id=str(root), environment_profile_digest=canonical_digest({"profile":"continuity-v2"}), mounts=tuple(mounts), evidence_namespace=f"continuity-v2:{attempt.id}", retention_policy="benchmark-retained")
    if prior_attempt is not None and contract_additions is None:
        contract = prior_contract
        payload = dict(contract.contract_payload)
    else:
        payload = (
            dict(prior_contract.contract_payload)
            if prior_attempt is not None
            else {"objective": task["objective"], "acceptance": task["acceptance"], "verification": task["verification"], "repositories": task["repositories"]}
        )
        if contract_additions:
            payload.update(contract_additions)
        contract = PWUContractVersionRecord(id=uuid4(), pwu_id=pwu_id, revision=revision, objective=task["objective"], contract_payload=payload, contract_digest=canonical_digest(payload), created_at=datetime.now(UTC))
    envelope = ResourceEnvelope(envelope_id=uuid4(), policy_version="continuity-v2", max_inference_submissions=30, max_tool_effects=100, max_active_seconds=1800, max_cost_units=10000, provider_profile=exact_profile(model), permitted_provider_profiles=permitted)
    admitted_paths = [
        workspace_path(mount_id, path)
        for mount_id, repo in task["repositories"].items()
        for path in repo["write_scope"]
    ]
    inspection_paths = sorted(set(admitted_paths + [
        workspace_path(mount_id, path)
        for mount_id, repo in task["repositories"].items()
        for path in repo["initial_files"]
    ]))
    grants = tuple(
        CapabilityGrant(
            identity=name,
            version="1",
            scope={
                "paths": admitted_paths if name == "file.write" else inspection_paths,
                "forbidden_paths": [".git"],
            },
        )
        for name in (
            "file.read", "file.write", "process.run", "git.status", "git.diff",
            "test.run", "build.run", "dependency.sync", "preview.inspect",
        )
    )
    binding = ExecutionBindingV2(work_id=work_id, steering_decision_id=uuid4(), pwu_id=pwu_id, pwu_contract_version_id=contract.id, pwu_contract_digest=contract.contract_digest, attempt_id=attempt.id, generation=attempt.generation, session_id=session_id, source_vector=vector, workspace=workspace, context_package_ref=f"continuity-v2:{task['id']}", materialized_input_digest=canonical_digest(payload), backend_implementation="watt-native", backend_version="1", inference_profile=exact_profile(model), capability_grants=grants, resource_envelope=envelope, obligation_references=verification_labels(task) + tuple(task["acceptance"]))
    return attempt, session_id, NativeExecutionAdmission(command_id=uuid4(), actor_identity="human:continuity-benchmark-authorized", fairness_group=f"continuity:{task['id']}", binding=binding, contract=contract, materialization_path=str(root), required_resource_profile="standard", available_at=datetime.now(UTC))


def validate(root: Path, task: dict) -> list[dict]:
    results=[]
    for verification in task["verification"]:
        if isinstance(verification, str):
            command, cwd = verification, root
        else:
            command = verification["command"]
            cwd = root / verification["cwd"]
        safe_env={
            "PATH":os.environ.get("PATH",""),
            "PYTHONPATH":os.pathsep.join((str(cwd),str(cwd/"src"))),
        }
        if command.startswith("preview.inspect "):
            path=cwd/command.split(" ",1)[1]
            results.append({"command":command,"cwd":str(cwd.relative_to(root)) or ".","returncode":0 if path.is_file() else 1})
            continue
        argv=shlex.split(command)
        if argv and argv[0] == "pytest":
            argv=[sys.executable,"-m","pytest",*argv[1:]]
        proc=subprocess.run(argv,cwd=cwd,env=safe_env,capture_output=True,text=True,timeout=180)
        results.append({"command":command,"cwd":str(cwd.relative_to(root)) or ".","returncode":proc.returncode,"stdout":proc.stdout[-2000:],"stderr":proc.stderr[-2000:]})
    return results


def repositories_at(root: Path, task: dict) -> dict[str, Path]:
    if tuple(task["repositories"]) == ("primary",):
        return {"primary": root}
    return {mount_id: root / mount_id for mount_id in task["repositories"]}


def copied_workspace(root: Path, suffix: str, task: dict) -> tuple[Path, dict[str, Path]]:
    target = root.with_name(f"{root.name}-{suffix}")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(root, target, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    return target, repositories_at(target, task)


def stop_attempt(runtime: NativeExecutorRuntimeService, attempt_id: UUID, reason: str) -> None:
    state = attempt_state(runtime, attempt_id)
    if state.runtime_mode is ExecutionMode.FINISHED:
        return
    receipt = runtime.control(BackendControlCommand(
        command_id=uuid4(),
        handle=ExecutionHandle(
            backend_identity="watt-native", dispatch_id=attempt_id,
            attempt_id=attempt_id, generation=state.generation,
            opaque_reference=f"attempt:{attempt_id}",
        ),
        action=ControlAction.STOP,
        expected_control_version=state.control_version,
        actor_identity="human:continuity-benchmark-authorized",
        reason=reason,
    ))
    if not receipt.accepted:
        raise RuntimeError(f"BENCHMARK_STOP_REJECTED:{attempt_id}")
    final_state = attempt_state(runtime, attempt_id)
    if final_state.runtime_mode is ExecutionMode.FINISHED:
        with runtime.database.unit_of_work() as uow:
            uow.session.execute(text("""
                UPDATE execution_control_requests
                SET condition='APPLIED', applied_at=COALESCE(applied_at,now())
                WHERE attempt_id=:attempt_id AND action='STOP' AND condition='REQUESTED'
            """), {"attempt_id": attempt_id})
            uow.commit()


def resolve_read_only_uncertainty(database, attempt_id: UUID, ledger: BudgetLedger) -> None:
    """Resolve an interrupted read as no-mutation without replaying it."""
    with database.unit_of_work() as uow:
        rows = uow.session.execute(text("""
            SELECT e.id, e.classification
            FROM execution_effects e
            JOIN execution_steps s ON s.id=e.step_id
            WHERE s.attempt_id=:attempt_id
              AND e.condition IN ('INTENDED','STARTING','ACTIVE','UNKNOWN')
            ORDER BY s.sequence,e.proposal_index
        """), {"attempt_id": attempt_id}).all()
        if not rows:
            return
        if any(classification != "READ" for _, classification in rows):
            raise RuntimeError("NON_READ_EFFECT_UNCERTAINTY_REQUIRES_EXTERNAL_RECONCILIATION")
        output = {
            "reconciliation": "interrupted read result discarded; read has no mutation",
            "effect_observed": False,
        }
        digest = canonical_digest(output)
        for effect_id, _ in rows:
            uow.session.execute(text("UPDATE execution_effects SET condition='FAILED' WHERE id=:id"), {"id": effect_id})
            uow.session.execute(text("""
                UPDATE effect_receipts
                SET condition='FAILED', output=CAST(:output AS jsonb), output_digest=:digest
                WHERE effect_id=:id AND condition='UNKNOWN'
            """), {"id": effect_id, "output": json.dumps(output), "digest": digest})
            uow.session.execute(text("""
                UPDATE execution_resource_usage
                SET certainty='ACTUAL', condition='CONSUMED',
                    evidence=CAST(:evidence AS jsonb)
                WHERE attempt_id=:attempt_id AND reservation_key=:key
            """), {
                "attempt_id": attempt_id, "key": f"tool:{effect_id}",
                "evidence": json.dumps({"effect_id": str(effect_id), "reconciled_read_only": True}),
            })
        uow.session.execute(text("""
            UPDATE native_attempt_states
            SET effect_uncertainty=false, blocker_reasons='[]'::jsonb,
                version=version+1, updated_at=now()
            WHERE attempt_id=:attempt_id
        """), {"attempt_id": attempt_id})
        uow.session.execute(text("""
            UPDATE execution_recovery_cases
            SET effect_uncertainty=false,
                resolution='read-only uncertainty reconciled without replay',
                resolved_at=now()
            WHERE attempt_id=:attempt_id AND resolved_at IS NULL
        """), {"attempt_id": attempt_id})
        uow.commit()
    ledger.event("READ_ONLY_EFFECT_RECONCILED_WITHOUT_REPLAY", attempt_id=str(attempt_id), effect_count=len(rows))


def reconcile_prelaunch_tool_rejection(database, attempt_id: UUID, ledger: BudgetLedger) -> bool:
    """Recover a process proposal proven rejected before process creation."""
    with database.unit_of_work() as uow:
        rows = uow.session.execute(text("""
            SELECT e.id,e.classification,e.semantic_input
            FROM execution_effects e
            JOIN execution_steps s ON s.id=e.step_id
            WHERE s.attempt_id=:attempt_id
              AND e.condition IN ('INTENDED','STARTING','ACTIVE','UNKNOWN')
        """), {"attempt_id": attempt_id}).all()
        if not rows:
            return False
        def proven_prelaunch(row) -> bool:
            _, classification, semantic = row
            cwd = (semantic or {}).get("cwd")
            return classification == "PROCESS" and isinstance(cwd,str) and Path(cwd).is_absolute()
        if not all(proven_prelaunch(row) for row in rows):
            return False
        active = uow.session.execute(text("""
            SELECT count(*) FROM execution_allocations
            WHERE attempt_id=:attempt_id AND condition IN ('ISSUED','ACTIVE')
        """), {"attempt_id": attempt_id}).scalar_one()
        if active:
            raise RuntimeError("PRELAUNCH_REJECTION_STILL_HAS_ACTIVE_ALLOCATION")
        for effect_id, _, semantic in rows:
            output={
                "error_type":"WorkspaceMaterializationError",
                "message":"process cwd was absolute and rejected before launch",
                "effect_observed":False,
                "reconciled_from":semantic,
            }
            digest=canonical_digest(output)
            uow.session.execute(text("UPDATE execution_effects SET condition='FAILED' WHERE id=:id"),{"id":effect_id})
            uow.session.execute(text("""
                UPDATE effect_receipts
                SET condition='FAILED',output=CAST(:output AS jsonb),output_digest=:digest
                WHERE effect_id=:id AND condition='UNKNOWN'
            """),{"id":effect_id,"output":json.dumps(output),"digest":digest})
            uow.session.execute(text("""
                UPDATE execution_resource_usage
                SET certainty='ACTUAL',condition='CONSUMED',evidence=CAST(:evidence AS jsonb)
                WHERE attempt_id=:attempt_id AND reservation_key=:key
            """),{
                "attempt_id":attempt_id,"key":f"tool:{effect_id}",
                "evidence":json.dumps({"effect_id":str(effect_id),"rejected_before_process_launch":True}),
            })
        uow.session.execute(text("""
            UPDATE executor_queue SET condition='RETURNED_TO_QUEUE',
                wait_reason='prelaunch tool rejection reconciled',resume_count=resume_count+1,
                available_at=now(),version=version+1
            WHERE attempt_id=:attempt_id
        """),{"attempt_id":attempt_id})
        uow.session.execute(text("""
            UPDATE native_attempt_states SET grant_state='GRANTED',runtime_mode='QUEUED',
                terminal_outcome=NULL,effect_uncertainty=false,blocker_reasons='[]'::jsonb,
                version=version+1,updated_at=now()
            WHERE attempt_id=:attempt_id
        """),{"attempt_id":attempt_id})
        uow.session.execute(text("""
            UPDATE execution_recovery_cases SET effect_uncertainty=false,
                resolution='process proposal rejected before launch; same Attempt requeued',resolved_at=now()
            WHERE attempt_id=:attempt_id AND resolved_at IS NULL
        """),{"attempt_id":attempt_id})
        uow.commit()
    ledger.event("PRELAUNCH_TOOL_REJECTION_RECONCILED",attempt_id=str(attempt_id),effect_count=len(rows),same_attempt_requeued=True)
    return True


def settle_superseded_predecessor(database, attempt_id: UUID, ledger: BudgetLedger) -> None:
    """Finish a fenced predecessor only after leases and effects are reconciled."""
    with database.unit_of_work() as uow:
        active_allocations = uow.session.execute(text("""
            SELECT count(*) FROM execution_allocations
            WHERE attempt_id=:attempt_id AND condition IN ('ISSUED','ACTIVE')
        """), {"attempt_id": attempt_id}).scalar_one()
        unresolved = uow.session.execute(text("""
            SELECT count(*) FROM execution_effects e
            JOIN execution_steps s ON s.id=e.step_id
            WHERE s.attempt_id=:attempt_id
              AND e.condition NOT IN ('SETTLED','FAILED')
        """), {"attempt_id": attempt_id}).scalar_one()
        if active_allocations or unresolved:
            raise RuntimeError("SUPERSEDED_PREDECESSOR_IS_NOT_QUIESCENT")
        uow.session.execute(text("""
            UPDATE executor_queue
            SET condition='COMPLETED', wait_reason='superseded after reconciled recovery',
                version=version+1
            WHERE attempt_id=:attempt_id AND condition NOT IN ('COMPLETED','CANCELLED')
        """), {"attempt_id": attempt_id})
        uow.session.execute(text("""
            UPDATE native_attempt_states
            SET grant_state='RELEASED', runtime_mode='FINISHED',
                terminal_outcome='STOPPED', effect_uncertainty=false,
                blocker_reasons='[]'::jsonb, version=version+1, updated_at=now()
            WHERE attempt_id=:attempt_id AND runtime_mode<>'FINISHED'
        """), {"attempt_id": attempt_id})
        uow.session.execute(text("""
            UPDATE execution_control_requests
            SET condition='APPLIED', applied_at=COALESCE(applied_at,now())
            WHERE attempt_id=:attempt_id AND action='STOP' AND condition='REQUESTED'
        """), {"attempt_id": attempt_id})
        uow.commit()
    ledger.event("SUPERSEDED_PREDECESSOR_SETTLED", attempt_id=str(attempt_id), terminal_outcome="STOPPED")


def record_unknown_provider_reservations(spec: dict, ledger: BudgetLedger, database) -> None:
    represented={
        (item.get("attempt_id"),item.get("step_sequence"))
        for item in ledger.data["provider_requests"]+ledger.data["pending_provider_requests"]
    }
    with database.unit_of_work() as uow:
        rows=uow.session.execute(text("""
            SELECT u.attempt_id,s.sequence,b.binding_payload->>'inference_profile',s.started_at
            FROM execution_resource_usage u
            JOIN execution_steps s ON u.reservation_key=('inference:' || s.id::text)
            JOIN native_attempt_bindings b ON b.attempt_id=u.attempt_id
            WHERE u.resource_type='inference_submission'
              AND u.condition='UNKNOWN'
            ORDER BY s.started_at
        """)).all()
    for attempt_id,sequence,profile,started_at in rows:
        key=(str(attempt_id),sequence)
        if key in represented:
            continue
        model=profile.split(":")[1]
        price=spec["pricing_usd_per_million_tokens"][model]
        reserve=(20_000*price["cache_miss_input"]+20_000*price["output"])/1_000_000*spec["usd_to_rmb_reservation_rate"]
        local_id=f"historical-unknown:{attempt_id}:{sequence}"
        ledger.data["pending_provider_requests"].append({
            "local_request_id":local_id,
            "execution_id":(ledger.data.get("in_progress") or {}).get("execution_id"),
            "attempt_id":str(attempt_id),"step_sequence":sequence,
            "model":model,"provider_profile":profile,
            "reserved_cost_rmb":round(reserve,8),
            "started_at":started_at.isoformat(),
            "certainty":"REQUEST_SENT_RESPONSE_UNKNOWN",
        })
        ledger.data["reserved_uncertain_cost_rmb"]=round(ledger.data["reserved_uncertain_cost_rmb"]+reserve,8)
        represented.add(key)
    ledger.flush()


def pwu_inference_usage(database, pwu_id: UUID) -> tuple[int,int]:
    with database.unit_of_work() as uow:
        used=uow.session.execute(text("""
            SELECT count(*)
            FROM execution_resource_usage u
            JOIN execution_resource_envelopes e ON e.id=u.envelope_id
            WHERE e.pwu_id=:pwu_id AND u.resource_type='inference_submission'
              AND u.condition<>'RELEASED'
        """),{"pwu_id":pwu_id}).scalar_one()
        cap=uow.session.execute(text("""
            SELECT min(max_inference_submissions)
            FROM execution_resource_envelopes WHERE pwu_id=:pwu_id
        """),{"pwu_id":pwu_id}).scalar_one()
    if cap is None:
        raise RuntimeError("PWU_INFERENCE_ENVELOPE_IS_MISSING")
    return int(used or 0),int(cap)


def finish_budget_exhausted(database, attempt_id: UUID) -> None:
    with database.unit_of_work() as uow:
        active=uow.session.execute(text("""
            SELECT count(*) FROM execution_allocations
            WHERE attempt_id=:attempt_id AND condition IN ('ISSUED','ACTIVE')
        """),{"attempt_id":attempt_id}).scalar_one()
        if active:
            raise RuntimeError("CANNOT_FINISH_BUDGET_EXHAUSTED_WITH_ACTIVE_ALLOCATION")
        uow.session.execute(text("""
            UPDATE executor_queue SET condition='COMPLETED',
                wait_reason='PWU inference submission pool exhausted',version=version+1
            WHERE attempt_id=:attempt_id
        """),{"attempt_id":attempt_id})
        uow.session.execute(text("""
            UPDATE native_attempt_states SET grant_state='RELEASED',runtime_mode='FINISHED',
                terminal_outcome='BUDGET_EXHAUSTED',effect_uncertainty=false,
                blocker_reasons='[]'::jsonb,version=version+1,updated_at=now()
            WHERE attempt_id=:attempt_id
        """),{"attempt_id":attempt_id})
        uow.commit()


def recover_legacy_first_execution(spec: dict, trial: dict, settings: Settings, ledger: BudgetLedger, database) -> None:
    """Adopt the pre-ledger first execution and continue through a successor."""
    if ledger.data.get("in_progress") is not None or ledger.data["trials"] or not ledger.data["provider_requests"]:
        return
    with database.unit_of_work() as uow:
        row = uow.session.execute(text("""
            SELECT q.attempt_id
            FROM executor_queue q
            WHERE q.fairness_group=:group_name
            ORDER BY q.enqueued_at DESC LIMIT 1
        """), {"group_name": f"continuity:{trial['task_id']}"}).one_or_none()
    if row is None:
        raise RuntimeError("LEGACY_PROVIDER_REQUESTS_EXIST_WITHOUT_ATTEMPT")
    attempt_id = UUID(str(row[0]))
    runtime_service, runtime = RuntimeService(database), NativeExecutorRuntimeService(database)
    old_attempt = runtime_service.get_attempt(attempt_id)
    with database.unit_of_work() as uow:
        old_binding = NativeExecutionStore(uow.session).attempt_binding(attempt_id).binding
    old_root = Path(old_binding.workspace.host_storage_id)
    ledger.begin_trial(trial)
    ledger.add_attempt(attempt_id, old_binding.pwu_id, old_binding.session_id, spec["profiles"]["primary"]["model"], old_root, reason="adopted_interrupted_pre-ledger execution")
    for index, request in enumerate(ledger.data["provider_requests"], start=1):
        request.setdefault("execution_id", trial["execution_id"])
        request.setdefault("attempt_id", str(attempt_id))
        request.setdefault("provider_profile", spec["profiles"]["primary"]["profile_id"])
        request.setdefault("step_sequence", index)
    ledger.event(
        "PRE_LEDGER_EXECUTION_ADOPTED",
        attempt_id=str(attempt_id),
        observed_plan_position=trial["execution_id"],
        note="frozen order begins with B; earlier narrative calling it A was corrected",
    )
    resolve_read_only_uncertainty(database, attempt_id, ledger)
    stop_attempt(runtime, attempt_id, "supersede invalid benchmark mount mapping after safe reconciliation")

    task = next(item for item in spec["tasks"] if item["id"] == trial["task_id"])
    new_root = old_root.with_name(f"{old_root.name}-mount-recovery")
    if new_root.exists():
        shutil.rmtree(new_root)
    new_root.mkdir(parents=True)
    for mount_id in task["repositories"]:
        shutil.copytree(old_root / mount_id, new_root / mount_id, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    # Preserve one repository's useful output in the successor and leave the
    # other as an explicit residual obligation for the preassigned T5 fault.
    for relative in ("src/status_client.py", "tests/test_status_client.py"):
        source = old_root / relative
        if source.exists():
            target = new_root / "client" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    repos = repositories_at(new_root, task)
    permitted = (spec["profiles"]["primary"]["profile_id"], spec["profiles"]["replacement"]["profile_id"])
    successor, session_id, admission = admission_for(
        runtime_service, task, new_root, repos, spec["profiles"]["primary"]["model"], permitted,
        prior_attempt=old_attempt, session_id=old_binding.session_id, revision=2,
        contract_additions={"recovery_note": "client output retained; server output remains residual after mount correction"},
    )
    runtime.admit(admission)
    ledger.add_attempt(successor.id, admission.binding.pwu_id, session_id, spec["profiles"]["primary"]["model"], new_root, reason="successor after mount-path reconciliation")
    ledger.event(
        "SUCCESSOR_ADMITTED_AFTER_HARNESS_RECONCILIATION",
        predecessor_attempt_id=str(attempt_id), successor_attempt_id=str(successor.id),
        retained_client_files=2, duplicated_server_files=2,
        human_technical_intervention_count=0,
    )


def adopt_unadmitted_successor(spec: dict, ledger: BudgetLedger, database) -> None:
    progress=ledger.data.get("in_progress")
    if progress is None or not progress.get("attempts"):
        return
    last=progress["attempts"][-1]
    prior_id=UUID(last["attempt_id"])
    prior_attempt=RuntimeService(database).get_attempt(prior_id)
    with database.unit_of_work() as uow:
        row=uow.session.execute(text("""
            SELECT a.id,a.generation,a.provider_ref
            FROM execution_attempts a
            LEFT JOIN native_attempt_bindings b ON b.attempt_id=a.id
            WHERE a.work_unit_id=:pwu_id AND a.generation>:generation
              AND b.attempt_id IS NULL
            ORDER BY a.generation
        """),{"pwu_id":prior_attempt.work_unit_id,"generation":prior_attempt.generation}).all()
    if not row:
        return
    if len(row) != 1:
        raise RuntimeError("MULTIPLE_UNADMITTED_SUCCESSORS_REQUIRE_RECONCILIATION")
    attempt_id,generation,provider_ref=row[0]
    orphan=RuntimeService(database).get_attempt(attempt_id)
    if provider_ref != last["provider_profile"]:
        raise RuntimeError("UNADMITTED_SUCCESSOR_PROFILE_DIFFERS")
    task=next(item for item in spec["tasks"] if item["id"]==progress["task_id"])
    prior_root=Path(last["workspace"])
    root=prior_root.with_name(f"{prior_root.name}-successor-{generation}")
    if not root.is_dir():
        raise RuntimeError("UNADMITTED_SUCCESSOR_WORKSPACE_IS_MISSING")
    repos=repositories_at(root,task)
    permitted=(spec["profiles"]["primary"]["profile_id"],spec["profiles"]["replacement"]["profile_id"])
    model=provider_ref.split(":")[1]
    runtime_service=RuntimeService(database)
    _,session,admission=admission_for(
        runtime_service,task,root,repos,model,permitted,
        prior_attempt=prior_attempt,attempt_override=orphan,
        session_id=UUID(last["session_id"]),
    )
    NativeExecutorRuntimeService(database).admit(admission)
    ledger.add_attempt(orphan.id,admission.binding.pwu_id,session,model,root,reason="same-Attempt recovery cap reached after preserved frontier")
    ledger.event("UNADMITTED_SUCCESSOR_ADOPTED",attempt_id=str(orphan.id),generation=generation,provider_profile=provider_ref)


def recover_zero_request_harness_failure(spec: dict, ledger: BudgetLedger, database) -> None:
    if ledger.data.get("in_progress") is not None or not ledger.data["trials"]:
        return
    failed=ledger.data["trials"][-1]
    usage=failed.get("inference_submissions") or {}
    if usage.get("used") != 0 or usage.get("cap") != 0 or "PWU_INFERENCE_POOL_EXHAUSTED" not in failed.get("failure_reasons",[]):
        return
    if any(item.get("execution_id")==failed["execution_id"] for item in ledger.data["provider_requests"]):
        raise RuntimeError("ZERO_REQUEST_HARNESS_FAILURE_HAS_PROVIDER_HISTORY")
    ledger.data["trials"].pop()
    ledger.data.setdefault("harness_failures",[]).append({
        **failed,
        "classification":"INVALID_ZERO_REQUEST_RESOURCE_PREFLIGHT",
        "retained_as_benchmark_result":False,
    })
    ledger.data["in_progress"]={
        "execution_id":failed["execution_id"],"task_id":failed["task_id"],
        "repetition":failed["repetition"],"arm":failed["arm"],
        "injections":failed["injections"],"started_at":failed["finished_at"],
        "attempts":failed["attempts"],"injection_events":[],
        "consumed_injections":[],"human_technical_intervention_count":0,
        "segments":[],
    }
    ledger.flush()
    progress=ledger.data["in_progress"]
    old_info=progress["attempts"][-1]
    old=RuntimeService(database).get_attempt(UUID(old_info["attempt_id"]))
    task=next(item for item in spec["tasks"] if item["id"]==failed["task_id"])
    old_root=Path(old_info["workspace"])
    root,repos=copied_workspace(old_root,f"successor-{old.generation+1}",task)
    model=old_info["provider_profile"].split(":")[1]
    permitted=(spec["profiles"]["primary"]["profile_id"],spec["profiles"]["replacement"]["profile_id"])
    _,session,admission=admission_for(
        RuntimeService(database),task,root,repos,model,permitted,
        prior_attempt=old,session_id=UUID(old_info["session_id"]),
    )
    NativeExecutorRuntimeService(database).admit(admission)
    ledger.add_attempt(admission.binding.attempt_id,admission.binding.pwu_id,session,model,root,reason="successor after zero-request harness preflight correction")
    ledger.event("ZERO_REQUEST_HARNESS_FAILURE_RECOVERED",predecessor_attempt_id=str(old.id),successor_attempt_id=str(admission.binding.attempt_id))


def recover_interrupted_current_trial(ledger: BudgetLedger, database) -> None:
    progress=ledger.data.get("in_progress")
    if progress is None or not progress.get("attempts"):
        return
    attempt_id=UUID(progress["attempts"][-1]["attempt_id"])
    runtime=NativeExecutorRuntimeService(database)
    reconciled=runtime.reconcile_expired_leases()
    with database.unit_of_work() as uow:
        store=NativeExecutionStore(uow.session)
        state=store.attempt_state(attempt_id)
        checkpoint=store.latest_checkpoint(attempt_id)
        after=checkpoint.step_sequence if checkpoint else 0
        recovered=store.tool_results_after(
            attempt_id,after_step_sequence=after,
        )
        steps=store.steps_for_attempt(attempt_id)
        effects=store.effects_for_attempt(attempt_id)
    ledger.event(
        "INTERRUPTED_EXECUTION_REALITY_RECOVERED",
        attempt_id=str(attempt_id),
        lease_reconciled=attempt_id in reconciled,
        runtime_mode=state.runtime_mode.value,
        terminal_outcome=(state.terminal_outcome.value if state.terminal_outcome else None),
        effect_uncertainty=state.effect_uncertainty,
        latest_checkpoint_sequence=after,
        step_count=len(steps),
        effect_count=len(effects),
        uncheckpointed_settled_receipt_count=len(recovered),
    )
    if state.effect_uncertainty:
        raise RuntimeError("INTERRUPTED_EXECUTION_EFFECT_UNCERTAINTY_REQUIRES_RECONCILIATION")
    failed_unknown_requests=[
        item for item in ledger.data.get("provider_request_failures",[])
        if item.get("execution_id")==progress["execution_id"]
        and item.get("attempt_id")==str(attempt_id)
        and any(
            pending.get("local_request_id")==item.get("local_request_id")
            for pending in ledger.data.get("pending_provider_requests",[])
        )
    ]
    if failed_unknown_requests and state.runtime_mode is not ExecutionMode.FINISHED:
        stop_attempt(
            runtime,attempt_id,
            "Provider response became unknown; benchmark contract forbids automatic retry",
        )
        ledger.event(
            "PROVIDER_RESPONSE_UNKNOWN_SETTLED_WITHOUT_RETRY",
            attempt_id=str(attempt_id),
            failed_request_count=len(failed_unknown_requests),
            retained_cost_reservation_rmb=round(sum(
                pending["reserved_cost_rmb"]
                for pending in ledger.data.get("pending_provider_requests",[])
                if any(
                    failed.get("local_request_id")==pending.get("local_request_id")
                    for failed in failed_unknown_requests
                )
            ),8),
        )
        state=attempt_state(runtime,attempt_id)
    injection="worker_loss_after_effect_before_checkpoint"
    if (
        injection in set(progress.get("injections",[]))
        and not ledger.injection_consumed(injection)
        and recovered
    ):
        # The harness process died after the receipt and before checkpointing.
        # Treat the observed durable frontier as the frozen injection itself;
        # replaying another artificial crash would duplicate the fault.
        ledger.consume_injection(injection)
        ledger.event(
            "WORKER_LOSS_AFTER_EFFECT_BEFORE_CHECKPOINT_RECOVERED",
            attempt_id=str(attempt_id),
            recovered_receipt_count=len(recovered),
            duplicated_provider_requests=0,
        )


async def run_trial(spec: dict, trial: dict, settings: Settings, ledger: BudgetLedger, database) -> dict:
    task=next(t for t in spec["tasks"] if t["id"]==trial["task_id"])
    runtime_service=RuntimeService(database); runtime=NativeExecutorRuntimeService(database)
    permitted=(spec["profiles"]["primary"]["profile_id"],spec["profiles"]["replacement"]["profile_id"])
    ledger.begin_trial(trial)
    progress=ledger.data["in_progress"]
    if progress["attempts"]:
        latest=progress["attempts"][-1]
        attempt=runtime_service.get_attempt(UUID(latest["attempt_id"]))
        session=UUID(latest["session_id"]); root=Path(latest["workspace"])
        repos=repositories_at(root,task)
        model=latest["provider_profile"].split(":")[1]
        with database.unit_of_work() as uow:
            binding=NativeExecutionStore(uow.session).attempt_binding(attempt.id).binding
        pwu_id=binding.pwu_id
    else:
        root,repos=prepare_repositories(settings.native_executor_workspace_root/"continuity-v2"/trial["execution_id"],task)
        model=spec["profiles"]["primary"]["model"]
        attempt,session,admission=admission_for(runtime_service,task,root,repos,model,permitted)
        runtime.admit(admission); pwu_id=admission.binding.pwu_id
        ledger.add_attempt(attempt.id,pwu_id,session,model,root,reason="initial frozen execution")
    injections=set(trial.get("injections",[]))
    used_inferences,inference_cap=pwu_inference_usage(database,pwu_id)
    initial_state=attempt_state(runtime,attempt.id)
    if initial_state.runtime_mode is ExecutionMode.FINISHED:
        checks=validate(root,task)
        missing_injections=sorted(injections-set(progress.get("consumed_injections",[])))
        terminal=(
            initial_state.terminal_outcome.value
            if initial_state.terminal_outcome else None
        )
        failure_reasons=[]
        if terminal != "RESULT_READY":
            failure_reasons.append(f"TERMINAL_{terminal or 'MISSING'}")
        if any(check["returncode"] != 0 for check in checks):
            failure_reasons.append("FROZEN_VERIFICATION_FAILED")
        if missing_injections:
            failure_reasons.append("REQUIRED_INJECTION_NOT_OBSERVED")
        if any(
            item.get("execution_id")==trial["execution_id"]
            for item in ledger.data.get("provider_request_failures",[])
        ):
            failure_reasons.extend((
                "PROVIDER_RESPONSE_UNKNOWN",
                "NO_AUTOMATIC_PROVIDER_RETRY_BY_CONTRACT",
            ))
        return {
            **trial,"attempt_id":str(attempt.id),"attempts":progress["attempts"],
            "pwu_id":str(pwu_id),"session_id":str(session),
            "effective_model":model,"segments":list(progress.get("segments",[])),
            "terminal_outcome":terminal,"checks":checks,
            "missing_injections":missing_injections,"passed":False,
            "failure_reasons":failure_reasons,
            "inference_submissions":{"used":used_inferences,"cap":inference_cap},
            "finished_at":datetime.now(UTC).isoformat(),
        }
    if used_inferences >= inference_cap and initial_state.runtime_mode is not ExecutionMode.FINISHED:
        finish_budget_exhausted(database,attempt.id)
        checks=validate(root,task)
        missing_injections=sorted(injections-set(progress.get("consumed_injections",[])))
        ledger.event(
            "PWU_INFERENCE_POOL_EXHAUSTED",
            attempt_id=str(attempt.id),used=used_inferences,cap=inference_cap,
        )
        return {
            **trial,"attempt_id":str(attempt.id),"attempts":progress["attempts"],
            "pwu_id":str(pwu_id),"session_id":str(session),"effective_model":model,
            "segments":list(progress.get("segments",[])),
            "terminal_outcome":"BUDGET_EXHAUSTED","checks":checks,
            "missing_injections":missing_injections,"passed":False,
            "failure_reasons":["PWU_INFERENCE_POOL_EXHAUSTED","FROZEN_VERIFICATION_FAILED" if any(c["returncode"] for c in checks) else "INFERENCE_CAP_EXCEEDED"],
            "inference_submissions":{"used":used_inferences,"cap":inference_cap},
            "finished_at":datetime.now(UTC).isoformat(),
        }

    def make_successor(active_model: str, reason: str, *, additions: dict | None = None):
        nonlocal attempt, session, root, repos, model, pwu_id
        old=attempt
        stop_attempt(runtime,old.id,reason)
        root,repos=copied_workspace(root,f"successor-{old.generation + 1}",task)
        attempt,session,admission=admission_for(
            runtime_service,task,root,repos,active_model,permitted,
            prior_attempt=old,session_id=session,
            revision=len(ledger.data["in_progress"]["attempts"])+1,
            contract_additions=additions,
        )
        runtime.admit(admission); model=active_model; pwu_id=admission.binding.pwu_id
        ledger.add_attempt(attempt.id,pwu_id,session,model,root,reason=reason)
        ledger.event("SUCCESSOR_EXECUTION_ADMITTED", predecessor_attempt_id=str(old.id), successor_attempt_id=str(attempt.id), reason=reason, provider_profile=exact_profile(model))

    def make_worker(active_model, active_attempt, active_injections):
        adapter=MeteredAdapter(DeepSeekResponsesInferenceAdapter(model=active_model,api_key=settings.native_executor_deepseek_api_key.get_secret_value,base_url=settings.native_executor_deepseek_base_url,timeout_seconds=settings.executor_timeout_seconds,reasoning_effort="high"),ledger,active_model,active_injections,runtime,active_attempt.id)
        def factory(grant):
            with database.unit_of_work() as uow: binding=NativeExecutionStore(uow.session).attempt_binding(grant.allocation.attempt_id)
            checkpoints=DurableCheckpointPort(database,ContentAddressedStorage(settings.native_executor_storage_root/"checkpoints"),attempt_id=binding.attempt_id,session_id=binding.session_id,worker_epoch=grant.allocation.lease_epoch)
            checkpoints=CrashAfterReceiptCheckpoint(checkpoints,ledger,active_injections,binding.attempt_id)
            tools=BenchmarkTools(
                RemoteNativeToolHost(settings.native_executor_tool_host_url,settings.native_executor_internal_token.get_secret_value()),
                ledger,active_injections,runtime,binding.attempt_id,
            )
            audit=BenchmarkAudit(
                DurableKernelAudit(database,attempt_id=binding.attempt_id,session_id=binding.session_id,pwu_id=binding.pwu_id,envelope_id=binding.resource_envelope_id),
                adapter,ledger,active_injections,
            )
            return NativeExecutorKernel(
                inference=adapter,tools=tools,checkpoints=checkpoints,audit=audit,
                context=BenchmarkContext(ledger,active_injections),
            )
        offer=WorkerOffer(worker_id=f"continuity:{trial['execution_id']}:{active_model}",worker_profile="local-container-v1",provider_profiles=(exact_profile(active_model),),resource_profiles=("standard",),capability_identities=("file.read","file.write","process.run","git.status","git.diff","test.run","build.run","dependency.sync","preview.inspect"),lease_seconds=5)
        return NativeExecutionWorker(runtime,factory,heartbeat_seconds=1),offer
    worker,offer=make_worker(model,attempt,injections)
    segments=list(progress.get("segments",[]))
    for cycle in range(len(segments),30):
        try:
            worked=await worker.run_once(offer)
        except RuntimeError as exc:
            if "PWU resource pool is exhausted" in str(exc):
                await asyncio.sleep(6)
                runtime.reconcile_expired_leases()
                finish_budget_exhausted(database,attempt.id)
                segments.append({"cycle":cycle,"resource_boundary":"PWU_INFERENCE_POOL_EXHAUSTED"})
                progress["segments"]=segments; ledger.flush()
                break
            if not str(exc).startswith("BENCHMARK_"):
                raise
            segments.append({"cycle":cycle,"injected_crash":str(exc)[:120]})
            progress["segments"]=segments; ledger.flush()
            await asyncio.sleep(6)
            reconciled=runtime.reconcile_expired_leases()
            ledger.event("EXPIRED_LEASE_RECONCILED", attempt_id=str(attempt.id), reconciled=str(attempt.id) in {str(item) for item in reconciled})
            state=attempt_state(runtime,attempt.id)
            if state.effect_uncertainty:
                raise RuntimeError("BENCHMARK_EFFECT_UNCERTAINTY_REQUIRES_RECONCILIATION")
            worker,offer=make_worker(model,attempt,injections)
            continue
        if not worked:
            state=attempt_state(runtime,attempt.id)
            with database.unit_of_work() as uow:
                queue=NativeExecutionStore(uow.session).queue_for_attempt(attempt.id)
            if state.runtime_mode is ExecutionMode.QUEUED and queue is not None and queue.resume_count >= 3:
                make_successor(model,"same-Attempt recovery cap reached after preserved frontier")
                worker,offer=make_worker(model,attempt,injections)
                continue
            await asyncio.sleep(1)
            continue
        state=attempt_state(runtime,attempt.id); segments.append({"cycle":cycle,"mode":state.runtime_mode.value,"outcome":state.terminal_outcome.value if state.terminal_outcome else None})
        progress["segments"]=segments; ledger.flush()
        if state.runtime_mode is ExecutionMode.PAUSED:
            if ledger.injection_consumed("model_replacement") and model == spec["profiles"]["primary"]["model"]:
                make_successor(spec["profiles"]["replacement"]["model"],"preassigned compatible model replacement")
            elif ledger.injection_consumed("material_human_correction") and not any(item["reason"] == "material Human correction" for item in progress["attempts"]):
                correction={
                    "T3":"Correction: preserve the exact existing ASCII normalization behavior and both public signatures.",
                    "T6":"Correction: missing or blank state must render literal lowercase unknown; network calls remain forbidden.",
                }.get(task["id"],"Correction: retain every frozen acceptance criterion while applying the clarified scope.")
                make_successor(model,"material Human correction",additions={"material_correction":correction})
            else:
                runtime.control(BackendControlCommand(command_id=uuid4(),handle=ExecutionHandle(backend_identity="watt-native",dispatch_id=attempt.id,attempt_id=attempt.id,generation=state.generation,opaque_reference=f"attempt:{attempt.id}"),action=ControlAction.RESUME,expected_control_version=state.control_version,actor_identity="human:continuity-benchmark-authorized",reason="resume preassigned segment"))
            worker,offer=make_worker(model,attempt,injections); continue
        if state.runtime_mode is ExecutionMode.WAITING_RESOURCE:
            successor_reason=None
            if ledger.injection_consumed("quota_after_useful_edit"):
                successor_reason="simulated quota recovery after retained useful edits"
            elif ledger.injection_consumed("compaction_failure"):
                successor_reason="compaction failure fallback from portable checkpoint"
            if successor_reason and not any(item["reason"] == successor_reason for item in progress["attempts"]):
                make_successor(model,successor_reason)
                worker,offer=make_worker(model,attempt,injections)
            else:
                await asyncio.sleep(31)
            continue
        if state.runtime_mode is ExecutionMode.FINISHED:
            break
    state=attempt_state(runtime,attempt.id)
    if state.runtime_mode is not ExecutionMode.FINISHED:
        raise RuntimeError("BENCHMARK_CYCLE_BOUND_EXHAUSTED_WITHOUT_TERMINAL_RESULT")
    checks=validate(root,task)
    missing_injections=sorted(injections-set(progress.get("consumed_injections",[])))
    terminal_outcome=state.terminal_outcome.value if state.terminal_outcome else None
    passed=bool(terminal_outcome=="RESULT_READY" and all(c["returncode"]==0 for c in checks) and not missing_injections)
    failure_reasons=[]
    if terminal_outcome != "RESULT_READY":
        failure_reasons.append(f"TERMINAL_{terminal_outcome or 'MISSING'}")
    if any(check["returncode"] != 0 for check in checks):
        failure_reasons.append("FROZEN_VERIFICATION_FAILED")
    if missing_injections:
        failure_reasons.append("REQUIRED_INJECTION_NOT_OBSERVED")
    return {**trial,"attempt_id":str(attempt.id),"attempts":progress["attempts"],"pwu_id":str(pwu_id),"session_id":str(session),"effective_model":model,"segments":segments,"terminal_outcome":terminal_outcome,"checks":checks,"missing_injections":missing_injections,"passed":passed,"failure_reasons":failure_reasons,"finished_at":datetime.now(UTC).isoformat()}


def normalize_completed_trial_evidence(spec: dict, ledger: BudgetLedger) -> None:
    """Re-run only local frozen checks after a harness validation fix.

    This never changes a Provider/runtime terminal outcome and keeps the prior
    checks as history.  It repairs evidence produced before the src-layout
    PYTHONPATH was included in the validation environment.
    """
    tasks={item["id"]:item for item in spec["tasks"]}
    changed=False
    for trial in ledger.data["trials"]:
        checks=trial.get("checks",[])
        affected=(
            trial.get("task_id")=="T4"
            and any("No module named 'watt_ids'" in check.get("stdout","") for check in checks)
        )
        if not affected:
            continue
        attempts=trial.get("attempts") or []
        if not attempts:
            raise RuntimeError("COMPLETED_TRIAL_REVALIDATION_WORKSPACE_IS_UNKNOWN")
        root=Path(attempts[-1]["workspace"])
        if not root.is_dir():
            raise RuntimeError("COMPLETED_TRIAL_REVALIDATION_WORKSPACE_IS_MISSING")
        trial.setdefault("check_history",[]).append({
            "checks":checks,
            "reason":"validation environment lacked src-layout PYTHONPATH",
            "superseded_at":datetime.now(UTC).isoformat(),
        })
        trial["checks"]=validate(root,tasks[trial["task_id"]])
        terminal=trial.get("terminal_outcome")
        missing=trial.get("missing_injections",[])
        trial["passed"]=bool(
            terminal=="RESULT_READY"
            and all(check["returncode"]==0 for check in trial["checks"])
            and not missing
        )
        reasons=[]
        if terminal != "RESULT_READY":
            reasons.append(f"TERMINAL_{terminal or 'MISSING'}")
        if any(check["returncode"] != 0 for check in trial["checks"]):
            reasons.append("FROZEN_VERIFICATION_FAILED")
        if missing:
            reasons.append("REQUIRED_INJECTION_NOT_OBSERVED")
        trial["failure_reasons"]=reasons
        trial["evidence_revalidated_at"]=datetime.now(UTC).isoformat()
        changed=True
    if changed:
        ledger.flush()


def enrich_completed_trial_evidence(ledger: BudgetLedger, database) -> None:
    """Materialize compact, credential-free evidence required by the contract."""
    for trial in ledger.data["trials"]:
        attempt_ids=[UUID(item["attempt_id"]) for item in trial.get("attempts",[])]
        if not attempt_ids:
            continue
        request_rows=[
            item for item in ledger.data.get("provider_requests",[])
            if item.get("execution_id")==trial["execution_id"]
        ]
        pending_rows=[
            item for item in ledger.data.get("pending_provider_requests",[])
            if item.get("execution_id")==trial["execution_id"]
        ]
        failures=[
            item for item in ledger.data.get("provider_request_failures",[])
            if item.get("execution_id")==trial["execution_id"]
        ]
        usage={"input_tokens":0,"output_tokens":0,"total_tokens":0,"cached_input_tokens":0,"reasoning_tokens":0}
        for request in request_rows:
            item=request.get("usage") or {}
            for key in usage:
                usage[key]+=int(item.get(key) or 0)
        with database.unit_of_work() as uow:
            store=NativeExecutionStore(uow.session)
            bindings=[store.attempt_binding(attempt_id).binding for attempt_id in attempt_ids]
            steps=[step for attempt_id in attempt_ids for step in store.steps_for_attempt(attempt_id)]
            effects=[effect for attempt_id in attempt_ids for effect in store.effects_for_attempt(attempt_id)]
            checkpoint_rows=uow.session.execute(text("""
                SELECT id,attempt_id,step_sequence,condition,content_digest
                FROM checkpoint_bundles
                WHERE attempt_id = ANY(:attempt_ids)
                ORDER BY committed_at,id
            """),{"attempt_ids":attempt_ids}).mappings().all()
            claim_count=int(uow.session.scalar(text("""
                SELECT count(*) FROM result_ready_claims
                WHERE attempt_id = ANY(:attempt_ids)
            """),{"attempt_ids":attempt_ids}) or 0)
            resource_rows=uow.session.execute(text("""
                SELECT resource_type,coalesce(sum(amount),0) AS amount
                FROM execution_resource_usage
                WHERE attempt_id = ANY(:attempt_ids)
                GROUP BY resource_type ORDER BY resource_type
            """),{"attempt_ids":attempt_ids}).mappings().all()
        step_digests=[step.request_digest for step in steps]
        effect_digests=[effect.semantic_input_digest for effect in effects]
        duplicated_steps=len(step_digests)-len(set(step_digests))
        duplicated_effects=len(effect_digests)-len(set(effect_digests))
        members=bindings[0].source_vector.members
        consumed=sorted(set(trial.get("injections",[]))-set(trial.get("missing_injections",[])))
        started=(trial.get("started_at") or trial["attempts"][0].get("recorded_at"))
        duration=None
        if started and trial.get("finished_at"):
            duration=max((datetime.fromisoformat(trial["finished_at"])-datetime.fromisoformat(started)).total_seconds(),0.0)
        trial["provider_evidence"]={
            "profiles":sorted({item["provider_profile"] for item in trial["attempts"]}),
            "completed_request_count":len(request_rows),
            "response_unknown_request_count":len(pending_rows),
            "failure_classes":sorted({item.get("error_type","UNKNOWN") for item in failures}),
            "usage":usage,
            "known_cost_rmb":round(sum(float(item["cost_rmb"]) for item in request_rows),8),
            "reserved_unknown_cost_rmb":round(sum(float(item["reserved_cost_rmb"]) for item in pending_rows),8),
        }
        trial["source_baseline"]=[{
            "mount_id":member.mount_id,
            "source_baseline_ref":member.source_baseline_ref,
            "source_commit_oid":member.source_commit_oid,
            "source_tree_oid":member.source_tree_oid,
        } for member in members]
        trial["runtime_evidence"]={
            "step_count":len(steps),"effect_count":len(effects),
            "checkpoint_count":len(checkpoint_rows),"result_ready_claim_count":claim_count,
            "checkpoints":[{
                "id":str(row["id"]),"attempt_id":str(row["attempt_id"]),
                "step_sequence":row["step_sequence"],"condition":row["condition"],
                "content_digest":row["content_digest"],
            } for row in checkpoint_rows],
            "resource_usage":{row["resource_type"]:int(row["amount"]) for row in resource_rows},
        }
        trial["continuity_evidence"]={
            "consumed_injections":consumed,
            "successor_execution_count":max(len(attempt_ids)-1,0),
            "nonterminal_segment_count":sum(
                segment.get("outcome") is None or "injected_crash" in segment
                for segment in trial.get("segments",[])
            ),
            "duplicated_inference_request_digest_count":duplicated_steps,
            "duplicated_tool_effect_digest_count":duplicated_effects,
            "human_technical_intervention_count":trial.get("human_technical_intervention_count",0),
            "elapsed_seconds":round(duration,6) if duration is not None else None,
            "elapsed_basis":"ledger start/finish" if trial.get("started_at") else "first attempt record/finish lower bound",
        }
        if "engineering_quality_score" not in trial:
            trial["engineering_quality_score"] = {
                "status": "MISSING_V2_EVALUATION",
                "score": None,
            }
    ledger.flush()


def plan(spec: dict) -> list[dict]:
    trials=[]
    for task in spec["tasks"]:
        for repetition in range(1,4):
            for arm in ("A","B"):
                key=f"{task['id']}-{repetition}"
                trials.append({"execution_id":f"{key}-{arm}","task_id":task["id"],"repetition":repetition,"arm":arm,"injections":spec["b_injections"].get(key,[]) if arm=="B" else []})
    random.Random(spec["randomization_seed"]).shuffle(trials)
    return trials


async def main_async(args):
    spec=json.loads(SPEC_PATH.read_text()); output=Path(args.output); ledger=BudgetLedger(output,spec)
    if ledger.data.get("spec_digest") != canonical_digest(spec):
        raise RuntimeError("RESULT_LEDGER_SPEC_DIGEST_MISMATCH")
    generated=plan(spec); plan_path=output.with_name("frozen-plan.json")
    if not plan_path.exists():
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps({"spec_digest":canonical_digest(spec),"trials":generated},indent=2)+"\n")
    frozen_payload=json.loads(plan_path.read_text())
    if frozen_payload.get("spec_digest") != canonical_digest(spec):
        raise RuntimeError("FROZEN_PLAN_SPEC_DIGEST_MISMATCH")
    frozen=frozen_payload.get("trials")
    if not isinstance(frozen,list) or len(frozen) != 36:
        raise RuntimeError("FROZEN_PLAN_MUST_CONTAIN_36_EXECUTIONS")
    identities=[item.get("execution_id") for item in frozen]
    if len(set(identities)) != 36:
        raise RuntimeError("FROZEN_PLAN_EXECUTION_IDS_MUST_BE_UNIQUE")
    if generated != frozen:
        raise RuntimeError("GENERATED_PLAN_DIFFERS_FROM_FROZEN_PLAN")
    if args.plan_only:
        print(json.dumps({"status":"FROZEN","spec_digest":canonical_digest(spec),"executions":len(frozen),"paired_trials":len(frozen)//2,"plan":str(plan_path)},sort_keys=True)); return
    app=bootstrap(); settings=app.settings; database=app.persistence()
    normalize_completed_trial_evidence(spec,ledger)
    enrich_completed_trial_evidence(ledger,database)
    recover_legacy_first_execution(spec,frozen[0],settings,ledger,database)
    recover_zero_request_harness_failure(spec,ledger,database)
    adopt_unadmitted_successor(spec,ledger,database)
    record_unknown_provider_reservations(spec,ledger,database)
    recover_interrupted_current_trial(ledger,database)
    progress=ledger.data.get("in_progress")
    if progress is not None:
        for prior in progress.get("attempts",[])[:-1]:
            settle_superseded_predecessor(database,UUID(prior["attempt_id"]),ledger)
        if progress.get("attempts"):
            reconcile_prelaunch_tool_rejection(
                database,UUID(progress["attempts"][-1]["attempt_id"]),ledger
            )
    if args.recover_only:
        print(json.dumps({
            "status":"RECOVERY_FRONTIER_READY",
            "execution_id":progress.get("execution_id") if progress else None,
            "attempt_count":len(progress.get("attempts",[])) if progress else 0,
            "provider_requests":len(ledger.data["provider_requests"]),
            "actual_cost_rmb":ledger.data["actual_cost_rmb"],
        },sort_keys=True))
        database.dispose()
        return
    completed={t["execution_id"] for t in ledger.data["trials"]}
    unfinished=next((item for item in frozen if item["execution_id"] not in completed),None)
    if ledger.data.get("in_progress") is not None and (
        unfinished is None or ledger.data["in_progress"]["execution_id"] != unfinished["execution_id"]
    ):
        raise RuntimeError("IN_PROGRESS_EXECUTION_DIFFERS_FROM_FROZEN_FRONTIER")
    executed_this_process=0
    for trial in frozen:
        if trial["execution_id"] in completed: continue
        if args.max_executions is not None and executed_this_process >= args.max_executions:
            break
        result=await run_trial(spec,trial,settings,ledger,database)
        progress_snapshot=ledger.data.get("in_progress") or {}
        result["started_at"]=progress_snapshot.get("started_at")
        result["injection_events"]=list(progress_snapshot.get("injection_events",[]))
        result["consumed_injections"]=list(progress_snapshot.get("consumed_injections",[]))
        result["human_technical_intervention_count"]=int(
            progress_snapshot.get("human_technical_intervention_count",0)
        )
        task=next(item for item in spec["tasks"] if item["id"]==result["task_id"])
        root=Path(result["attempts"][-1]["workspace"])
        assessment=evaluate(root,task,result["checks"],result.get("terminal_outcome"))
        result["engineering_quality_score"]=assessment
        if not assessment["mandatory_gate_passed"]:
            result["passed"]=False
            if "FROZEN_V2_MANDATORY_EVALUATION_FAILED" not in result["failure_reasons"]:
                result["failure_reasons"].append("FROZEN_V2_MANDATORY_EVALUATION_FAILED")
        if assessment["material_defects"]:
            result["passed"]=False
            if "ENGINEERING_QUALITY_MATERIAL_DEFECT" not in result["failure_reasons"]:
                result["failure_reasons"].append("ENGINEERING_QUALITY_MATERIAL_DEFECT")
        ledger.data["trials"].append(result)
        ledger.data["in_progress"]=None
        enrich_completed_trial_evidence(ledger,database)
        ledger.flush()
        executed_this_process+=1
        print(json.dumps({"execution_id":result["execution_id"],"passed":result["passed"],"cost_rmb":ledger.data["actual_cost_rmb"]},sort_keys=True),flush=True)
    database.dispose()


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",required=True); parser.add_argument("--plan-only",action="store_true"); parser.add_argument("--recover-only",action="store_true"); parser.add_argument("--max-executions",type=int)
    asyncio.run(main_async(parser.parse_args()))


if __name__=="__main__": main()
