from pathlib import Path
from datetime import datetime,timezone
import json,os,subprocess
ROOT=Path('/data/watt/c2-execution-readiness-20261009');E=ROOT/'evidence';P=ROOT/'private';identifier='40a95832d05f210b3c40cb497742cda759286f4da371fbc6be0ffa49ce4415e9'
result=subprocess.run(['docker','events','--since','2026-10-09T07:31:15Z','--until','2026-10-09T07:31:50Z','--filter','container='+identifier,'--format','{{json .}}'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
assert result.returncode==0,'Bounded Docker evidence read failed'
with (P/'original-production-environment-docker-events.jsonl').open('x') as stream:os.fchmod(stream.fileno(),0o600);stream.write(result.stdout)
selected=[]
for line in result.stdout.splitlines():
    event=json.loads(line);actor=event.get('Actor',{});attributes=actor.get('Attributes',{})
    if event.get('Action') not in ('create','start','die','stop','destroy','kill'):continue
    assert actor.get('ID')==identifier
    selected.append({'type':event.get('Type'),'action':event.get('Action'),'container_id':actor.get('ID'),'time':event.get('time'),'timeNano':event.get('timeNano'),'image_reference':attributes.get('image'),'name':attributes.get('name'),'exitCode':attributes.get('exitCode'),'evidence_owner':'Docker daemon retained original container lifecycle event'})
receipt={'captured_at_utc':datetime.now(timezone.utc).isoformat(),'original_container_id':identifier,'window':['2026-10-09T07:31:15Z','2026-10-09T07:31:50Z'],'events':selected,'event_count':len(selected),'unknown_if_missing':True,'replacement_environment_created':False}
(E/'original-pe-docker-events.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)