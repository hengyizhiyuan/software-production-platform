from types import SimpleNamespace as NS
from uuid import uuid4
import pytest
from spg.application.work import WorkApplicationService
from spg.domain.planning import ProductionNodeKind
from spg.domain.verification import VerificationResultValue


def test_human_pause_survives_restart_until_explicit_restart_or_new_basis():
    revision = uuid4(); work = NS(id=uuid4(), current_work_reality_revision_id=revision)
    rows = [NS(decision_type='WORK_PAUSED', scope={'work_reality_revision_id': str(revision)})]
    store = NS(governance_for_subject=lambda _: rows)
    assert WorkApplicationService._human_paused(store, work)
    rows.append(NS(decision_type='WORK_RECOVERY_PREVIEW', scope={}))
    assert WorkApplicationService._human_paused(store, work)
    rows.append(NS(decision_type='RESTART_CONVERGENCE_EPISODE', scope={}))
    assert not WorkApplicationService._human_paused(store, work)
    rows.pop(); work.current_work_reality_revision_id = uuid4()
    assert not WorkApplicationService._human_paused(store, work)


@pytest.mark.parametrize('result,owner_recovery', [(VerificationResultValue.UNKNOWN, True),
    (VerificationResultValue.FAIL, False), (VerificationResultValue.PASS, False)])
def test_unknown_verification_stays_with_verifier_instead_of_regenerating_code(result, owner_recovery):
    facts = NS(proposed_snapshot_id=uuid4())
    runtime = NS(verification_records_for_snapshot=lambda _: [NS(result=result, evidence=NS(metadata={}))])
    assert WorkApplicationService._verification_owner_recovery(runtime, facts) is owner_recovery


@pytest.mark.parametrize('generation,result', [(3, VerificationResultValue.FAIL), (1, VerificationResultValue.UNKNOWN)])
def test_required_unrecoverable_branch_stops_new_sibling_generation(monkeypatch, generation, result):
    import spg.infrastructure.executor_runtime.postgres_store as native
    monkeypatch.setattr(native, 'NativeExecutionStore', lambda _: NS(queue_for_attempt=lambda _: None))
    ids = [uuid4(), uuid4()]
    units = [NS(node_id=f'pwu:{i+1}', id=identity, source_baseline_id=uuid4(),
                verified_output_baseline_id=None) for i, identity in enumerate(ids)]
    class Binding:
        plan_revision_id = uuid4()
        def model_copy(self, update):return NS(**update)
    def summary(binding):
        return NS(attempt_id=uuid4() if binding.work_unit_id == ids[0] else None,
                  proposed_snapshot_id=uuid4(), completion_outcome='PRODUCED',
                  admissibility_outcome='INADMISSIBLE' if binding.work_unit_id == ids[0] else None)
    product = NS(session=None, runtime_summary=summary)
    runtime = NS(work_units_for_plan=lambda _: units, attempt=lambda _: NS(generation=generation),
                 verification_records_for_snapshot=lambda _: [NS(result=result, evidence=NS(metadata={}))])
    graph = NS(nodes=[NS(node_id=u.node_id, kind=ProductionNodeKind.PWU, dependency_ids=()) for u in units])
    assert WorkApplicationService._select_multi_pwu(product, runtime, Binding(), graph) is None
