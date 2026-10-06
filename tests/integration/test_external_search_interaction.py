"""External Evidence survives the real Interaction, Connector, and HTTP path."""

import os
import json
from time import monotonic, sleep
from types import SimpleNamespace
from uuid import UUID
import pytest

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from spg.api import create_http_application
from spg.application.bootstrap import Application
from spg.application.connectors import ConnectorResolver
from spg.application.external_research import GovernedExternalResearch
from spg.application.interaction import WorkInteractionService
from spg.application.production_intelligence import default_system_capability_reality
from spg.config import Settings
from spg.domain.interaction import InteractionAssessmentCandidate, InteractionTurnStatus
from spg.domain.wic_response import WicRuntimeMode
from spg.providers.external_search import BoundedPublicHttp, BraveWebSearchProvider
from spg.application.wic_reception import (
    DeterministicFastReceptionCapability, ShadowFastReceptionRuntime,
)

from tests.irk_test_fixtures import semantic_candidate
from spg.domain.intent_realization import SemanticArgument, SemanticProvenance, SemanticOrigin, SemanticItem, SemanticKind, OperationalIntent
from tests.test_external_research import _GitHub, _Web, _evidence


class _Semantic:
    def __init__(self, operations=("SEARCH_GITHUB",), repository_source=None):
        self.operations = operations
        self.repository_source = repository_source

    def interpret(self, basis):
        record = basis.records[-1]
        source = SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT, source_record_id=record.id, source_text=record.content)
        inferred = SemanticProvenance(origin=SemanticOrigin.MODEL_CANDIDATE, evidence_reference="compiler:query")
        items = tuple(SemanticItem(item_id=f"search-{index}", kind=SemanticKind.OPERATIONAL_ACTION, statement="Declared retrieval request", provenance=(source,), confidence=1, action=OperationalIntent(operation=operation, speech_act="EXPLICIT_REQUEST", arguments={"query": SemanticArgument(value="python async queue", provenance=inferred)})) for index, operation in enumerate(self.operations))
        ir = semantic_candidate(record, extra_items=items)
        if self.repository_source:
            from spg.domain.intent_realization import ProductionIntent
            ir = semantic_candidate(record, production=ProductionIntent(objective="Later implementation", primary_change="Unresolved", current=False, bounded_change=False, repository_reference=SemanticArgument(value=self.repository_source, provenance=source)), extra_items=items)
        return InteractionAssessmentCandidate(
            semantic_intent=ir,
            interpreted_motive="Find public async queue implementations",
            current_requests=(basis.records[-1].content,),
            natural_response="I can discuss queue designs from memory.",
            provider_identity="test:wic-semantic",
        )


def _wait(service, turn_id: UUID):
    deadline = monotonic() + 8
    while monotonic() < deadline:
        turn = service.get_turn(turn_id)
        if turn.status in {InteractionTurnStatus.COMPLETED, InteractionTurnStatus.FAILED}:
            return turn
        sleep(0.03)
    raise AssertionError("Interaction Turn did not settle")


def test_gzip_fetch_content_survives_canonical_turn_jsonb_persistence(postgres_database, monkeypatch):
    """Wire gzip cannot be treated as text and poison the response-event JSONB."""
    import gzip
    import io
    from spg.providers.external_search import inspect_web_resource
    monkeypatch.setenv("SPG_DATABASE_URL", os.environ["SPG_TEST_DATABASE_URL"])
    command.upgrade(Config("alembic.ini"), "head")
    monkeypatch.setattr(BoundedPublicHttp, "_check_url", staticmethod(lambda _: None))
    class Response(io.BytesIO):
        headers = {"Content-Type":"text/html", "Content-Encoding":"gzip"}
    http = BoundedPublicHttp()
    http.opener = SimpleNamespace(open=lambda *a, **k: Response(gzip.compress(b'<main>Exact compressed reference</main>')))
    class GitHub(_GitHub):
        def inspect_result(self, item):
            return inspect_web_resource(http, item)
    research = GovernedExternalResearch(ConnectorResolver(postgres_database),
        github=GitHub(((_evidence("compressed"),),)), web=_Web(), http=http)
    service = WorkInteractionService(postgres_database, capability=_Semantic(),
        runtime_mode=WicRuntimeMode.WIC_VNEXT_CONTROLLED, external_research=research)
    try:
        item = service.create_interaction(human_identity="human:gzip-regression")
        turn = service.submit_turn(item.id, "检索并核查公开来源", human_identity="human:gzip-regression")
        settled = _wait(service, turn.id)
        assert settled.status is InteractionTurnStatus.COMPLETED, settled.failure_message
        events = service.response_events(turn.id)
        inspected = [e.metadata for e in events if e.event_type.value == "SEARCH_EVIDENCE"]
        assert any(e.get("inspected_content") == "Exact compressed reference" for e in inspected)
        assert all("\x00" not in json.dumps(e) for e in inspected)
        assert service.get_shared_understanding(item.id).conversation_messages[-1].content
    finally:
        service.shutdown()


