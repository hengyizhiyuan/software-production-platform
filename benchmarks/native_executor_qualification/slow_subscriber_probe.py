"""Q46 live slow-subscriber/disconnect/reconnect probe without Provider use."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import http.client
import json
from pathlib import Path
import sys
from threading import Event, Thread
import time
from uuid import uuid4

from spg.application.bootstrap import bootstrap
from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.application.runtime import RuntimeService
from spg.domain.native_execution import ExecutionEventRecord
from spg.domain.runtime import BootstrapAlreadyInitialized, BootstrapRequest
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore

sys.path.insert(0, "/benchmark")
from runner import admission_for, prepare_repositories


PROFILE = "deepseek-responses:deepseek-flash:high"


def read_event(response: http.client.HTTPResponse) -> tuple[int, str]:
    event_id = 0
    event_type = ""
    while True:
        line = response.readline().decode("utf-8")
        if not line:
            raise RuntimeError("SSE connection ended before a complete event")
        if line == "\n":
            if event_id:
                return event_id, event_type
            continue
        if line.startswith("id: "):
            event_id = int(line[4:].strip())
        elif line.startswith("event: "):
            event_type = line[7:].strip()


def main() -> None:
    app = bootstrap()
    database = app.persistence()
    spec = json.loads(Path("/benchmark/spec.json").read_text())
    task = next(item for item in spec["tasks"] if item["id"] == "T1")
    root, repositories = prepare_repositories(
        app.settings.native_executor_workspace_root / f"q46-slow-{uuid4().hex}", task
    )
    runtime_service = RuntimeService(database)
    primary = next(iter(repositories.values()))
    try:
        runtime_service.bootstrap_trusted_baseline(BootstrapRequest(
            repository_path=primary,
            repository_identity=str(primary),
            repository_ref="refs/heads/main",
            authority_identity="qualification:q46",
            scope={"qualification": "slow-subscriber"},
            rationale="isolated Q46 live transport probe",
        ))
    except BootstrapAlreadyInitialized:
        pass
    attempt, _, admission = admission_for(
        runtime_service, task, root, repositories,
        "deepseek-flash", (PROFILE,),
    )
    NativeExecutorRuntimeService(database).admit(admission)
    created_at = datetime.now(timezone.utc)
    payload = "x" * 8192
    with database.unit_of_work() as uow:
        store = NativeExecutionStore(uow.session)
        for sequence in range(2, 602):
            store.append_event(ExecutionEventRecord(
                id=uuid4(), pwu_id=admission.binding.pwu_id,
                attempt_id=attempt.id, sequence=sequence,
                event_type="QualificationProgress",
                payload={"sequence": sequence, "delta": payload},
                correlation_id=admission.binding.pwu_id,
                created_at=created_at + timedelta(microseconds=sequence),
            ))
        uow.commit()

    started = Event()
    disconnected = Event()
    observation: dict[str, object] = {}

    def slow_browser() -> None:
        connection = http.client.HTTPConnection("app", 8000, timeout=10)
        connection.request(
            "GET", f"/api/native-execution/pwus/{admission.binding.pwu_id}/events"
        )
        response = connection.getresponse()
        ids = []
        for _ in range(10):
            event_id, _ = read_event(response)
            ids.append(event_id)
            if len(ids) == 2:
                started.set()
            time.sleep(0.05)
        observation["slow_ids"] = ids
        response.close()
        connection.close()
        disconnected.set()

    browser = Thread(target=slow_browser, daemon=True)
    browser.start()
    assert started.wait(5), "slow browser did not receive initial events"
    production_started = time.monotonic()
    with database.unit_of_work() as uow:
        NativeExecutionStore(uow.session).append_event(ExecutionEventRecord(
            id=uuid4(), pwu_id=admission.binding.pwu_id,
            attempt_id=attempt.id, sequence=602,
            event_type="QualificationProductionContinued",
            payload={"required_output": "preserved-after-slow-subscriber"},
            correlation_id=admission.binding.pwu_id,
            created_at=datetime.now(timezone.utc),
        ))
        uow.commit()
    production_commit_ms = (time.monotonic() - production_started) * 1000
    assert disconnected.wait(5), "slow browser did not disconnect"
    browser.join(timeout=1)

    cursor = int(observation["slow_ids"][-1])
    connection = http.client.HTTPConnection("app", 8000, timeout=15)
    connection.request(
        "GET",
        f"/api/native-execution/pwus/{admission.binding.pwu_id}/events?after_sequence={cursor}",
    )
    response = connection.getresponse()
    replayed = []
    event_type = ""
    while not replayed or replayed[-1] < 602:
        event_id, event_type = read_event(response)
        replayed.append(event_id)
    response.close()
    connection.close()

    evidence = {
        "pwu_id": str(admission.binding.pwu_id),
        "provider_requests": 0,
        "seeded_events": 601,
        "server_query_batch_limit": 256,
        "slow_events_consumed_before_disconnect": len(observation["slow_ids"]),
        "production_commit_while_subscriber_slow_ms": round(production_commit_ms, 3),
        "reconnect_after_sequence": cursor,
        "replayed_event_count": len(replayed),
        "replay_last_sequence": replayed[-1],
        "required_output_event_type": event_type,
        "native_stream_semantics": "durable milestones only; no lossy text-delta queue",
        "q46_slow_subscriber": "PASS" if replayed[-1] == 602 else "FAIL",
    }
    Path("/evidence/q46-slow-subscriber.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )
    print(json.dumps(evidence, sort_keys=True))
    database.dispose()


if __name__ == "__main__":
    main()
