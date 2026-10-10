"""Request economy cannot replace canonical or Owner verification."""
from copy import deepcopy
import json
import pytest
from spg.application import governed_obligations as a
from spg.providers import fulfillment_candidate as p
from spg.providers.verification_receipts import MAX_CANDIDATE_BYTES
from tests.test_c3_fulfillment_capacity_representation import controlled_capacity_case, controlled_model_provider


@pytest.mark.parametrize("scale", ("small", "medium", "complex"))
def test_independent_review_shares_contracts_without_losing_components_or_semantics(scale, record_property):
    _, _, inventory, plan = controlled_capacity_case(scale)
    caps = a.fulfillment_capability_contracts()
    before = deepcopy((inventory, plan.model_dump(mode="json"), caps))
    view = p._review_input_view(inventory, plan, caps, {})
    assert p._restore_review_component_contracts(view["component_index_table"], caps) == p._review_component_table(inventory, plan, caps)
    assert p._restore_formation_inventory_view(view["immutable_inventory"], view.get("existing_ir_item_table", {})) == inventory
    assert len(view["component_index_table"]) == len(plan.routes)
    assert view["required_result_identity_slots"] == p._review_result_identity_slots(inventory, plan)
    assert (inventory, plan.model_dump(mode="json"), caps) == before
    # Every original component remains explicit; only repeated Owner contracts
    # move to their existing authoritative table, with no model output repair.
    old = p._review_component_table(inventory, plan, caps)
    assert len(json.dumps(view["component_index_table"]).encode()) < len(json.dumps(old).encode())
    record_property("original_comparison_bytes", len(json.dumps(old).encode()))
    record_property("shared_comparison_bytes", len(json.dumps(view["component_index_table"]).encode()))


@pytest.mark.parametrize("field", ("consumer_binding", "consumer_operation_contract"))
def test_review_contract_reference_cannot_drift_to_a_different_owner(field):
    _, _, inventory, plan = controlled_capacity_case()
    caps = a.fulfillment_capability_contracts()
    view = p._review_input_view(inventory, plan, caps, {})
    row = next(r for r in view["component_index_table"] if field in r)
    row[field] = {next(iter(row[field])): "UNRESOLVED"}
    with pytest.raises(p._FulfillmentWireReceiptIdentityError, match="REVIEW_INPUT_IDENTITY_DRIFT"):
        p._restore_review_component_contracts(view["component_index_table"], caps)


@pytest.mark.parametrize("drift", (None, "source", "field"))
def test_reviewer_prerequisite_sharing_retains_exact_original_source_domains(drift):
    revision, ir, inventory, plan = controlled_capacity_case()
    caps = a.fulfillment_capability_contracts()
    owner = a._owner_source_preconditions(revision, ir, inventory, caps,
        generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT, review_input_contract=p._REVIEW_INPUT_CONTRACT)
    choices = p._formation_binding_choices(inventory, caps, owner)
    view = p._review_input_view(inventory, plan, caps, {
        "existing_owner_source_preconditions": owner, "existing_owner_binding_domains": choices})
    shared = view["existing_owner_binding_domains"]
    if drift is None:
        assert p._restore_review_owner_domains(shared, owner) == choices
        assert len(json.dumps(shared).encode()) < len(json.dumps(choices).encode())
    else:
        row = next(r for r in shared if isinstance(r.get('necessary_source_proofs'), dict))
        operand = row['necessary_source_proofs']
        if drift == 'source': operand['existing_owner_prerequisite_ref'] = (row['source'] + 1) % len(shared)
        else: operand['field'] = 'ineligible_binding_prerequisites'
        with pytest.raises(p._FulfillmentWireReceiptIdentityError, match='REVIEW_INPUT_IDENTITY_DRIFT'):
            p._restore_review_owner_domains(shared, owner)


