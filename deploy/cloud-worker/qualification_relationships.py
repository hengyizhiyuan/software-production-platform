"""Read-only restored engineering lineage checks; never start execution owners."""
import json
import os
from pathlib import Path
from sqlalchemy import text
from spg.config import Settings
from spg.infrastructure.persistence import Database


def snapshot():
    database = Database.from_settings(Settings())
    root = Path(os.environ['WATT_RESTORED_APP'])
    try:
        with database.unit_of_work() as uow:
            uow.session.execute(text('SET TRANSACTION READ ONLY'))
            candidates = {str(r['id']): r for r in uow.session.execute(text('select * from baseline_candidates')).mappings()}
            units = {str(r['id']): r for r in uow.session.execute(text('select * from production_work_units')).mappings()}
            verifications = {str(r['id']): r for r in uow.session.execute(text('select * from verification_records')).mappings()}
            tasks = {}
            context_count = 0
            for unit in units.values():
                task = unit['completion_contract'].get('task_contract')
                if task is None:
                    continue
                tasks[task['task_contract_id']] = task
                lineage = task.get('decision_context')
                if lineage:
                    for obligation in lineage['protected_obligations']:
                        assert obligation['package_fingerprint'] == lineage['package_fingerprint']
                    context_count += 1
            for candidate in candidates.values():
                assert set(candidate['satisfied_work_unit_ids']).issubset(units)
                assert set(candidate['verification_record_ids']).issubset(verifications)
                for identity in candidate['satisfied_work_unit_ids']:
                    assert units[identity]['plan_revision_id'] == candidate['plan_revision_id']
            guardian_count = 0
            owner = root / 'owner-runtime/guardian'
            for path in (owner/'results').glob('*.json'):
                result = json.loads(path.read_text())
                if 'source_revision' not in result or 'runtime_ref' not in result:
                    continue
                request = json.loads((owner/'requests'/(result['request_id']+'.json')).read_text())
                for key in ('request_id','candidate_id','candidate_fingerprint','source_revision','source_tree','runtime_ref'):
                    assert request[key] == result[key]
                candidate = candidates[result['candidate_id']]
                assert candidate['fingerprint'] == result['candidate_fingerprint']
                assert candidate['proposed_commit_identity'] == result['source_revision']
                assert candidate['proposed_tree_identity'] == result['source_tree']
                ref = request.get('task_contract_ref')
                if ref:
                    task = tasks[ref.removeprefix('task-contract:')]
                    lineage = task.get('decision_context')
                    if request.get('decision_context_fingerprint'):
                        assert lineage['package_fingerprint'] == request['decision_context_fingerprint']
                for ref in request['verification_refs']:
                    if ref.startswith('verification:'):
                        assert ref.removeprefix('verification:') in verifications
                guardian_count += 1
            heads = uow.session.execute(text('select version_num from alembic_version')).scalars().all()
            assert heads == ['20261005_68']
            accepted = uow.session.execute(text('select count(*) from product_source_versions v join work_delivery_acceptances a on a.id=v.acceptance_id')).scalar_one()
            return {'migration': heads[0], 'candidates': len(candidates), 'pwus': len(units),
                'verification_records': len(verifications), 'ecf_task_bindings': context_count,
                'guardian_results': guardian_count, 'accepted_source_human_links': accepted,
                'guardian_sql_lineage_equal': True, 'ecf_fingerprints_equal': True}
    finally:
        database.dispose()


if __name__ == '__main__':
    print(json.dumps(snapshot(), sort_keys=True))
