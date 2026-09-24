"""Executable, domain-separated acceptance corpus for a candidate Watt version."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[3]


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

    if purpose not in {"focused", "release"}:
        raise ValueError("evaluation purpose must be focused or release")
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
        if case.duplicate_group and not case.critical:
            if case.duplicate_group in grouped:
                continue
            grouped.add(case.duplicate_group)
        selected.append(case)
    return tuple(selected)


def run_case(case: EvaluationCase, *, root: Path = ROOT) -> dict:
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Write JSON qualification evidence")
    parser.add_argument("--purpose", choices=("focused", "release"), default="release")
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
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if arguments.report is not None:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    raise SystemExit(0 if result["qualification"] == "PASS" else 1)


if __name__ == "__main__":
    main()
