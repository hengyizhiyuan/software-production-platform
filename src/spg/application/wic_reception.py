"""Shadow-only Fast Semantic Reception with deterministic authority policy."""

from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
import re
from threading import RLock
from time import monotonic
from typing import Protocol
from uuid import UUID

from spg.application.wic_context import build_fast_context_card, fast_context_is_fresh
from spg.domain.interaction import InteractionInterpretationInput
from spg.domain.wic_reception import (
    FastContextCard, FastReceptionCandidate, FastReceptionObservation,
    FastReceptionVisibility,
)


class FastReceptionCapability(Protocol):
    def receive(self, basis: InteractionInterpretationInput, card: FastContextCard, turn_id: UUID) -> FastReceptionCandidate | None: ...


_AUTHORITY = re.compile(r"(客户数据|个人信息|隐私).*(权限|保留期|留存|外部模型)|(删除|销毁|付费|预算)")
_CORRECTION = re.compile(r"(?:不对|不是|纠正|改口)[，,:：\s]*(.+)")
_CONSTRAINT = re.compile(r"(?:新增约束|约束是|必须|不得|不要)[：,:，\s]*(.+)")
_NARROW_CHANGE = re.compile(r"(把.+?(?:改成|改为).+?)(?:[。；;]|$)")
_NEW_OBJECT = re.compile(r"(?:另外|还有).*(我想|我要).*(开发|做|创建)(.+?(?:系统|平台|网站|应用))")


def neutral_fast_provisional_message(human_input: str) -> str:
    """Acknowledge reception without asserting ungoverned meaning."""

    if re.search(r"[\u4e00-\u9fff]", human_input):
        return "收到，我正在结合当前上下文核对这条输入。"
    return "Received. I’m checking this input against the current context."


def _correction_target(value: str) -> str:
    reversed_object = re.search(r"不是.+?[，,]是(.+)", value)
    if reversed_object:
        return reversed_object.group(1).strip("。 ")
    positive = re.split(r"[,，]不是", value, maxsplit=1)[0].strip()
    return positive or value.strip("。 ")


def apply_fast_grounding_policy(candidate: FastReceptionCandidate, basis: InteractionInterpretationInput, card: FastContextCard) -> FastReceptionCandidate:
    latest = basis.records[-1]
    blocked = False
    if not fast_context_is_fresh(card, basis):
        blocked = True
    if f"INTERACTION_RECORD:{latest.id}" not in candidate.grounding_references:
        blocked = True
    haystack = " ".join((latest.content, card.motive or "", card.desired_outcome or "", *card.material_facts, *card.material_constraints))
    if candidate.captured_object and candidate.captured_object not in haystack:
        blocked = True
    if any(value not in latest.content and value not in haystack for value in candidate.captured_explicit_constraints):
        blocked = True
    if candidate.confidence < 0.65:
        blocked = True
    sentence = candidate.meaningful_sentence
    if _AUTHORITY.search(latest.content):
        protected = bool(re.search(r"(需要|应由|必须由).{0,8}(你|Human).{0,8}(决定|确认)|不会.{0,8}(替你|擅自).{0,8}(决定|设定)", sentence))
        if not protected:
            blocked = True
    if sentence.strip() in {"收到。", "明白了。", "好的。", "我来看看。"}:
        blocked = True
    disposition = FastReceptionVisibility.BLOCKED if blocked else FastReceptionVisibility.SAFE_TO_EMIT
    return candidate.model_copy(update={
        "policy_disposition": disposition,
        # Fast semantic fields remain available for later reconciliation, but text
        # visible before Deep WIC governance may only report reception/progress.
        "meaningful_sentence": neutral_fast_provisional_message(latest.content),
    })


