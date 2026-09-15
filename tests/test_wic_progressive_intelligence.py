from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from pathlib import Path
import json
from uuid import NAMESPACE_URL, UUID, uuid5

from spg.application.interaction import WorkInteractionService, interaction_basis_fingerprint
from spg.application.wic_intelligence import build_progressive_semantics
from spg.application.wic_response import policy_governed_response, reconcile_fast_and_deep
from spg.application.wic_context import build_fast_context_card
from spg.application.wic_reception import DeterministicFastReceptionCapability
from spg.domain.interaction import (
    Interaction, InteractionActor, InteractionAssessment,
    InteractionAssessmentCandidate, InteractionCondition,
    InteractionInterpretationInput, InteractionRecord,
    WorkFocusClassification, WorkImpactDisposition,
)
from spg.domain.wic_intelligence import (
    GovernanceCandidateKind, InferenceDisposition, PatternSignal,
    QuestionDisposition, ReadinessTarget, SemanticAuthority,
    SemanticDeltaOperation, TransitionReadinessStatus,
)
from spg.domain.wic_response import ResponseReconciliation
from spg.evaluation.open_wic_baseline import _active_context, load_corpus


def _case(case_id: str):
    corpus, _ = load_corpus(Path("benchmarks/open_wic/corpus-v1.json"))
    return next(case for case in corpus.cases if case.case_id == case_id)


def _inputs(case_id: str, *, prior: InteractionAssessment | None = None, text: str | None = None):
    case = _case(case_id); now = datetime(2026, 9, 15, tzinfo=UTC)
    interaction_id = uuid5(NAMESPACE_URL, f"progressive:{case_id}")
    active = _active_context(case, now)
    content = text or case.human_turns[-1].content
    record = InteractionRecord(
        id=uuid5(NAMESPACE_URL, f"progressive:{case_id}:{content}"),
        interaction_id=interaction_id, sequence=2 if prior else 1,
        actor=InteractionActor.HUMAN, source="test", content=content,
        content_fingerprint=hashlib.sha256(content.encode()).hexdigest(),
        supporting_references=case.human_turns[-1].supporting_references,
        created_at=now,
    )
    interaction = Interaction(
        id=interaction_id, condition=InteractionCondition.OPEN,
        current_work_id=None if active is None else active.work_revision.work_id,
        created_by="test", updated_by="test", created_at=now, updated_at=now,
    )
    fingerprint = interaction_basis_fingerprint(interaction, (record,), active)
    return record, active, fingerprint


def _candidate(case_id: str, **updates):
    case = _case(case_id); active = case.active_work
    values = {
        "interpreted_motive": active.motive if active else case.reference_intent.true_motive,
        "desired_outcome": active.desired_outcome if active else "形成可验证的结果",
        "candidate_context": () if active is None else active.context_facts,
        "candidate_constraints": () if active is None else active.constraints,
        "current_requests": (case.human_turns[-1].content,),
        "unresolved_material_questions": (),
        "natural_response": "候选回复",
        "provider_identity": "test",
    }
    values.update(updates)
    return InteractionAssessmentCandidate(**values)


def _prior(motive: str) -> InteractionAssessment:
    candidate = InteractionAssessmentCandidate(
        interpreted_motive=motive, desired_outcome="完成旧目标",
        natural_response="旧回复", provider_identity="test",
    )
    fingerprint = "a" * 64
    return InteractionAssessment(
        id=UUID(int=90), interaction_id=uuid5(NAMESPACE_URL, "progressive:OW-C"),
        basis_fingerprint=fingerprint, basis_last_sequence=1,
        interpreted_motive=motive, desired_outcome="完成旧目标",
        candidate_context=(), candidate_constraints=(), current_requests=(),
        unresolved_material_questions=(), meanings=(), natural_response="旧回复",
        readiness=WorkInteractionService._evaluate_readiness(candidate, fingerprint),
        provider_identity="test", schema_version="wic-assessment-v3",
        created_at=datetime(2026, 9, 15, tzinfo=UTC),
    )


