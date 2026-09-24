"""Read-only Codex adapter for governed semantic Steering Step execution."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from copy import deepcopy
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from spg.domain.planning import ProductionPlanArtifactTarget
from spg.domain.steering import (
    SemanticBoundedRepositoryArea,
    SemanticProductionProposal,
    SemanticResultKind,
    SemanticStepInput,
    SemanticStepResultCandidate,
    SteeringAuthorityAssessment,
    SteeringInvariantViolation,
    SteeringStepType,
)
CodexFactory = Callable[[], AbstractContextManager[Any]]


def _provider_strict_output_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Adapt typed JSON Schema to the Provider's strict pure-``$ref`` dialect."""

    normalized = deepcopy(schema)

    def normalize(value: object) -> None:
        if isinstance(value, dict):
            if "$ref" in value:
                reference = value["$ref"]
                value.clear()
                value["$ref"] = reference
                return
            for nested in value.values():
                normalize(nested)
        elif isinstance(value, list):
            for nested in value:
                normalize(nested)

    normalize(normalized)
    return normalized


class _SemanticProviderProductionProposal(SemanticProductionProposal):
    """Strict Provider wire shape over unchanged domain proposal semantics."""

    artifact_targets: tuple[ProductionPlanArtifactTarget, ...] = Field(
        description=(
            "Typed documentation artifact targets; CODE_WORK must leave this empty."
        ),
    )
    code_targets: tuple[str, ...] = Field(
        description="Exact repository-relative code paths without wildcards.",
    )
    allowed_areas: tuple[SemanticBoundedRepositoryArea, ...] = Field(
        description=(
            "Repository-relative bounded subdirectories ending with /**; "
            "root-wide areas such as src/** or tests/** are invalid."
        ),
    )
    forbidden_areas: tuple[str, ...] = Field(
        description=(
            "Repository-relative exact paths or bounded areas ending with /**."
        ),
    )

    def to_domain(self) -> SemanticProductionProposal:
        """Discard wire-only requiredness without changing semantic values."""

        return SemanticProductionProposal.model_validate(self.model_dump())


class _SemanticProviderResolvedDisposition(BaseModel):
    """Wire shape for a semantic result with no governed attention boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["RESOLVED"]
    authority_assessment: Literal[SteeringAuthorityAssessment.WITHIN_AUTHORITY]
    unresolved_questions: tuple[str, ...] = Field(max_length=0)
    human_attention_recommendation: None
    completion_claimed: Literal[True]


class _SemanticProviderUnresolvedDisposition(BaseModel):
    """Wire shape for an explicit unresolved semantic question."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["UNRESOLVED"]
    authority_assessment: Literal[SteeringAuthorityAssessment.UNCERTAIN]
    unresolved_questions: tuple[str, ...] = Field(min_length=1)
    human_attention_recommendation: str = Field(min_length=1)
    completion_claimed: Literal[False]