class DeterministicFastReceptionCapability:
    """Extract only explicit meanings; absence is a valid result."""

    def receive(self, basis: InteractionInterpretationInput, card: FastContextCard, turn_id: UUID) -> FastReceptionCandidate | None:
        started_at = datetime.now(UTC); started = monotonic()
        latest = basis.records[-1]; text = latest.content.strip()
        intent = None; captured = None; constraints: tuple[str, ...] = (); correction = None; decision = None; sentence = None
        if _AUTHORITY.search(text):
            intent = "HUMAN_OWNED_DECISION"
            decision = "权限、保留期或其他高影响条件"
            captured = "客户数据" if "客户数据" in text else None
            sentence = "这涉及客户数据外发；权限和保留期需要由你决定，我不会先替你设定。" if "客户数据" in text else "这涉及需要由你决定的高影响条件，我不会先替你设定。"
        elif match := _CORRECTION.search(text):
            intent = "CORRECTION"; correction = match.group(1).strip("。 ")
            captured = _correction_target(correction)
            sentence = f"明白，你是在纠正对象：{captured}。"
        elif match := _CONSTRAINT.search(text):
            intent = "CONSTRAINT_ADDITION"; value = match.group(1).strip("。 "); constraints = (value,)
            sentence = f"我已捕捉到新增约束：{value}。"
        elif match := _NARROW_CHANGE.search(text):
            intent = "BOUNDED_CHANGE"; captured = match.group(1).strip()
            sentence = "这会作为现有对象的局部变更继续评估；当前范围不会被默认扩大。"
        elif match := _NEW_OBJECT.search(text):
            intent = "POSSIBLE_NEW_OBJECT"; captured = match.group(3).strip("。 ")
            sentence = f"你提出了另一个对象：{captured}；是否形成新 Work 仍由你决定。"
        elif text.endswith(("?", "？")):
            # Repeating a question is not a meaningful fast response. Let the
            # governed answer become the first visible text instead.
            return None
        if sentence is None:
            return None
        ready = (monotonic() - started) * 1000
        candidate = FastReceptionCandidate(
            interaction_id=basis.interaction.id, turn_id=turn_id,
            source_record_id=latest.id, basis_fingerprint=basis.basis_fingerprint,
            fast_context_fingerprint=card.source_fingerprint,
            active_work_id=card.active_work_id,
            active_work_revision_id=card.active_work_revision_id,
            provisional_turn_intent=intent, captured_object=captured,
            current_focus=card.current_focus,
            captured_explicit_constraints=constraints,
            detected_correction=correction,
            detected_human_owned_decision=decision,
            confidence=0.98,
            grounding_references=(f"INTERACTION_RECORD:{latest.id}", *card.source_references),
            meaningful_sentence=sentence,
            provider="watt-local", model=None, profile="deterministic-explicit-v1",
            started_at=started_at, first_delta_ms=ready, candidate_ready_ms=ready,
            visibility_disposition=FastReceptionVisibility.SHADOW,
            policy_disposition=FastReceptionVisibility.SAFE_TO_EMIT,
        )
        return apply_fast_grounding_policy(candidate, basis, card)


class ShadowFastReceptionRuntime:
    """Runs independently; exposes observations but no mutation service."""

    def __init__(self, capability: FastReceptionCapability, *, timeout_seconds: float = 2.0) -> None:
        self.capability = capability; self.timeout_seconds = timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="watt-fast-reception")
        self._observations: OrderedDict[UUID, FastReceptionObservation] = OrderedDict()
        self._lock = RLock()

    def start(self, basis: InteractionInterpretationInput, turn_id: UUID) -> Future[FastReceptionObservation]:
        return self._executor.submit(self._run, basis, turn_id)

    def _run(self, basis: InteractionInterpretationInput, turn_id: UUID) -> FastReceptionObservation:
        started = datetime.now(UTC); started_clock = monotonic()
        try:
            card = build_fast_context_card(basis)
            candidate = self.capability.receive(basis, card, turn_id)
            observation = FastReceptionObservation(
                turn_id=turn_id, correlation_id=turn_id, started_at=started,
                terminal_at=datetime.now(UTC),
                status="NO_EMISSION" if candidate is None or candidate.policy_disposition is FastReceptionVisibility.BLOCKED else "CANDIDATE",
                stage="grounding_policy_completed", candidate=candidate,
                provider=None if candidate is None else candidate.provider,
                model=None if candidate is None else candidate.model,
                profile=None if candidate is None else candidate.profile,
                first_delta_ms=None if candidate is None else candidate.first_delta_ms,
                terminal_ms=(monotonic() - started_clock) * 1000,
                input_tokens=None if candidate is None else candidate.input_tokens,
                output_tokens=None if candidate is None else candidate.output_tokens,
                total_tokens=None if candidate is None else candidate.total_tokens,
            )
        except Exception as error:
            provenance = getattr(self.capability, "last_failure_provenance", {}) or {}
            observation = FastReceptionObservation(
                turn_id=turn_id, correlation_id=turn_id, started_at=started,
                terminal_at=datetime.now(UTC), status="FAILED", stage="fast_reception_failed",
                failure_type=type(error).__name__, failure_message=str(error), retry_count=0,
                terminal_ms=(monotonic() - started_clock) * 1000,
                **provenance,
            )
        with self._lock:
            self._observations[turn_id] = observation
            while len(self._observations) > 128: self._observations.popitem(last=False)
        return observation

    def observation(self, turn_id: UUID) -> FastReceptionObservation | None:
        with self._lock: return self._observations.get(turn_id)

    def close(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=False)
