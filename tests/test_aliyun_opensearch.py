"""Provider contract and selected capability without a live credential."""

import io
import json
from urllib.error import HTTPError

import pytest

from spg.application.connector_manifest import built_in_executable_capabilities
from spg.config import Settings
from spg.domain.external_search import SearchFailure, SearchProviderError
from spg.providers.external_search import (
    AliyunOpenSearchWebProvider, BoundedPublicHttp, inspect_web_resource,
)


class FakeTransport:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def post_json(self, url, payload, *, bearer):
        self.calls.append((url, payload, bearer))
        return json.dumps(self.payload, ensure_ascii=False).encode()

    def get(self, url, *, headers=None):
        return b"<main><h1>Observed page</h1><p>Fetched content is independent.</p></main>", "text/html"


def _payload(results=None):
    return {"request_id": "request-123", "usage": {"ops-web-search-001/pro": 1},
        "result": {"search_result": [
            {"title": "Python asyncio guide", "link": "https://docs.python.org/3/library/asyncio.html",
             "snippet": "Search summary only", "content": "Search summary only",
             "meta_info": {"publishedTime": "2026-09-01T08:00:00Z"}}
        ] if results is None else results}}


def test_request_contract_and_provider_neutral_snippet_then_fetch():
    transport = FakeTransport(_payload())
    provider = AliyunOpenSearchWebProvider(transport, api_key="fake-unit-key",
        endpoint="http://example.opensearch.aliyuncs.com", workspace="default")
    hit = provider.search("Python asyncio 中文教程", limit=99)[0]
    url, body, bearer = transport.calls[0]
    assert url == ("https://example.opensearch.aliyuncs.com/v3/openapi/"
        "workspaces/default/web-search/ops-web-search-001")
    assert body == {"query": "Python asyncio 中文教程", "query_rewrite": True,
        "top_k": 8, "content_type": "snippet", "way": "pro"}
    assert bearer == "fake-unit-key"
    assert hit.provider == "aliyun-opensearch"
    assert hit.query == "Python asyncio 中文教程"
    assert hit.url == "https://docs.python.org/3/library/asyncio.html"
    assert hit.snippet == "Search summary only"
    assert hit.inspected_content is None and hit.completeness == "SEARCH_RESULT"
    assert hit.metadata["provider_request_id"] == "request-123"
    assert hit.metadata["published_at"] == "2026-09-01T08:00:00Z"
    assert hit.metadata["usage:ops-web-search-001/pro"] == 1
    inspected = inspect_web_resource(transport, hit)
    assert inspected.completeness == "INSPECTED"
    assert inspected.inspected_content != hit.snippet
    assert inspected.evidence_id == hit.evidence_id
    assert inspected.metadata["provider_request_id"] == "request-123"


def test_empty_results_and_invalid_payload_are_distinct():
    empty = AliyunOpenSearchWebProvider(FakeTransport(_payload([])),
        api_key="fake", endpoint="https://example.opensearch.aliyuncs.com")
    assert empty.search("bounded query") == ()
    broken = AliyunOpenSearchWebProvider(FakeTransport({"result": {"wrong": []}}),
        api_key="fake", endpoint="https://example.opensearch.aliyuncs.com")
    with pytest.raises(SearchProviderError) as caught:
        broken.search("bounded query")
    assert caught.value.category is SearchFailure.PROVIDER_PROTOCOL_ERROR


def test_insecure_provider_hit_is_skipped_without_losing_secure_results():
    items = [
        {"title": "Insecure hit", "link": "http://example.org/page", "snippet": "Unsafe source"},
        {"title": "Secure hit", "link": "https://example.org/page", "snippet": "Usable source"},
    ]
    provider = AliyunOpenSearchWebProvider(FakeTransport(_payload(items)),
        api_key="fake", endpoint="https://example.opensearch.aliyuncs.com",
        workspace="watt", service_id="ops-web-search-001")
    results = provider.search("bounded query")
    assert len(results) == 1
    assert results[0].rank == 2
    assert results[0].url == "https://example.org/page"
    assert results[0].metadata["provider_skipped_non_https"] == 1

    only_insecure = AliyunOpenSearchWebProvider(FakeTransport(_payload(items[:1])),
        api_key="fake", endpoint="https://example.opensearch.aliyuncs.com")
    with pytest.raises(SearchProviderError) as caught:
        only_insecure.search("bounded query")
    assert caught.value.category is SearchFailure.PROVIDER_PROTOCOL_ERROR


@pytest.mark.parametrize("status,category", [
    (401, SearchFailure.AUTHENTICATION_FAILED), (403, SearchFailure.AUTHENTICATION_FAILED),
    (429, SearchFailure.RATE_LIMITED), (503, SearchFailure.PROVIDER_UNAVAILABLE),
])
def test_http_failure_mapping_redacts_credential(monkeypatch, status, category):
    monkeypatch.setattr(BoundedPublicHttp, "_check_url", staticmethod(lambda _url: None))
    class RejectingOpener:
        def open(self, request, timeout):
            assert request.get_header("Authorization") == "Bearer fake-unit-key"
            raise HTTPError(request.full_url, status, "ignored", {}, io.BytesIO())
    http = BoundedPublicHttp()
    http.opener = RejectingOpener()
    provider = AliyunOpenSearchWebProvider(http, api_key="fake-unit-key",
        endpoint="https://example.opensearch.aliyuncs.com")
    with pytest.raises(SearchProviderError) as caught:
        provider.search("bounded query")
    assert caught.value.category is category
    assert "fake-unit-key" not in str(caught.value)


def test_selected_capability_and_missing_credential_have_no_brave_fallback(monkeypatch):
    monkeypatch.setenv("SPG_WEB_SEARCH_PROVIDER", "aliyun-opensearch")
    monkeypatch.setenv("SPG_WEB_SEARCH_API_KEY", "brave-only-key")
    monkeypatch.setenv("SPG_ALIYUN_OPENSEARCH_ENDPOINT",
        "https://example.opensearch.aliyuncs.com")
    monkeypatch.delenv("SPG_ALIYUN_OPENSEARCH_API_KEY", raising=False)
    selected = {item.capability_id: item for item in built_in_executable_capabilities()}["web.search"]
    assert selected.execution_provider == "aliyun-opensearch"
    assert selected.credential_requirements == ("aliyun.opensearch",)
    with pytest.raises(SearchProviderError) as caught:
        AliyunOpenSearchWebProvider(FakeTransport(_payload()), api_key=None,
            endpoint="https://example.opensearch.aliyuncs.com").search("bounded query")
    assert caught.value.category is SearchFailure.CREDENTIAL_REQUIRED
    monkeypatch.setenv("SPG_ALIYUN_OPENSEARCH_API_KEY", "fake-unit-key")
    selected = {item.capability_id: item for item in built_in_executable_capabilities()}["web.search"]
    assert selected.execution_provider == "aliyun-opensearch"
    assert selected.credential_requirements == ()
    assert Settings(_env_file=None).web_search_provider == "aliyun-opensearch"
