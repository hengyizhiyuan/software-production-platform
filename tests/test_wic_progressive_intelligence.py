from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from pathlib import Path
import json
from uuid import NAMESPACE_URL, UUID, uuid5

from spg.application.interaction import WorkInteractionService, interaction_basis_fingerprint
from spg.application.wic_intelligence import build_progressive_semantics
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
