from types import SimpleNamespace
from uuid import uuid4
import pytest
from spg.application.steering_decision import _current_verification_references
from spg.domain.product import RuntimeFactSummary
from spg.domain.steering import RealityReference, RealityReferenceKind
from spg.domain.verification import VerificationResultValue

@pytest.mark.parametrize("case", ("pass", "fail", "missing", "unknown", "mismatched-result", "bad-cardinality"))
def test_current_proof_ids_do_not_zip_with_all_historical_records(case):
    old = SimpleNamespace(id=uuid4(), result=VerificationResultValue.FAIL)
    current = SimpleNamespace(id=uuid4(), result=VerificationResultValue.PASS)
    fallback = RealityReference(kind=RealityReferenceKind.COMPLETION, identity=uuid4())
    selected = str(current.id); result = "PASS"
    if case == "fail":current.result = VerificationResultValue.FAIL; result = "FAIL"
    if case in ("missing", "unknown"):selected = None
    if case == "unknown":result = "UNKNOWN"
    if case == "mismatched-result":current.result = VerificationResultValue.FAIL
    ids = [] if case == "bad-cardinality" else [selected]
    summary = RuntimeFactSummary(verification_results=(result,), extra={"verification_record_ids": ids})
    refs, failing = _current_verification_references(summary, (old, current), fallback)
    assert all(ref.identity != old.id for ref in refs)
    assert bool(failing) is (case != "pass")
    if case in ("missing", "unknown", "bad-cardinality"):assert failing == (fallback,)
    if case == "pass":assert [ref.identity for ref in refs] == [current.id]
    assert old.result is VerificationResultValue.FAIL
