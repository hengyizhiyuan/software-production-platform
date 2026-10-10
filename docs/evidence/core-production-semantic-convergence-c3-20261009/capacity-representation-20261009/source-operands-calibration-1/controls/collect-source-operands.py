from pathlib import Path
from hashlib import sha256
import json,subprocess,tarfile
root=Path.cwd();remote='/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010'
short=root/'.c3-development-inputs/source-operands-collected';short.mkdir(exist_ok=False)
folders=['source-owner-calibration-20261010/source-owner-dev-11-targeted','source-owner-calibration-20261010/source-owner-dev-12-targeted',
 'source-operands-calibration-20261010/readonly-analysis',
 'source-operands-qualified-20261010/final-image/evidence','source-operands-qualified-20261010/owner-pg-final/evidence','source-operands-qualified-20261010/image-recovery',
 'source-operands2-qualified-20261010/final-image/evidence','source-operands2-qualified-20261010/owner-pg-final/evidence','source-operands2-qualified-20261010/image-recovery',
 'source-operands-live-1/evidence','source-operands2-live-1/evidence',
 'source-owner-calibration-20261010/source-owner-dev-13-regression',
 'source-operands2-qualified-20261010/readonly-capacity','source-operands2-qualified-20261010/readonly-capacity-2',
 'source-review-qualified-20261010/final-image/evidence','source-review-qualified-20261010/owner-pg-final/evidence','source-review-qualified-20261010/image-recovery','source-review-qualified-20261010/readonly-economy',
 'source-review-live-1/evidence','source-review-fixed-qualified-20261010/final-image/evidence','source-review-fixed-qualified-20261010/owner-pg-final/evidence','source-review-fixed-qualified-20261010/image-recovery','source-review-fixed-live-1/evidence',
 'source-owner-calibration-20261010/source-owner-dev-14-targeted',
 'source-typed-qualified-20261010/final-image/evidence','source-typed-qualified-20261010/owner-pg-final/evidence','source-typed-qualified-20261010/image-recovery',
 'source-typed-qualified-20261010/readonly-owner/evidence','source-typed-qualified-20261010/readonly-owner2/evidence','source-typed-live-1/evidence',
 'source-owner-calibration-20261010/source-owner-dev-15-targeted',
 'source-consumption-qualified-20261010/final-image/evidence','source-consumption-qualified-20261010/owner-pg-final/evidence','source-consumption-qualified-20261010/image-recovery',
 'source-consumption-qualified-20261010/readonly-owner3/evidence','source-consumption-live-1/evidence',
 'source-owner-calibration-20261010/source-owner-dev-16-targeted',
 'source-ownerprobe-qualified-20261010/final-image/evidence','source-ownerprobe-qualified-20261010/owner-pg-final/evidence','source-ownerprobe-qualified-20261010/image-recovery',
 'source-ownerprobe-qualified-20261010/readonly-owner4/evidence','source-ownerprobe-live-1/evidence']
code='''from pathlib import Path
from hashlib import sha256
import json,tarfile
R=Path(REMOTE);folders=FOLDERS;files={}
for folder in folders:
 for p in sorted((R/folder).iterdir()):
  if p.is_file() and p.suffix in ('.json','.log','.xml'):files[p.relative_to(R).as_posix()]=p
manifest={n:sha256(p.read_bytes()).hexdigest() for n,p in files.items()}
with tarfile.open(str(R/'source-operands-public-receipts.tar'),'x') as a:
 for n,p in files.items():a.add(str(p),arcname=n)
(R/'source-operands-public-receipts-manifest.json').write_text(json.dumps({'files':manifest,'archive_sha256':sha256((R/'source-operands-public-receipts.tar').read_bytes()).hexdigest()},indent=2))
print(len(files))
'''.replace('REMOTE',repr(remote)).replace('FOLDERS',repr(folders))
subprocess.run(['ssh','watt-ecs','python3 -'],input=code,text=True,check=True)
for filename in ('source-operands-public-receipts.tar','source-operands-public-receipts-manifest.json'):
 subprocess.run(['scp','watt-ecs:'+remote+'/'+filename,str(short/filename)],check=True)
m=json.loads((short/'source-operands-public-receipts-manifest.json').read_text());assert sha256((short/'source-operands-public-receipts.tar').read_bytes()).hexdigest()==m['archive_sha256']
out=Path(chr(92)*2+'?'+chr(92)+str(root/'docs/evidence/core-production-semantic-convergence-c3-20261009/capacity-representation-20261009/source-operands-calibration-1/receipts'));out.mkdir(parents=True,exist_ok=False)
with tarfile.open(short/'source-operands-public-receipts.tar') as a:
 for member in a.getmembers():
  assert member.isfile() and member.name in m['files'] and '..' not in Path(member.name).parts
  data=a.extractfile(member).read();assert sha256(data).hexdigest()==m['files'][member.name]
  p=out/member.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
(out/'manifest.json').write_text(json.dumps(m,indent=2))
print('Verified',len(m['files']),'receipts')