def test_explicit_search_uses_connector_and_persists_source_evidence(postgres_database, monkeypatch):
    monkeypatch.setenv("SPG_DATABASE_URL", os.environ["SPG_TEST_DATABASE_URL"])
    command.upgrade(Config("alembic.ini"), "head")
    github = _GitHub(((_evidence("one"), _evidence("two", 2)),))
    research = GovernedExternalResearch(
        ConnectorResolver(postgres_database), github=github, web=_Web(),
        http=BoundedPublicHttp(),
    )
    service = WorkInteractionService(
        postgres_database, capability=_Semantic(),
        runtime_mode=WicRuntimeMode.WIC_VNEXT_CONTROLLED,
        external_research=research,
    )
    interaction = service.create_interaction(human_identity="human:search-test")
    turn = service.submit_turn(
        interaction.id, "帮我查 GitHub 上关于 async queue 的实现",
        human_identity="human:search-test",
    )
    settled = _wait(service, turn.id)
    assert settled.status is InteractionTurnStatus.COMPLETED, settled.failure_message
    projection = service.get_shared_understanding(interaction.id)
    assert projection.governed_work_id is None
    answer = projection.conversation_messages[-1]
    assert "https://github.com/owner/one" in answer.content
    assert "discuss queue designs from memory" not in answer.content
    assert "external-search:one" in answer.supporting_references
    events = service.response_events(turn.id)
    assert any(event.event_type.value == "SEARCH_STARTED" for event in events)
    assert any(event.event_type.value == "SEARCH_EVIDENCE" and
               event.metadata.get("completeness") == "INSPECTED" for event in events)
    assert any(event.event_type.value == "SEARCH_COMPLETED" and
               event.metadata["metrics"]["sufficient"] for event in events)
    app = create_http_application(
        Application(Settings(database_url=os.environ["SPG_TEST_DATABASE_URL"])),
        database=postgres_database, interaction_service=service,
    )
    with TestClient(app) as client:
        response = client.get(
            f"/api/interactions/{interaction.id}/turns/{turn.id}/external-evidence"
        )
    assert response.status_code == 200
    assert response.json()["state"] == "COMPLETED"
    assert len(response.json()["evidence"]) == 2
    assert response.json()["evidence"][0]["url"].startswith("https://github.com/")


