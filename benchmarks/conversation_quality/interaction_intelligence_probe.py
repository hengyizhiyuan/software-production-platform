"""Real-Provider WIC interaction-quality probe over the public HTTP/SSE surface.

The probe creates isolated pre-Work conversations only.  It never admits Work or
invokes production.  It evaluates semantic properties and routing contracts,
not exact answer text.  Use it only against an explicitly authorized runtime.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CASES_PATH = Path(__file__).with_name("interaction_intelligence_cases.json")
TERMINAL_EVENTS = {"message.completed", "turn.failed"}
DISTINCTIVE_DOMAIN_PATTERNS = {
    "企业官网": r"企业官网",
    "小程序": r"小程序",
    "独居老人": r"独居老人",
    "请假审批": r"请假(?:审批|系统)",
    "日志分析 CLI": r"日志分析|日志\s*CLI",
    "工程上下文": r"工程上下文",
    "徒步": r"徒步",
    "库存管理": r"库存(?:管理|系统)",
    "两级审批": r"两级审批",
}


def _json_request(base_url: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = Request(
        base_url.rstrip("/") + path,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urlopen(request, timeout=360) as response:
        return json.load(response)


def _read_sse(base_url: str, path: str) -> dict:
    event_name = None
    visible = ""
    events: list[dict] = []
    response_ids: set[str] = set()
    growth_valid = True
    started = time.monotonic()
    with urlopen(base_url.rstrip("/") + path, timeout=360) as response:
        for raw in response:
            line = raw.decode("utf-8").strip()
            if line.startswith("event: "):
                event_name = line[7:]
                continue
            if not line.startswith("data: "):
                continue
            payload = json.loads(line[6:])
            elapsed = round(time.monotonic() - started, 4)
            before = visible
            if event_name == "response.provisional":
                visible = payload.get("content") or ""
            elif event_name == "response.delta":
                visible += payload.get("content") or ""
            elif event_name == "response.final":
                final = payload.get("content") or ""
                growth_valid = growth_valid and (final == visible or final.startswith(visible))
                visible = final
            elif event_name == "message.delta":
                visible += payload.get("delta") or ""
            elif event_name == "message.reset":
                visible = payload.get("content") or ""
            if before and event_name in {"response.delta", "message.delta"}:
                growth_valid = growth_valid and visible.startswith(before)
            response_id = payload.get("response_id")
            if response_id:
                response_ids.add(response_id)
            events.append(
                {
                    "event": event_name,
                    "seconds": elapsed,
                    "characters": len(payload.get("content") or payload.get("delta") or ""),
                    "sequence": payload.get("sequence"),
                }
            )
            if event_name in TERMINAL_EVENTS:
                return {
                    "terminal_event": event_name,
                    "visible_content": visible,
                    "events": events,
                    "response_ids": sorted(response_ids),
                    "single_response_identity": len(response_ids) <= 1,
                    "progressive_growth": growth_valid,
                    "elapsed_seconds": elapsed,
                    "failure_code": payload.get("code"),
                    "failure_message": payload.get("message"),
                }
    raise RuntimeError("SSE stream ended without a terminal event")


def _normalize(value: str) -> str:
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).casefold()


def _first_sentence(value: str) -> str:
    parts = re.split(r"(?<=[。！？!?])", value.strip(), maxsplit=1)
    return parts[0].strip() if parts else value.strip()


def _echo_flag(human_input: str, response: str) -> bool:
    source = _normalize(human_input)
    first = _normalize(_first_sentence(response))
    if not source or not first:
        return False
    ratio = SequenceMatcher(None, source, first).ratio()
    return (source in first and len(first) <= len(source) + 8) or ratio >= 0.86


def evaluate_case(case: dict) -> list[str]:
    """Return bounded semantic flags; absence of flags is not Human acceptance."""

    if case.get("status") not in {None, "COMPLETED"}:
        code = case.get("failure_code") or "UNKNOWN"
        return [f"TURN_FAILED:{code}"]
    flags: list[str] = []
    response = case.get("response") or ""
    expected_intents = case.get("expected_intents", [])
    expected_moves = case.get("expected_moves", [])
    intent = case.get("turn_intent")
    move = case.get("primary_move")
    strategy = case.get("interaction_strategy") or {}
    if intent not in expected_intents:
        flags.append("TURN_INTENT_MISMATCH")
    if move not in expected_moves:
        flags.append("INTERACTION_MOVE_MISMATCH")
    if move in {"ASK", "ORIENT"} and not set(expected_moves).intersection({"ASK", "ORIENT"}):
        flags.append("ASK_OR_ORIENT_WHEN_ANSWER_OR_PROPOSE_EXPECTED")
    if _echo_flag(case.get("input", ""), response):
        flags.append("SEMANTIC_ECHO")
    for term in case.get("forbidden_terms", []):
        if term.casefold() in response.casefold():
            flags.append(f"UNSUPPORTED_PREMISE:{term}")
    own_terms = set(case.get("domain_terms", []))
    for domain, pattern in DISTINCTIVE_DOMAIN_PATTERNS.items():
        if any(term in domain or domain in term for term in own_terms):
            continue
        if re.search(pattern, response, re.I) and not re.search(
            pattern, case.get("input", ""), re.I
        ):
            flags.append(f"CROSS_DOMAIN_LEAKAGE:{domain}")
    question_count = response.count("?") + response.count("？")
    if question_count > int(strategy.get("max_questions", 0)):
        flags.append("QUESTION_ALLOWANCE_EXCEEDED")
    if intent == "HOW_TO" or "HOW_TO" in expected_intents:
        if not strategy.get("answer_first") or _first_sentence(response).endswith(("?", "？")):
            flags.append("HOW_TO_NOT_ANSWERED_DIRECTLY")
    if strategy.get("candidate_first"):
        useful_domain_signal = any(term.casefold() in response.casefold() for term in own_terms)
        if len(_normalize(response)) < 24 or not useful_domain_signal or _first_sentence(response).endswith(("?", "？")):
            flags.append("BUILD_OR_PROPOSAL_HAS_NO_USEFUL_CANDIDATE")
    if not case.get("progressive_growth", False):
        flags.append("NON_PROGRESSIVE_RESPONSE_STREAM")
    if not case.get("single_response_identity", False):
        flags.append("DUPLICATE_RESPONSE_IDENTITY")
    if not case.get("projection_matches_stream", False):
        flags.append("STREAM_PROJECTION_DIVERGENCE")
    if not case.get("replay_matches_projection", False):
        flags.append("RECONNECT_REPLAY_DIVERGENCE")
    if case.get("provider_matches") is False:
        flags.append("PROVIDER_MISMATCH")
    if case.get("model_matches") is False:
        flags.append("MODEL_MISMATCH")
    return list(dict.fromkeys(flags))


def add_cross_case_flags(cases: list[dict]) -> None:
    orient_cases = [case for case in cases if case.get("primary_move") == "ORIENT"]
    if len(orient_cases) > 2:
        for case in orient_cases[2:]:
            case.setdefault("quality_flags", []).append("REPEATED_ORIENT_DEFAULT")
    for index, left in enumerate(cases):
        for right in cases[index + 1 :]:
            a, b = _normalize(left.get("response", "")), _normalize(right.get("response", ""))
            if min(len(a), len(b)) < 40:
                continue
            if SequenceMatcher(None, a, b).ratio() >= 0.78:
                left.setdefault("quality_flags", []).append(f"TEMPLATE_REUSE_WITH:{right['id']}")
                right.setdefault("quality_flags", []).append(f"TEMPLATE_REUSE_WITH:{left['id']}")
    for case in cases:
        case["quality_flags"] = list(dict.fromkeys(case.get("quality_flags", [])))


def render_markdown(report: dict) -> str:
    lines = [
        "# WIC Interaction Intelligence Probe",
        "",
        f"- Recorded: `{report['recorded_at']}`",
        f"- Runtime: `{report['base_url']}`",
        f"- Expected Provider / Model: `{report['expected_provider']}` / `{report['expected_model']}`",
        f"- Cases: `{len(report['cases'])}`",
        f"- Cases with flags: `{report['summary']['flagged_cases']}`",
        f"- Result: `{report['summary']['result']}`",
        "",
        "The probe checks bounded semantic properties, not exact response prose. A pass is not Human Product Acceptance.",
        "",
        "| Case | Intent | Cognitive State | Move | Fast | Seconds | Flags |",
        "|---|---|---|---|---|---:|---|",
    ]
    for case in report["cases"]:
        lines.append(
            "| {id} | {intent} | {cognitive} | {move} | {fast} | {seconds} | {flags} |".format(
                id=case["id"],
                intent=case.get("turn_intent", "—"),
                cognitive=case.get("cognitive_maturity", "—"),
                move=case.get("primary_move", "—"),
                fast="visible" if case.get("fast_visible") else case.get("fast_suppression_reason") or "none",
                seconds=case.get("elapsed_seconds", "—"),
                flags="; ".join(case.get("quality_flags", [])) or "—",
            )
        )
    lines.extend(("", "## Human-facing outputs", ""))
    for case in report["cases"]:
        lines.extend(
            (
                f"### {case['id']}",
                "",
                f"**Human:** {case['input']}",
                "",
                f"**Watt:** {case.get('response') or '(no response)' }",
                "",
            )
        )
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict:
    cases_spec = json.loads(args.cases_file.read_text(encoding="utf-8"))
    if not 15 <= len(cases_spec) <= 20:
        raise ValueError("Interaction intelligence corpus must contain 15–20 cases")
    report = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "base_url": args.base_url,
        "expected_provider": args.expected_provider,
        "expected_model": args.expected_model,
        "scope": "real Provider pre-Work conversation quality; no Work admission or production",
        "cases": [],
    }

    def save() -> None:
        report["summary"] = {
            "completed_cases": sum(case.get("status") == "COMPLETED" for case in report["cases"]),
            "flagged_cases": sum(bool(case.get("quality_flags")) for case in report["cases"]),
            "result": (
                "PASS"
                if len(report["cases"]) == len(cases_spec)
                and all(case.get("status") == "COMPLETED" and not case.get("quality_flags") for case in report["cases"])
                else "REVIEW_REQUIRED"
            ),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        args.output.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")

    for spec in cases_spec:
        item = dict(spec)
        report["cases"].append(item)
        started = time.monotonic()
        try:
            created = _json_request(
                args.base_url,
                "/api/interactions",
                {"human_identity": "human:interaction-intelligence-probe"},
            )
            interaction_id = created["interaction_id"]
            submitted = _json_request(
                args.base_url,
                f"/api/interactions/{interaction_id}/turns",
                {
                    "content": spec["input"],
                    "human_identity": "human:interaction-intelligence-probe",
                },
            )
            turn_id = submitted["turn_id"]
            stream_path = f"/api/interactions/{interaction_id}/turns/{turn_id}/events"
            live = _read_sse(args.base_url, stream_path)
            turn = _json_request(
                args.base_url,
                f"/api/interactions/{interaction_id}/turns/{turn_id}",
            )
            projection = _json_request(args.base_url, f"/api/interactions/{interaction_id}")
            timing = _json_request(
                args.base_url,
                f"/api/interactions/{interaction_id}/turns/{turn_id}/timing",
            )
            replay = _read_sse(args.base_url, stream_path + "?" + urlencode({"after_sequence": 0}))
            messages = [
                message for message in projection.get("conversation_messages", [])
                if message.get("turn_id") == turn_id and message.get("actor") == "WATT"
            ]
            response = messages[0]["content"] if len(messages) == 1 else ""
            assessment = projection.get("latest_assessment") or {}
            semantics = assessment.get("progressive_semantics") or {}
            strategy = timing.get("interaction_strategy") or {}
            semantic_evidence = timing.get("semantic_provider_evidence") or {}
            provider_values = json.dumps(
                {"semantic": semantic_evidence, "realizer": timing.get("realizer_provider")},
                ensure_ascii=False,
            ).casefold()
            model_values = json.dumps(
                {"semantic": semantic_evidence, "realizer": timing.get("realizer_model")},
                ensure_ascii=False,
            ).casefold()
            item.update(
                interaction_id=interaction_id,
                turn_id=turn_id,
                status=turn.get("status"),
                failure_code=turn.get("failure_code") or live.get("failure_code"),
                failure_message=turn.get("failure_message") or live.get("failure_message"),
                turn_intent=semantics.get("turn_intent"),
                cognitive_maturity=strategy.get("cognitive_maturity"),
                primary_move=strategy.get("primary_move"),
                interaction_strategy=strategy,
                response=response,
                provider={
                    "semantic": semantic_evidence,
                    "realizer": timing.get("realizer_provider"),
                },
                model={
                    "assessment": assessment.get("model_identity"),
                    "realizer": timing.get("realizer_model"),
                },
                provider_matches=args.expected_provider.casefold() in provider_values,
                model_matches=args.expected_model.casefold() in model_values,
                fast_visible=timing.get("fast_visible"),
                fast_suppression_reason=timing.get("fast_suppression_reason"),
                timeline=timing,
                stream_events=live["events"],
                response_ids=live["response_ids"],
                progressive_growth=live["progressive_growth"],
                single_response_identity=live["single_response_identity"],
                projection_matches_stream=response == live["visible_content"],
                replay_matches_projection=response == replay["visible_content"],
                watt_message_count=len(messages),
                governed_work_id=projection.get("governed_work_id"),
                elapsed_seconds=round(time.monotonic() - started, 4),
            )
            if item["governed_work_id"] is not None:
                item.setdefault("quality_flags", []).append("UNEXPECTED_WORK_CREATED")
            item.setdefault("quality_flags", []).extend(evaluate_case(item))
        except (HTTPError, OSError, RuntimeError, KeyError, ValueError) as error:
            item.update(
                status="PROBE_FAILED",
                elapsed_seconds=round(time.monotonic() - started, 4),
                error_type=type(error).__name__,
                error_message=str(error),
                quality_flags=["PROBE_EXECUTION_FAILURE"],
            )
        save()
    add_cross_case_flags(report["cases"])
    save()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-real-provider", action="store_true", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8047")
    parser.add_argument("--expected-provider", default="deepseek")
    parser.add_argument("--expected-model", default="deepseek-flash")
    parser.add_argument("--cases-file", type=Path, default=CASES_PATH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result["summary"], ensure_ascii=False))
    raise SystemExit(0 if result["summary"]["result"] == "PASS" else 1)


if __name__ == "__main__":
    main()
