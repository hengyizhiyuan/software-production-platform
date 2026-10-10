from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json, os, subprocess, uuid
R=Path('/data/watt/c3-semantic-convergence-20261009/final-g0-qualification-20261010');P=R/'private';E=R/'evidence'
API='watt-c3-finalg0-api-20261010'
state=(E/'normal-entry-state.json').read_bytes();s=json.loads(state)
work=str(uuid.UUID(s['work_id']));assert s['runtime_identity']['isolated'] and s['runtime_identity']['database_name']=='spg_c3_finalg0_qualification_20261010'
image='sha256:697b80141e1a11a70111166a1bb66db674457f8461ce9bea5fa21affebdbcbec'
x=json.loads(subprocess.check_output(['docker','inspect',API],universal_newlines=True))[0];assert x['Image']==image and x['State']['Running']
def call(args,data=None):
 p=subprocess.run(args,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 assert p.returncode==0,'READONLY_COLLECTOR_COMMAND_FAILED'
 return p.stdout
def private_write(path,b):
 with path.open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(b)
run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex
directory=P/('owner-export-'+run);directory.mkdir(mode=0o700)
tmp='/tmp/c3-final-g0-'+run
script=(R/'controls/c3_export_work_snapshot.py').read_bytes()
call(['docker','exec','-i',API,'python','-c','import sys;from pathlib import Path;p=Path(sys.argv[1]);p.mkdir(mode=0o700);(p/"collector.py").write_bytes(sys.stdin.buffer.read())',tmp],script)
call(['docker','exec','-i',API,'python','-c','import sys;from pathlib import Path;(Path(sys.argv[1])/"state.json").write_bytes(sys.stdin.buffer.read())',tmp],state)
cmd=['docker','exec',API,'python',tmp+'/collector.py','--state-file',tmp+'/state.json','--work-id',work,'--expected-database','spg_c3_finalg0_qualification_20261010','--private-output-dir',tmp+'/private']
p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
private_write(directory/'runner.json',json.dumps({'exit_code':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')},indent=2).encode())
info=json.loads(p.stdout.decode());assert info['work_id']==work
for name in (info['raw_private_file'],info['summary_private_file']):
 assert Path(name).name==name
 b=call(['docker','exec',API,'python','-c','import sys;from pathlib import Path;sys.stdout.buffer.write(Path(sys.argv[1]).read_bytes())',tmp+'/private/'+name])
 if name==info['raw_private_file']:assert sha256(b).hexdigest()==info['raw_private_sha256']
 private_write(directory/name,b)
receipt={'schema':'c3-final-g0-readonly-export-v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'work_id':work,'product_id':s['product_id'],'runtime_identity':s['runtime_identity'],'collector_exit_code':p.returncode,'private_directory':str(directory),'raw_private_file':info['raw_private_file'],'raw_private_sha256':info['raw_private_sha256'],'state_sha256':sha256(state).hexdigest(),'collector_sha256':sha256(script).hexdigest(),'actual_api_container_id':x['Id'],'actual_api_image':x['Image'],'model_requests':0,'work_mutations':0,'historical_owner_mutations':0}
with (E/('owner-export-'+run+'.json')).open('x') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt))
