"""Advisory investigation contracts. They confer no production authority."""
from enum import StrEnum
import re
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

    @model_validator(mode="after")
    def fact_requires_original_observation(self):
        if self.statement.strip() in {"CHECKED_FIELD_SCOPE", "INSPECTED_OWNER_BOUNDARY", "ORIGINAL_OWNER_TIME_BOUNDARY"}:
            raise ValueError("FACT_REQUIRES_ORIGINAL_OBSERVATION; boundary markers belong only to checked analysis/uncertainty/assessment fields. Describe the cited original positive fields, not a placeholder; factual prose is never automatically repaired.")
        return self


class TimelineItem(ObservedFact):
    stage: Literal["INTENT", "CONTEXT", "PLANNING", "EXECUTION", "VERIFICATION",
                   "FAILURE", "RECOVERY_REFINEMENT", "FINAL_STATE"]
    timestamp: str | None = Field(default=None, description="Original event time only. Composite stage summaries have no single timestamp. Dated entries must be ordered chronologically, regardless of stage.")
    timestamp_evidence_id: UUID | None = Field(default=None, description="Observed original Owner record whose time is used; must be cited. Other citations of a dated event must be explicitly associated with this record.")
    timestamp_field: Literal["created_at", "updated_at", "started_at", "finished_at", "sealed_at", "assessed_at", "committed_at", "timestamp"] | None = Field(default=None, description="Exact top-level original Owner timestamp field, not an invented stage-wide time.")
    time_interpretation: str | None = Field(default=None, description="For dated entries use ORIGINAL_OWNER_TIME_BOUNDARY or the exact evidence.read time_boundaries[timestamp_field]; presentation derives from the validated original field. Creation time cannot establish later snapshot state or recovery completion. Undated entries use null.")

    @model_validator(mode="after")
    def recorded_time_requires_source(self):
        if self.timestamp is None:
            if self.timestamp_evidence_id is not None or self.timestamp_field is not None:
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
        description="For findings about unavailable fields, cite performed checks. Such findings are UNKNOWN and analysis must be CHECKED_FIELD_SCOPE or the exact checked bounded_conclusion. PRESENT checks cannot establish a missing field. Do not use them to infer global/history absence.")
    classification: IssueClass
    epistemic_status: Literal["ROOT_CAUSE_HYPOTHESIS", "UNKNOWN"]
    fact: ObservedFact
    analysis: str = Field(min_length=1, max_length=4000,
        description="ROOT_CAUSE_HYPOTHESIS must start with '假设：若' and use conditional causal language. Owner diagnosis/expected/rejected-behavior lists are not proof of executed effects or an unavailable candidate's contents.")
    repository_citations: tuple[Citation, ...] = Field(default=(), max_length=8,
        description="Root cause hypotheses require EXACT_IMPLEMENTATION_READ from repository.read of the relevant implementation and its surrounding control flow. Search locates code; a single matching line and a final diff cannot alone ground a validation/recording mechanism. Keep the cause UNKNOWN without implementation evidence.")
    uncertainty: str = Field(min_length=1, max_length=12000,
        description="Use INSPECTED_OWNER_BOUNDARY. The verifier derives presentation text only from the registered subject inspection and uncertainty_check_ids. Exact canonical boundary text is also accepted. No free-form absence claims.")
    recommendation: str = Field(min_length=1, max_length=3000)
    handling: Literal["SELF_REFINE_RETRY_REGENERATE", "EVOLUTION_WORK_PROPOSAL",
                      "BLOCK_AND_ESCALATE", "INVESTIGATE"] = Field(description=
        "Required mapping: RUNTIME_MODEL_VARIANCE -> SELF_REFINE_RETRY_REGENERATE; "
        "SYSTEM_CAPABILITY_DEFECT -> EVOLUTION_WORK_PROPOSAL; "
        "GOVERNANCE_ISSUE -> BLOCK_AND_ESCALATE; UNKNOWN -> INVESTIGATE.")
    regression_scenario: str = Field(default="", max_length=2000,
        description="Describe an adversarial/recovery scenario, not a promise of zero future failures.")
    regression_qualification: str = Field(min_length=1, max_length=3000,
        description="Copy the criterion for classification exactly: " + str({k.value: v for k, v in REGRESSION_CRITERIA.items()}))

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
        if self.epistemic_status == "ROOT_CAUSE_HYPOTHESIS" and not self.analysis.startswith("假设：若"):
            raise ValueError("CAUSAL_HYPOTHESIS_MUST_BE_EXPLICIT; begin analysis with 假设：若, state a conditional mechanism, and do not promote diagnoses or repair plans to performed actions")
        if self.epistemic_status == "ROOT_CAUSE_HYPOTHESIS" and re.search(r"重做|重新生成|重新推理|替代配方|\b(?:regenerat\w*|retr(?:y|ied|ies)|replacement\s+recipe)\b", self.analysis, re.I):
            raise ValueError("CAUSE_MECHANISM_CANNOT_ASSERT_RECOVERY_ACTION; describe only the failure/recording condition here. Proposed recovery belongs in recommendations; performed recovery needs its own original fact receipts.")
        if self.epistemic_status == "ROOT_CAUSE_HYPOTHESIS" and re.search(
                r"本次|此次|随后|实际(?:执行|运行|加载|使用)|历史(?:执行|运行|加载|使用)|"
                r"\bthis\s+(?:work|run|incident)\b|\b(?:then|actually)\s+(?:executed|loaded|used)\b",
                self.analysis, re.I):
            raise ValueError("CAUSE_MECHANISM_CANNOT_NARRATE_HISTORICAL_EXECUTION; keep analysis a conditional implementation comparison. Put original-event observations in cited facts; an isolation/host label does not identify historical loaded code.")
        if self.regression_qualification != REGRESSION_CRITERIA[self.classification]:
            raise ValueError("REGRESSION_CRITERION_MUST_MATCH_GOVERNED_OUTCOME: " + REGRESSION_CRITERIA[self.classification])
        if self.scope_check_ids and (self.classification != IssueClass.UNKNOWN or self.epistemic_status != "UNKNOWN"):
            raise ValueError("checked capture limitations cannot establish a platform defect or root cause")
        return self


class Recommendation(AnalysisRecord):
    statement: str = Field(min_length=1, max_length=3000)
    evidence_family: EvidenceFamily = Field(description="Declare the recommendation topic surface. Each cited finding subject must belong to this family. Download/client-transfer suggestions use DELIVERY_TRANSFER; preview suggestions use PREVIEW_HTTP; general Owner/source suggestions use OWNER_RECORD. Do not borrow an unrelated finding.")
    finding_ids: tuple[str, ...] = Field(min_length=1, max_length=20)


class AnalysisReport(AnalysisRecord):
    schema_version: Literal["watt-trace-analysis-report-v6"] = "watt-trace-analysis-report-v6"
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
        description="Reconcile every family with its exact check_id and availability. Use CHECKED_FIELD_SCOPE as statement; presentation derives from that performed check. These are snapshot observations, not completeness or causal truth.")
    missing_evidence: tuple[EvidenceGap, ...] = Field(default=(), max_length=60,
        description="Use CHECKED_FIELD_SCOPE; the verifier materializes its performed check boundary. Every absence/incompleteness claim needs a prior evidence.check receipt for the same family. PRESENT evidence cannot be called missing; NOT_OBSERVED is limited to the checked snapshot scope. Put source/comparison limitations in uncertainty, not invented absence claims.")

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
