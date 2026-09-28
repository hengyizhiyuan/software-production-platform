"""Real database and Git effects, driven by declared semantic compiler fixtures."""
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
import subprocess
import time

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import delete, select, inspect

from spg.application.assets import RepositoryAssetService
from spg.application.interaction import WorkInteractionService
from spg.application.intent_realization import IntentRealizationViolation
from spg.domain.intent_realization import (
    AtomicBranchEffect, OperationalIntent, SemanticArgument, SemanticClause, SemanticItem, SemanticKind,
    SemanticOrigin, SemanticProvenance, TurnSemanticCandidate, ObligationState,
)
from spg.domain.interaction import InteractionAssessmentCandidate
from spg.domain.interaction_actions import ActionSpeechAct
from spg.domain.wic_response import WicRuntimeMode
from spg.infrastructure.persistence.intent_realization_store import IntentRealizationStore
from spg.infrastructure.production_environment import GitRepositoryAcquirer


class DeclaredCompiler:
    """The test sets its semantic oracle; it never routes Human phrase patterns."""
    operation = None
    arguments = {}
    speech_act = ActionSpeechAct.EXPLICIT_REQUEST
    conditional = False
    calls = 0

    def interpret(self, basis):
        self.calls += 1
        record = basis.records[-1]
        provenance = SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
            source_record_id=record.id, source_text=record.content)
        branch_effects = {"CREATE_BRANCH": ("CREATE_BRANCH",),
            "SWITCH_BRANCH": ("SWITCH_BRANCH",),
            "CREATE_AND_SWITCH_BRANCH": ("CREATE_BRANCH", "SWITCH_BRANCH")}.get(str(self.operation), ())
        action = None if self.operation is None else OperationalIntent(operation=self.operation,
            arguments={key: SemanticArgument(value=value, provenance=provenance)
                for key, value in self.arguments.items()}, speech_act=self.speech_act,
            conditional=self.conditional,
            atomic_branch_effects=tuple(AtomicBranchEffect(effect=effect,
                target_branch=self.arguments["target_branch"], provenance=provenance)
                for effect in branch_effects if "target_branch" in self.arguments))
        item = SemanticItem(item_id="current", kind=SemanticKind.EXPLORE if action is None
            else SemanticKind.OPERATIONAL_ACTION, statement="Declared compiler meaning",
            provenance=(provenance,), confidence=1, action=action)
        return InteractionAssessmentCandidate(semantic_intent=TurnSemanticCandidate(items=(item,),
            clauses=(SemanticClause(clause_id="full-turn", source_record_id=record.id,
                source_text=record.content, semantic_item_ids=(item.item_id,),
                speech_act=self.speech_act if branch_effects else None,
                polarity="AFFIRMATIVE" if branch_effects else "UNRESOLVED",
                modality="REQUEST" if branch_effects else "UNRESOLVED",
                temporal_scope="CURRENT" if branch_effects else "UNRESOLVED",
                requested_effects=branch_effects),)),
            natural_response="可以讨论这项想法。", provider_identity="fixture:declared-irk")


@pytest.fixture
def runtime(postgres_database, tmp_path, monkeypatch):
    monkeypatch.setenv("SPG_DATABASE_URL", postgres_database.engine.url.render_as_string(hide_password=False))
    command.upgrade(Config("alembic.ini"), "head")
    compiler = DeclaredCompiler()
    assets = RepositoryAssetService(postgres_database, tmp_path / "assets", tmp_path)
    service = WorkInteractionService(postgres_database, capability=compiler,
        runtime_mode=WicRuntimeMode.WIC_VNEXT_CONTROLLED)
    service.configure_repository_actions(assets.execute_interaction_actions, assets.interaction_observation)
    source = tmp_path / "source"
    source.mkdir()
    def git(*args):
        return subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True, text=True).stdout.strip()
    git("init", "-b", "main")
    (source / "README.md").write_text("# Real owner fixture\n")
    git("add", ".")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
    real = assets.repository_acquirer
    class LocalRemote(GitRepositoryAcquirer):
        def acquire(self, root, remote, destination, **kwargs):
            return real.acquire(root, str(source), destination)
    assets.repository_acquirer = LocalRemote()
    interaction = service.create_interaction(human_identity="human:owner")
    yield service, assets, compiler, interaction, git("rev-parse", "HEAD")
    service.shutdown()


