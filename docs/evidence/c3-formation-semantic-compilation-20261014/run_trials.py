"""Fixed non-Holdout qualification: fresh bounded Formation, real model, no Work writes.

Mounted read-only into the exact image. Cases/trials/budget are fixed by protocol.md.
"""
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy
import hashlib, json, os, re, sys, time, unicodedata
from dataclasses import asdict

from spg.application import governed_obligations as app
from spg.providers import fulfillment_candidate as wire_owner
from spg.providers.fulfillment_candidate import ModelFulfillmentCandidateProvider
from spg.domain.governed_obligation import (FulfillmentProjectionCandidate, fulfillment_source_semantic_text,
    fulfillment_component_id)
from spg.domain.model_runtime import (ModelProfile, ModelProvider, ModelPurpose, ModelProviderRegistry,
    PurposeProfileRouter, WattModelRuntime)
from spg.infrastructure.model_runtime import DeepSeekResponsesModelAdapter

exec(Path('/helper.py').read_text().split("report={'schema'")[0])
CASES = ('ordinary34', 'ordinary41')
TRIALS = 3
TOKEN_STOP = 2_000_000
evidence, private = Path('/evidence'), Path('/private')
spent = {'tokens': 0}
report = {'schema': 'c3-semantic-compilation-nonholdout-v1', 'source_revision': os.environ['SPG_RUNTIME_REVISION'],
    'actual_runtime_sha256': hashlib.sha256(Path(app.__file__).read_bytes()).hexdigest(),
    'provider_runtime_sha256': hashlib.sha256(Path(wire_owner.__file__).read_bytes()).hexdigest(),
    'holdout_used': False, 'new_work_created': False, 'database_access': False,
    'model_profile': {'provider': 'DEEPSEEK', 'model': 'deepseek-flash', 'reasoning_effort': 'none',
        'max_output_tokens': 16384, 'timeout_seconds': 120}, 'trials': []}

def runtime_factory(calls):
    def factory():
        registry = ModelProviderRegistry()
        registry.register(DeepSeekResponsesModelAdapter(api_key=lambda: os.environ['SPG_DEEPSEEK_API_KEY'],
            base_url=os.environ['SPG_DEEPSEEK_BASE_URL']))
        profile = ModelProfile(purpose=ModelPurpose.STEERING_SEMANTIC, provider=ModelProvider.DEEPSEEK,
            model='deepseek-flash', reasoning_effort='none', max_output_tokens=16384, timeout_seconds=120)
        actual = WattModelRuntime(registry, PurposeProfileRouter({ModelPurpose.STEERING_SEMANTIC: profile}))
        class Counted:
            def generate(self, **request):
                if len(calls) >= 4:
                    raise RuntimeError('QUALIFICATION_LOGICAL_CALL_LIMIT')
                result = actual.generate(**request)
                calls.append({'request_id': result.request_id, 'usage': asdict(result.usage),
                    'role': 'review' if 'untrusted_fulfillment_candidate' in request['input_text'][:400000] else 'formation'})
                spent['tokens'] += result.usage.total_tokens or 0
                return result
            def close(self):
                actual.close()
        return Counted()
    return factory

def attachment_violations(rows, inventory):
    texts = [fulfillment_source_semantic_text(s) for s in inventory['sources']]
    bad, seen = [], 0
    for row in rows:
        construction = ((row.get('wire_presentation') or {}).get('candidate_construction') or {})
        for item in (construction.get('geometry_compilation') or {}).get('attachments', []):
            seen += 1
            text = texts[item['source']]
            if any(not unicodedata.category(text[i]).startswith('P') for i in item['attached_codepoints']):
                bad.append(item)
    return seen, bad

def independent_admission_check(bindings, rows, revision, ir, inventory):
    """Re-derive the admitted candidate and re-run the unchanged validator offline."""
    admitted = all(b.state != 'UNRESOLVED' for b in bindings)
    if not admitted:
        return {'admitted': False}
    validated = [r for r in rows if r['stage'] == 'CANDIDATE_VALIDATED' and r.get('validation_passed')]
    reviews = [r for r in rows if r['stage'] == 'SEMANTIC_REVIEW_VALIDATED' and r.get('validation_passed')]
    final = validated[-1]
    candidate = FulfillmentProjectionCandidate.model_validate(final['candidate'])
    review = reviews[-1]['semantic_review'] if reviews else None
    owner = next(r for r in rows if r['stage'] == 'MODEL_REQUEST_PENDING' and r['attempt'] == final['attempt']).get('owner_source_preconditions')
    problems = []
    try:
        app.validate_projection_candidate(candidate, revision, ir, inventory, semantic_review=review,
            source_contract='v3', owner_preconditions=owner)
    except Exception as error:
        problems.append(stable(error))
    keys = [(fulfillment_component_id(r, inventory['inventory_fingerprint']), r.capability) for r in candidate.routes]
    if len(keys) != len(set(keys)):
        problems.append('DUPLICATE_COMPONENT_CONSUMER')
    for source in inventory['sources']:
        text = fulfillment_source_semantic_text(source)
        covered = set()
        for r in candidate.routes:
            if r.source_ref == source['source_ref']:
                covered.update(range(r.component_basis.source_span_start, r.component_basis.source_span_end))
        if any(not c.isspace() and i not in covered for i, c in enumerate(text)):
            problems.append('COVERAGE_LOST:' + source['source_ref'])
    if review is None or not all(row['complete_and_equivalent'] for row in review['source_results']):
        problems.append('NO_POSITIVE_INDEPENDENT_REVIEW')
    return {'admitted': True, 'offline_problems': problems, 'false_admission': bool(problems)}

