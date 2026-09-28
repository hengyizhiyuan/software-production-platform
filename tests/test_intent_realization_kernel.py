"""Meaning is compiler-owned; provenance and actual effect close obligations."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from spg.application.intent_realization import (
    IntentRealizationKernel, IntentRealizationViolation, canonical_operation,
    executable_semantic_actions, reconcile_obligation, validate_turn_completion,
)
from spg.application.interaction import (
    _grounded_named_branch_question, _grounded_status_facts, _research_repository_source,
)
from spg.domain.engineering_semantics import (
    SemanticEpistemicStatus, SemanticFactAuthority, SemanticRelation, SemanticRoleOrigin,
)
from spg.domain.interaction_actions import CanonicalOperation as O, ActionSpeechAct as S
from spg.domain.intent_realization import (
    AtomicBranchEffect, ObligationState, ObservedEffect, OperationalIntent, ProductionIntent,
    SemanticArgument, SemanticClause, SemanticItem, SemanticKind as K,
    SemanticOrigin as Origin, SemanticProvenance, TurnSemanticCandidate,
    RealizationRefinement, RealizationScope, RealizationSignal,
)
from spg.providers.interaction_contract import _safe_validation_summary


def source(text, *, identity=None):
    return SimpleNamespace(id=identity or uuid4(), actor="HUMAN", content=text)


def provenance(record, text=None):
    return SemanticProvenance(origin=Origin.HUMAN_EXPLICIT,
        source_record_id=record.id, source_text=text or record.content)


def test_named_branch_question_requires_exact_human_target_and_owner_branch_list():
    record = source("看看 feat_expected 分支是否存在")
    item = SemanticItem(item_id="branch-question", kind=K.QUESTION,
        statement="Check branch existence", subject="branch:feat_expected",
        provenance=(provenance(record),), confidence=.95)
    observation = ObservedEffect(owner="repository-asset",
        evidence_references=("repository-intake:receipt",),
        facts={"condition": "READY", "branches": ["main", "feat_other"]})
    answer, evidence = _grounded_named_branch_question(item, observation, record.id)
    assert "feat_expected 不存在" in answer
    assert evidence == ("repository-intake:receipt:branches:feat_expected",)
    present = observation.model_copy(update={"facts": {**observation.facts,
        "branches": ["main", "feat_expected"]}})
    assert "feat_expected 存在" in _grounded_named_branch_question(item, present, record.id)[0]
    wrong_target = item.model_copy(update={"subject": "branch:feat_other"})
    assert _grounded_named_branch_question(wrong_target, observation, record.id) is None
    incomplete = observation.model_copy(update={"facts": {"condition": "READY"}})
    assert _grounded_named_branch_question(item, incomplete, record.id) is None


def test_project_research_uses_one_confirmed_human_repository_fact():
    url = "http://qualified-git:8080/business-app.git"
    fact = SimpleNamespace(is_current=True, subject="repository.url",
        relation=SemanticRelation.REFERENCE, value=url,
        authority=SemanticFactAuthority.HUMAN_EXPLICIT,
        epistemic_status=SemanticEpistemicStatus.CONFIRMED,
        provenance=SimpleNamespace(role_origin=SemanticRoleOrigin.EXPLICIT,
            source_text=f"Current project repository: {url}"))
    assessment = SimpleNamespace(semantic_ir=SimpleNamespace(repository_source=None),
        engineering_semantic_facts=(fact,))
    assert _research_repository_source(assessment) == url
    compiler_fact = SimpleNamespace(**{**fact.__dict__, "subject": "repository.source"})
    assert _research_repository_source(SimpleNamespace(semantic_ir=assessment.semantic_ir,
        engineering_semantic_facts=(compiler_fact,))) == url
    project_fact = SimpleNamespace(**{**fact.__dict__, "subject": "project.repository_url"})
    assert _research_repository_source(SimpleNamespace(semantic_ir=assessment.semantic_ir,
        engineering_semantic_facts=(project_fact,))) == url
    fact_item = SimpleNamespace(kind=K.FACT, subject="repository",
        provenance=(SimpleNamespace(origin=Origin.HUMAN_EXPLICIT,
            source_text=f"Current project repository: {url}"),))
    fact_only = SimpleNamespace(semantic_ir=SimpleNamespace(repository_source=None,
        items=(fact_item,)), engineering_semantic_facts=())
    assert _research_repository_source(fact_only) == url
    other = "https://example.invalid/other.git"
    conflicting = SimpleNamespace(**{**fact.__dict__, "value": other,
        "provenance": SimpleNamespace(role_origin=SemanticRoleOrigin.EXPLICIT,
            source_text=f"Current project repository: {other}")})
    assert _research_repository_source(SimpleNamespace(semantic_ir=assessment.semantic_ir,
        engineering_semantic_facts=(fact, conflicting))) is None
    inferred = SimpleNamespace(**{**fact.__dict__,
        "authority": SemanticFactAuthority.SYSTEM_INFERRED})
    assert _research_repository_source(SimpleNamespace(semantic_ir=assessment.semantic_ir,
        engineering_semantic_facts=(inferred,))) is None


def test_structural_repair_feedback_identifies_typed_item_error_without_echoing_input():
    record = source("private human wording")
    with pytest.raises(ValidationError) as error:
        SemanticItem(item_id="invalid", kind=K.OPERATIONAL_ACTION,
            statement="private human wording", provenance=(provenance(record),),
            confidence=.95)
    summary = _safe_validation_summary(error.value)
    assert "SEMANTIC_TYPE_MISMATCH: operational items require an action" in summary
    assert "private human wording" not in summary


def action(record, *, op=O.CREATE_AND_SWITCH_BRANCH, act=S.EXPLICIT_REQUEST, identity="action", branch="feat_kernel", depends=()):
    args = {} if branch is None else {"target_branch": SemanticArgument(value=branch,
        provenance=provenance(record, branch))}
    effects = {O.CREATE_BRANCH: ("CREATE_BRANCH",), O.SWITCH_BRANCH: ("SWITCH_BRANCH",),
        O.CREATE_AND_SWITCH_BRANCH: ("CREATE_BRANCH", "SWITCH_BRANCH")}.get(op, ())
    return SemanticItem(item_id=identity, kind=K.OPERATIONAL_ACTION, statement="Compiler's bounded meaning",
        provenance=(provenance(record),), confidence=.95, depends_on=depends,
        action=OperationalIntent(operation=op, arguments=args, speech_act=act,
            atomic_branch_effects=tuple(AtomicBranchEffect(effect=effect,
                target_branch=branch, provenance=provenance(record))
                for effect in effects if branch is not None)))


def govern(record, items, *, records=None, clauses=None, history=()):
    effects = tuple(dict.fromkeys(effect.effect for item in items if item.action
        for effect in item.action.atomic_branch_effects))
    raw = TurnSemanticCandidate(items=tuple(items), clauses=clauses or (SemanticClause(
        clause_id="source", source_record_id=record.id, source_text=record.content,
        semantic_item_ids=tuple(i.item_id for i in items),
        speech_act=S.EXPLICIT_REQUEST if effects else None,
        polarity="AFFIRMATIVE" if effects else "UNRESOLVED",
        modality="REQUEST" if effects else "UNRESOLVED",
        temporal_scope="CURRENT" if effects else "UNRESOLVED",
        requested_effects=effects),))
    basis = SimpleNamespace(records=records or (record,), interaction=SimpleNamespace(id=uuid4()),
        basis_fingerprint="a"*64, governed_semantic_history=history)
    candidate = SimpleNamespace(semantic_intent=raw, provider_identity="test:semantic-compiler")
    return IntentRealizationKernel().govern(candidate, basis)


@pytest.mark.parametrize("raw", ["CREATE_AND_SWITCH_BRANCH", "CREATE_BRANCH_AND_CHECKOUT", "CREATE_NEW_BRANCH_AND_SWITCH", "NEW_BRANCH_AND_SWITCH"])
def test_structured_ontology_equivalence(raw):
    assert canonical_operation(raw) is O.CREATE_AND_SWITCH_BRANCH


def test_human_phrase_is_not_an_operation_alias():
    with pytest.raises(IntentRealizationViolation, match="SEMANTIC_TYPE_MISMATCH"):
        canonical_operation("切个新分支")


def test_contextual_old_target_requires_exact_governed_item_reference():
    prior_record = source("Create feat_kernel")
    prior_ir = govern(prior_record, (action(prior_record, op=O.CREATE_BRANCH),))
    current = source("Now switch to that branch")
    item = action(current, op=O.SWITCH_BRANCH)
    old_target = SemanticArgument(value="feat_kernel",
        provenance=provenance(prior_record, "feat_kernel"))
    item = item.model_copy(update={"action": item.action.model_copy(update={
        "arguments": {"target_branch": old_target}})})
    clause = SemanticClause(clause_id="current", source_record_id=current.id,
        source_text=current.content, semantic_item_ids=(item.item_id,),
        speech_act=S.EXPLICIT_REQUEST, polarity="AFFIRMATIVE", modality="REQUEST",
        temporal_scope="CURRENT", requested_effects=("SWITCH_BRANCH",))
    with pytest.raises(IntentRealizationViolation, match="old Human target lacks"):
        govern(current, (item,), records=(prior_record, current),
            clauses=(clause,), history=(prior_ir,))
    clause = clause.model_copy(update={"refers_to": (f"{prior_ir.id}:{prior_ir.items[0].item_id}",)})
    assert govern(current, (item,), records=(prior_record, current),
        clauses=(clause,), history=(prior_ir,)).operational_requests


def test_contextual_fact_target_keeps_old_evidence_but_needs_fresh_effect_consent():
    prior_record = source("The branch name is feat_kernel; just discussing it for now")
    fact = SemanticItem(item_id="name", kind=K.FACT,
        statement="The proposed branch name is feat_kernel", subject="branch.name",
        provenance=(provenance(prior_record, "feat_kernel"),), confidence=1)
    prior_ir = govern(prior_record, (fact,))
    current = source("Create that branch now")
    item = action(current, op=O.CREATE_BRANCH)
    old_target = SemanticArgument(value="feat_kernel",
        provenance=provenance(prior_record, "feat_kernel"))
    item = item.model_copy(update={"provenance": (*item.provenance, old_target.provenance),
        "action": item.action.model_copy(update={
            "arguments": {"target_branch": old_target}})})
    clause = SemanticClause(clause_id="current", source_record_id=current.id,
        source_text=current.content, semantic_item_ids=(item.item_id,),
        speech_act=S.EXPLICIT_REQUEST, polarity="AFFIRMATIVE", modality="REQUEST",
        temporal_scope="CURRENT", requested_effects=("CREATE_BRANCH",),
        refers_to=(f"{prior_ir.id}:{fact.item_id}",))
    assert govern(current, (item,), records=(prior_record, current),
        clauses=(clause,), history=(prior_ir,)).operational_requests


def test_same_turn_anaphoric_target_rebinds_only_to_exact_fact_dependency():
    record = source("feat_existing exists, switch to it")
    fact = SemanticItem(item_id="fact", kind=K.FACT,
        statement="feat_existing is the named branch", subject="branch.name",
        provenance=(provenance(record, "feat_existing exists, "),), confidence=1)
    item = action(record, op=O.SWITCH_BRANCH, branch="feat_existing", depends=("fact",))
    anaphor = SemanticArgument(value="feat_existing",
        provenance=provenance(record, "switch to it"))
    item = item.model_copy(update={"action": item.action.model_copy(update={
        "arguments": {"target_branch": anaphor},
        "atomic_branch_effects": (AtomicBranchEffect(effect="SWITCH_BRANCH",
            target_branch="feat_existing", provenance=provenance(record, "switch to it")),)})})
    clauses = (SemanticClause(clause_id="fact", source_record_id=record.id,
        source_text="feat_existing exists, ", semantic_item_ids=("fact",),
        polarity="AFFIRMATIVE", modality="ASSERTION", temporal_scope="CURRENT"),
        SemanticClause(clause_id="action", source_record_id=record.id,
            source_text="switch to it", semantic_item_ids=(item.item_id,),
            speech_act=S.EXPLICIT_REQUEST, polarity="AFFIRMATIVE", modality="REQUEST",
            temporal_scope="CURRENT", requested_effects=("SWITCH_BRANCH",)))
    governed = govern(record, (fact, item), clauses=clauses)
    assert governed.items[1].action.arguments["target_branch"].provenance.source_text == "feat_existing exists, "
    broad_claim = item.model_copy(update={"action": item.action.model_copy(update={
        "atomic_branch_effects": (AtomicBranchEffect(effect="SWITCH_BRANCH",
            target_branch="feat_existing", provenance=provenance(record)),)})})
    assert govern(record, (fact, broad_claim), clauses=clauses).operational_requests
    conflicting = item.model_copy(update={"action": item.action.model_copy(update={
        "arguments": {"target_branch": anaphor.model_copy(update={"value": "feat_other"})}})})
    with pytest.raises(IntentRealizationViolation, match="argument differs from literal source"):
        govern(record, (fact, conflicting), clauses=clauses)


def test_clause_coverage_allows_only_nonsemantic_separators_outside_spans():
    for separator in (",", "?"):
        record = source(f"First fact{separator} second fact")
        items = (SemanticItem(item_id="first", kind=K.FACT, statement="First fact",
            provenance=(provenance(record, "First fact"),), confidence=1),
            SemanticItem(item_id="second", kind=K.FACT, statement="second fact",
                provenance=(provenance(record, "second fact"),), confidence=1))
        clauses = (SemanticClause(clause_id="first", source_record_id=record.id,
            source_text="First fact", semantic_item_ids=("first",)),
            SemanticClause(clause_id="second", source_record_id=record.id,
                source_text="second fact", semantic_item_ids=("second",)))
        if separator == ",":
            assert len(govern(record, items, clauses=clauses).items) == 2
        else:
            with pytest.raises(IntentRealizationViolation, match="PRIMARY_INTENT_CLAUSE_LOST"):
                govern(record, items, clauses=clauses)


def test_unqualified_other_cannot_become_an_executable_semantic_operation():
    with pytest.raises(IntentRealizationViolation,match="unsupported structured operation"):
        canonical_operation("OTHER")


def test_parallel_unconsumed_argument_cannot_redirect_the_real_operation():
    record = source("Create feat_kernel")
    item = action(record)
    args = {**item.action.arguments, "branch_name": item.action.arguments["target_branch"]}
    item = item.model_copy(update={"action": item.action.model_copy(update={"arguments": args})})
    with pytest.raises(IntentRealizationViolation, match="unconsumed operational argument"):
        govern(record, (item,))


def test_create_only_cannot_carry_an_extra_switch_effect():
    record = source("Create feat_kernel")
    item = action(record, op=O.CREATE_BRANCH)
    added = AtomicBranchEffect(effect="SWITCH_BRANCH", target_branch="feat_kernel",
        provenance=provenance(record))
    item = item.model_copy(update={"action": item.action.model_copy(update={
        "atomic_branch_effects": (*item.action.atomic_branch_effects, added)})})
    with pytest.raises(IntentRealizationViolation, match="ATOMIC_EFFECT_AUTHORITY_MISSING"):
        govern(record, (item,))


def test_composite_branch_effect_requires_both_separate_claims():
    record = source("Create and switch to feat_kernel")
    item = action(record)
    item = item.model_copy(update={"action": item.action.model_copy(update={
        "atomic_branch_effects": item.action.atomic_branch_effects[:1]})})
    with pytest.raises(IntentRealizationViolation, match="ATOMIC_EFFECT_AUTHORITY_MISSING"):
        govern(record, (item,))


def test_atomic_effect_target_cannot_disagree_with_governed_target():
    record = source("Create feat_kernel, not feat_other")
    item = action(record, op=O.CREATE_BRANCH)
    conflicting = AtomicBranchEffect(effect="CREATE_BRANCH", target_branch="feat_other",
        provenance=provenance(record))
    item = item.model_copy(update={"action": item.action.model_copy(update={
        "atomic_branch_effects": (conflicting,)})})
    with pytest.raises(IntentRealizationViolation, match="ATOMIC_EFFECT_AUTHORITY_MISSING"):
        govern(record, (item,))


def test_clause_effect_with_target_suffix_must_bind_the_exact_argument():
    record = source("Create feat_kernel")
    item = action(record, op=O.CREATE_BRANCH)
    clause = SemanticClause(clause_id="current", source_record_id=record.id,
        source_text=record.content, semantic_item_ids=(item.item_id,),
        speech_act=S.EXPLICIT_REQUEST, polarity="AFFIRMATIVE", modality="REQUEST",
        temporal_scope="CURRENT", requested_effects=("CREATE_BRANCH:feat_kernel",))
    assert govern(record, (item,), clauses=(clause,)).operational_requests
    conflicting = clause.model_copy(update={"requested_effects": ("CREATE_BRANCH feat_other",)})
    with pytest.raises(IntentRealizationViolation, match="effect target conflicts"):
        govern(record, (item,), clauses=(conflicting,))


def test_typed_status_query_may_carry_only_a_read_only_owner_action():
    record = source("Which branch is current?")
    item = SemanticItem(item_id="status", kind=K.STATUS_QUERY,
        statement="Question about the current branch", provenance=(provenance(record),),
        confidence=1, action=OperationalIntent(operation=O.QUERY_CURRENT_BRANCH,
            speech_act=S.READ_ONLY_QUERY))
    assert govern(record, (item,)).operational_requests == (item,)
    assert govern(record, (item.model_copy(update={"kind": K.QUESTION}),)).operational_requests
    with pytest.raises(ValidationError, match="only read-only questions"):
        SemanticItem.model_validate({**item.model_dump(mode="json"),
            "action": {"operation": O.CREATE_BRANCH,
                "speech_act": S.EXPLICIT_REQUEST}})


def test_current_read_only_clause_cannot_hide_its_owner_action_as_noncurrent():
    record = source("Which branch is current?")
    item = SemanticItem(item_id="status", kind=K.QUESTION,
        statement="Question about the current branch", provenance=(provenance(record),),
        confidence=1, action=OperationalIntent(operation=O.QUERY_CURRENT_BRANCH,
            speech_act=S.READ_ONLY_QUERY, current=False))
    clause = SemanticClause(clause_id="current", source_record_id=record.id,
        source_text=record.content, semantic_item_ids=(item.item_id,),
        speech_act=S.READ_ONLY_QUERY, polarity="AFFIRMATIVE", modality="QUESTION",
        temporal_scope="CURRENT")
    with pytest.raises(IntentRealizationViolation, match="current Human operation"):
        govern(record, (item,), clauses=(clause,))


def test_observed_existing_branch_cannot_authorize_a_new_branch_target():
    record = source("Create a new branch")
    item = action(record, branch=None)
    argument = SemanticArgument(value="main", provenance=SemanticProvenance(
        origin=Origin.REPOSITORY_OBSERVED, evidence_reference="intake:actual-baseline"))
    item = item.model_copy(update={"action": item.action.model_copy(update={
        "arguments": {"target_branch": argument}})})
    with pytest.raises(IntentRealizationViolation, match="new branch target needs literal Human"):
        govern(record, (item,))


def test_missing_product_goal_blocks_only_that_goal_and_preserves_acquisition():
    record = source("Acquire https://example.invalid/repo.git; the product change is still undecided")
    acquire = action(record, op=O.ACQUIRE_REPOSITORY, branch=None)
    acquire = acquire.model_copy(update={"action": acquire.action.model_copy(update={"arguments": {
        "repository_source": SemanticArgument(value="https://example.invalid/repo.git",
            provenance=provenance(record))}})})
    goal = SemanticItem(item_id="goal", kind=K.PRODUCTION_INTENT,
        statement="Unspecified product change", provenance=(provenance(record),), confidence=1,
        production=ProductionIntent(objective="Unspecified change", primary_change="Unspecified change",
            current=True, bounded_change=True, unresolved_arguments=("primary_change",)))
    ir = govern(record, (acquire, goal))
    obligations = IntentRealizationKernel().obligations(ir, uuid4())
    assert ir.items[1].requires_human
    assert obligations[1].state is ObligationState.REQUIRES_HUMAN
    assert obligations[1].plane.value == "WORK"
    assert obligations[0].operation is O.ACQUIRE_REPOSITORY
    assert obligations[0].state is ObligationState.PENDING


def test_preview_without_candidate_requires_current_production_meaning():
    record = source("Start the existing project and provide a real preview")
    preview = action(record, op=O.REQUEST_PREVIEW, branch=None)
    with pytest.raises(IntentRealizationViolation, match="current production goal"):
        govern(record, (preview,))


def test_optional_product_implementation_uncertainty_does_not_block_the_goal():
    record = source("Build a user collection page")
    goal = SemanticItem(item_id="goal", kind=K.PRODUCTION_INTENT,
        statement="User collection page", provenance=(provenance(record),), confidence=1,
        production=ProductionIntent(objective="Collect user information", primary_change="Build a collection page",
            current=True, bounded_change=True, unresolved=("Choose implementation paths after inspection",)))
    ir = govern(record, (goal,))
    assert IntentRealizationKernel().obligations(ir, uuid4())[0].state is ObligationState.PENDING


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


def test_distinct_repository_acquisition_targets_require_one_owner_selection():
    first = "https://example.invalid/one.git"
    second = "https://example.invalid/two.git"
    record = source(f"clone {first} {second}")
    items = tuple(action(record, op=O.ACQUIRE_REPOSITORY, branch=None,
        identity=f"acquire-{index}").model_copy(update={"action": OperationalIntent(
            operation=O.ACQUIRE_REPOSITORY, speech_act=S.EXPLICIT_REQUEST,
            arguments={"repository_source": SemanticArgument(value=url,
                provenance=provenance(record, url))})})
        for index, url in enumerate((first, second)))
    ir = govern(record, items)
    assert not executable_semantic_actions(ir)
    assert all(item.requires_human and "repository_source" in item.action.unresolved_arguments
        for item in ir.items)
    assert any(question.blocks_current_step and question.requires_human for question in ir.questions)
    assert all(obligation.state is ObligationState.REQUIRES_HUMAN
        for obligation in IntentRealizationKernel().obligations(ir, uuid4()))


@pytest.mark.parametrize("speech_act", [S.DISCUSSION, S.UNRESOLVED])
def test_discussion_or_withdrawal_cannot_create_operational_obligation(speech_act):
    record = source("A lexical reference to searching GitHub")
    ir = govern(record, (action(record, op=O.SEARCH_GITHUB, act=speech_act, branch=None),))
    assert IntentRealizationKernel().obligations(ir, uuid4()) == ()


def test_current_authorization_can_reference_previous_literal_argument():
    previous = source("Consider a branch named feat_kernel")
    prior_fact = SemanticItem(item_id="branch-name", kind=K.FACT,
        statement="The discussed branch name is feat_kernel", subject="target_branch",
        provenance=(provenance(previous),), confidence=1)
    prior_ir = govern(previous, (prior_fact,))
    current = source("Use the name from our previous discussion and create it")
    item = action(previous, op=O.CREATE_BRANCH).model_copy(update={"provenance": (provenance(current),)})
    item = item.model_copy(update={"action": item.action.model_copy(update={
        "atomic_branch_effects": (AtomicBranchEffect(effect="CREATE_BRANCH",
            target_branch="feat_kernel", provenance=provenance(current)),)})})
    clause = SemanticClause(clause_id="current", source_record_id=current.id,
        source_text=current.content, semantic_item_ids=(item.item_id,),
        speech_act=S.EXPLICIT_REQUEST, polarity="AFFIRMATIVE", modality="REQUEST",
        temporal_scope="CURRENT", requested_effects=("CREATE_BRANCH",),
        refers_to=(f"{prior_ir.id}:{prior_fact.item_id}",))
    ir = govern(current, (item,), records=(previous, current),
        clauses=(clause,), history=(prior_ir,))
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


def test_status_coverage_uses_current_typed_owner_facts_not_answer_wording():
    record = source("Is the branch ready?")
    witness = SemanticProvenance(origin=Origin.REPOSITORY_OBSERVED,
        evidence_reference="repository-intake:current")
    item = SemanticItem(item_id="status", kind=K.STATUS_QUERY,
        statement="Branch readiness", answer="The branch is ready.",
        provenance=(provenance(record),), confidence=1,
        observed_facts={"condition": SemanticArgument(value="READY", provenance=witness),
            "target_branch": SemanticArgument(value="feat_kernel", provenance=witness)})
    current = ObservedEffect(owner="RepositoryAssetService",
        evidence_references=("repository-intake:current",),
        facts={"condition": "READY", "target_branch": "feat_kernel"})
    rendered = _grounded_status_facts(item, (current,))
    assert rendered is not None
    assert "feat_kernel" in rendered[0]
    assert rendered[1] == ("repository-intake:current:condition",
        "repository-intake:current:target_branch")
    stale = current.model_copy(update={"facts": {"condition": "RUNNING",
        "target_branch": "feat_kernel"}})
    assert _grounded_status_facts(item, (stale,)) is None


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


def test_pending_work_question_requires_owner_retirement_and_each_constraint():
    record = source("Search users by name and email")
    item = SemanticItem(item_id="scope", kind=K.CONSTRAINT,
        statement="Search users by name and email",
        provenance=(provenance(record),), confidence=1)
    ir = govern(record, (item,))
    step_id = uuid4()
    obligation = IntentRealizationKernel().obligations(ir, uuid4(),
        work_question_step_id=step_id)[0]
    observed = ObservedEffect(owner="work-steering-question",
        evidence_references=("work-reality-revision:revised",),
        facts={"question_step_id": str(step_id), "question_retired": False,
            "work_revision_id": "revised", "constraints": [item.statement]})
    with pytest.raises(IntentRealizationViolation, match="EXPECTED_EFFECT_NOT_REALIZED"):
        reconcile_obligation(obligation, observed)
    observed = observed.model_copy(update={"facts": {
        **observed.facts, "question_retired": True}})
    assert reconcile_obligation(obligation, observed).state is ObligationState.SATISFIED
    wrong_constraint = observed.model_copy(update={"facts": {
        **observed.facts, "constraints": ["Different scope"]}})
    with pytest.raises(IntentRealizationViolation, match="EXPECTED_EFFECT_NOT_REALIZED"):
        reconcile_obligation(obligation, wrong_constraint)
