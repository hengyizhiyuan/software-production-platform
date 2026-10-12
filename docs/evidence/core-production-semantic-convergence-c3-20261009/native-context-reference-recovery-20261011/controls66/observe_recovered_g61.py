from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
from urllib.request import urlopen,Request
import json,os,time,uuid
R=Path('/data/watt/c3-semantic-convergence-20261009/binding-g0-generation61-qualification-20261010');T=R/'native-context-recovery-generation66';E=T/'evidence';P=T/'private';WORK='6ba2cffa-0bf3-565a-81e0-7f3c6696f21e'
assert (E/'preview-owner-recovery.json').exists()
token=json.loads((R/'private/credentials.json').read_text())['operator_token'];id=str(uuid.uuid4());folder=P/('production-observer-'+id);folder.mkdir(mode=0o700)
seen=[]
for index in range(20):
 observation={'captured_at_utc':datetime.now(timezone.utc).isoformat(),'http':{},'model_calls_by_controller':0,'work_created':0}
 for suffix in ('','/steering','/operations','/guardian-assurance','/delivery'):
  request=Request('http://127.0.0.1:18327/api/works/'+WORK+suffix,headers={'Authorization':'Bearer '+token})
  try:
   with urlopen(request,timeout=30) as response:raw=response.read();status=response.status
   file=folder/(str(index)+('-work' if not suffix else suffix.replace('/','-'))+'.json')
   with file.open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(raw)
   data=json.loads(raw);observation['http'][suffix or 'work']={'status':status,'sha256':sha256(raw).hexdigest(),'private_path':str(file),'bytes':len(raw)}
   if suffix=='':
    observation['work']={k:data.get(k) for k in ('status','work_complete','human_attention_required','automatic_progression_state','current_production_run_id','current_work_reality_revision_id')}
   elif suffix=='/steering':
    observation['steering']={k:data.get(k) for k in ('status','condition','current_step','production_admission_state') if isinstance(data.get(k),(str,bool,int,type(None)))}
  except Exception as error:observation['http'][suffix or 'work']={'status':'UNKNOWN','error_type':type(error).__name__}
 seen.append(observation)
 f=E/('production-observation-'+id+'-'+str(index)+'.json')
 with f.open('x') as out:json.dump(observation,out,indent=2)
 print(json.dumps(observation.get('work',{})),flush=True)
 work=observation.get('work',{})
 if work.get('work_complete') or work.get('human_attention_required') or work.get('status') in ('COMPLETED','CANCELLED','TERMINATED','NON_CONVERGING'):break
 if index<19:time.sleep(5)
with (E/('production-observer-'+id+'.json')).open('x') as out:json.dump({'observations':len(seen),'latest':seen[-1],'private_folder':str(folder),'mutation_scope':'Normal Work GET projection and its existing autonomous production lifecycle; no new Work, Human Decision or explicit Artifact writes','provider_calls_by_controller':0,'controller_sha256':sha256(Path(__file__).read_bytes()).hexdigest()},out,indent=2)