def test_invalid_critic_identity_is_bound_to_review_not_mislabeled_as_mapping_failure():
    from hashlib import sha256
    revision, ir, inventory, plan = controlled_capacity_case()
    count = 0
    def change(review):
        nonlocal count
        count += 1
        if count == 1:
            review["component_results"] = review["component_results"][:1]
            review["component_results"][0]["component_id"] = review["component_results"][0]["component_id"][:48]
    provider, calls = controlled_model_provider(inventory, plan, review_change=change)
    kwargs = {"provider": provider, "exact_target_paths": inventory["exact_target_paths"]}
    result = a.form_fulfillment_projection(revision, ir, **kwargs)
    assert result[0].formation_receipt["terminal_reason"] == "VALIDATED_PROJECTION" and len(calls) == 4
    failed = next(r for r in provider._fulfillment_receipts if r["stage"] == "CANDIDATE_VALIDATED" and r["attempt"] == 1)
    f = json.loads(failed["validation_feedback"])
    assert f["primary_error"] == "OBLIGATION_SEMANTIC_REVIEW_SCHEMA_INVALID"
    violation = next(v for v in f["violations"] if v.get("failed_owner") == "INDEPENDENT_SEMANTIC_REVIEW_OUTPUT")
    assert violation["formation_deterministic_status"] == "PASS_REVIEW_PENDING_ONLY"
    d = violation["review_contract_failure"]
    assert d["observed_component_count"] == 1 and d["required_component_count"] == len(plan.routes)
    assert d["missing_component_route_indices"] == list(range(len(plan.routes)))
    observed = next(r for r in provider._fulfillment_receipts if r["stage"] == "SEMANTIC_REVIEW_OBSERVED" and r["attempt"] == 1)
    assert d["review_output_sha256"] == sha256(observed["review_output"].encode()).hexdigest()
    assert f["semantic_review_feedback_binding"]["observed_receipt_id"] == observed["receipt_id"]
    assert "INDEPENDENT_SEMANTIC_REVIEW" in f["not_evaluable"]
    original = deepcopy(provider._fulfillment_receipts)
    a.form_fulfillment_projection(revision, ir, **kwargs)
    assert len(calls) == 4 and provider._fulfillment_receipts == original
    f["semantic_review_feedback_binding"]["review_output_sha256"] = "0" * 64
    failed["validation_feedback"] = json.dumps(f, separators=(",", ":"))
    stopped = a.form_fulfillment_projection(revision, ir, **kwargs)
    assert stopped[0].formation_receipt["terminal_reason"] == "OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT"
    assert len(calls) == 4


def test_review_schema_observation_never_backfills_missing_ids_or_uses_invalid_verdicts():
    from tests.test_c3_semantic_contract_calibration import review
    _, _, inventory, plan = controlled_capacity_case()
    raw = review(inventory, plan).model_dump(mode="json")
    before = deepcopy(raw)
    assert p._review_schema_failure_observation(json.dumps(raw), inventory, plan) is None
    raw["component_results"][0]["component_id"] = "wrong-id"
    raw["private arbitrary provider field must not be published"] = "private payload"
    d = p._review_schema_failure_observation(json.dumps(raw), inventory, plan)
    assert d["schema_errors"] and 0 in d["missing_component_route_indices"]
    assert "INDEPENDENT_SEMANTIC_EQUIVALENCE" in d["not_evaluable"]
    assert "private arbitrary" not in json.dumps(d) and "private payload" not in json.dumps(d)
    assert raw["component_results"][0]["component_id"] == "wrong-id"
    invalid = p._review_schema_failure_observation("{", inventory, plan)
    assert invalid["observed_component_count"] == 0 and invalid["missing_component_route_indices"] == list(range(len(plan.routes)))
    assert before["component_results"][0]["component_id"] != "wrong-id"


def test_observed_only_invalid_json_review_recovers_without_repeating_critic():
    from dataclasses import replace
    revision, ir, inventory, plan = controlled_capacity_case()
    provider, calls = controlled_model_provider(inventory, plan)
    runtime = provider.runtime_factory()
    generate = runtime.generate
    seen = 0
    def invalid_once(**request):
        nonlocal seen
        result = generate(**request)
        if 'untrusted_fulfillment_candidate' in json.loads(request['input_text']):
            seen += 1
            if seen == 1:
                result = replace(result, output_text='{')
        return result
    runtime.generate = invalid_once
    original_review = provider.review
    class AfterObserved(BaseException):
        pass
    stopped = False
    def interrupt(inventory, candidate, *, capabilities, receipt_callback=None, owner_preconditions=None):
        def observe(**values):
            nonlocal stopped
            receipt_callback(**values)
            if not stopped:
                stopped = True
                raise AfterObserved()
        return original_review(inventory, candidate, capabilities=capabilities,
            owner_preconditions=owner_preconditions, receipt_callback=observe)
    provider.review = interrupt
    kwargs = {'provider': provider, 'exact_target_paths': inventory['exact_target_paths']}
    with pytest.raises(AfterObserved):
        a.form_fulfillment_projection(revision, ir, **kwargs)
    assert len(calls) == 2
    result = a.form_fulfillment_projection(revision, ir, **kwargs)
    assert result[0].formation_receipt['terminal_reason'] == 'VALIDATED_PROJECTION'
    assert len(calls) == 4 and seen == 2
    failed = next(r for r in provider._fulfillment_receipts if r['stage'] == 'SEMANTIC_REVIEW_VALIDATED' and r['attempt'] == 1)
    assert failed['review_contract_failure']['observed_component_count'] == 0
    assert failed['failed_predicate'] == 'OBLIGATION_SEMANTIC_REVIEW_SCHEMA_INVALID'
    a.form_fulfillment_projection(revision, ir, **kwargs)
    assert len(calls) == 4


