from types import SimpleNamespace as N
from uuid import uuid4
import pytest
from spg.application.guardian_assurance import _candidate_pwu_verifications
from spg.domain.product import ProductInvariantViolation

def _basis():
    unit=N(id=uuid4(),source_baseline_id=uuid4(),completion_contract=N(verification_obligations=("CONTENT","DIFF")))
    plan=N(id=uuid4());snapshot=N(id=uuid4(),work_unit_id=unit.id)
    records=[N(id=uuid4(),result=N(value="PASS"),obligation=o,proposed_snapshot_id=snapshot.id,
        work_unit_id=unit.id,plan_revision_id=plan.id,source_baseline_id=unit.source_baseline_id,
        completion_evaluation_id=uuid4(),proposed_commit_identity="a"*40,tree_identity="b"*40) for o in ("CONTENT","DIFF")]
    records[1].completion_evaluation_id=records[0].completion_evaluation_id
    old=N(**vars(records[0]));old.id=uuid4();old.result=N(value="FAIL")
    admitted=N(id=uuid4(),outcome=N(value="ADMISSIBLE"),basis_fingerprint="f"*64,
        proposed_snapshot_id=snapshot.id,work_unit_id=unit.id,plan_revision_id=plan.id,
        source_baseline_id=unit.source_baseline_id,completion_evaluation_id=records[0].completion_evaluation_id,
        obligation_results=tuple(N(obligation=r.obligation,verification_record_id=r.id,
            applicable=True,admissible=True,result=r.result) for r in records))
    candidate=N(proposed_snapshot_id=snapshot.id,production_admissibility_id=admitted.id,
        production_admissibility_basis_fingerprint=admitted.basis_fingerprint,
        verification_record_ids=tuple(r.id for r in records))
    data={r.id:r for r in (old,*records)}
    runtime=N(proposed_snapshot=lambda _:snapshot,production_admissibility=lambda _:admitted,
        verification_record=lambda i:data.get(i),verification_records_for_work_unit=lambda _:(old,*records))
    return runtime,candidate,unit,plan,records,old,admitted,data

@pytest.mark.parametrize("corruption", (None,"missing","failed","wrong-revision","wrong-tree","wrong-plan","wrong-source","wrong-completion","wrong-obligation","wrong-admission","nonapplicable","incomplete"))
def test_sealed_owner_proof_selects_current_ids_and_keeps_history_closed(corruption):
    runtime,candidate,unit,plan,records,old,admitted,data=_basis()
    if corruption=="missing":data.pop(records[0].id)
    elif corruption=="failed":records[0].result=N(value="FAIL")
    elif corruption=="wrong-revision":records[0].proposed_commit_identity="c"*40
    elif corruption=="wrong-tree":records[0].tree_identity="c"*40
    elif corruption=="wrong-plan":records[0].plan_revision_id=uuid4()
    elif corruption=="wrong-source":records[0].source_baseline_id=uuid4()
    elif corruption=="wrong-completion":records[0].completion_evaluation_id=uuid4()
    elif corruption=="wrong-obligation":records[0].obligation="OTHER"
    elif corruption=="wrong-admission":admitted.basis_fingerprint="0"*64
    elif corruption=="nonapplicable":admitted.obligation_results[0].applicable=False
    elif corruption=="incomplete":candidate.verification_record_ids=candidate.verification_record_ids[:1]
    if corruption:
        with pytest.raises(ProductInvariantViolation):_candidate_pwu_verifications(runtime,candidate,unit,plan,"a"*40,"b"*40)
    else:
        selected=_candidate_pwu_verifications(runtime,candidate,unit,plan,"a"*40,"b"*40)
        assert selected==tuple(records) and old not in selected
    assert old.result.value=="FAIL" and len(runtime.verification_records_for_work_unit(unit.id))==3
