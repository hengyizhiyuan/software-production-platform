"""Source roles may share an identity; controlled proofs are not model success."""
import json
from copy import deepcopy
import pytest
from spg.application.governed_obligations import (
    fulfillment_inventory, validate_projection_candidate, form_fulfillment_projection,
    fulfillment_capability_contracts, _owner_source_preconditions,
    work_constraint_sources_correspond, validate_fulfillment_projection,
)
from spg.domain.governed_obligation import (
    FulfillmentProjectionCandidate, FulfillmentRouteCandidate, FulfillmentComponentBasis,
    fulfillment_source_semantic_text,
)
from spg.domain.intent_realization import SemanticKind
from spg.domain.interaction_actions import ActionSpeechAct
from tests.test_fulfillment_projection import basis
from tests.test_c3_semantic_contract_calibration import ComponentOracle, review


def shared_item_case(description="This is an internal review exercise."):
    revision, ir = basis()
    negative = ir.clauses[0]
    goal = ir.current_production[0].model_copy(update={"exclusions": ("External release.",)})
    item = ir.items[0].model_copy(update={"kind": SemanticKind.PRODUCTION_INTENT, "production": goal})
    request = negative.model_copy(update={"clause_id": "current-artifact", "source_text": "Produce the specified caption artifact.",
        "polarity": "AFFIRMATIVE", "requested_effects": ("PRODUCTION_INTENT",), "speech_act": ActionSpeechAct.EXPLICIT_REQUEST})
    negative = negative.model_copy(update={"requested_effects": (), "speech_act": ActionSpeechAct.EXPLICIT_REQUEST})
    background = negative.model_copy(update={"clause_id": "description", "source_text": description,
        "polarity": "AFFIRMATIVE", "modality": "ASSERTION", "speech_act": ActionSpeechAct.DISCUSSION})
    ir.items, ir.clauses, ir.current_production = (item,), (request, negative, background), (goal,)
    original_fact = revision.engineering_semantic_facts[0]
    broad = " ".join(c.source_text for c in ir.clauses)
    revision.engineering_semantic_facts = (original_fact.model_copy(update={
        "provenance": original_fact.provenance.model_copy(update={"source_text": broad})}),)
    revision.constraints = ("Excluded from this Work: External release.",)
    inventory = fulfillment_inventory(revision, ir)
    negative_ref = next(s["source_ref"] for s in inventory["sources"] if s.get("clause_id") == negative.clause_id)
    routes = []
    for source in inventory["sources"]:
        text = fulfillment_source_semantic_text(source)
        cap = ("ARTIFACT_CONTENT" if source["kind"] == "FACT" or source.get("clause_id") == request.clause_id else
               "RETAIN_CONTEXT" if source["kind"] == "WORK_CONTEXT" or source.get("clause_id") == background.clause_id else "DENY_DEPLOY")
        routes.append(FulfillmentRouteCandidate(source_ref=source["source_ref"], capability=cap,
            work_constraint_indices=(source["index"],) if source["kind"] == "WORK_CONSTRAINT" else (),
            supporting_source_refs=(negative_ref,) if source["kind"] == "WORK_CONSTRAINT" else (),
            target_paths=tuple(inventory["exact_target_paths"]) if cap == "ARTIFACT_CONTENT" else (),
            component_basis=FulfillmentComponentBasis(source_span_start=0, source_span_end=len(text), source_component_quote=text),
            rationale="Declared controlled source-role proof, not an actual model result."))
    return revision, ir, inventory, FulfillmentProjectionCandidate(inventory_fingerprint=inventory["inventory_fingerprint"], routes=tuple(routes))


@pytest.mark.parametrize("description", ["This is an internal review exercise.", "这是一次内部验证场景。", "The present output is a software artifact."])
def test_shared_production_and_negative_clause_identity_has_a_legal_full_binding(description):
    revision, ir, inventory, plan = shared_item_case(description)
    before = deepcopy((revision.engineering_semantic_facts, ir.clauses, revision.constraints))
    provider = ComponentOracle([plan])
    result = form_fulfillment_projection(revision, ir, provider=provider)
    assert all(r.state != "UNRESOLVED" for r in result)
    assert len(provider.calls) == 1 and provider.review_calls == 1
    validate_fulfillment_projection(result, revision, ir, exact_target_paths=inventory["exact_target_paths"])
    assert before == (revision.engineering_semantic_facts, ir.clauses, revision.constraints)
    assert any(r.owner.value == "DELIVERY_GATE" and r.phase.value == "CONTINUOUS_FROM_ADMISSION" for r in result)
    assert result[0].formation_receipt["source_role_contract"] == "v2"