def test_combined_github_web_search_merges_real_provider_shapes_without_duplicate_claims(
    postgres_database, monkeypatch,
):
    monkeypatch.setenv("SPG_DATABASE_URL", os.environ["SPG_TEST_DATABASE_URL"])
    monkeypatch.setenv("SPG_WEB_SEARCH_API_KEY", "integration-test-key")
    default_system_capability_reality.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")

    class WebTransport:
        def get(self, url, *, headers=None):
            if "api.search.brave.com" in url:
                assert headers["X-Subscription-Token"] == "integration-test-key"
                return json.dumps({"web": {"results": [{
                    "title": "Python asyncio documentation",
                    "url": "https://docs.python.org/3/library/asyncio.html",
                    "description": "Official reference for Python async I/O",
                }]}}).encode(), "application/json"
            return b"<main><h1>asyncio</h1><p>asyncio is a library for concurrent code.</p></main>", "text/html"

    try:
        github = _GitHub(((_evidence("one"), _evidence("two", 2)),))
        http = WebTransport()
        research = GovernedExternalResearch(
            ConnectorResolver(postgres_database), github=github,
            web=BraveWebSearchProvider(http, api_key="integration-test-key"),
            http=http,
        )
        service = WorkInteractionService(
            postgres_database, capability=_Semantic(("SEARCH_GITHUB", "SEARCH_WEB")),
            runtime_mode=WicRuntimeMode.WIC_VNEXT_CONTROLLED,
            external_research=research,
        )
        interaction = service.create_interaction(human_identity="human:search-test")
        turn = service.submit_turn(
            interaction.id, "帮我查 GitHub 和网上关于 async queue 的实现",
            human_identity="human:search-test",
        )
        settled = _wait(service, turn.id)
        assert settled.status is InteractionTurnStatus.COMPLETED, settled.failure_message
        events = service.response_events(turn.id)
        completed = next(event for event in events if event.event_type.value == "SEARCH_COMPLETED")
        metrics = completed.metadata["metrics"]
        assert metrics["query_count"] >= 2
        assert metrics["result_count"] == 3
        assert metrics["fetch_count"] >= 2
        assert metrics["failure_categories"] == []
        sources = [event.metadata for event in events if event.event_type.value == "SEARCH_EVIDENCE"]
        assert any(item.get("source_type") == "WEB" and
                   item.get("completeness") == "INSPECTED" for item in sources)
        answer = service.get_shared_understanding(interaction.id).conversation_messages[-1].content
        assert "docs.python.org" in answer and "github.com" in answer
    finally:
        default_system_capability_reality.cache_clear()


def test_model_search_gap_suppresses_memory_provisional_in_shadow_mode(postgres_database, monkeypatch):
    monkeypatch.setenv("SPG_DATABASE_URL", os.environ["SPG_TEST_DATABASE_URL"])
    command.upgrade(Config("alembic.ini"), "head")

    class Model:
        def generate(self, *, instructions, **_):
            if instructions.startswith("Identify"):
                result = {"needed": True, "query": "python async task queue",
                          "sources": ["GITHUB"],
                          "information_gap": "Current maintenance requires source evidence"}
            else:
                result = {"observations": [{"evidence_id": "external-search:one",
                                            "fact": "README documents a queue API"}],
                          "comparison": "One inspected candidate; maintenance needs more evidence.",
                          "limitations": "Only sampled repositories were inspected.",
                          "cited_evidence_ids": ["external-search:one"]}
            return SimpleNamespace(output_text=json.dumps(result),
                                   usage=SimpleNamespace(total_tokens=200))

    research = GovernedExternalResearch(
        ConnectorResolver(postgres_database),
        github=_GitHub(((_evidence("one"),), (_evidence("one"), _evidence("two", 2)))),
        web=_Web(), http=BoundedPublicHttp(), model=Model(),
    )
    service = WorkInteractionService(
        postgres_database, capability=_Semantic(),
        runtime_mode=WicRuntimeMode.WIC_VNEXT_SHADOW,
        fast_reception=ShadowFastReceptionRuntime(DeterministicFastReceptionCapability()),
        external_research=research,
    )
    published = []
    monkeypatch.setattr(service, "_publish_turn_response_delta",
                        lambda _turn_id, content: published.append(content))
    interaction = service.create_interaction(human_identity="human:search-test")
    turn = service.submit_turn(
        interaction.id, "目前 Python 异步任务队列有哪些维护活跃的库？",
        human_identity="human:search-test",
    )
    settled = _wait(service, turn.id)
    assert settled.status is InteractionTurnStatus.COMPLETED, settled.failure_message
    events = service.response_events(turn.id)
    assert not any(event.event_type.value == "PROVISIONAL_RESPONSE" for event in events)
    assert not any("discuss queue designs from memory" in (event.content or "")
                   for event in events)
    assert sum(event.event_type.value == "SEARCH_STARTED" for event in events) == 2
    assert published == ["正在检索公开来源并核查结果…"]
    answer = service.get_shared_understanding(interaction.id).conversation_messages[-1].content
    assert "https://github.com/owner/one" in answer


