from pathlib import Path
from hashlib import sha256
import json,subprocess
root=Path('/c1/evidence/git-objects')
manifest=json.loads((root/'manifest.json').read_text())
results=[]
for item in manifest:
    path=Path('/c1/recovered-witnesses')/item['work_id']
    path.mkdir(parents=True,exist_ok=False)
    subprocess.run(['git','init','--bare','--quiet',str(path)],check=True)
    pack=(root/item['pack']).read_bytes()
    assert sha256(pack).hexdigest()==item['pack_sha256']
    subprocess.run(['git','-C',str(path),'index-pack','--stdin'],input=pack,stdout=subprocess.DEVNULL,check=True)
    blob=subprocess.check_output(['git','-C',str(path),'show',item['output_revision']+':index.html'])
    assert sha256(blob).hexdigest()==item['index_html_sha256']
    for revision,key in ((item['input_revision'],'input_tree'),(item['output_revision'],'output_tree')):
        assert subprocess.check_output(['git','-C',str(path),'rev-parse',revision+'^{tree}'],text=True).strip()==item[key]
    results.append({'work_id':item['work_id'],'pack_sha256':item['pack_sha256'],'input_and_output_trees_recovered':True,'candidate_blob_recovered':True,'production_effect':False})
(root/'recovery-check.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results))
