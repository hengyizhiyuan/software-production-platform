"""Read-only Codex adapter for advisory pre-Work Interaction interpretation."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
import json
from typing import Any

from openai_codex import ApprovalMode, Codex, Sandbox
from pydantic import BaseModel, ConfigDict

from spg.domain.interaction import (
    InteractionAssessmentCandidate,
    InteractionInterpretationInput,
    InterpretationMeaning,
    InteractionInvariantViolation,
    WorkFocusClassification,
    WorkImpactDisposition,
)
from spg.providers.codex_sdk_executor import _enum_value, _wait_for_terminal
from spg.providers.codex_semantic import _provider_strict_output_schema


CodexFactory = Callable[[], AbstractContextManager[Any]]


class _InteractionProviderMeaning(InterpretationMeaning):
    """Strict wire shape over unchanged domain defaults."""

    clarification_required: bool


class _InteractionProviderPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

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
    natural_response: str


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
            terminal = _wait_for_terminal(turn, self.timeout_seconds)
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
    def output_schema() -> dict[str, Any]:
        return _provider_strict_output_schema(
            _InteractionProviderPayload.model_json_schema()
        )

    @staticmethod
    def _instruction(basis: InteractionInterpretationInput) -> str:
        payload = basis.model_dump(mode="json")
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
            "Never inject the input into an active production cycle. supporting_references "
            "may only repeat typed references present in Interaction records; do not copy "
            "external findings. Every meaning must use one allowed kind and cite "
            "only source_record_ids present in the supplied basis. natural_response is "
            "concise Human-facing continuation or clarification; it is not authoritative. "
            "Return JSON only matching the supplied schema, including every key and [] "
            "for empty arrays.\n\nExact persisted Interaction basis:\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True)
        )
