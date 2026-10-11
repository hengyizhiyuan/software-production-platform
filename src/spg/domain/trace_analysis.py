"""Advisory investigation contracts. They confer no production authority."""
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnalysisRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class IssueClass(StrEnum):
    RUNTIME_MODEL_VARIANCE = "RUNTIME_MODEL_VARIANCE"
    SYSTEM_CAPABILITY_DEFECT = "SYSTEM_CAPABILITY_DEFECT"
    GOVERNANCE_ISSUE = "GOVERNANCE_ISSUE"
    UNKNOWN = "UNKNOWN"


class Citation(AnalysisRecord):
    evidence_id: UUID
    quote: str = Field(min_length=1, max_length=1200)


class EvidenceFamily(StrEnum):
    OWNER_RECORD = "OWNER_RECORD"
    PREVIEW_HTTP = "PREVIEW_HTTP"
    DELIVERY_TRANSFER = "DELIVERY_TRANSFER"
    EXECUTION_RELATIONSHIP = "EXECUTION_RELATIONSHIP"


class EvidenceAssessment(AnalysisRecord):
    family: EvidenceFamily
    check_id: UUID
    availability: Literal["PRESENT", "NOT_OBSERVED_IN_CAPTURE", "INCOMPLETE_CAPTURE"]
    statement: str = Field(min_length=1, max_length=2000)


class EvidenceGap(AnalysisRecord):
    statement: str = Field(min_length=1, max_length=2000)
    family: EvidenceFamily
    check_id: UUID
    availability: Literal["NOT_OBSERVED_IN_CAPTURE", "INCOMPLETE_CAPTURE"]


class ObservedFact(AnalysisRecord):
    statement: str = Field(min_length=1, max_length=2000)
    citations: tuple[Citation, ...] = Field(min_length=1, max_length=8)
    evidence_family: EvidenceFamily = Field(default=EvidenceFamily.OWNER_RECORD,
        description="Declare PREVIEW_HTTP for preview GET/status/digest claims, DELIVERY_TRANSFER for download audits, EXECUTION_RELATIONSHIP for identity linkage. Citation text from another surface cannot prove this fact.")


class TimelineItem(ObservedFact):
    stage: Literal["INTENT", "CONTEXT", "PLANNING", "EXECUTION", "VERIFICATION",
                   "FAILURE", "RECOVERY_REFINEMENT", "FINAL_STATE"]
    timestamp: str | None = None


class Finding(AnalysisRecord):
    finding_id: str = Field(min_length=1, max_length=80)
    classification: IssueClass
    epistemic_status: Literal["ROOT_CAUSE_HYPOTHESIS", "UNKNOWN"]
    fact: ObservedFact
    analysis: str = Field(min_length=1, max_length=4000)
    repository_citations: tuple[Citation, ...] = Field(default=(), max_length=8)
    uncertainty: str = Field(min_length=1, max_length=2000)
    recommendation: str = Field(min_length=1, max_length=3000)
    handling: Literal["SELF_REFINE_RETRY_REGENERATE", "EVOLUTION_WORK_PROPOSAL",
                      "BLOCK_AND_ESCALATE", "INVESTIGATE"] = Field(description=
        "Required mapping: RUNTIME_MODEL_VARIANCE -> SELF_REFINE_RETRY_REGENERATE; "
        "SYSTEM_CAPABILITY_DEFECT -> EVOLUTION_WORK_PROPOSAL; "
        "GOVERNANCE_ISSUE -> BLOCK_AND_ESCALATE; UNKNOWN -> INVESTIGATE.")
    regression_qualification: str = Field(min_length=1, max_length=3000)

    @model_validator(mode="after")
    def preserve_governance_boundary(self):
        handling = {
            IssueClass.RUNTIME_MODEL_VARIANCE: "SELF_REFINE_RETRY_REGENERATE",
            IssueClass.SYSTEM_CAPABILITY_DEFECT: "EVOLUTION_WORK_PROPOSAL",
            IssueClass.GOVERNANCE_ISSUE: "BLOCK_AND_ESCALATE",
            IssueClass.UNKNOWN: "INVESTIGATE",
        }
        if self.handling != handling[self.classification]:
            raise ValueError("handling must preserve the issue classification boundary")
        if not self.repository_citations and self.epistemic_status != "UNKNOWN":
            raise ValueError("a root cause hypothesis requires repository evidence")
        return self


class Recommendation(AnalysisRecord):
    statement: str = Field(min_length=1, max_length=3000)
    finding_ids: tuple[str, ...] = Field(min_length=1, max_length=20)


class AnalysisReport(AnalysisRecord):
    schema_version: Literal["watt-trace-analysis-report-v2"] = "watt-trace-analysis-report-v2"
    work_id: UUID
    original_objective: ObservedFact
    expected_outcome: ObservedFact
    actual_execution_path: ObservedFact
    current_state: ObservedFact
    timeline: tuple[TimelineItem, ...] = Field(min_length=1, max_length=80)
    findings: tuple[Finding, ...] = Field(default=(), max_length=30)
    immediate_recovery: tuple[Recommendation, ...] = Field(default=(), max_length=20)
    self_refine_opportunities: tuple[Recommendation, ...] = Field(default=(), max_length=20)
    platform_improvements: tuple[Recommendation, ...] = Field(default=(), max_length=20)
    deferred_items: tuple[Recommendation, ...] = Field(default=(), max_length=20)
    evidence_assessments: tuple[EvidenceAssessment, ...] = Field(max_length=8,
        description="Reconcile every family in the seeded evidence_reality summary with its exact check_id and availability. These are snapshot observations, not completeness or causal truth.")
    missing_evidence: tuple[EvidenceGap, ...] = Field(default=(), max_length=60,
        description="Every absence/incompleteness claim needs a prior evidence.check receipt for the same family. PRESENT evidence cannot be called missing; NOT_OBSERVED is limited to the checked snapshot scope. Put source/comparison limitations in uncertainty, not invented absence claims.")

    @model_validator(mode="after")
    def recommendation_lineage(self):
        ids = {finding.finding_id for finding in self.findings}
        if len(ids) != len(self.findings):
            raise ValueError("finding identities must be unique")
        for section in (self.immediate_recovery, self.self_refine_opportunities,
                        self.platform_improvements, self.deferred_items):
            for item in section:
                if not set(item.finding_ids).issubset(ids):
                    raise ValueError("recommendation references an unknown finding")
        return self


class AnalysisTrigger(AnalysisRecord):
    request_id: UUID
    rationale: str = Field(min_length=1, max_length=2000)