def settled(service, interaction, text):
    turn = service.submit_turn(interaction.id, text, human_identity="human:owner")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        current = service.get_turn(turn.id)
        if current.status.value in {"COMPLETED", "FAILED"}:
            assert current.status.value == "COMPLETED", current.failure_message
            return turn, service.realization_projection(turn.id)
        time.sleep(.02)
    pytest.fail("Turn did not reach a terminal outcome")


def acquired(runtime):
    service, assets, compiler, interaction, revision = runtime
    source_url = f"https://github.com/acme/irk-{interaction.id.hex}.git"
    compiler.operation = "ACQUIRE_REPOSITORY"
    compiler.arguments = {"repository_source": source_url}
    turn, projection = settled(service, interaction, f"请获取 {source_url}")
    assert projection["obligations"][0]["state"] == "SATISFIED"
    assert projection["obligations"][0]["observed_effect"]["facts"]["revision"] == revision
    return service, assets, compiler, interaction


def test_actual_branch_effect_and_single_compiler_call(runtime):
    service, assets, compiler, interaction = acquired(runtime)
    compiler.operation = "CREATE_AND_SWITCH_BRANCH"
    compiler.arguments = {"target_branch": "feat_feedback"}
    turn, projection = settled(service, interaction, "切个新分支：feat_feedback")
    obligation = projection["obligations"][0]
    assert compiler.calls == 2  # Exactly one interpretation per Turn.
    assert obligation["state"] == "SATISFIED"
    assert [effect["predicate"] for effect in obligation["expected_effects"]] == ["BRANCH_EXISTS", "CURRENT_BRANCH"]
    assert obligation["observed_effect"]["facts"]["repository_ref"] == "refs/heads/feat_feedback"
    assert len(assets.attempts_for_interaction(interaction.id)) == 2
    request = assets.attempts_for_interaction(interaction.id)[-1]["request"]
    assert request["expected_base_revision"] == obligation["expected_effects"][0]["exact_revision"]
    assert request["expected_base_tree"] == obligation["observed_effect"]["facts"]["tree"]
    assert service.get_shared_understanding(interaction.id).governed_work_id is None
    # Reconstruction is solely from the database, not a session/model memory.
    with service.database.unit_of_work() as uow:
        restored = IntentRealizationStore(uow.session)
        restored.validate_completion(turn.id)
        assert restored.projection(turn.id) == projection


def test_failed_compilation_keeps_a_governed_nonexecutable_turn_envelope(runtime, monkeypatch):
    service, _assets, compiler, interaction, _revision = runtime
    def invalid_candidate(_basis):
        raise ValueError("Compiler did not establish a valid semantic candidate")
    monkeypatch.setattr(compiler, "interpret", invalid_candidate)
    turn = service.submit_turn(interaction.id, "Create a feature from this request",
        human_identity="human:owner")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if service.get_turn(turn.id).status.value == "FAILED":
            break
        time.sleep(.02)
    projection = service.realization_projection(turn.id)
    envelope = projection["semantic_envelope"]
    assert envelope["state"] == "SEMANTIC_COMPILATION_FAILED"
    assert envelope["source_record_id"] == str(turn.request_record_id)
    assert envelope["attempt"] == 1
    assert envelope["blocker"]["code"]
    assert projection["semantic_ir"] is None
    assert projection["obligations"] == []
    assert projection["historical_without_ir"] is False


