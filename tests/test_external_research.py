"""Bounded Search qualification without external provider dependence."""

import base64
from datetime import UTC, datetime
import json
from types import SimpleNamespace
from urllib.error import HTTPError
from uuid import uuid4

import pytest

from spg.application.connector_manifest import built_in_executable_capabilities
from spg.application.external_research import (
    GovernedExternalResearch, explicit_search_intents, potential_external_research,
)
from spg.domain.connectors import ConnectorResolution
from spg.domain.external_search import (
    SearchBudget, SearchEvidence, SearchFailure, SearchIntent, SearchProviderError,
    SearchRequest,
)
from spg.providers.external_search import (
    BoundedPublicHttp, BraveWebSearchProvider, GitHubPublicSearchProvider,
    inspect_web_resource,
)


def _evidence(name: str, rank: int = 1, inspected: bool = False) -> SearchEvidence:
    return SearchEvidence(
        evidence_id=f"external-search:{name}", source_type="GITHUB",
        provider="github-rest-public", query="async queue", title=f"owner/{name}",
        url=f"https://github.com/owner/{name}", retrieved_at=datetime.now(UTC),
        rank=rank, snippet="Async queue implementation", metadata={"stars": 100},
        inspected_content="Documented queue API" if inspected else None,
        completeness="INSPECTED" if inspected else "SEARCH_RESULT",
    )


class _Resolver:
    def __init__(self):
        self.calls = []
        self.capabilities = {item.capability_id: item for item in built_in_executable_capabilities()}

    def resolve(self, requirement, *, record_gap=True):
        self.calls.append((requirement.capability_id, record_gap, requirement.operation_ref))
        capability = self.capabilities[requirement.capability_id]
        executable = capability.availability.value == "AVAILABLE"
        return ConnectorResolution(requirement=requirement, capability=capability,
                                   executable=executable, reason="test")


class _GitHub:
    def __init__(self, results):
        self.results = results
        self.queries = []

    def search(self, query, kind="repositories", *, limit=6):
        self.queries.append((query, kind))
        return self.results[min(len(self.queries) - 1, len(self.results) - 1)]

    def inspect_repository(self, item):
        return item.model_copy(update={"inspected_content": "Documented queue API",
                                       "completeness": "INSPECTED"})

    def inspect_result(self, item):
        return self.inspect_repository(item)


class _Web:
    def search(self, query, *, limit=6):
        raise AssertionError("Web provider should be capability-blocked without a key")


def _research(github, *, budget=None):
    resolver = _Resolver()
    service = GovernedExternalResearch(resolver, github=github, web=_Web(),
                                       http=object(), budget=budget)
    return service, resolver


def test_explicit_search_routing_is_canonical_and_not_production_mutation():
    assert explicit_search_intents("帮我查下 GitHub 上或者网上有没有关于异步队列的好实现") == (
        SearchIntent.SEARCH_GITHUB_REPOSITORIES, SearchIntent.SEARCH_WEB,
    )
    assert explicit_search_intents("查下这个技术有没有现成库") == (
        SearchIntent.SEARCH_GITHUB_REPOSITORIES,
    )
    assert explicit_search_intents("搜下网上有没有成熟实现") == (SearchIntent.SEARCH_WEB,)
    assert explicit_search_intents("帮我查 GitHub issue 里的相关问题") == (
        SearchIntent.SEARCH_GITHUB_ISSUES,
    )
    assert explicit_search_intents("帮我开发一个异步队列") == ()
    assert explicit_search_intents("find a report about delivery metrics") == ()
    assert explicit_search_intents("帮我找相关repo") == (SearchIntent.SEARCH_GITHUB_REPOSITORIES,)
    assert potential_external_research("目前 Python 异步任务队列有哪些维护活跃的库？")
    assert not potential_external_research("帮我开发一个异步队列")


