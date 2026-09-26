"""Publish bounded Golden evidence without turning automation into Human Acceptance.

Raw runtime snapshots and databases are retained independently. This projection
only collects completed observer results, explicit failure classifications and
business oracles; an available Preview alone never supplies a business PASS.
"""
import argparse
import json
from pathlib import Path


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    corpus = read(Path(__file__).resolve().parents[1]/'tier0-v1.json')
    cases = []
    for case in corpus['cases']:
        trials = []
        for root in args.evidence_root:
            for directory in sorted((root/case['id']).glob('trial-*')):
                result = read(directory/'result.json')
                diagnosis = read(directory/'diagnostic-classification.json')
                oracles = [{'evidence_record': path.name, **read(path)}
                    for path in sorted(directory.glob('business-oracle*.json'), key=lambda path: path.stat().st_mtime_ns)]
                if result is None and diagnosis is None and not oracles:
                    continue
                state = read(directory/'latest.json', read(directory/'snapshot-latest.json', {}))
                journey = read(directory/'journey.json', {})
                refinements = state.get('refinement', {}).get('events', [])
                trials.append({'trial': int(directory.name.removeprefix('trial-')),
                    'evidence_directory': str(directory),
                    'runtime_activation': read(directory/'runtime-activation.json', {'status': 'NOT_CAPTURED_AT_SUBMISSION'}),
                    'observer_result': result, 'failure_classification': diagnosis,
                    'business_oracles': oracles,
                    'business_status': oracles[-1]['status'] if oracles else 'NOT_EVALUATED',
                    'work_id': state.get('work', {}).get('work_id'),
                    'interaction_id': journey.get('interaction_id'),
                    'refinements': [{key: event.get(key) for key in (
                        'id', 'affected_component', 'signal_kind', 'refinement_class',
                        'final_result', 'budget_decision', 'diagnostic_evidence',
                        'model_token_usage', 'extra_elapsed_seconds')} for event in refinements],
                    'execution_lineage': [{key: item.get(key) for key in (
                        'pwu_id', 'attempt_id', 'condition', 'resume_count')}
                        for item in state.get('queue', [])],
                    'plan_lineage': state.get('work', {}).get('production_plan_runtime'),
                    'economics': state.get('economics', {}),
                    'human_attention': state.get('attention', []),
                    'manual_rescue_actions': journey.get('manual_rescue_actions', []),
                    'human_acceptance': 'PENDING'})
        trials.sort(key=lambda trial: trial['trial'])
        passed = [trial for trial in trials if trial['business_status'] == 'PASS']
        cases.append({'id': case['id'], 'required_oracle': case['acceptance_oracle'],
            'trials': trials, 'successful_independent_trials': len(passed),
            'status': 'PASS' if passed else 'PENDING'})
    report = {'schema_version': 1, 'corpus_version': corpus['corpus_version'],
        'tier_0_gate': 'PENDING', 'core_repeat_stability': 'PENDING',
        'human_acceptance': 'PENDING', 'cases': cases,
        'note': 'Closure requires every mandatory oracle and qualified repeated semantic outcomes; no aggregate quality score is inferred.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'cases': len(cases), 'cases_with_passed_oracle': sum(case['status']=='PASS' for case in cases),
        'tier_0_gate': 'PENDING', 'human_acceptance': 'PENDING'}))


if __name__ == '__main__':
    main()
