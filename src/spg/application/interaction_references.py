"""Exact citation eligibility over the current WIC Owner basis, never authority."""

from uuid import UUID

from spg.domain.interaction import InteractionInvariantViolation


SUPPORTING_REALITY_KINDS = frozenset({
    "VERIFICATION", "RUNTIME_FACT", "COMPLETION", "ENGINEERING_FINDING", "STEERING_DECISION",
})


def normalize_supporting_references(values):
    normalized = []
    for raw in values:
        value = raw.strip()
        if not value:
            continue
        kind, separator, identity = value.partition(":")
        if separator != ":" or kind not in SUPPORTING_REALITY_KINDS:
            raise InteractionInvariantViolation(
                "Supporting Reality reference must use an allowed typed identity")
        try:
            UUID(identity)
        except ValueError as error:
            raise InteractionInvariantViolation(
                "Supporting Reality reference identity must be a UUID") from error
        normalized.append(f"{kind}:{identity}")
    return tuple(dict.fromkeys(normalized))


def available_interaction_references(basis):
    """References actually supplied by records, current Work and observed Owners."""
    active = getattr(basis, "active_work_context", None)
    return tuple(dict.fromkeys((
        *(ref for record in basis.records for ref in getattr(record, "supporting_references", ())),
        *(getattr(active, "relevant_reality_references", ()) if active is not None else ()),
        *(ref for observation in getattr(basis, "observed_reality", ())
          for ref in observation.evidence_references),
    )))


def available_supporting_references(basis):
    # Other Owner families remain available only in their own typed fields.
    values = []
    for ref in available_interaction_references(basis):
        if ref.partition(":")[0] not in SUPPORTING_REALITY_KINDS:
            continue
        try:
            values.extend(normalize_supporting_references((ref,)))
        except InteractionInvariantViolation:
            continue
    return tuple(dict.fromkeys(values))


def validate_supporting_references(values, basis):
    references = normalize_supporting_references(values)
    if not set(references) <= set(available_supporting_references(basis)):
        raise InteractionInvariantViolation("Interpretation cannot invent supporting Reality references")
    return references