@pytest.mark.parametrize("operation", ["CREATE_BRANCH", "CREATE_AND_SWITCH_BRANCH", "SWITCH_BRANCH"])
def test_persisted_exact_baseline_blocks_drift_before_branch_effect(runtime, operation):
    from uuid import UUID
    from spg.infrastructure.persistence.product_store import ProductStore
    service, assets, compiler, interaction = acquired(runtime)
    original_observation = assets.interaction_observation(interaction.id)
    with service.database.unit_of_work() as uow:
        resource = ProductStore(uow.session).resource(UUID(original_observation["resource_id"]))
    repository = Path(resource.location_ref)
    def git(*args):
        return subprocess.run(["git", "-C", str(repository), *args],
            check=True, capture_output=True, text=True).stdout.strip()
    if operation == "SWITCH_BRANCH":
        git("branch", "feat_drift")
    original_start = assets.start_intake
    captured = {}
    def start_then_drift(request):
        receipt = original_start(request)
        if request.target_branch:
            captured["request"] = request
            (repository / "README.md").write_text("# Later repository version\n")
            git("add", "README.md")
            git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture baseline drift")
            captured["refs"] = git("for-each-ref", "--format=%(refname) %(objectname)")
        return receipt
    assets.start_intake = start_then_drift
    compiler.operation = operation
    compiler.arguments = {"target_branch": "feat_drift"}
    _, projection = settled(service, interaction, "Realize the requested local branch feat_drift")
    assert captured["request"].expected_base_revision == original_observation["revision"]
    assert captured["request"].expected_base_tree == original_observation["tree"]
    failed = assets.attempts_for_interaction(interaction.id)[-1]
    assert failed["technical_evidence"]["signal"] == "ACTION_REQUIRES_REALITY_REFRESH"
    assert failed["technical_evidence"]["effect_observed"] is False
    assert not (assets.asset_root / str(captured["request"].request_id)).exists()
    assert git("for-each-ref", "--format=%(refname) %(objectname)") == captured["refs"]
    assert projection["obligations"][0]["state"] == "BLOCKED_WITH_EVIDENCE"
    # An untrusted Git change cannot be silently exposed as READY, and old
    # acquisition evidence remains the original immutable observation.
    assert assets.observation(resource.id)["condition"] == "BLOCKED"
    assert assets.attempts_for_interaction(interaction.id)[0]["revision"] == original_observation["revision"]


def test_fresh_asset_observation_requires_matching_trusted_runtime_pointer(runtime):
    from uuid import UUID
    from spg.infrastructure.persistence.product_store import ProductStore
    from spg.infrastructure.persistence.runtime_store import RuntimeStore
    service, assets, _, interaction = acquired(runtime)
    before = assets.interaction_observation(interaction.id)
    with service.database.unit_of_work() as uow:
        resource = ProductStore(uow.session).resource(UUID(before["resource_id"]))
        pointer = RuntimeStore(uow.session).current_pointer(
            repository_identity=resource.repository_identity, repository_ref=resource.authoritative_ref)
    repository = Path(resource.location_ref)
    def git(*args):
        return subprocess.run(["git", "-C", str(repository), *args],
            check=True, capture_output=True, text=True).stdout.strip()
    (repository / "README.md").write_text("# Current accepted fixture version\n")
    git("add", "README.md")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "later owner fixture")
    revision, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
    assert assets.observation(resource.id)["condition"] == "BLOCKED"
    # The persistence fixture now supplies the existing Runtime owner's trusted
    # pointer. This tests projection validation, not a Human acceptance claim.
    snapshot_id = uuid4()
    with service.database.unit_of_work() as uow:
        runtime_store = RuntimeStore(uow.session)
        runtime_store.insert_snapshot({"id": snapshot_id, "condition": "TRUSTED",
            "repository_identity": resource.repository_identity, "repository_ref": resource.authoritative_ref,
            "repository_revision": revision, "repository_tree_identity": tree,
            "source_baseline_id": pointer.snapshot_id, "created_at": datetime.now(UTC)})
        runtime_store.update_baseline_pointer(pointer.version, snapshot_id,
            expected_snapshot_id=pointer.snapshot_id)
        uow.commit()
    refreshed = assets.observation(resource.id)
    assert (refreshed["condition"], refreshed["revision"], refreshed["tree"]) == ("READY", revision, tree)
    assert refreshed["technical_evidence"]["trusted_snapshot_id"] == str(snapshot_id)
    assert assets.interaction_observation(interaction.id)["fingerprint"] == refreshed["fingerprint"]
    assert assets.observation(resource.id) == refreshed
    assert assets.attempts_for_interaction(interaction.id)[0]["revision"] == before["revision"]


