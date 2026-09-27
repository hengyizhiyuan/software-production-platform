"""Canonical meaning and literal source evidence are distinct contracts."""
from pathlib import Path
import subprocess
from uuid import uuid4

import pytest

from spg.application.semantic_steps import SemanticStepApplicationService, MAX_CONTEXT_FILES
from spg.domain.refinement import RepositoryChangeProposalRequest, RepositoryTargetNecessityProof
from spg.providers.repository_change_proposal import RepositoryAwareChangeProposalProvider


def test_large_inventory_preserves_implementation_observations():
    paths = tuple(f'src/pkg/module_{i}.py' for i in range(200)) + ('web/index.html','web/app.js')
    selected = SemanticStepApplicationService._observation_paths(('README.md',), paths)
    assert len(selected) <= MAX_CONTEXT_FILES
    assert {'README.md','web/index.html','web/app.js'} <= set(selected)
    assert selected == SemanticStepApplicationService._observation_paths(('README.md',),paths)


def test_canonical_paraphrase_does_not_invalidate_literal_human_scope_witness(tmp_path):
    def git(*args):
        return subprocess.run(['git','-C',str(tmp_path),*args],check=True,capture_output=True,text=True).stdout.strip()
    git('init','-b','main')
    (tmp_path/'widget.js').write_text('cancel.addEventListener("click", closeDialog);\n')
    git('add','.')
    git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','baseline')
    request=RepositoryChangeProposalRequest(work_id=uuid4(),engineering_resource_id=uuid4(),
        repository_identity='fixture',repository_location=str(tmp_path),source_baseline_id=uuid4(),
        source_ref='refs/heads/main',source_revision=git('rev-parse','HEAD'),
        refined_code_intent='Clicking cancel closes the dialog',human_authority_text='取消按钮点了没反应，修一下',
        governed_semantic_ir_id=uuid4(),candidate_targets=('widget.js',),necessity_proofs=(
            RepositoryTargetNecessityProof(path='widget.js',source_path='widget.js',
                repository_quote='cancel.addEventListener',human_clause='取消按钮点了没反应',
                necessity='The observed cancel handler implements the admitted dialog behavior'),))
    provider=RepositoryAwareChangeProposalProvider()
    assert tuple(t.path for t in provider.propose(request).required_targets)==('widget.js',)
    forged=request.model_copy(update={'human_authority_text':'Discuss navigation only'})
    with pytest.raises(ValueError,match='no exact repository/Human witness'):
        provider.propose(forged)
    unsupported=request.model_copy(update={'necessity_proofs':()})
    assert provider.propose(unsupported).required_targets == ()
