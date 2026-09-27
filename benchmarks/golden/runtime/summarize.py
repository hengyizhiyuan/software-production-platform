"""Publish bounded Golden evidence without turning automation into Human Acceptance.

Raw runtime snapshots and databases are retained independently. This projection
only collects completed observer results, explicit failure classifications and
business oracles; an available Preview alone never supplies a business PASS.
"""
import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def qualification_status(value):
    # Normalize current projections while preserving verbatim historical oracles.
    return 'BLOCKED_EXTERNAL' if value in {
        'BLOCKED_EXTERNAL_CREDENTIAL', 'BLOCKED_EXTERNAL_SECRET',
        'PARTIAL_EXTERNAL_SECRET', 'BLOCKED_EXTERNAL'} else value


def observer_receipt(path):
    value = read(path)
    if path.name == 'external-evidence.json':
        # Keep the immutable original locally; publish provenance and exact
        # inspected-text identities without duplicating upstream README bodies.
        value['raw_evidence_receipt'] = {
            'path': str(path), 'sha256': sha256(path.read_bytes()).hexdigest()}
        for source in value.get('evidence', []):
            content = source.pop('inspected_content', None)
            if content is not None:
                source['inspected_excerpt_sha256'] = sha256(content.encode()).hexdigest()
                source['inspected_excerpt_characters'] = len(content)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    corpus = read(Path(__file__).resolve().parents[1]/'tier0-v1.json')
    findings_path = Path(__file__).resolve().parents[3]/'docs/evidence/stability/golden-boundary-findings-20260927.json'
    findings = read(findings_path, {}).get('findings', [])
    findings_by_trial = {(row.get('case'), row.get('trial')): row for row in findings}
    cases = []
    for case in corpus['cases']:
        trials = []
        for root in args.evidence_root:
            for directory in sorted((root/case['id']).glob('trial-*')):
                result = read(directory/'result.json')
                diagnosis = read(directory/'diagnostic-classification.json') or findings_by_trial.get((case['id'], int(directory.name.removeprefix('trial-'))))
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
                    'continuation_observations': {path.name: read(path)
                        for path in sorted(directory.glob('result-after-*.json'))},
                    'human_clarification': read(directory/'human-clarification.json'),
                    'runtime_retirement': read(directory/'runtime-retirement.json'),
                    'business_oracles': oracles,
                    'business_observations': {path.name: observer_receipt(path) for pattern in (
                        'browser-oracle*.json', 'persistence-oracle*.json', 'external-evidence.json',
                        'semantic-prerequisite-evidence.json', 'worker-interruption.json',
                        'review-authority-oracle.json', 'response-stream*.json')
                        for path in sorted(directory.glob(pattern))},
                    'source_diff_sha256': sha256((directory/'candidate.diff').read_bytes()).hexdigest()
                        if (directory/'candidate.diff').exists() else None,
                    'served_body_sha256': sha256((directory/'served.html').read_bytes()).hexdigest()
                        if (directory/'served.html').exists() else None,
                    'business_status': qualification_status(oracles[-1]['status']) if oracles else 'NOT_EVALUATED',
                    'observed_latency_seconds':(result or {}).get('elapsed_seconds'),
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
                    'human_question_projection':state.get('interaction',{}).get('unresolved_material_questions',[]),
                    'work_convergence':state.get('refinement',{}).get('work_convergence',[]),
                    'manual_rescue_actions': journey.get('manual_rescue_actions', []),
                    'human_acceptance': 'PENDING'})
        trials.sort(key=lambda trial: trial['trial'])
        passed = [trial for trial in trials if trial['business_status'] == 'PASS']
        independent = {trial['interaction_id'] for trial in passed if trial['interaction_id']}
        cases.append({'id': case['id'], 'required_oracle': case['acceptance_oracle'],
            'trials': trials, 'successful_independent_trials': len(independent),
            'minimum_independent_trials': case['minimum_independent_trials'],
            'repeat_requirement': 'PASS' if len(independent) >= case['minimum_independent_trials'] else 'NOT_QUALIFIED',
            'status': 'PASS' if passed else ('BLOCKED_EXTERNAL' if any(trial['business_status'] == 'BLOCKED_EXTERNAL' for trial in trials) else 'PENDING')})
    all_trials = [trial for case in cases for trial in case['trials']]
    passed_trials = [trial for trial in all_trials if trial['business_status'] == 'PASS']
    core_cases = [case for case in cases if case['minimum_independent_trials'] >= 3]
    core_status = 'PASS' if all(case['repeat_requirement'] == 'PASS' for case in core_cases) else 'NOT_QUALIFIED'
    feasible_status = 'PASS' if all(case['status'] == 'PASS' and case['repeat_requirement'] == 'PASS'
        for case in cases if case['status'] != 'BLOCKED_EXTERNAL') else 'NOT_QUALIFIED'
    tier_status = 'PASS' if all(case['status'] == 'PASS' and case['repeat_requirement'] == 'PASS'
        for case in cases) else ('BLOCKED_EXTERNAL' if feasible_status == 'PASS'
        and any(case['status'] == 'BLOCKED_EXTERNAL' for case in cases) else 'NOT_QUALIFIED')
    denominator = len(all_trials)
    inappropriate = [trial for trial in all_trials if (trial['human_attention'] or trial['human_question_projection'])
        and any(marker in str((trial.get('failure_classification') or {}).get('signal') or (trial.get('failure_classification') or {}).get('status','')) for marker in (
            'DESIGN_SCHEMA_MISMATCH','ALREADY_DECIDED','HUMAN_FACT_REASKED','RUNTIME_PREREQUISITE_REASKED',
            'SOURCE_DERIVABLE_PREVIEW_MECHANISM','BOUNDED_MAINTENANCE_MISROUTED','PROVIDER_CANDIDATE_PROMOTED',
            'MODEL_CANDIDATE_CANNOT_EXPAND','INAPPROPRIATE_PRE_DISCOVERY_QUESTION'))]
    signatures = Counter(((trial.get('failure_classification') or {}).get('signal') or (trial.get('failure_classification') or {}).get('status')) for trial in all_trials if trial.get('failure_classification'))
    attention_unknown = [trial for trial in all_trials if trial['human_attention'] and trial['business_status'] != 'PASS' and not trial.get('failure_classification') and any(item.get('kind') != 'CANDIDATE_AUTHORIZATION' for item in trial['human_attention'])]
    scope_detected = [trial for trial in all_trials if any(marker in str((trial.get('failure_classification') or {}).get('signal') or (trial.get('failure_classification') or {}).get('status','')) for marker in ('SCOPE_INFLATION','SCOPE_EXPANSION','PROVIDER_CANDIDATE_PROMOTED','MODEL_CANDIDATE_CANNOT_EXPAND','TEST_REFERENCE'))]
    contract_detected = [trial for trial in all_trials if any(marker in str((trial.get('failure_classification') or {}).get('signal') or (trial.get('failure_classification') or {}).get('status','')) for marker in ('CONTRACT','CAPABILITY','TOOL_GRANT'))]
    recovered = [trial for trial in passed_trials if any(event['final_result'] == 'LOCAL_OBLIGATION_RECOVERED' for event in trial['refinements'])]
    non_converging = [trial for trial in all_trials if any(row.get('condition') in
        {'NON_CONVERGING','ESCALATED'} for row in trial['work_convergence'])]
    dimensions = {'historical_submitted_trials':denominator,'successful_business_trials':len(passed_trials),
        'historical_final_success_rate': len(passed_trials)/denominator if denominator else None,
        'review_ready_without_business_evaluation_trials':sum(
            trial['business_status']=='NOT_EVALUATED'
            and (trial['observer_result'] or {}).get('status')=='REVIEW_READY_AWAITING_BUSINESS_ORACLE'
            for trial in all_trials),
        'external_credential_blocked_trials':sum(trial['business_status']=='BLOCKED_EXTERNAL' for trial in all_trials),
        'scope_candidate_contraction_trials':sum(any(event.get('diagnostic_evidence',{}).get('signal')=='SCOPE_INFLATION' for event in trial['refinements']) for trial in all_trials),
        'detected_failed_scope_inflation_trials':len(scope_detected),'detected_scope_inflation_rate':len(scope_detected)/denominator if denominator else None,
        'detected_contract_or_capability_mismatch_trials':len(contract_detected),
        'business_success_after_observed_local_recovery':len(recovered),
        'recovery_rate_among_successful_business_trials':len(recovered)/len(passed_trials) if passed_trials else None,
        'observed_non_convergence_trials':len(non_converging),
        'observed_non_convergence_rate':len(non_converging)/denominator if denominator else None,
        'detected_inappropriate_human_interruption_trials':len(inappropriate),
        'detected_inappropriate_human_interruption_rate':len(inappropriate)/denominator if denominator else None,
        'manual_rescue_actions':sum(len(trial['manual_rescue_actions']) for trial in all_trials),
        'allowed_clarification_answers':sum(bool(trial['human_clarification']) for trial in all_trials),
        'unclassified_failed_attention_trials':len(attention_unknown),
        'recurring_failure_signatures':dict(signatures),
        'currency_cost':'UNREPORTED; observed provider tokens and runtime durations are retained per trial',
        'interpretation':'Historical rates include every submitted app revision, infrastructure-capacity failure and explicitly counted review-ready trial without a business evaluation; they are not the qualification-window success rate. Detected rates are evidence-backed lower bounds, not claims that unknown observations are clean.'}
    report = {'schema_version': 2, 'corpus_version': corpus['corpus_version'],
        'tier_0_gate': tier_status, 'core_repeat_stability': core_status,
        'feasible_golden_gate': feasible_status,
        'blocked_external_cases': [case['id'] for case in cases if case['status'] == 'BLOCKED_EXTERNAL'],
        'dimensions':dimensions,
        'human_acceptance': 'PENDING', 'cases': cases,
        'note': 'Closure requires every mandatory oracle and qualified repeated semantic outcomes; no aggregate quality score is inferred.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'cases': len(cases), 'cases_with_passed_oracle': sum(case['status']=='PASS' for case in cases),
        'tier_0_gate': tier_status, 'core_repeat_stability':core_status, 'human_acceptance': 'PENDING'}))


if __name__ == '__main__':
    main()
