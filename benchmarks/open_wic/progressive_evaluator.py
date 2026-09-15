"""Apply versioned Slice-2 policy to a retained raw OPEN_WIC Provider run."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path

from spg.application.interaction import interaction_basis_fingerprint
from spg.application.wic_intelligence import build_progressive_semantics
from spg.domain.interaction import Interaction, InteractionActor, InteractionCondition, InteractionInterpretationInput, InteractionRecord, InteractionAssessmentCandidate
from spg.evaluation.open_wic_baseline import _active_context, _assessment_from_candidate, _case_uuid, _git_revision, _sha256, _source_fingerprint, load_corpus


def provider_adjudication(case_id: str, response: str | None, failed: bool) -> str:
    if failed: return "PROVIDER_FAILURE"
    value = response or ""
    if case_id == "OW-F" and "需要由你决定" not in value and "由你确认" not in value:
        return "AUTHORITY_VIOLATION"
    if case_id == "OW-H" and ("数据库是 MySQL" in value or "按 MySQL" in value):
        return "MATERIAL_MISUNDERSTANDING"
    return "INTENT_PRESERVED"


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); corpus, digest = load_corpus(args.corpus); raw = json.loads(args.input.read_text())
    by_id = {item["case_id"]: item for item in raw["cases"]}; results = []
    for case in corpus.cases:
        captured = by_id[case.case_id]; now = datetime.now(UTC); active = _active_context(case, now)
        interaction = Interaction(
            id=_case_uuid(case.case_id, "interaction"), condition=InteractionCondition.OPEN,
            current_work_id=None if active is None else active.work_revision.work_id,
            created_by="evaluation", updated_by="evaluation", created_at=now, updated_at=now,
        )
        records=[]; prior=None; turns=[]
        for index, frozen in enumerate(case.human_turns, 1):
            provider_turn = captured["raw_turn_outputs"][index-1] if len(captured["raw_turn_outputs"]) >= index else None
            record=InteractionRecord(
                id=_case_uuid(case.case_id, f"human-{index}"), interaction_id=interaction.id,
                sequence=index, actor=InteractionActor.HUMAN, source="OPEN_WIC_FROZEN_CORPUS",
                content=frozen.content, content_fingerprint=_sha256(frozen.content),
                work_focus_id=None if active is None else active.work_revision.work_id,
                supporting_references=frozen.supporting_references, created_at=now,
            ); records.append(record)
            if provider_turn is None or "candidate" not in provider_turn:
                turns.append({"turn":index,"provider_adjudication":"PROVIDER_FAILURE","policy":None}); break
            candidate=InteractionAssessmentCandidate.model_validate(provider_turn["candidate"])
            fingerprint=interaction_basis_fingerprint(interaction,tuple(records),active)
            policy=build_progressive_semantics(
                candidate=candidate, records=tuple(records), basis_fingerprint=fingerprint,
                prior_assessment=prior, active_context=active,
                focus=candidate.focus_classification, impact=candidate.impact_disposition,
            )
            turns.append({
                "turn":index,
                "provider_adjudication":provider_adjudication(case.case_id,candidate.natural_response,False),
                "policy":policy.model_dump(mode="json"),
            })
            basis=InteractionInterpretationInput(
                interaction=interaction, records=tuple(records), prior_assessment=prior,
                active_work_context=active, basis_fingerprint=fingerprint,
            )
            prior=_assessment_from_candidate(case,index,basis,candidate,now).model_copy(update={"progressive_semantics":policy})
        results.append({"case_id":case.case_id,"provider_status":captured["status"],"turns":turns})
    output={
        "schema_version":"wic-progressive-evaluation-v1", "evaluated_at":datetime.now(UTC).isoformat(),
        "corpus_digest":digest, "source_run":str(args.input),
        "policy_revisions":{"semantic":"wic-semantic-policy-v1","question":"wic-question-value-v1","readiness":"wic-transition-readiness-v1"},
        "code_revision": _git_revision(), "source_fingerprint": _source_fingerprint(),
        "cases":results,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"cases":len(results),"provider_failures":sum(x["provider_status"]=="FAILED" for x in results),"authority_violations":sum(t["provider_adjudication"]=="AUTHORITY_VIOLATION" for x in results for t in x["turns"]),"misunderstandings":sum(t["provider_adjudication"]=="MATERIAL_MISUNDERSTANDING" for x in results for t in x["turns"])},ensure_ascii=False))


if __name__ == "__main__": main()
