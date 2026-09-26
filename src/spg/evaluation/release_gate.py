"""Executable, domain-separated acceptance corpus for a candidate Watt version."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic
from uuid import uuid4
from xml.etree import ElementTree

from sqlalchemy import create_engine, insert, select
from spg.infrastructure.persistence.evaluation_schema import evaluation_runs


ROOT = Path(__file__).resolve().parents[3]
CORPUS_VERSION = "watt-p1-v1"


@dataclass(frozen=True)
class EvaluationCase:
    identity: str
    domain: str
    selector: str
    expected_outcome: str = "FIRST_PASS_SUCCESS"
    critical: bool = True
    capability_family: str = "GENERAL"
    failure_family: str | None = None
    protected_invariant: str | None = None
    risk: str = "HIGH"
    scenario_type: str = "REGRESSION"
    origin: str = "REGRESSION"
    duplicate_group: str | None = None
    required_environment: str = "POSTGRESQL"
    estimated_cost_seconds: int = 60
    last_failure: str | None = None
    last_meaningful_regression: str | None = None
    baseline_version: str = "8-plus-1-v1"

    def __post_init__(self) -> None:
        if self.risk not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise ValueError("evaluation risk must be LOW, MEDIUM, HIGH or CRITICAL")
        if self.origin not in {"DOGFOOD", "REGRESSION", "SYNTHETIC", "EXTERNAL"}:
            raise ValueError("evaluation origin is not governed")
        if self.required_environment not in {"PYTHON", "POSTGRESQL", "REAL_CONTAINER"}:
            raise ValueError("evaluation environment is not governed")
        if self.estimated_cost_seconds < 1:
            raise ValueError("estimated execution cost must be positive")
        if not self.protected_invariant:
            object.__setattr__(self, "protected_invariant", self.identity)


CORPUS = (
    EvaluationCase("GJ-SR-01", "PRODUCTION", "tests/integration/test_wic_governed_work_admission.py::test_governed_branch_operation_preserves_main_and_binds_exact_commit"),
    EvaluationCase("REPOSITORY_REALITY", "INTERACTION", "tests/integration/test_wic_governed_work_admission.py::test_explicit_repository_action_automatically_executes_governed_admission"),
    EvaluationCase("DESIGN_BEFORE_CODE", "PRODUCTION", "tests/integration/test_wic_governed_work_admission.py::test_guided_design_rejects_implementation_before_design_artifact_exists"),
    EvaluationCase("RESPONSE_OPERATION_REALITY", "INTERACTION", "tests/integration/test_wic_governed_work_admission.py::test_repository_acquisition_persists_requested_then_running_before_git_effect"),
    EvaluationCase("ACQUISITION_RECOVERY", "RESILIENCE", "tests/integration/test_wic_governed_work_admission.py::test_failed_repository_acquisition_reuses_work_and_retries_with_new_attempt"),
    EvaluationCase("SEMANTIC_AUTHORITY", "INTERACTION", "tests/integration/test_wic_governed_work_admission.py::test_engineering_semantic_truth_persists_and_explicit_correction_versions_work"),
    EvaluationCase("SELF_REFINE_RECOVERY", "RESILIENCE", "tests/integration/test_native_executor_runtime.py::test_self_refine_records_failure_repair_and_verified_resume", "RECOVERED_BY_SELF_REFINE"),
    EvaluationCase("STRUCTURAL_REPAIR", "RESILIENCE", "tests/integration/test_native_executor_runtime.py::test_structural_decision_repair_is_durable_and_recovers_same_attempt", "RECOVERED_BY_SELF_REFINE"),
    EvaluationCase("REAL_CONTAINER_REPAIR", "RESILIENCE", "tests/integration/test_brownfield_native_production_flow.py::test_real_work_task_contract_pwu_native_pe_preview_and_authorization[True]", "RECOVERED_BY_SELF_REFINE"),
    EvaluationCase("SELF_CONVERGE", "RESILIENCE", "tests/integration/test_native_executor_runtime.py::test_self_converge_stops_repeated_unchanged_failure", "ESCALATED_TO_HUMAN"),
    EvaluationCase("RESTART_RESUME", "RESILIENCE", "tests/integration/test_native_executor_runtime.py::test_expired_worker_before_any_step_restarts_same_attempt_with_new_epoch"),
    EvaluationCase("NO_EXTERNAL_AGENT", "ASSURANCE", "tests/test_no_external_coding_agent_runtime.py"),
    EvaluationCase("HUMAN_RESPONSE", "INTERACTION", "tests/test_wic_response_contract_expression.py"),
    EvaluationCase("CONNECTOR_SCOPE", "PRODUCTION", "tests/test_git_operation_recipes.py"),
    EvaluationCase("HUMAN_DELIVERY_AUTHORITY", "ASSURANCE", "tests/integration/test_software_delivery.py::test_exact_candidate_is_previewable_before_repository_authorization"),
    EvaluationCase("GATE_FAILS_REGRESSION", "ASSURANCE", "tests/test_release_evaluation_gate.py"),
    EvaluationCase(
        "BUSINESS_ORACLE_REPAIR", "RESILIENCE",
        "tests/integration/test_native_executor_runtime.py::test_explicit_business_oracle_repairs_verifies_and_resumes_without_human",
        "RECOVERED_BY_SELF_REFINE", capability_family="SELF_REFINE",
        failure_family="VERIFICATION_FAILURE", protected_invariant="explicit admitted business oracle can be repaired without Human",
        risk="CRITICAL", scenario_type="CONTROLLED_FAILURE", origin="REGRESSION",
        estimated_cost_seconds=120,
    ),
    EvaluationCase(
        "AMBIGUOUS_BUSINESS_TRUTH", "ASSURANCE",
        "tests/integration/test_native_executor_runtime.py::test_ambiguous_business_truth_escalates_without_code_mutation",
        "ESCALATED_TO_HUMAN", capability_family="HUMAN_GOVERNANCE",
        failure_family="PRODUCT_AMBIGUITY", protected_invariant="ambiguous Product Truth cannot be invented by repair",
        risk="CRITICAL", scenario_type="CONTROLLED_FAILURE", origin="REGRESSION",
        estimated_cost_seconds=90,
    ),
    EvaluationCase(
        "COMPILER_DIAGNOSTIC_PROMOTION", "RESILIENCE",
        "tests/integration/test_native_executor_runtime.py::test_compiler_diagnostic_requires_source_evidence_before_bounded_repair",
        "EVIDENCE_SUFFICIENT_FOR_REPAIR", capability_family="SELF_REFINE",
        failure_family="DEPENDENCY_BUILD_FAILURE",
        protected_invariant="compiler finding requires admitted source evidence before repair",
        risk="CRITICAL", scenario_type="CONTROLLED_FAILURE", origin="REGRESSION",
        estimated_cost_seconds=90,
    ),
    EvaluationCase(
        "TRANSIENT_HEALTH_NOISE", "RESILIENCE",
        "tests/integration/test_native_executor_runtime.py::test_transient_health_noise_resolves_without_self_refine",
        capability_family="SELF_OBSERVE", failure_family="RUNTIME_HEALTH",
        protected_invariant="one transient health timeout does not start Self-Refine",
        scenario_type="CONTROLLED_FAILURE", estimated_cost_seconds=45,
    ),
    EvaluationCase(
        "CONFIRMED_HEALTH_FAILURE", "RESILIENCE",
        "tests/integration/test_native_executor_runtime.py::test_stable_health_failure_is_confirmed_before_self_refine",
        capability_family="SELF_OBSERVE", failure_family="RUNTIME_HEALTH",
        protected_invariant="stable health failure starts evidence-backed Self-Refine",
        scenario_type="CONTROLLED_FAILURE", estimated_cost_seconds=45,
    ),
    EvaluationCase(
        "AUTHORITATIVE_REALITY_MISMATCH", "RESILIENCE",
        "tests/integration/test_native_executor_runtime.py::test_authoritative_git_mismatch_is_confirmed_without_debounce",
        capability_family="SELF_OBSERVE", failure_family="REPOSITORY_REALITY_MISMATCH",
        protected_invariant="authoritative Git mismatch is not debounced",
        scenario_type="CONTROLLED_FAILURE", estimated_cost_seconds=45,
    ),
    EvaluationCase(
        "SR-Q1", "PRODUCTION",
        "tests/integration/test_wic_governed_work_admission.py::test_governed_branch_operation_preserves_main_and_binds_exact_commit",
        capability_family="SEMANTIC_TRUTH", protected_invariant="provider representation variance still produces exact branch operation through canonical binding",
        risk="CRITICAL", scenario_type="GOLDEN_JOURNEY", required_environment="REAL_CONTAINER",
        baseline_version="self-refine-v2", estimated_cost_seconds=180,
    ),
    EvaluationCase(
        "SR-Q2", "INTERACTION",
        "tests/test_wic_progressive_intelligence.py::test_question_policy_ranks_high_impact_boundary_above_lower_value_scope_detail",
        capability_family="WIC", protected_invariant="high-impact ambiguity consumes only minimum-sufficient question budget",
        required_environment="PYTHON", baseline_version="self-refine-v2", estimated_cost_seconds=10,
    ),
    EvaluationCase(
        "SR-Q3", "PRODUCTION",
        "tests/integration/test_mvp_semantic_step_execution.py::test_semantic_admission_conflict_refines_once_on_same_basis_and_records_routine",
        "RECOVERED_BY_SELF_REFINE", capability_family="STEERING",
        protected_invariant="rejected semantic plan candidate is revised on unchanged Reality before admission",
        baseline_version="self-refine-v2", estimated_cost_seconds=30,
    ),
    EvaluationCase(
        "SR-Q4", "PRODUCTION",
        "tests/integration/test_connector_capabilities.py::test_missing_quality_connector_qualifies_and_resumes_same_work",
        capability_family="CONNECTOR", protected_invariant="missing capability cannot enter executable Task Contract without qualified connector and original Work resume",
        baseline_version="self-refine-v2", estimated_cost_seconds=60,
    ),
    EvaluationCase(
        "SR-Q5", "RESILIENCE",
        "tests/integration/test_brownfield_native_production_flow.py::test_real_work_task_contract_pwu_native_pe_preview_and_authorization[True]",
        "RECOVERED_BY_SELF_REFINE", capability_family="SELF_REFINE",
        protected_invariant="real container candidate repair remains bounded and verified",
        required_environment="REAL_CONTAINER", baseline_version="self-refine-v2", estimated_cost_seconds=240,
    ),
    EvaluationCase(
        "SR-Q6", "ASSURANCE",
        "tests/integration/test_s3b_verification_satisfaction.py::test_s3b_12_old_snapshot_pass_cannot_satisfy_new_snapshot",
        capability_family="VERIFICATION", protected_invariant="PASS for wrong exact revision cannot satisfy current production",
        risk="CRITICAL", baseline_version="self-refine-v2", estimated_cost_seconds=45,
    ),
    EvaluationCase(
        "SR-Q7", "RESILIENCE",
        "tests/integration/test_native_executor_runtime.py::test_self_converge_stops_repeated_unchanged_failure",
        "ESCALATED_TO_HUMAN", capability_family="SELF_CONVERGE",
        protected_invariant="unchanged failure stops retry and preserves incident evidence",
        risk="CRITICAL", baseline_version="self-refine-v2", estimated_cost_seconds=45,
    ),
    EvaluationCase(
        "SR-Q8", "ASSURANCE",
        "tests/integration/test_mvp_semantic_step_execution.py::test_semantic_authority_expansion_does_not_receive_automatic_refinement",
        capability_family="HUMAN_GOVERNANCE", protected_invariant="candidate correction cannot auto-expand Human constraints",
        risk="CRITICAL", baseline_version="self-refine-v2", estimated_cost_seconds=30,
    ),
    EvaluationCase(
        "SR-Q9", "PRODUCTION",
        "tests/test_git_operation_recipes.py::test_git_recipe_rejects_widening",
        capability_family="DETERMINISTIC_EVIDENCE", protected_invariant="Git recipe rejects widening without model reflection inside primitive",
        required_environment="PYTHON", baseline_version="self-refine-v2", estimated_cost_seconds=10,
    ),
    EvaluationCase(
        "SR-Q10", "RESILIENCE",
        "tests/integration/test_native_executor_runtime.py::test_routine_refinement_recurrence_promotes_economic_signal_without_incident",
        capability_family="SELF_REFINE", protected_invariant="successful recurring correction produces cost and improvement signal without each Work becoming incident",
        baseline_version="self-refine-v2", estimated_cost_seconds=30,
    ),
    EvaluationCase(
        "SEARCH-Q1", "INTERACTION",
        "tests/integration/test_external_search_interaction.py::test_explicit_search_uses_connector_and_persists_source_evidence",
        capability_family="EXTERNAL_RESEARCH", protected_invariant="explicit GitHub search executes through Connector and persists inspected source Evidence",
        baseline_version="external-search-v1", estimated_cost_seconds=20,
    ),
    EvaluationCase(
        "SEARCH-Q2", "INTERACTION",
        "tests/test_external_research.py::test_brave_search_parses_real_api_shape_and_fetches_page_separately",
        capability_family="EXTERNAL_RESEARCH", protected_invariant="Web search snippet and fetched page remain distinct source observations",
        required_environment="PYTHON", baseline_version="external-search-v1", estimated_cost_seconds=5,
    ),
    EvaluationCase(
        "SEARCH-Q3", "INTERACTION",
        "tests/integration/test_external_search_interaction.py::test_combined_github_web_search_merges_real_provider_shapes_without_duplicate_claims",
        capability_family="EXTERNAL_RESEARCH", protected_invariant="GitHub and Web results merge into one sourced answer without duplicate evidence",
        baseline_version="external-search-v1", estimated_cost_seconds=20,
    ),
    EvaluationCase(
        "SEARCH-Q4", "INTERACTION",
        "tests/test_external_research.py::test_model_information_gap_can_request_governed_search_then_resume_with_evidence",
        capability_family="EXTERNAL_RESEARCH", protected_invariant="structured model information gap becomes governed read capability and grounded synthesis",
        required_environment="PYTHON", baseline_version="external-search-v1", estimated_cost_seconds=5,
    ),
    EvaluationCase(
        "SEARCH-Q5", "INTERACTION",
        "tests/test_external_research.py::test_query_refines_once_and_stops_on_repeated_evidence",
        capability_family="EXTERNAL_RESEARCH", protected_invariant="weak query broadens once without creating an incident or infinite search",
        required_environment="PYTHON", baseline_version="external-search-v1", estimated_cost_seconds=5,
    ),
    EvaluationCase(
        "SEARCH-Q6", "ASSURANCE",
        "tests/test_external_research.py::test_rate_limited_research_response_preserves_failure_category",
        capability_family="EXTERNAL_RESEARCH", failure_family="RATE_LIMITED",
        protected_invariant="provider limit is not reported as absence of implementations",
        required_environment="PYTHON", baseline_version="external-search-v1", estimated_cost_seconds=5,
    ),
    EvaluationCase(
        "SEARCH-Q7", "ASSURANCE",
        "tests/test_external_research.py::test_web_credential_boundary_preserves_github_results_and_truthful_failure",
        capability_family="EXTERNAL_RESEARCH", failure_family="CREDENTIAL_REQUIRED",
        protected_invariant="missing Web credential does not hide public GitHub evidence or expand authority",
        required_environment="PYTHON", baseline_version="external-search-v1", estimated_cost_seconds=5,
    ),
    EvaluationCase(
        "SEARCH-Q8", "ASSURANCE",
        "tests/integration/test_external_search_interaction.py::test_explicit_search_uses_connector_and_persists_source_evidence",
        capability_family="EXTERNAL_RESEARCH", protected_invariant="final source claims retain persisted URL and Evidence identity",
        baseline_version="external-search-v1", estimated_cost_seconds=20,
    ),
    EvaluationCase(
        "SEARCH-Q9", "RESILIENCE",
        "tests/test_external_research.py::test_query_refines_once_and_stops_on_repeated_evidence",
        capability_family="EXTERNAL_RESEARCH", protected_invariant="equivalent repeated results stop within bounded query budget",
        required_environment="PYTHON", baseline_version="external-search-v1", estimated_cost_seconds=5,
    ),
    EvaluationCase(
        "P1-Q1", "PRODUCTION",
        "tests/integration/test_mvp_api.py::test_p1_q1_product_continues_across_three_distinct_works",
        capability_family="PRODUCT_CONTINUITY", protected_invariant="one Product retains three independent Work histories and exact repository asset",
        scenario_type="GOLDEN_JOURNEY", baseline_version="p1-v1", estimated_cost_seconds=20,
    ),
    EvaluationCase(
        "P1-Q2", "PRODUCTION",
        "tests/integration/test_dcp2_production_measurement.py::test_p1_q2_parallel_fan_in_economics_and_candidate_lineage",
        capability_family="PRODUCTION_ECONOMICS", protected_invariant="parallel fan-in reports exact PWU usage and separates wall from accumulated time",
        baseline_version="p1-v1", estimated_cost_seconds=20,
    ),
    EvaluationCase(
        "P1-Q3", "ASSURANCE",
        "tests/integration/test_github_governed_delivery.py::test_p1_q3_connector_disable_health_and_credential_rotation_are_governed",
        capability_family="CONNECTOR", protected_invariant="invalid credential fails closed and rotation preserves grant audit",
        baseline_version="p1-v1", estimated_cost_seconds=25,
    ),
    EvaluationCase(
        "P1-Q4", "PRODUCTION",
        "tests/integration/test_brownfield_native_production_flow.py::test_real_work_task_contract_pwu_native_pe_preview_and_authorization[False]",
        capability_family="BROWNFIELD", protected_invariant="existing project produces a verified native Candidate and governed delivery boundary under one Product",
        scenario_type="GOLDEN_JOURNEY", required_environment="REAL_CONTAINER",
        baseline_version="p1-v1", estimated_cost_seconds=240,
    ),
    EvaluationCase(
        "P1-Q4-INTAKE", "PRODUCTION",
        "tests/integration/test_p1_brownfield_product.py::test_p1_q4_brownfield_intake_product_work_and_delivery_boundary",
        capability_family="BROWNFIELD", protected_invariant="local existing Git project imports exact branch/revision and binds durable Product source",
        baseline_version="p1-v1", estimated_cost_seconds=30,
    ),
    EvaluationCase(
        "P1-Q5", "RESILIENCE",
        "tests/integration/test_native_executor_runtime.py::test_workspace_hibernation_respects_pins_and_restores_verified_bundle",
        capability_family="RETENTION", protected_invariant="evidence-referenced workspace survives while expired unreferenced workspace retires idempotently",
        baseline_version="p1-v1", estimated_cost_seconds=40,
    ),
    EvaluationCase(
        "P1-Q5-PREVIEW", "RESILIENCE",
        "tests/test_candidate_full_preview.py::test_p1_preview_retention_keeps_review_and_evidence_then_releases_runtime",
        capability_family="RETENTION", protected_invariant="pending review protects Preview and old reviewed runtime stops while immutable evidence survives",
        required_environment="PYTHON", baseline_version="p1-v1", estimated_cost_seconds=10,
    ),
    EvaluationCase(
        "P1-Q6", "PRODUCTION",
        "tests/integration/test_mvp_api.py::test_p1_q6_operator_diagnosis_identifies_capability_blocker",
        capability_family="OPERATIONS", protected_invariant="Work and platform views identify an observed capability blocker with evidence",
        baseline_version="p1-v1", estimated_cost_seconds=20,
    ),
    EvaluationCase(
        "P1-Q6-PREVIEW", "PRODUCTION",
        "tests/integration/test_mvp_api.py::test_p1_q6_operator_probe_detects_unhealthy_candidate_preview",
        capability_family="OPERATIONS", protected_invariant="operator diagnosis probes exact Candidate Preview health instead of trusting a persisted launch record",
        baseline_version="p1-v1", estimated_cost_seconds=20,
    ),
    EvaluationCase(
        "P1-Q7", "ASSURANCE",
        "tests/test_release_evaluation_gate.py::test_p1_q7_versioned_release_evaluation_compares_qualified_baseline",
        capability_family="EVALUATION", protected_invariant="versioned four-domain evaluation compares a qualified baseline without equating tests to Human acceptance",
        required_environment="PYTHON", baseline_version="p1-v1", estimated_cost_seconds=10,
    ),
    EvaluationCase(
        "P1-Q8", "INTERACTION",
        "tests/integration/test_mvp_api.py::test_p1_q8_product_history_survives_new_service_session",
        capability_family="LONG_HORIZON_HISTORY", protected_invariant="returning Human can inspect distinct governed Product Work facts across sessions",
        baseline_version="p1-v1", estimated_cost_seconds=20,
    ),
    EvaluationCase(
        "P1-Q9", "ASSURANCE",
        "tests/integration/test_p1_schema_hygiene.py::test_p1_q9_upgrade_p0_schema_preserves_work_and_alembic_check_passes",
        capability_family="SCHEMA", protected_invariant="forward P0 to P1 migration keeps unbound Work history and schema autogenerate clean",
        baseline_version="p1-v1", estimated_cost_seconds=30,
    ),
)

_BASELINE_METADATA = {
    "GJ-SR-01": dict(capability_family="PRODUCTION", protected_invariant="governed branch lineage stays bound to exact commit", risk="CRITICAL", scenario_type="GOLDEN_JOURNEY", origin="DOGFOOD", estimated_cost_seconds=120),
    "REPOSITORY_REALITY": dict(capability_family="WORK_ADMISSION", protected_invariant="repository request creates governed Work", estimated_cost_seconds=90),
    "DESIGN_BEFORE_CODE": dict(capability_family="PRODUCTION", protected_invariant="design prerequisite precedes implementation", estimated_cost_seconds=90),
    "RESPONSE_OPERATION_REALITY": dict(capability_family="SELF_OBSERVE", protected_invariant="conversation reflects persisted repository operation", estimated_cost_seconds=90),
    "ACQUISITION_RECOVERY": dict(capability_family="SELF_RESUME", failure_family="REPOSITORY_ACQUISITION", protected_invariant="failed acquisition resumes existing Work", estimated_cost_seconds=90),
    "SEMANTIC_AUTHORITY": dict(capability_family="HUMAN_GOVERNANCE", protected_invariant="explicit Human correction supersedes weaker meaning", risk="CRITICAL", estimated_cost_seconds=90),
    "SELF_REFINE_RECOVERY": dict(capability_family="SELF_REFINE", failure_family="PROVIDER_TRANSPORT", protected_invariant="failed attempt recovers under same admitted contract", duplicate_group="self-refine-recovery", estimated_cost_seconds=90),
    "STRUCTURAL_REPAIR": dict(capability_family="SELF_REFINE", failure_family="SEMANTIC_BINDING_FAILURE", protected_invariant="structural decision repair preserves authority", duplicate_group="self-refine-recovery", estimated_cost_seconds=90),
    "REAL_CONTAINER_REPAIR": dict(capability_family="SELF_REFINE", failure_family="IMPLEMENTATION_EFFECT_FAILURE", protected_invariant="real container repair produces verified Candidate", duplicate_group="self-refine-recovery", required_environment="REAL_CONTAINER", estimated_cost_seconds=240),
    "SELF_CONVERGE": dict(capability_family="SELF_CONVERGE", failure_family="REPEATED_FAILURE", protected_invariant="unchanged failure contracts retry budget", risk="CRITICAL", estimated_cost_seconds=90),
    "RESTART_RESUME": dict(capability_family="SELF_RESUME", failure_family="WORKER_LOSS", protected_invariant="restart resumes same Attempt without duplicate effect", estimated_cost_seconds=90),
    "NO_EXTERNAL_AGENT": dict(capability_family="PRODUCTION", protected_invariant="external coding-agent fallback remains absent", required_environment="PYTHON", estimated_cost_seconds=5),
    "HUMAN_RESPONSE": dict(capability_family="INTERACTION", protected_invariant="governed response remains consistent with Work", required_environment="PYTHON", estimated_cost_seconds=10),
    "CONNECTOR_SCOPE": dict(capability_family="PRODUCTION", protected_invariant="connector effects stay inside admitted scope", required_environment="PYTHON", estimated_cost_seconds=10),
    "HUMAN_DELIVERY_AUTHORITY": dict(capability_family="HUMAN_GOVERNANCE", protected_invariant="Candidate preview does not authorize delivery", risk="CRITICAL", estimated_cost_seconds=240),
    "GATE_FAILS_REGRESSION": dict(capability_family="SELF_EVALUATE", protected_invariant="critical regression fails release qualification", required_environment="PYTHON", estimated_cost_seconds=15),
}
CORPUS = tuple(
    replace(case, **_BASELINE_METADATA[case.identity])
    if case.identity in _BASELINE_METADATA else case
    for case in CORPUS
)


def select_cases(
    cases: tuple[EvaluationCase, ...] = CORPUS, *, purpose: str,
    capability_families: tuple[str, ...] = (), failure_families: tuple[str, ...] = (),
    minimum_risk: str = "LOW",
) -> tuple[EvaluationCase, ...]:
    """Select one governed purpose slice while preserving every critical invariant."""

    if purpose not in {"focused", "milestone", "release"}:
        raise ValueError("evaluation purpose must be focused, milestone or release")
    if minimum_risk not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        raise ValueError("minimum risk is not governed")
    if purpose == "focused" and not capability_families and not failure_families:
        raise ValueError("focused evaluation requires an affected capability or failure family")
    rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    candidates = [
        case for case in cases
        if rank[case.risk] >= rank[minimum_risk]
        and (
            (purpose == "release" and (case.critical or case.scenario_type == "GOLDEN_JOURNEY"))
            or (purpose == "milestone" and case.estimated_cost_seconds <= 180)
            or (purpose == "focused" and (
                case.capability_family in capability_families
                or case.failure_family in failure_families
            ))
        )
    ]
    selected: list[EvaluationCase] = []
    grouped: set[str] = set()
    for case in sorted(candidates, key=lambda item: (
        not item.critical, item.last_meaningful_regression is None,
        item.estimated_cost_seconds, item.identity,
    )):
        # Duplicate grouping only consolidates noncritical siblings; critical
        # invariants and Golden Journeys remain independently executable.
        if purpose == "milestone":
            group = f"{case.domain}:{case.capability_family}"
            if group in grouped:
                continue
            grouped.add(group)
        elif case.duplicate_group and not case.critical:
            if case.duplicate_group in grouped:
                continue
            grouped.add(case.duplicate_group)
        selected.append(case)
    return tuple(selected)


def run_case(case: EvaluationCase, *, root: Path = ROOT) -> dict:
    started = monotonic()
    with TemporaryDirectory(prefix="watt-evaluation-") as directory:
        report_path = Path(directory) / "result.xml"
        command = [
            sys.executable, "-m", "pytest", case.selector,
            "-q", "--disable-warnings", f"--junitxml={report_path}",
        ]
        completed = subprocess.run(
            command, cwd=root, capture_output=True, text=True, check=False,
            timeout=900, env=os.environ.copy(),
        )
        elapsed = monotonic() - started
        counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        if report_path.exists():
            tree = ElementTree.parse(report_path)
            suites = tree.findall(".//testsuite")
            if tree.getroot().tag == "testsuite":
                suites = [tree.getroot()]
            for suite in suites:
                for key in counts:
                    counts[key] += int(suite.get(key, "0"))
        passed = completed.returncode == 0 and counts["tests"] > 0 and counts["skipped"] == 0
        return {
            "case": case.identity,
            "domain": case.domain,
            "expected_outcome": case.expected_outcome,
            "result": case.expected_outcome if passed else "FAILED",
            "critical": case.critical,
            "counts": counts,
            "exit_code": completed.returncode,
            "elapsed_seconds": round(elapsed, 3),
            "failure_signature": None if passed else sha256(
                (completed.stdout + completed.stderr)[-2400:].encode("utf-8")
            ).hexdigest()[:24],
            "diagnostic_tail": "" if passed else (completed.stdout + completed.stderr)[-2400:],
            "metadata": {
                "capability_family": case.capability_family,
                "failure_family": case.failure_family,
                "protected_invariant": case.protected_invariant,
                "risk": case.risk,
                "scenario_type": case.scenario_type,
                "origin": case.origin,
                "duplicate_group": case.duplicate_group,
                "required_environment": case.required_environment,
                "estimated_cost_seconds": case.estimated_cost_seconds,
                "last_failure": (
                    datetime.now(timezone.utc).isoformat() if not passed else case.last_failure
                ),
                "last_meaningful_regression": case.last_meaningful_regression,
                "baseline_version": case.baseline_version,
            },
        }


def qualify(cases: tuple[EvaluationCase, ...] = CORPUS, *, root: Path = ROOT) -> dict:
    if (not cases or any(case.required_environment != "PYTHON" for case in cases)) and not os.environ.get("SPG_TEST_DATABASE_URL"):
        raise RuntimeError("SPG_TEST_DATABASE_URL is required; PostgreSQL cases must not silently skip")
    results = [run_case(case, root=root) for case in cases]
    domains = sorted({case.domain for case in cases})
    gate = all(not result["critical"] or result["result"] != "FAILED" for result in results)
    return {
        "corpus_version": CORPUS_VERSION,
        "qualification": "PASS" if gate else "FAIL",
        "domains": {
            domain: "PASS" if all(
                result["result"] != "FAILED" for result in results if result["domain"] == domain
            ) else "FAIL"
            for domain in domains
        },
        "cases": results,
        "recovered_case_count": sum(
            item["result"] == "RECOVERED_BY_SELF_REFINE" for item in results
        ),
    }


def evaluation_metrics(report: dict) -> dict:
    """Comparable observed dimensions; absent production telemetry remains unknown."""
    cases = report.get("cases", [])
    count = lambda outcome: sum(row["result"] == outcome for row in cases)
    durations = sorted(row["elapsed_seconds"] for row in cases
                       if isinstance(row.get("elapsed_seconds"), (int, float)))
    failures = sorted({row["failure_signature"] for row in cases
                       if row.get("failure_signature")})
    return {
        "case_count": len(cases),
        "first_pass_success": count("FIRST_PASS_SUCCESS"),
        "recovered_by_self_refine": count("RECOVERED_BY_SELF_REFINE"),
        "human_escalation": count("ESCALATED_TO_HUMAN"),
        "failure": count("FAILED"),
        "total_success": count("FIRST_PASS_SUCCESS") + count("RECOVERED_BY_SELF_REFINE"),
        "convergence_rate": None if not cases else round(
            (count("FIRST_PASS_SUCCESS") + count("RECOVERED_BY_SELF_REFINE")) / len(cases), 4),
        "average_case_seconds": None if not durations else round(sum(durations) / len(durations), 3),
        "p95_case_seconds": None if not durations else durations[max(0, (95 * len(durations) + 99) // 100 - 1)],
        "average_refinement_attempts": None,
        "p95_refinement_attempts": None,
        "token_usage": "UNREPORTED", "compute_usage": "UNREPORTED",
        "work_cost": "UNREPORTED",
        "failure_signatures": failures,
        "real_container_cases": sum(row.get("metadata", {}).get("required_environment") == "REAL_CONTAINER"
                                    for row in cases),
        "real_container_failures": sum(row.get("metadata", {}).get("required_environment") == "REAL_CONTAINER"
                                       and row["result"] == "FAILED" for row in cases),
    }


def compare_baseline(current: dict, previous: dict | None) -> dict:
    current_metrics = evaluation_metrics(current)
    if previous is None:
        return {"status": "NO_QUALIFIED_BASELINE", "current": current_metrics,
                "previous": None, "delta": None}
    previous_metrics = evaluation_metrics(previous)
    current_by_id = {row["case"]: row for row in current.get("cases", [])}
    previous_by_id = {row["case"]: row for row in previous.get("cases", [])}
    shared = sorted(current_by_id.keys() & previous_by_id.keys())
    comparable_current = evaluation_metrics({"cases": [current_by_id[key] for key in shared]})
    comparable_previous = evaluation_metrics({"cases": [previous_by_id[key] for key in shared]})
    dimensions = ("first_pass_success", "recovered_by_self_refine", "human_escalation",
                  "failure", "total_success", "convergence_rate",
                  "average_case_seconds", "p95_case_seconds")
    delta = {key: None if not shared or comparable_current[key] is None or comparable_previous[key] is None
             else round(comparable_current[key] - comparable_previous[key], 4) for key in dimensions}
    return {"status": "COMPARED" if current_by_id.keys() == previous_by_id.keys()
                      else "PARTIAL_COMPARISON", "current": current_metrics,
            "previous": previous_metrics, "delta": delta,
            "comparable_case_ids": shared,
            "new_case_ids": sorted(current_by_id.keys() - previous_by_id.keys()),
            "removed_case_ids": sorted(previous_by_id.keys() - current_by_id.keys()),
            "case_set_changed": current_by_id.keys() != previous_by_id.keys()}


def persist_evaluation(database_url: str, *, version: str, revision: str,
                       purpose: str, report: dict) -> dict:
    if not version.strip() or not revision.strip() or purpose not in {"focused", "milestone", "release"}:
        raise ValueError("Version, revision and governed purpose are required")
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            baseline = connection.execute(select(evaluation_runs).where(
                evaluation_runs.c.purpose == "release",
                evaluation_runs.c.qualification == "PASS",
                evaluation_runs.c.version != version.strip(),
            ).order_by(evaluation_runs.c.created_at.desc(), evaluation_runs.c.id.desc())
            .limit(1)).mappings().first()
            trend = compare_baseline(report, None if baseline is None else baseline["report"])
            run_id = uuid4()
            connection.execute(insert(evaluation_runs).values(
                id=run_id, version=version.strip(), revision=revision.strip(),
                corpus_version=CORPUS_VERSION, purpose=purpose,
                qualification=report["qualification"],
                baseline_run_id=None if baseline is None else baseline["id"],
                report=report, trend=trend,
            ))
        return {"id": str(run_id), "version": version, "revision": revision,
                "purpose": purpose, "baseline_run_id": None if baseline is None else str(baseline["id"]),
                "trend": trend}
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Write JSON qualification evidence")
    parser.add_argument("--purpose", choices=("focused", "milestone", "release"), default="release")
    parser.add_argument("--version", help="Candidate Watt version; enables durable run evidence")
    parser.add_argument("--database-url", default=os.environ.get("SPG_DATABASE_URL"))
    parser.add_argument("--capability", action="append", default=[])
    parser.add_argument("--failure-family", action="append", default=[])
    parser.add_argument("--minimum-risk", choices=("LOW", "MEDIUM", "HIGH", "CRITICAL"), default="LOW")
    parser.add_argument("--list-selected", action="store_true")
    arguments = parser.parse_args()
    selected = select_cases(
        purpose=arguments.purpose,
        capability_families=tuple(arguments.capability),
        failure_families=tuple(arguments.failure_family),
        minimum_risk=arguments.minimum_risk,
    )
    if arguments.list_selected:
        print(json.dumps([case.__dict__ for case in selected], ensure_ascii=False, indent=2))
        return
    result = qualify(selected)
    result["selection"] = {
        "purpose": arguments.purpose,
        "selected_case_ids": [case.identity for case in selected],
        "selected_count": len(selected),
        "corpus_count": len(CORPUS),
    }
    if arguments.version:
        if not arguments.database_url:
            parser.error("--version requires --database-url or SPG_DATABASE_URL")
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, check=True).stdout.strip()
        result["persisted"] = persist_evaluation(arguments.database_url,
            version=arguments.version, revision=revision,
            purpose=arguments.purpose, report=result)
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if arguments.report is not None:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    raise SystemExit(0 if result["qualification"] == "PASS" else 1)


if __name__ == "__main__":
    main()
