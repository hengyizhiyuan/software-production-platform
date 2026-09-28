"""Record one allowed Human scope choice through the ordinary conversation API.

This qualification actor supplies a product choice, never implementation hints,
retry, Preview startup, Candidate acceptance or delivery authorization.
"""
import argparse
import json
from pathlib import Path

if __package__:
    from .journey import ProductClient
else:
    from journey import ProductClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--answer', required=True)
    args = parser.parse_args()
    directory = args.directory
    output = directory/'human-clarification.json'
    if output.exists():
        raise SystemExit('The allowed Human choice has already been recorded')
    journey_path = directory/'journey.json'
    try:
        journey = json.loads(journey_path.read_text(encoding='utf-8'))
    except UnicodeDecodeError:
        journey = json.loads(journey_path.read_text(encoding='gbk'))
    corpus = json.loads((Path(__file__).resolve().parents[1]/'tier0-v1.json').read_text(encoding='utf-8'))
    case = next(item for item in corpus['cases'] if item['id'] == journey['case'])
    if 'answer one genuine high-impact clarification' not in case['allowed_human_actions']:
        raise SystemExit('This case does not allow a clarification choice')
    env = dict(line.split('=', 1) for line in args.env_file.read_text(encoding='utf-8').splitlines() if '=' in line)
    client = ProductClient(args.base, env['SPG_OPERATOR_TOKEN'])
    interaction = client.request('/api/interactions/'+journey['interaction_id'])
    work_id = interaction.get('governed_work_id')
    attention = client.request('/api/attention?work_id='+work_id) if work_id else []
    questions = [item for item in attention
        if item.get('steering_reason') == 'MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION']
    if len(questions) != 1:
        raise SystemExit('Requires exactly one observed governed scope question')
    evidence = {'case': journey['case'], 'trial': journey['trial'],
        'question': questions[0], 'answer': args.answer,
        'classification': 'LEGITIMATE_PRODUCT_SCOPE_CHOICE', 'question_count': 1,
        'implementation_assistance': False, 'human_acceptance': 'PENDING'}
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    receipt = client.request('/api/interactions/'+journey['interaction_id']+'/turns', {
        'content': args.answer, 'human_identity': 'human:golden-operator'})
    (directory/'clarification-submission.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'case': journey['case'], 'classification': evidence['classification'],
        'receipt': receipt}, ensure_ascii=False))


if __name__ == '__main__':
    main()
