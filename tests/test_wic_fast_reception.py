from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import time
from uuid import UUID

from spg.application.interaction import interaction_basis_fingerprint
from spg.application.wic_context import build_fast_context_card, fast_context_is_fresh
from spg.application.wic_reception import (
    DeterministicFastReceptionCapability,
    ShadowFastReceptionRuntime,
    apply_fast_grounding_policy,
)
from spg.domain.interaction import (
    Interaction, InteractionActor, InteractionCondition,
    InteractionInterpretationInput, InteractionRecord,
)
from spg.domain.wic_reception import FastReceptionVisibility
from spg.evaluation.open_wic_baseline import _active_context, load_corpus


def _basis(case_id: str, text: str | None = None) -> InteractionInterpretationInput:
    corpus, _ = load_corpus(Path("benchmarks/open_wic/corpus-v1.json"))
    case = next(case for case in corpus.cases if case.case_id == case_id)
    now = datetime(2026, 9, 15, tzinfo=UTC)
    interaction_id = UUID(int=100 + ord(case_id[-1]))
    active = _active_context(case, now)
    interaction = Interaction(
        id=interaction_id, condition=InteractionCondition.OPEN,
        current_work_id=None if active is None else active.work_revision.work_id,
        created_by="test", updated_by="test", created_at=now, updated_at=now,
    )
    content = text or case.human_turns[-1].content
    record = InteractionRecord(
        id=UUID(int=200 + ord(case_id[-1])), interaction_id=interaction_id,
        sequence=1, actor=InteractionActor.HUMAN, source="test", content=content,
        content_fingerprint=hashlib.sha256(content.encode()).hexdigest(),
        supporting_references=case.human_turns[-1].supporting_references,
        created_at=now,
    )
    fingerprint = interaction_basis_fingerprint(interaction, (record,), active)
    return InteractionInterpretationInput(
        interaction=interaction, records=(record,), active_work_context=active,
        basis_fingerprint=fingerprint,
    )


def test_fast_context_is_small_deterministic_and_preserves_active_references() -> None:
    basis = _basis("OW-H")
    first = build_fast_context_card(basis)
    second = build_fast_context_card(basis)

    assert first.source_fingerprint == second.source_fingerprint
    assert first.active_work_revision_id == basis.active_work_context.work_revision.id
    assert first.source_references == basis.active_work_context.relevant_reality_references
    assert first.serialized_bytes < 4096
    assert not hasattr(first, "admit_work")


def test_pre_work_card_and_stale_sequence_are_distinguished() -> None:
    basis = _basis("OW-A")
    card = build_fast_context_card(basis)
    assert card.condition == "PRE_WORK"
    assert fast_context_is_fresh(card, basis)
    assert not fast_context_is_fresh(card.model_copy(update={"interaction_sequence": 2}), basis)


def test_deterministic_correction_and_constraint_are_grounded_shadow_candidates() -> None:
    capability = DeterministicFastReceptionCapability()
    correction = _basis("OW-C")
    result = capability.receive(correction, build_fast_context_card(correction), UUID(int=1))
    assert result.detected_correction
    assert result.policy_disposition is FastReceptionVisibility.SAFE_TO_EMIT
    assert result.visibility_disposition is FastReceptionVisibility.SHADOW
    assert result.authority == "PROVISIONAL_READ_ONLY"
    assert result.meaningful_sentence == "收到，我正在结合当前上下文核对这条输入。"

    constraint = _basis("OW-D")
    result = capability.receive(constraint, build_fast_context_card(constraint), UUID(int=2))
    assert result.captured_explicit_constraints
    assert result.policy_disposition is FastReceptionVisibility.SAFE_TO_EMIT


def test_ow_f_keeps_privacy_and_retention_with_human_authority() -> None:
    basis = _basis("OW-F")
    result = DeterministicFastReceptionCapability().receive(
        basis, build_fast_context_card(basis), UUID(int=3)
    )
    assert result.detected_human_owned_decision
    assert result.meaningful_sentence == "收到，我正在结合当前上下文核对这条输入。"
    assert result.policy_disposition is FastReceptionVisibility.SAFE_TO_EMIT


