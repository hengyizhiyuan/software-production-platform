"""Run deterministic and bounded hosted Fast Reception lanes on frozen OPEN_WIC."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import statistics
from uuid import NAMESPACE_URL, uuid5

from spg.application.interaction import interaction_basis_fingerprint
from spg.application.wic_context import build_fast_context_card
from spg.application.wic_reception import DeterministicFastReceptionCapability, ShadowFastReceptionRuntime
from spg.config import Settings
from spg.domain.interaction import Interaction, InteractionActor, InteractionCondition, InteractionInterpretationInput, InteractionRecord
from spg.domain.model_runtime import ModelProfile, ModelProvider, ModelProviderRegistry, ModelPurpose, PurposeProfileRouter, WattModelRuntime
from spg.evaluation.open_wic_baseline import _active_context, load_corpus
from spg.infrastructure.model_runtime import DeepSeekResponsesModelAdapter
from spg.providers.deepseek_fast_reception import DeepSeekFastReceptionCapability


def basis_for(case):
    now = datetime.now(UTC); interaction_id = uuid5(NAMESPACE_URL, f"fast:{case.case_id}:interaction")
    active = _active_context(case, now); records = []
    for index, turn in enumerate(case.human_turns, 1):
        records.append(InteractionRecord(
            id=uuid5(NAMESPACE_URL, f"fast:{case.case_id}:record:{index}"), interaction_id=interaction_id,
            sequence=index, actor=InteractionActor.HUMAN, source="OPEN_WIC_FROZEN_CORPUS",
            content=turn.content, content_fingerprint=hashlib.sha256(turn.content.encode()).hexdigest(),
            supporting_references=turn.supporting_references, created_at=now,
        ))
    interaction = Interaction(
        id=interaction_id, condition=InteractionCondition.OPEN,
        current_work_id=None if active is None else active.work_revision.work_id,
        created_by="qualification", updated_by="qualification", created_at=now, updated_at=now,
    )
    fingerprint = interaction_basis_fingerprint(interaction, tuple(records), active)
    return InteractionInterpretationInput(
        interaction=interaction, records=tuple(records), active_work_context=active,
        basis_fingerprint=fingerprint,
    )


def adjudicate(observation) -> str:
    if observation.status == "NO_EMISSION": return "NO_EMISSION"
    if observation.status != "CANDIDATE": return "NO_EMISSION"
    candidate = observation.candidate
    if candidate.policy_disposition.value == "BLOCKED": return "FALSE_CONFIDENCE"
    if candidate.detected_human_owned_decision and "需要由你决定" not in candidate.meaningful_sentence:
        return "AUTHORITY_VIOLATION"
    return "CORRECT_GROUNDED"


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True); parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--run-real-provider", action="store_true", required=True); args = parser.parse_args()
    settings = Settings(_env_file=args.env_file); corpus, digest = load_corpus(args.corpus)
    registry = ModelProviderRegistry(); registry.register(DeepSeekResponsesModelAdapter(
        api_key=lambda: "" if settings.deepseek_api_key is None else settings.deepseek_api_key.get_secret_value(),
        base_url=settings.deepseek_base_url,
    ))
    profile = ModelProfile(
        purpose=ModelPurpose.WIC_FAST_RECEPTION, provider=ModelProvider.DEEPSEEK,
        model="deepseek-flash", reasoning_effort="low", timeout_seconds=8,
        max_output_tokens=256,
    )
    hosted = ShadowFastReceptionRuntime(DeepSeekFastReceptionCapability(
        WattModelRuntime(registry, PurposeProfileRouter({ModelPurpose.WIC_FAST_RECEPTION: profile}))
    ))
    deterministic = ShadowFastReceptionRuntime(DeterministicFastReceptionCapability())
    report = {
        "schema_version": "wic-fast-reception-qualification-v1", "captured_at": datetime.now(UTC).isoformat(),
        "corpus_digest": digest, "provider_profile": profile.identity,
        "scope": "shadow candidates only; no database, admission, Work or production",
        "cases": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        for case in corpus.cases:
            basis = basis_for(case); turn_id = uuid5(NAMESPACE_URL, f"fast:{case.case_id}:turn")
            card = build_fast_context_card(basis)
            lane_a = deterministic.start(basis, turn_id).result(timeout=1)
            lane_b = hosted.start(basis, turn_id).result(timeout=10)
            item = {
                "case_id": case.case_id,
                "context": card.model_dump(mode="json"),
                "lane_a_deterministic": lane_a.model_dump(mode="json"),
                "lane_a_adjudication": adjudicate(lane_a),
                "lane_b_hosted": lane_b.model_dump(mode="json"),
                "lane_b_adjudication": adjudicate(lane_b),
                "lane_c_no_emission_valid": True,
                "reference_intent": case.reference_intent.model_dump(mode="json"),
            }
            report["cases"].append(item)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
            print(json.dumps({"case_id": case.case_id, "a": lane_a.status, "b": lane_b.status}, ensure_ascii=False), flush=True)
    finally:
        deterministic.close(); hosted.close(); registry.close()
    latencies = [lane["terminal_ms"] for item in report["cases"] for lane in [item["lane_b_hosted"]] if lane["terminal_ms"] is not None]
    report["summary"] = {
        "cases": len(report["cases"]),
        "deterministic_candidates": sum(x["lane_a_deterministic"]["status"] == "CANDIDATE" for x in report["cases"]),
        "hosted_candidates": sum(x["lane_b_hosted"]["status"] == "CANDIDATE" for x in report["cases"]),
        "hosted_failures": sum(x["lane_b_hosted"]["status"] == "FAILED" for x in report["cases"]),
        "hosted_p50_ms": None if not latencies else statistics.median(latencies),
        "hosted_p95_ms": None if not latencies else sorted(latencies)[min(len(latencies)-1, int(len(latencies)*.95))],
        "hosted_calls": len(report["cases"]),
        "hosted_tokens": sum((x["lane_b_hosted"].get("total_tokens") or 0) for x in report["cases"]),
        "cost_rmb": None,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)


if __name__ == "__main__": main()
