"""Exercise exact Candidate acceptance independently from Delivery authority.

This is a declared automated governance actor, not Human Acceptance. It never
requests delivery or writes the fixture remote. All remote inspection is read-only.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

if __package__:
    from .journey import ProductClient
else:
    from journey import ProductClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--fixture-repository', type=Path, required=True)
    args = parser.parse_args()
    output = args.directory/'review-authority-oracle.json'
    submission = args.directory/'review-authority-submission.json'
    if output.exists() or submission.exists():
        raise SystemExit('Existing review evidence is immutable')
    journey = json.loads((args.directory/'journey.json').read_text(encoding='utf-8'))
    corpus = json.loads((Path(__file__).resolve().parents[1]/'tier0-v1.json').read_text(encoding='utf-8'))
    case = next(item for item in corpus['cases'] if item['id'] == journey['case'])
    if ('review exact Candidate' not in case['allowed_human_actions']
            or 'acceptance alone does not push' not in case['acceptance_oracle']):
        raise SystemExit('The case does not qualify this governance transition')
    if args.fixture_repository.name != case['fixture']+'.git':
        raise SystemExit('Remote inspection must name the declared fixture')
    env = dict(line.split('=', 1) for line in args.env_file.read_text(encoding='utf-8').splitlines() if '=' in line)
    client = ProductClient(args.base, env['SPG_OPERATOR_TOKEN'])
    state = json.loads((args.directory/'latest.json').read_text(encoding='utf-8'))
    work_id = state['work']['work_id']
    prefix = '/api/works/'+work_id
    preview = client.request(prefix+'/functional-preview')
    if preview['status'] != 'READY':
        raise SystemExit('Review requires the actual ready Candidate Preview')
    attention = [item for item in client.request('/api/attention?work_id='+work_id)
        if item['kind'] == 'CANDIDATE_AUTHORIZATION']
    if len(attention) != 1:
        raise SystemExit('Requires one exact sealed Candidate authorization')
    def refs():
        return subprocess.check_output(['git','-C',str(args.fixture_repository),
            'for-each-ref','--format=%(refname) %(objectname)'], text=True).splitlines()
    before = refs()
    receipt = client.request('/api/attention/'+attention[0]['attention_id']+'/resolve', {
        'action':'AUTHORIZE', 'authority_identity':'human:golden-governance-actor',
        'rationale':'Automated exact Candidate acceptance boundary qualification; no Delivery Authorization.'})
    submission.write_text(json.dumps({'attention':attention[0], 'receipt':receipt,
        'remote_refs_before':before, 'actor':'AUTOMATED_GOVERNANCE_QUALIFICATION',
        'human_acceptance':'PENDING'}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    started = time.monotonic()
    while time.monotonic()-started < 90:
        work = client.request(prefix)
        delivery = client.request(prefix+'/delivery')
        if work.get('latest_trusted_runtime_commit_id') or work.get('status') in {'BLOCKED','FAILED'}:
            break
        time.sleep(1)
    after = refs()
    record = {'candidate_id':preview['session']['candidate_id'],
        'candidate_revision':preview['session']['repository_revision'],
        'candidate_accepted':not receipt.get('error_status'),
        'local_runtime_commit_observed':bool(work.get('latest_trusted_runtime_commit_id')),
        'remote_refs_before':before, 'remote_refs_after':after,
        'remote_unchanged':before == after, 'delivery_records':delivery.get('deliveries',[]),
        'no_delivery_authorization':not delivery.get('deliveries'),
        'work_after_review':work,
        'actor':'AUTOMATED_GOVERNANCE_QUALIFICATION', 'human_acceptance':'PENDING',
        'manual_implementation_assistance':False}
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key:record[key] for key in ('candidate_accepted',
        'local_runtime_commit_observed','remote_unchanged','no_delivery_authorization','human_acceptance')}))


if __name__ == '__main__':
    main()