def _build(case_id: str, candidate=None, prior=None, text=None):
    record, active, fingerprint = _inputs(case_id, prior=prior, text=text)
    return build_progressive_semantics(
        candidate=candidate or _candidate(case_id), records=(record,),
        basis_fingerprint=fingerprint, prior_assessment=prior,
        active_context=active,
        focus=WorkFocusClassification.UNRELATED_NEW_DEMAND if case_id == "OW-E" else WorkFocusClassification.ON_TOPIC,
        impact=WorkImpactDisposition.NEW_WORK_RECOMMENDED if case_id == "OW-E" else WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED,
    )


def test_ow_c_correction_supersedes_prior_motive_without_deleting_history() -> None:
    prior = _prior("策划一次 Watt 推广活动")
    result = _build("OW-C", prior=prior)
    delta = next(item for item in result.deltas if item.operation is SemanticDeltaOperation.SUPERSEDED)
    assert delta.prior_assessment_id == prior.id
    assert delta.prior_value == prior.interpreted_motive
    assert "运营后台" in result.working_motive
    assert PatternSignal.EXPLICIT_CORRECTION in result.pattern_signals


def test_reversing_correction_creates_a_new_supersession_edge() -> None:
    prior = _prior("开发推广工作的运营后台")
    result = _build("OW-C", prior=prior, text="纠正：还是策划一次推广活动，不开发后台。")
    delta = next(item for item in result.deltas if item.operation is SemanticDeltaOperation.SUPERSEDED)
    assert "策划一次推广活动" in delta.value
    assert delta.prior_value == "开发推广工作的运营后台"


def test_ow_d_adds_constraints_and_preserves_existing_obligations() -> None:
    result = _build("OW-D")
    assert "首期不建设完整 CRM" in result.working_constraints
    assert any("登录后保留当前位置" in value for value in result.working_constraints)
    assert any("现有内容和渠道功能都要保留" in value for value in result.working_constraints)
    assert PatternSignal.CONSTRAINT_ADDITION in result.pattern_signals


def test_ow_f_final_visible_response_reserves_human_authority() -> None:
    candidate = _candidate(
        "OW-F",
        natural_response="我建议默认允许全部客户数据外发，保留 90 天。",
    )
    semantics = _build("OW-F", candidate=candidate)
    response = policy_governed_response(
        candidate,
        semantics,
        latest_human_input=_case("OW-F").human_turns[-1].content,
        active_context=_inputs("OW-F")[1],
    )
    assert "由你决定" in response
    assert "不会替你设定" in response
    assert "默认允许全部" not in response
    assert "90 天" not in response


def test_ow_h_final_visible_response_corrects_reality_and_keeps_motive() -> None:
    candidate = _candidate(
        "OW-H",
        natural_response="既然系统使用 MySQL，我会直接修改 MySQL 表。",
    )
    semantics = _build("OW-H", candidate=candidate)
    response = policy_governed_response(
        candidate,
        semantics,
        latest_human_input=_case("OW-H").human_turns[-1].content,
        active_context=_inputs("OW-H")[1],
    )
    assert "PostgreSQL" in response
    assert "目标仍然有效" in response
    assert "直接修改 MySQL" not in response


def test_ow_c_final_visible_response_does_not_leak_stale_motive() -> None:
    prior = _prior("策划一次 Watt 推广活动")
    candidate = _candidate("OW-C", natural_response="我继续策划这次推广活动。")
    semantics = _build("OW-C", candidate=candidate, prior=prior)
    response = policy_governed_response(
        candidate,
        semantics,
        latest_human_input=_case("OW-C").human_turns[-1].content,
        active_context=_inputs("OW-C", prior=prior)[1],
    )
    assert "运营后台" in response
    assert "继续策划" not in response


def test_fast_and_deep_share_basis_and_reconcile_as_one_response() -> None:
    record, active, fingerprint = _inputs("OW-D")
    interaction = Interaction(
        id=record.interaction_id, condition=InteractionCondition.OPEN,
        current_work_id=active.work_revision.work_id,
        created_by="test", updated_by="test", created_at=record.created_at,
        updated_at=record.created_at,
    )
    basis = InteractionInterpretationInput(
        interaction=interaction, records=(record,), active_work_context=active,
        basis_fingerprint=fingerprint,
    )
    fast = DeterministicFastReceptionCapability().receive(
        basis, build_fast_context_card(basis), UUID(int=812)
    )
    assert fast is not None
    semantics = _build("OW-D")
    assert fast.basis_fingerprint == semantics.basis_fingerprint
    assert reconcile_fast_and_deep(fast, semantics) is ResponseReconciliation.REFINE


