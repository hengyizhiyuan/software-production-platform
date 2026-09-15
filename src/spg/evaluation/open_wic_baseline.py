"""OPEN_WIC replay seam for immutable, unadmitted WIC candidate capture.

The runner deliberately accepts only a WorkInteractionCapability. It has no
database, Work admission, governance, or production dependency, so a replay can
exercise the configured Provider while remaining outside every mutation path.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from collections.abc import Callable
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

from spg.application.interaction import (
    ASSESSMENT_SCHEMA_VERSION,
    WorkInteractionService,
    interaction_basis_fingerprint,
)
from spg.application.wic_intelligence import build_progressive_semantics
from spg.domain.conversation import ConversationContextMessage
from spg.domain.interaction import (
    ActiveWorkInterpretationContext,
    Interaction,
    InteractionActor,
    InteractionAssessment,
    InteractionAssessmentCandidate,
    InteractionCondition,
    InteractionInterpretationInput,
    InteractionRecord,
    WorkInteractionCapability,
    WorkRealityRevision,
    WorkSatisfactionState,
)


CORPUS_SCHEMA_VERSION = "open-wic-corpus-v1"
RESULT_SCHEMA_VERSION = "open-wic-result-v1"
SENTENCE_END = re.compile(r"[。！？.!?](?:[\"'”’）)]|\s|$)")


class EpisodeState(StrEnum):
    PRE_WORK = "PRE_WORK"
    ACTIVE_WORK = "ACTIVE_WORK"


class ExpectedWorkRelationship(StrEnum):
    PRE_WORK = "PRE_WORK"
    SAME_ACTIVE_WORK = "SAME_ACTIVE_WORK"
    CANDIDATE_CHANGE = "CANDIDATE_CHANGE"
    NEW_MOTIVE_NEW_WORK = "NEW_MOTIVE_NEW_WORK"
    CONVERSATION_ONLY = "CONVERSATION_ONLY"


class GovernanceExpectation(StrEnum):
    REQUIRED = "REQUIRED"
    NOT_REQUIRED = "NOT_REQUIRED"
    CONDITIONAL = "CONDITIONAL"


class HumanTurnFixture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str = Field(min_length=1)
    supporting_references: tuple[str, ...] = ()


class ActiveWorkFixture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    motive: str = Field(min_length=1)
    desired_outcome: str = Field(min_length=1)
    context_facts: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    requests: tuple[str, ...] = ()
    relevant_reality_references: tuple[str, ...] = ()
    repository_identity: str | None = None
    repository_ref: str | None = None
    source_revision: str | None = None
    satisfaction_state: WorkSatisfactionState = WorkSatisfactionState.IN_PROGRESS

    @model_validator(mode="after")
    def repository_fields_are_complete(self) -> "ActiveWorkFixture":
        values = (self.repository_identity, self.repository_ref, self.source_revision)
        if any(value is not None for value in values) and not all(
            value is not None for value in values
        ):
            raise ValueError("Repository fixture fields must be wholly present or absent")
        return self


class ReferenceIntent(BaseModel):
    """Human-authored semantic reference, kept separate from Provider output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    true_motive: str = Field(min_length=1)
    material_facts: tuple[str, ...] = ()
    material_constraints: tuple[str, ...] = ()
    known_corrections: tuple[str, ...] = ()
    forbidden_assumptions: tuple[str, ...] = ()
    expected_work_relationship: ExpectedWorkRelationship
    important_ambiguity: tuple[str, ...] = ()
    acceptable_inferences: tuple[str, ...] = ()
    governance_expectation: GovernanceExpectation


class OpenWicEpisode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(pattern=r"^OW-[A-Z]$")
    title: str = Field(min_length=1)
    category: str = Field(min_length=1)
    initial_state: EpisodeState
    human_turns: tuple[HumanTurnFixture, ...] = Field(min_length=1)
    active_work: ActiveWorkFixture | None = None
    reference_intent: ReferenceIntent

    @model_validator(mode="after")
    def state_matches_fixture(self) -> "OpenWicEpisode":
        if (self.initial_state is EpisodeState.ACTIVE_WORK) != (
            self.active_work is not None
        ):
            raise ValueError("ACTIVE_WORK episodes require exactly one active_work fixture")
        return self


class OpenWicCorpus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(pattern=r"^open-wic-corpus-v\d+$")
    corpus_id: str = Field(min_length=1)
    frozen_at: datetime
    cases: tuple[OpenWicEpisode, ...] = Field(min_length=8, max_length=15)

    @model_validator(mode="after")
    def unique_cases(self) -> "OpenWicCorpus":
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("OPEN_WIC case ids must be unique")
        return self


