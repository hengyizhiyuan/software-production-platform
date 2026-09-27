"""Meaning is compiler-owned; provenance and actual effect close obligations."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from spg.application.intent_realization import (
    IntentRealizationKernel, IntentRealizationViolation, canonical_operation,
    reconcile_obligation, validate_turn_completion,
)
from spg.domain.interaction_actions import CanonicalOperation as O, ActionSpeechAct as S
from spg.domain.intent_realization import (
    ObligationState, ObservedEffect, OperationalIntent, ProductionIntent,
    SemanticArgument, SemanticClause, SemanticItem, SemanticKind as K,
    SemanticOrigin as Origin, SemanticProvenance, TurnSemanticCandidate,
    RealizationRefinement, RealizationScope, RealizationSignal,
)


def source(text, *, identity=None):
    return SimpleNamespace(id=identity or uuid4(), actor="HUMAN", content=text)


def provenance(record, text=None):
    return SemanticProvenance(origin=Origin.HUMAN_EXPLICIT,
        source_record_id=record.id, source_text=text or record.content)


def action(record, *, op=O.CREATE_AND_SWITCH_BRANCH, act=S.EXPLICIT_REQUEST, identity="action", branch="feat_kernel", depends=()):
    args = {} if branch is None else {"target_branch": SemanticArgument(value=branch,
        provenance=provenance(record, branch))}
    return SemanticItem(item_id=identity, kind=K.OPERATIONAL_ACTION, statement="Compiler's bounded meaning",
        provenance=(provenance(record),), confidence=.95, depends_on=depends,
        action=OperationalIntent(operation=op, arguments=args, speech_act=act))


def govern(record, items, *, records=None, clauses=None):
    raw = TurnSemanticCandidate(items=tuple(items), clauses=clauses or (SemanticClause(
        clause_id="source", source_record_id=record.id, source_text=record.content,
        semantic_item_ids=tuple(i.item_id for i in items)),))
    basis = SimpleNamespace(records=records or (record,), interaction=SimpleNamespace(id=uuid4()), basis_fingerprint="a"*64)
    candidate = SimpleNamespace(semantic_intent=raw, provider_identity="test:semantic-compiler")
    return IntentRealizationKernel().govern(candidate, basis)


@pytest.mark.parametrize("raw", ["CREATE_AND_SWITCH_BRANCH", "CREATE_BRANCH_AND_CHECKOUT", "CREATE_NEW_BRANCH_AND_SWITCH", "NEW_BRANCH_AND_SWITCH"])
def test_structured_ontology_equivalence(raw):
    assert canonical_operation(raw) is O.CREATE_AND_SWITCH_BRANCH


def test_human_phrase_is_not_an_operation_alias():
    with pytest.raises(IntentRealizationViolation, match="SEMANTIC_TYPE_MISMATCH"):
        canonical_operation("切个新分支")


def test_business_scope_cannot_be_promoted_to_filesystem_write_area():
    record = source("调整首页；只允许 src/web/**")
    def goal(area):
        return SemanticItem(item_id="goal",kind=K.PRODUCTION_INTENT,statement="Bounded UI change",
            provenance=(provenance(record),),confidence=1,
            production=ProductionIntent(objective="Adjust existing UI",primary_change="Bounded change",
                current=True,bounded_change=True,scope=("首页",),allowed_areas=(SemanticArgument(
                    value=area,provenance=provenance(record,area)),)))
    with pytest.raises(IntentRealizationViolation,match="filesystem patterns"):
        govern(record,(goal("首页"),))
    assert govern(record,(goal("src/web/**"),)).current_production[0].scope == ("首页",)


def test_multi_clause_preserves_current_action_and_future_product_intent():
    record = source("acquire example repository; modify the product later")
    acquire = action(record, op=O.ACQUIRE_REPOSITORY, branch=None)
    future = SemanticItem(item_id="future", kind=K.PRODUCTION_INTENT,
        statement="Undefined later modification", provenance=(provenance(record),), confidence=.9,
        production=ProductionIntent(objective="Modify the product", primary_change="Unresolved modification",
            current=False, bounded_change=False, unresolved=("Change scope",)))
    ir = govern(record, (acquire, future))
    assert len(ir.items) == 2 and not ir.current_production
    obligations = IntentRealizationKernel().obligations(ir, uuid4())
    assert len(obligations) == 1 and obligations[0].operation is O.ACQUIRE_REPOSITORY


@pytest.mark.parametrize("speech_act", [S.DISCUSSION, S.UNRESOLVED])
def test_discussion_or_withdrawal_cannot_create_operational_obligation(speech_act):
    record = source("A lexical reference to searching GitHub")
    ir = govern(record, (action(record, op=O.SEARCH_GITHUB, act=speech_act, branch=None),))
    assert IntentRealizationKernel().obligations(ir, uuid4()) == ()


def test_current_authorization_can_reference_previous_literal_argument():
    previous = source("Consider a branch named feat_kernel")
    current = source("Use the name from our previous discussion and create it")
    item = action(previous).model_copy(update={"provenance": (provenance(current),)})
    ir = govern(current, (item,), records=(previous, current))
    assert ir.items[0].action.arguments['target_branch'].provenance.source_record_id == previous.id


def test_previous_request_cannot_supply_current_effect_authority():
    previous = source("Create feat_kernel")
    current = source("Tell me about branches")
    with pytest.raises(IntentRealizationViolation, match="old request"):
        govern(current, (action(previous),), records=(previous, current))


def test_invented_source_and_target_are_rejected():
    record = source("Create feat_kernel")
    item = action(record)
    forged = item.action.arguments['target_branch'].model_copy(update={"value": "feat_unrequested"})
    item = item.model_copy(update={"action":item.action.model_copy(update={"arguments":{"target_branch":forged}})})
    with pytest.raises(IntentRealizationViolation, match="ACTION_ARGUMENT_PROVENANCE_INVALID"):
        govern(record, (item,))


def test_primary_clause_cannot_disappear_from_compiler_coverage():
    record = source("add a user form; provide a preview")
    item = SemanticItem(item_id="preview", kind=K.EXPLORE, statement="Preview only",
        provenance=(provenance(record),), confidence=.9)
    clause = SemanticClause(clause_id="partial", source_record_id=record.id,
        source_text="provide a preview", semantic_item_ids=(item.item_id,))
    with pytest.raises(IntentRealizationViolation, match="PRIMARY_INTENT_CLAUSE_LOST"):
        govern(record, (item,), clauses=(clause,))


def test_production_goal_cannot_grant_delivery():
    record = source("Add a form; I will decide delivery later")
    item = SemanticItem(item_id="product", kind=K.PRODUCTION_INTENT, statement="Form",
        provenance=(provenance(record),), confidence=.9,
        production=ProductionIntent(objective="Add a form", primary_change="Add a form",
            current=True, bounded_change=True, delivery_authorized=True))
    with pytest.raises(IntentRealizationViolation, match="ACTION_SCOPE_INFLATION"):
        govern(record, (item,))


def test_dependencies_survive_materialization_and_cycles_fail_before_effect():
    record = source("Acquire first; then create feat_kernel")
    acquire = action(record, op=O.ACQUIRE_REPOSITORY, branch=None, identity="acquire")
    branch = action(record, depends=("acquire",))
    ir = govern(record, (acquire, branch))
    obligations = IntentRealizationKernel().obligations(ir, uuid4())
    assert obligations[1].depends_on == (obligations[0].id,)
    acquire = acquire.model_copy(update={"depends_on":(branch.item_id,)})
    with pytest.raises(IntentRealizationViolation, match="cyclic"):
        govern(record, (acquire, branch))


def test_execution_receipt_cannot_close_wrong_observed_branch():
    record = source("Create feat_kernel")
    ir = govern(record, (action(record),))
    obligation = IntentRealizationKernel().obligations(ir, uuid4())[0]
    wrong = ObservedEffect(owner="RepositoryAssetService", evidence_references=("intake:real-receipt",),
        facts={"condition":"READY", "repository_ref":"refs/heads/main", "revision":"a"*40, "tree":"b"*40})
    with pytest.raises(IntentRealizationViolation, match="EXPECTED_EFFECT_NOT_REALIZED"):
        reconcile_obligation(obligation, wrong)
    right = wrong.model_copy(update={"facts":{**wrong.facts,"repository_ref":"refs/heads/feat_kernel"}})
    closed = reconcile_obligation(obligation, right)
    assert closed.state is ObligationState.SATISFIED
    validate_turn_completion(ir, (closed,))


def test_narrative_is_not_a_terminal_state_but_evidenced_blocker_is():
    record = source("Create feat_kernel")
    ir = govern(record, (action(record),));obligation = IntentRealizationKernel().obligations(ir, uuid4())[0]
    with pytest.raises(IntentRealizationViolation, match="narrative"):
        validate_turn_completion(ir, (obligation,))
    with pytest.raises(ValidationError, match="needs owner evidence"):
        type(obligation).model_validate({**obligation.model_dump(),"state":"SATISFIED"})
    blocked = obligation.model_copy(update={"state":ObligationState.REQUIRES_HUMAN,
        "blocker_reference":"authority:exact-current-grant-missing"})
    validate_turn_completion(ir, (blocked,))


@pytest.mark.parametrize("scope", [RealizationScope.TURN, RealizationScope.ACTION])
def test_local_refinement_never_establishes_work_convergence(scope):
    with pytest.raises(ValidationError, match="Local recovery"):
        RealizationRefinement(id=uuid4(), turn_id=uuid4(), scope=scope,
            signal=RealizationSignal.EXPECTED_EFFECT_NOT_REALIZED, attempt=1, attempt_budget=2,
            evidence_references=("owner:observation",), local_recovered=True, work_converged=True)


@pytest.mark.parametrize("operation", [O.REQUEST_PREVIEW, O.ACCEPT_CANDIDATE, O.AUTHORIZE_DELIVERY, O.CREATE_PR])
def test_candidate_effect_requires_the_exact_bound_revision(operation):
    from spg.application.intent_realization import expected_effects, effect_matches
    record = source("Use candidate " + "a" * 40)
    argument = SemanticArgument(value="a" * 40, provenance=provenance(record))
    effect = expected_effects(operation, {"candidate_revision": argument})[0]
    facts = {"candidate_revision": "b" * 40, "preview_status": "READY", "served_verification": "PASS",
        "acceptance": "ACCEPT", "delivery_authorization_id": "authorization", "pull_request_url": "https://github.com/acme/repo/pull/1"}
    observation = ObservedEffect(owner="candidate-owner", evidence_references=("owner:receipt",), facts=facts)
    assert not effect_matches(effect, observation)
    assert effect_matches(effect, observation.model_copy(update={"facts": {**facts, "candidate_revision": "a" * 40}}))


def test_future_human_delivery_decision_does_not_block_current_production():
    from spg.application.intent_realization import current_step_semantic_items, project_interaction_candidate
    from spg.domain.interaction import InteractionAssessmentCandidate
    record = source("做一个反馈表单。以后由我另行决定交付。")
    goal = SemanticItem(item_id="produce", kind=K.PRODUCTION_INTENT, statement="Current form",
        provenance=(provenance(record),), confidence=1,
        production=ProductionIntent(objective="Feedback form", primary_change="Feedback form",
            current=True, bounded_change=True))
    future = SemanticItem(item_id="delivery", kind=K.CONSTRAINT, statement="Delivery remains Human owned",
        provenance=(provenance(record),), confidence=1, requires_human=True, depends_on=(goal.item_id,))
    ir = govern(record, (goal, future))
    assert [item.item_id for item in current_step_semantic_items(ir)] == ["produce"]
    obligations = IntentRealizationKernel().obligations(ir, uuid4())
    assert len(obligations) == 1 and obligations[0].state is ObligationState.PENDING
    candidate = InteractionAssessmentCandidate(natural_response="advisory", provider_identity="fixture",
        unresolved_material_questions=("Will Human authorize delivery?",))
    projected = project_interaction_candidate(candidate, ir)
    assert projected.unresolved_material_questions == ()
    assert future.statement in projected.candidate_constraints
    # The reverse relationship is genuinely blocking and must remain so.
    required = future.model_copy(update={"depends_on": ()})
    dependent = goal.model_copy(update={"depends_on": (required.item_id,)})
    blocked_ir = govern(record, (dependent, required))
    assert IntentRealizationKernel().obligations(blocked_ir, uuid4())[0].state is ObligationState.REQUIRES_HUMAN


def test_cited_model_prose_cannot_be_promoted_to_owner_observed_fact():
    record = source("检查仓库的实际版本。")
    witness = SemanticProvenance(origin=Origin.REPOSITORY_OBSERVED, evidence_reference="owner:repository")
    item = SemanticItem(item_id="fact", kind=K.CORRECTION, statement="model prose",
        provenance=(witness,), confidence=1,
        observed_facts={"revision": SemanticArgument(value="invented", provenance=witness)})
    raw = TurnSemanticCandidate(items=(item,), clauses=(SemanticClause(clause_id="all",
        source_record_id=record.id, source_text=record.content, semantic_item_ids=(item.item_id,)),))
    basis = SimpleNamespace(records=(record,), interaction=SimpleNamespace(id=uuid4()),
        basis_fingerprint="a"*64, observed_reality=(ObservedEffect(owner="repository",
            evidence_references=("owner:repository",), facts={"revision":"a"*40}),))
    with pytest.raises(IntentRealizationViolation, match="fact claim differs"):
        IntentRealizationKernel().govern(SimpleNamespace(semantic_intent=raw, provider_identity="fixture"), basis)


def test_parallel_design_frame_cannot_inflate_canonical_bounded_production():
    from spg.application.intent_realization import project_interaction_candidate
    from spg.domain.design_intent import DesignIntentFrame, DesignObjectType, DesignScopeLevel, DesignCollaborationMode
    from spg.domain.interaction import InteractionAssessmentCandidate
    record = source("修复取消按钮。")
    goal = SemanticItem(item_id="goal",kind=K.PRODUCTION_INTENT,statement="Fix cancel",
        provenance=(provenance(record),),confidence=1,production=ProductionIntent(
            objective="Fix cancel",primary_change="Fix cancel",current=True,bounded_change=True))
    ir = govern(record,(goal,))
    old_frame=DesignIntentFrame(design_subject="System-wide redesign",object_type=DesignObjectType.PRODUCT_SYSTEM,
        scope_level=DesignScopeLevel.STRATEGIC,collaboration_mode=DesignCollaborationMode.DESIGN,confidence=1)
    candidate=InteractionAssessmentCandidate(natural_response="advisory",provider_identity="fixture",design_intent_frame=old_frame)
    projected=project_interaction_candidate(candidate,ir)
    assert projected.design_intent_frame.object_type is DesignObjectType.FEATURE
    assert projected.design_intent_frame.collaboration_mode is DesignCollaborationMode.EXECUTION
    assert projected.design_intent_frame.scope_level is DesignScopeLevel.IMPLEMENTATION


def test_optional_uncertainty_does_not_become_a_new_human_owned_target():
    from spg.application.intent_realization import executable_semantic_actions
    record = source("获取 https://github.com/acme/example.git")
    item = action(record,op=O.ACQUIRE_REPOSITORY,branch=None)
    item = item.model_copy(update={"action":item.action.model_copy(update={"arguments":{
        "repository_source":SemanticArgument(value="https://github.com/acme/example.git",provenance=provenance(record))},
        "unresolved":("Owner workspace location is unspecified",)})})
    ir = govern(record,(item,))
    assert executable_semantic_actions(ir) == ir.operational_requests
    assert IntentRealizationKernel().obligations(ir,uuid4())[0].state is ObligationState.PENDING
    unresolved = item.model_copy(update={"action":item.action.model_copy(update={
        "unresolved_arguments":("repository_source",)})})
    blocked = govern(record,(unresolved,))
    assert executable_semantic_actions(blocked) == ()
    assert IntentRealizationKernel().obligations(blocked,uuid4())[0].state is ObligationState.REQUIRES_HUMAN


def test_routine_discovery_uncertainty_does_not_become_a_human_question():
    from spg.application.intent_realization import project_interaction_candidate
    from spg.domain.interaction import InteractionAssessmentCandidate
    record=source("修复取消按钮。")
    goal=SemanticItem(item_id="goal",kind=K.PRODUCTION_INTENT,statement="Fix cancel",
        provenance=(provenance(record),),confidence=1,production=ProductionIntent(objective="Fix cancel",
            primary_change="Fix cancel",current=True,bounded_change=True,unresolved=("Inspect current implementation",)))
    ir=govern(record,(goal,)).model_copy(update={"unresolved":("Discover repository technology",)})
    candidate=InteractionAssessmentCandidate(natural_response="advisory",provider_identity="fixture",
        unresolved_material_questions=("Tell me the repository implementation",))
    projected=project_interaction_candidate(candidate,ir)
    assert projected.unresolved_material_questions == ()
    assert ir.unresolved and ir.current_production[0].unresolved
    assert IntentRealizationKernel().obligations(ir,uuid4())[0].state is ObligationState.PENDING


def test_search_effect_requires_the_exact_compiled_query():
    from spg.application.intent_realization import expected_effects, effect_matches
    record=source("搜索成熟的验证库")
    query=SemanticArgument(value="mature validation libraries",provenance=provenance(record))
    effect=expected_effects(O.SEARCH_GITHUB,{'query':query})[0]
    observed=ObservedEffect(owner='search',evidence_references=('source:actual',),facts={
        'search_state':'COMPLETED','search_operations':['SEARCH_GITHUB'],'evidence_ids':['actual'],
        'queries':['unrelated keyword']})
    assert not effect_matches(effect,observed)
    correct=observed.model_copy(update={'facts':{**observed.facts,'queries':[query.value]}})
    assert effect_matches(effect,correct)