@pytest.mark.parametrize("description", ["This is an internal review exercise.", "这是一次内部验证场景。", "The present output is a software artifact."])
def test_generation_domain_preserves_legal_reviewed_whole_background_not_just_typed_context(description):
    from spg.providers.fulfillment_candidate import _formation_output_schema
    revision, ir, inventory, plan = shared_item_case(description)
    capabilities = fulfillment_capability_contracts()
    prerequisites = _owner_source_preconditions(revision, ir, inventory, capabilities)
    ordinal = next(i for i,s in enumerate(inventory['sources']) if s.get('clause_id') == 'description')
    assert prerequisites['sources'][ordinal]['whole_source_context_only'] is False
    conditional = prerequisites['sources'][ordinal]['reviewed_background_prerequisites']
    assert conditional['conditional_source_eligible'] is True
    assert conditional['required_current_fact_refs'] == ['semantic-fact:' + str(f.id) for f in revision.engineering_semantic_facts if f.is_current]
    assert conditional['required_one_current_request_ref_from']
    assert conditional['independent_full_plan_and_component_review_required'] is True
    historical = _owner_source_preconditions(revision, ir, inventory, capabilities,
        typed_prerequisite_contract='existing-owner-typed-prerequisites-v5')
    assert all('reviewed_background_prerequisites' not in r for r in historical['sources'])
    schema = _formation_output_schema(inventory, capabilities, owner_preconditions=prerequisites)
    retain = next(i for i,c in enumerate(capabilities) if c['capability'] == 'RETAIN_CONTEXT')
    branch = next(b for b in schema['properties']['routes']['items']['anyOf']
        if ordinal in b['properties']['s']['enum'] and retain in b['properties']['c']['enum'])
    assert {'properties': {'q': {'type': 'null'}, 'a': {'enum': [0]}, 'z': {'enum': [len(description)]}}} in branch['anyOf']
    result = validate_projection_candidate(plan, revision, ir, inventory, semantic_review=review(inventory,plan))
    assert any(b.state == 'RETAINED_CONTEXT' for b in result)


def test_conditional_background_availability_does_not_admit_missing_current_fact_consumers():
    revision, ir, inventory, plan = shared_item_case()
    changed = plan.model_copy(update={'routes': tuple(r.model_copy(update={
        'capability': 'UNRESOLVED','target_paths': ()}) if r.source_ref.startswith('semantic-fact:') else r for r in plan.routes)})
    with pytest.raises(ValueError, match='CURRENT_CLAUSE_CANNOT_BE_CONTEXT_ONLY'):
        validate_projection_candidate(changed,revision,ir,inventory,allow_review_pending=True)


def test_located_coverage_feedback_reports_exact_gap_without_repairing_candidate():
    from spg.application.governed_obligations import projection_validation_feedback
    from hashlib import sha256
    revision, ir, inventory, plan = shared_item_case()
    original = next(r for r in plan.routes if r.capability == 'ARTIFACT_CONTENT' and r.source_ref.startswith('ir-clause:'))
    basis = original.component_basis
    changed = original.model_copy(update={'component_basis':basis.model_copy(update={
        'source_span_start':1,'source_component_quote':basis.source_component_quote[1:]})})
    candidate = plan.model_copy(update={'routes':tuple(changed if r == original else r for r in plan.routes)})
    before = candidate.model_dump_json()
    data=json.loads(projection_validation_feedback(candidate,revision,ir,inventory,'OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST',include_coverage=True))
    gap=next(v for v in data['violations'] if v['code']=='OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST')
    assert gap['uncovered_codepoint_ranges']==[[0,1]] and gap['additional_uncovered_range_count']==0
    assert gap['original_text_sha256']==sha256(basis.source_component_quote.encode()).hexdigest()
    assert candidate.model_dump_json()==before
    old=json.loads(projection_validation_feedback(candidate,revision,ir,inventory,'OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST'))
    assert 'coverage_observation_contract' not in old
    assert all('uncovered_codepoint_ranges' not in v for v in old['violations'])


