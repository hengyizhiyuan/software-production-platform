"""Recover only the two already-successful C3 Owner snapshot files; no recapture."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path
ROOT=Path('/data/watt/c3-semantic-convergence-20261009')
RUN='20261009T114024248251Z-160bdaceae6d4e11ab9cfd1726340f5b'
API='watt-c3-api-20261009'
WORK='24d9cc2d-52a8-5d27-b38a-e49c3f73394c'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-read-only',action='store_true');args=parser.parse_args()
    if not args.execute_read_only:
        print(json.dumps({'prepared_only':True,'docker_contacted':False}));return 0
    os.umask(0o077)
    spec=importlib.util.spec_from_file_location('c3_export_helpers',str(ROOT/'c3_export_owner_records.py'))
    helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
    private=ROOT/'private'/('owner-export-'+RUN)
    runner=json.loads((private/'runner-raw.json').read_text(encoding='utf-8'))
    info=json.loads(runner['stdout'])
    if runner['exit_code']!=0 or info.get('work_id')!=WORK or info.get('export_complete') is not True:
        raise ValueError('EXACT_SUCCESSFUL_SAVED_COLLECTOR_REQUIRED')
    runtime=json.loads(helpers.invoke(['docker','inspect',API]).decode())[0]
    expected=json.loads((ROOT/'evidence/driver-runtime-identity.json').read_text(encoding='utf-8'))
    if runtime['Image']!=expected['image_id'] or runtime['Config']['User']!='10001:10001':
        raise ValueError('EXACT_EXISTING_C3_API_REQUIRED')
    transfer=[]
    for name in (info['raw_private_file'],info['summary_private_file']):
        if Path(name).name!=name or not name.endswith(('.json',)):
            raise ValueError('EXACT_FILE_NAME_REQUIRED')
        source='/tmp/c3-owner-export-'+RUN+'/private/canonical/'+name
        command=['docker','exec','--user','10001:10001',API,'python','-c',
            'import sys;from pathlib import Path;sys.stdout.buffer.write(Path(sys.argv[1]).read_bytes())',source]
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if result.returncode:
            helpers.exclusive_json(private/('recovery-'+name+'-error.json'),
                {'exit_code':result.returncode,'private_stderr':result.stderr.decode('utf-8',errors='replace')},private=True)
            raise RuntimeError('EXACT_SAVED_FILE_READ_FAILED')
        raw=result.stdout;payload=json.loads(raw)
        if payload.get('work_id')!=WORK:raise ValueError('SAVED_WORK_IDENTITY_MISMATCH')
        digest=hashlib.sha256(raw).hexdigest()
        if name==info['raw_private_file'] and digest!=info['raw_private_sha256']:
            raise ValueError('ORIGINAL_CAPTURE_HASH_MISMATCH')
        target=private/name
        if target.exists():
            if target.read_bytes()!=raw:raise ValueError('PRESERVE_EXISTING_PRIVATE_CAPTURE')
        else:
            fd=os.open(str(target),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.chmod(str(target),0o600)
        transfer.append({'file':name,'raw_sha256':digest,'bytes':len(raw)})
    canonical=json.loads((private/info['raw_private_file']).read_text(encoding='utf-8'))
    public=ROOT/'evidence'/('owner-export-recovered-'+RUN)
    if public.exists():raise ValueError('PRESERVE_EXISTING_PUBLIC_RECOVERY')
    public.mkdir(mode=0o750)
    values=helpers.known_secrets();redactions=0
    for item in transfer:
        content=(private/item['file']).read_text(encoding='utf-8')
        for value in values:redactions+=content.count(value);content=content.replace(value,'[REDACTED]')
        payload=json.loads(content)
        payload['public_release']={'method':'known C3 credential values removed in memory','private_root_released':False,
            'evidence_level':'E1_SCOPED_OWNER_OBSERVATIONS','qualification_claim':'NO_PASS_OR_AUTHORITY_INFERRED',
            'unknown_sensitive_values_not_claimed_absent':True,'recovery_not_new_capture':True}
        helpers.exclusive_json(public/item['file'],payload)
        if any(value in (public/item['file']).read_text(encoding='utf-8') for value in values):
            raise ValueError('KNOWN_SECRET_PUBLICATION_REJECTED')
    receipt={'schema':'c3-saved-owner-snapshot-recovery-v1','work_id':WORK,'recovered_at_utc':helpers.now(),
        'original_collector_capture_started_at_utc':canonical['started_at_utc'],
        'original_database_snapshot':canonical['database_snapshot'],
        'original_collector_exit_code':runner['exit_code'],'original_export_complete':info['export_complete'],
        'original_raw_snapshot_sha256':info['raw_private_sha256'],'files':transfer,
        'root_private_directory':str(private),'private_file_mode':'0600','known_credential_redactions':redactions,
        'failure_boundary':'host docker cp after successful existing collector output; original error stderr was not retained',
        'historical_docker_cp_error_message':'UNKNOWN_NOT_RETAINED','transfer_method':'read exact existing files via docker exec Python read_bytes; no directory copy',
        'recaptured_database_or_owners':False,'model_calls':0,'work_created_resumed_or_changed':False,
        'qualification_claim':'ORIGINAL_SCOPED_OWNER_OBSERVATIONS_ONLY_NO_WORK_PASS',
        'recovery_harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    helpers.exclusive_json(public/'recovery-execution.json',receipt)
    print(json.dumps({'recovered':True,'work_id':WORK,'public_directory':str(public),'raw_files_transferred':len(transfer),
        'original_capture_preserved':True,'recaptured':False,'sensitive_values_output':False,'known_redactions':redactions}))
    return 0


if __name__=='__main__':
    try:sys.exit(main())
    except Exception as failure:
        print(json.dumps({'recovered':False,'error_type':type(failure).__name__,'raw_error_omitted':True}),file=sys.stderr)
        sys.exit(2)
