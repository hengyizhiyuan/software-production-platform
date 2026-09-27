"""A partial live qualification must not hide unrelated failures or fake Search."""
from benchmarks.golden.runtime.qualify_research import qualification_checks, qualification_status
from benchmarks.golden.runtime.summarize import qualification_status as normalized_status


def test_credential_block_does_not_hide_stream_or_other_provider_failures():
    checks = {'browser_stream_completed': True, 'real_web_retrieval': False,
        'inspected_web_source_cited': False}
    missing_web = [{'category': 'CREDENTIAL_REQUIRED', 'search_type': 'SEARCH_WEB'}]
    assert qualification_status(checks, missing_web) == ('BLOCKED_EXTERNAL', True)
    assert qualification_status({**checks, 'browser_stream_completed': False}, missing_web) == ('FAIL', False)
    assert qualification_status(checks, missing_web + [
        {'category': 'RATE_LIMITED', 'search_type': 'SEARCH_GITHUB_REPOSITORIES'}]) == ('FAIL', True)
    assert qualification_status(checks, []) == ('FAIL', True)


def test_direct_web_fetch_and_search_snippets_cannot_qualify_live_search():
    stream = 'event: response.final\n\nevent: message.completed\n'
    interaction = {'governed_work_id': None, 'conversation_messages': [
        {'actor': 'WATT', 'content': 'Observed page', 'supporting_references': ['web:1']}]}
    source = {'evidence_id': 'web:1', 'url': 'https://example.org', 'provider': 'public-web-fetch',
        'source_type': 'WEB', 'rank': 1, 'query': 'form validation', 'retrieved_at': '2026-09-27T00:00:00Z',
        'completeness': 'INSPECTED', 'inspected_content': 'Observed page'}
    packet = {'evidence': [source], 'metrics': {'sufficient': True}, 'failures': []}
    checks = qualification_checks('web-live', interaction, packet, stream)
    assert checks['inspected_web_source_cited']
    assert not checks['real_web_retrieval']
    assert qualification_status(checks, []) == ('FAIL', True)
    packet['evidence'] = [{**source, 'provider': 'brave-web-search',
        'completeness': 'SNIPPET', 'inspected_content': None}]
    checks = qualification_checks('web-live', interaction, packet, stream)
    assert checks['real_web_retrieval']
    assert not checks['inspected_web_source_cited']
    assert qualification_status(checks, [])[0] == 'FAIL'
    packet['evidence'] = [{**source, 'provider': 'brave-web-search'}]
    assert qualification_status(qualification_checks('web-live', interaction, packet, stream), []) == ('PASS', True)


def test_empty_projection_and_historical_block_normalization():
    checks = qualification_checks('GC-EX-12', {}, {'metrics': None}, '')
    assert qualification_status(checks, []) == ('FAIL', False)
    assert normalized_status('BLOCKED_EXTERNAL_CREDENTIAL') == 'BLOCKED_EXTERNAL'
    assert normalized_status('PASS') == 'PASS'
