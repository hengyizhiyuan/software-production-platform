"""Business evidence after review readiness, separate from Human Acceptance.

Only bounded read-only source/diff/served observations are automated here.
Interactive and persistence cases require their actual Browser/API oracle evidence;
absence is reported as NOT_EVALUATED rather than converted into a green score.
"""
import argparse
from html.parser import HTMLParser
import json
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--base',required=True)
    parser.add_argument('--env-file',type=Path,required=True)
    args=parser.parse_args()
    root=args.directory
    output=root/'business-oracle.json'
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
            one_source_file=len(paths)==1, one_added_line=len(added)==1,
            zero_removed_lines=not removed)
    elif identity in {'GC-EX-02','GC-EX-04','GC-EX-14','GC-EX-15'}:
        checks.update(new_label='立即体验' in body, old_label='开始使用' not in body,
            one_source_file=len(paths)==1, minimal_source_diff=len(added)==1 and len(removed)==1)
    elif identity in {'GC-EX-03','GC-EX-05'}:
        checks.update(browser_dialog_oracle=(root/'browser-oracle.json').exists())
        if checks['browser_dialog_oracle']:
            checks['actual_cancel_closes_dialog']=json.loads((root/'browser-oracle.json').read_text()).get('cancel_closes') is True
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
