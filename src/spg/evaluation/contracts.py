"""Quality-owned observations and experiments; none convey production authority."""
from __future__ import annotations

from enum import StrEnum
from hashlib import sha256
import json
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Cohort(StrEnum):
    GOLDEN = "GOLDEN"
    REGRESSION = "REGRESSION"
    FRESH_HOLDOUT = "FRESH_HOLDOUT"
    PREFERENCE = "PREFERENCE"


class Evaluator(StrEnum):
    DETERMINISTIC = "DETERMINISTIC"
    RUNTIME = "RUNTIME"
    GUARDIAN = "GUARDIAN"
    LLM = "LLM"
    HUMAN = "HUMAN"


class Stage(StrEnum):
    WIC = "WIC"
    IRK = "IRK"
    ECF = "ECF"
    SEARCH = "SEARCH"
    STEERING = "STEERING"
    PLANNING = "PLANNING"
    PWU = "PWU"
    MODEL_ROUTING = "MODEL_ROUTING"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"
    GUARDIAN = "GUARDIAN"
    ACCEPTANCE_PROMOTION = "ACCEPTANCE_PROMOTION"


class QualityError(ValueError):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


def fingerprint(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, default=str).encode()).hexdigest()


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CaseDefinition(Record):
    key: str = Field(min_length=1, max_length=160, pattern=r"^[a-zA-Z0-9_.:-]+$")
    title: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=80)
    motive: str = Field(min_length=1, max_length=4000)
    invariants: tuple[str, ...] = Field(min_length=1, max_length=30)
    context: dict[str, Any] = Field(default_factory=dict)
    provenance: tuple[str, ...] = Field(min_length=1)
    runner_key: str = Field(min_length=1, max_length=160)
    stage: Stage
    cohorts: tuple[Cohort, ...] = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    private_material: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def nonempty_obligations(self):
        if any(not s.strip() for s in self.invariants):
            raise ValueError("Case obligations cannot be empty")
        return self


class Evaluation(Record):
    evaluator: Evaluator
    outcome: str = Field(pattern=r"^(PASS|FAIL|BLOCKED|UNKNOWN|PREFERRED|REJECTED)$")
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    evaluator_version: str = Field(min_length=1)
    stage: Stage | None = None
    finding_code: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


def objective_verdict(evaluations: tuple[Evaluation, ...]) -> str:
    """Preference never compensates for missing or failing engineering evidence."""
    objective = [e for e in evaluations if e.evaluator in {
        Evaluator.DETERMINISTIC, Evaluator.RUNTIME, Evaluator.GUARDIAN}]
    if any(e.outcome == "FAIL" for e in objective):
        return "FAIL"
    if not any(e.evaluator == Evaluator.DETERMINISTIC for e in objective):
        return "UNKNOWN"
    if any(e.outcome != "PASS" for e in objective):
        return "BLOCKED"
    return "PASS"


def earliest_divergence(evaluations: tuple[Evaluation, ...]) -> dict:
    """Order observed failures only; never infer that unobserved prior stages passed."""
    failures = [e for e in evaluations if e.evaluator in {
        Evaluator.DETERMINISTIC, Evaluator.RUNTIME, Evaluator.GUARDIAN}
        and e.outcome in {"FAIL", "BLOCKED"}]
    witnessed = [e for e in failures if e.stage is not None]
    first = min(witnessed, key=lambda e: list(Stage).index(e.stage)) if witnessed else None
    return {"stage": None if first is None else first.stage.value,
            "certainty": "EARLIEST_OBSERVED" if first else "UNKNOWN",
            "earlier_stages_proven": False,
            "evidence_refs": [] if first is None else list(first.evidence_refs)}


class CampaignRequest(Record):
    campaign_id: UUID
    experiment_id: UUID | None = None
    variant_key: str | None = None


class Variant(Record):
    key: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    label: str = Field(min_length=1, max_length=160)
    model: str = Field(min_length=1, max_length=160)
    provider: str = Field(min_length=1, max_length=80)
    policy: dict[str, Any]
    output_refs: tuple[str, ...] = ()


class ExperimentRequest(Record):
    case_id: UUID
    name: str = Field(min_length=1, max_length=160)
    variants: tuple[Variant, ...] = Field(min_length=2, max_length=5)
    changed_variables: tuple[str, ...] = Field(min_length=1, max_length=12)
    rationale: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def exact_comparison(self):
        if len({v.key for v in self.variants}) != len(self.variants):
            raise ValueError("Duplicate experiment variant")
        allowed = {"model", "provider", "policy"}
        if not set(self.changed_variables) <= allowed:
            raise ValueError("Unsupported experiment variable")
        base = self.variants[0]
        observed = {key for variant in self.variants[1:] for key in allowed
                    if getattr(variant, key) != getattr(base, key)}
        if observed != set(self.changed_variables):
            raise ValueError("Declared variables must match the exact experiment differences")
        return self


class PreferenceRequest(Record):
    experiment_id: UUID
    ranking: tuple[str, ...] = Field(min_length=2, max_length=5)
    acceptability: dict[str, bool]
    case_run_ids: dict[str, UUID]
    confidence: float = Field(ge=0, le=1)
    reason_tags: tuple[str, ...] = Field(min_length=1, max_length=12)
    rationale: str = Field(min_length=1, max_length=4000)


class AttributionRequest(Record):
    source_kind: str = Field(pattern=r"^(PREFERENCE|FINDING)$")
    source_id: UUID
    owners: tuple[Stage, ...] = Field(min_length=1, max_length=5)
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=2000)


class PromotionRequest(Record):
    experiment_id: UUID
    variant_key: str
    campaign_run_ids: tuple[UUID, ...] = Field(min_length=1, max_length=10)
    rationale: str = Field(min_length=1, max_length=2000)


class FindingClosureRequest(Record):
    qualified_case_run_id: UUID
    rationale: str = Field(min_length=1, max_length=2000)
