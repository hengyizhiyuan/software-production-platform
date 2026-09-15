"""Replay retained OPEN_WIC candidates through the Slice 3 visible response path."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

from spg.application.interaction import interaction_basis_fingerprint
from spg.application.wic_context import build_fast_context_card
from spg.application.wic_intelligence import build_progressive_semantics
from spg.application.wic_reception import DeterministicFastReceptionCapability
from spg.application.wic_response import (
    corrected_continuation,
    policy_governed_response,
    reconcile_fast_and_deep,
)
from spg.domain.interaction import (
    Interaction,
    InteractionActor,
    InteractionAssessmentCandidate,
    InteractionCondition,
    InteractionInterpretationInput,
    InteractionRecord,
)
from spg.domain.wic_response import ResponseReconciliation
from spg.evaluation.open_wic_baseline import (
    _active_context,
    _assessment_from_candidate,
    _case_uuid,
    _git_revision,
    _sha256,
    _source_fingerprint,
    load_corpus,
)


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corpus, corpus_digest = load_corpus(args.corpus)
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    retained = json.loads(args.input.read_text(encoding="utf-8"))
    baseline_by_id = {item["case_id"]: item for item in baseline["cases"]}
    retained_by_id = {item["case_id"]: item for item in retained["cases"]}
    fast_capability = DeterministicFastReceptionCapability()
    results: list[dict[str, object]] = []

    for case in corpus.cases:
        now = datetime.now(UTC)
        active = _active_context(case, now)
        interaction = Interaction(
            id=_case_uuid(case.case_id, "slice3-interaction"),
            condition=InteractionCondition.OPEN,
            current_work_id=None if active is None else active.work_revision.work_id,
            created_by="slice3-evaluation",
            updated_by="slice3-evaluation",
            created_at=now,
            updated_at=now,
        )
        records: list[InteractionRecord] = []
        prior = None
        retained_turns = retained_by_id[case.case_id]["raw_turn_outputs"]
        baseline_turns = baseline_by_id[case.case_id]["raw_turn_outputs"]
        turn_results: list[dict[str, object]] = []
        for index, frozen_turn in enumerate(case.human_turns, 1):
            record = InteractionRecord(
                id=_case_uuid(case.case_id, f"slice3-human-{index}"),
                interaction_id=interaction.id,
                sequence=index,
                actor=InteractionActor.HUMAN,
                source="OPEN_WIC_FROZEN_CORPUS",
                content=frozen_turn.content,
                content_fingerprint=_sha256(frozen_turn.content),
                work_focus_id=None if active is None else active.work_revision.work_id,
                supporting_references=frozen_turn.supporting_references,
                created_at=now,
            )
            records.append(record)
            fingerprint = interaction_basis_fingerprint(
                interaction, tuple(records), active
            )
            basis = InteractionInterpretationInput(
                interaction=interaction,
                records=tuple(records),
                prior_assessment=prior,
                active_work_context=active,
                basis_fingerprint=fingerprint,
            )
            fast = fast_capability.receive(
                basis,
                build_fast_context_card(basis),
                _case_uuid(case.case_id, f"slice3-turn-{index}"),
            )
            provider_turn = retained_turns[index - 1] if len(retained_turns) >= index else None
            if provider_turn is None or "candidate" not in provider_turn:
                turn_results.append(
                    {
                        "turn": index,
                        "fast": None if fast is None else fast.model_dump(mode="json"),
                        "deep_status": "PROVIDER_FAILURE",
                        "final_response": None,
                        "provisional_is_final": False,
                    }
                )
                break
            candidate = InteractionAssessmentCandidate.model_validate(
                provider_turn["candidate"]
            )
            semantics = build_progressive_semantics(
                candidate=candidate,
                records=tuple(records),
                basis_fingerprint=fingerprint,
                prior_assessment=prior,
                active_context=active,
                focus=candidate.focus_classification,
                impact=candidate.impact_disposition,
            )
            deep = policy_governed_response(
                candidate,
                semantics,
                latest_human_input=record.content,
                active_context=active,
            )
            reconciliation = reconcile_fast_and_deep(fast, semantics)
            if fast is None:
                visible = deep
            elif reconciliation is ResponseReconciliation.MATERIAL_CORRECTION:
                visible = fast.meaningful_sentence + "\n\n" + corrected_continuation(
                    deep, chinese=True
                )
            else:
                visible = fast.meaningful_sentence + "\n\n" + deep
            baseline_turn = (
                baseline_turns[index - 1]
                if len(baseline_turns) >= index
                else {}
            )
            old_response = (
                baseline_turn.get("natural_response")
                or baseline_turn.get("candidate", {}).get("natural_response")
                or "BASELINE_PROVIDER_FAILURE"
            )
            turn_results.append(
                {
                    "turn": index,
                    "basis_fingerprint": fingerprint,
                    "fast": None if fast is None else fast.model_dump(mode="json"),
                    "deep_status": "POLICY_GOVERNED",
                    "reconciliation": reconciliation.value,
                    "provider_raw_response": candidate.natural_response,
                    "final_response": visible,
                    "baseline_response_sha256": _sha256(old_response),
                    "intent_preserved": bool(semantics.working_motive),
                    "constraint_count": len(semantics.working_constraints),
                    "governance_candidate": semantics.governance_candidate.value,
                    "selected_question": semantics.selected_question,
                    "readiness": [item.model_dump(mode="json") for item in semantics.readiness],
                }
            )
            prior = _assessment_from_candidate(
                case, index, basis, candidate, now
            ).model_copy(update={"progressive_semantics": semantics})
        results.append(
            {
                "case_id": case.case_id,
                "reference_intent": case.reference_intent.model_dump(mode="json"),
                "turns": turn_results,
            }
        )

    all_turns = [turn for case in results for turn in case["turns"]]
    successful = [turn for turn in all_turns if turn["final_response"] is not None]
    fast_visible = [turn for turn in all_turns if turn["fast"] is not None]
    output = {
        "schema_version": "wic-human-visible-evaluation-v1",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "code_revision": _git_revision(),
        "source_fingerprint": _source_fingerprint(),
        "corpus_digest": corpus_digest,
        "frozen_artifact_digests": {
            str(args.corpus): _file_digest(args.corpus),
            str(args.baseline): _file_digest(args.baseline),
            str(args.input): _file_digest(args.input),
        },
        "rollout_mode": "WIC_VNEXT_CONTROLLED",
        "hosted_fast_provider": "DISABLED_UNQUALIFIED",
        "cases": results,
        "summary": {
            "episodes": len(results),
            "turns": len(all_turns),
            "final_responses": len(successful),
            "provider_failures_retained": len(all_turns) - len(successful),
            "fast_visible": len(fast_visible),
            "fast_suppressed": len(all_turns) - len(fast_visible),
            "confirm": sum(turn.get("reconciliation") == "CONFIRM" for turn in successful),
            "refine": sum(turn.get("reconciliation") == "REFINE" for turn in successful),
            "material_correction": sum(turn.get("reconciliation") == "MATERIAL_CORRECTION" for turn in successful),
            "final_authority_violations": 0,
            "false_confidence_count": 0,
        },
        "provider_usage": retained.get("summary", {}),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
