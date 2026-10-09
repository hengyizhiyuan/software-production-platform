"""Offline exact-image analysis; no model, database, authority or admitted plan."""
import sys
sys.dont_write_bytecode = True
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import time

def main():
    from spg.domain.interaction import WorkRealityRevision
    from spg.domain.intent_realization import GovernedSemanticIR
    from spg.domain.governed_obligation import (FulfillmentProjectionCandidate,
        fulfillment_source_semantic_text, fulfillment_candidate_fingerprint,
        fulfillment_components_fingerprint, exact_file_scope_paths)
    from spg.application.governed_obligations import (fulfillment_inventory,
        fulfillment_capability_contracts, validate_projection_candidate,
        validate_projection_components, _projection_binding,
        _reviewed_background_context_refs, work_constraint_sources_correspond,
        is_context_only_clause)
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    import_bytes = Path('/qualified-imports.json').read_bytes()
    assert sha256(import_bytes).hexdigest() == 'fea7676b7c6bdfec6aa6d1fa1e6665a67ac0e205157cc48dc11af158a6823f12'
    attestation = json.loads(import_bytes)
    import_counts = {}
    for name in ('spg', 'guardian', 'ecf'):
        imported = attestation['actual_imports'][name]
        base = Path(imported['package_root'])
        for relative, expected in imported['file_sha256'].items():
            assert sha256((base / relative).read_bytes()).hexdigest() == expected
        import_counts[name] = len(imported['file_sha256'])
    basis_bytes, candidate_bytes = Path('/basis.json').read_bytes(), Path('/candidate.json').read_bytes()
    assert sha256(basis_bytes).hexdigest() == '9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c'
    assert sha256(candidate_bytes).hexdigest() == 'e9020a908ba354c2e12ab4db297b32b7d17041fd12e4180a740f39d9fb42c9b5'
    data = json.loads(basis_bytes)
    revision = WorkRealityRevision.model_validate(next(row for row in data['datasets']['work_reality_revisions']['rows'] if row['id'] == '332a3a38-8719-580c-a1a2-c331ae14a5ae'))
    assessment = next(row for row in data['datasets']['interaction_assessments']['rows'] if row['id'] == str(revision.source_assessment_id))
    ir = GovernedSemanticIR.model_validate(assessment['semantic_ir'])
    inventory = fulfillment_inventory(revision, ir, source_revision='465038ded6cf4ba335a11577de76acb1dea55b76', exact_target_paths=('index.html',))
    assert inventory['inventory_fingerprint'] == '7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf'
    candidate = FulfillmentProjectionCandidate.model_validate_json(candidate_bytes)
    assert fulfillment_candidate_fingerprint(candidate) == '98e38e96d66751327a6eb44519cf980db471aae99664b324c3e36a043a049444'
    assert len(candidate.routes) == 57 and len(inventory['sources']) == 26
    sources = inventory['sources']
    refs = {source['source_ref']: index for index, source in enumerate(sources)}
    texts = [fulfillment_source_semantic_text(source) for source in sources]
    background = _reviewed_background_context_refs(candidate, revision, ir, inventory)
    sensitive_phrases = sorted({text for text in texts if len(text) > 6}, key=len, reverse=True)
    for fact in revision.engineering_semantic_facts:
        values = fact.value if isinstance(fact.value, tuple) else (fact.value,)
        sensitive_phrases.extend(value for value in values if isinstance(value, str) and len(value) > 6 and value != 'index.html')
    def rationale_hint(text):
        for phrase in sensitive_phrases:
            text = text.replace(phrase, '[ORIGINAL_VALUE_OR_QUOTE]')
        return text[:350]
    def code(error):
        matches = re.findall(r'\bOBLIGATION_[A-Z0-9_]+\b', str(error))
        return matches[0] if matches else type(error).__name__
    def attempt(function):
        try:
            value = function()
            if isinstance(value, (list, tuple)):
                return {'result': 'PREDICATES_RETURNED_NOT_ADMISSION', 'binding_count': len(value),
                    'state_counts': dict(Counter(str(item.state) for item in value))}
            return {'result': 'LOCAL_PREDICATES_RETURNED_NOT_ADMISSION', 'state': getattr(value, 'state', None)}
        except Exception as error:
            return {'result': 'REJECTED', 'predicate': code(error), 'error_type': type(error).__name__}
    route_rows = []
    private_rows = []
    for index, route in enumerate(candidate.routes):
        ordinal = refs[route.source_ref]
        entry = {'route_index': index, 'source_ordinal': ordinal, 'capability': route.capability,
            'support_ordinals': [refs[ref] for ref in route.supporting_source_refs],
            'linked_fact_ordinals': list(route.component_basis.linked_fact_refs),
            'target_paths': list(route.target_paths), 'constraint_indices': list(route.work_constraint_indices),
            'span': [route.component_basis.source_span_start, route.component_basis.source_span_end],
            'full_source_span': route.component_basis.source_span_start == 0 and route.component_basis.source_span_end == len(texts[ordinal]),
            'quote_sha256': sha256(route.component_basis.source_component_quote.encode()).hexdigest(),
            'rationale_sha256': sha256(route.rationale.encode()).hexdigest(),
            'local_original_route_check': attempt(lambda r=route: _projection_binding(revision, ir, inventory, r, reviewed_background_refs=background))}
        entry['linked_fact_ordinals'] = [refs[ref] for ref in route.component_basis.linked_fact_refs]
        route_rows.append(entry)
        private_rows.append({**entry, 'rationale': route.rationale, 'source_text': texts[ordinal], 'original_route': route.model_dump(mode='json')})
    catalog = []
    private_catalog = []
    for ordinal, source in enumerate(sources):
        routes = [row for row in route_rows if row['source_ordinal'] == ordinal]
        row = {'source_ordinal': ordinal, 'kind': source['kind'], 'source_ref': source['source_ref'],
            'source_text_sha256': sha256(texts[ordinal].encode()).hexdigest(), 'source_text_chars': len(texts[ordinal]),
            'route_indices': [route['route_index'] for route in routes],
            'capabilities': [route['capability'] for route in routes],
            'conflicting_source_disposition': bool(set(route['capability'] for route in routes) & {'UNRESOLVED', 'RETAIN_CONTEXT'}) and len(set(route['capability'] for route in routes)) > 1}
        if source['kind'] == 'FACT':
            fact = next(f for f in revision.engineering_semantic_facts if str(f.id) == source['fact_id'])
            row['fact'] = {key: getattr(fact, key) for key in ('subject', 'relation', 'scope', 'unit', 'reference_role', 'authority', 'epistemic_status')}
            row['fact'].update(value_sha256=sha256(json.dumps(fact.model_dump(mode='json')['value'], sort_keys=True).encode()).hexdigest(),
                value_type=type(fact.value).__name__, qualifier_keys=list(fact.qualifiers),
                provenance_origins=[str(p.origin) for p in fact.provenance.governed_provenance],
                exact_file_scope_paths=exact_file_scope_paths(fact))
        if source['kind'] in {'IR_CLAUSE', 'IR_CONSTRAINT'}:
            clause = next(c for c in ir.clauses if c.clause_id == source['clause_id'])
            item = next(i for i in ir.items if i.item_id == source['item_id'])
            row['clause'] = {key: getattr(clause, key) for key in ('clause_id', 'polarity', 'modality', 'temporal_scope', 'speech_act', 'requested_effects')}
            row['item'] = {'item_id': item.item_id, 'kind': item.kind, 'requires_human': item.requires_human,
                'provenance_origins': [str(p.origin) for p in item.provenance],
                'production_present': item.production is not None, 'action_present': item.action is not None,
                'is_context_only_by_existing_contract': is_context_only_clause(revision, ir, item.item_id, clause.clause_id)}
            if item.production is not None:
                row['item']['production'] = {'current': item.production.current, 'acceptance_required': item.production.acceptance_required,
                    'preview_required': item.production.preview_required, 'delivery_authorized': item.production.delivery_authorized,
                    'scope_count': len(item.production.scope), 'exclusion_count': len(item.production.exclusions)}
        if source['kind'] == 'WORK_CONSTRAINT':
            row['constraint_index'] = source['index']
            row['exact_clause_text_match_ordinals'] = [i for i, entry in enumerate(sources) if entry['kind'] in {'IR_CLAUSE', 'IR_CONSTRAINT'} and source['payload']['content'] == texts[i]]
            row['exact_item_statement_match_ordinals'] = [i for i, entry in enumerate(sources) if entry['kind'] in {'IR_CLAUSE', 'IR_CONSTRAINT'} and source['payload']['content'] == entry['payload']['item']['statement']]
            row['production_scope_match_ordinals'] = [i for i, entry in enumerate(sources) if entry['kind'] in {'IR_CLAUSE', 'IR_CONSTRAINT'} and entry['payload']['item'].get('production') and source['payload']['content'] in entry['payload']['item']['production']['scope']]
            row['production_exclusion_match_ordinals'] = [i for i, entry in enumerate(sources) if entry['kind'] in {'IR_CLAUSE', 'IR_CONSTRAINT'} and entry['payload']['item'].get('production') and any(source['payload']['content'] == 'Excluded from this Work: ' + value for value in entry['payload']['item']['production']['exclusions'])]
        catalog.append(row)
        private_catalog.append({**row, 'full_source': source, 'source_text': texts[ordinal]})
    def variant(name, indices, reason):
        plan = candidate.model_copy(update={'routes': tuple(candidate.routes[index] for index in indices)})
        return {'name': name, 'counterfactual_only': True, 'invalid_as_production_result': True,
            'recipe': reason, 'kept_original_route_indices': indices,
            'removed_original_route_indices': sorted(set(range(57)) - set(indices)),
            'candidate_fingerprint': fulfillment_candidate_fingerprint(plan),
            'source_count': len(set(route.source_ref for route in plan.routes)),
            'result': attempt(lambda: validate_projection_candidate(plan, revision, ir, inventory, allow_review_pending=True)),
            'independent_review': 'NOT_EXECUTED', 'admission_or_assurance': False}
    unique, seen = [], set()
    for index, route in enumerate(candidate.routes):
        key = (route.source_ref, route.capability)
        if key not in seen:
            unique.append(index)
            seen.add(key)
    caps_by_source = {source['source_ref']: {route.capability for route in candidate.routes if route.source_ref == source['source_ref']} for source in sources}
    prefer_executable = [index for index in unique if candidate.routes[index].capability not in {'UNRESOLVED', 'RETAIN_CONTEXT'} or not (caps_by_source[candidate.routes[index].source_ref] - {'UNRESOLVED', 'RETAIN_CONTEXT'})]
    prefer_unresolved = [index for index in unique if candidate.routes[index].capability == 'UNRESOLVED' or 'UNRESOLVED' not in caps_by_source[candidate.routes[index].source_ref]]
    prefer_retained = [index for index in unique if candidate.routes[index].capability == 'RETAIN_CONTEXT' or 'RETAIN_CONTEXT' not in caps_by_source[candidate.routes[index].source_ref]]
    variants = [variant('ORIGINAL', list(range(57)), 'unchanged original actual candidate'),
        variant('CF_EXACT_DUPLICATE_REMOVED', unique, 'Remove later repeated source/capability pair in isolated copy; never a repair'),
        variant('CF_PREFER_EXECUTABLE', prefer_executable, 'After dedup, suppress unresolved/context dispositions where an executable proposal exists; destroys proposed meaning and is not eligible'),
        variant('CF_PREFER_UNRESOLVED', prefer_unresolved, 'After dedup, retain unresolved instead of other routes on that source; exposes remaining rejection, no fulfillment'),
        variant('CF_PREFER_RETAINED', prefer_retained, 'After dedup, retain context instead of other routes on that source; diagnostic only')]
    report = {'schema': 'c3-semantic-contract-calibration-offline-v1', 'started_at_utc': started,
        'application_source': 'e0df8196cb51480f542af13b40cfa77fca6b6a6e',
        'qualified_import_file_counts': import_counts,
        'inventory_fingerprint': inventory['inventory_fingerprint'], 'basis_sha256': sha256(basis_bytes).hexdigest(),
        'candidate_file_sha256': sha256(candidate_bytes).hexdigest(),
        'candidate_fingerprint': fulfillment_candidate_fingerprint(candidate),
        'component_fingerprint': fulfillment_components_fingerprint(candidate), 'original_route_count': 57,
        'catalog': catalog, 'routes': route_rows, 'counterfactuals': variants,
        'original_component_coverage_check_review_pending': attempt(lambda: validate_projection_components(candidate, inventory, allow_review_pending=True)),
        'reviewed_background_eligibility_ordinals': [refs[ref] for ref in background],
        'model_calls': 0, 'database_access': False, 'input_files_mutated': False,
        'semantic_review_or_assurance_claim': False, 'counterfactual_admission_claim': False,
        'ended_at_utc': datetime.now(timezone.utc).isoformat(), 'wall_seconds': time.monotonic()-clock}
    for path, content in ((Path('/evidence/analysis.json'), report), (Path('/private/full-semantic-dossier.json'), {'catalog': private_catalog, 'routes': private_rows})):
        assert not path.exists()
        with path.open('x', encoding='utf-8') as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(content, stream, ensure_ascii=False, indent=2, default=str)
            stream.write('\n')
    special = [{'route_index': row['route_index'], 'source_ordinal': row['source_ordinal'], 'capability': row['capability'],
        'rationale_hint': rationale_hint(candidate.routes[row['route_index']].rationale), 'local_check': row['local_original_route_check']}
        for row in route_rows if row['capability'] in {'UNRESOLVED', 'RETAIN_CONTEXT'}]
    print(json.dumps({'special_routes': special, 'sources': catalog,
        'counterfactuals': [{'name': row['name'], 'result': row['result'], 'source_count': row['source_count']} for row in variants]}, ensure_ascii=False, default=str))

if __name__ == '__main__':
    main()
