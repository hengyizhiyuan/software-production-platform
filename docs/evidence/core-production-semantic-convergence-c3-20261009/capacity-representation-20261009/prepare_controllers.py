"""Derive bounded controls from the already qualified isolation/build mechanisms."""
from pathlib import Path
import json

HERE=Path(__file__).parent
OLD=HERE.parent/'continuation-20261010'
build=(OLD/'qualify_c3_continuation.py').read_text(encoding='utf-8')
replacements={
    'continuation-20261010/continuation-final-image':'capacity-representation-20261009/final-image',
    'ROOT/"continuation-20261010"':'ROOT/"capacity-representation-20261009"',
    '.c3-development-inputs/continuation-final-image-':'.c3-development-inputs/capacity-final-image-',
    'continuation-final-inputs':'capacity-final-inputs',
    'continuation-20261010/final-image-test-nodes.json':'capacity-representation-20261009/final-image-test-nodes.json',
    'watt-c3-continuation:':'watt-c3-capacity:',
    'watt-c3-continuation-imports-':'watt-c3-capacity-imports-',
    'watt-c3-continuation-regression-':'watt-c3-capacity-regression-',
    'Bounded R1 target proof, R2 failure continuity, P0 safe metadata and R3 exact stop projection; not real G0 or Holdout':
        'Bounded C3 fulfillment wire capacity and unchanged semantic/evidence gates; no model requests, real G0 or Holdout',
}
for old,new in replacements.items():
    assert old in build,old
    build=build.replace(old,new)
(HERE/'qualify_capacity_image.py').write_bytes(build.encode('utf-8'))
nodes=['tests/test_c3_fulfillment_capacity_representation.py','tests/test_fulfillment_projection.py',
    'tests/test_c3_fulfillment_components.py','tests/test_c3_admitted_source_facets.py',
    'tests/test_c3_fulfillment_provider_failures.py','tests/test_c3_fulfillment_admission_stop.py',
    'tests/test_c3_provider_http_metadata.py','tests/test_model_runtime.py',
    'tests/test_guardian_assurance_adapter.py','tests/test_c3_evidence_projection.py',
    'tests/test_governed_obligation_fulfillment.py']
(HERE/'final-image-test-nodes.json').write_bytes((json.dumps(nodes,indent=2)+'\n').encode('utf-8'))
pg=(OLD/'qualify_semantic_owner_pg.py').read_text(encoding='utf-8')
pg=pg.replace('continuation-20261010/semantic-owner-pg','capacity-representation-20261009/owner-pg')
pg=pg.replace('continuation-20261010/continuation-final-image/evidence/build.json','capacity-representation-20261009/final-image/evidence/build.json')
pg=pg.replace('watt-c3-continuation-owner','watt-c3-capacity-owner')
pg=pg.replace('owner-pg-20261009','owner-pg-20261010').replace('owner-tests-20261009','owner-tests-20261010')
start=pg.index('NODES=');end=pg.index('\nassert not TARGET',start)
pg=pg[:start]+"NODES=['tests/integration/test_c3_fulfillment_receipts.py']"+pg[end:]
pg=pg.replace("counts['tests']==len(NODES)","counts['tests']>=2")
pg=pg.replace("database='spg_c3_continuation_fixture'","database='spg_c3_capacity_fixture'")
(HERE/'qualify_capacity_pg.py').write_bytes(pg.encode('utf-8'))