@pytest.mark.parametrize("invalid_first_synthesis", [False, True])
def test_project_research_observation_survives_real_turn_event_persistence(
    postgres_database, monkeypatch, invalid_first_synthesis,
):
    monkeypatch.setenv("SPG_DATABASE_URL", os.environ["SPG_TEST_DATABASE_URL"])
    command.upgrade(Config("alembic.ini"), "head")
    packet = {"condition":"READY", "repository_identity":"https://github.com/owner/project.git",
        "revision":"a" * 40,"tree":"b" * 40,
        "materials":[{"path":"server.py","content":"from http.server import HTTPServer"}]}
    class Model:
        calls = 0

        def generate(self, *, instructions, **_):
            if instructions.startswith("Identify"):
                return SimpleNamespace(output_text=json.dumps({
                    "needed": True, "query": "python queue adapter",
                    "sources": ["GITHUB"], "information_gap": "Inspect mature source implementations",
                }), usage=SimpleNamespace(total_tokens=50))
            self.calls += 1
            valid = not invalid_first_synthesis or self.calls > 1
            return SimpleNamespace(output_text=json.dumps({
                "observations": [{"evidence_id": "external-search:one", "fact": "Observed queue API"}],
                "comparison": "An inspected queue can integrate at the existing HTTP boundary.",
                "limitations": "Only bounded project source was inspected.",
                "cited_evidence_ids": ["external-search:one"],
                "project_recommendation": "Use the existing Python HTTPServer boundary." if valid else "",
                "project_evidence_paths": ["server.py"] if valid else [],
            }), usage=SimpleNamespace(total_tokens=100))

    model = Model()
    research = GovernedExternalResearch(ConnectorResolver(postgres_database),
        github=_GitHub(((_evidence("one"),_evidence("two",2)),)), web=_Web(),
        http=BoundedPublicHttp(), project_repository=lambda **_: packet, model=model)
    service = WorkInteractionService(postgres_database, capability=_Semantic(repository_source="https://github.com/owner/project.git"),
        runtime_mode=WicRuntimeMode.WIC_VNEXT_CONTROLLED, external_research=research)
    interaction = service.create_interaction(human_identity="human:research-test")
    turn = service.submit_turn(interaction.id,
        "这是项目仓库：https://github.com/owner/project.git\n搜索 GitHub 的成熟实现并建议当前项目如何使用。",
        human_identity="human:research-test")
    settled = _wait(service, turn.id)
    assert settled.status is InteractionTurnStatus.COMPLETED, settled.failure_message
    events = service.response_events(turn.id)
    observed = next(event for event in events if event.event_type.value == "PROJECT_RESEARCH_EVIDENCE")
    assert observed.metadata["repository_observation"] == packet
    assert observed.metadata["production_authorized"] is False
    projection = service.get_shared_understanding(interaction.id)
    assert projection.governed_work_id is None
    assert "commit " + "a" * 40 in projection.conversation_messages[-1].content
    app = create_http_application(Application(Settings(database_url=os.environ["SPG_TEST_DATABASE_URL"])),
        database=postgres_database, interaction_service=service)
    with TestClient(app) as client:
        result = client.get(f"/api/interactions/{interaction.id}/turns/{turn.id}/external-evidence").json()
        stream = client.get(f"/api/interactions/{interaction.id}/turns/{turn.id}/events")
    assert stream.status_code == 200
    assert "event: response.final" in stream.text
    assert "event: message.completed" in stream.text
    assert "from http.server import HTTPServer" not in stream.text
    assert result["project_observation"]["revision"] == "a" * 40
    assert result["project_observation"]["materials"][0]["path"] == "server.py"
    assert "content" not in result["project_observation"]["materials"][0]
    assert len(result["synthesis_refinements"]) == int(invalid_first_synthesis)
    assert model.calls == 1 + int(invalid_first_synthesis)
    if invalid_first_synthesis:
        assert "event: search.refinement" in stream.text
        assert result["synthesis_refinements"][0]["attempt_budget"] == 2
