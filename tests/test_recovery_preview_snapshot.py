from contextlib import contextmanager
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from spg.application import recovery_preview as module
from spg.domain.product import ProductInvariantViolation


@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    work_id, revision, record_id = uuid4(), uuid4(), uuid4()
    files = {'index.html': sha256(b'<h1>retained</h1>').hexdigest()}
    identity = sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    record = SimpleNamespace(id=record_id, decision_type='WORK_RECOVERY_PREVIEW', scope={
        'work_id': str(work_id), 'work_reality_revision_id': str(revision),
        'snapshot': identity, 'files': files})
    work = SimpleNamespace(current_work_reality_revision_id=revision)
    monkeypatch.setattr(module, 'ProductStore', lambda _: SimpleNamespace(work=lambda _: work))
    monkeypatch.setattr(module, 'RuntimeStore', lambda _: SimpleNamespace(governance_for_subject=lambda _: [record]))
    class Database:
        @contextmanager
        def unit_of_work(self):
            yield SimpleNamespace(session=None)
    directory = tmp_path / str(work_id) / identity
    directory.mkdir(parents=True)
    (directory / 'index.html').write_bytes(b'<h1>retained</h1>')
    return Database(), work_id, revision, record, work, tmp_path, identity


def test_recovery_preview_serves_exact_bytes_without_verification_or_acceptance(snapshot):
    db, wid, _, _, _, root, identity = snapshot
    view = module.recovery_preview_context(db, wid)
    assert view['verification'] == 'NOT_QUALIFIED'
    assert view['authorization_pending'] is True
    assert 'candidate_id' not in view
    assert module.recovery_preview_artifact(db, root, wid, identity, 'index.html') == b'<h1>retained</h1>'


def test_recovery_preview_rejects_mutated_artifact_and_out_of_manifest_path(snapshot):
    db, wid, _, _, _, root, identity = snapshot
    for path in ['../index.html', '/index.html', 'secret.env']:
        with pytest.raises(ProductInvariantViolation):
            module.recovery_preview_artifact(db, root, wid, identity, path)
    (root / str(wid) / identity / 'index.html').write_bytes(b'changed')
    with pytest.raises(ProductInvariantViolation, match='identity differs'):
        module.recovery_preview_artifact(db, root, wid, identity, 'index.html')


def test_recovery_preview_invalidates_on_new_work_reality(snapshot):
    db, wid, _, record, work, _, _ = snapshot
    work.current_work_reality_revision_id = uuid4()
    assert module.recovery_preview_context(db, wid) is None
    record.scope['work_reality_revision_id'] = str(work.current_work_reality_revision_id)
    record.scope['files']['index.html'] = 'f' * 64
    with pytest.raises(ProductInvariantViolation, match='manifest identity differs'):
        module.recovery_preview_context(db, wid)


def test_generated_static_snapshot_is_inspectable_before_semantic_verification(tmp_path, monkeypatch):
    import subprocess
    repo = tmp_path / 'repo'; repo.mkdir()
    def git(*args):return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL, text=True).strip()
    git('init', '-b', 'main'); git('config', 'user.name', 'Preview'); git('config', 'user.email', 'preview@example.invalid')
    (repo / '.env').write_text('FAKE_TEST_ONLY_SECRET=must-not-be-served')
    git('add', '.'); git('commit', '-m', 'source'); base = git('rev-parse', 'HEAD')
    (repo / 'index.html').write_text('<script src="app.js"></script>')
    (repo / 'app.js').write_text('document.title = "Observed preview";')
    git('add', '.'); git('commit', '-m', 'generated implementation')
    wid, rid, run, plan, sid = (uuid4() for _ in range(5))
    work = SimpleNamespace(current_work_reality_revision_id=rid)
    binding = SimpleNamespace(production_run_id=run, plan_revision_id=plan, work_reality_revision_id=rid)
    proposed = SimpleNamespace(work_unit_id=uuid4(), attempt_id=uuid4(),
        proposed_commit_identity=git('rev-parse', 'HEAD'), tree_identity=git('rev-parse', 'HEAD^{tree}'))
    contract = SimpleNamespace(source_revision=base, exact_targets=(SimpleNamespace(path='index.html'),),
        allows_path=lambda p: p in {'index.html', 'app.js'})
    unit = SimpleNamespace(production_run_id=run, plan_revision_id=plan,
        completion_contract=SimpleNamespace(change_contract=contract))
    records = []
    product = SimpleNamespace(work=lambda _: work, runtime_binding=lambda _: binding)
    runtime = SimpleNamespace(proposed_snapshot=lambda _: proposed, work_unit=lambda _: unit,
        execution_dispatch_for_attempt=lambda _: SimpleNamespace(workspace=SimpleNamespace(repository_path=repo)),
        governance_for_subject=lambda _: records, insert_governance=lambda r: records.append(SimpleNamespace(**r)))
    monkeypatch.setattr(module, 'ProductStore', lambda _: product)
    monkeypatch.setattr(module, 'RuntimeStore', lambda _: runtime)
    class Database:
        @contextmanager
        def unit_of_work(self):yield SimpleNamespace(session=None, commit=lambda: None)
    db = Database(); root = tmp_path / 'previews'
    result = module.capture_working_preview(db, root, wid, sid)
    assert result['status'] == 'AVAILABLE' and result['verification'] == 'NOT_QUALIFIED'
    assert '.env' not in result['files']
    assert module.recovery_preview_artifact(db, root, wid, result['snapshot'], 'app.js') == (repo/'app.js').read_bytes()
    assert all(r.decision_type == 'WORKING_PREVIEW_OBSERVED' for r in records)
    (repo / 'outside.js').write_text('unauthorized change')
    git('add', '.'); git('commit', '-m', 'out of scope')
    proposed.proposed_commit_identity = git('rev-parse', 'HEAD'); proposed.tree_identity = git('rev-parse', 'HEAD^{tree}')
    assert module.capture_working_preview(db, root, wid, uuid4()) is None
    assert len(records) == 1
    binding.plan_revision_id = uuid4()
    assert module.recovery_preview_context(db, wid) is None