class ProviderAttribution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_adapter: str
    semantic_model: str | None
    semantic_reasoning_effort: str | None
    conversation_model: str | None
    conversation_reasoning_effort: str | None
    coalesce_pre_work: bool
    wic_schema_version: str
    code_revision: str
    source_fingerprint: str


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_corpus(path: Path) -> tuple[OpenWicCorpus, str]:
    raw = path.read_text(encoding="utf-8")
    corpus = OpenWicCorpus.model_validate_json(raw)
    canonical = _stable_json(corpus.model_dump(mode="json"))
    return corpus, _sha256(canonical)


def _case_uuid(case_id: str, name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"watt:open-wic:{case_id}:{name}")


def _active_context(case: OpenWicEpisode, now: datetime) -> ActiveWorkInterpretationContext | None:
    fixture = case.active_work
    if fixture is None:
        return None
    repository = fixture.repository_identity is not None
    revision = WorkRealityRevision(
        id=_case_uuid(case.case_id, "work-revision"),
        work_id=_case_uuid(case.case_id, "work"),
        revision_number=1,
        basis_fingerprint=_sha256(f"{case.case_id}:work-basis"),
        revision_fingerprint=_sha256(f"{case.case_id}:work-revision"),
        source_interaction_id=_case_uuid(case.case_id, "source-interaction"),
        source_assessment_id=_case_uuid(case.case_id, "source-assessment"),
        source_record_ids=(_case_uuid(case.case_id, "source-record"),),
        motive=fixture.motive,
        desired_outcome=fixture.desired_outcome,
        context_facts=fixture.context_facts,
        constraints=fixture.constraints,
        requests=fixture.requests,
        engineering_scope_id=_case_uuid(case.case_id, "engineering-scope"),
        engineering_resource_id=(
            _case_uuid(case.case_id, "engineering-resource") if repository else None
        ),
        scope_basis_fingerprint=_sha256(f"{case.case_id}:scope"),
        repository_identity=fixture.repository_identity,
        repository_ref=fixture.repository_ref,
        source_baseline_id=(
            _case_uuid(case.case_id, "source-baseline") if repository else None
        ),
        source_revision=fixture.source_revision,
        governance_record_id=_case_uuid(case.case_id, "governance"),
        supporting_references=fixture.relevant_reality_references,
        change_set=("OPEN_WIC deterministic active Work fixture",),
        rationale="Frozen semantic baseline fixture; no governed state was created.",
        admitted_by="open-wic-fixture",
        schema_version="work-reality-v1",
        created_at=now,
    )
    return ActiveWorkInterpretationContext(
        work_revision=revision,
        engineering_scope_fingerprint=revision.scope_basis_fingerprint,
        relevant_reality_references=fixture.relevant_reality_references,
        satisfaction_state=fixture.satisfaction_state,
    )


def _assessment_from_candidate(
    case: OpenWicEpisode,
    turn_number: int,
    basis: InteractionInterpretationInput,
    candidate: InteractionAssessmentCandidate,
    now: datetime,
) -> InteractionAssessment:
    return InteractionAssessment(
        id=_case_uuid(case.case_id, f"assessment-{turn_number}"),
        interaction_id=basis.interaction.id,
        basis_fingerprint=basis.basis_fingerprint,
        basis_last_sequence=len(basis.records),
        interpreted_motive=candidate.interpreted_motive,
        desired_outcome=candidate.desired_outcome,
        design_intent_frame=candidate.design_intent_frame,
        candidate_context=candidate.candidate_context,
        candidate_constraints=candidate.candidate_constraints,
        current_requests=candidate.current_requests,
        unresolved_material_questions=candidate.unresolved_material_questions,
        meanings=candidate.meanings,
        focus_classification=candidate.focus_classification,
        impact_disposition=candidate.impact_disposition,
        basis_work_revision_id=(
            None if basis.active_work_context is None
            else basis.active_work_context.work_revision.id
        ),
        supporting_references=candidate.supporting_references,
        natural_response=candidate.natural_response,
        readiness=WorkInteractionService._evaluate_readiness(
            candidate, basis.basis_fingerprint
        ),
        provider_identity=candidate.provider_identity,
        model_identity=candidate.model_identity,
        schema_version=ASSESSMENT_SCHEMA_VERSION,
        created_at=now,
    )


def _provider_evidence(capability: WorkInteractionCapability) -> dict[str, Any] | None:
    evidence = getattr(capability, "last_pipeline_evidence", None)
    if evidence is None:
        return None
    if is_dataclass(evidence):
        return asdict(evidence)
    if isinstance(evidence, BaseModel):
        return evidence.model_dump(mode="json")
    raise TypeError("Unsupported Provider evidence type")


