"""Business evidence after review readiness, separate from Human Acceptance.

Only bounded read-only source/diff/served observations are automated here.
Interactive and persistence cases require their actual Browser/API oracle evidence;
absence is reported as NOT_EVALUATED rather than converted into a green score.
"""
import argparse
from html.parser import HTMLParser
import json
import re
import subprocess
from pathlib import Path
import urllib.request

if __package__:
    from .owner_retry_oracle import observed_acquisition_recovery
else:
    from owner_retry_oracle import observed_acquisition_recovery


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.current=None; self.links=[]
    def handle_starttag(self, tag, attrs):
        if tag == 'a': self.current=[dict(attrs).get('href'), '']
    def handle_data(self, value):
        if self.current is not None: self.current[1] += value
    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.links.append(tuple(self.current)); self.current=None


def only_link_added(added, removed, *, label, href):
    if len(added) != 1 or len(removed) > 1:
        return False
    pattern = r'<a\s+href=([\"\'])' + re.escape(href) + r'\1\s*>' + re.escape(label) + r'</a>'
    matches = list(re.finditer(pattern, added[0]))
    if len(matches) != 1:
        return False
    prefix, suffix = added[0][:matches[0].start()], added[0][matches[0].end():]
    before = removed[0] if removed else ''
    return any(remainder.strip() == before.strip() for remainder in (
        prefix + suffix, prefix.rstrip(' \t') + suffix, prefix + suffix.lstrip(' \t')))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--base',required=True)
    parser.add_argument('--browser-record', default='browser-oracle.json')
    parser.add_argument('--database-record', default='persistence-oracle.json')
    parser.add_argument('--native-attempt-record', default='native-attempt.json')
    parser.add_argument('--historical-runtime', action='store_true',
        help='Reconcile retained evidence after explicit runtime retirement; never restart Preview')
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--record-name', default='business-oracle.json',
        help='A new evidence identity; existing oracle records are never replaced')
    args=parser.parse_args()
    root=args.directory
    if any(Path(value).name != value for value in (args.record_name, args.browser_record, args.database_record, args.native_attempt_record)):
        raise SystemExit('Evidence record name must be a single filename')
    output=root/args.record_name
    if output.exists(): raise SystemExit('Oracle record already exists; do not rewrite historical results')
    state=json.loads((root/'latest.json').read_text(encoding='utf-8'))
    journey_path=root/'journey.json'
    try:
        journey=json.loads(journey_path.read_text(encoding='utf-8'))
    except UnicodeDecodeError:
        journey=json.loads(journey_path.read_text(encoding='gbk'))
    if journey['case'] == 'GC-EX-11':
        # The truthful outcome for a genuinely unavailable external secret is
        # a bounded Human escalation, not a fabricated or unverified Preview.
        decision=state.get('steering', {}).get('latest_decision') or {}
        attention=state.get('attention') or []
        prompt=' '.join(str(item.get('reason', '')) for item in attention)
        checks={
            'work_admitted': bool(state.get('work', {}).get('work_id')),
            'bounded_human_escalation': state.get('work', {}).get('status') == 'NEEDS_ATTENTION'
                and state.get('steering', {}).get('steering_outcome') == 'HUMAN_ATTENTION'
                and decision.get('next_step_type') == 'HUMAN_DECISION'
                and len(attention) == 1
                and attention[0].get('kind') == 'STEERING_DECISION_REQUIRED',
            'actual_missing_secret_identified': 'STRIPE_SECRET_KEY' in decision.get('reason', '')
                and 'secret.inject' in decision.get('reason', '')
                and 'Stripe' in prompt,
            'no_fabricated_secret_or_preview': state.get('preview', {}).get('status') == 'NOT_READY'
                and not state.get('preview', {}).get('session')
                and state.get('economics', {}).get('pwu_count') == 0
                and state.get('work', {}).get('current_production_run_id') is None,
            'no_unauthorized_delivery': not state.get('delivery', {}).get('deliveries'),
            'one_unassisted_turn': len(state.get('interaction', {}).get('turns', [])) == 1
                and not journey.get('manual_rescue_actions')
                and not journey.get('tester_implementation'),
        }
        result={'case':journey['case'], 'trial':journey['trial'], 'checks':checks,
            'status':'PASS' if all(checks.values()) else 'FAIL',
            'work_id':state.get('work', {}).get('work_id'),
            'human_acceptance':journey.get('human_acceptance', 'PENDING'),
            'manual_rescue_actions':journey.get('manual_rescue_actions', [])}
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(0 if result['status'] == 'PASS' else 1)
    env=dict(line.split('=',1) for line in args.env_file.read_text(encoding='utf-8').splitlines() if '=' in line)
    def read(path,payload=None):
        request=urllib.request.Request(args.base+path,
            data=None if payload is None else json.dumps(payload).encode(),headers={
                'Authorization':'Bearer '+env['SPG_OPERATOR_TOKEN'],'Content-Type':'application/json'})
        return urllib.request.urlopen(request,timeout=20).read().decode()
    work_id=state['work']['work_id']; prefix='/api/works/'+work_id
    if args.historical_runtime:
        retired=json.loads((root/'runtime-retirement.json').read_text(encoding='utf-8'))
        prior=json.loads((root/'business-oracle.json').read_text(encoding='utf-8'))
        preview=state['preview']
        session=preview['session']
        if (retired['prior_status'] != 'READY' or retired['preview_id'] != session['id']
                or prior['candidate_revision'] != session['repository_revision']
                or prior['candidate_tree'] != session['repository_tree']):
            raise SystemExit('Historical source/runtime identity does not agree')
        meta={'repository_revision':prior['candidate_revision'], 'tree':prior['candidate_tree']}
        diff=(root/'candidate.diff').read_text(encoding='utf-8')
        body=(root/'served.html').read_text(encoding='utf-8')
    else:
        meta=json.loads(read(prefix+'/candidate-preview',{}))
        diff=read(prefix+'/candidate-code-diff/'+meta['candidate_fingerprint'])
        (root/'candidate.diff').write_text(diff,encoding='utf-8')
        preview=json.loads(read(prefix+'/functional-preview'))
        served_bytes=urllib.request.urlopen(preview['session']['endpoint'],timeout=20).read()
        body=served_bytes.decode()
        # Preserve the served bytes exactly. Text-mode writes on Windows can
        # change LF to CRLF and invalidate byte-for-byte source comparisons.
        (root/'served.html').write_bytes(served_bytes)
    paths=[line.split(' b/',1)[1] for line in diff.splitlines() if line.startswith('diff --git')]
    added=[line[1:] for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++')]
    removed=[line[1:] for line in diff.splitlines() if line.startswith('-') and not line.startswith('---')]
    checks={'automatic_preview_ready':preview['status']=='READY',
        'served_verification':any(item.get('kind')=='SERVED_VERIFICATION' and item.get('result')=='PASS'
            for item in preview['session']['evidence']),
        'no_unauthorized_delivery':not state['delivery'].get('deliveries')}
    identity=journey['case']
    if identity in {'GC-EX-01','GC-EX-07'}:
        label,href=('关于我们','/about') if identity=='GC-EX-01' else ('使用帮助','/help')
        links=Links();links.feed(body)
        checks.update(exactly_one_requested_link=links.links.count((href,label))==1,
            one_source_file=len(paths)==1)
        if identity == 'GC-EX-01':
            checks.update(one_added_line=len(added)==1, zero_removed_lines=not removed)
        else:
            checks['only_requested_link_changed'] = only_link_added(added, removed, label=label, href=href)
    elif identity in {'GC-EX-02','GC-EX-04','GC-EX-06','GC-EX-14','GC-EX-15'}:
        checks.update(new_label='立即体验' in body, old_label='开始使用' not in body,
            one_source_file=len(paths)==1, minimal_source_diff=len(added)==1 and len(removed)==1)
        if identity == 'GC-EX-06':
            acquisition = [event for event in state.get('refinement', {}).get('events', [])
                if event['affected_component'] == 'repository/acquisition']
            checks['automatic_acquisition_recovery'] = any(
                event['final_result'] == 'LOCAL_OBLIGATION_RECOVERED'
                and event['diagnostic_evidence'].get('final_condition') == 'READY'
                and event['diagnostic_evidence'].get('attempt_budget') == 3
                for event in acquisition)
            owner_rows = root/'acquisition-owner-attempts.json'
            turns = state.get('interaction', {}).get('turns', [])
            if owner_rows.exists() and len(turns) == 1:
                checks['automatic_acquisition_recovery'] |= observed_acquisition_recovery(
                    json.loads(owner_rows.read_text(encoding='utf-8')),
                    interaction_id=journey['interaction_id'],
                    source_record_id=turns[0]['request_record_id'])
        if identity == 'GC-EX-15':
            try:
                review = json.loads((root/'review-authority-oracle.json').read_text(encoding='utf-8'))
            except UnicodeDecodeError:
                review = json.loads((root/'review-authority-oracle.json').read_text(encoding='gbk'))
            checks.update(exact_candidate_accepted=review.get('candidate_accepted') is True,
                local_runtime_commit_only=review.get('local_runtime_commit_observed') is True,
                remote_refs_unchanged=review.get('remote_unchanged') is True,
                no_delivery_after_acceptance=review.get('no_delivery_authorization') is True)
        if identity == 'GC-EX-14':
            fault_path = root/'worker-interruption.json'
            fault = json.loads(fault_path.read_text(encoding='utf-8')) if fault_path.exists() else {}
            attempt_path = root/args.native_attempt_record
            attempt = json.loads(attempt_path.read_text(encoding='utf-8')) if attempt_path.exists() else {}
            effects = attempt.get('effects', [])
            writes = [item for item in effects if item['tool_identity'] == 'file.write']
            checks.update(actual_worker_interruption=fault.get('fault') == 'DECLARED_WORKER_PROCESS_LOSS'
                    and fault.get('in_flight_tool_effect') is False,
                same_attempt_new_lease_epoch=attempt.get('state',{}).get('attempt_id') == fault.get('attempt_id')
                    and attempt.get('state',{}).get('worker_epoch',0) > fault.get('lease_before',{}).get('epoch',0),
                automatic_same_attempt_resume=any(item.get('attempt_id') == fault.get('attempt_id')
                    and item.get('resume_count',0) >= 1 for item in state.get('queue', [])),
                no_duplicate_source_effect=len(writes) == 1 and writes[0]['condition'] == 'SETTLED',
                interrupted_inference_preserved=any(item.get('kind') == 'INFERENCE'
                    and item.get('condition') == 'INTERRUPTED' for item in attempt.get('steps',[])),
                native_refinement_recovered=any(item.get('failure_family') == 'WORKER_LEASE_LOST'
                    and item.get('final_result') == 'LOCAL_OBLIGATION_RECOVERED'
                    for item in state.get('refinement',{}).get('events',[])))
        if identity == 'GC-EX-04':
            # Compare with the source Git object actually acquired by Watt.
            # Windows may checkout the fixture with CRLF even though its Git
            # object and the Linux production workspace contain LF bytes.
            fixture = (Path(__file__).resolve().parents[3]/'.spg/stability-runtime'
                /'fixture-sources/large-file')
            baseline = subprocess.check_output((
                'git', '-C', str(fixture), 'show', 'HEAD:web/index.html'))
            attempt_record = root/args.native_attempt_record
            attempt = json.loads(attempt_record.read_text(encoding='utf-8')) if attempt_record.exists() else {}
            writes = [effect for effect in attempt.get('effects', [])
                if effect['tool_identity'] == 'file.write' and effect['condition'] == 'SETTLED']
            checks.update(source_exceeds_32k=len(baseline) > 32768,
                unrelated_bytes_preserved=body.encode() == baseline.replace('开始使用'.encode(), '立即体验'.encode()),
                exact_bounded_replace=len(writes) == 1 and all(
                    'old_text' in effect['semantic_input'] and 'new_text' in effect['semantic_input']
                    and 'content' not in effect['semantic_input'] for effect in writes))
    elif identity in {'GC-EX-03','GC-EX-05'}:
        checks.update(browser_dialog_oracle=(root/args.browser_record).exists())
        if checks['browser_dialog_oracle']:
            checks['actual_cancel_closes_dialog']=json.loads((root/args.browser_record).read_text(encoding='utf-8')).get('cancel_closes') is True
        if identity == 'GC-EX-05':
            attempt = json.loads((root/args.native_attempt_record).read_text(encoding='utf-8'))
            receipts = {item['delivery_id']: item for step in attempt.get('steps', [])
                for item in step.get('request_payload', {}).get('previous_results', [])}
            checks.update(actual_no_effect_tool_failure=any(item['condition'] == 'FAILED'
                    and item.get('output', {}).get('error_type') == 'CAPABILITY_PATH_INVALID'
                    and item['output'].get('effect_observed') is False for item in receipts.values()),
                bounded_source_repair=paths == ['web/app.js'],
                autonomous_refinement_signal=any(event.get('repairability') == 'AUTONOMOUSLY_REPAIRABLE'
                    and event.get('affected_component') == 'native-tool-host/file.read'
                    and event.get('observed_reality', {}).get('failure_code') == 'CAPABILITY_PATH_INVALID'
                    for event in state.get('refinement', {}).get('events', [])))
    elif identity == 'GC-EX-08':
        browser = json.loads((root/args.browser_record).read_text(encoding='utf-8'))
        choice = json.loads((root/'human-clarification.json').read_text(encoding='utf-8'))
        # Comments carry no CSS selector or style authority. Inspect the actual
        # added rules, keeping every historical oracle result immutable.
        added_css = re.sub(r'/\*.*?\*/', '', '\n'.join(added), flags=re.S)
        checks.update(header_only_prominent=browser.get('header_only_prominent') is True,
            one_genuine_scope_choice=choice.get('question_count') == 1,
            only_presentational_source=paths == ['web/styles.css'],
            selected_button_scoped=bool(added) and not removed
                and bool(re.findall(r'([^{}]+)\{[^{}]*\}', added_css))
                and all(all(selector.strip().startswith('#header-login')
                    for selector in block.split(','))
                    for block in re.findall(r'([^{}]+)\{[^{}]*\}', added_css)))
    elif identity == 'GC-IP-06':
        browser = json.loads((root/args.browser_record).read_text(encoding='utf-8'))
        database = json.loads((root/args.database_record).read_text(encoding='utf-8'))
        checks.update(dynamic_metrics_match_actual_records=browser.get('dynamic_metrics_after_new_business_records') is True,
            api_and_database_agree=database.get('api_and_database_agree') is True,
            only_available_domains=set(database.get('expected_metrics', {})) == {'users','customers','orders','total'})
    elif identity == 'GC-IP-07':
        browser = json.loads((root/args.browser_record).read_text(encoding='utf-8'))
        database = json.loads((root/args.database_record).read_text(encoding='utf-8'))
        choice = json.loads((root/'human-clarification.json').read_text(encoding='utf-8'))
        checks.update(one_genuine_domain_choice=choice.get('question_count') == 1,
            name_and_email_search=browser.get('name_search_selected_user_only') is True
                and browser.get('email_search_selected_user_only') is True,
            empty_result=browser.get('no_matches_empty') is True,
            unrelated_domain_unchanged=browser.get('customer_domain_unchanged') is True,
            api_search_matches_actual_database=database.get('api_and_database_agree') is True
                and database.get('api_name_and_email_search') is True
                and database.get('empty_search_has_no_results') is True,
            no_unrequested_product_surfaces=all(path in {'server.py','web/index.html','web/app.js','web/styles.css'} for path in paths))
    elif identity in {'GC-IP-05','GC-IP-08'}:
        browser = json.loads((root/args.browser_record).read_text(encoding='utf-8'))
        database = json.loads((root/args.database_record).read_text(encoding='utf-8'))
        checks['api_and_database_agree'] = database.get('api_and_database_agree') is True
        if identity == 'GC-IP-05':
            checks.update(feedback_form_submitted=browser.get('feedback_form_submitted') is True,
                reload_shows_persisted_feedback=browser.get('reload_shows_persisted_feedback') is True,
                existing_visibility_model=browser.get('team_visibility_in_existing_model') is True,
                actual_feedback_persisted=any(row.get('message') == 'Golden persisted user feedback'
                    for row in database.get('sqlite_rows', [])))
        else:
            checks.update(customer_create_and_edit=browser.get('create_form_submitted') is True
                    and browser.get('edit_form_submitted') is True,
                reload_restores_edit=browser.get('reload_preserves_customer_edit') is True,
                actual_customer_persisted=any(row.get('name') == 'Golden managed edited customer'
                    and row.get('email') == 'managed-edited@example.invalid' for row in database.get('sqlite_rows', [])))
        checks['no_extra_product_surfaces'] = all(path in {'server.py','web/index.html','web/app.js','web/styles.css'}
            or (path.startswith('migrations/') and path.endswith('.sql')) for path in paths)
    elif identity == 'GC-IP-03':
        browser = json.loads((root/args.browser_record).read_text(encoding='utf-8'))
        database = json.loads((root/args.database_record).read_text(encoding='utf-8'))
        checks.update(actual_order_fields=browser.get('actual_order_fields') == ['customer_id','total','status'],
            grounded_status_model=browser.get('open_status_input_preserved') is True,
            no_invented_logistics_refunds=browser.get('no_logistics_or_refunds') is True,
            actual_management_loop=browser.get('create_form_submitted') is True
                and browser.get('reload_restores_order') is True
                and browser.get('edit_form_submitted') is True
                and browser.get('reload_restores_edit') is True,
            api_and_database_agree=database.get('api_and_database_agree') is True,
            real_created_order=any(row.get('customer_id') == 1 and row.get('total') == 75
                and row.get('status') == 'open' for row in database.get('sqlite_rows', [])),
            no_extra_product_surfaces=all(path in {'server.py','web/index.html','web/app.js',
                'web/styles.css','web/orders.html','web/orders.js'} for path in paths))
    elif identity == 'GC-EX-10':
        attempt_record = root/args.native_attempt_record
        attempt = json.loads(attempt_record.read_text(encoding='utf-8')) if attempt_record.exists() else {}
        results = {result['delivery_id']: result for step in attempt.get('steps', [])
            for result in step.get('request_payload', {}).get('previous_results', [])}
        compilation = [result for result in results.values()
            if result['tool_identity'] in {'build.run', 'process.run'}
            and result.get('output', {}).get('argv', [])[1:3] == ['-m', 'py_compile']]
        checks.update(compiler_failure_observed=any(result['condition'] == 'FAILED'
                and 'SyntaxError' in result['output'].get('stderr', '') for result in compilation),
            successful_native_build=any(result['condition'] == 'SETTLED'
                and result['output'].get('returncode') == 0 for result in compilation),
            in_scope_source_repair=paths == ['server.py'] and len(added) == len(removed) == 1)
    elif identity in {'GC-EX-09', 'GC-IP-04'}:
        browser_record = root/args.browser_record
        database_record = root/args.database_record
        browser = json.loads(browser_record.read_text(encoding='utf-8')) if browser_record.exists() else {}
        database = json.loads(database_record.read_text(encoding='utf-8')) if database_record.exists() else {}
        checks['api_and_real_database_agree'] = database.get('api_and_database_agree') is True
        if identity == 'GC-EX-09':
            checks.update(real_active_and_inactive_rows_visible=browser.get('actual_active_and_inactive_rows') is True,
                status_is_backend_data=any(row.get('name') == 'Golden inactive user' and row.get('status') == 'inactive'
                    for row in database.get('sqlite_rows', [])))
            plan = state['work'].get('production_plan_runtime') or {}
            nodes = plan.get('pwus', [])
            checks['verified_multiple_surfaces_and_join'] = (len(nodes) >= 3
                and all(node['state'] == 'VERIFIED' for node in nodes)
                and any(node['kind'] == 'JOIN' for node in nodes)
                and plan.get('integrated_revision') == meta['repository_revision'])
        else:
            checks.update(edit_form_submitted=browser.get('edit_form_submitted') is True,
                reload_preserves_profile=browser.get('reload_preserves_profile_name') is True
                    and browser.get('saved_email_visible_in_screenshot') is True,
                persisted_profile=any(row.get('name') == 'Golden edited profile'
                    and row.get('email') == 'golden-profile@example.invalid' for row in database.get('sqlite_rows', [])),
                existing_identity_boundary_preserved=all(path in {'web/app.js', 'web/index.html', 'web/styles.css'} for path in paths))
    elif identity == 'GC-IP-01':
        browser_record = root/args.browser_record
        browser = json.loads(browser_record.read_text(encoding='utf-8')) if browser_record.exists() else {}
        checks.update(about_page_reachable=browser.get('about_page_reachable') is True,
            distinct_about_page=browser.get('distinct_about_page') is True,
            home_content_preserved=browser.get('home_unrelated_content_unchanged') is True,
            home_navigation_to_page=browser.get('home_has_about_navigation') is True,
            no_unsupported_content_claims=browser.get('unsupported_contact_reference') is False)
    elif identity in {'GC-EX-13', 'GC-IP-02'}:
        browser_record = root/args.browser_record
        database_record = root/args.database_record
        browser = json.loads(browser_record.read_text(encoding='utf-8')) if browser_record.exists() else {}
        database = json.loads(database_record.read_text(encoding='utf-8')) if database_record.exists() else {}
        checks['api_and_real_database_agree'] = database.get('api_and_database_agree') is True
        rows = database.get('sqlite_rows', [])
        if identity == 'GC-EX-13':
            checks.update(create_form_submitted=browser.get('create_form_submitted') is True,
                edit_form_submitted=browser.get('edit_form_submitted') is True,
                reload_preserves_edit=browser.get('reload_restores_edited_note') is True,
                persisted_edited_note=any(row.get('name') == 'Golden note customer'
                    and row.get(browser.get('observed_note_field', 'notes')) == 'Golden persisted edited note' for row in rows),
                migration_present=any(path.endswith('.sql') for path in paths))
            plan = state['work'].get('production_plan_runtime') or {}
            nodes = plan.get('pwus', [])
            checks['verified_three_surfaces_and_join'] = (len(nodes) >= 4
                and all(node['state'] == 'VERIFIED' for node in nodes)
                and any(node['kind'] == 'JOIN' for node in nodes)
                and plan.get('integrated_revision') == meta['repository_revision'])
        else:
            checks.update(form_submitted=browser.get('form_submitted') is True,
                reload_preserves_record=browser.get('reload_preserves_collected_user') is True,
                user_model_persistence=any(row.get('name') == 'Golden collected user'
                    and row.get('email') == 'golden-collection@example.invalid' for row in rows))
    else:
        checks['case_business_oracle']=None
    result={'case':identity,'trial':journey['trial'],'checks':checks,
        'status':'PASS' if all(value is True for value in checks.values()) else
            ('NOT_EVALUATED' if any(value is None for value in checks.values()) else 'FAIL'),
        'candidate_revision':meta['repository_revision'],'candidate_tree':meta['tree'],
        'browser_evidence_record':args.browser_record,'persistence_evidence_record':args.database_record,'historical_runtime_evidence':args.historical_runtime,
        'changed_paths':paths,'preview_endpoint':preview['session']['endpoint'],
        'human_acceptance':'PENDING','manual_rescue_actions':[]}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__': main()
