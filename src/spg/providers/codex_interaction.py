"""Read-only Codex adapter for advisory pre-Work Interaction interpretation."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
import json
from queue import Empty, Queue
from threading import Thread
from typing import Any

from openai_codex import ApprovalMode, Codex, Sandbox
from pydantic import BaseModel, ConfigDict

from spg.application.guided_design import (
    design_schema_by_identity,
    match_design_schema_text,
)
from spg.domain.interaction import (
    InteractionAssessmentCandidate,
    InteractionInterpretationInput,
    InterpretationMeaning,
    InteractionInvariantViolation,
    WorkFocusClassification,
    WorkImpactDisposition,
)
from spg.providers.codex_sdk_executor import INTERRUPT_GRACE_SECONDS, _enum_value
from spg.providers.codex_semantic import _provider_strict_output_schema


CodexFactory = Callable[[], AbstractContextManager[Any]]


class _InteractionProviderMeaning(InterpretationMeaning):
    """Strict wire shape over unchanged domain defaults."""

    clarification_required: bool


class _InteractionProviderPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    # Keep Human-facing text first so the structured response can be projected
    # incrementally while the remaining advisory fields are still being formed.
    natural_response: str
    interpreted_motive: str | None
    desired_outcome: str | None
    candidate_context: tuple[str, ...]
    candidate_constraints: tuple[str, ...]
    current_requests: tuple[str, ...]
    unresolved_material_questions: tuple[str, ...]
    meanings: tuple[_InteractionProviderMeaning, ...]
    focus_classification: WorkFocusClassification | None
    impact_disposition: WorkImpactDisposition | None
    supporting_references: tuple[str, ...]


@dataclass(frozen=True)
class _StreamingTurnResult:
    status: object
    error: object | None
    final_response: str


@dataclass(frozen=True)
class _StreamingTerminal:
    result: _StreamingTurnResult | None = None
    timed_out: bool = False


class _JsonStringFieldStream:
    """Extract one JSON string field without exposing its structured envelope."""

    def __init__(self, field: str) -> None:
        self._marker = json.dumps(field)
        self._buffer = ""
        self._emitted = ""

    def feed(self, delta: str) -> str:
        self._buffer += delta
        marker_at = self._buffer.find(self._marker)
        if marker_at < 0:
            return ""
        value_at = marker_at + len(self._marker)
        while value_at < len(self._buffer) and self._buffer[value_at].isspace():
            value_at += 1
        if value_at >= len(self._buffer) or self._buffer[value_at] != ":":
            return ""
        value_at += 1
        while value_at < len(self._buffer) and self._buffer[value_at].isspace():
            value_at += 1
        if value_at >= len(self._buffer) or self._buffer[value_at] != '"':
            return ""
        decoded = self._decode_prefix(self._buffer[value_at + 1 :])
        emitted = decoded[len(self._emitted) :]
        self._emitted = decoded
        return emitted

    @staticmethod
    def _decode_prefix(value: str) -> str:
        decoded: list[str] = []
        index = 0
        escapes = {
            '"': '"',
            "\\": "\\",
            "/": "/",
            "b": "\b",
            "f": "\f",
            "n": "\n",
            "r": "\r",
            "t": "\t",
        }
        while index < len(value):
            character = value[index]
            if character == '"':
                break
            if character != "\\":
                decoded.append(character)
                index += 1
                continue
            if index + 1 >= len(value):
                break
            escaped = value[index + 1]
            if escaped == "u":
                if index + 6 > len(value):
                    break
                digits = value[index + 2 : index + 6]
                try:
                    codepoint = int(digits, 16)
                except ValueError:
                    break
                if 0xD800 <= codepoint <= 0xDBFF:
                    if (
                        index + 12 > len(value)
                        or value[index + 6 : index + 8] != "\\u"
                    ):
                        break
                    low_digits = value[index + 8 : index + 12]
                    try:
                        low = int(low_digits, 16)
                    except ValueError:
                        break
                    if not 0xDC00 <= low <= 0xDFFF:
                        break
                    decoded.append(
                        chr(
                            0x10000
                            + ((codepoint - 0xD800) << 10)
                            + (low - 0xDC00)
                        )
                    )
                    index += 12
                    continue
                decoded.append(chr(codepoint))
                index += 6
                continue
            replacement = escapes.get(escaped)
            if replacement is None:
                break
            decoded.append(replacement)
            index += 2
        return "".join(decoded)


class CodexSdkWorkInteractionCapability:
    """Use one ephemeral Turn per exact persisted basis; no hidden session is truth."""

    def __init__(
        self,
        *,
        repository_location: str,
        codex_factory: CodexFactory | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.repository_location = repository_location
        self.codex_factory = codex_factory or Codex
        self.model = model
        self.timeout_seconds = timeout_seconds

    def interpret(
        self, basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        return self._interpret(basis, on_response_delta=None)

    def interpret_stream(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_response_delta: Callable[[str], None],
    ) -> InteractionAssessmentCandidate:
        """Interpret while projecting only the Human-facing response text."""

        return self._interpret(basis, on_response_delta=on_response_delta)

    def _interpret(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_response_delta: Callable[[str], None] | None,
    ) -> InteractionAssessmentCandidate:
        with self.codex_factory() as codex:
            thread = codex.thread_start(
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                ephemeral=True,
                model=self.model,
                sandbox=Sandbox.read_only,
            )
            turn = thread.turn(
                self._instruction(basis),
                approval_mode=ApprovalMode.deny_all,
                cwd=self.repository_location,
                model=self.model,
                output_schema=self.output_schema(),
                sandbox=Sandbox.read_only,
            )
            terminal = self._wait_for_streaming_terminal(
                turn,
                timeout_seconds=self.timeout_seconds,
                on_response_delta=on_response_delta,
            )
        if terminal.timed_out or terminal.result is None:
            raise InteractionInvariantViolation(
                "Watt Native interpretation Provider did not complete in its bounded Turn"
            )
        result = terminal.result
        if _enum_value(result.status) != "completed" or result.error is not None:
            raise InteractionInvariantViolation(
                "Watt Native interpretation Provider did not return a completed result"
            )
        try:
            payload = _InteractionProviderPayload.model_validate_json(
                result.final_response.strip()
            )
        except (ValueError, TypeError) as error:
            raise InteractionInvariantViolation(
                "Watt Native interpretation Provider returned an invalid structured result"
            ) from error
        return InteractionAssessmentCandidate(
            **payload.model_dump(),
            provider_identity=f"codex-sdk:thread:{thread.id}:turn:{turn.id}",
            model_identity=self.model,
        )

    @staticmethod
    def _wait_for_streaming_terminal(
        turn: Any,
        *,
        timeout_seconds: float | None,
        on_response_delta: Callable[[str], None] | None,
    ) -> _StreamingTerminal:
        completed: Queue[tuple[str, Any]] = Queue(maxsize=1)

        def consume() -> None:
            raw_response: list[str] = []
            final_item_text: str | None = None
            completed_turn: object | None = None
            extractor = _JsonStringFieldStream("natural_response")
            try:
                for notification in turn.stream():
                    if notification.method == "item/agentMessage/delta":
                        delta = str(notification.payload.delta)
                        raw_response.append(delta)
                        if on_response_delta is not None:
                            response_delta = extractor.feed(delta)
                            if response_delta:
                                on_response_delta(response_delta)
                    elif notification.method == "item/completed":
                        item = notification.payload.item
                        if getattr(item, "type", None) == "agentMessage":
                            final_item_text = str(item.text)
                    elif notification.method == "turn/completed":
                        completed_turn = notification.payload.turn
                if completed_turn is None:
                    raise RuntimeError("turn completed event not received")
                completed.put(
                    (
                        "result",
                        _StreamingTurnResult(
                            status=completed_turn.status,
                            error=completed_turn.error,
                            final_response=final_item_text or "".join(raw_response),
                        ),
                    )
                )
            except Exception as error:
                completed.put(("error", error))

        worker = Thread(
            target=consume,
            name="spg-wic-codex-stream",
            daemon=True,
        )
        worker.start()
        try:
            kind, value = completed.get(timeout=timeout_seconds)
        except Empty:
            try:
                turn.interrupt()
            except Exception:
                pass
            try:
                completed.get(timeout=INTERRUPT_GRACE_SECONDS)
            except Empty:
                pass
            return _StreamingTerminal(timed_out=True)
        if kind == "error":
            raise value
        return _StreamingTerminal(result=value)

    @staticmethod
    def output_schema() -> dict[str, Any]:
        return _provider_strict_output_schema(
            _InteractionProviderPayload.model_json_schema()
        )

    @staticmethod
    def _instruction(basis: InteractionInterpretationInput) -> str:
        payload = basis.model_dump(mode="json")
        schema = (
            design_schema_by_identity(
                basis.interaction.selected_design_schema_identity,
                basis.interaction.selected_design_schema_version,
            )
            if basis.interaction.selected_design_schema_identity is not None
            else match_design_schema_text(
                "\n".join(record.content for record in basis.records)
            )[0]
        )
        design_path = [
            {
                "stage": issue.title,
                "objective": issue.objective,
                "why_it_matters": issue.why_it_matters,
            }
            for issue in schema.issues
        ]
        return (
            "Interpret one Human–Watt interaction from the exact persisted basis "
            "supplied below. This is advisory, read-only interpretation. Do not "
            "create or imply Work admission, governance, production authority, a Plan, "
            "Run, PWU, repository change, or execution. Do not use tools or hidden "
            "conversation memory. Distinguish casual/exploratory/background input from "
            "an actionable Motive. Idle, vague, or materially incomplete interaction "
            "must retain unresolved_material_questions and must not fabricate motive or "
            "outcome. A sufficiently clear long-lived Motive needs a concrete desired "
            "outcome but does not need an exact production target. Preserve explicit "
            "constraints and requests. When active_work_context exists, preserve its "
            "Motive/outcome/context/constraints/requests unless the latest Human input "
            "actually proposes a change. Classify how that input relates to current Work "
            "focus and its production impact. Questions, bounded exploration, material "
            "branches, and unrelated demands must not silently rewrite current Work. "
            "When satisfaction_state is CURRENTLY_SATISFIED, distinguish a same-Motive "
            "continuation from a materially new demand. Same-Motive continuation may "
            "propose a governed revision and must treat the prior completion as historical "
            "truth; materially new demand must use NEW_WORK_RECOMMENDED and must not "
            "inherit the completed Work's authority. "
            "Never inject the input into an active production cycle. supporting_references "
            "may only repeat typed references present in Interaction records; do not copy "
            "external findings. Every meaning must use one allowed kind and cite "
            "only source_record_ids present in the supplied basis. Act as an active "
            "product/system design partner, not a requirements questionnaire. In "
            "natural_response: acknowledge and use facts the Human already supplied; "
            "briefly explain the relevant design path and current stage; choose the "
            "highest-value current focus and explain why it comes next; proactively "
            "offer a concrete framing, direction, alternatives, trade-offs, or decision "
            "order when the evidence supports them; and ask at most one highest-impact "
            "unresolved question. Never ask the Human to repeat information already in "
            "the basis. Explain progress without claiming that advisory interpretation "
            "is governed Reality. Respond in the Human's language. natural_response is "
            "Human-facing and advisory, never Authority. "
            "Return JSON only matching the supplied schema, including every key and [] "
            "for empty arrays.\n\nCandidate Design Schema and ordered path:\n"
            + json.dumps(
                {
                    "identity": schema.identity,
                    "version": schema.version,
                    "title": schema.title,
                    "applicability": schema.applicability,
                    "path": design_path,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n\nExact persisted Interaction basis:\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True)
        )
