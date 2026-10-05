"""Controlled ECS scheduling proof; no model calls, tools, or Product mutation.

Run inside the existing Worker image against a dedicated PostgreSQL database.
The persisted native authority/queue/leases and NativeExecutionWorker are real;
the bounded kernel only waits and stops, and never claims a software result.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.engine import make_url

from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.application.runtime import RuntimeService
from spg.config import Settings
from spg.domain.native_execution import (
    AttemptTerminalOutcome, CapabilityGrant, CloudExecutionStatus, ExecutionBindingV2,
    ExecutionMode, KernelRunResult, NativeExecutionAdmission, PWUContractVersionRecord,
    ResourceEnvelope, SourceMember, SourceVector, WorkerOffer,
    WorkspaceManifest, WorkspaceMount, canonical_digest,
)
from spg.domain.runtime import (AttemptRequest, BootstrapRequest, CompletionContract,
    InitialRunRequest, ProductionHorizon)
from spg.infrastructure.executor_runtime.worker import NativeExecutionWorker
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.native_execution_schema import executor_scheduler_state


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def admission(database, repo, work):
    owner = RuntimeService(database)
    spine = owner.create_initial_runtime_spine(InitialRunRequest(
        intent_ref='qualification:capacity-runtime', goal='Controlled scheduling proof',
        production_horizon=ProductionHorizon.CODE,
        initial_work_unit_objective='Capacity qualification; no software changes',
        completion_contract=CompletionContract(required_outputs=('qualification evidence',),
            required_changes=('none; controlled stop only',), forbidden_changes=('Product mutation',),
            verification_obligations=('capacity scheduling',))))
    attempt = owner.create_initial_attempt(spine.work_unit.id,
        AttemptRequest(provider_ref='watt-native:capacity-qualification'))
    vector = SourceVector(members=(SourceMember(mount_id='primary',
        repository_identity=str(repo), source_baseline_ref='refs/heads/main',
        source_commit_oid=git(repo, 'rev-parse', 'HEAD'),
        source_tree_oid=git(repo, 'rev-parse', 'HEAD^{tree}'),
        container_path='/workspace/primary', read_scope=('README.md',),
        write_scope=(), forbidden_paths=('.git',)),))
    workspace = WorkspaceManifest(workspace_id=uuid4(), work_id=work,
        pwu_id=spine.work_unit.id, attempt_id=attempt.id,
        source_vector_digest=vector.digest or '', host_storage_id=str(repo),
        environment_profile_digest='b' * 64,
        mounts=(WorkspaceMount(mount_id='primary', host_path=str(repo),
            container_path='/workspace/primary', writable=False, write_scope=(), forbidden_paths=('.git',)),),
        evidence_namespace='capacity-qualification', retention_policy='qualification')
    payload = {'objective': 'Controlled capacity scheduling; no external effects'}
    contract = PWUContractVersionRecord(id=uuid4(), pwu_id=spine.work_unit.id,
        revision=1, objective=payload['objective'], contract_payload=payload,
        contract_digest=canonical_digest(payload), created_at=datetime.now(timezone.utc))
    envelope = ResourceEnvelope(envelope_id=uuid4(), policy_version='qualification-v1',
        provider_profile='capacity-qualification', max_active_seconds=60,
        max_inference_submissions=1, max_tool_effects=1)
    binding = ExecutionBindingV2(work_id=work, steering_decision_id=uuid4(),
        pwu_id=spine.work_unit.id, pwu_contract_version_id=contract.id,
        pwu_contract_digest=contract.contract_digest, attempt_id=attempt.id,
        generation=attempt.generation, session_id=uuid4(), source_vector=vector,
        workspace=workspace, context_package_ref='context:capacity-qualification',
        materialized_input_digest='c' * 64, backend_implementation='watt-native',
        backend_version='1', inference_profile='capacity-qualification',
        capability_grants=(CapabilityGrant(identity='capacity.qualify', version='1', scope={}),),
        resource_envelope=envelope, obligation_references=('capacity scheduling',))
    return NativeExecutionAdmission(command_id=uuid4(), actor_identity='qualification:ecs',
        fairness_group=f'work:{work}', binding=binding, contract=contract,
        materialization_path=str(repo), required_resource_profile='capacity-qualification',
        available_at=datetime.now(timezone.utc))


def stopped():
    return KernelRunResult(runtime_mode=ExecutionMode.FINISHED,
        terminal_outcome=AttemptTerminalOutcome.STOPPED, final_checkpoint_id=None,
        step_count=0, inference_submissions=0, tool_effects=0,
        summary='Controlled qualification kernel stopped without external effects')


async def until(predicate):
    async with asyncio.timeout(20):
        while not predicate():
            await asyncio.sleep(.05)


async def contention(runtime, database, repo, state):
    a, b = sorted([uuid4(), uuid4()], key=str)
    requests = [admission(database, repo, a) for _ in range(3)] + [admission(database, repo, b)]
    for request in requests:
        runtime.admit(request)
    offer = WorkerOffer(worker_id='ecs-capacity-qualification:one', max_concurrency=1,
        worker_profile='qualification-v1', provider_profiles=('capacity-qualification',),
        resource_profiles=('capacity-qualification',), capability_identities=('capacity.qualify',),
        lease_seconds=5, runtime_version='capacity-v1')
    runtime.heartbeat_worker(offer)
    starts, gates = [], {request.binding.attempt_id: asyncio.Event() for request in requests}
    class Kernel:
        def __init__(self, grant): self.grant = grant
        async def run(self, **_kwargs):
            starts.append(self.grant)
            await gates[self.grant.allocation.attempt_id].wait()
            return stopped()
    worker = NativeExecutionWorker(runtime, Kernel, heartbeat_seconds=1)
    stop = asyncio.Event()
    async def poll():
        while not stop.is_set():
            runtime.heartbeat_worker(offer)
            await worker.run_once(offer)
            await asyncio.sleep(.05)
    polling = asyncio.create_task(poll())
    await until(lambda: len(starts) == 1)
    assert starts[0].queue_entry.work_id == a
    b_id = requests[-1].binding.attempt_id
    waiting = runtime.execution_request(b_id)
    assert waiting.status is CloudExecutionStatus.QUEUED
    assert waiting.scheduling.available_slots == 0 and waiting.scheduling.occupied_slots == 1
    runtime.reconcile_queue_ownership()
    gates[starts[0].allocation.attempt_id].set()
    await until(lambda: len(starts) == 2)
    assert starts[1].queue_entry.work_id == b
    runtime.set_worker_draining(offer.worker_id, draining=True)
    gates[starts[1].allocation.attempt_id].set()
    await until(lambda: next(w for w in runtime.list_workers() if w.worker_id == offer.worker_id).safe_to_restart)
    await asyncio.sleep(.25)
    assert len(starts) == 2
    assert runtime.heartbeat_worker(offer).status.value == 'DRAINING'
    runtime.set_worker_draining(offer.worker_id, draining=False)
    for count in (3, 4):
        await until(lambda: len(starts) == count)
        gates[starts[-1].allocation.attempt_id].set()
    await until(lambda: all(runtime.execution_request(r.binding.attempt_id).status is CloudExecutionStatus.CANCELLED for r in requests))
    stop.set(); await polling
    runtime.set_worker_draining(offer.worker_id, draining=True)
    state['single_slot'] = {'status':'REAL_PASS','executions':[str(r.binding.attempt_id) for r in requests],
        'work_allocation_order':[str(g.queue_entry.work_id) for g in starts]}
    state['fairness'] = 'REAL_PASS'; state['draining'] = 'REAL_PASS'

    # Two real concurrent NativeExecutionWorker kernels, without a model or tool.
    requests = [admission(database, repo, uuid4()) for _ in range(3)]
    for request in requests: runtime.admit(request)
    offer = offer.model_copy(update={'worker_id':'ecs-capacity-qualification:two','max_concurrency':2})
    runtime.heartbeat_worker(offer)
    starts.clear(); gates = {r.binding.attempt_id: asyncio.Event() for r in requests}
    stop.clear(); polling = [asyncio.create_task(poll()) for _ in range(2)]
    await until(lambda: len(starts) == 2)
    remaining = next(r.binding.attempt_id for r in requests if r.binding.attempt_id not in {g.allocation.attempt_id for g in starts})
    observed = runtime.execution_request(remaining)
    assert observed.scheduling.occupied_slots == 2 and observed.scheduling.available_slots == 0
    assert runtime.allocate(offer) is None
    gates[starts[0].allocation.attempt_id].set()
    await until(lambda: len(starts) == 3)
    for gate in gates.values(): gate.set()
    await until(lambda: all(runtime.execution_request(r.binding.attempt_id).status is CloudExecutionStatus.CANCELLED for r in requests))
    stop.set(); await asyncio.gather(*polling)
    runtime.set_worker_draining(offer.worker_id, draining=True)
    state['multi_slot'] = {'status':'REAL_PASS','maximum_active_allocations':2,
        'executions':[str(r.binding.attempt_id) for r in requests],
        'operational_production_max_concurrency':1}


async def prepare(runtime, database, repo, state):
    offer = WorkerOffer(worker_id='ecs-capacity-qualification:recovery', max_concurrency=1,
        worker_profile='qualification-v1', provider_profiles=('capacity-qualification',),
        resource_profiles=('capacity-qualification',), capability_identities=('capacity.qualify',),
        lease_seconds=5)
    requests = [admission(database, repo, uuid4()) for _ in range(2)]
    for request in requests: runtime.admit(request)
    started = asyncio.Event()
    class Kernel:
        async def run(self, **_kwargs):
            started.set()
            await asyncio.Event().wait()
    worker = NativeExecutionWorker(runtime, lambda _grant: Kernel(), heartbeat_seconds=1)
    task = asyncio.create_task(worker.run_once(offer))
    await started.wait()
    active = next(runtime.execution_request(r.binding.attempt_id) for r in requests
                  if runtime.execution_request(r.binding.attempt_id).status is CloudExecutionStatus.RUNNING)
    task.cancel(); await asyncio.gather(task, return_exceptions=True)
    with database.unit_of_work() as uow:
        cursor = uow.session.execute(select(executor_scheduler_state)).mappings().one()
        state['cursor_before_restart'] = cursor['last_fairness_group']
    state['recovery'] = {'running_execution':str(active.execution_id),
        'executions':[str(r.binding.attempt_id) for r in requests], 'offer':offer.model_dump(mode='json')}


async def verify(runtime, database, state):
    from uuid import UUID
    ids = [UUID(value) for value in state['recovery']['executions']]
    with database.unit_of_work() as uow:
        cursor = uow.session.execute(select(executor_scheduler_state)).mappings().one()
        assert cursor['last_fairness_group'] == state['cursor_before_restart']
    assert all(runtime.execution_request(value).status not in {CloudExecutionStatus.COMPLETED,
               CloudExecutionStatus.CANCELLED,CloudExecutionStatus.FAILED} for value in ids)
    runtime.reconcile_worker_liveness(); runtime.reconcile_expired_leases()
    assert all(runtime.execution_request(value).status is CloudExecutionStatus.QUEUED for value in ids)
    offer = WorkerOffer.model_validate(state['recovery']['offer'])
    runtime.heartbeat_worker(offer)
    seen = []
    class Kernel:
        async def run(self, **kwargs):
            seen.append(str(kwargs['binding'].attempt_id))
            return stopped()
    worker = NativeExecutionWorker(runtime, lambda _grant: Kernel())
    for _ in ids: assert await worker.run_once(offer)
    assert set(seen) == {str(value) for value in ids} and len(seen) == 2
    recovered = UUID(state['recovery']['running_execution'])
    kinds = {item['event_type'] for item in runtime.execution_evidence(recovered)}
    assert 'ExecutionRecoveryRequired' in kinds
    runtime.set_worker_draining(offer.worker_id, draining=True)
    state['restart_persistence'] = 'REAL_PASS'; state['capacity_loss_recovery'] = 'REAL_PASS'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare','verify'))
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    settings = Settings()
    url = make_url(settings.database_url).set(database='spg_capacity_qualification')
    # Never run schema/reset helpers against the Product continuity database.
    assert url.database == 'spg_capacity_qualification'
    os.environ['SPG_DATABASE_URL'] = url.render_as_string(hide_password=False)
    database = Database.from_settings(settings.model_copy(update={'database_url':os.environ['SPG_DATABASE_URL']}))
    if args.phase == 'prepare':
        assert not args.state.exists(), 'qualification state already exists; use a new exact run path'
        command.upgrade(Config('/app/alembic.ini'), 'head')
        args.state.parent.mkdir(parents=True, exist_ok=True)
        repo = args.state.parent / 'source'; repo.mkdir()
        git(repo, 'init', '-b', 'main'); git(repo, 'config', 'user.name', 'Watt Qualification')
        git(repo, 'config', 'user.email', 'qualification@watt.invalid')
        (repo / 'README.md').write_text('Controlled capacity qualification; no Product changes.\n')
        git(repo, 'add', '.'); git(repo, 'commit', '-m', 'Qualification source baseline')
        RuntimeService(database).bootstrap_trusted_baseline(BootstrapRequest(
            repository_path=repo, repository_identity=str(repo), repository_ref='refs/heads/main',
            authority_identity='qualification:ecs', scope={'qualification':'capacity-runtime'}))
        state = {'run_id':str(uuid4()),'database':'spg_capacity_qualification'}
        runtime = NativeExecutorRuntimeService(database)
        asyncio.run(contention(runtime, database, repo, state))
        asyncio.run(prepare(runtime, database, repo, state))
    else:
        state = json.loads(args.state.read_text())
        asyncio.run(verify(NativeExecutorRuntimeService(database), database, state))
    args.state.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    print(json.dumps(state, ensure_ascii=False))
    database.dispose()


if __name__ == '__main__': main()
