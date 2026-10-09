from pathlib import Path
from hashlib import sha256
import json, subprocess
root=Path('/c1/evidence')
output=root/'git-objects'
output.mkdir(exist_ok=True)
repos=sorted({path.resolve() for path in Path('/tmp/pytest-of-root').glob('pytest-*/test_both_actual_admission_pat*/wic-admission-repository')})
receipt=[]
for source in (root/'exact-contract-chain').glob('*.json'):
    item=json.loads(source.read_text())
    candidate=item['candidate']['proposed_commit_identity']
    baseline=item['source_baseline']['repository_revision']
    matches=[repo for repo in repos if subprocess.run(['git','-C',str(repo),'cat-file','-e',candidate],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0]
    assert len(matches)==1, (source.name,len(matches))
    repo=matches[0]
    work=item['work_reality_revision']['work_id']
    pack=subprocess.check_output(['git','-C',str(repo),'pack-objects','--stdout','--revs'],input=(baseline+'\n'+candidate+'\n').encode())
    target=output/(work+'.pack')
    target.write_bytes(pack)
    blob=subprocess.check_output(['git','-C',str(repo),'show',candidate+':index.html'])
    (output/(work+'-index.html')).write_bytes(blob)
    baseline_tree=subprocess.check_output(['git','-C',str(repo),'rev-parse',baseline+'^{tree}'],text=True).strip()
    candidate_tree=subprocess.check_output(['git','-C',str(repo),'rev-parse',candidate+'^{tree}'],text=True).strip()
    assert baseline_tree==item['source_baseline']['repository_tree_identity']
    assert candidate_tree==item['candidate']['proposed_tree_identity']
    receipt.append({'work_id':work,'source_receipt':source.name,'pack':target.name,'pack_sha256':sha256(pack).hexdigest(),'pack_bytes':len(pack),'input_revision':baseline,'input_tree':baseline_tree,'output_revision':candidate,'output_tree':candidate_tree,'index_html_sha256':sha256(blob).hexdigest(),'index_html_blob':subprocess.check_output(['git','-C',str(repo),'rev-parse',candidate+':index.html'],text=True).strip(),'diff':subprocess.check_output(['git','-C',str(repo),'diff','--name-status',baseline,candidate],text=True).strip(),'read_only_git_export':True})
(output/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
