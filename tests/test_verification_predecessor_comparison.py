from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from types import SimpleNamespace as NS
from uuid import uuid4
import subprocess
import pytest
from spg.application import verification_comparison as comparison


@pytest.fixture
def predecessor(tmp_path, monkeypatch):
    def git(*args):return subprocess.check_output(['git','-C',str(tmp_path),*args]).decode().strip()
    git('init','-b','main');git('config','user.name','Owner');git('config','user.email','owner@example.invalid')
    (tmp_path/'page.html').write_text('<main>Previous report layout</main>')
    (tmp_path/'unrelated.md').write_text('outside selected comparison paths')
    git('add','.');git('commit','-m','sealed predecessor')
    oid=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
    now=datetime.now(timezone.utc);wid,rid,parent,pwu,cid,sid,vid=[uuid4() for _ in range(7)]
    revision=NS(id=rid,work_id=wid,previous_revision_id=parent,created_at=now)
    binding=NS(work_reality_revision_id=parent,work_unit_id=pwu)
    candidate=NS(id=cid,sealed_at=now-timedelta(minutes=1),repository_identity='repo:reports',
        proposed_snapshot_id=sid,proposed_commit_identity=oid,proposed_tree_identity=tree,
        verification_record_ids=(vid,),fingerprint='f'*64)
    snapshot=NS(attempt_id=uuid4(),proposed_commit_identity=oid,tree_identity=tree)
    record=NS(result=NS(value='PASS'),proposed_commit_identity=oid,tree_identity=tree)
    state=NS(revision=revision,bindings=[binding],candidates=[candidate],snapshot=snapshot,
        record=record,dispatch=NS(workspace=NS(repository_path=str(tmp_path))))
    class Product:
        def __init__(self,session):pass
        def work_reality_revision(self,identity):assert identity==rid;return state.revision
        def runtime_bindings(self,identity):assert identity==wid;return state.bindings
    class Runtime:
        def __init__(self,session):pass
        def baseline_candidates_for_work_unit(self,identity):assert identity==pwu;return state.candidates
        def proposed_snapshot(self,identity):assert identity==sid;return state.snapshot
        def verification_record(self,identity):assert identity==vid;return state.record
        def execution_dispatch_for_attempt(self,identity):assert identity==snapshot.attempt_id;return state.dispatch
    class Database:
        @contextmanager
        def unit_of_work(self):yield NS(session=object())
    monkeypatch.setattr(comparison,'ProductStore',Product);monkeypatch.setattr(comparison,'RuntimeStore',Runtime)
    contract=NS(repository_identity='repo:reports',exact_targets=(NS(path='page.html'),))
    return Database(),state,contract,tmp_path


def test_only_exact_immediate_predecessor_is_read_without_source_promotion(predecessor):
    db,s,contract,repo=predecessor
    before=(repo/'page.html').read_bytes()
    result=comparison.predecessor_candidate_sources(db,s.revision.id,contract)
    assert len(result)==1
    artifact=result[0]
    assert artifact['comparison_only'] and not artifact['grants_current_pass_or_authority']
    assert artifact['candidate_id']==str(s.candidates[0].id)
    assert artifact['work_reality_revision_id']==str(s.revision.previous_revision_id)
    assert set(artifact['sources'])=={'page.html'}
    assert artifact['sources']['page.html']['sha256']==sha256(before).hexdigest()
    assert (repo/'page.html').read_bytes()==before


@pytest.mark.parametrize('change',['no-parent','wrong-revision','no-candidate','future-candidate'])
def test_absent_predecessor_is_explicitly_absent(predecessor,change):
    db,s,c,_=predecessor
    if change=='no-parent':s.revision.previous_revision_id=None
    elif change=='wrong-revision':s.bindings[0].work_reality_revision_id=uuid4()
    elif change=='no-candidate':s.candidates=[]
    else:s.candidates[0].sealed_at=s.revision.created_at+timedelta(seconds=1)
    assert comparison.predecessor_candidate_sources(db,s.revision.id,c)==()


@pytest.mark.parametrize('change',['repository','snapshot','verification','unverified','tree','missing-workspace'])
def test_invalid_predecessor_does_not_supply_comparison_evidence(predecessor,change):
    db,s,c,_=predecessor
    if change=='repository':s.candidates[0].repository_identity='other:repo'
    elif change=='snapshot':s.snapshot.tree_identity='0'*40
    elif change=='verification':s.record.result.value='UNKNOWN'
    elif change=='unverified':s.candidates[0].verification_record_ids=()
    elif change=='tree':
        s.candidates[0].proposed_tree_identity='0'*40;s.snapshot.tree_identity='0'*40;s.record.tree_identity='0'*40
    else:s.dispatch=None
    with pytest.raises(ValueError,match='VERIFICATION_COMPARISON_'):
        comparison.predecessor_candidate_sources(db,s.revision.id,c)
