"""Declared semantic oracles for tests; no language routing or phrase grammar."""
from uuid import UUID
from spg.domain.intent_realization import (
    AtomicBranchEffect, GovernedSemanticIR, OperationalIntent, ProductionIntent, SemanticArgument,
    SemanticClause, SemanticItem, SemanticKind, SemanticOrigin, SemanticProvenance,
    SemanticQuestion, TurnSemanticCandidate,
)
from spg.domain.interaction_actions import ActionSpeechAct


def semantic_candidate(record, *, kind=SemanticKind.EXPLORE, statement=None,
        operation=None, arguments=None, production=None, questions=(), requires_human=False,
        altitude="DOMAIN", uncertain=False, extra_items=(), provenance=None, observed_facts=None, design_frame=None):
    source = provenance or SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
        source_record_id=record.id, source_text=record.content)
    branch_effects = {"CREATE_BRANCH": ("CREATE_BRANCH",),
        "SWITCH_BRANCH": ("SWITCH_BRANCH",),
        "CREATE_AND_SWITCH_BRANCH": ("CREATE_BRANCH", "SWITCH_BRANCH")}.get(str(operation), ())
    action = None if operation is None else OperationalIntent(operation=operation,
        speech_act=ActionSpeechAct.EXPLICIT_REQUEST,
        arguments={key: SemanticArgument(value=value, provenance=source) for key, value in (arguments or {}).items()},
        atomic_branch_effects=tuple(AtomicBranchEffect(effect=effect,
            target_branch=(arguments or {})["target_branch"], provenance=source)
            for effect in branch_effects if "target_branch" in (arguments or {})))
    if action is not None:
        kind = SemanticKind.OPERATIONAL_ACTION
    if production is not None:
        kind = SemanticKind.PRODUCTION_INTENT
    item = SemanticItem(item_id="meaning", kind=kind, statement=statement or record.content,
        provenance=(source,), action=action, production=production, observed_facts=observed_facts or {}, design_frame=design_frame,
        confidence=1, requires_human=requires_human)
    items = (item, *extra_items)
    return TurnSemanticCandidate(items=items, clauses=(SemanticClause(clause_id="current-source",
        source_record_id=record.id, source_text=record.content,
        semantic_item_ids=tuple(item.item_id for item in items),
        speech_act=ActionSpeechAct.EXPLICIT_REQUEST if branch_effects else None,
        polarity="AFFIRMATIVE" if branch_effects else "UNRESOLVED",
        modality="REQUEST" if branch_effects else "UNRESOLVED",
        temporal_scope="CURRENT" if branch_effects else "UNRESOLVED",
        requested_effects=branch_effects),), questions=questions,
        human_abstraction_level=altitude, uncertain=uncertain)


def governed_ir(record, **options):
    raw = semantic_candidate(record, **options)
    return GovernedSemanticIR(**raw.model_dump(), id=UUID(int=700),
        interaction_id=record.interaction_id, source_record_id=record.id,
        basis_fingerprint="a" * 64, compiler_reference="fixture:declared-irk")


def question(text, *, blocking=True, human=False, reversible=False, decision_value=70):
    return SemanticQuestion(question=text, blocks_current_step=blocking, requires_human=human,
        safe_reversible_assumption=reversible, decision_value=decision_value,
        provenance=SemanticProvenance(origin=SemanticOrigin.MODEL_CANDIDATE,
            evidence_reference="compiler:question"))
