"""Business evidence after review readiness, separate from Human Acceptance.

Only bounded read-only source/diff/served observations are automated here.
Interactive and persistence cases require their actual Browser/API oracle evidence;
absence is reported as NOT_EVALUATED rather than converted into a green score.
"""
import argparse
from html.parser import HTMLParser
import json
import re
from pathlib import Path
import urllib.request


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
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--record-name', default='business-oracle.json',
        help='A new evidence identity; existing oracle records are never replaced')
    args=parser.parse_args()
    root=args.directory
    if Path(args.record_name).name != args.record_name:
        raise SystemExit('Evidence record name must be a single filename')
    output=root/args.record_name
    if output.exists(): raise SystemExit('Oracle record already exists; do not rewrite historical results')
    state=json.loads((root/'latest.json').read_text())
    journey=json.loads((root/'journey.json').read_text())
    env=dict(line.split('=',1) for line in args.env_file.read_text().splitlines() if '=' in line)
    def read(path,payload=None):
        request=urllib.request.Request(args.base+path,
            data=None if payload is None else json.dumps(payload).encode(),headers={
                'Authorization':'Bearer '+env['SPG_OPERATOR_TOKEN'],'Content-Type':'application/json'})
        return urllib.request.urlopen(request,timeout=20).read().decode()
    work_id=state['work']['work_id']; prefix='/api/works/'+work_id
    meta=json.loads(read(prefix+'/candidate-preview',{}))
    diff=read(prefix+'/candidate-code-diff/'+meta['candidate_fingerprint'])
    (root/'candidate.diff').write_text(diff)
    preview=json.loads(read(prefix+'/functional-preview'))
    body=urllib.request.urlopen(preview['session']['endpoint'],timeout=20).read().decode()
    (root/'served.html').write_text(body)
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
        if identity == 'GC-EX-04':
            baseline = (Path(__file__).resolve().parents[3]/'.spg/stability-runtime'
                /'fixture-sources/large-file/web/index.html').read_bytes()
            attempt_record = root/'native-attempt.json'
            attempt = json.loads(attempt_record.read_text()) if attempt_record.exists() else {}
            writes = [effect for effect in attempt.get('effects', [])
                if effect['tool_identity'] == 'file.write' and effect['condition'] == 'SETTLED']
            checks.update(source_exceeds_32k=len(baseline) > 32768,
                unrelated_bytes_preserved=body.encode() == baseline.replace('开始使用'.encode(), '立即体验'.encode()),
                exact_bounded_replace=len(writes) == 1 and all(
                    'old_text' in effect['semantic_input'] and 'new_text' in effect['semantic_input']
                    and 'content' not in effect['semantic_input'] for effect in writes))
    elif identity in {'GC-EX-03','GC-EX-05'}:
        checks.update(browser_dialog_oracle=(root/'browser-oracle.json').exists())
        if checks['browser_dialog_oracle']:
            checks['actual_cancel_closes_dialog']=json.loads((root/'browser-oracle.json').read_text()).get('cancel_closes') is True
    elif identity == 'GC-EX-10':
        attempt_record = root/'native-attempt.json'
        attempt = json.loads(attempt_record.read_text()) if attempt_record.exists() else {}
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
        browser_record = root/'browser-oracle.json'
        database_record = root/'persistence-oracle.json'
        browser = json.loads(browser_record.read_text()) if browser_record.exists() else {}
        database = json.loads(database_record.read_text()) if database_record.exists() else {}
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
        browser_record = root/'browser-oracle.json'
        browser = json.loads(browser_record.read_text()) if browser_record.exists() else {}
        checks.update(about_page_observed=browser.get('about_page_reachable') is True,
            no_unsupported_content_claims=browser.get('unsupported_contact_reference') is False)
    elif identity in {'GC-EX-13', 'GC-IP-02'}:
        browser_record = root/'browser-oracle.json'
        database_record = root/'persistence-oracle.json'
        browser = json.loads(browser_record.read_text()) if browser_record.exists() else {}
        database = json.loads(database_record.read_text()) if database_record.exists() else {}
        checks['api_and_real_database_agree'] = database.get('api_and_database_agree') is True
        rows = database.get('sqlite_rows', [])
        if identity == 'GC-EX-13':
            checks.update(create_form_submitted=browser.get('create_form_submitted') is True,
                edit_form_submitted=browser.get('edit_form_submitted') is True,
                reload_preserves_edit=browser.get('reload_restores_edited_note') is True,
                persisted_edited_note=any(row.get('name') == 'Golden note customer'
                    and row.get('notes') == 'Golden persisted edited note' for row in rows),
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
        'changed_paths':paths,'preview_endpoint':preview['session']['endpoint'],
        'human_acceptance':'PENDING','manual_rescue_actions':[]}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__': main()
