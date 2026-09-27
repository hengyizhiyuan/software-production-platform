"""Explicit qualification denominators, including fail-closed compilations.

This evaluates declared oracles and retained results, never Human wording.
Compiler-only observations cannot establish effect satisfaction.
"""
import argparse
import json
from pathlib import Path


def metrics(corpus, results):
    cases = corpus["cases"]
    by_id = {result["case_id"]: result for result in results}
    if set(by_id) != {case["id"] for case in cases}:
        raise ValueError("Every declared case needs a retained result")
    explicit = [case for case in cases if case["expected_operations"]]
    negatives = [case for case in cases if not case["expected_operations"] and not case["current_production"]]
    arguments = [case for case in cases if case.get("expected_branch")]
    missed = [case["id"] for case in explicit if
        sorted(by_id[case["id"]].get("observed_operations", [])) != sorted(case["expected_operations"])]
    false_positive = [case["id"] for case in negatives if
        by_id[case["id"]].get("observed_operations") or
        any(item.get("production", {}).get("current") for item in
            by_id[case["id"]].get("governed_ir", {}).get("items", []) if item.get("production"))]
    def repair_count(result):
        evidence = result.get("provider_metadata", {})
        if "qualification_semantic_repair_count" in evidence:
            return evidence["qualification_semantic_repair_count"]
        key = "coalesced_structured_repair_count" if evidence.get("pipeline_mode") == "coalesced_pre_work" else "semantic_structured_repair_count"
        return evidence.get(key)
    recovered = sum(result["status"] == "PASS" and bool(repair_count(result)) for result in results)
    return {
        "metrics_version": "irk-denominators-v2",
        "cases": len(cases), "passed": sum(result["status"] == "PASS" for result in results),
        "semantic_equivalence_accuracy": sum(result["status"] == "PASS" for result in results) / len(cases),
        "explicit_action_cases": len(explicit), "missed_explicit_action_cases": missed,
        "missed_explicit_action_rate": len(missed) / len(explicit) if explicit else None,
        "hard_negative_cases": len(negatives), "false_execution_intent_cases": false_positive,
        "false_execution_intent_rate": len(false_positive) / len(negatives) if negatives else None,
        "hard_negative_compilation_failures": sum("error_type" in by_id[case["id"]] for case in negatives),
        "argument_target_cases": len(arguments),
        "action_argument_accuracy": sum(by_id[case["id"]].get("checks", {}).get("branch_arguments", False)
            for case in arguments) / len(arguments) if arguments else None,
        "inappropriate_human_interventions": sum(result.get("inappropriate_human_intervention", False)
            for result in results),
        "compilation_failures": sum("error_type" in result for result in results),
        "self_refine_recovered": recovered,
        "self_refine_recovery_fraction": recovered / len(cases),
        "semantic_repair_observation_unavailable": sum(repair_count(result) is None for result in results),
        "effect_satisfaction": None,
        "effect_observation": "NOT_EXECUTED: public runtime owner receipts qualify effects separately",
        "failure_note": "Compilation failure counts as missed requested execution, never successful understanding. False execution here is admitted intent, not observed execution. A staged wording call is not a semantic repair; unavailable repair counts remain unknown.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    corpus = json.loads(args.corpus.read_text())
    results = [json.loads((args.directory / (case["id"] + ".json")).read_text()) for case in corpus["cases"]]
    output = args.directory / "report-metrics-v2.json"
    if output.exists():
        raise SystemExit("Retained metrics are immutable")
    value = metrics(corpus, results)
    output.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(value))


if __name__ == "__main__":
    main()
