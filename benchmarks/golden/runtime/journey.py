"""One natural-language product journey; never supplies implementation or rescue.

The fixture URL names starting repository authority, not a file hint. This runner
uses the same public Interaction turn API as /app. GUI behavior is independently
checked in Browser. It never admits Work manually, starts Preview, creates a Work
branch, retries acquisition, writes target files or authorizes delivery.
"""
from __future__ import annotations
import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[3]


class ProductClient:
    def __init__(self, base: str, token: str):
        self.base, self.token = base.rstrip('/'), token

    def request(self, path: str, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(self.base + path, data=data, headers={
            'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            return {'error_status': error.code, 'detail': error.read().decode()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    parser.add_argument('--trial', type=int, required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--fixture-base', default='http://qualified-git:8080')
    parser.add_argument('--interaction-id', help='Observe an already submitted /app journey')
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    env = dict(line.split('=', 1) for line in args.env_file.read_text().splitlines() if '=' in line)
    client = ProductClient(args.base, env['SPG_OPERATOR_TOKEN'])
    corpus = json.loads((ROOT/'benchmarks/golden/tier0-v1.json').read_text())
    case = next(item for item in corpus['cases'] if item['id'] == args.case)
    directory = args.evidence_root/args.case/f'trial-{args.trial}'
    directory.mkdir(parents=True, exist_ok=True)
    if (directory/'result.json').exists():
        raise SystemExit('Existing attempt result is immutable; choose a new trial identity')
    runtime_record = directory/'runtime-activation.json'
    if not runtime_record.exists():
        runtime_record.write_text(json.dumps(client.request('/api/runtime-activation'),
            ensure_ascii=False, indent=2))
    intent = case['human_request']
    if case['fixture'] != 'public-watt-main':
        intent = f"这是当前项目仓库：{args.fixture_base}/{case['fixture']}.git\n" + intent
    if args.interaction_id:
        interaction_id = args.interaction_id
    else:
        interaction = client.request('/api/interactions', {'human_identity': 'human:golden-operator'})
        interaction_id = interaction['interaction_id']
        receipt = client.request('/api/interactions/'+interaction_id+'/turns', {
            'content': intent, 'human_identity': 'human:golden-operator'})
        (directory/'submission.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    (directory/'journey.json').write_text(json.dumps({'case': case['id'],
        'corpus_version': corpus['corpus_version'], 'trial': args.trial,
        'interaction_id': interaction_id, 'human_input': intent,
        'tester_implementation': False, 'manual_rescue_actions': [],
        'human_acceptance': 'PENDING'}, ensure_ascii=False, indent=2))
    started = time.monotonic()
    previous = None
    work_id = None
    result = {'case': args.case, 'trial': args.trial, 'status': 'TIMEOUT'}
    while time.monotonic()-started < args.timeout:
        interaction = client.request('/api/interactions/'+interaction_id)
        work_id = interaction.get('governed_work_id')
        state = {'interaction': interaction, 'observed_at': datetime.now(UTC).isoformat()}
        if work_id:
            prefix = '/api/works/'+work_id
            state.update(work=client.request(prefix), steering=client.request(prefix+'/steering'),
                refinement=client.request(prefix+'/self-refine'), queue=client.request(
                    '/api/native-execution/queue?work_id='+work_id),
                preview=client.request(prefix+'/functional-preview'),
                attention=client.request('/api/attention?work_id='+work_id),
                economics=client.request(prefix+'/economics'), delivery=client.request(prefix+'/delivery'))
        status = ('PREVIEW_READY' if state.get('preview',{}).get('status') == 'READY' else
            state.get('work',{}).get('status') or
            (interaction.get('turns') or [{}])[-1].get('status', 'UNDERSTANDING'))
        (directory/'latest.json').write_text(json.dumps(state, ensure_ascii=False, indent=2))
        if status != previous:
            stamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')
            (directory/(stamp+'.json')).write_text(json.dumps(state, ensure_ascii=False, indent=2))
            print(json.dumps({'case': args.case, 'trial': args.trial, 'work': work_id,
                'status': status, 'elapsed_seconds': int(time.monotonic()-started)}, ensure_ascii=False), flush=True)
            previous = status
        if status == 'PREVIEW_READY':
            result['status'] = 'REVIEW_READY_AWAITING_BUSINESS_ORACLE'
            break
        if state.get('attention') or status in {'BLOCKED', 'FAILED'}:
            result['status'] = 'ATTENTION_OR_FAILURE_REQUIRES_CLASSIFICATION'
            break
        if (not work_id and status == 'COMPLETED'
                and interaction.get('unresolved_material_questions')
                and time.monotonic()-started > 60):
            result['status'] = 'CLARIFICATION_REQUIRES_CLASSIFICATION'
            break
        if (interaction.get('repository_acquisition_state') in {'FAILED_RETRYABLE', 'FAILED_TERMINAL'}
                and time.monotonic()-started > 120 and not state.get('queue')):
            result['status'] = 'UNRECOVERED_ACQUISITION'
            break
        if (not work_id and status == 'COMPLETED'
                and time.monotonic()-started > 60
                and interaction.get('readiness', {}).get('status') == 'READY'
                and args.case != 'GC-EX-12'):
            result['status'] = 'EXPLICIT_PRODUCTION_REQUEST_NOT_ADMITTED'
            break
        time.sleep(4)
    result.update(work_id=work_id, elapsed_seconds=int(time.monotonic()-started),
        human_acceptance='PENDING', automatic_delivery_authorization=False,
        business_oracle='NOT_YET_EVALUATED')
    (directory/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
