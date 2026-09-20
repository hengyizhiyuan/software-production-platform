"""Admission and lineage rules for software-production semantic facts."""

from __future__ import annotations

from hashlib import sha256
import json
import unicodedata
from uuid import NAMESPACE_URL, UUID, uuid5

from spg.domain.engineering_semantics import (
    EngineeringSemanticFact,
    EngineeringSemanticFactCandidate,
    NeutralSemanticExtractionCandidate,
    SemanticCandidateOperation,
    SemanticEpistemicStatus,
    SemanticFactAuthority,
    SemanticFactProvenance,
)
from spg.domain.interaction import (
    InteractionActor,
    InteractionInvariantViolation,
    InteractionRecord,
)


def bind_engineering_semantic_facts(
    *,
    basis_fingerprint: str,
    records: tuple[InteractionRecord, ...],
    extractions: tuple[NeutralSemanticExtractionCandidate, ...],
    candidates: tuple[EngineeringSemanticFactCandidate, ...],
    prior_facts: tuple[EngineeringSemanticFact, ...] = (),
) -> tuple[EngineeringSemanticFact, ...]:
    """Validate extraction evidence and reconcile one current semantic ledger.

    The function is deliberately domain-neutral. Subjects come from the current
    Work context; reusable relations and authority rules govern reconciliation.
    """

    record_by_id = {record.id: record for record in records}
    extraction_by_id: dict[str, NeutralSemanticExtractionCandidate] = {}
    for extraction in extractions:
        if extraction.extraction_id in extraction_by_id:
            raise InteractionInvariantViolation("Neutral extraction identity is duplicated")
        source_ids, source_text = _canonical_provenance(
            record_by_id=record_by_id,
            source_record_ids=(extraction.source_record_id,),
            source_text=extraction.source_text,
            invalid_source_message=(
                "Neutral semantic extraction must cite a Human source record"
            ),
        )
        extraction = extraction.model_copy(
            update={"source_record_id": source_ids[-1], "source_text": source_text}
        )
        extraction_by_id[extraction.extraction_id] = extraction

    ledger = list(prior_facts)
    current = {fact.id: fact for fact in ledger if fact.is_current}
    by_key = {fact.semantic_key: fact for fact in current.values()}
    candidate_ids: set[str] = set()

    for candidate in candidates:
        if candidate.candidate_id in candidate_ids:
            raise InteractionInvariantViolation("Semantic fact candidate identity is duplicated")
        candidate_ids.add(candidate.candidate_id)
        source_ids, source_text = _canonical_provenance(
            record_by_id=record_by_id,
            source_record_ids=candidate.source_record_ids,
            source_text=candidate.source_text,
            invalid_source_message=(
                "Engineering semantic fact must cite Human source records"
            ),
        )
        candidate = candidate.model_copy(
            update={"source_record_ids": source_ids, "source_text": source_text}
        )
        if any(item not in extraction_by_id for item in candidate.source_extraction_ids):
            raise InteractionInvariantViolation(
                "Engineering semantic fact cites an unknown neutral extraction"
            )
        explicitly_superseded = tuple(dict.fromkeys(candidate.supersedes_fact_ids))
        if any(fact_id not in current for fact_id in explicitly_superseded):
            raise InteractionInvariantViolation(
                "Engineering semantic supersession must cite a current fact"
            )
        existing = by_key.get((candidate.subject, candidate.relation, candidate.scope))
        superseded_ids = list(explicitly_superseded)
        if existing is not None and candidate.operation is SemanticCandidateOperation.UPSERT:
            same_claim = (
                existing.value == candidate.value
                and existing.unit == candidate.unit
                and existing.qualifiers == candidate.qualifiers
            )
            if same_claim and not explicitly_superseded:
                if _authority_rank(existing.authority) >= _authority_rank(candidate.authority):
                    continue
                superseded_ids.append(existing.id)
            elif not same_claim and existing.id not in superseded_ids:
                superseded_ids.append(existing.id)

        if candidate.operation is SemanticCandidateOperation.REMOVE:
            _require_explicit_supersession(candidate)
            _supersede(ledger, current, by_key, tuple(superseded_ids))
            continue

        for fact_id in superseded_ids:
            old = current[fact_id]
            if (
                old.authority is SemanticFactAuthority.HUMAN_EXPLICIT
                and candidate.authority is SemanticFactAuthority.SYSTEM_INFERRED
            ):
                raise InteractionInvariantViolation(
                    "System inference cannot supersede explicit Human semantic truth"
                )
        _supersede(ledger, current, by_key, tuple(superseded_ids))
        identity = _fact_identity(basis_fingerprint, candidate)
        fact = EngineeringSemanticFact(
            id=identity,
            subject=candidate.subject,
            relation=candidate.relation,
            value=candidate.value,
            unit=candidate.unit,
            scope=candidate.scope,
            qualifiers=candidate.qualifiers,
            authority=candidate.authority,
            epistemic_status=candidate.epistemic_status,
            provenance=SemanticFactProvenance(
                source_record_ids=candidate.source_record_ids,
                source_text=candidate.source_text,
                source_extraction_ids=candidate.source_extraction_ids,
                role_origin=candidate.role_origin,
            ),
            supersedes_fact_ids=tuple(superseded_ids),
        )
        ledger.append(fact)
        current[fact.id] = fact
        by_key[fact.semantic_key] = fact

    return tuple(ledger)


