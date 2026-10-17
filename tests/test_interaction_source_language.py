"""Known Owner citations survive follow-up turns; language never changes authority."""
from copy import deepcopy
import json
from types import SimpleNamespace as NS
from uuid import uuid4

import pytest

from spg.application.interaction_references import (
    available_supporting_references, validate_supporting_references,
)
from spg.application.intent_realization import validate_semantic_candidate
from spg.application.model_language import exclusion_constraint
from spg.domain.interaction import InteractionInvariantViolation
from spg.domain.intent_realization import ObservedEffect, ProductionSufficiency
from spg.providers.deepseek_interaction import DeepSeekInteractionSemanticCapability
from spg.providers.interaction_contract import InteractionSemanticContract
from tests.irk_test_fixtures import semantic_candidate


def basis(text="把阅读页的字号放大一些，再给我看看。"):
    record = NS(id=uuid4(), actor="HUMAN", content=text, supporting_references=())
    verification = "VERIFICATION:" + str(uuid4())
    active = NS(relevant_reality_references=(verification, "WORK_REALITY_REVISION:" + str(uuid4())),
        work_revision=NS(engineering_semantic_facts=()))
    value = NS(records=(record,), active_work_context=active, observed_reality=(),
        governed_semantic_history=(), prior_assessment=None, basis_fingerprint="a" * 64)
    return value, record, verification


@pytest.mark.parametrize("kind", ["VERIFICATION", "COMPLETION", "ENGINEERING_FINDING", "RUNTIME_FACT", "STEERING_DECISION"])
def test_actual_active_owner_citation_does_not_require_duplicate_human_attachment(kind):
    value, _, _ = basis()
    ref = kind + ":" + str(uuid4())
    value.active_work_context.relevant_reality_references = (ref,)
    before = deepcopy(vars(value.active_work_context))
    assert validate_supporting_references((ref,), value) == (ref,)
    assert value.records[0].supporting_references == ()
    assert before == vars(value.active_work_context)


def test_observed_owner_and_attached_sources_are_citable_without_creating_authority():
    value, record, ref = basis()
    attached = "ENGINEERING_FINDING:" + str(uuid4())
    observed = "RUNTIME_FACT:" + str(uuid4())
    record.supporting_references = (attached,)
    value.observed_reality = (ObservedEffect(owner="bounded-reality",
        evidence_references=(observed,), facts={"state": "OBSERVED"}),)
    assert set(available_supporting_references(value)) == {ref, attached, observed}


@pytest.mark.parametrize("change", ["unknown", "removed", "wrong-type", "invalid-uuid"])
def test_unobserved_stale_or_malformed_references_remain_rejected(change):
    value, _, ref = basis()
    if change == "unknown": ref = "VERIFICATION:" + str(uuid4())
    elif change == "removed": value.active_work_context.relevant_reality_references = ()
    elif change == "wrong-type": ref = value.active_work_context.relevant_reality_references[1]
    else: ref = "VERIFICATION:unknown"
    with pytest.raises(InteractionInvariantViolation):
        validate_supporting_references((ref,), value)


def test_reference_rejection_reaches_existing_compiler_repair_before_admission():
    value, record, ref = basis()
    payload = NS(supporting_references=("VERIFICATION:" + str(uuid4()),),
        semantic_intent=semantic_candidate(record), neutral_semantic_extractions=(), semantic_fact_candidates=())
    with pytest.raises(ValueError, match="SEMANTIC_SUPPORTING_REFERENCE_UNGROUNDED"):
        DeepSeekInteractionSemanticCapability._validate_action_semantics(payload, value)
    payload.supporting_references = (ref,)
    DeepSeekInteractionSemanticCapability._validate_action_semantics(payload, value)


@pytest.mark.parametrize("repairable", [True, False])
def test_real_provider_reference_feedback_converges_or_stops_with_existing_budget(repairable):
    from tests.test_deepseek_wic_provider import _basis, _semantics, _runtime, _Adapter
    from spg.providers.deepseek_interaction import DeepSeekWorkInteractionCapability
    from spg.domain.interaction import StructuredResponseSchemaViolation
    source = "VERIFICATION:" + str(uuid4())
    value = _basis().model_copy(update={"observed_reality": (
        ObservedEffect(owner="verification", evidence_references=(source,), facts={"result": "PASS"}),)})
    bad = json.loads(_semantics())
    bad["supporting_references"] = ["VERIFICATION:" + str(uuid4())]
    good = {**bad, "supporting_references": [source]}
    outputs = [json.dumps(bad), json.dumps(good)] if repairable else [json.dumps(bad)] * 4
    runtime, adapter = _runtime(_Adapter(outputs))
    capability = DeepSeekWorkInteractionCapability(runtime=runtime)
    emitted = []
    def interpret():
        return capability.interpret_controlled_stream_observed(value,
            on_response_delta=emitted.append, on_pipeline_stage=lambda _: None)
    if repairable:
        result = interpret()
        assert result.supporting_references == (source,)
        assert adapter.calls == 2
    else:
        with pytest.raises(StructuredResponseSchemaViolation, match="bounded_repair_exhausted"):
            interpret()
        assert adapter.calls == 4
    assert emitted == []
    assert "SEMANTIC_SUPPORTING_REFERENCE_UNGROUNDED" in adapter.requests[1]["instructions"]
    assert source in adapter.requests[1]["instructions"]


