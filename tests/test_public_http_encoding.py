"""Permanent regression for the Pilot's gzip bytes -> JSONB NUL incident."""
from datetime import UTC, datetime
import gzip
import io
from types import SimpleNamespace
import zlib
import pytest
from spg.domain.external_search import SearchEvidence, SearchFailure, SearchProviderError
from spg.providers.external_search import BoundedPublicHttp, inspect_web_resource


def transport(monkeypatch, body, encoding, *, limit=250000, content_type='text/html'):
    monkeypatch.setattr(BoundedPublicHttp, '_check_url', staticmethod(lambda _: None))
    http = BoundedPublicHttp(max_bytes=limit)
    class Response(io.BytesIO):
        headers = {'Content-Type': content_type, 'Content-Encoding': encoding}
    http.opener = SimpleNamespace(open=lambda *a, **k: Response(body))
    return http


def evidence():
    return SearchEvidence(evidence_id='external-search:gzip-incident', source_type='WEB',
        provider='reviewed-regression', query='official reference', title='Official page',
        url='https://example.org/release', retrieved_at=datetime.now(UTC), rank=1,
        completeness='SEARCH_RESULT', snippet='Search snippet; not fetched content', metadata={'provider_request_id':'exact-request'})


@pytest.mark.parametrize('encoding,compress', [('identity',lambda x:x),('gzip',gzip.compress),('deflate',zlib.compress)])
def test_decoded_text_preserves_fetch_provenance(monkeypatch,encoding,compress):
    http=transport(monkeypatch,compress(b'<main>Official release 3.14.0</main>'),encoding)
    hit=evidence();result=inspect_web_resource(http,hit)
    assert result.inspected_content=='Official release 3.14.0'
    assert result.completeness=='INSPECTED' and result.evidence_id==hit.evidence_id
    assert result.metadata['provider_request_id']=='exact-request'
    assert result.snippet==hit.snippet and '\x00' not in result.inspected_content


@pytest.mark.parametrize('encoding,compress', [('gzip',gzip.compress),('deflate',zlib.compress)])
@pytest.mark.parametrize('method', ['get','post_json'])
def test_expansion_is_bounded_before_json_or_text(monkeypatch,encoding,compress,method):
    http=transport(monkeypatch,compress(b'x'*1000000),encoding,limit=4096)
    with pytest.raises(SearchProviderError) as caught:
        if method=='get': http.get('https://example.org')
        else: http.post_json('https://example.org',{},bearer='test-only')
    assert caught.value.category==(SearchFailure.FETCH_FAILED if method=='get' else SearchFailure.PROVIDER_PROTOCOL_ERROR)
    assert 'bounded fetch size' in str(caught.value)


@pytest.mark.parametrize('body,encoding', [(gzip.compress(b'hello')[:-4],'gzip'),(b'not gzip','gzip'),
    (zlib.compress(b'hello')[:-2],'deflate'),(b'hello','br'),(b'hello','gzip, br'),
    (zlib.compress(b'hello')+b'trailing','deflate')])
def test_malformed_or_unsupported_encoding_fails_closed(monkeypatch,body,encoding):
    with pytest.raises(SearchProviderError) as caught:
        transport(monkeypatch,body,encoding).get('https://example.org')
    assert caught.value.category is SearchFailure.FETCH_FAILED


@pytest.mark.parametrize('body',[b'<main>binary\x00content</main>',b'<main>binary&#0;content</main>'])
def test_binary_nul_never_enters_inspected_evidence(monkeypatch,body):
    if b'\x00' not in body:
        # HTMLParser normalizes an invalid numeric reference to replacement text.
        result=inspect_web_resource(transport(monkeypatch,body,'identity'),evidence())
        assert '\x00' not in result.inspected_content
    else:
        with pytest.raises(SearchProviderError) as caught:
            inspect_web_resource(transport(monkeypatch,body,'identity'),evidence())
        assert caught.value.category is SearchFailure.FETCH_FAILED


def test_provider_post_json_decodes_without_leaking_bearer(monkeypatch):
    http=transport(monkeypatch,gzip.compress(b'{"result":[]}'),'gzip',content_type='application/json')
    assert http.post_json('https://example.org',{},bearer='test-only')==b'{"result":[]}'
