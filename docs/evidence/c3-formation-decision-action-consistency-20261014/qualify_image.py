"""Exact installed image checks, on an isolated disposable PostgreSQL instance."""
from datetime import datetime, timezone
import argparse
import ipaddress
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

root = Path('/data/watt/ai-native-evolution-20261013/decision-action-consistency-20261014')
parser=argparse.ArgumentParser()
parser.add_argument('--postgres-only',action='store_true')
args=parser.parse_args()
out = root / 'evidence/installed'
out.mkdir(exist_ok=args.postgres_only)
os.chown(str(out), 10001, 10001)
image = json.loads((root/'evidence/image-build.json').read_text())['actual_image_id']
def call(args):
    return subprocess.check_output(args, universal_newlines=True).strip()
def run(name, args, network='none', env=None):
    command=['docker','create','--name','c3-action-'+name,'--network',network,
        '--memory','1024m','--cpus','1','--workdir','/qualification',
        '-v',str(out)+':/evidence']
    if env:
        command += ['--env-file',str(env)]
    container=call(command+[image]+args)
    fact=json.loads(call(['docker','inspect',container]))[0]
    assert fact['Image']==image
    # Environment values deliberately excluded from public records.
    (out/(name+'-container.json')).write_text(json.dumps({
        'id':fact['Id'],'actual_image':fact['Image'],'mounts':fact['Mounts'],
        'network_mode':fact['HostConfig']['NetworkMode'],'user':fact['Config']['User']},indent=2))
    started=time.monotonic()
    with (out/(name+'.log')).open('x') as log:
        result=subprocess.run(['docker','start','-a',container],stdout=log,stderr=subprocess.STDOUT)
    status=json.loads(call(['docker','inspect',container]))[0]['State']
    assert result.returncode==status['ExitCode']
    receipt={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
        'actual_image':image,'exit_code':status['ExitCode'],'elapsed_seconds':time.monotonic()-started,
        'oom_killed':status['OOMKilled']}
    (out/(name+'-run.json')).write_text(json.dumps(receipt,indent=2))
    print(name,json.dumps(receipt),flush=True)
    assert status['ExitCode']==0,name

if not args.postgres_only:
    run('attestation',['python','/opt/c3-build/attest_c3_image.py','--output','/evidence/attestation.json'])
    run('focused',['python','-m','pytest','-q','--tb=short','-p','no:cacheprovider',
    'tests/test_c3_decision_revision_contract.py','tests/test_ai_native_role_convergence.py',
    'tests/test_ai_native_interpretation_binding.py','tests/test_c3_early_consumer_mapping_diagnostics.py',
    'tests/test_c3_reviewed_fact_method_applicability.py','tests/test_c3_reviewer_contract_feedback.py',
    'tests/test_c3_formation_repair_consumption.py','--junitxml=/evidence/focused.xml'])

network='c3-decision-action-qualification'
pgname='c3-decision-action-postgres'
pgimage=call(['docker','image','inspect','public.ecr.aws/docker/library/postgres:17.6-alpine','--format','{{.Id}}'])
password=secrets.token_hex(24)
credentials=root/'private/isolated-pg-final.env'
credentials.write_text('POSTGRES_PASSWORD='+password+'\nPOSTGRES_DB=c1_contract_continuity\n')
credentials.chmod(0o600)
appenv=root/'private/isolated-test-final.env'
url='postgresql+psycopg://postgres:'+password+'@127.0.0.1:5432/c1_contract_continuity'
appenv.write_text('SPG_TEST_DATABASE_URL='+url+'\nSPG_DATABASE_URL='+url+'\n')
appenv.chmod(0o600)
networks=json.loads(call(['docker','network','inspect']+call(['docker','network','ls','-q']).split()))
routes=json.loads(call(['ip','-j','route']))
occupied=[ipaddress.ip_network(c['Subnet']) for n in networks for c in n['IPAM'].get('Config') or [] if c.get('Subnet')]
occupied += [ipaddress.ip_network(r['dst'],strict=False) for r in routes if r.get('dst') not in (None,'default')]
subnet=ipaddress.ip_network('172.23.10.16/28')
existing=next((n for n in networks if n['Name']==network),None)
if existing:
    assert existing['Internal'] and not existing['Containers']
    assert existing['IPAM']['Config'][0]['Subnet']==str(subnet)
else:
    assert not any(subnet.overlaps(n) for n in occupied if n.version==4)
    call(['docker','network','create','--internal','--subnet',str(subnet),network])
pg=call(['docker','run','-d','--name',pgname,'--network',network,'--memory','512m',
    '--cpus','1','--env-file',str(credentials),pgimage])
try:
    for _ in range(30):
        if subprocess.run(['docker','exec',pg,'pg_isready','-U','postgres','-d','c1_contract_continuity'],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
            break
        time.sleep(1)
    else:
        raise RuntimeError('ISOLATED_DATABASE_NOT_READY')
    (out/'database-final-identity.json').write_text(json.dumps({'container_id':pg,'image_id':pgimage,
        'network':network,'internal':True,'host_ports':[],'fresh_database':True},indent=2))
    run('postgres-final',['python','-m','pytest','-q','--tb=short','-p','no:cacheprovider',
        'tests/integration/test_ai_native_candidate_construction.py',
        '--junitxml=/evidence/postgres-final.xml'],'container:'+pgname,appenv)
finally:
    subprocess.run(['docker','stop',pg],stdout=subprocess.DEVNULL,check=True)