def test_full_wire_owner_feedback_uses_same_locator_and_exposes_context_removal_geometry_only():
    from spg.application.governed_obligations import _owner_repair_context, _owner_source_preconditions, fulfillment_capability_contracts, locate_projection_components
    from spg.domain.governed_obligation import fulfillment_candidate_fingerprint
    from tests.test_c3_fulfillment_capacity_representation import controlled_wire
    import json
    revision, ir, inventory, plan = shared_item_case()
    artifact = next(r for r in plan.routes if r.capability == 'ARTIFACT_CONTENT' and r.source_ref.startswith('ir-clause:'))
    text = artifact.component_basis.source_component_quote
    shortened = artifact.model_copy(update={'component_basis': artifact.component_basis.model_copy(update={
        'source_span_end': len(text)-1, 'source_component_quote': text[:-1]})})
    retained = artifact.model_copy(update={'capability': 'RETAIN_CONTEXT', 'target_paths': (),
        'component_basis': artifact.component_basis.model_copy(update={'linked_fact_refs': ()})})
    proposal = plan.model_copy(update={'routes': tuple(shortened if r == artifact else r for r in plan.routes)+(retained,)})
    caps = fulfillment_capability_contracts()
    prerequisites = _owner_source_preconditions(revision, ir, inventory, caps)
    wire, _ = controlled_wire(inventory, proposal, owner_preconditions=prerequisites)
    ordinal = next(i for i,r in enumerate(proposal.routes) if r == shortened)
    wire['routes'][ordinal].update(a=1,z=len(text),q=text[:-1])
    raw = json.dumps(wire)
    before = proposal.model_dump_json()
    observed = _owner_repair_context(raw,revision,ir,inventory,caps,validation_feedback=None,
        owner_preconditions=prerequisites,located_candidate=proposal)
    assert observed['located_component_observation_contract']=='existing-complete-wire-location-feedback-v1'
    assert observed['raw_routes_not_evaluable']==[]
    assert observed['located_components'][ordinal]['located_span']==[0,len(text)-1]
    counterfactual = next(v for v in observed['coverage_if_context_routes_removed']
        if ordinal in v['remaining_route_indices'])
    assert counterfactual['uncovered_codepoint_ranges']==[[len(text)-1,len(text)]]
    assert 'SEMANTIC_DISPOSITION_NOT_EVALUATED' in counterfactual['disposition']
    assert proposal.model_dump_json()==before and wire['routes'][ordinal]['a']==1
    old = _owner_source_preconditions(revision,ir,inventory,caps,typed_prerequisite_contract='existing-owner-typed-prerequisites-v6')
    old_wire,_=controlled_wire(inventory,proposal,owner_preconditions=old)
    old_wire['routes'][ordinal].update(a=1,z=len(text),q=text[:-1])
    legacy = _owner_repair_context(json.dumps(old_wire),revision,ir,inventory,caps,validation_feedback=None,
        owner_preconditions=old,located_candidate=proposal)
    assert 'located_component_observation_contract' not in legacy and ordinal in legacy['raw_routes_not_evaluable']
    changed = proposal.model_copy(update={'routes': proposal.routes[:-1]})
    with pytest.raises(RuntimeError,match='WIRE_FEEDBACK_IDENTITY_DRIFT'):
        _owner_repair_context(raw,revision,ir,inventory,caps,validation_feedback=None,
            owner_preconditions=prerequisites,located_candidate=changed)


def test_same_item_clause_proves_two_roles_but_affirmative_or_future_cannot_prove_prohibition():
    revision, ir, inventory, _ = shared_item_case()
    source = next(s for s in inventory["sources"] if s["kind"] == "WORK_CONSTRAINT")
    negative = next(s for s in inventory["sources"] if s.get("clause_id") == "original-clause")
    from spg.domain.governed_obligation import FulfillmentPhase
    args = dict(component="deploy", phase=FulfillmentPhase.CONTINUOUS_FROM_ADMISSION, semantic_component_declared=True, calibrated=True)
    assert work_constraint_sources_correspond(ir, source["payload"]["content"], [negative], **args)
    assert not work_constraint_sources_correspond(ir, source["payload"]["content"], [negative], source_contract="v1", **args)
    for field, value in [("polarity", "AFFIRMATIVE"), ("temporal_scope", "FUTURE")]:
        changed = deepcopy(ir)
        changed.clauses = tuple(c.model_copy(update={field: value}) if c.clause_id == negative["clause_id"] else c for c in changed.clauses)
        assert not work_constraint_sources_correspond(changed, source["payload"]["content"], [negative], **args)


def test_legacy_prerequisite_bytes_are_recomputable_and_new_contract_exposes_dual_role_proof():
    revision, ir, inventory, _ = shared_item_case()
    capabilities = fulfillment_capability_contracts()
    legacy = _owner_source_preconditions(revision, ir, inventory, capabilities, typed_prerequisite_contract="existing-owner-typed-prerequisites-v3")
    current = _owner_source_preconditions(revision, ir, inventory, capabilities)
    index = next(i for i,s in enumerate(inventory["sources"]) if s["kind"] == "WORK_CONSTRAINT")
    assert "necessary_source_proofs" not in legacy["sources"][index]
    assert current["sources"][index]["necessary_source_proofs"]
    assert json.dumps(legacy, sort_keys=True) == json.dumps(_owner_source_preconditions(
        revision, ir, inventory, capabilities, typed_prerequisite_contract="existing-owner-typed-prerequisites-v3"), sort_keys=True)


