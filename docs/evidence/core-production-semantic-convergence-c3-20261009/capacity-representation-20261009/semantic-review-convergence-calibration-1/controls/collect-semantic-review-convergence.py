from pathlib import Path
from hashlib import sha256
import json,subprocess,tarfile
root=Path.cwd();remote='/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010'
short=root/'.c3-development-inputs/semantic-review-convergence-collected';short.mkdir(exist_ok=False)
folders=['source-owner-calibration-20261010/source-owner-dev-17-regression', 'source-owner-calibration-20261010/source-owner-dev-18-regression', 'source-owner-calibration-20261010/source-owner-dev-19-regression', 'source-owner-calibration-20261010/source-owner-dev-20-targeted', 'source-owner-calibration-20261010/source-owner-dev-21-regression', 'source-owner-calibration-20261010/source-owner-dev-22-targeted', 'review-feedback-qualified-20261010/final-image/evidence', 'review-feedback-qualified-20261010/owner-pg-final-subnet1/evidence', 'review-feedback-qualified-20261010/image-recovery', 'review-entailment-qualified-20261010/final-image/evidence', 'review-entailment-qualified-20261010/owner-pg-final-subnet1/evidence', 'review-entailment-qualified-20261010/image-recovery', 'review-domains-qualified-20261010/final-image/evidence', 'review-domains-qualified-20261010/owner-pg-final-subnet1/evidence', 'review-domains-qualified-20261010/image-recovery', 'review-primary-qualified-20261010/final-image/evidence', 'review-primary-qualified-20261010/owner-pg-final-subnet1/evidence', 'review-primary-qualified-20261010/image-recovery', 'review-none-calibration-1/evidence', 'review-none-qualified-1/evidence', 'review-none-entailment-1/evidence', 'semantic-convergence-live-1/evidence', 'semantic-domains-live-1/evidence', 'semantic-primary-live-1/evidence', 'preview-negative-final-1/evidence', 'review-primary-qualified-20261010/readonly-analysis', 'review-primary-qualified-20261010/readonly-analysis-narrow1']
code='''from pathlib import Path
from hashlib import sha256
import json,tarfile
R=Path(REMOTE);folders=FOLDERS;files={}
for folder in folders:
 for p in sorted((R/folder).iterdir()):
  if p.is_file() and p.suffix in ('.json','.log','.xml'):files[p.relative_to(R).as_posix()]=p
manifest={n:sha256(p.read_bytes()).hexdigest() for n,p in files.items()}
with tarfile.open(str(R/'semantic-review-convergence-public-receipts.tar'),'x') as a:
 for n,p in files.items():a.add(str(p),arcname=n)
(R/'semantic-review-convergence-public-receipts-manifest.json').write_text(json.dumps({'files':manifest,'archive_sha256':sha256((R/'semantic-review-convergence-public-receipts.tar').read_bytes()).hexdigest()},indent=2))
print(len(files))
'''.replace('REMOTE',repr(remote)).replace('FOLDERS',repr(folders))
subprocess.run(['ssh','watt-ecs','python3 -'],input=code,text=True,check=True)
for filename in ('semantic-review-convergence-public-receipts.tar','semantic-review-convergence-public-receipts-manifest.json'):
 subprocess.run(['scp','watt-ecs:'+remote+'/'+filename,str(short/filename)],check=True)
m=json.loads((short/'semantic-review-convergence-public-receipts-manifest.json').read_text());assert sha256((short/'semantic-review-convergence-public-receipts.tar').read_bytes()).hexdigest()==m['archive_sha256']
out=Path(chr(92)*2+'?'+chr(92)+str(root/'docs/evidence/core-production-semantic-convergence-c3-20261009/capacity-representation-20261009/semantic-review-convergence-calibration-1/receipts'));out.mkdir(parents=True,exist_ok=False)
with tarfile.open(short/'semantic-review-convergence-public-receipts.tar') as a:
 for member in a.getmembers():
  assert member.isfile() and member.name in m['files'] and '..' not in Path(member.name).parts
  data=a.extractfile(member).read();assert sha256(data).hexdigest()==m['files'][member.name]
  p=out/member.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
(out/'manifest.json').write_text(json.dumps(m,indent=2))
print('Verified',len(m['files']),'receipts')