def test_query_refines_once_and_stops_on_repeated_evidence():
    github = _GitHub(((_evidence("first"),), (_evidence("first"),)))
    service, resolver = _research(github, budget=SearchBudget(max_queries=3, max_fetches=1))
    events = []
    result = service.run(
        turn_id=uuid4(), interaction_id=uuid4(), work_id=None,
        user_id="human:test", text="查 GitHub 异步队列实现",
        requests=(SearchRequest(intent=SearchIntent.SEARCH_GITHUB_REPOSITORIES,
                                query="async queue implementation", reason="Human request", origin="HUMAN_EXPLICIT"),),
        on_event=lambda kind, details: events.append((kind, details)),
    )
    assert result.metrics.query_count == 2
    assert result.metrics.refinement_count == 1
    assert len(result.evidence) == 1
    assert result.evidence[0].completeness == "INSPECTED"
    assert not result.metrics.sufficient
    assert "INSUFFICIENT_EVIDENCE" in result.metrics.failure_categories
    assert github.queries[1][0] != github.queries[0][0]
    assert {call[0] for call in resolver.calls} == {"github.repository.search", "github.resource.fetch"}
    assert all(not call[1] for call in resolver.calls)  # no non-existent pre-Work gap FK
    assert all(call[2] == f"task-contract:{result.task_contract_id}" for call in resolver.calls)
    assert any(kind == "SEARCH_EVIDENCE" and details["completeness"] == "INSPECTED"
               for kind, details in events)
    assert result.evidence[0].url in result.answer


def test_weak_mature_repository_set_broadens_to_better_observed_candidates():
    weak = (_evidence("small-one"), _evidence("small-two", 2))
    weak = tuple(item.model_copy(update={"metadata": {"stars": 4}}) for item in weak)
    strong = (_evidence("strong-one"), _evidence("strong-two", 2))
    strong = tuple(item.model_copy(update={"metadata": {"stars": 2000}}) for item in strong)
    github = _GitHub((weak, strong))
    service, _ = _research(github)
    result = service.run(
        turn_id=uuid4(), interaction_id=uuid4(), work_id=None,
        user_id="human:test", text="查 GitHub 上成熟的 Python asyncio task queue 实现",
        requests=(SearchRequest(intent=SearchIntent.SEARCH_GITHUB_REPOSITORIES,
                                query="python asyncio task queue library", reason="Human request",
                                origin="HUMAN_EXPLICIT"),),
    )
    assert github.queries == [
        ("python asyncio task queue library", "repositories"),
        ("python asyncio task queue", "repositories"),
    ]
    assert result.metrics.refinement_count == 1
    assert len(result.evidence) == 4
    assert any(item.metadata.get("stars") == 2000 for item in result.evidence)
    assert all(item.completeness == "INSPECTED" for item in result.evidence
               if item.metadata.get("stars") == 2000)


def test_web_credential_boundary_preserves_github_results_and_truthful_failure():
    github = _GitHub(((_evidence("one"), _evidence("two", 2)),))
    service, resolver = _research(github)
    result = service.run(
        turn_id=uuid4(), interaction_id=uuid4(), work_id=None,
        user_id="human:test", text="查 GitHub 和网上的异步队列实现",
        requests=(
            SearchRequest(intent=SearchIntent.SEARCH_GITHUB_REPOSITORIES,
                          query="async queue", reason="Human request", origin="HUMAN_EXPLICIT"),
            SearchRequest(intent=SearchIntent.SEARCH_WEB,
                          query="async queue", reason="Human request", origin="HUMAN_EXPLICIT"),
        ),
    )
    assert len(result.evidence) == 2
    assert result.metrics.query_count == 1
    assert SearchFailure.CREDENTIAL_REQUIRED.value in result.metrics.failure_categories
    assert "CREDENTIAL_REQUIRED" in result.answer
    assert "web.search" in {call[0] for call in resolver.calls}


def test_gitHub_code_search_requires_read_credential_without_blocking_public_repos():
    provider = GitHubPublicSearchProvider(BoundedPublicHttp(), token=None)
    with pytest.raises(SearchProviderError) as error:
        provider.search("queue", "code")
    assert error.value.category is SearchFailure.CREDENTIAL_REQUIRED
    assert _Resolver().capabilities["github.repository.search"].availability.value == "AVAILABLE"


