import json, os, subprocess
from pathlib import Path
from hashlib import sha256
R=Path('/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010')
S=R/'source-owner-dev-2'
T=R/'source-owner-calibration-20261010'/'readonly-analysis-exact';T.mkdir(mode=0o750,exist_ok=False)
os.chown(str(T),10001,10001)
snapshot=json.loads((S/'manifest.json').read_text())
build=json.loads((R/'source-owner-calibration-20261010/final-image/evidence/build.json').read_text())
image=build['image']['Id']
basis='/data/watt/c3-semantic-convergence-20261009/public-delivery-c3-final/retry-1/g0-owner-2/20261009T130020024208Z-2fc7b990c1b54846a25bd067bc94b849-canonical-work.json'
assert sha256(Path(basis).read_bytes()).hexdigest()=='9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c'
cmd=['docker','run','--name','watt-c3-source-owner-readonly-exact-20261010','--network','none',
 '--user','10001:10001','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
 '--tmpfs','/tmp:rw,nosuid,size=128m','--label','watt.production=false','--memory','1536m','--cpus','1',
 '-e','SNAPSHOT_SHA256='+snapshot['archive_sha256'],
 '--mount','type=bind,src='+str(R/'repair-context-live-1/private/model-observations')+',dst=/retained,readonly',
 '--mount','type=bind,src='+basis+',dst=/basis.json,readonly',
 '--mount','type=bind,src='+str(R/'analyze-source-owner-calibration-exact.py')+',dst=/analysis.py,readonly',
 '--mount','type=bind,src='+str(T)+',dst=/diagnostic',
 image,'python','/analysis.py']
result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True)
(T/'result.log').write_text(result.stdout)
actual=json.loads(subprocess.check_output(['docker','inspect','watt-c3-source-owner-readonly-exact-20261010'],universal_newlines=True))[0]
receipt={'exit_code':result.returncode,'actual_image_id':actual['Image'],'container_id':actual['Id'],
 'network':'none','source_overlay':False,'watt_source':build['sources']['watt']['revision'],'source_snapshot_sha256':snapshot['archive_sha256'],
 'controller_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'script_sha256':sha256((R/'analyze-source-owner-calibration-exact.py').read_bytes()).hexdigest(),
 'private_mounts_readonly':True,'production_modified':False,'model_calls':0}
(T/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(result.stdout);print(json.dumps(receipt))
raise SystemExit(result.returncode)