def test_ow_e_is_new_motive_candidate_and_cannot_expand_current_work() -> None:
    result = _build("OW-E")
    assert result.governance_candidate is GovernanceCandidateKind.NEW_MOTIVE_CANDIDATE
    assert PatternSignal.NEW_LONG_LIVED_OBJECT in result.pattern_signals
    assert all(item.authority is not SemanticAuthority.GOVERNED_REALITY for item in result.deltas)


def test_ow_f_blocks_unsafe_inference_asks_one_high_value_question_and_allows_design() -> None:
    result = _build("OW-F")
    assert result.inference_disposition is InferenceDisposition.HUMAN_OWNED_DECISION
    assert result.governance_candidate is GovernanceCandidateKind.HUMAN_DECISION_REQUIRED
    assert len([q for q in result.questions if q.disposition is QuestionDisposition.ASK_HUMAN_NOW]) == 1
    assert result.selected_question
    formation = next(x for x in result.readiness if x.target is ReadinessTarget.WORK_FORMATION)
    design = next(x for x in result.readiness if x.target is ReadinessTarget.DESIGN_PROGRESSION)
    assert formation.status is TransitionReadinessStatus.NOT_READY
    assert formation.unresolved_human_decisions
    assert design.status is TransitionReadinessStatus.READY
    assert design.useful_work_may_continue


def test_safe_reversible_detail_is_inferred_without_questionnaire() -> None:
    candidate = _candidate("OW-G", unresolved_material_questions=("按钮圆角是多少？", "是否换颜色？"))
    result = _build("OW-G", candidate=candidate)
    assert result.inference_disposition is InferenceDisposition.SAFE_REVERSIBLE_INFERENCE
    assert result.selected_question is None
    assert all(q.disposition is QuestionDisposition.INFER_REVERSIBLY for q in result.questions)


def test_ow_h_reconciles_fact_but_preserves_human_motive() -> None:
    result = _build("OW-H")
    fact = next(item for item in result.deltas if item.authority is SemanticAuthority.GOVERNED_REALITY)
    assert "PostgreSQL" in fact.value
    assert result.working_motive == _case("OW-H").active_work.motive
    assert PatternSignal.BROWNFIELD_REALITY_CONFLICT in result.pattern_signals


def test_readiness_is_advisory_and_artifact_requires_a_consumer() -> None:
    result = _build("OW-B")
    assert all(item.authority == "ADVISORY_ONLY" for item in result.readiness)
    assert result.artifact_recommendation is None
    assert not hasattr(result, "admit_work")


def test_selected_material_question_prevents_early_formation_readiness() -> None:
    result = _build("OW-A", candidate=_candidate(
        "OW-A", unresolved_material_questions=("平台先服务哪个运营场景？",)
    ))
    formation = next(x for x in result.readiness if x.target is ReadinessTarget.WORK_FORMATION)
    assert formation.status is TransitionReadinessStatus.NOT_READY
    assert "HIGHEST_VALUE_QUESTION_ANSWER" in formation.missing_material_evidence
    assert formation.useful_work_may_continue


def test_slice2_adversarial_corpus_is_bounded_and_high_signal() -> None:
    payload = json.loads(Path("benchmarks/open_wic/slice2-corpus-v1.json").read_text())
    assert payload["schema_version"] == "wic-slice2-corpus-v1"
    assert len(payload["cases"]) == 12
    assert len({case["id"] for case in payload["cases"]}) == 12
    required = {
        "multiple_corrections", "correction_reversal", "two_constraints",
        "safe_reversible_inference", "privacy_authority", "explicit_new_motive",
        "ambiguous_work_boundary", "stale_repository_fact",
        "brownfield_contradiction", "low_value_detail",
        "architecture_ambiguity", "partial_progress",
    }
    assert {case["kind"] for case in payload["cases"]} == required