def test_legacy_request_marker_preserves_formation_instructions():
    revision, ir, inventory, plan = controlled_capacity_case()
    provider, calls = controlled_model_provider(inventory, plan)
    runtime = provider.runtime_factory(); generate = runtime.generate; instructions = []
    def capture(**request):
        instructions.append(request['instructions'])
        return generate(**request)
    runtime.generate = capture
    caps = a.fulfillment_capability_contracts()
    legacy = a._owner_source_preconditions(revision, ir, inventory, caps,
        generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT,
        raw_operand_observation_contract='existing-original-wire-owner-operands-v1')
    provider.form(inventory, caps, owner_preconditions=legacy)
    assert len(instructions[0].encode()) == 7413
    assert 'INDEPENDENT_SEMANTIC_REVIEW_OUTPUT' not in instructions[0]
    fresh = {**legacy, 'review_input_contract': p._REVIEW_INPUT_CONTRACT}
    provider.form(inventory, caps, owner_preconditions=fresh)
    assert instructions[1].startswith(instructions[0])
    assert 'INDEPENDENT_SEMANTIC_REVIEW_OUTPUT' in instructions[1]


@pytest.mark.parametrize('scale', ['small', 'medium', 'complex'])
def test_primary_meaning_view_keeps_complete_owner_choices_without_duplicating_a_checklist(scale, record_property):
    revision, ir, inventory, plan = controlled_capacity_case(scale)
    caps = a.fulfillment_capability_contracts()
    owner = a._owner_source_preconditions(revision, ir, inventory, caps,
        generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT,
        semantic_selection_input_contract=p._PRIMARY_MEANING_INPUT_CONTRACT)
    before = deepcopy((inventory, owner))
    context = p._fulfillment_wire_context(inventory, caps, owner_preconditions=owner)
    view = p._source_consumer_input(inventory, caps, context, owner)
    restored = p._restore_primary_meaning_input(view)
    assert view['owner_source_preconditions'] == owner
    for original, row in zip(restored['temporary_wire']['source_index_table'], view['temporary_wire']['source_index_table'], strict=True):
        assert 'necessary_capability_domain' not in row and 'conditional_provenance_operands' not in row
        assert original['primary_semantic_text'] == row['primary_semantic_text']
        assert original['whole_source_basis'] == row['whole_source_basis']
        assert original['owner_prerequisites_ref'] == row['index']
    comparison = deepcopy(owner); comparison.pop('semantic_selection_input_contract')
    legacy = p._source_consumer_input(inventory, caps,
        p._fulfillment_wire_context(inventory, caps, owner_preconditions=comparison), comparison)
    assert [r['primary_semantic_text'] for r in view['temporary_wire']['source_index_table']] == [r['primary_semantic_text'] for r in legacy['temporary_wire']['source_index_table']]
    assert len(json.dumps(view)) < len(json.dumps(restored))
    record_property('complete_joined_bytes', len(json.dumps(restored, ensure_ascii=False).encode()))
    record_property('primary_meaning_reference_bytes', len(json.dumps(view, ensure_ascii=False).encode()))
    assert (inventory, owner) == before
    a.validate_projection_candidate(plan, revision, ir, inventory, allow_review_pending=True, source_contract='v3', owner_preconditions=owner)
    with pytest.raises(ValueError, match='REVIEW_REQUIRED'):
        a.validate_projection_candidate(plan, revision, ir, inventory, source_contract='v3', owner_preconditions=owner)


@pytest.mark.parametrize('drift', ['owner-ref', 'source-ref', 'reintroduced-domain', 'unknown-marker'])
def test_primary_meaning_reference_drift_cannot_change_source_or_owner_choices(drift):
    revision, ir, inventory, plan = controlled_capacity_case()
    caps = a.fulfillment_capability_contracts()
    owner = a._owner_source_preconditions(revision, ir, inventory, caps,
        generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT,
        semantic_selection_input_contract=p._PRIMARY_MEANING_INPUT_CONTRACT)
    view = p._source_consumer_input(inventory, caps, p._fulfillment_wire_context(inventory, caps, owner_preconditions=owner), owner)
    row = view['temporary_wire']['source_index_table'][0]
    if drift == 'owner-ref': row['owner_prerequisites_ref'] = 1
    elif drift == 'source-ref': row['source_ref'] = inventory['sources'][1]['source_ref']
    elif drift == 'reintroduced-domain': row['necessary_capability_domain'] = [0]
    else: view['semantic_selection_input_contract'] = 'invented'
    with pytest.raises(p._FulfillmentWireReceiptIdentityError): p._restore_primary_meaning_input(view)


