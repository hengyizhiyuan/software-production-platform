"""Build and validate the small WIC Fast Context projection."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from time import monotonic

from spg.domain.interaction import InteractionInterpretationInput, InterpretationMeaningKind
from spg.domain.wic_reception import FastContextCard


def _language(text: str) -> str:
    return "zh-CN" if any("\u4e00" <= char <= "\u9fff" for char in text) else "en"


def build_fast_context_card(basis: InteractionInterpretationInput) -> FastContextCard:
    started = monotonic()
    active = basis.active_work_context
    prior = basis.prior_assessment
    revision = None if active is None else active.work_revision
    corrections = () if prior is None else tuple(
        meaning for meaning in prior.meanings
        if meaning.kind is InterpretationMeaningKind.CORRECTION
    )
    latest_correction = corrections[-1] if corrections else None
    facts = (prior.candidate_context if prior else ()) if revision is None else revision.context_facts
    constraints = (prior.candidate_constraints if prior else ()) if revision is None else revision.constraints
    requests = (prior.current_requests if prior else ()) if revision is None else revision.requests
    decisions = () if prior is None else prior.unresolved_material_questions
    references = tuple(dict.fromkeys((
        *(reference for record in basis.records for reference in record.supporting_references),
        *((active.relevant_reality_references) if active else ()),
    )))
    source = {
        "basis": basis.basis_fingerprint,
        "sequence": basis.records[-1].sequence,
        "work_revision": None if revision is None else str(revision.id),
        "references": references,
        "correction_sources": () if latest_correction is None else tuple(
            str(value) for value in latest_correction.source_record_ids
        ),
    }
    fingerprint = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
    values = {
        "interaction_id": basis.interaction.id,
        "interaction_sequence": basis.records[-1].sequence,
        "condition": "PRE_WORK" if revision is None else "ACTIVE_WORK",
        "motive": (prior.interpreted_motive if prior else None) if revision is None else revision.motive,
        "desired_outcome": (prior.desired_outcome if prior else None) if revision is None else revision.desired_outcome,
        "active_work_id": None if revision is None else revision.work_id,
        "active_work_revision_id": None if revision is None else revision.id,
        "active_work_revision_number": None if revision is None else revision.revision_number,
        "current_focus": None if revision is None else revision.desired_outcome,
        "material_facts": tuple(facts[:5]),
        "material_constraints": tuple(constraints[:5]),
        "current_requests": tuple(requests[:5]),
        "unresolved_human_decisions": tuple(decisions[:3]),
        "last_correction": None if latest_correction is None else latest_correction.statement,
        "correction_supersedes": None,
        "response_language": _language(basis.records[-1].content),
        "source_references": references,
        "source_fingerprint": fingerprint,
        "source_count": len(basis.records) + (1 if revision else 0) + len(references),
        "built_at": datetime.now(UTC),
    }
    payload = json.dumps(values, default=str, ensure_ascii=False, sort_keys=True)
    return FastContextCard(
        **values,
        serialized_characters=len(payload),
        serialized_bytes=len(payload.encode("utf-8")),
        estimated_tokens=(len(payload) + 3) // 4,
        build_latency_ms=(monotonic() - started) * 1000,
    )


def fast_context_is_fresh(card: FastContextCard, basis: InteractionInterpretationInput) -> bool:
    rebuilt = build_fast_context_card(basis)
    return (
        card.interaction_id == basis.interaction.id
        and card.interaction_sequence == basis.records[-1].sequence
        and card.source_fingerprint == rebuilt.source_fingerprint
        and card.active_work_revision_id == rebuilt.active_work_revision_id
    )