def _canonical_provenance(
    *,
    record_by_id: dict[UUID, InteractionRecord],
    source_record_ids: tuple[UUID, ...],
    source_text: str,
    invalid_source_message: str,
) -> tuple[tuple[UUID, ...], str]:
    """Bind advisory Provider quotes to exact persisted Human evidence.

    Models occasionally normalize spacing, casing, or a short fragment, and can
    attach that fragment to the adjacent record in a multi-turn basis. Persisted
    Human records remain the authority: recover an exact matching record when
    possible, otherwise retain valid cited records and store one complete cited
    record as the verbatim provenance text. Unknown or non-Human citations still
    fail closed.
    """

    sources = tuple(record_by_id.get(item) for item in source_record_ids)
    if not sources or any(
        source is None or source.actor is not InteractionActor.HUMAN
        for source in sources
    ):
        raise InteractionInvariantViolation(invalid_source_message)
    human_records = tuple(
        record for record in record_by_id.values()
        if record.actor is InteractionActor.HUMAN
    )
    exact = tuple(record for record in human_records if source_text in record.content)
    if exact:
        cited_exact = tuple(record for record in exact if record.id in source_record_ids)
        chosen = cited_exact or exact
        return tuple(record.id for record in chosen), source_text
    normalized = _normalized_quote(source_text)
    if normalized:
        normalized_matches = tuple(
            record for record in human_records
            if normalized in _normalized_quote(record.content)
            or _normalized_quote(record.content) in normalized
        )
        if normalized_matches:
            cited_matches = tuple(
                record for record in normalized_matches
                if record.id in source_record_ids
            )
            chosen = (cited_matches or normalized_matches)[-1]
            return (chosen.id,), chosen.content
    cited = tuple(source for source in sources if source is not None)
    canonical = max(cited, key=lambda record: record.sequence)
    return source_record_ids, canonical.content


def _normalized_quote(value: str) -> str:
    return "".join(unicodedata.normalize("NFKC", value).casefold().split())


def admit_semantic_facts(
    facts: tuple[EngineeringSemanticFact, ...],
    *,
    work_revision_id: UUID,
) -> tuple[EngineeringSemanticFact, ...]:
    """Bind newly admitted facts to the exact Work Reality revision."""

    return tuple(
        fact
        if fact.admitted_work_revision_id is not None
        else fact.model_copy(update={"admitted_work_revision_id": work_revision_id})
        for fact in facts
    )


def _supersede(
    ledger: list[EngineeringSemanticFact],
    current: dict[UUID, EngineeringSemanticFact],
    by_key: dict[tuple[object, ...], EngineeringSemanticFact],
    fact_ids: tuple[UUID, ...],
) -> None:
    for fact_id in fact_ids:
        fact = current.pop(fact_id)
        superseded = fact.model_copy(
            update={"epistemic_status": SemanticEpistemicStatus.SUPERSEDED}
        )
        ledger[ledger.index(fact)] = superseded
        if by_key.get(fact.semantic_key) == fact:
            by_key.pop(fact.semantic_key)


def _require_explicit_supersession(candidate: EngineeringSemanticFactCandidate) -> None:
    if candidate.authority is not SemanticFactAuthority.HUMAN_EXPLICIT:
        raise InteractionInvariantViolation(
            "Only explicit Human semantics may remove current semantic truth"
        )


def _authority_rank(authority: SemanticFactAuthority) -> int:
    return 2 if authority is SemanticFactAuthority.HUMAN_EXPLICIT else 1


def _fact_identity(
    basis_fingerprint: str,
    candidate: EngineeringSemanticFactCandidate,
) -> UUID:
    payload = candidate.model_dump(mode="json", exclude={"candidate_id"})
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = sha256(canonical.encode("utf-8")).hexdigest()
    return uuid5(NAMESPACE_URL, f"spg:engineering-semantic-fact:{basis_fingerprint}:{digest}")
