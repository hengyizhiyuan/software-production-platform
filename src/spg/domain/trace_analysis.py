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


REGRESSION_CRITERIA = {
    IssueClass.RUNTIME_MODEL_VARIANCE: "在既有权限和预算内恢复，或受治理地终止；不要求未来随机失败次数为零。",
    IssueClass.SYSTEM_CAPABILITY_DEFECT: "在已准入范围内验证能力修复，保留证据、权限与来源门禁。",
    IssueClass.GOVERNANCE_ISSUE: "拒绝越权或证据无效的动作并按契约升级，不以绕过门禁作为通过。",
    IssueClass.UNKNOWN: "核对原始记录、关联与已检查范围；证据不足时保留 UNKNOWN，不扩大结论。",
}


class Citation(AnalysisRecord):
    evidence_id: UUID
    quote: str | None = Field(default=None, min_length=1, max_length=1200)
    field: str | None = Field(default=None, max_length=500,
        description="Alternative to copying a quote: JSON Pointer to an original Owner or admitted exact-repository tool value already fully read. Derived lookups and model drafts are not original evidence. The service derives observed_value; this does not establish the prose conclusion or historical loaded source.")
    observed_value: str | None = Field(default=None, description="Service-derived original serialized value excerpt; not a model-created quotation.")
    observed_value_truncated: bool = Field(default=False)

    @model_validator(mode="after")
    def reference_requires_quote_or_field(self):
        if self.quote is None and self.field is None:
            raise ValueError("CITATION_REQUIRES_QUOTE_OR_ORIGINAL_FIELD_REFERENCE")
        return self


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
    checked_boundary: str = Field(default="", description="Service-derived scope receipt; not a historical event or model assertion.")


class EvidenceGap(AnalysisRecord):
    statement: str = Field(min_length=1, max_length=2000)
    family: EvidenceFamily
    check_id: UUID
    availability: Literal["NOT_OBSERVED_IN_CAPTURE", "INCOMPLETE_CAPTURE"]
    checked_boundary: str = Field(default="", description="Service-derived scope receipt; unexported does not establish historical loss.")


class ObservedFact(AnalysisRecord):
    statement: str = Field(min_length=1, max_length=2000)
    citations: tuple[Citation, ...] = Field(min_length=1, max_length=8)
    evidence_family: EvidenceFamily = Field(default=EvidenceFamily.OWNER_RECORD,
        description="Declare PREVIEW_HTTP for preview GET/status/digest claims, DELIVERY_TRANSFER for download audits, EXECUTION_RELATIONSHIP for identity linkage. Citation text from another surface cannot prove this fact.")



class TimelineItem(ObservedFact):
    stage: Literal["INTENT", "CONTEXT", "PLANNING", "EXECUTION", "VERIFICATION",
                   "FAILURE", "RECOVERY_REFINEMENT", "FINAL_STATE"]
    timestamp: str | None = Field(default=None, description="Original event time only. Provide an exact value OR omit it with paired timestamp_evidence_id/timestamp_field to derive the observed original value. Wrong explicit values are rejected. Composite summaries omit all time references.")
    timestamp_evidence_id: UUID | None = Field(default=None, description="Observed original Owner record whose time is used; must be cited. Other citations of a dated event must be explicitly associated with this record.")
    timestamp_field: Literal["created_at", "updated_at", "started_at", "finished_at", "sealed_at", "assessed_at", "committed_at", "timestamp"] | None = Field(default=None, description="Exact top-level original Owner timestamp field, not an invented stage-wide time.")
    time_interpretation: str | None = Field(default=None, description="Explain the meaning of this observed Owner time in your own words; do not infer a later transition from row creation.")
    owner_time_boundary: str | None = Field(default=None, description="Service-derived neutral meaning of the validated original timestamp field.")

    @model_validator(mode="after")
    def recorded_time_requires_source(self):
        if self.timestamp is None:
            if (self.timestamp_evidence_id is None) != (self.timestamp_field is None):
                raise ValueError("TIMELINE_SUMMARY_HAS_NO_SINGLE_EVENT_TIME")
        elif self.timestamp_evidence_id is None or self.timestamp_field is None:
            raise ValueError("TIMELINE_TIME_REQUIRES_ORIGINAL_OWNER_FIELD")
        return self


