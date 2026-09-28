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
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            return {'error_status': error.code, 'detail': error.read().decode()}


def stopped_owner_without_pending_effect(state):
    """A READY Work can have a terminally stopped Steering owner."""
    turns = state.get('interaction', {}).get('turns', [])
    steering = state.get('steering') or {}
    return (bool(turns) and turns[-1].get('status') in {'COMPLETED', 'FAILED'}
        and steering.get('automatic_progression_state') == 'STOPPED'
        and steering.get('last_stop_reason') == 'BLOCKED'
        and not state.get('queue'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    parser.add_argument('--trial', type=int, required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--fixture-base', default='http://qualified-git:8080')
    parser.add_argument('--interaction-id', help='Observe an already submitted /app journey')
    parser.add_argument('--observation-phase', choices=('initial', 'after-clarification', 'after-reassessment'), default='initial')
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    env = dict(line.split('=', 1) for line in args.env_file.read_text(encoding='utf-8').splitlines() if '=' in line)
    client = ProductClient(args.base, env['SPG_OPERATOR_TOKEN'])
    corpus = json.loads((ROOT/'benchmarks/golden/tier0-v1.json').read_text(encoding='utf-8'))
    case = next(item for item in corpus['cases'] if item['id'] == args.case)
    directory = args.evidence_root/args.case/f'trial-{args.trial}'
    directory.mkdir(parents=True, exist_ok=True)
    result_path = directory/('result.json' if args.observation_phase == 'initial'
        else f'result-{args.observation_phase}.json')
    if result_path.exists():
        raise SystemExit('Existing attempt result is immutable; choose a new trial identity')
    runtime_record = directory/'runtime-activation.json'
    if not runtime_record.exists():
        runtime_record.write_text(json.dumps(client.request('/api/runtime-activation'),
            ensure_ascii=False, indent=2), encoding='utf-8')
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
        (directory/'submission.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    journey_path = directory/'journey.json'
    if journey_path.exists():
        try:
            previous_journey = json.loads(journey_path.read_text(encoding='utf-8'))
        except UnicodeDecodeError:
            previous_journey = json.loads(journey_path.read_text(encoding='gbk'))
        if previous_journey['interaction_id'] != interaction_id:
            raise SystemExit('Existing trial belongs to a different interaction')
    else:
        journey_path.write_text(json.dumps({'case': case['id'],
        'corpus_version': corpus['corpus_version'], 'trial': args.trial,
        'interaction_id': interaction_id, 'human_input': intent,
        'tester_implementation': False, 'manual_rescue_actions': [],
        'human_acceptance': 'PENDING'}, ensure_ascii=False, indent=2), encoding='utf-8')
    started = time.monotonic()
    previous = None
    work_id = None
    result = {'case': args.case, 'trial': args.trial, 'status': 'TIMEOUT'}
    while time.monotonic()-started < args.timeout:
        interaction = client.request('/api/interactions/'+interaction_id)
        work_id = interaction.get('governed_work_id')
        for turn in interaction.get('turns', []):
            if turn.get('assessment_id'):
                realization = client.request('/api/interactions/'+interaction_id+'/turns/'+turn['turn_id']+'/realization')
                (directory/('realization-'+turn['turn_id']+'.json')).write_text(json.dumps(realization,ensure_ascii=False,indent=2), encoding='utf-8')
        state = {'interaction': interaction, 'observed_at': datetime.now(UTC).isoformat()}
        turns = interaction.get('turns', [])
        if not work_id and turns and turns[-1].get('status') == 'COMPLETED':
            projection = client.request('/api/interactions/'+interaction_id+'/turns/'+turns[-1]['turn_id']+'/realization')
            ir = projection.get('semantic_ir') or {}
            if any(item.get('production', {}).get('current') for item in ir.get('items', []) if item.get('production')):
                result.update(status='CURRENT_PRODUCTION_NOT_ADMITTED', interaction_id=interaction_id,
                    obligations=projection.get('obligations', []), business_oracle='NOT_EVALUATED')
                (directory/'latest.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
                break
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
        (directory/'latest.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        if status != previous:
            stamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')
            (directory/(stamp+'.json')).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({'case': args.case, 'trial': args.trial, 'work': work_id,
                'status': status, 'elapsed_seconds': int(time.monotonic()-started)}, ensure_ascii=False), flush=True)
            previous = status
        if status == 'PREVIEW_READY':
            result['status'] = 'REVIEW_READY_AWAITING_BUSINESS_ORACLE'
            break
        if (not work_id and status == 'COMPLETED'
                and case['expected_governed_journey'][-1] == 'advisory response'):
            result['status'] = 'ADVISORY_COMPLETE_AWAITING_SOURCE_ORACLE'
            break
        if not work_id and status == 'COMPLETED':
            obligations = projection.get('obligations', [])
            if all(item.get('state') in {'SATISFIED', 'BLOCKED_WITH_EVIDENCE',
                    'REQUIRES_HUMAN', 'SUPERSEDED'} for item in obligations):
                result.update(status='NO_PRODUCTION_RESULT_AFTER_TERMINAL_TURN',
                    obligation_states=[item['state'] for item in obligations])
                break
        if stopped_owner_without_pending_effect(state):
            result['status'] = 'OWNER_CONVERGENCE_STOPPED_WITHOUT_RESULT'
            break
        pending_turn = (interaction.get('turns') or [{}])[-1].get('status') in {'RECEIVED', 'PROCESSING'}
        if not pending_turn and (state.get('attention') or status in {'BLOCKED', 'FAILED'}):
            result['status'] = 'ATTENTION_OR_FAILURE_REQUIRES_CLASSIFICATION'
            break
        if (not work_id and status == 'COMPLETED'
                and interaction.get('unresolved_material_questions')
                and time.monotonic()-started > 60):
            result['status'] = 'CLARIFICATION_REQUIRES_CLASSIFICATION'
            break
        if (interaction.get('repository_acquisition_state') in {'FAILED_RETRYABLE', 'FAILED_TERMINAL'}
                and time.monotonic()-started > 120 and not state.get('queue') and not pending_turn):
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
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