@pytest.mark.parametrize('change', ['valid-prefix', 'wrong-header', 'duplicate-key', 'incomplete', 'legacy'])
def test_complete_value_owner_checks_observe_original_wire_without_admitting_prefix(change):
    from hashlib import sha256
    from tests.test_c3_fulfillment_capacity_representation import controlled_wire
    revision, ir, inventory, plan = controlled_capacity_case()
    caps = a.fulfillment_capability_contracts()
    owner = a._owner_source_preconditions(revision, ir, inventory, caps,
        generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT,
        semantic_selection_input_contract=p._PRIMARY_MEANING_INPUT_CONTRACT if change != 'legacy' else None)
    wire, _ = controlled_wire(inventory, plan, owner_preconditions=owner)
    wire['routes'][0]['t'] = []
    wire['routes'][0]['f'] = [next(i for i,s in enumerate(inventory['sources']) if s['kind'] != 'FACT')]
    if change == 'wrong-header': wire['h'] = '0'*64
    raw = json.dumps(wire)
    if change == 'duplicate-key': raw = '{"v":1,' + raw[1:]
    elif change == 'incomplete': raw = raw[:-1]
    raw += '}'
    if change == 'incomplete': raw = raw[:-3]
    observed = p._raw_fulfillment_owner_operands(raw, inventory, caps, owner_preconditions=owner)
    if change == 'valid-prefix':
        assert any('OBLIGATION_CONTENT_TARGET_UNRESOLVED' in v['failed_predicates'] for v in observed['violations'])
        assert observed['complete_value_observation']['original_wire_sha256'] == sha256(raw.encode()).hexdigest()
        assert observed['complete_value_observation']['trailing_bytes'] == 1
        assert 'COMPLETE_WIRE_SYNTAX' in observed['not_evaluable']
        assert 'SEMANTIC_EQUIVALENCE' in observed['not_evaluable']
        with pytest.raises(p._FulfillmentWireValidationError, match='WIRE_JSON_INVALID'):
            p._decode_fulfillment_candidate_wire(raw, inventory, caps, owner_preconditions=owner)
    else:
        assert observed == {'violations': [], 'not_evaluable': ['ORIGINAL_WIRE_OWNER_OPERANDS']}


def test_new_selection_hint_does_not_rewrite_legacy_request_or_grant_an_operation():
    revision, ir, inventory, plan = controlled_capacity_case()
    caps = a.fulfillment_capability_contracts()
    old = a._owner_source_preconditions(revision, ir, inventory, caps,
        generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT)
    assert 'semantic_selection_input_contract' not in old
    new = a._owner_source_preconditions(revision, ir, inventory, caps,
        generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT,
        semantic_selection_input_contract=p._PRIMARY_MEANING_INPUT_CONTRACT)
    assert p._fulfillment_wire_context(inventory, caps, owner_preconditions=old)['wire_request_fingerprint'] != p._fulfillment_wire_context(inventory, caps, owner_preconditions=new)['wire_request_fingerprint']
    assert p._fulfillment_wire_context(inventory, caps, owner_preconditions=old)['wire_table_fingerprint'] == p._fulfillment_wire_context(inventory, caps, owner_preconditions=new)['wire_table_fingerprint']
    assert 'alternative justifications for ONE proposed binding' in p._primary_meaning_instructions(new)
    assert new['sources'] == old['sources']
    with pytest.raises(ValueError, match='REQUEST_VIEW_CONTRACT_INVALID'):
        a._owner_source_preconditions(revision, ir, inventory, caps,
            semantic_selection_input_contract=p._PRIMARY_MEANING_INPUT_CONTRACT)
    unsupported = plan.model_copy(update={'routes': (*plan.routes, plan.routes[0])})
    with pytest.raises(ValueError, match='DUPLICATE_ROUTE'):
        a.validate_projection_candidate(unsupported, revision, ir, inventory, allow_review_pending=True, source_contract='v3', owner_preconditions=new)


def test_invalid_fact_operand_cannot_hide_independent_original_source_and_scope_rejections():
    from tests.test_c3_fulfillment_capacity_representation import controlled_wire
    revision,ir,inventory,plan=controlled_capacity_case()
    caps=a.fulfillment_capability_contracts()
    owner=a._owner_source_preconditions(revision,ir,inventory,caps,
        generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT,
        raw_operand_observation_contract="existing-original-wire-owner-operands-v1")
    wire,context=controlled_wire(inventory,plan,owner_preconditions=owner)
    ordinal=next(i for i,r in enumerate(wire["routes"]) if r["u"] and
        any(proof["capability"]==r["c"] for proof in owner["sources"][r["s"]].get("necessary_source_proofs",[])))
    route=wire["routes"][ordinal]
    nonfact=next(i for i,s in enumerate(inventory["sources"]) if s["kind"]!="FACT")
    route["f"]=[nonfact]
    route["u"]=[]
    route["c"]=next(i for i,c in enumerate(caps) if c["capability"]=="GIT_DIFF_SCOPE")
    route["t"]=[]
    # Obtain a route whose Git consumer actually has a source prerequisite.
    proof=next((p for p in owner["sources"][route["s"]].get("necessary_source_proofs",[]) if p["capability"]==route["c"]),None)
    if proof is None:
        route["c"]=next(p["capability"] for p in owner["sources"][route["s"]]["necessary_source_proofs"])
    raw=json.dumps(wire);before=deepcopy((wire,inventory,owner))
    with pytest.raises(p._FulfillmentWireValidationError,match="FACT_KIND_INVALID"):
        p._decode_fulfillment_candidate_wire(raw,inventory,caps,owner_preconditions=owner)
    observed=p._raw_fulfillment_owner_operands(raw,inventory,caps,owner_preconditions=owner)
    failure=next(f for f in observed["violations"] if f["route"]==ordinal)
    assert "OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN" in failure["failed_predicates"]
    if caps[route["c"]]["capability"]=="GIT_DIFF_SCOPE":
        assert "OBLIGATION_DIFF_SCOPE_INCOMPLETE" in failure["failed_predicates"]
    assert "SEMANTIC_EQUIVALENCE" in observed["not_evaluable"]
    assert "ASSURANCE" in observed["not_evaluable"]
    assert (wire,inventory,owner)==before
    repair=a._owner_repair_context(raw,revision,ir,inventory,caps,validation_feedback=None,owner_preconditions=owner)
    assert {k:v for k,v in repair["original_wire_owner_operands"].items()
        if k!="definite_fact_self_dependencies"}==observed
    assert "COMPLETE_PLAN_ADMISSION" in repair["not_evaluable"]
    legacy=a._owner_source_preconditions(revision,ir,inventory,caps,generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT)
    legacy_wire,_=controlled_wire(inventory,plan,owner_preconditions=legacy)
    legacy_context=a._owner_repair_context(json.dumps(legacy_wire),revision,ir,inventory,caps,
        validation_feedback=None,owner_preconditions=legacy)
    assert "original_wire_owner_operands" not in legacy_context


