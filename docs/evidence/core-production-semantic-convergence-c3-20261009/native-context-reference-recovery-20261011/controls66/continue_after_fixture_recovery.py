from pathlib import Path
import json,time,subprocess,xml.etree.ElementTree as ET
Q=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation66-qualified-20261010');I=Q/'final-inputs';original=Q/'owner-pg-generation66/evidence/receipt.json'
for _ in range(180):
 if original.exists():break
 time.sleep(5)
else:raise RuntimeError('ORIGINAL_QUALIFICATION_NOT_COMPLETED_NO_RECOVERY_EXECUTED')
x=json.loads(original.read_text());assert x['counts']=={'tests':16,'failures':2,'errors':0,'skipped':0,'passed':14}
failures=list(ET.parse(str(original.parent/'result.xml')).iter('failure'));assert len(failures)==2 and all('Unconsumed column names: provider' in (f.text or '') for f in failures),'UNEXPECTED_FAILURE_NOT_A_FIXTURE_RECOVERY'
for name in ('qualify_postgresql_recovery.py','upgrade_existing_g61_after_test_recovery.py','recover_existing_preview.py','collect_recovered_g61.py','observe_recovered_g61.py'):
 print(json.dumps({'executing_control':name}),flush=True)
 r=subprocess.run(['python3',str(I/name)])
 if r.returncode:raise SystemExit(r.returncode)