def test_authenticated_code_and_public_issue_results_are_inspected_from_exact_resources():
    class Transport:
        def __init__(self):
            self.calls = []

        def get(self, url, *, headers=None):
            self.calls.append((url, headers))
            if "/search/code?" in url:
                payload = {"items": [{"html_url": "https://github.com/owner/repo/blob/main/pkg/queue.py",
                                      "name": "queue.py", "path": "pkg/queue.py",
                                      "repository": {"full_name": "owner/repo", "private": False}}]}
            elif "/search/issues?" in url:
                assert "is%3Aissue" in url
                payload = {"items": [{"html_url": "https://github.com/owner/repo/issues/12",
                                      "title": "Queue retries", "body": "Retry discussion",
                                      "repository": {"full_name": "owner/repo", "private": False}}]}
            elif url.endswith("/issues/12"):
                payload = {"title": "Queue retries", "body": "Maintainer explains retry handling",
                           "state": "open", "updated_at": "2026-09-01T00:00:00Z"}
            elif "/contents/pkg/queue.py?" in url:
                payload = {"encoding": "base64", "content": base64.b64encode(b"class Queue: pass").decode()}
            else:
                assert url == "https://api.github.com/repos/owner/repo"
                payload = {"private": False}
            return json.dumps(payload).encode(), "application/json"

    transport = Transport()
    provider = GitHubPublicSearchProvider(transport, token="read-only-test-token")
    code = provider.search("async queue", "code")[0]
    issue = provider.search("async queue", "issues")[0]
    assert code.completeness == issue.completeness == "SEARCH_RESULT"
    assert "class Queue: pass" in provider.inspect_result(code).inspected_content
    assert "Maintainer explains" in provider.inspect_result(issue).inspected_content
    assert all(headers.get("Authorization") == "Bearer read-only-test-token"
               for _, headers in transport.calls)


def test_public_repository_inspection_includes_readme_root_paths_and_package_metadata():
    class Transport:
        def get(self, url, *, headers=None):
            if url.endswith("/readme"):
                payload = {"encoding": "base64", "path": "README.md",
                           "content": base64.b64encode(b"Queue usage examples").decode()}
            elif url.endswith("/contents/pyproject.toml"):
                payload = {"encoding": "base64",
                           "content": base64.b64encode(b"[project]\nname = 'queue-lib'").decode()}
            elif url.endswith("/contents"):
                payload = [{"path": "README.md"}, {"path": "pyproject.toml"}]
            else:
                payload = {"private": False, "description": "Async queue",
                           "default_branch": "main", "stargazers_count": 40}
            return json.dumps(payload).encode(), "application/json"

    provider = GitHubPublicSearchProvider(Transport())
    inspected = provider.inspect_repository(_evidence("repo"))
    assert inspected.completeness == "INSPECTED"
    assert "Queue usage examples" in inspected.inspected_content
    assert "name = 'queue-lib'" in inspected.inspected_content
    assert inspected.metadata["package_manifest"] == "pyproject.toml"


def test_public_fetch_rejects_local_and_non_https_sources_before_network():
    for url in ("http://example.com", "https://127.0.0.1/private", "https://localhost/private"):
        with pytest.raises(SearchProviderError):
            BoundedPublicHttp._check_url(url)


def test_brave_search_parses_real_api_shape_and_fetches_page_separately():
    class Transport:
        def __init__(self):
            self.calls = []

        def get(self, url, *, headers=None):
            self.calls.append((url, headers))
            if "api.search.brave.com" in url:
                return json.dumps({"web": {"results": [
                    {"title": "Python asyncio guide", "url": "https://docs.python.org/3/library/asyncio.html",
                     "description": "Official asyncio documentation"},
                ]}}).encode(), "application/json"
            return b"<html><nav>Menu</nav><main><h1>asyncio</h1><p>asyncio is a library to write concurrent code.</p></main></html>", "text/html"

    http = Transport()
    provider = BraveWebSearchProvider(http, api_key="test-secret")
    result = provider.search("python asyncio")[0]
    assert result.completeness == "SEARCH_RESULT"
    assert result.snippet == "Official asyncio documentation"
    assert http.calls[0][1]["X-Subscription-Token"] == "test-secret"
    inspected = inspect_web_resource(http, result)
    assert inspected.completeness == "INSPECTED"
    assert "asyncio is a library" in inspected.inspected_content
    assert "Menu" not in inspected.inspected_content
    assert http.calls[1][1].get("X-Subscription-Token") is None


def test_direct_public_resource_request_is_canonicalized():
    service, _ = _research(_GitHub(((),)))
    requests = service.requests_for_turn(
        "请查看 https://github.com/taskiq-python/taskiq/blob/master/README.md",
        "I can inspect that file.",
    )
    assert requests[0].intent is SearchIntent.FETCH_GITHUB_RESOURCE
    assert requests[0].capability_id == "github.resource.fetch"
    assert SearchRequest(
        intent=SearchIntent.INSPECT_SEARCH_RESULT,
        query="https://github.com/owner/repo/blob/main/README.md",
        reason="Inspect selected result", origin="HUMAN_EXPLICIT",
    ).capability_id == "github.resource.fetch"
    assert SearchRequest(
        intent=SearchIntent.INSPECT_SEARCH_RESULT,
        query="https://example.com/article", reason="Inspect selected result",
        origin="HUMAN_EXPLICIT",
    ).capability_id == "web.resource.fetch"


