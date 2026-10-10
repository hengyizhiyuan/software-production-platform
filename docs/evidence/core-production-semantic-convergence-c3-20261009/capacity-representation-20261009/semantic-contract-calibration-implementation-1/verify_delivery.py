"""Offline public receipt integrity; no model, database or Owner mutation."""
from pathlib import Path
from hashlib import sha256
import json,os
ROOT=Path(__file__).resolve().parent
if os.name=='nt': ROOT=Path('\\\\?\\'+str(ROOT))
WATT='a91442c21ed487b10d8dc38023b0807787a29648'
GUARDIAN='76c1e87a1b29d151f4ed949748e3298f2169c5b1'
IMAGE='sha256:90f2cd847ad891fda6ca95b5736c84b680c9d58bd6a3203bf0ea31c970da0f16'
manifest=json.loads((ROOT/'receipt-manifest.json').read_text())
for entry in manifest['files']:
    p=ROOT/entry['file']; assert p.resolve().is_relative_to(ROOT)
    b=p.read_bytes();assert len(b)==entry['bytes'] and sha256(b).hexdigest()==entry['sha256'],entry['file']
for path,number in [('final-image/watt-continuation-receipt.json',231),('final-image/guardian-receipt.json',163),('postgresql/receipt.json',5)]:
    r=json.loads((ROOT/'receipts'/path).read_text())
    assert r['sources']['watt']['revision']==WATT and r['sources']['guardian']['revision']==GUARDIAN
    assert r['counts']=={'tests':number,'failures':0,'errors':0,'skipped':0,'passed':number}
    assert r['exit_code']==0
    assert (r.get('image_id') or r.get('actual_image') or r.get('actual_image_id'))==IMAGE
negative=json.loads((ROOT/'receipts/retained-negative/historical-replay.json').read_text())
controller=json.loads((ROOT/'receipts/retained-negative/controller.json').read_text())
assert negative['watt_source']==WATT and negative['guardian_source']==GUARDIAN
assert negative['candidate_routes']==57 and negative['inventory_sources']==26
assert negative['predicate']=='OBLIGATION_PROJECTION_DUPLICATE_ROUTE' and not negative['candidate_modified']
assert controller['actual_image']==IMAGE and controller['immutable_inputs'] and controller['exit_code']==0
assert controller['model_calls']==0 and controller['inputs_before']==controller['inputs_after']
recovery=json.loads((ROOT/'receipts/recovery/receipt.json').read_text())
assert recovery['source']==WATT and recovery['actual_image_id']==IMAGE
print(json.dumps({'public_files':len(manifest['files']),'receipt_integrity':'PASS','final_source':WATT,
    'guardian':GUARDIAN,'image':IMAGE,'claim':'CONTROLLED_CONTRACT_QUALIFICATION_ONLY_C3_PARTIAL'}))
