"""Prepare/passively export one existing C3 Work; never create/resume/authorize it.

Host script supports Python 3.6. SQL/Owner collector runs on actual image Python3.12.
Raw output stays under the C3 private directory mode0600. Explicit execution is
required; creating this file or invoking it without the flag does not contact Docker.
"""
import argparse, base64, hashlib, json, os, re, subprocess, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

ROOT=Path('/data/watt/c3-semantic-convergence-20261009')
E=ROOT/'evidence'; P=ROOT/'private'
SCHEMA='c3-read-only-owner-export-execution-v1'


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')


def invoke(command, data=None):
    result=subprocess.run(command,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if result.returncode:
        # All failure detail stays private. Never print Docker ENV or raw SQL errors.
        raise RuntimeError('READ_ONLY_EXPORT_COMMAND_FAILED')
    return result.stdout


def exclusive_json(path,value,private=False):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700 if private else 0o750)
    raw=(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n').encode('utf-8')
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600 if private else 0o640)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest()


def known_secrets():
    values=set()
    # Same C2 value-based redaction, confined to this new isolated private root.
    def add(name,value):
        if isinstance(value,str) and value and any(part in name.upper() for part in ('PASSWORD','TOKEN','API_KEY','ACCESS_KEY','SECRET','DATABASE_URL','DSN')):
            values.add(value)
            if name.upper().endswith(('DATABASE_URL','DSN')):
                try:
                    password=urlsplit(value).password
                    if password:values.update((password,unquote(password)))
                except ValueError:pass
    for envfile in P.glob('*.env'):
        for line in envfile.read_text(encoding='utf-8').splitlines():
            if '=' in line:
                name,value=line.split('=',1);add(name,value)
    credentials=json.loads((P/'credentials.json').read_text(encoding='utf-8'))
    for name,value in credentials.items():add(name,value)
    user=credentials.get('gitea_user'); password=credentials.get('gitea_password')
    if isinstance(user,str) and isinstance(password,str):
        values.add(base64.b64encode((user+':'+password).encode()).decode())
    originals=list(values)
    values.update(quote(value,safe='') for value in originals)
    return sorted((value for value in values if value),key=len,reverse=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-read-only',action='store_true')
    args=parser.parse_args()
    if not args.execute_read_only:
        print(json.dumps({'schema':SCHEMA,'prepared_only':True,'docker_or_database_contacted':False,'work_created':False}))
        return 0
    os.umask(0o077)
    freeze=json.loads((ROOT/'frozen-inputs.json').read_text(encoding='utf-8'))
    hashes=freeze['control_harness_sha256']
    for name in ('c3_export_work_snapshot.py','c3_export_owner_records.py'):
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=hashes.get(name):
            raise ValueError('EXACT_FROZEN_EXPORT_HARNESS_REQUIRED')
    state_path=E/'normal-entry-state.json'
    state_raw=state_path.read_bytes();state=json.loads(state_raw)
    wid=str(uuid.UUID(state['work_id']))
    identity=state['runtime_identity']
    if (state.get('schema')!='c3-normal-entry-state-v1' or identity.get('qualification')!='C3'
        or identity.get('isolated') is not True or identity.get('database_name')!='spg_c3_qualification_20261009'
        or not re.fullmatch(r'[0-9a-f]{40}',identity.get('source_revision',''))
        or not re.fullmatch(r'sha256:[0-9a-f]{64}',identity.get('image_id',''))):
        raise ValueError('EXACT_EXISTING_C3_STATE_REQUIRED')
    api=identity['api_service']
    if api!='watt-c3-api-20261009':raise ValueError('EXACT_ISOLATED_API_REQUIRED')
    # inspect is consumed only in memory, before any copying; Config.Env is never output.
    runtime=json.loads(invoke(['docker','inspect',api]).decode())[0]
    labels=runtime.get('Config',{}).get('Labels') or {}
    if (runtime['Image']!=identity['image_id'] or labels.get('watt.production')!='false'
        or labels.get('watt.qualification')!='C3-semantic-convergence'
        or runtime['Config']['User']!='10001:10001' or runtime['State']['Running'] is not True):
        raise ValueError('ACTUAL_API_IMAGE_OR_ISOLATION_MISMATCH')
    actual_environment=dict(value.split('=',1) for value in runtime['Config'].get('Env',[]) if '=' in value)
    if actual_environment.get('SPG_RUNTIME_REVISION')!=identity['source_revision']:
        raise ValueError('ACTUAL_API_CODE_REVISION_MISMATCH')
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex
    tmp='/tmp/c3-owner-export-'+run_id
    target=P/('owner-export-'+run_id); public=E/('owner-export-'+run_id)
    if target.exists() or public.exists():raise ValueError('PRESERVE_EXISTING_EXPORT')
    script=(ROOT/'c3_export_work_snapshot.py').read_bytes()
    create="import os,sys;from pathlib import Path;p=Path(sys.argv[1]);p.mkdir(mode=0o700);f=p/'collector.py';f.write_bytes(sys.stdin.buffer.read());f.chmod(0o600)"
    invoke(['docker','exec','-i','--user','10001:10001',api,'python','-c',create,tmp],script)
    copy_state="import sys;from pathlib import Path;p=Path(sys.argv[1])/'state.json';p.write_bytes(sys.stdin.buffer.read());p.chmod(0o600)"
    invoke(['docker','exec','-i','--user','10001:10001',api,'python','-c',copy_state,tmp],state_raw)
    command=['docker','exec','--user','10001:10001',api,'python',tmp+'/collector.py',
        '--state-file',tmp+'/state.json','--work-id',wid,'--expected-database',identity['database_name'],
        '--private-output-dir',tmp+'/private/canonical']
    started=now()
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    target.mkdir(mode=0o700)
    # Stdout is a safe collector summary, stderr and failure detail are private.
    exclusive_json(target/'runner-raw.json',{'started_at_utc':started,'ended_at_utc':now(),
        'exit_code':result.returncode,'stdout':result.stdout.decode('utf-8',errors='replace'),
        'stderr':result.stderr.decode('utf-8',errors='replace')},private=True)
    invoke(['docker','cp',api+':'+tmp+'/private/canonical/.',str(target)])
    for path in target.rglob('*'):
        if path.is_symlink():raise ValueError('PRIVATE_EXPORT_SYMLINK_REJECTED')
        os.chmod(str(path),0o700 if path.is_dir() else 0o600)
    snapshots=list(target.glob('*-canonical-work.json'))
    if len(snapshots)!=1:raise ValueError('EXACT_ONE_CANONICAL_SNAPSHOT_REQUIRED')
    raw=snapshots[0].read_bytes(); canonical=json.loads(raw)
    # Current Docker observation is a separate time, never a substitute for immutable
    # PE Owner history. A removed container remains UNKNOWN; no restart is attempted.
    pe=[]
    for file in canonical.get('filesystem_owner_observations',{}).get('files',[]):
        if not file['relative_path'].startswith('native-execution-bindings/'):continue
        binding=file['payload'];handle=binding.get('provider_handle') or {}
        observation=handle.get('runtime_image_observation')
        entry={'attempt_id':binding.get('attempt_id'),'pwu_id':binding.get('pwu_id'),
            'environment_id':(binding.get('environment') or {}).get('id'),
            'persisted_runtime_image_observation':observation,'observed_at_utc':now()}
        container=handle.get('opaque_reference','')
        if re.fullmatch(r'[0-9a-f]{64}',container):
            inspected=subprocess.run(['docker','inspect','--format','{{.Id}} {{.Image}} {{.State.Running}}',container],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            parts=inspected.stdout.decode().strip().split()
            if inspected.returncode==0 and len(parts)==3:
                entry.update(current_container_id=parts[0],current_image_id=parts[1],current_running=parts[2]=='true',current_observation_status='OBSERVED',evidence_level='E1')
                if isinstance(observation,dict):entry['matches_persisted_image_identity']=(parts[0]==observation.get('container_identity') and parts[1]==observation.get('actual_image_id'))
            else:entry.update(current_observation_status='UNAVAILABLE_AT_OBSERVATION_HISTORY_UNKNOWN',evidence_level='UNKNOWN')
        else:entry.update(current_observation_status='NO_DOCKER_IDENTITY_IN_ACTUAL_HANDLE',evidence_level='UNKNOWN')
        pe.append(entry)
    canonical['pe_current_container_observations']={'records':pe,'scope':'existing actual Provider handle container IDs only; readonly Docker inspect',
        'consistency':'DOCKER_READ_AFTER_DB_AND_FILESYSTEM_CAPTURE_NOT_ATOMIC',
        'historical_effect_absence_not_inferred':True}
    # Extra observations have their own raw file/hash; do not overwrite original snapshot.
    exclusive_json(target/'current-pe-owner-observations.json',canonical['pe_current_container_observations'],private=True)
    secrets=known_secrets();public.mkdir(mode=0o750);redactions=0;published=[]
    for path in sorted(target.glob('*.json')):
        content=path.read_text(encoding='utf-8')
        for value in secrets:
            redactions+=content.count(value);content=content.replace(value,'[REDACTED]')
        payload=json.loads(content)
        payload['public_release']={'method':'exact known C3 private credential values removed in memory',
            'private_root_released':False,'evidence_level':'E1_SCOPED_OWNER_OBSERVATION',
            'qualification_claim':'NO_WORK_PASS_OR_HUMAN_AUTHORITY_INFERRED',
            'unknown_sensitive_values_not_claimed_absent':True}
        public_path=public/path.name;exclusive_json(public_path,payload)
        # Value scan verifies the published bytes, without exposing values/prefix/hash.
        released=public_path.read_text(encoding='utf-8')
        if any(value in released for value in secrets):raise ValueError('KNOWN_SECRET_PUBLICATION_REJECTED')
        published.append({'file':public_path.name,'sha256':hashlib.sha256(public_path.read_bytes()).hexdigest()})
    identity_refs=[]
    for name in ('build.json','runtime-role-preparation.json','api-import-attestation.json','coordinator-import-attestation.json','worker-import-attestation.json','tool-host-import-attestation.json'):
        artifact=E/name
        identity_refs.append({'file':name,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'status':'EXISTING_RETAINED_ARTIFACT'} if artifact.is_file() else {'file':name,'status':'UNAVAILABLE_AT_OBSERVATION','evidence_level':'UNKNOWN'})
    receipt={'schema':SCHEMA,'work_id':wid,'runtime_identity':identity,'started_at_utc':started,'ended_at_utc':now(),
        'collector_exit_code':result.returncode,'export_complete':not canonical.get('export_error'),
        'actual_api_container_id':runtime['Id'],'actual_api_image_id':runtime['Image'],'actual_api_user':runtime['Config']['User'],
        'state_file_sha256':hashlib.sha256(state_raw).hexdigest(),'harness_sha256':{name:hashes[name] for name in ('c3_export_work_snapshot.py','c3_export_owner_records.py')},
        'private_directory':str(target),'private_file_mode':'0600','public_directory':str(public),
        'public_files':published,'known_credential_redactions':redactions,'known_secret_scan':'PASS_KNOWN_VALUES_ONLY',
        'database_transaction_read_only':canonical.get('database_snapshot',{}).get('read_only'),
        'evidence_level':'E1_SCOPED_OWNER_OBSERVATIONS','qualification_claim':'NO_COMPLETE_WORK_OR_GENERIC_CAPABILITY_PASS_INFERRED',
        'work_created_or_resumed':False,'human_authority_written':False,'model_calls':0,'mutating_database_queries':0,
        'mutating_git_commands':0,'docker_services_created_restarted_or_removed':0,
        'collector_installs_source_overlay':False,'retained_history_rewritten':False,'source_identity_artifact_refs':identity_refs}
    exclusive_json(public/'export-execution.json',receipt)
    print(json.dumps({'work_id':wid,'export_complete':receipt['export_complete'],'collector_exit_code':result.returncode,
        'public_directory':str(public),'private_raw_retained':True,'known_credential_redactions':redactions,
        'qualification_claim':'OBSERVATIONS_ONLY_NO_PASS_CLAIM'}))
    return result.returncode


if __name__=='__main__':
    try:sys.exit(main())
    except Exception as failure:
        print(json.dumps({'schema':SCHEMA,'export_complete':False,'error_type':type(failure).__name__,
            'raw_error_omitted':True,'qualification_claim':'NO_PASS_CLAIM'}),file=sys.stderr)
        sys.exit(3)