def test_model_information_gap_can_request_governed_search_then_resume_with_evidence():
    class Model:
        def generate(self, *, instructions, **_):
            if instructions.startswith("Identify"):
                content = {"needed": True, "query": "python async queue",
                           "sources": ["GITHUB"],
                           "information_gap": "Current maintenance must be checked externally"}
            else:
                content = {"observations": [
                    {"evidence_id": "external-search:one", "fact": "README documents a queue API"}],
                    "comparison": "This is one candidate; maintenance still needs verification.",
                    "limitations": "Only one source was inspected.",
                    "cited_evidence_ids": ["external-search:one"]}
            return SimpleNamespace(output_text=json.dumps(content),
                                   usage=SimpleNamespace(total_tokens=500))

    github = _GitHub(((_evidence("one"), _evidence("two", 2)),))
    service, resolver = _research(github)
    service.model = Model()
    requests = service.requests_for_turn(
        "目前 Python 异步任务队列有哪些维护活跃的库？",
        "I cannot confirm current maintenance from memory.",
    )
    assert requests and requests[0].origin == "MODEL_INFORMATION_GAP"
    result = service.run(turn_id=uuid4(), interaction_id=uuid4(), work_id=None,
                         user_id="human:test", text="当前有哪些维护活跃的库？",
                         requests=requests)
    assert result.metrics.sufficient
    assert result.metrics.model_tokens == 500
    assert "来源事实 [external-search:one]" in result.answer
    assert "比较与判断" in result.answer
    assert "github.repository.search" in {call[0] for call in resolver.calls}


def test_http_rate_limit_is_not_misreported_as_no_results(monkeypatch):
    http = BoundedPublicHttp()
    monkeypatch.setattr(http, "_check_url", lambda _: None)

    class Denied:
        def open(self, request, *, timeout):
            raise HTTPError(request.full_url, 429, "Rate limited", {}, None)

    http.opener = Denied()
    provider = GitHubPublicSearchProvider(http)
    with pytest.raises(SearchProviderError) as error:
        provider.search("async queue")
    assert error.value.category is SearchFailure.RATE_LIMITED


def test_provider_server_error_is_distinct_from_empty_search(monkeypatch):
    http = BoundedPublicHttp()
    monkeypatch.setattr(http, "_check_url", lambda _: None)

    class Unavailable:
        def open(self, request, *, timeout):
            raise HTTPError(request.full_url, 503, "Unavailable", {}, None)

    http.opener = Unavailable()
    with pytest.raises(SearchProviderError) as error:
        GitHubPublicSearchProvider(http).search("async queue")
    assert error.value.category is SearchFailure.PROVIDER_UNAVAILABLE


def test_rate_limited_research_response_preserves_failure_category():
    class LimitedGithub(_GitHub):
        def search(self, query, kind="repositories", *, limit=6):
            raise SearchProviderError(SearchFailure.RATE_LIMITED, "GitHub search rate limited")

    service, _ = _research(LimitedGithub(((),)))
    result = service.run(
        turn_id=uuid4(), interaction_id=uuid4(), work_id=None,
        user_id="human:test", text="查 GitHub 上有没有 async queue 实现",
        requests=(SearchRequest(intent=SearchIntent.SEARCH_GITHUB_REPOSITORIES,
                                query="async queue", reason="Human request",
                                origin="HUMAN_EXPLICIT"),),
    )
    assert result.metrics.failure_categories == (SearchFailure.RATE_LIMITED.value,)
    assert "RATE_LIMITED" in result.answer
    assert "不存在" in result.answer
    assert result.evidence == ()


def test_malformed_provider_results_are_reported_as_unavailable():
    class Transport:
        def get(self, url, *, headers=None):
            return b'{"items": null}' if "github.com" in url else b'{"web": {"results": null}}', "application/json"

    transport = Transport()
    for provider in (GitHubPublicSearchProvider(transport),
                     BraveWebSearchProvider(transport, api_key="test-secret")):
        with pytest.raises(SearchProviderError) as error:
            provider.search("async queue")
        assert error.value.category is SearchFailure.PROVIDER_UNAVAILABLE
