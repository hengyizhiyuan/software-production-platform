"""Read only the two new C3 application logs; private raw, scrubbed error excerpts."""
import argparse, hashlib, importlib.util, json, os, re, subprocess, uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path('/data/watt/c3-semantic-convergence-20261009/retry-1')
WORK='048189aa-0613-5307-b6f4-c430e7977f93'
IMAGE='sha256:6f8d9b3a27e7e2452097a77427115df6e09b9a03276eb72d0170a66160e0578f'
ROLES=('watt-c3-retry1-api-20261009','watt-c3-retry1-coordinator-20261009')
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-read-only',action='store_true');args=parser.parse_args()
    if not args.execute_read_only:
        print(json.dumps({'prepared':True,'executed':False}));return
    spec=importlib.util.spec_from_file_location('c3_export_helpers',str(ROOT/'c3_export_owner_records.py'))
    helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
    now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex
    private=ROOT/'private'/('g0-stop-logs-'+run);public=ROOT/'evidence'/('g0-stop-logs-'+run)
    private.mkdir(mode=0o700);public.mkdir(mode=0o750)
    secrets=helpers.known_secrets();records=[]
    for role in ROLES:
        inspect=subprocess.run(['docker','inspect','--format','{{json .Id}} {{json .Image}} {{json .Config.User}}',role],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if inspect.returncode:
            helpers.exclusive_json(private/(role+'-inspect-error.json'),{'exit_code':inspect.returncode,'stderr':inspect.stderr.decode('utf-8',errors='replace')},private=True)
            raise RuntimeError('C3_STOP_LOG_INSPECT_FAILED')
        identity=[json.loads(part) for part in inspect.stdout.decode().strip().split(' ')]
        if identity[1]!=IMAGE or identity[2] not in ('10001','10001:10001'):
            raise ValueError('C3_STOP_LOG_IDENTITY_REJECTED')
        result=subprocess.run(['docker','logs','--timestamps','--since','2026-10-09T12:55:00Z','--until',now,role],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        helpers.exclusive_json(private/(role+'-raw.json'),{'command_ordinal':len(records)+1,'container_id':identity[0],'image':identity[1],'user':identity[2],'exit_code':result.returncode,'stdout':result.stdout.decode('utf-8',errors='replace'),'stderr':result.stderr.decode('utf-8',errors='replace')},private=True)
        if result.returncode:raise RuntimeError('C3_STOP_LOG_READ_FAILED')
        content=result.stdout.decode('utf-8',errors='replace')+'\n'+result.stderr.decode('utf-8',errors='replace')
        redactions=0
        for value in secrets:
            redactions+=content.count(value);content=content.replace(value,'[REDACTED]')
        lines=content.splitlines();indices=set()
        for index,line in enumerate(lines):
            if WORK in line or any(word in line for word in ('Traceback (most recent call last)', 'ERROR', 'Exception', 'Error:', 'BLOCKED','PROJECTION_UNRESOLVED')):
                indices.update(range(max(0,index-3),min(len(lines),index+55)))
        excerpts=[{'line':index+1,'text':lines[index]} for index in sorted(indices)]
        records.append({'role':role,'container_id':identity[0],'image':identity[1],'user':identity[2],'total_lines':len(lines),'error_or_work_excerpts':excerpts,'known_redactions':redactions})
    payload={'schema':'c3-existing-g0-stop-log-observation-v1','work_id':WORK,'application_revision':'91f5dbc9906d1f857113736981517c1091ec52ae','control_harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'captured_at':now,'log_since':'2026-10-09T12:55:00Z','log_until':now,'evidence_level':'E1_SCOPED_APPLICATION_LOG_OBSERVATION','logs_do_not_prove_full_effect_audit':True,'known_value_redaction_only':True,'unknown_secrets_not_claimed_absent':True,'private_raw_retained':True,'records':records}
    helpers.exclusive_json(public/'stop-log-observation.json',payload)
    print(json.dumps({'captured':True,'work_id':WORK,'public_directory':str(public),'roles':list(ROLES),'record_counts':[len(row['error_or_work_excerpts']) for row in records],'private_file_mode':'0600','sensitive_values_output':False}))
if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'captured':False,'error_type':type(error).__name__,'sensitive_values_output':False}));raise SystemExit(1)