def test_negated_semantics_cannot_be_overridden_by_github_keywords(runtime):
    service, assets, compiler, interaction, _ = runtime
    compiler.operation = "SEARCH_GITHUB"
    compiler.speech_act = ActionSpeechAct.DISCUSSION
    turn, projection = settled(service, interaction, "不要搜索 GitHub，告诉我 Search 路由原理。")
    assert projection["obligations"] == []
    assert assets.attempts_for_interaction(interaction.id) == ()
    assert compiler.calls == 1


@pytest.mark.parametrize("additional_human_fact", [False, True])
def test_constraint_acknowledgement_does_not_invent_prior_execution_history(runtime, additional_human_fact):
    service, assets, compiler, interaction = acquired(runtime)
    before = assets.interaction_observation(interaction.id)
    original = compiler.interpret
    def compile_constraint(basis):
        candidate = original(basis)
        item = candidate.semantic_intent.items[0].model_copy(update={
            "kind": SemanticKind.CONSTRAINT, "action": None,
            "statement": "Keep the current Candidate for review; do not deliver"})
        items = (item,)
        if additional_human_fact:
            items += (item.model_copy(update={"item_id": "review-fact", "kind": SemanticKind.FACT,
                "statement": "Human wishes to review this version"}),)
        clause = candidate.semantic_intent.clauses[0].model_copy(update={
            "semantic_item_ids": tuple(i.item_id for i in items)})
        return candidate.model_copy(update={
            "natural_response": "I will continue changing the product. No acquisition has ever completed.",
            "semantic_intent": candidate.semantic_intent.model_copy(update={"items": items, "clauses": (clause,)})})
    compiler.interpret = compile_constraint
    _, projection = settled(service, interaction, "保留当前版本待审阅，暂不交付")
    assert projection["obligations"] == []  # Recorded constraints grant no execution.
    assert projection["semantic_ir"]["items"][0]["kind"] == "CONSTRAINT"
    assert assets.interaction_observation(interaction.id) == before
    assert len(assets.attempts_for_interaction(interaction.id)) == 1
    assert compiler.calls == 2
    answer = service.get_shared_understanding(interaction.id).conversation_messages[-1].content
    assert answer == "已记录当前约束：Keep the current Candidate for review; do not deliver"


def test_unrealized_branch_records_actual_mismatch_and_refinement(runtime):
    service, assets, compiler, interaction = acquired(runtime)
    compiler.operation = "CREATE_AND_SWITCH_BRANCH"
    compiler.arguments = {"target_branch": "feat_feedback"}
    service.configure_repository_actions(lambda *_: "我会建立分支。", assets.interaction_observation)
    turn, projection = settled(service, interaction, "建立 feat_feedback 并切过去")
    obligation = projection["obligations"][0]
    assert obligation["state"] == "BLOCKED_WITH_EVIDENCE"
    assert obligation["observed_effect"]["facts"]["repository_ref"] == "refs/heads/main"
    assert projection["refinements"][0]["signal"] == "EXPECTED_EFFECT_NOT_REALIZED"
    answer = service.get_shared_understanding(interaction.id).conversation_messages[-1].content
    assert "我会建立分支" not in answer
    assert "尚未完成" in answer


def test_conditional_action_requires_human_and_does_not_execute(runtime):
    service, assets, compiler, interaction = acquired(runtime)
    compiler.operation = "CREATE_AND_SWITCH_BRANCH"
    compiler.arguments = {"target_branch": "feat_maybe"}
    compiler.conditional = True
    _, projection = settled(service, interaction, "如果通过评审再切到 feat_maybe")
    assert projection["obligations"][0]["state"] == "REQUIRES_HUMAN"
    assert len(assets.attempts_for_interaction(interaction.id)) == 1


