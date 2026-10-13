"""Database-backed export contract; these fixtures are not live ECS qualification."""
from hashlib import sha256
from io import BytesIO
import json
from uuid import uuid4
from zipfile import ZipFile

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import insert, select, update, func

from spg.api.admin import install_admin
from spg.api.authority import install_authority_boundary
from spg.config import Settings
from spg.evaluation.work_registry import WorkRegistryService
from spg.infrastructure.persistence import metadata
from tests.integration.test_admin_universal_trace import simple
from tests.integration.test_software_delivery import produce
from tests.integration.test_work_delivery import clean_schema

pytestmark = pytest.mark.postgresql


def client(db, tmp_path):
    settings = Settings(auth_mode='required', operator_token='test-operator-token-1234567890-long',
        owner_runtime_store_root=tmp_path/'owner',
        native_executor_production_environment_store_root=tmp_path/'preview')
    api = FastAPI()
    install_authority_boundary(api, database=db, settings=settings)
    install_admin(api, db, settings)
    return TestClient(api), settings


def extract(response):
    assert response.status_code == 200, response.text
    with ZipFile(BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {'report.md','trace.json','diagnosis-context.md','evidence-manifest.json'}
        body = {name:archive.read(name) for name in archive.namelist()}
    manifest = json.loads(body['evidence-manifest.json'])
    for name, item in manifest['exported_files'].items():
        assert sha256(body[name]).hexdigest() == item['sha256']
        assert len(body[name]) == item['bytes']
    return body, json.loads(body['trace.json'])


def test_design_stage_owner_isolation_auth_and_read_only(postgres_database, tmp_path, monkeypatch):
    db = postgres_database
    target = simple(db, condition='AWAITING_APPROVAL', title='DESIGN 阶段需要 Human 决定')
    sibling = simple(db, title='sibling-private-marker')
    foreign = simple(db, owner='human:another', title='foreign-private-marker')
    with db.engine.begin() as conn:
        interaction = uuid4()
        conn.execute(insert(metadata.tables['product_interactions']).values(
            id=interaction, created_by='human:owner', updated_by='human:owner',
            condition='OPEN', current_work_id=target))
        conn.execute(insert(metadata.tables['interaction_records']).values(
            id=uuid4(), interaction_id=interaction, sequence=1, actor='HUMAN',
            source='test', content='请先设计；token=fixture-secret-123',
            content_fingerprint='a'*64, supporting_references=[], work_focus_id=target))
        for sequence in range(2, 41):
            conn.execute(insert(metadata.tables['interaction_records']).values(
                id=uuid4(), interaction_id=interaction, sequence=sequence, actor='WATT',
                source='test', content=f'已保存对话 {sequence}',
                content_fingerprint=f'{sequence:064x}', supporting_references=[], work_focus_id=target))
    monkeypatch.setenv('SPG_DIAGNOSTIC_EXPORT_MAX_ROWS_PER_TABLE','30')
    watched = ['product_works','interaction_records','production_work_units',
        'baseline_candidates','governance_records']
    def counts():
        with db.engine.connect() as conn:
            return {name:conn.scalar(select(func.count()).select_from(metadata.tables[name])) for name in watched}
    before = counts()
    with client(db, tmp_path)[0] as api:
        path = f'/api/admin/works/{target}/diagnostic'
        assert api.get(path).status_code == 401
        api.post('/auth/session', json={'token':'test-operator-token-1234567890-long'})
        assert api.get(f'/api/admin/works/{foreign}/diagnostic').status_code == 409
        assert api.get(f'/api/admin/works/{uuid4()}/diagnostic').status_code == 409
        assert api.get(path+'?mode=invalid').status_code == 409
        assert api.get(path+'?file=../../private.env').status_code == 409
        compact_response = api.get(path)
        body, evidence = extract(compact_response)
        full, full_evidence = extract(api.get(path+'?mode=full'))
        for name in ('report.md','trace.json','evidence-manifest.json'):
            response = api.get(path+'?file='+name)
            assert response.status_code == 200
            assert response.headers['x-evidence-sha256'] == sha256(response.content).hexdigest()
    assert counts() == before
    assert str(target) == evidence['work_id'] == full_evidence['work_id']
    assert evidence['lifecycle']['units'] == evidence['lifecycle']['candidate'] == []
    assert evidence['lifecycle']['capture_truncation']['interaction_records']['observed_count'] == 40
    assert evidence['lifecycle']['capture_truncation']['interaction_records']['exported_count'] <= 30
    assert 'PASS' not in body['report.md'].decode().split('## D. Production Lifecycle')[1].split('## E. Diagnostics')[0]
    for marker in ('fixture-secret-123','sibling-private-marker','foreign-private-marker',str(sibling),str(foreign)):
        assert marker not in str(body) and marker not in str(full)
    assert '请先设计' in body['report.md'].decode()
    assert full_evidence['lifecycle']['detail_level'] == 'full'


def test_production_work_has_pwu_candidate_and_exact_sources(postgres_database, tmp_path):
    db = postgres_database
    _service, work_id, _delivery, _ = produce(db, tmp_path, authorize_candidate=False,
        set_delivery_target=False)
    # The owner identity is resolved from the Registry, then the same exact
    # Work is sent to Trace; no consumer-supplied source revision is accepted.
    product_id = uuid4()
    with db.engine.begin() as conn:
        conn.execute(insert(metadata.tables['software_products']).values(
            id=product_id, owner_id='human:owner', name='diagnostic fixture', lifecycle='ACTIVE'))
        conn.execute(update(metadata.tables['product_works']).where(
            metadata.tables['product_works'].c.id == work_id).values(product_id=product_id))
    row = WorkRegistryService(db).get('human:owner', work_id)
    assert row['product_id']
    with client(db, tmp_path)[0] as api:
        api.post('/auth/session', json={'token':'test-operator-token-1234567890-long'})
        _, evidence = extract(api.get(f'/api/admin/works/{work_id}/diagnostic?mode=full'))
    lifecycle = evidence['lifecycle']
    assert lifecycle['units'] and lifecycle['candidate']
    assert any(ref.startswith('production_work_units:') for ref in
        (event['source_ref'] for event in lifecycle['timeline']))
    assert not evidence['capture'].get('global_atomic_snapshot')
