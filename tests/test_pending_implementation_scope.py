"""Pending reversible scope does not claim behavior/necessity PASS."""
from contextlib import contextmanager
from types import SimpleNamespace
import subprocess
from uuid import uuid4

import pytest

from spg.application.semantic_steps import SemanticStepApplicationService
from spg.domain.change import ProductionTargetKind
from tests.test_staged_production_brief import basis


@pytest.fixture
def pending_case(tmp_path, monkeypatch):
    import spg.application.semantic_steps as module
    revision, ir = basis()
    # Exact existing test IR carries explicit index.html. For a new surface
    # choice use the same authorized goal without specifying implementation HOW.
    items = tuple(i.model_copy(update={'production':i.production.model_copy(update={'target_paths':()})})
        if i.production else i for i in ir.items)
    ir = ir.model_copy(update={'items':items})
    repo = tmp_path/'repo'; repo.mkdir()
    subprocess.run(['git','init','-q',str(repo)],check=True)
    subprocess.run(['git','-C',str(repo),'config','user.name','Qualification'],check=True)
    subprocess.run(['git','-C',str(repo),'config','user.email','test@example.invalid'],check=True)
    (repo/'README.md').write_text('Managed workspace\n')
    subprocess.run(['git','-C',str(repo),'add','README.md'],check=True)
    subprocess.run(['git','-C',str(repo),'commit','-qm','seed'],check=True)
    git = lambda *args: subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
    revision = revision.model_copy(update={'source_revision':git('rev-parse','HEAD')})
    monkeypatch.setattr(module,'ProductStore',lambda _:SimpleNamespace(current_work_reality_revision=lambda _:revision))
    @contextmanager
    def uow():yield SimpleNamespace(session=None)
    service = SemanticStepApplicationService.__new__(SemanticStepApplicationService)
    service.database=SimpleNamespace(unit_of_work=uow)
    current=SimpleNamespace(work_id=revision.work_id, governed_semantic_ir=ir.model_dump(mode='json'),
        governed_semantic_ir_id=ir.id, canonical_explicit_targets=(), canonical_allowed_areas=(),
        required_intermediate_artifacts=(), repository_identity='watt://work-branches/'+str(revision.work_id),
        repository_location=str(repo), source_revision=revision.source_revision, source_tree=git('rev-parse','HEAD^{tree}'),
        human_explicit_requests=(ir.items[0].provenance[0].source_text,))
    proposal=SimpleNamespace(target_kind=ProductionTargetKind.CODE_WORK,code_targets=('index.html','styles.css','app.js'),allowed_areas=())
    return service,current,proposal,repo,git


def test_new_multifile_implementation_scope_stays_pending_with_complete_brief(pending_case):
    service,current,proposal,_,_=pending_case
    result=service._source_preserving_scope(current,proposal)
    assert result.evidence_status=='PENDING_ARTIFACT_VERIFICATION'
    assert {p.path for p in result.required_targets}==set(proposal.code_targets)
    assert all(p.evidence_kind=='NEW_TARGET_PENDING_VERIFICATION' for p in result.required_targets)
    assert all(p.source_revision==current.source_revision and p.source_tree==current.source_tree for p in result.required_targets)
    assert 'actual Verification' in result.explanation


@pytest.mark.parametrize('change',['foreign-repo','changed-tree','area','existing-implementation','missing-source','explicit-scope-drift'])
def test_unproved_or_expanded_scope_keeps_existing_review(pending_case,change):
    service,current,proposal,repo,git=pending_case
    if change=='foreign-repo':current.repository_identity='https://example.invalid/repo'
    elif change=='changed-tree':current.source_tree='0'*40
    elif change=='area':proposal.allowed_areas=('src/app/**',)
    elif change=='missing-source':current.governed_semantic_ir=None
    elif change=='explicit-scope-drift':current.canonical_explicit_targets=('one.html',)
    else:
        (repo/'existing.js').write_text('function keep() {}')
        subprocess.run(['git','-C',str(repo),'add','existing.js'],check=True)
        subprocess.run(['git','-C',str(repo),'commit','-qm','existing'],check=True)
        current.source_revision=git('rev-parse','HEAD');current.source_tree=git('rev-parse','HEAD^{tree}')
    assert service._source_preserving_scope(current,proposal) is None


def test_existing_import_keeps_exact_human_selected_scope_pending(pending_case):
    service,current,proposal,repo,git=pending_case
    current.repository_identity='https://example.invalid/controlled-import'
    proposal.code_targets=('index.html',)
    current.canonical_explicit_targets=proposal.code_targets
    (repo/'index.html').write_text('<html>Existing implementation</html>')
    subprocess.run(['git','-C',str(repo),'add','index.html'],check=True)
    subprocess.run(['git','-C',str(repo),'commit','-qm','existing'],check=True)
    from spg.application import semantic_steps as module
    # The immutable Work source remains the originally imported baseline.
    # Change only the local Git fixture before reconstructing that Work view.
    current.source_revision=git('rev-parse','HEAD');current.source_tree=git('rev-parse','HEAD^{tree}')
    import unittest.mock
    revision,ir=basis()
    revision=revision.model_copy(update={'source_revision':current.source_revision})
    with unittest.mock.patch.object(module,'ProductStore',lambda _:SimpleNamespace(current_work_reality_revision=lambda _:revision)):
        result=service._source_preserving_scope(current,proposal)
    assert result is not None and result.evidence_status=='PENDING_ARTIFACT_VERIFICATION'
    assert result.required_targets==()  # Existing exact paths need no invented new-file proof.
