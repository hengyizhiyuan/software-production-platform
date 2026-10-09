"""Exact installed image, fresh isolated PostgreSQL, bounded Owner regressions."""
import json,os,secrets,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import xml.etree.ElementTree as ET
ROOT=Path('/data/watt/c3-semantic-convergence-20261009')
TARGET=ROOT/'capacity-representation-20261009/owner-pg'
BUILD=ROOT/'capacity-representation-20261009/final-image/evidence/build.json'
PG_IMAGE='sha256:d741b376874687de90374fd34f55c6b2760e8f7bd7e4ae5cd47f50757fc08cf8'
NAME='watt-c3-capacity-owner-pg-20261010';NETWORK=NAME;VOLUME=NAME
NODES=['tests/integration/test_c3_fulfillment_receipts.py']
assert not TARGET.exists();TARGET.mkdir(mode=0o750)
private=TARGET/'private';private.mkdir(mode=0o700)
evidence=TARGET/'evidence';evidence.mkdir(mode=0o750);os.chown(str(evidence),10001,10001)
build=json.loads(BUILD.read_text());assert build['exit_code']==0
IMAGE=build['image']['Id'];app=json.loads(subprocess.check_output(['docker','image','inspect',IMAGE],universal_newlines=True))[0]
assert app['Id']==IMAGE and app['Config']['Labels']['org.opencontainers.image.revision']==build['sources']['watt']['revision']
assert subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',PG_IMAGE],universal_newlines=True).strip()==PG_IMAGE
for kind,name in [('container',NAME),('network',NETWORK),('volume',VOLUME)]:assert subprocess.run(['docker',kind,'inspect',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
password=secrets.token_hex(32);user='c3_fixture';database='spg_c3_capacity_fixture'
url='postgresql+psycopg://'+user+':'+password+'@127.0.0.1:5432/'+database
for filename,values in [('postgres.env',{'POSTGRES_USER':user,'POSTGRES_PASSWORD':password,'POSTGRES_DB':database}),('test.env',{'SPG_DATABASE_URL':url,'SPG_TEST_DATABASE_URL':url})]:
 with (private/filename).open('x') as f:
  os.fchmod(f.fileno(),0o600)
  for k,v in values.items():f.write(k+'='+v+'\n')
subprocess.check_output(['docker','network','create','--internal','--label','watt.production=false',NETWORK])
subprocess.check_output(['docker','volume','create','--label','watt.production=false',VOLUME])
subprocess.check_output(['docker','run','-d','--name',NAME,'--network',NETWORK,'--label','watt.production=false','--label','watt.qualification=C3-owner-fixture','--env-file',str(private/'postgres.env'),'--mount','type=volume,src='+VOLUME+',dst=/var/lib/postgresql/data',PG_IMAGE])
ready=False
for _ in range(30):
 if subprocess.run(['docker','exec',NAME,'pg_isready','-U',user,'-d',database],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:ready=True;break
 time.sleep(1)
assert ready,'New isolated fixture PostgreSQL not ready; no alternate resource retry'
container='watt-c3-capacity-owner-tests-20261010'
fixture=private/'fixture-tmp';fixture.mkdir(mode=0o700);os.chown(str(fixture),10001,10001)
pytest=['python','-m','pytest','-p','no:cacheprovider','--basetemp=/c3-private-fixture/tests','--tb=short','--junitxml=/c3-evidence/result.xml']+NODES
command=['docker','run','--name',container,'--network','container:'+NAME,'--workdir','/qualification','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,exec,nosuid,size=512m','--memory','1536m','--cpus','1','--label','watt.production=false','--label','watt.qualification=C3-owner-fixture','--env-file',str(private/'test.env'),'--mount','type=bind,src='+str(evidence)+',dst=/c3-evidence','--mount','type=bind,src='+str(fixture)+',dst=/c3-private-fixture',IMAGE]+pytest
started=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
with (private/'test.raw.log').open('x') as stream:
 os.fchmod(stream.fileno(),0o600);result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
def redact(text):return text.replace(url,'[REDACTED_DB_URL]').replace(password,'[REDACTED_DB_PASSWORD]')
(evidence/'result.log').write_text(redact((private/'test.raw.log').read_text(errors='replace')))
counts={k:0 for k in ('tests','failures','errors','skipped')}
xml=evidence/'result.xml'
if xml.exists():
 xml.write_text(redact(xml.read_text()))
 for suite in ET.parse(str(xml)).iter('testsuite'):
  for k in counts:counts[k]+=int(suite.get(k,'0'))
counts['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped']
actual=json.loads(subprocess.check_output(['docker','inspect',container],universal_newlines=True))[0]
pg=json.loads(subprocess.check_output(['docker','inspect',NAME],universal_newlines=True))[0]
head=subprocess.check_output(['docker','exec',NAME,'psql','-U',user,'-d',database,'-Atc','SELECT version_num FROM alembic_version'],universal_newlines=True).strip()
receipt={'schema':'c3-semantic-owner-pg-regression-v1','started_at_utc':started,'ended_at_utc':datetime.now(timezone.utc).isoformat(),'wall_seconds':time.monotonic()-clock,'counts':counts,'exit_code':result.returncode,'sources':build['sources'],'actual_image_id':actual['Image'],'actual_container_id':actual['Id'],'actual_postgres_image_id':pg['Image'],'actual_postgres_container_id':pg['Id'],'database_name':database,'migration_head':head,'network_internal':True,'nodes':NODES,'source_or_test_overlay':False,'credentials_independently_generated':True,'live_model_calls':0,'actual_ai_work_created':0,'fixture_only':True,'original_database_access':False,'existing_services_started':False,'controller_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'claim':'ISOLATED_PG_OWNER_PERSISTENCE_AND_STATE_REGRESSION_NOT_REAL_G0'}
(evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
subprocess.check_output(['docker','stop',NAME])
print(json.dumps(receipt))
assert result.returncode==0 and counts['tests']>=2 and counts['skipped']==0