for name in CASES:
    for trial in range(1, TRIALS + 1):
        if spent['tokens'] >= TOKEN_STOP:
            report['token_stop_reached'] = True
            break
        raw, revision, ir, old, inventory, caps = load_case(name)
        before = deepcopy((revision, ir, inventory))
        calls = []
        provider = ModelFulfillmentCandidateProvider(runtime_factory(calls), candidate_construction=True,
            candidate_construction_contract='owner-local-interpretation-role-construction-v4', raw_role_repair=True,
            construction_consumer_instructions=True, unparsed_claim_repair=True, role_convergence=True,
            decision_revision_actions=True, semantic_compilation=True)
        tag = f'{name}-t{trial}'
        started = datetime.now(timezone.utc).isoformat(); begin = time.monotonic()
        terminal, error = None, None
        try:
            kwargs = dict(source_revision=inventory['source_revision'], exact_target_paths=inventory['exact_target_paths'])
            bindings = app.form_fulfillment_projection(revision, ir, provider=provider, **kwargs)
            terminal = bindings[0].formation_receipt['terminal_reason']
            count = len(calls); snapshot = json.dumps(provider._fulfillment_receipts, sort_keys=True)
            app.form_fulfillment_projection(revision, ir, provider=provider, **kwargs)
            replay_ok = len(calls) == count and json.dumps(provider._fulfillment_receipts, sort_keys=True) == snapshot
        except Exception as exc:
            bindings, replay_ok = [], None
            error = stable(exc); terminal = error
        assert before == (revision, ir, inventory)
        rows = app.FulfillmentFormationReceipts(revision, inventory, memory=provider._fulfillment_receipts).records()
        (private / f'{tag}-owner-receipts.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1))
        seen, bad = attachment_violations(rows, inventory)
        admission = independent_admission_check(bindings, rows, revision, ir, inventory) if bindings else {'admitted': False}
        attempts = []
        for row in rows:
            if row['stage'] == 'CANDIDATE_VALIDATED':
                codes = []
                if isinstance(row.get('validation_feedback'), str):
                    fb = json.loads(row['validation_feedback'])
                    codes = sorted({v.get('code') for v in fb.get('violations', [])}
                        | {v.get('code') for v in (fb.get('owner_repair_context') or {}).get('violations', [])})
                attempts.append({'attempt': row['attempt'], 'passed': row.get('validation_passed'),
                    'failed_predicate': row.get('failed_predicate'), 'codes': codes})
        constructions = [((r.get('wire_presentation') or {}).get('candidate_construction') or {}) for r in rows
            if r['stage'] == 'MODEL_RESPONSE_OBSERVED']
        result = {'trial': tag, 'case': name, 'started_at_utc': started, 'elapsed_seconds': time.monotonic() - begin,
            'inventory_fingerprint': inventory['inventory_fingerprint'], 'source_count': len(inventory['sources']),
            'formation_calls': sum(c['role'] == 'formation' for c in calls), 'review_calls': sum(c['role'] == 'review' for c in calls),
            'tokens': sum(c['usage'].get('total_tokens') or 0 for c in calls), 'terminal_reason': terminal, 'error': error,
            'terminal_replay_without_calls': replay_ok, 'attempts': attempts,
            'reexpressed_sources': [len(c.get('reexpressed_original_ordinals', [])) for c in constructions],
            'compilation_attachments': seen, 'non_punctuation_attachments': len(bad), **admission,
            'request_ids': [c['request_id'] for c in calls]}
        report['trials'].append(result)
        report['tokens_spent'] = spent['tokens']
        (evidence / 'trials.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({k: result[k] for k in ('trial', 'formation_calls', 'review_calls', 'tokens', 'terminal_reason',
            'admitted', 'compilation_attachments', 'non_punctuation_attachments')}), flush=True)
        if terminal and ('TRANSPORT' in terminal or 'PENDING_OUTCOME_UNKNOWN' in terminal):
            report['stopped_on_transport'] = tag
            (evidence / 'trials.json').write_text(json.dumps(report, indent=2) + '\n')
            sys.exit(2)