def test_broad_provenance_does_not_approve_background_without_independent_component_review():
    revision, ir, inventory, plan = shared_item_case()
    validate_projection_candidate(plan, revision, ir, inventory, allow_review_pending=True)
    with pytest.raises(ValueError, match="SEMANTIC_REVIEW_REQUIRED|COMPONENT_REVIEW_REQUIRED"):
        validate_projection_candidate(plan, revision, ir, inventory)
    rejected = review(inventory, plan)
    rejected = rejected.model_copy(update={"component_results": tuple(r.model_copy(update={
        "complete_and_equivalent": False}) if r.capability == "RETAIN_CONTEXT" else r for r in rejected.component_results)})
    with pytest.raises(ValueError, match="SEMANTIC_COMPONENT_MISMATCH"):
        validate_projection_candidate(plan, revision, ir, inventory, semantic_review=rejected)


def test_background_cannot_erase_current_fact_or_make_a_negative_clause_context():
    revision, ir, inventory, plan = shared_item_case()
    hidden = plan.model_copy(update={"routes": tuple(r.model_copy(update={"capability": "RETAIN_CONTEXT", "target_paths": ()})
        if r.source_ref.startswith("semantic-fact:") else r for r in plan.routes)})
    with pytest.raises(ValueError, match="CURRENT_FACT_CANNOT_BE_CONTEXT_ONLY"):
        validate_projection_candidate(hidden, revision, ir, inventory, allow_review_pending=True)
    negative = plan.model_copy(update={"routes": tuple(r.model_copy(update={"capability": "RETAIN_CONTEXT"})
        if r.source_ref.endswith(":original-clause") else r for r in plan.routes)})
    with pytest.raises(ValueError, match="CURRENT_CLAUSE_CANNOT_BE_CONTEXT_ONLY"):
        validate_projection_candidate(negative, revision, ir, inventory, allow_review_pending=True)


def test_consumer_view_binds_actual_implementation_and_keeps_evidence_domains_distinct():
    import inspect
    from hashlib import sha256
    from spg.providers.fulfillment_candidate import _existing_consumer_contracts, _review_component_table
    from spg.application.governed_obligations import evaluate_constraint_routes
    capabilities = fulfillment_capability_contracts()
    rows = {r["capability"]: r for r in _existing_consumer_contracts(capabilities)}
    assert set(rows) == {c["capability"] for c in capabilities} - {"UNRESOLVED"}
    assert rows["GIT_DIFF_SCOPE"]["enforced_decision"]["operation"] == "EXACT_CHANGED_PATH_SET"
    assert rows["DENY_DEPLOY"]["enforced_decision"]["operation"] == "ENFORCED_EFFECT_PERMISSION"
    expected = {"callable": evaluate_constraint_routes.__module__ + "." + evaluate_constraint_routes.__qualname__,
        "source_sha256": sha256(inspect.getsource(evaluate_constraint_routes).encode()).hexdigest()}
    assert expected in rows["GIT_DIFF_SCOPE"]["consumer_sources"]
    assert expected in rows["DENY_DEPLOY"]["consumer_sources"]
    assert "deploy" in rows["GIT_DIFF_SCOPE"]["does_not_prove"]
    assert "current Verification" in rows["CANDIDATE_SEAL"]["does_not_prove"]
    assert all(r["actual_evidence_present"] is False for r in rows.values())
    revision, ir, inventory, plan = shared_item_case()
    # The critic sees the actual operation even for a plausible but wrong
    # proposal. This table neither gives a semantic verdict nor changes it.
    wrong = plan.model_copy(update={"routes": tuple(r.model_copy(update={
        "capability": "GIT_DIFF_SCOPE", "target_paths": tuple(inventory["exact_target_paths"])})
        if r.capability == "DENY_DEPLOY" else r for r in plan.routes)})
    comparison = _review_component_table(inventory, wrong, capabilities)
    for route, row in zip(wrong.routes, comparison, strict=True):
        assert row["original_component_text"] == route.component_basis.source_component_quote
        assert row["consumer_operation_contract"] == rows[route.capability]
        assert not {"passed", "complete_and_equivalent", "rationale"} & row.keys()


@pytest.mark.parametrize("change", ["v1", "removed", "unsupported"])
def test_source_role_contract_is_bound_to_original_wire_preconditions_on_replay(change):
    from tests.test_c3_fulfillment_repair_context import repair_case
    provider, calls, _, run = repair_case()
    assert all(b.state != "UNRESOLVED" for b in run())
    before = len(calls)
    request = next(r for r in provider._fulfillment_receipts if r["stage"] == "MODEL_REQUEST_PENDING")
    assert request["source_role_contract"] == "v3"
    if change == "removed": request.pop("source_role_contract")
    else: request["source_role_contract"] = "v1" if change == "v1" else "unknown-role-policy"
    result = run()
    assert len(calls) == before
    assert all(b.state == "UNRESOLVED" for b in result)
    assert result[0].formation_receipt["terminal_reason"] in {
        "OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT", "OBLIGATION_SOURCE_ROLE_CONTRACT_UNSUPPORTED"}