def test_sufficiency_accepts_exact_active_context_but_not_unobserved_context():
    value, record, ref = basis()
    candidate = semantic_candidate(record).model_copy(update={"production_sufficiency":
        ProductionSufficiency(status="READY", context_references=(ref,), reason="当前修改可逆，已提供实际上下文。")})
    validate_semantic_candidate(candidate, value)
    value.active_work_context.relevant_reality_references = ()
    with pytest.raises(ValueError, match="PRODUCTION_DEFINITION_CONTEXT_UNGROUNDED"):
        validate_semantic_candidate(candidate, value)


@pytest.mark.parametrize("text,chinese", [("制作一页花园浇水记录，先不做远程控制。", True),
    ("Build a garden watering log without remote control.", False)])
def test_semantic_prompt_selects_language_without_translating_exact_source(text, chinese):
    value, _, ref = basis(text)
    value.interaction = NS(selected_design_schema_identity=None, selected_design_schema_version=None)
    value.model_dump = lambda **_: {"records": [{"content": text}]}
    before = deepcopy(value.model_dump())
    instruction = InteractionSemanticContract.instruction(value)
    assert text in instruction and ref in instruction
    assert instruction.startswith("你是 Watt") if chinese else instruction.startswith("Interpret one Human")
    assert before == value.model_dump()


def test_chinese_projection_is_still_an_exact_typed_exclusion_source():
    from tests.test_production_brief_admission import brief_case, admit
    revision, ir = brief_case("一页植物养护记录", "远程控制水阀")
    old = exclusion_constraint("远程控制水阀", chinese=False)
    new = exclusion_constraint("远程控制水阀", chinese=True)
    revision.constraints = tuple(new if text == old else text for text in revision.constraints)
    bindings = admit(revision, ir)
    result = next(b for b in bindings if b.source_quote == new)
    assert result.state == "BOUND_PENDING_EVIDENCE"
    assert result.evidence_method == "EXACT_CANDIDATE_CONTENT"
    assert result.component_basis.source_component_quote == new


def test_executor_prompt_changes_language_without_changing_contract_or_tool_grants():
    from tests.test_deepseek_inference_adapter import _request
    from spg.infrastructure.executor_runtime.inference import DeepSeekResponsesInferenceAdapter
    request = _request().model_copy(update={"objective": "将日历页改成按周显示，保留现有权限。"})
    adapter = DeepSeekResponsesInferenceAdapter(model="test", api_key="test", base_url="http://invalid.local")
    before = request.model_dump(mode="json")
    payload, names = adapter._request_payload(request)
    assert payload["instructions"].startswith("你是 Watt")
    assert json.loads(payload["input"]) == before
    assert "CONTINUE 仅能用 API 函数调用" in payload["instructions"]
    assert names and before == request.model_dump(mode="json")


@pytest.mark.parametrize("correction", [False, True])
def test_bounded_followup_retains_original_constraints_unless_typed_correction_replaces_them(correction):
    from spg.application.interaction import WorkInteractionService
    from spg.domain.interaction import InteractionAssessmentCandidate, WorkSatisfactionState
    from spg.domain.intent_realization import ProductionIntent, SemanticKind
    value, record, _ = basis("把日历加上周数和节气，先改一版再看看。")
    current = NS(motive="家庭日历", desired_outcome="单页可用家庭日历", context_facts=("原有配色保持",),
        constraints=("单页离线可用", "不接入第三方账户"), requests=("原始日历请求",))
    active = NS(work_revision=current, active_production_binding_id=uuid4(),
        satisfaction_state=WorkSatisfactionState.IN_PROGRESS)
    raw = semantic_candidate(record, production=ProductionIntent(objective=current.motive,
        primary_change="增加周数和节气", current=True, bounded_change=True))
    if correction:
        raw = raw.model_copy(update={"items": (*raw.items,
            raw.items[0].model_copy(update={"item_id": "correction", "kind": SemanticKind.CORRECTION, "production": None}))})
    candidate = InteractionAssessmentCandidate(semantic_intent=raw, interpreted_motive=current.motive,
        desired_outcome="增加周数和节气", candidate_constraints=("显示周数与节气",),
        candidate_context=("新的可逆展示细节",), current_requests=(record.content,),
        natural_response="继续调整当前日历。", provider_identity="declared:test")
    _, _, change = WorkInteractionService._normalize_active_candidate(candidate, active,
        latest_human_record_id=record.id)
    assert change is not None
    assert change.constraints == (("显示周数与节气",) if correction else (*current.constraints, "显示周数与节气"))
    assert ("原有配色保持" in change.context_facts) is (not correction)
    assert current.constraints == ("单页离线可用", "不接入第三方账户")