def test_terminal_ledger_cannot_replay_and_missing_obligation_cannot_complete(runtime):
    service, assets, compiler, interaction = acquired(runtime)
    compiler.operation = "QUERY_CURRENT_BRANCH"
    compiler.arguments = {}
    turn, projection = settled(service, interaction, "我现在在哪个分支？")
    with service.database.unit_of_work() as uow:
        ledger = IntentRealizationStore(uow.session)
        obligation = ledger.obligations(turn.id)[0]
        with pytest.raises(IntentRealizationViolation, match="terminal obligation"):
            ledger.transition(obligation, state=ObligationState.RUNNING)
        from spg.infrastructure.persistence.intent_realization_schema import turn_obligations
        uow.session.execute(delete(turn_obligations).where(turn_obligations.c.turn_id == turn.id))
        with pytest.raises(IntentRealizationViolation, match="incomplete persistent"):
            ledger.validate_completion(turn.id)
        uow.rollback()


def test_additive_migration_preserves_historical_turn_without_ir_backfill(runtime):
    service, assets, compiler, interaction = acquired(runtime)
    turn = service.get_shared_understanding(interaction.id).turns[0]
    from spg.infrastructure.persistence.product_schema import interaction_assessments, interaction_turns
    def historical_rows():
        with service.database.unit_of_work() as uow:
            assessment = dict(uow.session.execute(select(interaction_assessments).where(
                interaction_assessments.c.id == turn.assessment_id)).mappings().one())
            assessment.pop("semantic_ir")
            persisted_turn = dict(uow.session.execute(select(interaction_turns).where(
                interaction_turns.c.id == turn.id)).mappings().one())
            return assessment, persisted_turn
    before = historical_rows()
    records = service.get_shared_understanding(interaction.id).records
    config = Config("alembic.ini")
    command.downgrade(config,"20260927_60")
    assert "semantic_ir" not in {column["name"] for column in inspect(service.database.engine).get_columns("interaction_assessments")}
    command.upgrade(config,"head")
    assert historical_rows() == before
    assert service.get_shared_understanding(interaction.id).records == records
    projection = service.realization_projection(turn.id)
    assert projection == {"semantic_ir":None,"semantic_envelope":None,
        "obligations":[],"refinements":[],"historical_without_ir":True}


def test_create_only_then_switch_preserves_omitted_effects(runtime):
    service, assets, compiler, interaction = acquired(runtime)
    compiler.operation = "CREATE_BRANCH"
    compiler.arguments = {"target_branch": "feat_draft"}
    _, created = settled(service, interaction, "创建 feat_draft；先留在当前分支")
    obligation = created["obligations"][0]
    assert obligation["state"] == "SATISFIED"
    assert obligation["observed_effect"]["facts"]["repository_ref"] == "refs/heads/main"
    assert "feat_draft" in obligation["observed_effect"]["facts"]["branches"]
    compiler.operation = "SWITCH_BRANCH"
    _, switched = settled(service, interaction, "现在切换到已存在的 feat_draft")
    obligation = switched["obligations"][0]
    assert obligation["state"] == "SATISFIED"
    assert obligation["observed_effect"]["facts"]["repository_ref"] == "refs/heads/feat_draft"
    assert compiler.calls == 3