@pytest.mark.parametrize("change",["header","syntax","owner-marker"])
def test_original_wire_owner_operands_fail_closed_on_non_evaluable_identity(change):
    from tests.test_c3_fulfillment_capacity_representation import controlled_wire
    revision,ir,inventory,plan=controlled_capacity_case()
    caps=a.fulfillment_capability_contracts()
    owner=a._owner_source_preconditions(revision,ir,inventory,caps)
    wire,_=controlled_wire(inventory,plan,owner_preconditions=owner)
    if change=="header":wire["h"]="0"*64
    if change=="owner-marker":
        with pytest.raises(ValueError):a._owner_source_preconditions(revision,ir,inventory,caps,
            raw_operand_observation_contract="invented")
        return
    raw="{" if change=="syntax" else json.dumps(wire)
    observed=p._raw_fulfillment_owner_operands(raw,inventory,caps,owner_preconditions=owner)
    assert observed["violations"]==[] and observed["not_evaluable"]==["ORIGINAL_WIRE_OWNER_OPERANDS"]


def test_raw_operand_feedback_uses_bound_original_wire_and_preserves_two_candidate_replay():
    revision,ir,inventory,plan=controlled_capacity_case()
    calls_count=0
    def invalid_operand(wire):
        nonlocal calls_count
        calls_count+=1
        if calls_count==1:
            wire["routes"][0]["f"]=[next(i for i,s in enumerate(inventory["sources"]) if s["kind"]!="FACT")]
            wire["routes"][0]["t"]=[]
    provider,calls=controlled_model_provider(inventory,plan,wire_change=invalid_operand)
    kwargs={"provider":provider,"exact_target_paths":inventory["exact_target_paths"]}
    result=a.form_fulfillment_projection(revision,ir,**kwargs)
    assert len(calls)==3 and result[0].formation_receipt["terminal_reason"]=="VALIDATED_PROJECTION"
    failed=next(r for r in provider._fulfillment_receipts if r["stage"]=="CANDIDATE_VALIDATED" and r["attempt"]==1)
    feedback=json.loads(failed["validation_feedback"])
    from hashlib import sha256
    assert sha256(feedback["untrusted_previous_wire"].encode()).hexdigest()==feedback["repair_feedback_binding"]["wire_output_fingerprint"]
    original=next(r for r in provider._fulfillment_receipts if r["stage"]=="MODEL_RESPONSE_OBSERVED" and r["attempt"]==1)
    assert feedback["repair_feedback_binding"]["response_receipt_id"]==original["receipt_id"]
    failures=feedback["owner_repair_context"]["original_wire_owner_operands"]["violations"]
    assert any(f["route"]==0 and "OBLIGATION_CONTENT_TARGET_UNRESOLVED" in f["failed_predicates"] for f in failures)
    rows=deepcopy(provider._fulfillment_receipts)
    a.form_fulfillment_projection(revision,ir,**kwargs)
    assert provider._fulfillment_receipts==rows and len(calls)==3
    observed=feedback["owner_repair_context"]["original_wire_owner_operands"]
    observed["violations"][0]["raw_route_fingerprint"]="0"*64
    failed["validation_feedback"]=json.dumps(feedback,separators=(",",":"))
    stopped=a.form_fulfillment_projection(revision,ir,**kwargs)
    assert stopped[0].formation_receipt["terminal_reason"]=="OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT"
    assert len(calls)==3


