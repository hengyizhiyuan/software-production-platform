import json
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4
from spg.evaluation.production_trace import work_delivery_qualification


def test_only_checksum_bound_exact_work_candidate_incident_is_visible(tmp_path):
    work, candidate = uuid4(), uuid4()
    settings = SimpleNamespace(owner_runtime_store_root=tmp_path)
    root=tmp_path/'qualifications';index=root/'work-references';index.mkdir(parents=True)
    artifact=root/'incident.json'
    data={'work_id':str(work),'candidate_id':str(candidate),'candidate_fingerprint':'a'*64,
          'root_cause':'Accepted source export differs from the unaccepted produced Candidate',
          'result':'REQUALIFIED','new_manifest_id':str(uuid4())}
    artifact.write_text(json.dumps(data))
    digest=sha256(artifact.read_bytes()).hexdigest()
    pointer=index/(str(work)+'.json')
    pointer.write_text(json.dumps({'delivery_integrity':[f'evidence:{artifact}:sha256:{digest}']}))
    rows=[{'id':candidate,'fingerprint':'a'*64}]
    result=work_delivery_qualification(settings,work,rows)
    assert len(result)==1 and result[0]['root_cause']==data['root_cause']
    assert work_delivery_qualification(settings,uuid4(),rows)==[]
    assert work_delivery_qualification(settings,work,[{'id':candidate,'fingerprint':'b'*64}])==[]
    artifact.write_text(json.dumps(dict(data,result='forged')))
    assert work_delivery_qualification(settings,work,rows)==[]