def test_owner_refresh_recovers_without_recompilation_or_a_second_git_write(runtime):
    from spg.domain.intent_realization import RealizationRefinement, RealizationSignal
    service, assets, compiler, interaction = acquired(runtime)
    actual = service._repository_effect
    stale = actual(interaction.id)
    reads = []
    def stale_then_current(identity):
        reads.append(identity)
        return stale if len(reads) == 1 else actual(identity)
    service._repository_effect = stale_then_current
    compiler.operation = "CREATE_AND_SWITCH_BRANCH"
    compiler.arguments = {"target_branch":"feat_refresh"}
    turn, projection = settled(service,interaction,"创建 feat_refresh 并切换过去")
    assert projection['obligations'][0]['state'] == 'SATISFIED'
    assert compiler.calls == 2
    assert len(assets.attempts_for_interaction(interaction.id)) == 2
    assert len(reads) == 2
    assert [r['attempt'] for r in projection['refinements']] == [1,2]
    assert projection['refinements'][-1]['local_recovered'] is True
    assert not any(r['work_converged'] for r in projection['refinements'])
    # A new signal or reconstructed session cannot create a fresh budget.
    with service.database.unit_of_work() as uow:
        ledger=IntentRealizationStore(uow.session)
        prior=ledger.refinements(turn.id)[-1]
        restarted=prior.model_copy(update={'id':uuid4(),'parent_id':None,'attempt':1,
            'signal':RealizationSignal.RESPONSE_ACTION_INCONSISTENCY,'local_recovered':False})
        with pytest.raises(IntentRealizationViolation,match='durable attempt budget'):
            ledger.record_refinement(restarted)


@pytest.mark.parametrize("already_running", [False, True])
def test_current_correction_supersedes_only_undispatched_effect(runtime, monkeypatch, already_running):
    from spg.domain.intent_realization import ObservedEffect
    from spg.infrastructure.persistence.interaction_store import InteractionStore
    from spg.domain.interaction import InteractionTurnStatus
    service, assets, compiler, interaction = acquired(runtime)
    compiler.operation = "CREATE_BRANCH"
    compiler.arguments = {"target_branch":"feat_cancelled"}
    schedule = service.schedule_turn
    monkeypatch.setattr(service,"schedule_turn",lambda _identity:None)
    interrupted = service.submit_turn(interaction.id,"创建 feat_cancelled",human_identity="human:owner")
    assessment = service._assess_current(interaction.id,on_response_delta=None)
    with service.database.unit_of_work() as uow:
        ledger = IntentRealizationStore(uow.session)
        prior = ledger.initialize(interrupted.id,assessment.id,assessment.semantic_ir)[0]
        with pytest.raises(IntentRealizationViolation,match="validated supersession"):
            ledger.transition(prior,state=ObligationState.SUPERSEDED,blocker_reference="arbitrary-narrative")
        if already_running:
            prior = ledger.transition(prior,state=ObligationState.RUNNING,running_evidence=ObservedEffect(
                owner="repository-asset",evidence_references=("repository-intake:actually-pending",),facts={"owner_running":True}))
        InteractionStore(uow.session).update_turn(interrupted.id,status=InteractionTurnStatus.FAILED,
            failure_code="OWNER_INTERRUPTED",failure_message="Retained interrupted owner fixture",updated_at=datetime.now(UTC))
        uow.commit()
    class CorrectionCompiler(DeclaredCompiler):
        def interpret(self,basis):
            value = super().interpret(basis)
            item = value.semantic_intent.items[0].model_copy(update={"kind":SemanticKind.CORRECTION,
                "action":None,"supersedes":(str(prior.id),)})
            return value.model_copy(update={"semantic_intent":value.semantic_intent.model_copy(update={"items":(item,)})})
    service.capability = CorrectionCompiler()
    monkeypatch.setattr(service,"schedule_turn",schedule)
    turn, result = settled(service,interaction,"撤回刚才尚未完成的操作。")
    assert result["obligations"][0]["state"] == ("BLOCKED_WITH_EVIDENCE" if already_running else "SATISFIED")
    with service.database.unit_of_work() as uow:
        ledger = IntentRealizationStore(uow.session)
        retained = ledger.obligations(interrupted.id)[0]
        assert retained.state.value == ("RUNNING" if already_running else "SUPERSEDED")
        if not already_running:
            assert str(retained.supersession.replacement_ir_id) == result["semantic_ir"]["id"]
            assert retained.supersession.owner_disposition.facts["dispatch_status"] == "NOT_DISPATCHED"
    assert len(assets.attempts_for_interaction(interaction.id)) == 1