def test_valid_original_wire_operands_are_not_reported_as_failed_or_as_evidence():
    from tests.test_c3_fulfillment_capacity_representation import controlled_wire
    revision,ir,inventory,plan=controlled_capacity_case()
    caps=a.fulfillment_capability_contracts()
    owner=a._owner_source_preconditions(revision,ir,inventory,caps)
    wire,_=controlled_wire(inventory,plan,owner_preconditions=owner)
    observed=p._raw_fulfillment_owner_operands(json.dumps(wire),inventory,caps,owner_preconditions=owner)
    assert observed["violations"]==[] and "SEMANTIC_EQUIVALENCE" in observed["not_evaluable"]


def test_unrelated_invalid_sibling_cannot_hide_proven_mixed_acceptance_self_dependency():
    from tests.test_c3_generation_owner_domains import mixed_current_proof_case
    from tests.test_c3_fulfillment_capacity_representation import controlled_wire
    revision,ir,inventory,plan,_=mixed_current_proof_case(self_reference=True)
    caps=a.fulfillment_capability_contracts()
    owner=a._owner_source_preconditions(revision,ir,inventory,caps,
        raw_operand_observation_contract="existing-original-wire-owner-operands-v1")
    wire,_=controlled_wire(inventory,plan,owner_preconditions=owner)
    own=next(i for i,s in enumerate(inventory["sources"]) if s["source_ref"]==plan.routes[0].source_ref)
    sibling=next(r for r in wire["routes"] if r["s"]!=own)
    sibling["f"]=[next(i for i,s in enumerate(inventory["sources"]) if s["kind"]!="FACT")]
    raw=json.dumps(wire);before=deepcopy(wire)
    repair=a._owner_repair_context(raw,revision,ir,inventory,caps,validation_feedback=None,owner_preconditions=owner)
    failed=repair["original_wire_owner_operands"]["definite_fact_self_dependencies"]
    assert failed and all(f["source"]==own for f in failed)
    assert all(f["code"]=="OBLIGATION_LINKED_FACT_DEPENDENCY_UNFULFILLABLE" for f in failed)
    assert repair["raw_routes_not_evaluable"] and "OWNER_BACKGROUND_CROSS_ROUTE_PRECONDITIONS" in repair["not_evaluable"]
    assert before==wire


def test_mixed_acceptance_self_dependency_is_not_broadcast_to_another_component():
    from tests.test_c3_generation_owner_domains import mixed_current_proof_case
    from tests.test_c3_fulfillment_capacity_representation import controlled_wire
    revision,ir,inventory,plan,_=mixed_current_proof_case(self_reference=True)
    content=plan.routes[0]
    other=next(s['source_ref'] for s in inventory['sources'] if s['kind']=='FACT' and s['source_ref']!=content.source_ref)
    distinct=content.model_copy(update={'component_basis':content.component_basis.model_copy(update={
        'linked_fact_refs':(other,), 'source_span_end':content.component_basis.source_span_end-1,
        'source_component_quote':content.component_basis.source_component_quote[:-1]})})
    plan=plan.model_copy(update={'routes':(*plan.routes,distinct)})
    caps=a.fulfillment_capability_contracts()
    owner=a._owner_source_preconditions(revision,ir,inventory,caps,
        raw_operand_observation_contract='existing-original-wire-owner-operands-v1')
    wire,_=controlled_wire(inventory,plan,owner_preconditions=owner)
    result=a._owner_repair_context(json.dumps(wire),revision,ir,inventory,caps,
        validation_feedback=None,owner_preconditions=owner)['original_wire_owner_operands']
    failures=result['definite_fact_self_dependencies']
    assert any(f['route']==0 for f in failures)
    assert all(f['route']!=len(plan.routes)-1 for f in failures)

@pytest.mark.parametrize("scale", ["small", "medium", "complex"])
def test_new_request_reuses_canonical_domains_and_full_owner_proofs(scale, record_property):
    revision,ir,inventory,plan=controlled_capacity_case(scale)
    caps=a.fulfillment_capability_contracts()
    old=a._owner_source_preconditions(revision,ir,inventory,caps,generation_view_contract="existing-lossless-source-consumer-input-v2")
    new=a._owner_source_preconditions(revision,ir,inventory,caps,generation_view_contract=p._SOURCE_CONSUMER_INPUT_CONTRACT)
    before=deepcopy((inventory,new))
    schema=p._formation_output_schema(inventory,caps,owner_preconditions=new)
    legacy=p._formation_output_schema(inventory,caps,owner_preconditions=old)
    assert "anyOf" not in schema["properties"]["routes"]["items"]
    assert "anyOf" in legacy["properties"]["routes"]["items"]
    assert len(json.dumps(schema)) < len(json.dumps(legacy))/2
    record_property("previous_request_schema_bytes",len(json.dumps(legacy).encode()))
    record_property("current_request_schema_bytes",len(json.dumps(schema).encode()))
    payload=p._source_consumer_input(inventory,caps,p._fulfillment_wire_context(inventory,caps,owner_preconditions=new),new)
    assert payload["owner_source_preconditions"]==new
    for row,choice in zip(payload["temporary_wire"]["source_index_table"],p._formation_binding_choices(inventory,caps,new),strict=True):
        assert row["conditional_provenance_operands"]==p._formation_provenance_operands(choice,caps)
    assert (inventory,new)==before
    a.validate_projection_candidate(plan,revision,ir,inventory,allow_review_pending=True,source_contract="v3",owner_preconditions=new)
    with pytest.raises(ValueError):a.validate_projection_candidate(plan,revision,ir,inventory,source_contract="v3",owner_preconditions=new)
    wrong=plan.model_copy(update={"routes":tuple(r.model_copy(update={"target_paths":("unauthorized.html",)}) if r.target_paths else r for r in plan.routes)})
    with pytest.raises(ValueError):a.validate_projection_candidate(wrong,revision,ir,inventory,allow_review_pending=True,source_contract="v3",owner_preconditions=new)
    drift=deepcopy(new);drift["sources"][0]["source_ref"]="substituted"
    with pytest.raises(p._FulfillmentWireReceiptIdentityError):p._formation_output_schema(inventory,caps,owner_preconditions=drift)