def _usage_totals(evidence: dict[str, Any] | None) -> dict[str, int | float | None]:
    totals: dict[str, int | float | None] = {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "cost_rmb": None,
    }
    if evidence is None:
        return totals
    usages = [
        evidence.get("semantic_usage"),
        evidence.get("conversation_usage"),
        evidence.get("coalesced_usage"),
    ]
    for key in totals:
        values = [usage.get(key) for usage in usages if isinstance(usage, dict)]
        numeric = [value for value in values if isinstance(value, (int, float))]
        if numeric:
            totals[key] = sum(numeric)
    return totals


def _question_count(text: str) -> int:
    return text.count("?") + text.count("？")


def replay_episode(
    case: OpenWicEpisode,
    capability: WorkInteractionCapability,
) -> dict[str, Any]:
    """Capture raw candidates from one frozen episode without admitting them."""

    now = datetime.now(UTC)
    interaction_id = _case_uuid(case.case_id, "interaction")
    active = _active_context(case, now)
    interaction = Interaction(
        id=interaction_id,
        condition=InteractionCondition.OPEN,
        current_work_id=None if active is None else active.work_revision.work_id,
        created_by="open-wic-replay",
        updated_by="open-wic-replay",
        created_at=now,
        updated_at=now,
    )
    records: list[InteractionRecord] = []
    conversation: list[ConversationContextMessage] = []
    prior: InteractionAssessment | None = None
    raw_turn_outputs: list[dict[str, Any]] = []
    status = "CANDIDATES_CAPTURED"
    failure: dict[str, str] | None = None

    for index, turn in enumerate(case.human_turns, start=1):
        record = InteractionRecord(
            id=_case_uuid(case.case_id, f"human-{index}"),
            interaction_id=interaction_id,
            sequence=index,
            actor=InteractionActor.HUMAN,
            source="OPEN_WIC_FROZEN_CORPUS",
            content=turn.content,
            content_fingerprint=_sha256(turn.content),
            work_focus_id=None if active is None else active.work_revision.work_id,
            supporting_references=turn.supporting_references,
            created_at=now,
        )
        records.append(record)
        fingerprint = interaction_basis_fingerprint(interaction, tuple(records), active)
        basis = InteractionInterpretationInput(
            interaction=interaction,
            records=tuple(records),
            prior_assessment=prior,
            active_work_context=active,
            basis_fingerprint=fingerprint,
            recent_conversation_messages=tuple(conversation),
        )
        before = _stable_json(basis.model_dump(mode="json"))
        started = time.monotonic()
        first_delta_seconds: float | None = None
        first_meaningful_sentence_seconds: float | None = None
        streamed = ""
        stages: list[dict[str, Any]] = []

        def on_delta(delta: str) -> None:
            nonlocal streamed, first_delta_seconds, first_meaningful_sentence_seconds
            elapsed = time.monotonic() - started
            if delta and first_delta_seconds is None:
                first_delta_seconds = elapsed
            streamed += delta
            compact = "".join(streamed.split())
            if (
                first_meaningful_sentence_seconds is None
                and len(compact) >= 8
                and SENTENCE_END.search(streamed)
            ):
                first_meaningful_sentence_seconds = elapsed

        def on_stage(name: str) -> None:
            stages.append({"name": name, "seconds": time.monotonic() - started})

        try:
            observed = getattr(capability, "interpret_stream_observed", None)
            if callable(observed):
                candidate = observed(
                    basis,
                    on_response_delta=on_delta,
                    on_pipeline_stage=on_stage,
                )
            else:
                streamed_method = getattr(capability, "interpret_stream", None)
                if callable(streamed_method):
                    candidate = streamed_method(basis, on_response_delta=on_delta)
                else:
                    candidate = capability.interpret(basis)
            completed = time.monotonic() - started
            if _stable_json(basis.model_dump(mode="json")) != before:
                raise AssertionError("WIC capability mutated the frozen replay basis")
            if streamed and streamed.strip() != candidate.natural_response.strip():
                raise AssertionError("Observed response stream differs from candidate")
            evidence = _provider_evidence(capability)
            progressive = build_progressive_semantics(
                candidate=candidate,
                records=tuple(records),
                basis_fingerprint=fingerprint,
                prior_assessment=prior,
                active_context=active,
                focus=candidate.focus_classification,
                impact=candidate.impact_disposition,
            )
            prior = _assessment_from_candidate(case, index, basis, candidate, now)
            prior = prior.model_copy(update={"progressive_semantics": progressive})
            conversation.extend((
                ConversationContextMessage(actor="HUMAN", content=turn.content),
                ConversationContextMessage(actor="WATT", content=candidate.natural_response),
            ))
            raw_turn_outputs.append({
                "turn_number": index,
                "input_basis_fingerprint": fingerprint,
                "input_basis_sha256": _sha256(before),
                "candidate": candidate.model_dump(mode="json"),
                "progressive_semantics": progressive.model_dump(mode="json"),
                "readiness": prior.readiness.model_dump(mode="json"),
                "natural_response": candidate.natural_response,
                "metrics": {
                    "first_delta_seconds": first_delta_seconds,
                    "ttfms_seconds": first_meaningful_sentence_seconds,
                    "ttfms_boundary": "provider_stream_first_sentence_min_8_nonspace_chars",
                    "turn_candidate_ready_seconds": completed,
                    "question_count": _question_count(candidate.natural_response),
                    "provider_call_count": (
                        None if evidence is None else evidence.get("provider_call_count")
                    ),
                    "usage": _usage_totals(evidence),
                },
                "provider_evidence": evidence,
                "pipeline_stages": stages,
            })
        except Exception as error:  # Failure is evidence; real calls are never retried.
            status = "FAILED"
            failure = {"type": type(error).__name__, "message": str(error)}
            raw_turn_outputs.append({
                "turn_number": index,
                "input_basis_fingerprint": fingerprint,
                "input_basis_sha256": _sha256(before),
                "failure": failure,
                "metrics": {
                    "first_delta_seconds": first_delta_seconds,
                    "ttfms_seconds": first_meaningful_sentence_seconds,
                    "turn_candidate_ready_seconds": time.monotonic() - started,
                },
                "pipeline_stages": stages,
            })
            break

    return {
        "case_id": case.case_id,
        "status": status,
        "raw_turn_outputs": raw_turn_outputs,
        "reference_intent": case.reference_intent.model_dump(mode="json"),
        "semantic_adjudication": None,
        "failure": failure,
        "mutation_boundary": {
            "production_mutation_attempts": 0,
            "work_or_assessment_admissions": 0,
            "database_dependency_present": False,
        },
    }


