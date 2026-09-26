"""External Evidence survives the real Interaction, Connector, and HTTP path."""

import os
import json
from time import monotonic, sleep
from types import SimpleNamespace
from uuid import UUID

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

from tests.test_external_research import _GitHub, _Web, _evidence


class _Semantic:
    def interpret(self, basis):
        return InteractionAssessmentCandidate(
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
            postgres_database, capability=_Semantic(),
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
