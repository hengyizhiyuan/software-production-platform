from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,subprocess
ROOT=Path('/data/watt/c2-execution-readiness-20261009');E=ROOT/'evidence';w=E/'git-witness';m=json.loads((w/'manifest.json').read_text())
assert sha256((w/'source-output.pack').read_bytes()).hexdigest()==m['pack_sha256']
repository=ROOT/'recovered-git-witness.git';assert not repository.exists()
subprocess.run(['git','init','--bare',str(repository)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
with (w/'source-output.pack').open('rb') as stream:subprocess.run(['git','-C',str(repository),'index-pack','--stdin'],stdin=stream,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
checks={}
for name in ('source','output'):
    tree=subprocess.check_output(['git','-C',str(repository),'rev-parse',m[name+'_revision']+'^{tree}'],universal_newlines=True).strip()
    assert tree==m[name+'_tree'];checks[name+'_tree']=tree
artifact=subprocess.check_output(['git','-C',str(repository),'show',m['output_revision']+':index.html'])
assert sha256(artifact).hexdigest()==m['artifact_sha256'] and artifact==(w/'index.html').read_bytes()
(w/'recovery-check.json').write_text(json.dumps({'captured_at_utc':datetime.now(timezone.utc).isoformat(),'recovered_in_fresh_bare_repository':str(repository),'source_output_trees':checks,'artifact_sha256':m['artifact_sha256'],'pack_valid':True,'source_restored_without_reexecution':True,'qualification_claim':'Git evidence recovery only; no Work/Verification/Human PASS'},indent=2)+'\n')
print(json.dumps({'git_object_recovery':'PASS','source_tree':checks['source_tree'],'output_tree':checks['output_tree'],'artifact_digest_matches':True}))