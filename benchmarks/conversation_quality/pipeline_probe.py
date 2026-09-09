"""Bounded real-provider HTTP/SSE probe against an empty isolated test database.

Run only with --run-real-provider. Source is selected through PYTHONPATH so the
same probe can measure a preserved baseline and the working implementation.
Never points at a product database, truncates data, or invokes production.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import inspect
import json
import os
from pathlib import Path
import socket
from threading import Thread
import time
from urllib.request import Request, urlopen
from uuid import UUID

import uvicorn
from sqlalchemy import func, select

from spg.api import create_http_application
from spg.application.bootstrap import bootstrap
from spg.application.interaction import WorkInteractionService
from spg.config import Settings
from spg.infrastructure.persistence import Database, runtime_tables
from spg.infrastructure.persistence.product_schema import product_works
import spg.providers.codex_interaction as provider_module
from spg.providers.codex_interaction import CodexSdkWorkInteractionCapability


SCENARIOS = (
    "I want to build an operation management platform.",
    "The platform is for promoting Watt, targeting individual developers and small teams.",
    "Not an operation plan. I want a Web application system.",
    "Where will the design document be output?",
    "Please explain the design approach and next steps in detail.",
)


SCENARIOS_V31_ZH = (
    "我想做一个运营管理平台。",
    "这个平台主要用于推广 Watt。\n目标用户包括个人开发者、小型开发团队。\n渠道包括公众号、小红书和直播。",
    "不对，我不是想设计运营活动，我是想开发一个后台系统。",
    "设计方案的文档会输出到哪里？",
    "你建议下一步先设计什么？",
)


def completed_top_level_string(buffer: str, field: str) -> str | None:
    """Observe a closed top-level string without accepting partial JSON as truth."""
    decoder = json.JSONDecoder()
    index = 0
    try:
        while index < len(buffer) and buffer[index].isspace():
            index += 1
        if index == len(buffer) or buffer[index] != "{":
            return None
        index += 1
        while True:
            while index < len(buffer) and buffer[index].isspace():
                index += 1
            key, index = decoder.raw_decode(buffer, index)
            if not isinstance(key, str):
                return None
            while index < len(buffer) and buffer[index].isspace():
                index += 1
            if index == len(buffer) or buffer[index] != ":":
                return None
            index += 1
            while index < len(buffer) and buffer[index].isspace():
                index += 1
            value, index = decoder.raw_decode(buffer, index)
            if key == field:
                return value if isinstance(value, str) else None
            while index < len(buffer) and buffer[index].isspace():
                index += 1
            if index == len(buffer) or buffer[index] != ",":
                return None
            index += 1
    except (ValueError, IndexError):
        return None


class ProviderObservation:
    """Benchmark-only SDK boundary observations; never changes domain contracts."""

    def __init__(self, stage, request_clock):
        self.stage = stage
        self.request_clock = request_clock

    def mark(self, name):
        self.stage.setdefault(name + "_seconds", time.monotonic() - self.request_clock[0])

    def factory(self, original):
        observation = self

        class Context:
            def __enter__(self):
                observation.mark("sdk_starting")
                self.context = original()
                self.client = self.context.__enter__()
                observation.mark("sdk_ready")
                return self

            def __exit__(self, *args):
                observation.mark("sdk_teardown_started")
                try:
                    return self.context.__exit__(*args)
                finally:
                    observation.mark("sdk_teardown_completed")

            def thread_start(self, *args, **kwargs):
                observation.mark("provider_thread_requested")
                thread = self.client.thread_start(*args, **kwargs)
                observation.mark("provider_thread_ready")
                return ObservedThread(thread)

        class ObservedThread:
            def __init__(self, thread):
                self.thread = thread
                self.id = thread.id

            def turn(self, *args, **kwargs):
                observation.mark("provider_turn_requested")
                turn = self.thread.turn(*args, **kwargs)
                observation.mark("provider_turn_ready")
                return ObservedTurn(turn)

        class ObservedTurn:
            def __init__(self, turn):
                self.turn = turn
                self.id = turn.id

            def interrupt(self):
                return self.turn.interrupt()

            def stream(self):
                buffer = ""
                for notification in self.turn.stream():
                    if notification.method == "item/agentMessage/delta":
                        observation.mark("first_raw_provider_delta")
                        buffer += str(notification.payload.delta)
                        if completed_top_level_string(buffer, "natural_response") is not None:
                            observation.mark("natural_response_completed")
                    elif notification.method == "item/completed":
                        item = notification.payload.item
                        if getattr(item, "type", None) == "agentMessage":
                            buffer = str(item.text)
                            observation.mark("semantic_envelope_completed")
                            if completed_top_level_string(buffer, "natural_response") is not None:
                                observation.mark("natural_response_completed")
                            observation.stage["wire_characters"] = len(buffer)
                            observation.stage["wire_utf8_bytes"] = len(buffer.encode("utf-8"))
                            try:
                                wire = json.loads(buffer)
                                observation.stage["wire_semantic_field_characters"] = {
                                    key: len(json.dumps(value, ensure_ascii=False))
                                    for key, value in wire.get("semantics", {}).items()
                                }
                            except (ValueError, AttributeError):
                                pass
                    elif notification.method == "turn/completed":
                        observation.mark("provider_terminal")
                        # Some SDK versions expose no agentMessage item/completed.
                        # Terminal receipt is the conservative complete-envelope boundary.
                        terminal = notification.payload.turn
                        status = getattr(terminal.status, "value", terminal.status)
                        if status == "completed" and terminal.error is None:
                            observation.mark("semantic_envelope_completed")
                        observation.stage.setdefault("wire_characters", len(buffer))
                        observation.stage.setdefault("wire_utf8_bytes", len(buffer.encode("utf-8")))
                        try:
                            wire = json.loads(buffer)
                            observation.stage.setdefault("wire_semantic_field_characters", {
                                key: len(json.dumps(value, ensure_ascii=False))
                                for key, value in wire.get("semantics", {}).items()
                            })
                        except (ValueError, AttributeError):
                            pass
                    yield notification
                observation.mark("provider_stream_closed")

        return Context

    def install_validation_observer(self):
        payload = provider_module._CoalescedInteractionProviderPayload
        original = payload.model_validate_json
        observation = self

        def validate(cls, *args, **kwargs):
            observation.mark("wire_validation_started")
            result = original(*args, **kwargs)
            observation.mark("wire_validation_completed")
            return result

        payload.model_validate_json = classmethod(validate)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-real-provider", action="store_true", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--scenario-set", choices=("v3-en", "v31-zh"), default="v3-en")
    parser.add_argument("--separate-pre-work", action="store_true")
    parser.add_argument("--semantic-effort", default=None)
    parser.add_argument("--conversation-effort", default=None)
    args = parser.parse_args()
    scenarios = SCENARIOS_V31_ZH if args.scenario_set == "v31-zh" else SCENARIOS
    database = Database.from_settings(Settings(database_url=os.environ["SPG_TEST_DATABASE_URL"]))
    database_name = database.engine.url.database or ""
    if not database_name.startswith("spg_pipeline_"):
        raise ValueError("Probe requires a new dedicated spg_pipeline_* database")
    with database.engine.connect() as connection:
        if connection.scalar(select(func.count()).select_from(product_works)):
            raise ValueError("Probe database must contain no Work")
        from spg.infrastructure.persistence.interaction_store import InteractionStore
        with database.unit_of_work() as uow:
            if InteractionStore(uow.session).list_interactions():
                raise ValueError("Probe requires a fresh database with no interactions")
    options = {}
    if args.separate_pre_work:
        options["coalesce_pre_work"] = False
    if args.semantic_effort is not None:
        options["reasoning_effort"] = args.semantic_effort
    if args.conversation_effort is not None:
        options["conversation_reasoning_effort"] = args.conversation_effort
    # Empty cwd prevents incidental repository instructions entering the probe.
    provider_root = args.output.parent / "provider-empty-cwd"
    provider_root.mkdir(parents=True, exist_ok=True)
    stage = {}
    request_clock = [time.monotonic()]
    observation = ProviderObservation(stage, request_clock)
    observation.install_validation_observer()
    capability = CodexSdkWorkInteractionCapability(
        repository_location=str(provider_root.resolve()), model=args.model,
        conversation_model=args.model, timeout_seconds=180,
        codex_factory=observation.factory(provider_module.Codex), **options,
    )
    original_semantic = capability.semantic_capability.interpret_semantics
    original_compose = capability.response_composer.compose

    def semantic(basis):
        started = time.monotonic()
        stage["semantic_prompt_chars"] = len(capability.semantic_capability.instruction(basis))
        try:
            return original_semantic(basis)
        finally:
            stage["semantic_seconds"] = time.monotonic() - started

    def compose(*values, **kwargs):
        started = time.monotonic()
        try:
            return original_compose(*values, **kwargs)
        finally:
            stage["conversation_seconds"] = time.monotonic() - started

    capability.semantic_capability.interpret_semantics = semantic
    capability.response_composer.compose = compose
    service = WorkInteractionService(database, capability=capability)
    original_basis = service._basis
    original_admit = service.admit_candidate

    def basis(*args, **kwargs):
        observation.mark("basis_started")
        value = original_basis(*args, **kwargs)
        observation.mark("basis_prepared")
        return value

    def admit(*args, **kwargs):
        observation.mark("admission_started")
        value = original_admit(*args, **kwargs)
        observation.mark("assessment_persisted")
        return value

    service._basis = basis
    service.admit_candidate = admit
    app = create_http_application(
        application=bootstrap(Settings(executor_adapter="unconfigured")),
        database=database, interaction_service=service,
    )
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="off"))
    worker = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    worker.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("Probe HTTP server did not start")
        time.sleep(0.01)
    origin = f"http://127.0.0.1:{listener.getsockname()[1]}"

    def request(path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = Request(origin + path, data=data, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=400) as response:
            return json.load(response)

    source_root = Path(inspect.getfile(CodexSdkWorkInteractionCapability)).resolve().parents[2]
    source_files = {
        path.relative_to(source_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(source_root.rglob("*"))
        if path.is_file() and path.suffix in {".py", ".js", ".css", ".html"}
    }
    source_fingerprint = hashlib.sha256(
        json.dumps(source_files, sort_keys=True).encode()
    ).hexdigest()
    report = {"label": args.label, "source_fingerprint": source_fingerprint,
              "source_files": source_files,
              "probe_fingerprint": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "recorded_at": datetime.now(UTC).isoformat(),
              "model": args.model, "scenario_set": args.scenario_set, "semantic_effort": args.semantic_effort,
              "conversation_effort": args.conversation_effort, "cases": [],
              "scope": "five Human turns, real provider, isolated database and loopback HTTP; no production"}

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    try:
        created = request("/api/interactions", {"human_identity": "human:pipeline-validation"})
        interaction_id = created["interaction_id"]
        for number, message in enumerate(scenarios, 1):
            stage.clear()
            case = {"number": number, "message": message,
                    "request_started_at": datetime.now(UTC).isoformat(),
                    "first_event_seconds": None, "first_text_seconds": None}
            report["cases"].append(case)
            started = time.monotonic()
            request_clock[0] = started
            submitted = request(f"/api/interactions/{interaction_id}/turns", {
                "content": message, "human_identity": "human:pipeline-validation"})
            case["ack_seconds"] = time.monotonic() - started
            turn_id = UUID(submitted["turn_id"])
            event = None
            streamed = ""
            with urlopen(f"{origin}/api/interactions/{interaction_id}/turns/{turn_id}/events", timeout=400) as stream:
                for raw in stream:
                    line = raw.decode("utf-8").strip()
                    if line.startswith("event: "):
                        event = line[7:]
                        if case["first_event_seconds"] is None:
                            case["first_event_seconds"] = time.monotonic() - started
                    elif line.startswith("data: "):
                        payload = json.loads(line[6:])
                        if event == "message.delta" and payload["delta"]:
                            if payload["delta"].strip() and case["first_text_seconds"] is None:
                                case["first_text_seconds"] = time.monotonic() - started
                            streamed += payload["delta"]
                        elif event == "message.reset":
                            if payload["content"].strip() and case["first_text_seconds"] is None:
                                case["first_text_seconds"] = time.monotonic() - started
                            streamed = payload["content"]
                        elif event in {"message.completed", "turn.failed"}:
                            case["completion_seconds"] = time.monotonic() - started
                            break
            turn = service.get_turn(turn_id)
            case.update(stage)
            case.update(status=turn.status.value, request_received_at=turn.created_at.isoformat(),
                        persisted_completed_at=turn.completed_at.isoformat() if turn.completed_at else None)
            if hasattr(service, "turn_timing"):
                case["server_timing"] = service.turn_timing(turn_id)
            if turn.status.value != "COMPLETED":
                case["failure_code"] = turn.failure_code
                save()
                raise RuntimeError(f"Probe case {number} failed: {turn.failure_code}")
            projection = service.get_shared_understanding(UUID(interaction_id))
            replies = [item for item in projection.conversation_messages
                       if item.turn_id == turn_id and item.actor.value == "WATT"]
            assert len(replies) == 1 and replies[0].content == streamed
            case["response"] = replies[0].content
            case["intent"] = capability.last_collaboration_result.turn_intent.value
            case["frame"] = projection.latest_assessment.design_intent_frame.model_dump(mode="json")
            case["schema"] = projection.interaction.selected_design_schema_identity
            case["provider"] = asdict(capability.last_pipeline_evidence)
            if hasattr(service, "turn_timing"):
                case["server_timing"] = service.turn_timing(turn_id)
            assert case["frame"]["object_type"] == "PRODUCT_SYSTEM"
            assert case["schema"] == "watt:guided-design:general-product-system"
            expected_intents = ("NEW_GOAL", "CONTEXT_ADDITION", "CORRECTION", "DIRECT_QUESTION", "REQUEST_DETAIL")
            if args.scenario_set == "v31-zh":
                expected_intents = (*expected_intents[:4], "REQUEST_RECOMMENDATION")
            assert case["intent"] == expected_intents[number - 1]
            case["response_characters"] = len(case["response"])
            case["question_marks"] = case["response"].count("?") + case["response"].count("？")
            case["detailed_explanation_requested"] = capability.last_collaboration_result.detailed_explanation_requested
            with database.engine.connect() as connection:
                counts = {table.name: connection.scalar(select(func.count()).select_from(table))
                          for table in (product_works, *runtime_tables)}
            assert not any(counts.values()), "Probe created Work or production facts"
            case["work_and_runtime_rows"] = sum(counts.values())
            save()
            print(json.dumps({key: value for key, value in case.items()
                              if key not in {"response", "frame", "provider"}}), flush=True)
        report["completed"] = True
        save()
    except Exception as error:
        report["failure_type"] = type(error).__name__
        save()
        raise
    finally:
        server.should_exit = True
        worker.join(timeout=10)
        service.shutdown()
        database.dispose()


if __name__ == "__main__":
    main()