class _SemanticProviderAuthorityExpansionDisposition(BaseModel):
    """Wire shape for a proposed direction outside admitted Work authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["AUTHORITY_EXPANSION"]
    authority_assessment: Literal[
        SteeringAuthorityAssessment.EXPANDS_AUTHORITY
    ]
    unresolved_questions: tuple[str, ...] = Field(min_length=1)
    human_attention_recommendation: str = Field(min_length=1)
    completion_claimed: Literal[False]


_SemanticProviderDisposition = (
    _SemanticProviderResolvedDisposition
    | _SemanticProviderUnresolvedDisposition
    | _SemanticProviderAuthorityExpansionDisposition
)


class _SemanticProviderPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bounded_summary: str
    decisions: tuple[str, ...]
    derived_constraints: tuple[str, ...]
    proposed_production: _SemanticProviderProductionProposal | None
    disposition: _SemanticProviderDisposition

    @property
    def unresolved_questions(self) -> tuple[str, ...]:
        return self.disposition.unresolved_questions

    @property
    def authority_assessment(self) -> SteeringAuthorityAssessment:
        return self.disposition.authority_assessment

    @property
    def human_attention_recommendation(self) -> str | None:
        return self.disposition.human_attention_recommendation

    @property
    def completion_claimed(self) -> bool:
        return self.disposition.completion_claimed

    def domain_production_proposal(self) -> SemanticProductionProposal | None:
        """Convert the strict wire proposal into the existing domain contract."""

        if self.proposed_production is None:
            return None
        return self.proposed_production.to_domain()


def _admitted_derived_constraints(
    payload: _SemanticProviderPayload,
    input: SemanticStepInput,
) -> tuple[str, ...]:
    """Keep Provider inference from becoming Human-approved constraint truth."""

    admitted = set(input.constraints)
    return tuple(
        constraint
        for constraint in payload.derived_constraints
        if constraint in admitted
    )


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
        if codex_factory is None:
            from openai_codex import Codex

            codex_factory = Codex
        self.codex_factory = codex_factory
        self.model = model
        self.timeout_seconds = timeout_seconds

    def execute(self, input: SemanticStepInput) -> SemanticStepResultCandidate:
        from openai_codex import ApprovalMode, Sandbox

        from spg.providers.codex_sdk_executor import _enum_value, _wait_for_terminal

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
            derived_constraints=_admitted_derived_constraints(payload, input),
            evidence_refs=input.reality_refs,
            unresolved_questions=payload.unresolved_questions,
            authority_assessment=payload.authority_assessment,
            human_attention_recommendation=(
                payload.human_attention_recommendation
            ),
            proposed_production=payload.domain_production_proposal(),
            reasoning_provider_identity=(
                f"codex-sdk:thread:{thread.id}:turn:{turn.id}"
            ),
            completion_claimed=payload.completion_claimed,
        )

    @staticmethod
    def output_schema() -> dict[str, Any]:
        """Return the exact typed payload contract supplied to Provider generation."""

        return _provider_strict_output_schema(
            _SemanticProviderPayload.model_json_schema()
        )

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
    def _parse_payload_ignoring_annotations(raw: str) -> _SemanticProviderPayload:
        """Ignore transport-only prose keys while preserving strict semantic validation."""

        value = raw.strip()
        if value.startswith("```"):
            lines = value.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            value = "\n".join(lines).strip()
        try:
            decoded = json.loads(value)
            if not isinstance(decoded, dict):
                raise TypeError("semantic payload must be an object")
            decoded = {
                key: item
                for key, item in decoded.items()
                if key in _SemanticProviderPayload.model_fields
            }
            proposal = decoded.get("proposed_production")
            if isinstance(proposal, dict):
                decoded["proposed_production"] = {
                    key: item
                    for key, item in proposal.items()
                    if key in _SemanticProviderProductionProposal.model_fields
                }
            disposition = decoded.get("disposition")
            if isinstance(disposition, dict):
                decoded["disposition"] = {
                    key: item
                    for key, item in disposition.items()
                    if key
                    in {
                        "state",
                        "authority_assessment",
                        "unresolved_questions",
                        "human_attention_recommendation",
                        "completion_claimed",
                    }
                }
            return _SemanticProviderPayload.model_validate(decoded)
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
            "push. Do not invoke shell, filesystem, or repository tools in this Turn. "
            "Repository access is bounded to the supplied repository_tree_paths and context_materials. "
            "Available and unavailable executable capability identities in the governed input are System Capability Reality, not authority. Do not claim an unavailable operation will execute immediately; retain its capability gap for governed recovery. "
            "When engineering_resource_id is null, continue design without claiming repository evidence. "
            "For intermediate design issues (production_transition_issue=false), repository absence "
            "does not prevent completion: claim completion when that issue is resolved. "
            "At the production-transition issue, the execution infrastructure supplies either an "
            "explicitly admitted Repository Asset or a Watt-managed local execution workspace. "
            "A user-provided remote repository is optional and its absence is not a reason to block "
            "or omit an otherwise reviewable production proposal. Never infer remote access, write, "
            "branch, pull-request, or push authority from a repository URL. "
            "The supplied context_materials are authoritative for the exact baseline. A path "
            "inventory that identifies existing implementation and test seams may "
            "support exact production targets even when full source contents are not "
            "included; missing full contents alone is not a Human decision. Never "
            "claim that a path absent from that inventory already exists. A CREATE proposal "
            "may specify a new bounded path supported by the admitted Work request; absence "
            "from the tree is expected for CREATE, not missing evidence. Evaluate sufficiency "
            "for this current governed Step, not for every question that may eventually matter "
            "to the whole Work. Missing information blocks only when (1) Watt lacks authority "
            "to choose it and (2) different choices materially change the current artifact, "
            "scope, cost, risk, irreversible effect, execution constraint, or acceptance result. "
            "Both conditions are required. Broader product discovery that does not affect this "
            "bounded Step is non-blocking and must not be placed in unresolved_questions. "
            "Resolve routine analysis autonomously. Ground the result in the supplied Work, "
            "authority, exact baseline, "
            "repository tree, and bounded context. Return JSON only, with exactly these "
            "fields: bounded_summary (string); decisions (non-empty string array); "
            "derived_constraints (array containing only constraints copied verbatim from "
            "the supplied constraints; put inferred implementation choices in decisions); "
            "proposed_production "
            "(null, or a typed object with target_kind, objective, artifact_targets, "
            "code_targets, allowed_areas, forbidden_areas, verification_expectation); "
            "disposition (exactly one schema-selected object). disposition RESOLVED "
            "requires authority_assessment WITHIN_AUTHORITY, unresolved_questions [], "
            "human_attention_recommendation null, and completion_claimed true. Completion here "
            "means this current issue only, not the whole design agenda or Human product acceptance. "
            "disposition UNRESOLVED requires authority_assessment UNCERTAIN, at least one "
            "material current-Step unresolved question that Watt lacks authority to answer, a non-empty Human "
            "recommendation, and completion_claimed false. disposition "
            "AUTHORITY_EXPANSION requires authority_assessment EXPANDS_AUTHORITY, at least "
            "one material current-Step unresolved question, a non-empty Human recommendation, "
            "and completion_claimed false. For REFINE, "
            "proposed_production must be null. "
            "When design_context is present, address only its current_issue and preserve "
            "that governed focus. Earlier admitted results are context, not permission to "
            "collapse the remaining agenda. When production_transition_issue is false, "
            "proposed_production must be null. Only the production-transition issue may "
            "form a reviewable production proposal, and it must do so to claim completion. "
            "When production_proposal_required is true, the current DESIGN Step leads to "
            "PRODUCE but the latest Work Reality has no current implementation Production Plan. A RESOLVED "
            "result must therefore include one complete bounded proposed_production; do not "
            "reuse or merely describe a historical proposal. If current Reality cannot "
            "support exact bounded targets, return a truthful unresolved disposition. "
            "Request Human Attention only when the decision is both outside Watt's admitted "
            "authority and material to the current governed Step; routine analysis and "
            "synthesis remain automatic. A bounded, reversible, low-risk artifact with a "
            "known observable outcome and verification basis must not be blocked merely for "
            "missing persona, market, commercial rationale, or broad journey information. "
            "For proposed production, target_kind must be exactly DOCUMENTATION_WORK or "
            "CODE_WORK. required_intermediate_artifacts and approved_artifact_references "
            "are governed transition constraints, not suggestions. When "
            "APPROVED_DESIGN_ARTIFACT is required and no approved artifact reference is "
            "present, propose DOCUMENTATION_WORK that materializes the current admitted "
            "design basis for Human review; CODE_WORK is forbidden. Once that exact "
            "prerequisite evidence exists and the current Step follows a DESIGN_ARTIFACT "
            "cycle, the admitted working-software outcome must use CODE_WORK with implementation "
            "and verification targets; do not propose another documentation-only cycle. Otherwise an "
            "admitted working-software outcome may choose CODE_WORK with implementation "
            "and executable test paths. Preserve the admitted runtime form and entrypoint "
            "in the production objective. "
            "DOCUMENTATION_WORK uses exactly one artifact_targets object with "
            "repository-relative path and CREATE or UPDATE operation, and MUST set code_targets, "
            "allowed_areas and forbidden_areas to empty arrays. For example a new document "
            "may use artifact_targets=[{\"path\":\"docs/design.md\",\"operation\":\"CREATE\"}], "
            "with code_targets=[], allowed_areas=[], forbidden_areas=[]. Put documentation "
            "scope exclusions in objective/verification_expectation instead of those code fields. CODE_WORK leaves "
            "artifact_targets empty and uses exact repository-relative code_targets and/or "
            "allowed_areas. Every allowed_areas value must be a repository-relative "
            "subdirectory ending with /** and with at least two path segments before it; "
            "root-wide fallback "
            "areas such as src/** and tests/** and natural-language area descriptions are "
            "invalid. Use exact code_targets, narrower nested areas, or an unresolved "
            "disposition instead. DESIGN may "
            "propose production but never authorizes it. If an exact target or bounded area "
            "is not supported by the supplied Reality, record the uncertainty instead of "
            "fabricating a path. "
            "Select UNRESOLVED or AUTHORITY_EXPANSION only for a material current-Step choice "
            "that Watt lacks authority to make; never encode an incoherent cross-field combination. Do not "
            "treat your prose as authority.\n\n"
            "Governed SemanticStepInput:\n"
            + json.dumps(governed, ensure_ascii=False, sort_keys=True)
        )
