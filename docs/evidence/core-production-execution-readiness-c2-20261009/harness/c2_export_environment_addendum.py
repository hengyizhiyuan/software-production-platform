#!/usr/bin/env python3
"""C2 passive WHERE-owner addendum to an existing private DB snapshot."""
import argparse, hashlib, json, os, sys, uuid
from datetime import datetime, timezone
from pathlib import Path


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--canonical-snapshot',required=True,type=Path)
    parser.add_argument('--private-output-dir',required=True,type=Path)
    args=parser.parse_args()
    if 'private' not in args.private_output_dir.resolve().parts:
        raise ValueError('PRIVATE_OUTPUT_DIRECTORY_REQUIRED')
    raw=args.canonical_snapshot.read_bytes()
    source=json.loads(raw)
    if (source.get('schema')!='c2-work-canonical-private-snapshot-v1'
        or source.get('export_error')
        or source.get('database_snapshot',{}).get('database_name')!='spg_c2_qualification_20261009'
        or source.get('database_snapshot',{}).get('read_only')!='on'):
        raise ValueError('EXACT_COMPLETED_C2_SNAPSHOT_REQUIRED')
    wid=str(uuid.UUID(source['work_id']))
    attempts={str(uuid.UUID(row['id'])):row['work_unit_id'] for row in source['datasets']['execution_attempts']['rows']}
    from spg.config import Settings
    root=Settings().native_executor_production_environment_store_root.resolve()
    files=[];missing=[]
    def read(path):
        path=path.resolve()
        if not path.is_relative_to(root):raise ValueError('OWNER_FILE_OUTSIDE_ROOT')
        relative=str(path.relative_to(root))
        if not path.is_file():
            missing.append({'relative_path':relative,'status':'MISSING_AT_THIS_FILESYSTEM_OBSERVATION_HISTORY_UNKNOWN'})
            return None
        data=path.read_bytes();payload=json.loads(data)
        files.append({'relative_path':relative,'sha256':hashlib.sha256(data).hexdigest(),'payload':payload})
        return payload
    started=datetime.now(timezone.utc).isoformat()
    observed=[]
    for attempt,pwu in attempts.items():
        binding=read(root/'native-execution-bindings'/(attempt+'.json'))
        if binding is None:continue
        if str(binding['work_id'])!=wid or str(binding['pwu_id'])!=str(pwu) or str(binding['attempt_id'])!=attempt:
            raise ValueError('WHERE_OWNER_SCOPE_MISMATCH')
        workspace=binding['workspace'];environment=binding['environment']
        if workspace['work_id']!=wid or environment['work_id']!=wid or environment['workspace_id']!=workspace['id']:
            raise ValueError('WHERE_OWNER_LINEAGE_MISMATCH')
        workspace_id=str(uuid.UUID(workspace['id']));environment_id=str(uuid.UUID(environment['id']))
        read(root/'workspaces'/(workspace_id+'.json'))
        directory=root/'environments'/environment_id
        current=read(directory/'current.json')
        for folder in ('versions','transitions'):
            matches=sorted((directory/folder).glob('*.json'))
            if len(matches)>1000:raise ValueError('OWNER_HISTORY_LIMIT')
            for path in matches:read(path)
        observed.append({'attempt_id':attempt,'pwu_id':pwu,'workspace_id':workspace_id,'environment_id':environment_id,
                         'binding_environment_state':environment.get('lifecycle_state'),
                         'current_environment_state':None if current is None else current.get('lifecycle_state'),
                         'prepared_at':binding['prepared_workspace'].get('prepared_at'),
                         'binding_created_at':binding.get('created_at')})
    output={'schema':'c2-where-owner-private-addendum-v1','work_id':wid,
            'source_canonical_snapshot_sha256':hashlib.sha256(raw).hexdigest(),
            'source_database_snapshot':source['database_snapshot'],
            'source_runtime_identity':source['driver_state']['runtime_identity'],
            'started_at_utc':started,'completed_at_utc':datetime.now(timezone.utc).isoformat(),
            'consistency':'FILESYSTEM_AFTER_PREVIOUS_DB_SNAPSHOT_NOT_ATOMIC',
            'public_release':'ROOT_REDACTION_REQUIRED','files':files,'missing_at_observation':missing}
    args.private_output_dir.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(args.private_output_dir,0o700)
    path=args.private_output_dir/(uuid.uuid4().hex+'-where-owner-addendum.json')
    data=(json.dumps(output,sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'private_file':str(path),'sha256':hashlib.sha256(data).hexdigest(),'file_count':len(files),
                      'missing_observation_count':len(missing),'observed':observed,'public_release':'ROOT_REDACTION_REQUIRED'}))


if __name__=='__main__':
    try:main()
    except Exception as failure:
        print(json.dumps({'error_type':type(failure).__name__,'raw_error_omitted':True}),file=sys.stderr)
        sys.exit(2)
