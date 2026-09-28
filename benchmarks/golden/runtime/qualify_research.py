"""Independent real-provider qualification; missing Web credentials never halt a batch.

Run web-live or GC-EX-12 with a new trial identity. --allow-partial exercises the
available GitHub/project/SSE surfaces while leaving real Web BLOCKED_EXTERNAL.
No fixture provider, Work admission, production edit or delivery is supplied.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
from hashlib import sha256
from http.client import IncompleteRead
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

if __package__:
    from .journey import ProductClient, ROOT
else:
    from journey import ProductClient, ROOT


def qualification_checks(scope, interaction, evidence, stream):
    sources = evidence.get('evidence', [])
    messages = interaction.get('conversation_messages', [])
    answer = next((item for item in reversed(messages) if item.get('actor') == 'WATT'), {})
    content = answer.get('content', '')
    cited = set(answer.get('supporting_references', []))
    inspected = [item for item in sources if item.get('completeness') == 'INSPECTED'
        and item.get('inspected_content')]
    checks = {
        'source_provenance': bool(sources) and all(all(item.get(key) for key in
            ('evidence_id', 'url', 'provider', 'source_type', 'query', 'retrieved_at'))
            and isinstance(item.get('rank'), int) and item['rank'] >= 1
            for item in sources),
        'inspected_source_cited': any(item.get('evidence_id') in cited for item in inspected),
        'search_sufficient': (evidence.get('metrics') or {}).get('sufficient') is True,
        'browser_stream_completed': 'event: response.final\n' in stream
            and 'event: message.completed\n' in stream and 'event: turn.failed\n' not in stream,
        'no_unrequested_production': interaction.get('governed_work_id') is None,
        'real_web_retrieval': any(item.get('source_type') == 'WEB'
            and item.get('provider') == 'brave-web-search' for item in sources),
        'inspected_web_source_cited': any(item.get('source_type') == 'WEB'
            and item.get('evidence_id') in cited for item in inspected),
    }
    if scope == 'GC-EX-12':
        project = evidence.get('project_observation') or {}
        materials = project.get('materials', [])
        checks.update(
            real_github_retrieval=any(item.get('source_type') == 'GITHUB'
                and item.get('provider') == 'github-rest-public' for item in inspected),
            exact_project_observation=project.get('condition') == 'READY'
                and bool(project.get('revision') and project.get('tree') and materials)
                and all(item.get('path') and item.get('content_sha256') for item in materials),
            grounded_project_recommendation='项目建议：' in content
                and bool(content.split('项目建议：', 1)[-1].split('\n', 1)[0].strip())
                and any(item.get('path', '') in content for item in materials),
            project_packet_kept_off_human_stream='PROJECT_RESEARCH_EVIDENCE' not in stream,
        )
    return checks


def qualification_status(checks, failures):
    web_checks = {'real_web_retrieval', 'inspected_web_source_cited'}
    code_owned = all(value for key, value in checks.items() if key not in web_checks)
    web_blocked = bool(failures) and all(item.get('category') == 'CREDENTIAL_REQUIRED'
        and item.get('search_type') == 'SEARCH_WEB' for item in failures)
    return ('PASS' if all(checks.values()) and not failures else
        'BLOCKED_EXTERNAL' if code_owned and web_blocked else 'FAIL'), code_owned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', choices=('web-live', 'GC-EX-12'), required=True)
    parser.add_argument('--trial', type=int, required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--fixture-base', default='http://qualified-git:8080')
    parser.add_argument('--allow-partial', action='store_true')
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    if args.trial < 1 or args.timeout < 1:
        parser.error('trial and timeout must be positive')
    directory = args.evidence_root / args.scope / f'trial-{args.trial}'
    if directory.exists():
        raise SystemExit('Trial identity already exists; preserve it and choose a new trial')
    directory.mkdir(parents=True)
    env = dict(line.split('=', 1) for line in args.env_file.read_text(encoding='utf-8').splitlines() if '=' in line)

    def save(name, value):
        (directory / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    if not env.get('SPG_WEB_SEARCH_API_KEY', '').strip() and not args.allow_partial:
        receipt = {'scope': args.scope, 'trial': args.trial, 'status': 'BLOCKED_EXTERNAL',
            'external_dependency': 'SPG_WEB_SEARCH_API_KEY', 'retrieval_attempted': False,
            'recorded_at': datetime.now(UTC).isoformat(), 'human_acceptance': 'PENDING'}
        save('qualification.json', receipt)
        print(json.dumps(receipt))
        return
    client = ProductClient(args.base, env['SPG_OPERATOR_TOKEN'])
    activation = client.request('/api/runtime-activation')
    save('runtime-activation.json', activation)
    corpus = json.loads((ROOT / 'benchmarks/golden/tier0-v1.json').read_text(encoding='utf-8'))
    case = next(item for item in corpus['cases'] if item['id'] == 'GC-EX-12')
    intent = (f"这是当前项目仓库：{args.fixture_base}/{case['fixture']}.git\n" + case['human_request']
        if args.scope == 'GC-EX-12' else '搜索 Web 中成熟的表单验证实现，检查实际页面，比较并给出真实来源。')
    interaction = client.request('/api/interactions', {'human_identity': 'human:golden-operator'})
    interaction_id = interaction['interaction_id']
    turn = client.request(f'/api/interactions/{interaction_id}/turns',
        {'content': intent, 'human_identity': 'human:golden-operator'})
    turn_id = turn['turn_id']
    save('submission.json', turn)
    save('journey.json', {'case': args.scope, 'corpus_version': corpus['corpus_version'],
        'trial': args.trial, 'interaction_id': interaction_id, 'turn_id': turn_id,
        'human_input': intent, 'tester_implementation': False, 'manual_rescue_actions': [],
        'human_acceptance': 'PENDING'})
    started = time.monotonic()
    while time.monotonic() - started < args.timeout:
        interaction = client.request(f'/api/interactions/{interaction_id}')
        save('latest.json', {'interaction': interaction, 'observed_at': datetime.now(UTC).isoformat()})
        current = next(item for item in interaction['turns'] if item['turn_id'] == turn_id)
        if current['status'] in {'COMPLETED', 'FAILED'}:
            break
        time.sleep(2)
    evidence = client.request(f'/api/interactions/{interaction_id}/turns/{turn_id}/external-evidence')
    save('external-evidence.json', evidence)
    stream = ''
    stream_failure = None
    if current['status'] in {'COMPLETED', 'FAILED'}:
        request = urllib.request.Request(
            f'{args.base.rstrip("/")}/api/interactions/{interaction_id}/turns/{turn_id}/events',
            headers={'Authorization': 'Bearer ' + env['SPG_OPERATOR_TOKEN']})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                stream = response.read().decode()
        except IncompleteRead as error:
            stream = error.partial.decode(errors='replace')
            stream_failure = type(error).__name__
        except (OSError, urllib.error.URLError) as error:
            stream_failure = type(error).__name__
    (directory / 'response-stream.txt').write_text(stream)
    save('response-stream.json', {'raw_stream_record': 'response-stream.txt',
        'sha256': sha256(stream.encode()).hexdigest(),
        'event_names': [line.removeprefix('event: ') for line in stream.splitlines()
            if line.startswith('event: ')],
        'source_head': activation.get('active_application_revision'),
        'transport_failure': stream_failure})
    checks = qualification_checks(args.scope, interaction, evidence, stream)
    if stream_failure:
        checks['browser_stream_completed'] = False
    status, code_owned = qualification_status(checks, evidence.get('failures', []))
    if current['status'] != 'COMPLETED' or stream_failure:
        status = 'FAIL'
    receipt = {'case': args.scope, 'trial': args.trial, 'status': status, 'checks': checks,
        'qualified_code_owned_surface': 'PASS' if code_owned else 'FAIL',
        'external_dependency': 'SPG_WEB_SEARCH_API_KEY' if status == 'BLOCKED_EXTERNAL' else None,
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'observed_metrics': evidence.get('metrics'), 'manual_rescue_actions': [],
        'human_acceptance': 'PENDING', 'recorded_at': datetime.now(UTC).isoformat()}
    save('qualification.json', receipt)
    save('business-oracle.json', receipt)
    save('result.json', {'case': args.scope, 'trial': args.trial,
        'status': 'ADVISORY_COMPLETE_AWAITING_SOURCE_ORACLE' if current['status'] == 'COMPLETED' else current['status'],
        'elapsed_seconds': receipt['elapsed_seconds'], 'human_acceptance': 'PENDING'})
    print(json.dumps(receipt, ensure_ascii=False))
    if status == 'FAIL':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