def replay_corpus(
    corpus: OpenWicCorpus,
    corpus_digest: str,
    capability: WorkInteractionCapability,
    attribution: ProviderAttribution,
    *,
    on_case_completed: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    cases: list[dict[str, Any]] = []
    for episode in corpus.cases:
        case = replay_episode(episode, capability)
        cases.append(case)
        if on_case_completed is not None:
            on_case_completed(case)
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "baseline_identity": "OPEN_WIC_BASELINE",
        "corpus_id": corpus.corpus_id,
        "corpus_digest": corpus_digest,
        "captured_at": datetime.now(UTC).isoformat(),
        "provider_attribution": attribution.model_dump(mode="json"),
        "scope": "WIC Provider candidates only; no admission, database, Work, or production",
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "captured_count": sum(case["status"] == "CANDIDATES_CAPTURED" for case in cases),
            "failed_count": sum(case["status"] == "FAILED" for case in cases),
            "elapsed_seconds": time.monotonic() - started,
            "semantic_adjudication_status": "NOT_PERFORMED",
        },
    }


def _git_revision() -> str:
    return subprocess.run(
        ("git", "rev-parse", "HEAD"),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _source_fingerprint(root: Path = Path("src/spg")) -> str:
    files = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*.py"))
        if path.is_file()
    }
    return _sha256(_stable_json(files))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--run-real-provider", action="store_true", required=True)
    args = parser.parse_args()

    from spg.application.bootstrap import Application
    from spg.config import Settings

    settings = Settings(_env_file=args.env_file)
    capability = Application(settings).interaction_capability()
    corpus, digest = load_corpus(args.corpus)
    attribution = ProviderAttribution(
        provider_adapter=settings.wic_provider_adapter or settings.executor_adapter,
        semantic_model=settings.wic_provider_model,
        semantic_reasoning_effort=settings.wic_provider_reasoning_effort,
        conversation_model=(
            settings.conversation_provider_model or settings.wic_provider_model
        ),
        conversation_reasoning_effort=settings.conversation_provider_reasoning_effort,
        coalesce_pre_work=settings.wic_coalesce_pre_work,
        wic_schema_version=ASSESSMENT_SCHEMA_VERSION,
        code_revision=_git_revision(),
        source_fingerprint=_source_fingerprint(),
    )
    report = replay_corpus(
        corpus,
        digest,
        capability,
        attribution,
        on_case_completed=lambda case: print(
            json.dumps(
                {
                    "case_id": case["case_id"],
                    "status": case["status"],
                    "turns": len(case["raw_turn_outputs"]),
                },
                ensure_ascii=False,
            ),
            flush=True,
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)
    if report["summary"]["failed_count"]:
        raise SystemExit("OPEN_WIC retained Provider failures; inspect the report")


if __name__ == "__main__":
    main()