class Finding(AnalysisRecord):
    finding_id: str = Field(min_length=1, max_length=80)
    subject_evidence_id: UUID = Field(description="Original Owner record this finding is about. Fact citations must be this record or explicitly linked records; shared Work/attempt, similar errors or timestamps do not establish the same incident.")
    inspection_id: UUID = Field(description="Call evidence.inspect(subject_evidence_id) to read the original linked Owner fields, not merely relationship hints. Copy its inspection_id. An index snippet is insufficient.")
    uncertainty_check_ids: tuple[UUID, ...] = Field(default=(), max_length=4,
        description="Performed field checks relevant to this finding's uncertainty. Do not infer whole-response or historical absence from them.")
    scope_check_ids: tuple[UUID, ...] = Field(default=(), max_length=4,
        description="Performed gap checks relevant to this finding. Their retrieval limits do not establish a cause or defect; independent positive facts/source may support other parts of the finding. PRESENT checks cannot establish a missing field. Explain uncertainty without broadening the checked scope.")
    classification: IssueClass
    epistemic_status: Literal["ROOT_CAUSE_HYPOTHESIS", "UNKNOWN"]
    fact: ObservedFact
    analysis: str = Field(min_length=1, max_length=4000,
        description="Explain a conditional cause comparison in any semantically equivalent wording; epistemic_status carries the hypothesis boundary. Owner diagnosis/expected/rejected-behavior lists are not proof of executed effects or an unavailable candidate's contents.")
    repository_citations: tuple[Citation, ...] = Field(default=(), max_length=8,
        description="Root cause hypotheses require EXACT_IMPLEMENTATION_READ from repository.read of the relevant implementation and its surrounding control flow. Search locates code; a single matching line and a final diff cannot alone ground a validation/recording mechanism. Keep the cause UNKNOWN without implementation evidence.")
    uncertainty: str = Field(min_length=1, max_length=12000,
        description="Explain uncertainty in your own words. Service-derived checked_boundaries preserve exact retrieval scope separately; do not broaden that scope into historical absence.")
    checked_boundaries: tuple[str, ...] = Field(default=(), description="Service-derived inspection/check receipts; never an independent historical fact.")
    recommendation: str = Field(min_length=1, max_length=3000)
    handling: Literal["SELF_REFINE_RETRY_REGENERATE", "EVOLUTION_WORK_PROPOSAL",
                      "BLOCK_AND_ESCALATE", "INVESTIGATE"] = Field(description=
        "Required mapping: RUNTIME_MODEL_VARIANCE -> SELF_REFINE_RETRY_REGENERATE; "
        "SYSTEM_CAPABILITY_DEFECT -> EVOLUTION_WORK_PROPOSAL; "
        "GOVERNANCE_ISSUE -> BLOCK_AND_ESCALATE; UNKNOWN -> INVESTIGATE.")
    regression_scenario: str = Field(default="", max_length=2000,
        description="Describe an adversarial/recovery scenario, not a promise of zero future failures.")
    regression_qualification: str = Field(min_length=1, max_length=3000,
        description="Describe permission/budget-bounded recovery or governed termination in your own words; model variance does not require zero future errors. Guidance: " + str({k.value: v for k, v in REGRESSION_CRITERIA.items()}))

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
    evidence_family: EvidenceFamily = Field(description="Declare the recommendation topic surface. Each cited finding subject must belong to this family. Download/client-transfer suggestions use DELIVERY_TRANSFER; preview suggestions use PREVIEW_HTTP; general Owner/source suggestions use OWNER_RECORD. Do not borrow an unrelated finding.")
    finding_ids: tuple[str, ...] = Field(min_length=1, max_length=20)


class AnalysisReport(AnalysisRecord):
    schema_version: Literal["watt-trace-analysis-report-v8"] = "watt-trace-analysis-report-v8"
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
        description="Reconcile every family with its exact check_id and availability. Describe the performed check in any equivalent wording; checked_boundary is derived separately. These are snapshot observations, not completeness or causal truth.")
    missing_evidence: tuple[EvidenceGap, ...] = Field(default=(), max_length=60,
        description="Describe the gap in your own words; checked_boundary preserves the performed lookup scope separately. Every absence/incompleteness claim needs a prior evidence.check receipt for the same family. PRESENT evidence cannot be called missing; NOT_OBSERVED is limited to the checked snapshot scope. Put source/comparison limitations in uncertainty, not invented absence claims.")

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
