from pathlib import Path
from hashlib import sha256
import json,os,shutil
root=Path('/data/watt/c3-semantic-convergence-20261009/retry-1'); stage=root/'evidence/control-amendment-1'
new_raw=(stage/'amended-frozen-inputs.json').read_bytes(); new=json.loads(new_raw); amendment=new['runtime_control_amendment']; old_raw=(root/'frozen-inputs.json').read_bytes();old=json.loads(old_raw)
assert sha256(old_raw).hexdigest()==amendment['original_freeze_sha256'];assert old['control_harness_revision']==new['control_harness_revision']=='b575e4346bf50d9046e4ed888daaeaccc4d5e8ee'
assert old['sources']==new['sources'] and old['archives']==new['archives'];assert new['application_commit']=='91f5dbc9906d1f857113736981517c1091ec52ae'
assert not (root/'evidence/normal-entry-state.json').exists()
assert set(amendment['changed_files'])=={'c3_normal_entry.py','run_c3_normal_entry.py'}
assert not (stage/'original-frozen-inputs.json').exists();(stage/'original-frozen-inputs.json').write_bytes(old_raw)
for name, hashes in amendment['changed_files'].items():
 assert sha256((root/name).read_bytes()).hexdigest()==hashes['before'];assert sha256((stage/name).read_bytes()).hexdigest()==hashes['after'];assert not (stage/('original-'+name)).exists();shutil.copyfile(str(root/name),str(stage/('original-'+name)))
for name in amendment['changed_files']:shutil.copyfile(str(stage/name),str(root/name))
(root/'frozen-inputs.json').write_bytes(new_raw)
for name,digest in new['control_harness_sha256'].items():assert sha256((root/name).read_bytes()).hexdigest()==digest
receipt={'schema':'c3-external-control-amendment-applied-v1','runtime_control_revision':amendment['revision'],'build_control_revision':old['control_harness_revision'],'application_revision':new['application_commit'],'application_image_rebuilt':False,'old_controls_preserved':True,'all_current_12_control_hashes_match':True,'normal_entry_state_absent_before_apply':True,'product_or_work_request_sent_by_apply':False,'new_freeze_sha256':sha256(new_raw).hexdigest()}
(stage/'applied.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
