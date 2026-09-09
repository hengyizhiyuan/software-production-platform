"""Replay recorded immutable bases without a database or conversation feedback.

Only --run-real-provider enables execution. This isolates input drift between
provider conditions; results remain unadmitted candidates, not product truth.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import inspect
import json
from pathlib import Path
import time

from spg.domain.interaction import InteractionInterpretationInput
import spg.providers.codex_interaction as provider_module
from spg.providers.codex_interaction import CodexSdkWorkInteractionCapability

try:
    from .pipeline_probe import ProviderObservation, TextObservation, selected_case_numbers, stable_hash
except ImportError:  # Direct script execution keeps the selected product PYTHONPATH.
    from pipeline_probe import ProviderObservation, TextObservation, selected_case_numbers, stable_hash


def replay_cases(report: dict, numbers: str | None = None, source_repetition: int = 1):
    cases = [case for case in report["cases"] if case.get("repetition", 1) == source_repetition]
    if not cases:
        raise ValueError("No cases in requested source repetition")
    selected = selected_case_numbers(numbers, max(case["number"] for case in cases))
    result = [case for case in cases if case["number"] in selected]
    if {case["number"] for case in result} != selected:
        raise ValueError("Requested case is absent from source report")
    for case in result:
        if "basis" not in case or case.get("basis_sha256") != stable_hash(case["basis"]):
            raise ValueError(f"Missing or mismatched recorded basis for case {case['number']}")
        InteractionInterpretationInput.model_validate(case["basis"])
    return result


def interpret_fixed_basis(capability, payload: dict, on_delta, on_stage):
    """Fresh object per call; never feed a generated candidate into another case."""
    basis = InteractionInterpretationInput.model_validate(payload)
    before = stable_hash(basis.model_dump(mode="json"))
    observed = getattr(capability, "interpret_stream_observed", None)
    if callable(observed):
        candidate = observed(basis, on_response_delta=on_delta, on_pipeline_stage=on_stage)
    else:
        candidate = capability.interpret_stream(basis, on_response_delta=on_delta)
    if stable_hash(basis.model_dump(mode="json")) != before:
        raise AssertionError("Provider modified its replay basis")
    return candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-real-provider", action="store_true", required=True)
    parser.add_argument("--input", type=Path, required=True, help="pipeline_probe report with basis snapshots")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--semantic-effort")
    parser.add_argument("--conversation-effort")
    parser.add_argument("--separate-pre-work", action="store_true")
    parser.add_argument("--cases", help="Comma-separated recorded turn numbers")
    parser.add_argument("--source-repetition", type=int, default=1)
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    input_report = json.loads(args.input.read_text())
    cases = replay_cases(input_report, args.cases, args.source_repetition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    provider_root = args.output.parent / "provider-empty-cwd"
    provider_root.mkdir(parents=True, exist_ok=True)
    stages = {}
    request_clock = [time.monotonic()]
    observation = ProviderObservation(stages, request_clock)
    observation.install_validation_observer()
    capability = CodexSdkWorkInteractionCapability(
        repository_location=str(provider_root.resolve()), model=args.model,
        conversation_model=args.model, reasoning_effort=args.semantic_effort,
        conversation_reasoning_effort=args.conversation_effort,
        coalesce_pre_work=not args.separate_pre_work, timeout_seconds=180,
        codex_factory=observation.factory(provider_module.Codex),
    )
    source_root = Path(inspect.getfile(CodexSdkWorkInteractionCapability)).resolve().parents[2]
    source_files = {
        path.relative_to(source_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(source_root.rglob("*"))
        if path.is_file() and path.suffix in {".py", ".js", ".css", ".html"}
    }
    report = {
        "label": args.label, "recorded_at": datetime.now(UTC).isoformat(),
        "source_fingerprint": hashlib.sha256(json.dumps(source_files, sort_keys=True).encode()).hexdigest(),
        "source_files": source_files,
        "probe_fingerprint": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "observation_fingerprint": hashlib.sha256(Path(inspect.getfile(ProviderObservation)).read_bytes()).hexdigest(),
        "input_report_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "source_repetition": args.source_repetition, "repetitions": args.repeat,
        "model": args.model, "semantic_effort": args.semantic_effort,
        "conversation_effort": args.conversation_effort, "cases": [],
        "scope": "fixed recorded bases; provider-only candidates; no HTTP, database admission or production",
    }

    def save():
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for repetition in range(1, args.repeat + 1):
        for recorded in cases:
            stages.clear()
            observed_text = TextObservation()
            started = time.monotonic()
            request_clock[0] = started
            case = {"number": recorded["number"], "repetition": repetition,
                    "message": recorded.get("message"), "basis_sha256": recorded["basis_sha256"],
                    "status": "RUNNING"}
            report["cases"].append(case)
            try:
                candidate = interpret_fixed_basis(
                    capability, recorded["basis"],
                    lambda delta: observed_text.delta(delta, time.monotonic() - started),
                    observation.mark,
                )
                # Capture the Provider boundary before report serialization, but
                # publish success only after its candidate/evidence are recorded.
                candidate_validated_seconds = time.monotonic() - started
                if observed_text.content.strip() != candidate.natural_response.strip():
                    observed_text.reset(candidate.natural_response, time.monotonic() - started)
                case.update(status="CANDIDATE_VALIDATED", response=candidate.natural_response,
                            candidate=candidate.model_dump(mode="json"))
                evidence = capability.last_pipeline_evidence
                case["provider"] = asdict(evidence) if evidence is not None else None
                collaboration = capability.last_collaboration_result
                case["intent"] = None if collaboration is None else collaboration.turn_intent.value
                observed_text.terminal(candidate_validated_seconds, success=True)
            except Exception as error:
                observed_text.terminal(time.monotonic() - started, success=False)
                case.update(status="FAILED", failure_type=type(error).__name__, failure_message=str(error))
            case.update(stages)
            case.update(observed_text.as_dict())
            case["completion_boundary"] = "provider candidate validation; no admission/persistence"
            case["natural_response_closed_to_completion_seconds"] = (
                case["completion_seconds"] - case["natural_response_completed_seconds"]
                if case["completion_seconds"] is not None and "natural_response_completed_seconds" in case
                else None
            )
            save()
            print(json.dumps({key: value for key, value in case.items()
                              if key not in {"response", "candidate", "provider", "text_delta_events"}},
                             ensure_ascii=False), flush=True)
    report["completed"] = all(case["status"] == "CANDIDATE_VALIDATED" for case in report["cases"])
    save()
    if not report["completed"]:
        raise SystemExit("Replay retained failed candidates; see output report")


if __name__ == "__main__":
    main()