def test_policy_blocks_stale_low_confidence_and_ungrounded_object() -> None:
    basis = _basis("OW-G")
    card = build_fast_context_card(basis)
    candidate = DeterministicFastReceptionCapability().receive(basis, card, UUID(int=4))
    assert candidate is not None
    assert apply_fast_grounding_policy(
        candidate.model_copy(update={"confidence": 0.2}), basis, card
    ).policy_disposition is FastReceptionVisibility.BLOCKED
    assert apply_fast_grounding_policy(
        candidate.model_copy(update={"captured_object": "不存在的财务系统"}), basis, card
    ).policy_disposition is FastReceptionVisibility.BLOCKED
    stale = card.model_copy(update={"source_fingerprint": "0" * 64})
    assert apply_fast_grounding_policy(candidate, basis, stale).policy_disposition is FastReceptionVisibility.BLOCKED


def test_broad_motive_waits_for_context_sensitive_model_response() -> None:
    basis = _basis("OW-A")
    assert DeterministicFastReceptionCapability().receive(
        basis, build_fast_context_card(basis), UUID(int=5)
    ) is None


def test_direct_question_is_not_repeated_as_a_fast_response() -> None:
    basis = _basis("OW-A", "企业官网一般都需要哪些页面？")
    assert DeterministicFastReceptionCapability().receive(
        basis, build_fast_context_card(basis), UUID(int=51)
    ) is None


def test_bounded_change_fast_receipt_preserves_scope_without_echoing_request() -> None:
    basis = _basis("OW-G")
    result = DeterministicFastReceptionCapability().receive(
        basis, build_fast_context_card(basis), UUID(int=54)
    )
    assert result is not None
    assert result.provisional_turn_intent == "BOUNDED_CHANGE"
    assert "把按钮文案改成" not in result.meaningful_sentence
    assert result.meaningful_sentence == "收到，我正在结合当前上下文核对这条输入。"


def test_negative_instruction_fast_text_never_asserts_reversed_meaning() -> None:
    basis = _basis("OW-A", "不要开始执行，我只是想先确认方案。")
    result = DeterministicFastReceptionCapability().receive(
        basis, build_fast_context_card(basis), UUID(int=55)
    )
    assert result is not None
    assert result.provisional_turn_intent == "CONSTRAINT_ADDITION"
    assert "开始执行" not in result.meaningful_sentence
    assert result.meaningful_sentence == "收到，我正在结合当前上下文核对这条输入。"


def test_domain_context_waits_for_context_sensitive_model_response() -> None:
    basis = _basis("OW-A", "这是一家为制造企业提供节能改造服务的公司。")
    assert DeterministicFastReceptionCapability().receive(
        basis, build_fast_context_card(basis), UUID(int=52)
    ) is None


def test_human_uncertainty_waits_for_model_contribution() -> None:
    basis = _basis("OW-A", "我其实也不知道该做成什么样。")
    assert DeterministicFastReceptionCapability().receive(
        basis, build_fast_context_card(basis), UUID(int=53)
    ) is None


def test_shadow_failure_is_observed_without_retry_or_exception() -> None:
    class Broken:
        calls = 0
        def receive(self, *_args):
            self.calls += 1
            raise RuntimeError("fast failed")

    broken = Broken(); runtime = ShadowFastReceptionRuntime(broken)
    observation = runtime.start(_basis("OW-A"), UUID(int=6)).result(timeout=1)
    runtime.close()
    assert observation.status == "FAILED"
    assert observation.retry_count == 0
    assert broken.calls == 1


def test_deep_work_can_start_without_waiting_for_slow_fast_lane() -> None:
    class Slow:
        def receive(self, *_args):
            time.sleep(0.2)
            return None

    runtime = ShadowFastReceptionRuntime(Slow())
    future = runtime.start(_basis("OW-A"), UUID(int=7))
    deep_started = time.monotonic()
    deep_result = "deep-started"
    elapsed = time.monotonic() - deep_started
    assert deep_result == "deep-started"
    assert elapsed < 0.05
    assert not future.done()
    assert future.result(timeout=1).status == "NO_EMISSION"
    runtime.close()


def test_frozen_open_wic_artifacts_are_byte_unchanged() -> None:
    expected = {
        "benchmarks/open_wic/corpus-v1.json": "4a571b1c651483c4ee003f535a36134ccca57cbab20572d1d376ff9225e94247",
        "docs/evidence/open-wic-baseline-runs/2026-09-15-deepseek-flash-low.json": "f6c7e9c30239b0bd860fcc8be76acc0083a2ed11f24e9d357948e3c4061602d0",
    }
    for name, digest in expected.items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
