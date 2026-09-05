"""Read-only Codex adapter for governed semantic Steering Step execution."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
import json
from typing import Any

from openai_codex import ApprovalMode, Codex, Sandbox
from pydantic import BaseModel, ConfigDict

from spg.domain.steering import (
    SemanticProductionProposal,
    SemanticResultKind,
    SemanticStepInput,
    SemanticStepResultCandidate,
    SteeringAuthorityAssessment,
    SteeringInvariantViolation,
    SteeringStepType,
)
from spg.providers.codex_sdk_executor import _enum_value, _wait_for_terminal


CodexFactory = Callable[[], AbstractContextManager[Any]]


class _SemanticProviderPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bounded_summary: str
    decisions: tuple[str, ...]
    derived_constraints: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    authority_assessment: SteeringAuthorityAssessment
    human_attention_recommendation: str | None = None
    proposed_production: SemanticProductionProposal | None = None
    completion_claimed: bool


class CodexSdkSemanticStepCapability:
    """Execute one semantic Step in an ephemeral read-only provider Turn."""

    def __init__(
        self,
        *,
        codex_factory: CodexFactory | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive when provided")
        self.codex_factory = codex_factory or Codex
        self.model = model
        self.timeout_seconds = timeout_seconds

    def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
        with self.codex_factory() as codex:
            thread = codex.thread_start(
                approval_mode=ApprovalMode.deny_all,
                cwd=input.repository_location,
                ephemeral=True,
                model=self.model,
                sandbox=Sandbox.read_only,
            )
            turn = thread.turn(
                self._instruction(input),
                approval_mode=ApprovalMode.deny_all,
                cwd=input.repository_location,
                model=self.model,
                output_schema=self.output_schema(),
                sandbox=Sandbox.read_only,
            )
            terminal = _wait_for_terminal(turn, self.timeout_seconds)
        if terminal.timed_out or terminal.result is None:
            raise SteeringInvariantViolation(
                "Semantic reasoning Provider did not complete within its bounded Turn"
            )
        result = terminal.result
        if _enum_value(result.status) != "completed" or result.error is not None:
            raise SteeringInvariantViolation(
                "Semantic reasoning Provider did not return a completed result"
            )
        payload = self._parse_payload(result.final_response)
        kind = (
            SemanticResultKind.DESIGN_DIRECTION
            if input.step.type is SteeringStepType.DESIGN
            else SemanticResultKind.WORK_REFINEMENT
        )
        return SemanticStepResultCandidate(
            work_id=input.work_id,
            steering_plan_revision_id=input.steering_plan_revision_id,
            step_id=input.step.id,
            step_type=input.step.type,
            basis_fingerprint=input.basis_fingerprint,
            result_kind=kind,
            bounded_summary=payload.bounded_summary,
            decisions=payload.decisions,
            derived_constraints=payload.derived_constraints,
            evidence_refs=input.reality_refs,
            unresolved_questions=payload.unresolved_questions,
            authority_assessment=payload.authority_assessment,
            human_attention_recommendation=(
                payload.human_attention_recommendation
            ),
            proposed_production=payload.proposed_production,
            reasoning_provider_identity=(
                f"codex-sdk:thread:{thread.id}:turn:{turn.id}"
            ),
            completion_claimed=payload.completion_claimed,
        )

    @staticmethod
    def output_schema() -> dict[str, Any]:
        """Return the exact typed payload contract supplied to Provider generation."""

        return _SemanticProviderPayload.model_json_schema()

    @staticmethod
    def _parse_payload(raw: str) -> _SemanticProviderPayload:
        value = raw.strip()
        if value.startswith("```"):
            lines = value.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            value = "\n".join(lines).strip()
        try:
            return _SemanticProviderPayload.model_validate(json.loads(value))
        except (ValueError, TypeError) as error:
            raise SteeringInvariantViolation(
                "Semantic reasoning Provider returned an invalid structured result"
            ) from error

    @staticmethod
    def _instruction(input: SemanticStepInput) -> str:
        governed = input.model_dump(
            mode="json",
            exclude={"repository_location"},
        )
        return (
            "Execute exactly one governed semantic Steering Step. This is read-only "
            "reasoning: do not modify files, create production authority, commit, or "
            "push. Ground the result in the supplied Work, authority, exact baseline, "
            "repository tree, and bounded context. Return JSON only, with exactly these "
            "fields: bounded_summary (string); decisions (non-empty string array); "
            "derived_constraints (array containing only already admitted constraints); "
            "unresolved_questions (string array); authority_assessment "
            "(WITHIN_AUTHORITY, UNCERTAIN, or EXPANDS_AUTHORITY); "
            "human_attention_recommendation (string or null); proposed_production "
            "(null, or a typed object with target_kind, objective, artifact_targets, "
            "code_targets, allowed_areas, forbidden_areas, verification_expectation); "
            "completion_claimed (boolean). For REFINE, proposed_production must be null. "
            "For proposed production, target_kind must be exactly DOCUMENTATION_WORK or "
            "CODE_WORK. DOCUMENTATION_WORK uses exactly one artifact_targets object with "
            "repository-relative path and CREATE or UPDATE operation; CODE_WORK leaves "
            "artifact_targets empty and uses exact repository-relative code_targets and/or "
            "allowed_areas. Every allowed_areas value must be a repository-relative area "
            "ending with /**; natural-language area descriptions are invalid. DESIGN may "
            "propose production but never authorizes it. If an exact target or bounded area "
            "is not supported by the supplied Reality, record the uncertainty instead of "
            "fabricating a path. "
            "If uncertainty or authority expansion exists, provide a Human recommendation "
            "and do not claim completion. Do not treat your prose as authority.\n\n"
            "Governed SemanticStepInput:\n"
            + json.dumps(governed, ensure_ascii=False, sort_keys=True)
        )
