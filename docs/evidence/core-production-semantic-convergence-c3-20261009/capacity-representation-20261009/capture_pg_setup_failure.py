"""Preserve a setup failure and stop only this task's fresh fixture cluster."""
import json,subprocess
from hashlib import sha256
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path('/data/watt/c3-semantic-convergence-20261009/capacity-representation-20261009/owner-pg')
NAME='watt-c3-capacity-owner-pg-20261010'
APP='watt-c3-capacity-owner-tests-20261010'
def inspect(name):return json.loads(subprocess.check_output(['docker','inspect',name],universal_newlines=True))[0]
pg=inspect(NAME);app=inspect(APP)
assert pg['Image']=='sha256:d741b376874687de90374fd34f55c6b2760e8f7bd7e4ae5cd47f50757fc08cf8'
assert pg['Config']['Labels']['watt.qualification']=='C3-owner-fixture'
assert app['Image']=='sha256:7a4ac00e3599bda2dbcebe46b15dd0b45f3be86552021023ebd288eb732f7b35'
counts={k:0 for k in ('tests','failures','errors','skipped')}
for suite in ET.parse(str(ROOT/'evidence/result.xml')).iter('testsuite'):
    for key in counts:counts[key]+=int(suite.get(key,'0'))
counts['passed']=counts['tests']-sum(counts[k] for k in ('failures','errors','skipped'))
assert counts['errors']==4 and counts['passed']==0
receipt={'result':'SETUP_ERROR','counts':counts,'actual_image_id':app['Image'],'actual_container_id':app['Id'],
    'actual_postgres_image_id':pg['Image'],'actual_postgres_container_id':pg['Id'],
    'started_at_utc':app['State']['StartedAt'],'ended_at_utc':app['State']['FinishedAt'],
    'timing_source':'ACTUAL_DOCKER_FACT','controller_wall_seconds':'UNKNOWN',
    'database_name':'spg_c3_capacity_fixture','required_fixture_database_name':'c1_contract_continuity',
    'migration_head':'UNKNOWN_NOT_CREATED','exit_code':app['State']['ExitCode'],
    'cause':'Existing fixture rejected the newly generated database name before schema setup',
    'controller_sha256':sha256(Path('/data/watt/c3-semantic-convergence-20261009/capacity-final-inputs/qualify_capacity_pg.py').read_bytes()).hexdigest(),
    'actual_model_calls':0,'original_database_access':False,'source_overlay':False}
with (ROOT/'evidence/setup-failure-receipt.json').open('x',encoding='utf-8') as stream:stream.write(json.dumps(receipt,indent=2)+'\n')
subprocess.check_output(['docker','stop',NAME])
print(json.dumps(receipt))