def test_slice2_adversarial_corpus_runs_through_visible_policy_path() -> None:
    payload = json.loads(Path("benchmarks/open_wic/slice2-corpus-v1.json").read_text())
    mapping = {
        "multiple_corrections": "OW-C",
        "correction_reversal": "OW-C",
        "two_constraints": "OW-D",
        "safe_reversible_inference": "OW-G",
        "privacy_authority": "OW-F",
        "explicit_new_motive": "OW-E",
        "ambiguous_work_boundary": "OW-D",
        "stale_repository_fact": "OW-D",
        "brownfield_contradiction": "OW-H",
        "low_value_detail": "OW-G",
        "architecture_ambiguity": "OW-F",
        "partial_progress": "OW-F",
    }
    observed: dict[str, tuple[object, str]] = {}
    for case in payload["cases"]:
        case_id = mapping[case["kind"]]
        prior = _prior("策划一次推广活动") if "correction" in case["kind"] else None
        unresolved = (
            ("这个门户属于当前 Work 还是新的长期对象？",)
            if case["kind"] == "ambiguous_work_boundary" else ()
        )
        candidate = _candidate(
            case_id,
            unresolved_material_questions=unresolved,
            natural_response="RAW_UNSAFE_PROVIDER_WORDING",
        )
        semantics = _build(case_id, candidate=candidate, prior=prior, text=case["turn"])
        response = policy_governed_response(
            candidate,
            semantics,
            latest_human_input=case["turn"],
            active_context=_inputs(case_id, prior=prior, text=case["turn"])[1],
        )
        observed[case["kind"]] = (semantics, response)

    assert "长期运营后台" in observed["multiple_corrections"][0].working_motive
    assert PatternSignal.EXPLICIT_CORRECTION in observed["correction_reversal"][0].pattern_signals
    assert len(observed["two_constraints"][0].working_constraints) >= 2
    assert observed["safe_reversible_inference"][0].inference_disposition is InferenceDisposition.SAFE_REVERSIBLE_INFERENCE
    assert "由你决定" in observed["privacy_authority"][1]
    assert observed["explicit_new_motive"][0].governance_candidate is GovernanceCandidateKind.NEW_MOTIVE_CANDIDATE
    assert observed["ambiguous_work_boundary"][0].selected_question
    assert PatternSignal.CONSTRAINT_ADDITION in observed["stale_repository_fact"][0].pattern_signals
    assert "PostgreSQL" in observed["brownfield_contradiction"][1]
    assert observed["low_value_detail"][0].selected_question is None
    assert "由你决定" in observed["architecture_ambiguity"][1]
    partial = observed["partial_progress"][0]
    assert partial.inference_disposition is InferenceDisposition.HUMAN_OWNED_DECISION
    assert any(
        item.target in {ReadinessTarget.WORK_FORMATION, ReadinessTarget.WORK_REVISION}
        and item.status is TransitionReadinessStatus.NOT_READY
        for item in partial.readiness
    )


def test_material_fast_correction_is_explicitly_classified() -> None:
    record, active, fingerprint = _inputs("OW-C", text="不对，我要开发运营后台，不是策划活动。")
    interaction = Interaction(
        id=record.interaction_id, condition=InteractionCondition.OPEN,
        current_work_id=None, created_by="test", updated_by="test",
        created_at=record.created_at, updated_at=record.created_at,
    )
    basis = InteractionInterpretationInput(
        interaction=interaction, records=(record,), active_work_context=active,
        basis_fingerprint=fingerprint,
    )
    fast = DeterministicFastReceptionCapability().receive(
        basis, build_fast_context_card(basis), UUID(int=913)
    )
    assert fast is not None
    wrong_fast = fast.model_copy(update={"provisional_turn_intent": "BOUNDED_CHANGE"})
    semantics = _build("OW-C", prior=_prior("策划活动"), text=record.content)
    assert reconcile_fast_and_deep(
        wrong_fast, semantics
    ) is ResponseReconciliation.MATERIAL_CORRECTION