@pytest.mark.parametrize("case", ["feedback_fits", "row_limit", "next_request_limit"])
def test_expanded_capacity_reject_provides_same_wire_bound_owner_feedback_without_relaxation(case):
    revision,ir,inventory,plan=controlled_capacity_case()
    if case=="feedback_fits":
        # Legitimate long original source, kept losslessly; only its unadmitted
        # repeated proposal exceeds the expanded Candidate limit.
        first=revision.engineering_semantic_facts[0]
        text=first.provenance.source_text+" Original controlled provenance."*800
        first=first.model_copy(update={"provenance":first.provenance.model_copy(update={"source_text":text})})
        revision.engineering_semantic_facts=(first,*revision.engineering_semantic_facts[1:])
        inventory=a.fulfillment_inventory(revision,ir,exact_target_paths=inventory["exact_target_paths"])
        changed=plan.routes[0].model_copy(update={"component_basis":plan.routes[0].component_basis.model_copy(update={"source_span_end":len(text),"source_component_quote":text})})
        plan=plan.model_copy(update={"inventory_fingerprint":inventory["inventory_fingerprint"],"routes":(changed,*plan.routes[1:])})
    attempts=0
    def oversized(wire):
        nonlocal attempts
        attempts+=1
        if attempts==1:
            if case=="feedback_fits":
                wire["routes"].extend([deepcopy(wire["routes"][0]),deepcopy(wire["routes"][0])])
                return
            count=64 if case=="next_request_limit" else 130
            wire["routes"]=[deepcopy(wire["routes"][i%len(wire["routes"])]) for i in range(count)]
            if case=="next_request_limit":
                # Reach the real expanded limit using untrusted rationale, while
                # retaining an affordable number of source/route observations.
                base=plan.model_copy(update={"routes":tuple(plan.routes[i%len(plan.routes)].model_copy(update={"rationale":""}) for i in range(count))})
                size=(MAX_CANDIDATE_BYTES+128-len(base.model_dump_json().encode()))//count+1
                assert 0<size<=1000
                for route in wire["routes"]:route["r"]="x"*size
            else:
                for route in wire["routes"]:route["r"]="Unadmitted controlled repeated proposal. "*6
    provider,calls=controlled_model_provider(inventory,plan,wire_change=oversized)
    result=a.form_fulfillment_projection(revision,ir,provider=provider,exact_target_paths=inventory["exact_target_paths"])
    failed=next(r for r in provider._fulfillment_receipts if r["stage"]=="CANDIDATE_VALIDATED" and r["attempt"]==1)
    assert failed["failed_predicate"]=="OBLIGATION_FORMATION_EXPANDED_RECEIPT_LIMIT"
    assert failed.get("candidate") is None and failed["validation_passed"] is False
    if case in {"row_limit", "next_request_limit"}:
        assert result[0].formation_receipt["terminal_reason"]=="OBLIGATION_FORMATION_RECEIPT_LIMIT"
        assert all(b.state=="UNRESOLVED" for b in result) and len(calls)==1
        terminal=next(r for r in reversed(provider._fulfillment_receipts) if r.get("terminal"))
        assert "validation_feedback" not in terminal
        assert terminal["capacity_observation"]["original_row_bytes"]>131072
        if case=="next_request_limit":
            assert failed["repair_feedback_bound"] and failed["owner_repair_context_bound"]
            assert terminal["stage"]=="MODEL_REQUEST_PENDING"
        before=deepcopy(provider._fulfillment_receipts)
        a.form_fulfillment_projection(revision,ir,provider=provider,exact_target_paths=inventory["exact_target_paths"])
        assert provider._fulfillment_receipts==before and len(calls)==1
        if case=="next_request_limit":
            dropped=next(d for d in terminal["capacity_observation"]["dropped_fields"] if d["field"]=="feedback")
            dropped["sha256"]="0"*64
            rejected=a.form_fulfillment_projection(revision,ir,provider=provider,exact_target_paths=inventory["exact_target_paths"])
            assert rejected[0].formation_receipt["terminal_reason"]=="OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT"
            assert len(calls)==1
        return
    assert failed["repair_feedback_bound"] and failed["owner_repair_context_bound"]
    assert "validation_feedback" in failed, failed.get("capacity_observation")
    feedback=json.loads(failed["validation_feedback"])
    assert feedback["violations"][0]["limit_bytes"]==MAX_CANDIDATE_BYTES==65536
    assert feedback["violations"][0]["expanded_bytes"]>65536
    assert feedback["owner_repair_context"]["violations"]
    assert len(feedback["untrusted_previous_wire"].encode())<=65536
    assert len(calls)==3 and result[0].formation_receipt["terminal_reason"]=="VALIDATED_PROJECTION", {"reason":result[0].formation_receipt["terminal_reason"],"stages":[(r["stage"],r.get("failed_predicate"),r.get("terminal_reason")) for r in provider._fulfillment_receipts]}
    before=deepcopy(provider._fulfillment_receipts)
    a.form_fulfillment_projection(revision,ir,provider=provider,exact_target_paths=inventory["exact_target_paths"])
    assert provider._fulfillment_receipts==before and len(calls)==3


@pytest.mark.parametrize("tamper", ["sha256", "parent"])
def test_canonical_rejection_next_request_capacity_preserves_parent_identity(monkeypatch, tamper):
    revision,ir,inventory,plan=controlled_capacity_case()
    def duplicate(wire):wire["routes"].append(deepcopy(wire["routes"][0]))
    provider,calls=controlled_model_provider(inventory,plan,wire_change=duplicate)
    bind=a._bind_repair_feedback
    def bounded_failure_large_request(*args,**kwargs):
        data=json.loads(bind(*args,**kwargs));data["controlled_test_padding"]="x"*105000
        return json.dumps(data,separators=(",",":"))
    monkeypatch.setattr(a,"_bind_repair_feedback",bounded_failure_large_request)
    kwargs={"provider":provider,"exact_target_paths":inventory["exact_target_paths"]}
    result=a.form_fulfillment_projection(revision,ir,**kwargs)
    assert result[0].formation_receipt["terminal_reason"]=="OBLIGATION_FORMATION_RECEIPT_LIMIT" and len(calls)==1
    failed=next(r for r in provider._fulfillment_receipts if r["stage"]=="CANDIDATE_VALIDATED")
    terminal=provider._fulfillment_receipts[-1]
    assert failed.get("predecode_diagnostics") is None and failed["repair_feedback_bound"]
    assert terminal["stage"]=="MODEL_REQUEST_PENDING" and terminal["capacity_observation"]
    before=deepcopy(provider._fulfillment_receipts)
    a.form_fulfillment_projection(revision,ir,**kwargs)
    assert provider._fulfillment_receipts==before and len(calls)==1
    if tamper=="sha256":next(d for d in terminal["capacity_observation"]["dropped_fields"] if d["field"]=="feedback")["sha256"]="0"*64
    else:terminal["feedback_receipt_id"]="00000000-0000-0000-0000-000000000000"
    rejected=a.form_fulfillment_projection(revision,ir,**kwargs)
    assert rejected[0].formation_receipt["terminal_reason"]=="OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT"
    assert len(calls)==1 and all(b.state=="UNRESOLVED" for b in rejected)


@pytest.mark.parametrize("tamper", [False, True])
def test_first_request_capacity_has_no_parent_and_never_dispatches(monkeypatch, tamper):
    revision,ir,inventory,plan=controlled_capacity_case()
    provider,calls=controlled_model_provider(inventory,plan)
    owner=a._owner_source_preconditions
    def excessive_owner_input(*args,**kwargs):
        result=owner(*args,**kwargs);result["controlled_test_padding"]="x"*140000
        return result
    monkeypatch.setattr(a,"_owner_source_preconditions",excessive_owner_input)
    kwargs={"provider":provider,"exact_target_paths":inventory["exact_target_paths"]}
    result=a.form_fulfillment_projection(revision,ir,**kwargs)
    assert len(calls)==0 and result[0].formation_receipt["terminal_reason"]=="OBLIGATION_FORMATION_RECEIPT_LIMIT"
    rows=provider._fulfillment_receipts
    assert len(rows)==1 and rows[0]["stage"]=="MODEL_REQUEST_PENDING" and rows[0]["attempt"]==1
    assert rows[0].get("feedback_receipt_id") is None and rows[0]["capacity_observation"]
    before=deepcopy(rows)
    a.form_fulfillment_projection(revision,ir,**kwargs)
    assert rows==before and len(calls)==0
    if tamper:
        next(d for d in rows[0]["capacity_observation"]["dropped_fields"] if d["field"]=="feedback")["sha256"]="0"*64
        rejected=a.form_fulfillment_projection(revision,ir,**kwargs)
        assert rejected[0].formation_receipt["terminal_reason"]=="OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT"
        assert len(calls)==0 and all(b.state=="UNRESOLVED" for b in rejected)
