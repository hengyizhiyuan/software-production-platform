"""Intent Realization Kernel: bind one compiler result, derive obligations.

Existing WIC providers supply the replaceable semantic compiler transport.
Engineering Semantic Truth still governs facts and existing owners still admit
and execute effects. This owner never interprets raw language after compilation.
"""
from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5
import re

from spg.domain.interaction_actions import ActionSpeechAct, CanonicalOperation
from spg.domain.intent_realization import (
    EffectPredicate as P, ExpectedEffect, GovernedSemanticIR, ObligationPlane,
    ObligationState, ObservedEffect, OperationalIntent, ProductionIntent,
    SemanticArgument, SemanticClause, SemanticItem, SemanticKind, SemanticQuestion,
    SemanticOrigin, SemanticProvenance, TERMINAL_OBLIGATION_STATES,
    TurnObligation, TurnSemanticCandidate,
)


class IntentRealizationViolation(ValueError):
    """Safe generic signal plus source/owner evidence, never raw provider output."""


# Structured ontology normalization; no Human-language aliases or guessing.
_OPERATION_BINDINGS = {
    "CREATE_BRANCH_AND_CHECKOUT": CanonicalOperation.CREATE_AND_SWITCH_BRANCH,
    "CREATE_NEW_BRANCH_AND_SWITCH": CanonicalOperation.CREATE_AND_SWITCH_BRANCH,
    "NEW_BRANCH_AND_SWITCH": CanonicalOperation.CREATE_AND_SWITCH_BRANCH,
    "QUERY_BRANCH": CanonicalOperation.QUERY_CURRENT_BRANCH,
    "REQUEST_DELIVERY": CanonicalOperation.AUTHORIZE_DELIVERY,
}


# Closed argument contracts are the keys consumed by qualified owner adapters.
# Unknown structured fields cannot be silently discarded before an effect.
_OPERATION_ARGUMENTS = {
    CanonicalOperation.ACQUIRE_REPOSITORY: {"repository_source"},
    CanonicalOperation.INSPECT_REPOSITORY: {"repository_source"},
    CanonicalOperation.SEARCH_REPOSITORY: {"repository_source"},
    CanonicalOperation.QUERY_CURRENT_BRANCH: {"repository_source"},
    **{op: {"repository_source", "target_branch", "base_revision", "base_tree", "repository_identity"}
        for op in (CanonicalOperation.CREATE_BRANCH, CanonicalOperation.SWITCH_BRANCH,
            CanonicalOperation.CREATE_AND_SWITCH_BRANCH)},
    CanonicalOperation.SEARCH_GITHUB: {"query", "search_kind"},
    CanonicalOperation.SEARCH_WEB: {"query"},
    CanonicalOperation.FETCH_PUBLIC_RESOURCE: {"url"},
    CanonicalOperation.REQUEST_PREVIEW: {"candidate_revision"},
    CanonicalOperation.ACCEPT_CANDIDATE: {"candidate_revision"},
    CanonicalOperation.AUTHORIZE_DELIVERY: {"manifest_id", "candidate_revision", "target_branch", "expected_remote_revision"},
    CanonicalOperation.PUSH_BRANCH: {"authorization_id", "candidate_revision"},
    CanonicalOperation.CREATE_PR: {"authorization_id", "candidate_revision", "base_branch", "title", "body"},
}


def canonical_operation(value: str) -> CanonicalOperation:
    try:
        operation = _OPERATION_BINDINGS[value] if value in _OPERATION_BINDINGS else CanonicalOperation(value)
        if operation is CanonicalOperation.OTHER:
            raise ValueError("No qualified operational ontology for OTHER")
        return operation
    except ValueError as error:
        raise IntentRealizationViolation("SEMANTIC_TYPE_MISMATCH: unsupported structured operation") from error


def _branch_clause_effect(value: str, target: str) -> str | None:
    """Read a structured effect token with an optional exact target argument."""
    if value in {"CREATE_BRANCH", "SWITCH_BRANCH"}:
        return value
    match = re.fullmatch(r"(CREATE_BRANCH|SWITCH_BRANCH)(?::\s*|\s+)(\S+)", value)
    if match is None:
        return None
    if match.group(2) != target:
        raise IntentRealizationViolation(
            "ATOMIC_EFFECT_AUTHORITY_MISSING: clause effect target conflicts with governed branch")
    return match.group(1)


def _effect_span_covers_clause(effect_span: str, clause_span: str) -> bool:
    core = clause_span.strip(" \t\r\n,，;；、。")
    return bool(core) and (effect_span in clause_span or core in effect_span)


def _validate_provenance(provenance, records, *, current_record=None):
    if provenance.origin in {SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}:
        record = records.get(provenance.source_record_id)
        if (record is None or str(record.actor) != "HUMAN"
                or not provenance.source_text or provenance.source_text not in record.content):
            raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: source is not preserved Human evidence")
        if current_record is not None and record.id != current_record.id:
            raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: an old request cannot authorize a new effect")


def validate_semantic_candidate(candidate: TurnSemanticCandidate, basis) -> tuple[SemanticItem, ...]:
    records = {r.id: r for r in basis.records}
    latest = next(r for r in reversed(basis.records) if str(r.actor) == "HUMAN")
    historical_items = {f"{prior.id}:{item.item_id}": item
        for prior in getattr(basis, "governed_semantic_history", ())
        for item in prior.items}
    ids = {i.item_id for i in candidate.items}
    if len(ids) != len(candidate.items):
        raise IntentRealizationViolation("SEMANTIC_TYPE_MISMATCH: duplicate semantic identities")
    covered = set()
    represented = set()
    for clause in candidate.clauses:
        if clause.source_record_id != latest.id or clause.source_text not in latest.content:
            raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: clause is outside the current Human Turn")
        if not set(clause.semantic_item_ids) <= ids:
            raise IntentRealizationViolation("PRIMARY_INTENT_CLAUSE_LOST: clause has no semantic realization")
        if not set(clause.refers_to) <= historical_items.keys():
            raise IntentRealizationViolation(
                "ACTION_ARGUMENT_PROVENANCE_INVALID: contextual reference is outside governed semantic history")
        represented.update(clause.semantic_item_ids)
        # Coverage is syntax validation, not interpretation of clause meaning.
        start = latest.content.find(clause.source_text)
        while start >= 0:
            covered.update(range(start, start + len(clause.source_text)))
            start = latest.content.find(clause.source_text, start + 1)
    # Exact Human clause coverage does not require an independently observed
    # owner fact to masquerade as a Human statement. Only typed, non-Human
    # supplemental facts may be outside this map; their exact claims are
    # validated against the supplied owner observations below.
    for item in candidate.items:
        if (item.kind is SemanticKind.FACT and item.provenance
                and all(p.origin is SemanticOrigin.REPOSITORY_OBSERVED for p in item.provenance)
                and not item.observed_facts):
            raise IntentRealizationViolation(
                "ACTION_ARGUMENT_PROVENANCE_INVALID: REPOSITORY_OBSERVED FACT requires "
                "exact observed_facts key/value; omit an unsupported supplemental FACT")
    supplemental = {item.item_id for item in candidate.items
        if item.kind is SemanticKind.FACT and item.observed_facts
        and all(p.origin is SemanticOrigin.REPOSITORY_OBSERVED for p in item.provenance)}
    # Separators between exact clause spans carry no independent effect. Keep
    # question, conditional and path punctuation covered by a cited clause.
    separators = frozenset(",，;；、。")
    unlinked = ids - represented - supplemental
    if unlinked:
        raise IntentRealizationViolation(
            "PRIMARY_INTENT_CLAUSE_LOST: semantic items lack current-clause linkage: "
            + ", ".join(sorted(unlinked)))
    if any(not c.isspace() and c not in separators and n not in covered
            for n, c in enumerate(latest.content)):
        raise IntentRealizationViolation("PRIMARY_INTENT_CLAUSE_LOST: compiler must account for the entire current source")
    normalized = []
    observations = {reference: observation for observation in getattr(basis, "observed_reality", ())
        for reference in observation.evidence_references}
    basis_references = {reference for record in basis.records for reference in getattr(record, "supporting_references", ())}
    active = getattr(basis, "active_work_context", None)
    if active is not None:
        basis_references.update(active.relevant_reality_references)
    def validate_source(source, *, argument=None, key=None):
        _validate_provenance(source, records)
        if source.origin in {SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}:
            return
        reference = source.evidence_reference
        if source.origin is SemanticOrigin.MODEL_CANDIDATE and reference.startswith("compiler:"):
            if key in {"repository_source", "target_branch", "candidate_revision", "manifest_id", "authorization_id", "base_revision", "base_tree", "repository_identity", "expected_remote_revision"}:
                raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: model inference cannot supply an effect target")
            return
        if reference not in observations and reference not in basis_references:
            raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: non-Human evidence is outside the governed basis")
        if argument is not None and key in {"repository_source", "target_branch", "candidate_revision", "manifest_id", "authorization_id", "base_revision", "base_tree", "repository_identity", "expected_remote_revision"}:
            observation = observations.get(reference)
            if observation is None:
                raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: effect target requires an actual owner observation")
            values = {str(value) for value in observation.facts.values() if isinstance(value, (str, int))}
            values.update(value.removeprefix("refs/heads/") for value in tuple(values))
            if argument.value not in values:
                raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: argument is not in the referenced observation")
    for item in candidate.items:
        if item.supersedes:
            if item.kind is not SemanticKind.CORRECTION or not any(
                    p.source_record_id == latest.id and p.origin in {
                        SemanticOrigin.HUMAN_EXPLICIT,SemanticOrigin.HUMAN_CORRECTION} for p in item.provenance):
                raise IntentRealizationViolation(
                    "ACTION_SCOPE_INFLATION: supersession needs current Human correction; "
                    "FACT and ACTION items must leave supersedes empty")
            for reference in item.supersedes:
                witness = observations.get(f"obligation:{reference}")
                if witness is None or witness.owner != "turn-obligation-ledger" or witness.facts.get("state") not in {"PENDING","RUNNING"}:
                    raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: supersession target is outside current owner basis")
        if not set(item.depends_on) <= ids or item.item_id in item.depends_on:
            raise IntentRealizationViolation("SEMANTIC_TYPE_MISMATCH: invalid obligation dependencies")
        for source in item.provenance:
            validate_source(source)
        for key, claim in item.observed_facts.items():
            validate_source(claim.provenance, argument=claim, key=key)
            observed = observations.get(claim.provenance.evidence_reference)
            if (claim.provenance.origin is not SemanticOrigin.REPOSITORY_OBSERVED
                    or observed is None or str(observed.facts.get(key)) != claim.value):
                raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: fact claim differs from exact owner observation")
        if item.action is not None:
            action = item.action
            operation = canonical_operation(action.operation)
            if (not action.current and any(clause.temporal_scope == "CURRENT"
                    and clause.polarity == "AFFIRMATIVE"
                    and clause.speech_act in {ActionSpeechAct.EXPLICIT_REQUEST,
                        ActionSpeechAct.READ_ONLY_QUERY}
                    and item.item_id in clause.semantic_item_ids
                    for clause in candidate.clauses)):
                raise IntentRealizationViolation(
                    "SEMANTIC_TYPE_MISMATCH: current Human operation cannot be marked noncurrent")
            unsupported = (set(action.arguments) | set(action.unresolved_arguments)) - _OPERATION_ARGUMENTS[operation]
            if unsupported:
                raise IntentRealizationViolation("SEMANTIC_TYPE_MISMATCH: unconsumed operational argument keys: " + ", ".join(sorted(unsupported)))
            target = action.arguments.get("target_branch")
            if (target is not None and operation in {CanonicalOperation.CREATE_BRANCH,
                    CanonicalOperation.CREATE_AND_SWITCH_BRANCH}
                    and target.provenance.origin not in {SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}):
                raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: a new branch target needs literal Human provenance")
            if target is not None and target.value.startswith("refs/"):
                raise IntentRealizationViolation("SEMANTIC_TYPE_MISMATCH: branch targets require a local branch name, not a Git reference")
            if action.speech_act is ActionSpeechAct.READ_ONLY_QUERY and operation not in {
                    CanonicalOperation.QUERY_CURRENT_BRANCH, CanonicalOperation.INSPECT_REPOSITORY,
                    CanonicalOperation.SEARCH_REPOSITORY, CanonicalOperation.SEARCH_GITHUB,
                    CanonicalOperation.SEARCH_WEB, CanonicalOperation.FETCH_PUBLIC_RESOURCE}:
                raise IntentRealizationViolation("ACTION_SCOPE_INFLATION: read-only meaning cannot authorize a write")
            if action.speech_act is ActionSpeechAct.EXPLICIT_REQUEST:
                current = [s for s in item.provenance if s.origin in {
                    SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}
                    and s.source_record_id == latest.id]
                if not current:
                    if any(s.origin in {SemanticOrigin.HUMAN_EXPLICIT,
                            SemanticOrigin.HUMAN_CORRECTION} for s in item.provenance):
                        raise IntentRealizationViolation(
                            "ACTION_ARGUMENT_PROVENANCE_INVALID: an old request cannot authorize a new effect")
                    raise IntentRealizationViolation("ACTION_SCOPE_INFLATION: model inference is not Human authority")
                for source in current:
                    _validate_provenance(source, records, current_record=latest)
                for source in item.provenance:
                    if (source.origin in {SemanticOrigin.HUMAN_EXPLICIT,
                            SemanticOrigin.HUMAN_CORRECTION}
                            and source.source_record_id != latest.id
                            and not any(argument.provenance.source_record_id == source.source_record_id
                            and argument.provenance.source_text in source.source_text
                            and argument.value in source.source_text
                                for key, argument in action.arguments.items()
                                if key in {"target_branch", "repository_source"})):
                        raise IntentRealizationViolation(
                            "ACTION_ARGUMENT_PROVENANCE_INVALID: old Human item evidence is not a bound target")
            bound_arguments = dict(action.arguments)
            for key, argument in action.arguments.items():
                if (key in {"target_branch", "repository_source"}
                        and argument.provenance.origin in {
                            SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}
                        and argument.provenance.source_record_id == latest.id
                        and argument.value not in argument.provenance.source_text):
                    # A same-Turn anaphor may cite the action clause while its
                    # exact target literal is in an affirmative fact dependency.
                    # Rebind provenance to that unique governed Human span; a
                    # conflicting or unlinked model target remains invalid.
                    supports = tuple(dict.fromkeys(source for fact in candidate.items
                        if fact.item_id in item.depends_on and fact.kind is SemanticKind.FACT
                        and any(clause.polarity == "AFFIRMATIVE"
                            and clause.modality == "ASSERTION"
                            and fact.item_id in clause.semantic_item_ids
                            for clause in candidate.clauses)
                        for source in fact.provenance
                        if source.origin in {SemanticOrigin.HUMAN_EXPLICIT,
                            SemanticOrigin.HUMAN_CORRECTION}
                        and source.source_record_id == latest.id
                        and argument.value in source.source_text))
                    if len(supports) == 1:
                        argument = argument.model_copy(update={"provenance": supports[0]})
                        bound_arguments[key] = argument
                validate_source(argument.provenance, argument=argument, key=key)
                if (key in {"target_branch", "repository_source"}
                        and argument.provenance.origin in {
                            SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}
                        and argument.provenance.source_record_id != latest.id):
                    referenced = (historical_items[reference]
                        for clause in candidate.clauses
                        if item.item_id in clause.semantic_item_ids
                        for reference in clause.refers_to)
                    explicitly_referenced = any((prior.action is not None
                            and key in prior.action.arguments
                            and prior.action.arguments[key].value == argument.value
                            and prior.action.arguments[key].provenance.source_record_id
                                == argument.provenance.source_record_id)
                            or (prior.kind is SemanticKind.FACT
                                and argument.value in prior.statement
                                and any(source.source_record_id == argument.provenance.source_record_id
                                    for source in prior.provenance))
                            for prior in referenced)
                    # An admitted Work revision is also a governed reference
                    # to its source Turn. This supports an explicit recovery
                    # request after admission, even when a legacy compiler has
                    # no clause-level refers_to edge for the old URL.
                    active_revision = (None if active is None else active.work_revision)
                    admitted_source = (key == "repository_source"
                        and active_revision is not None
                        and basis.interaction.current_work_id == active_revision.work_id
                        and argument.provenance.source_record_id in active_revision.source_record_ids
                        and any(prior.source_record_id == argument.provenance.source_record_id
                            and any(prior_item.production is not None
                                and prior_item.production.repository_reference is not None
                                and prior_item.production.repository_reference.value == argument.value
                                and prior_item.production.repository_reference.provenance.source_record_id
                                    == argument.provenance.source_record_id
                                for prior_item in prior.items)
                            for prior in getattr(basis, "governed_semantic_history", ())))
                    if not explicitly_referenced and not admitted_source:
                        raise IntentRealizationViolation(
                            "ACTION_ARGUMENT_PROVENANCE_INVALID: old Human target lacks an exact governed reference")
                if argument.provenance.origin in {SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}:
                    if argument.value not in argument.provenance.source_text:
                        raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: argument differs from literal source")
                    if key == "target_branch" and not re.search(
                            rf"(?<![A-Za-z0-9._/-]){re.escape(argument.value)}(?![A-Za-z0-9._/-])",
                            argument.provenance.source_text):
                        raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: incomplete literal branch")
                if key in {"target_branch", "repository_source"} and argument.provenance.origin is SemanticOrigin.MODEL_CANDIDATE:
                    raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: inferred effect target is unbound")
            branch_effects = {
                CanonicalOperation.CREATE_BRANCH: {"CREATE_BRANCH"},
                CanonicalOperation.SWITCH_BRANCH: {"SWITCH_BRANCH"},
                CanonicalOperation.CREATE_AND_SWITCH_BRANCH: {"CREATE_BRANCH", "SWITCH_BRANCH"},
            }
            required_effects = branch_effects.get(operation, set())
            if action.atomic_branch_effects and not required_effects:
                raise IntentRealizationViolation("ACTION_SCOPE_INFLATION: branch effects on another operation")
            if (required_effects and action.current
                    and action.speech_act is ActionSpeechAct.EXPLICIT_REQUEST and target is not None):
                claims = action.atomic_branch_effects
                if len(claims) != len(required_effects) or {claim.effect for claim in claims} != required_effects:
                    raise IntentRealizationViolation("ATOMIC_EFFECT_AUTHORITY_MISSING: branch effects need exact separate Human claims")
                supporting_clauses = tuple(clause for clause in candidate.clauses
                    if item.item_id in clause.semantic_item_ids
                    and clause.speech_act is ActionSpeechAct.EXPLICIT_REQUEST
                    and clause.polarity == "AFFIRMATIVE"
                    and clause.modality == "REQUEST"
                    and clause.temporal_scope == "CURRENT")
                if {effect for clause in supporting_clauses
                        for value in clause.requested_effects
                        if (effect := _branch_clause_effect(value, target.value)) is not None} != required_effects:
                    raise IntentRealizationViolation(
                        "ATOMIC_EFFECT_AUTHORITY_MISSING: atomic effects lack an affirmative current clause")
                for claim in claims:
                    if claim.provenance.origin not in {SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}:
                        raise IntentRealizationViolation("ATOMIC_EFFECT_AUTHORITY_MISSING: model or owner evidence is not current Human consent")
                    _validate_provenance(claim.provenance, records, current_record=latest)
                    if (claim.target_branch != target.value or not any(
                            clause in supporting_clauses
                            and any(_branch_clause_effect(value, target.value) == claim.effect
                                for value in clause.requested_effects)
                            and _effect_span_covers_clause(
                                claim.provenance.source_text, clause.source_text)
                            for clause in candidate.clauses)):
                        raise IntentRealizationViolation("ATOMIC_EFFECT_AUTHORITY_MISSING: effect target or clause differs from governed intent")
                linked_clauses = tuple(clause for clause in candidate.clauses
                    if item.item_id in clause.semantic_item_ids)
                # A requested create-then-switch sequence is an internal
                # dependency of one atomic operation, not an unfulfilled
                # external condition. Both effects must already have exact
                # current Human clauses and no separate gating clause.
                if (operation is CanonicalOperation.CREATE_AND_SWITCH_BRANCH
                        and action.conditional and not action.unresolved
                        and not item.depends_on and len(linked_clauses) >= 2
                        and all(clause in supporting_clauses for clause in linked_clauses)
                        and any(tuple(clause.requested_effects) == ("CREATE_BRANCH",)
                            for clause in linked_clauses)
                        and any(tuple(clause.requested_effects) == ("SWITCH_BRANCH",)
                            for clause in linked_clauses)
                        and not any(clause.modality == "CONDITIONAL"
                            for clause in candidate.clauses)):
                    action = action.model_copy(update={"conditional": False})
            if operation in {CanonicalOperation.CREATE_BRANCH, CanonicalOperation.SWITCH_BRANCH,
                    CanonicalOperation.CREATE_AND_SWITCH_BRANCH} and action.speech_act is ActionSpeechAct.EXPLICIT_REQUEST:
                if "target_branch" not in action.arguments and not action.unresolved:
                    raise IntentRealizationViolation("EXPLICIT_ACTION_LOST_BEFORE_EXECUTION: missing branch target or explicit uncertainty")
            item = item.model_copy(update={"action": action.model_copy(update={
                "operation": operation.value, "arguments": bound_arguments})})
        if item.production is not None:
            production = item.production
            if production.current and production.unresolved_arguments:
                item = item.model_copy(update={"requires_human": True})
            if production.current and not any(s.origin in {SemanticOrigin.HUMAN_EXPLICIT,
                    SemanticOrigin.HUMAN_CORRECTION} and s.source_record_id == latest.id for s in item.provenance):
                raise IntentRealizationViolation("PRODUCTION_INTENT_SCOPE_INFLATION: current goal needs current Human provenance")
            if production.repository_reference:
                validate_source(production.repository_reference.provenance,
                    argument=production.repository_reference, key="repository_source")
            for argument in (*production.target_paths,*production.allowed_areas):
                validate_source(argument.provenance,argument=argument,key="explicit_target_path")
                if (argument.provenance.origin not in {SemanticOrigin.HUMAN_EXPLICIT,SemanticOrigin.HUMAN_CORRECTION}
                        or argument.value not in argument.provenance.source_text):
                    raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: explicit scope requires literal Human path authority")
            for argument in production.allowed_areas:
                path = argument.value
                if (not path.endswith("/**") or path.startswith("/") or "\\" in path
                        or any(part in {".","..",""} for part in path[:-3].split("/"))):
                    raise IntentRealizationViolation("SEMANTIC_TYPE_MISMATCH: literal allowed areas must be bounded repository-relative filesystem patterns ending in /**")
            if production.delivery_authorized:
                raise IntentRealizationViolation("ACTION_SCOPE_INFLATION: production intent cannot grant delivery authorization")
        normalized.append(item)
    for question in candidate.questions:
        validate_source(question.provenance)
    # An otherwise executable current effect cannot be silently converted into
    # a Human decision by the confidence gate after the compiler has finished.
    # Return this inconsistency to the same bounded semantic repair loop. A
    # genuinely unresolved target remains blocked by its typed argument or
    # requires_human marker instead of being promoted by a confidence bump.
    for item in normalized:
        if item.confidence >= .8 or item.requires_human:
            continue
        if (item.action is not None and item.action.current
                and item.action.speech_act in {
                    ActionSpeechAct.EXPLICIT_REQUEST, ActionSpeechAct.READ_ONLY_QUERY}
                and not item.action.conditional
                and not blocking_action_arguments(item.action)):
            raise IntentRealizationViolation(
                "LOW_CONFIDENCE: current action is below the execution gate; "
                "ground it in the exact current Human clause or retain a typed blocker")
        if (item.production is not None and item.production.current
                and not item.production.unresolved_arguments):
            raise IntentRealizationViolation(
                "LOW_CONFIDENCE: current production goal is below the admission gate; "
                "ground it in the exact current Human clause or retain a typed blocker")
    # Detect cycles in the compiler's structured graph before dispatch.
    graph = {i.item_id: i.depends_on for i in normalized}
    def visit(identity, active, done):
        if identity in active:
            raise IntentRealizationViolation("SEMANTIC_TYPE_MISMATCH: cyclic obligation dependencies")
        if identity in done:
            return
        for parent in graph[identity]:
            visit(parent, active | {identity}, done)
        done.add(identity)
    done = set()
    for identity in graph:
        visit(identity, set(), done)
    by_id = {item.item_id: item for item in normalized}
    repository_metadata = {"source", "url", "identity", "repository_identity",
        "revision", "tree", "branch", "current_branch", "repository_ref",
        "branches", "condition", "status", "ready", "paths", "product_id"}
    def has_read_obligation(identity, seen=frozenset()):
        if identity in seen:
            return False
        item = by_id[identity]
        if (item.action is not None and item.action.current
                and item.action.speech_act in {
                    ActionSpeechAct.EXPLICIT_REQUEST, ActionSpeechAct.READ_ONLY_QUERY}
                and canonical_operation(item.action.operation) in {
                    CanonicalOperation.INSPECT_REPOSITORY, CanonicalOperation.SEARCH_REPOSITORY}):
            return True
        return any(has_read_obligation(parent, seen | {identity}) for parent in item.depends_on)
    for item in normalized:
        subject = item.subject or ""
        if (item.kind in {SemanticKind.QUESTION, SemanticKind.ANALYSIS}
                and not item.requires_human and not item.answer and not item.observed_facts
                and (subject.startswith("repository.") or subject.startswith("repository:") and "#" in subject)
                and re.split(r"[.#]", subject)[-1] not in repository_metadata
                and not has_read_obligation(item.item_id)):
            raise IntentRealizationViolation(
                "PRIMARY_INTENT_CLAUSE_LOST: source-derived repository question "
                "needs a governed read obligation; acquisition metadata alone cannot answer it")
    branch_items = {}
    for item in normalized:
        if (item.action is None or not item.action.current
                or item.action.speech_act is not ActionSpeechAct.EXPLICIT_REQUEST):
            continue
        operation = canonical_operation(item.action.operation)
        if operation not in {CanonicalOperation.CREATE_BRANCH, CanonicalOperation.SWITCH_BRANCH}:
            continue
        target = item.action.arguments.get("target_branch")
        if target is not None:
            branch_items.setdefault(target.value, set()).add(operation)
    if any({CanonicalOperation.CREATE_BRANCH, CanonicalOperation.SWITCH_BRANCH} <= operations
            for operations in branch_items.values()):
        raise IntentRealizationViolation(
            "ATOMIC_EFFECT_SPLIT: same-target create and switch in one Turn require one CREATE_AND_SWITCH_BRANCH item")
    current_production = any(item.production and item.production.current for item in normalized)
    if not current_production and any(item.action and item.action.current
            and item.action.speech_act is ActionSpeechAct.EXPLICIT_REQUEST
            and canonical_operation(item.action.operation) is CanonicalOperation.REQUEST_PREVIEW
            and "candidate_revision" not in item.action.arguments
            for item in normalized):
        raise IntentRealizationViolation(
            "PRIMARY_INTENT_CLAUSE_LOST: Preview without an exact existing Candidate requires a current production goal")
    effect_ids = {item.item_id for item in normalized if (
        item.action and item.action.current and item.action.speech_act in {
            ActionSpeechAct.EXPLICIT_REQUEST, ActionSpeechAct.READ_ONLY_QUERY}) or (
        item.production and item.production.current) or item.kind in {
            SemanticKind.QUESTION, SemanticKind.ANALYSIS, SemanticKind.STATUS_QUERY}}
    by_id = {item.item_id: item for item in normalized}
    for item in normalized:
        if item.item_id in effect_ids and any(dependency not in effect_ids and
                by_id[dependency].kind not in {SemanticKind.FACT, SemanticKind.CONSTRAINT, SemanticKind.CORRECTION}
                for dependency in item.depends_on):
            raise IntentRealizationViolation("PRIMARY_INTENT_CLAUSE_LOST: current effect depends on unrequested future execution")
    return tuple(normalized)


def legacy_typed_candidate(assessment, basis) -> TurnSemanticCandidate:
    """Project existing structured ports, never recover missing intent from prose.

    This keeps historical/test compiler interfaces readable during migration.
    It is not a production language parser and grants no omitted action.
    """
    latest = next(r for r in reversed(basis.records) if str(r.actor) == "HUMAN")
    source = SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
        source_record_id=latest.id, source_text=latest.content)
    items = []
    for n, action in enumerate(assessment.action_candidates or ()):
        provenance = SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
            source_record_id=action.source_record_id, source_text=action.source_text)
        arguments = {key: SemanticArgument(value=value, provenance=provenance)
            for key, value in {"target_branch": action.target_branch,
                "repository_source": action.repository_source}.items() if value is not None}
        items.append(SemanticItem(item_id=f"legacy-action-{n}", kind=SemanticKind.OPERATIONAL_ACTION,
            statement=action.operation.value, provenance=(provenance,), confidence=action.confidence,
            action=OperationalIntent(operation=action.operation.value,
                arguments=arguments, speech_act=action.speech_act)))
    if not items:
        # A legacy compiler's summary remains advisory. Never infer a write or
        # production authorization from its response, motive or arbitrary text.
        items.append(SemanticItem(item_id="legacy-interaction", kind=SemanticKind.EXPLORE,
            statement=assessment.interpreted_motive or "Unresolved interaction meaning",
            provenance=(source,), confidence=.5))
    return TurnSemanticCandidate(items=tuple(items), clauses=(SemanticClause(
        clause_id="current-source", source_record_id=latest.id, source_text=latest.content,
        semantic_item_ids=tuple(i.item_id for i in items)),))


class IntentRealizationKernel:
    def govern(self, candidate, basis, *, engineering_fact_ids=()) -> GovernedSemanticIR:
        raw = candidate.semantic_intent
        legacy = raw is None
        raw = legacy_typed_candidate(candidate, basis) if legacy else raw
        items = validate_semantic_candidate(raw, basis)
        # One Interaction has one repository asset owner. Two distinct source
        # targets cannot both be authorized by the same acquisition Turn, even
        # when each literal independently has sound Human provenance.
        acquisitions = tuple(item for item in items if item.action is not None
            and item.action.current and item.action.speech_act is ActionSpeechAct.EXPLICIT_REQUEST
            and canonical_operation(item.action.operation) is CanonicalOperation.ACQUIRE_REPOSITORY)
        sources = {item.action.arguments["repository_source"].value for item in acquisitions
            if "repository_source" in item.action.arguments}
        if len(sources) > 1:
            blocked = {item.item_id for item in acquisitions}
            items = tuple(item.model_copy(update={"requires_human": True,
                "action": item.action.model_copy(update={
                    "unresolved_arguments": tuple(dict.fromkeys(
                        (*item.action.unresolved_arguments, "repository_source"))),
                    "unresolved": (*item.action.unresolved,
                        "Multiple repository sources need one Human-selected Interaction target.")})})
                if item.item_id in blocked else item for item in items)
            if not any(question.blocks_current_step and question.requires_human
                    for question in raw.questions):
                raw = raw.model_copy(update={"questions": (*raw.questions, SemanticQuestion(
                    question="Which repository source should this Interaction use?",
                    blocks_current_step=True, requires_human=True,
                    provenance=SemanticProvenance(origin=SemanticOrigin.MODEL_CANDIDATE,
                        evidence_reference="compiler:question")))})
        ready = [observation for observation in getattr(basis, "observed_reality", ())
            if observation.facts.get("condition") == "READY"]
        if len(ready) == 1:
            observation = ready[0]
            provenance = SemanticProvenance(origin=SemanticOrigin.REPOSITORY_OBSERVED,
                evidence_reference=observation.evidence_references[0])
            bound = []
            for item in items:
                if item.action is not None and canonical_operation(item.action.operation) in {
                        CanonicalOperation.CREATE_BRANCH, CanonicalOperation.CREATE_AND_SWITCH_BRANCH, CanonicalOperation.SWITCH_BRANCH}:
                    args = dict(item.action.arguments)
                    for key, owner_key in (("base_revision", "revision"), ("base_tree", "tree"),
                            ("repository_identity", "repository_identity")):
                        if key not in args and observation.facts.get(owner_key):
                            args[key] = SemanticArgument(value=observation.facts[owner_key], provenance=provenance)
                    item = item.model_copy(update={"action": item.action.model_copy(update={"arguments": args})})
                bound.append(item)
            items = tuple(bound)
        candidates = [observation for observation in getattr(basis, "observed_reality", ())
            if observation.owner == "candidate-verification" and observation.facts.get("candidate_revision")]
        if len(candidates) == 1:
            observed = candidates[0]
            origin = SemanticProvenance(origin=SemanticOrigin.REPOSITORY_OBSERVED,
                evidence_reference=observed.evidence_references[0])
            items = tuple(item.model_copy(update={"action": item.action.model_copy(update={"arguments": {
                **item.action.arguments, "candidate_revision": SemanticArgument(
                    value=observed.facts["candidate_revision"], provenance=origin)}})})
                if item.action and canonical_operation(item.action.operation) in {
                    CanonicalOperation.REQUEST_PREVIEW, CanonicalOperation.ACCEPT_CANDIDATE}
                and "candidate_revision" not in item.action.arguments else item for item in items)
        latest = next(r for r in reversed(basis.records) if str(r.actor) == "HUMAN")
        return GovernedSemanticIR(**raw.model_copy(update={"items": items}).model_dump(),
            id=uuid5(NAMESPACE_URL, f"watt:irk:{basis.interaction.id}:{basis.basis_fingerprint}"),
            interaction_id=basis.interaction.id, source_record_id=latest.id,
            basis_fingerprint=basis.basis_fingerprint, engineering_fact_ids=engineering_fact_ids,
            neutral_semantic_extractions=getattr(candidate,"neutral_semantic_extractions",()),
            semantic_fact_candidates=getattr(candidate,"semantic_fact_candidates",()),
            compiler_reference=candidate.provider_identity, legacy_typed_projection=legacy)

    def obligations(self, ir: GovernedSemanticIR, turn_id: UUID,
            *, work_question_step_id: UUID | None = None) -> tuple[TurnObligation, ...]:
        work_question_step_id = work_question_step_id or ir.work_question_step_id
        identities = {i.item_id: uuid5(turn_id, f"irk-obligation:{i.item_id}") for i in ir.items}
        obligations = []
        effect_ids = {item.item_id for item in ir.items if (
            item.action and item.action.current and item.action.speech_act in {
                ActionSpeechAct.EXPLICIT_REQUEST, ActionSpeechAct.READ_ONLY_QUERY}) or (
            item.production and item.production.current) or (work_question_step_id is not None
            and item.kind is SemanticKind.CONSTRAINT) or (item.kind is SemanticKind.CORRECTION and item.supersedes) or item.kind in {
                SemanticKind.QUESTION, SemanticKind.ANALYSIS, SemanticKind.STATUS_QUERY}}
        by_id = {item.item_id: item for item in ir.items}
        def unresolved_dependency(item):
            return any(by_id[dependency].requires_human or by_id[dependency].confidence < .8
                or unresolved_dependency(by_id[dependency]) for dependency in item.depends_on)
        for item in ir.items:
            operation = None
            if item.action is not None and item.action.current and item.action.speech_act in {
                    ActionSpeechAct.EXPLICIT_REQUEST, ActionSpeechAct.READ_ONLY_QUERY}:
                operation = canonical_operation(item.action.operation)
                effects = expected_effects(operation, item.action.arguments)
                plane = ObligationPlane.ACTION
            elif item.production is not None and item.production.current:
                effects = (ExpectedEffect(predicate=P.WORK_ADMITTED),)
                plane = ObligationPlane.WORK
            elif work_question_step_id is not None and item.kind is SemanticKind.CONSTRAINT:
                effects = (ExpectedEffect(predicate=P.WORK_QUESTION_RESOLVED,
                    target=str(work_question_step_id),
                    parameters={"constraint": item.statement}),)
                plane = ObligationPlane.WORK
            elif item.kind in {SemanticKind.QUESTION, SemanticKind.ANALYSIS, SemanticKind.STATUS_QUERY}:
                effects = (ExpectedEffect(predicate=P.QUESTION_ANSWERED),)
                plane = ObligationPlane.INTERACTION
            elif item.kind is SemanticKind.CORRECTION and item.supersedes:
                effects = tuple(ExpectedEffect(predicate=P.OBLIGATION_SUPERSEDED,target=target) for target in item.supersedes)
                plane = ObligationPlane.INTERACTION
            else:
                continue
            needs_human = item.requires_human or item.confidence < .8 or unresolved_dependency(item) or bool(
                item.action and (item.action.conditional or blocking_action_arguments(item.action))) or bool(
                item.production and item.production.current and item.production.unresolved_arguments)
            obligations.append(TurnObligation(id=identities[item.item_id], turn_id=turn_id,
                semantic_ir_id=ir.id, semantic_item_id=item.item_id, plane=plane,
                operation=operation, expected_effects=effects,
                state=ObligationState.REQUIRES_HUMAN if needs_human else ObligationState.PENDING,
                blocker_reference=f"semantic-ir:{ir.id}:item:{item.item_id}:unresolved" if needs_human else None,
                depends_on=tuple(identities[d] for d in item.depends_on if d in effect_ids)))
        materialized = {o.id for o in obligations}
        if any(set(o.depends_on) - materialized for o in obligations):
            raise IntentRealizationViolation("PRIMARY_INTENT_CLAUSE_LOST: effect depends on a non-materialized item")
        return tuple(obligations)


def expected_effects(operation, arguments) -> tuple[ExpectedEffect, ...]:
    branch = arguments.get("target_branch")
    branch = None if branch is None else branch.value
    effects = {
        CanonicalOperation.ACQUIRE_REPOSITORY: (P.REPOSITORY_READY,),
        CanonicalOperation.INSPECT_REPOSITORY: (P.REPOSITORY_INSPECTED,),
        CanonicalOperation.SEARCH_REPOSITORY: (P.REPOSITORY_INSPECTED,),
        CanonicalOperation.CREATE_BRANCH: (P.BRANCH_EXISTS,),
        CanonicalOperation.SWITCH_BRANCH: (P.CURRENT_BRANCH,),
        CanonicalOperation.CREATE_AND_SWITCH_BRANCH: (P.BRANCH_EXISTS, P.CURRENT_BRANCH),
        CanonicalOperation.QUERY_CURRENT_BRANCH: (P.CURRENT_BRANCH,),
        CanonicalOperation.SEARCH_GITHUB: (P.SEARCH_EVIDENCE,),
        CanonicalOperation.SEARCH_WEB: (P.SEARCH_EVIDENCE,),
        CanonicalOperation.FETCH_PUBLIC_RESOURCE: (P.SEARCH_EVIDENCE,),
        CanonicalOperation.REQUEST_PREVIEW: (P.PREVIEW_VERIFIED,),
        CanonicalOperation.ACCEPT_CANDIDATE: (P.CANDIDATE_ACCEPTED,),
        CanonicalOperation.AUTHORIZE_DELIVERY: (P.DELIVERY_AUTHORIZED,),
        CanonicalOperation.PUSH_BRANCH: (P.REMOTE_REF,),
        CanonicalOperation.CREATE_PR: (P.PULL_REQUEST_OBSERVED,),
    }.get(operation, (P.OWNER_EFFECT_OBSERVED,))
    revision = arguments.get("candidate_revision") or arguments.get("base_revision")
    source = arguments.get("repository_source")
    query = arguments.get("query") or arguments.get("url")
    return tuple(ExpectedEffect(predicate=p,
        parameters={"query":query.value} if p is P.SEARCH_EVIDENCE and query is not None else {}, target=branch if p in {P.BRANCH_EXISTS, P.CURRENT_BRANCH,
        P.REMOTE_REF} else operation.value if p is P.SEARCH_EVIDENCE else
        source.value if p is P.REPOSITORY_READY and source is not None else None,
        exact_revision=None if revision is None else revision.value) for p in effects)


def effect_matches(expected: ExpectedEffect, observed: ObservedEffect) -> bool:
    facts = observed.facts
    branch = facts.get("current_branch") or facts.get("repository_ref")
    if isinstance(branch, str) and branch.startswith("refs/heads/"):
        branch = branch.removeprefix("refs/heads/")
    checks = {
        P.REPOSITORY_READY: lambda: facts.get("condition") == "READY" and (
            expected.target is None or facts.get("source") == expected.target) and all(
            isinstance(facts.get(k), str) and re.fullmatch(r"[0-9a-f]{40}", facts[k]) for k in ["revision", "tree"]),
        P.BRANCH_EXISTS: lambda: (expected.exact_revision is None or facts.get("revision") == expected.exact_revision) and (
            expected.target in facts.get("branches", ()) or (
            facts.get("condition") == "READY" and branch == expected.target and bool(facts.get("revision")))),
        P.CURRENT_BRANCH: lambda: bool(branch) and (expected.target is None or branch == expected.target) and (expected.exact_revision is None or facts.get("revision") == expected.exact_revision),
        P.REPOSITORY_INSPECTED: lambda: bool(facts.get("inspected_paths") or facts.get("inspected_references")),
        P.SEARCH_EVIDENCE: lambda: facts.get("search_state") == "COMPLETED" and bool(facts.get("evidence_ids"))
            and expected.target in facts.get("search_operations", ()) and (
                not expected.parameters.get("query") or expected.parameters["query"] in facts.get("queries", ())),
        P.PREVIEW_VERIFIED: lambda: facts.get("preview_status") == "READY" and facts.get("served_verification") == "PASS",
        P.CANDIDATE_ACCEPTED: lambda: facts.get("acceptance") == "ACCEPT" and bool(facts.get("candidate_revision")),
        P.DELIVERY_AUTHORIZED: lambda: bool(facts.get("delivery_authorization_id")) and bool(facts.get("candidate_revision")),
        P.REMOTE_REF: lambda: bool(expected.exact_revision) and facts.get("remote_revision") == expected.exact_revision and (expected.target is None or facts.get("target_branch") == expected.target),
        P.PULL_REQUEST_OBSERVED: lambda: bool(facts.get("pull_request_url")) and bool(facts.get("candidate_revision")),
        P.WORK_ADMITTED: lambda: bool(facts.get("work_id")) and bool(facts.get("work_revision_id")),
        P.WORK_QUESTION_RESOLVED: lambda: observed.owner == "work-steering-question"
            and facts.get("question_step_id") == expected.target
            and facts.get("question_retired") is True
            and bool(facts.get("work_revision_id"))
            and expected.parameters.get("constraint") in facts.get("constraints", ()),
        P.QUESTION_ANSWERED: lambda: facts.get("answer_governed") is True,
        P.OBLIGATION_SUPERSEDED: lambda: observed.owner == "turn-obligation-ledger" and
            expected.target in facts.get("superseded_obligation_ids",()),
        P.OWNER_EFFECT_OBSERVED: lambda: False,
    }
    candidate_effects = {P.PREVIEW_VERIFIED, P.CANDIDATE_ACCEPTED, P.DELIVERY_AUTHORIZED, P.PULL_REQUEST_OBSERVED}
    if expected.predicate in candidate_effects and (not expected.exact_revision or facts.get("candidate_revision") != expected.exact_revision):
        return False
    return bool(checks[expected.predicate]())


def reconcile_obligation(obligation, observed) -> TurnObligation:
    if not all(effect_matches(effect, observed) for effect in obligation.expected_effects):
        raise IntentRealizationViolation("EXPECTED_EFFECT_NOT_REALIZED: owner Reality does not satisfy this obligation")
    return obligation.model_copy(update={"state": ObligationState.SATISFIED,
        "observed_effect": observed, "version": obligation.version + 1})


def validate_turn_completion(ir, obligations) -> None:
    if ir is None:
        raise IntentRealizationViolation("SEMANTIC_TYPE_MISMATCH: a Human Turn needs governed IR before finalization")
    if any(o.state not in TERMINAL_OBLIGATION_STATES for o in obligations):
        raise IntentRealizationViolation("RESPONSE_ACTION_INCONSISTENCY: narrative cannot close an unfulfilled obligation")
    for obligation in obligations:
        TurnObligation.model_validate(obligation.model_dump())
        if obligation.semantic_ir_id != ir.id:
            raise IntentRealizationViolation("SEMANTIC_TYPE_MISMATCH: obligation belongs to another interpretation")
        if obligation.state is ObligationState.SATISFIED and not all(
                effect_matches(effect, obligation.observed_effect) for effect in obligation.expected_effects):
            raise IntentRealizationViolation("EXPECTED_EFFECT_NOT_REALIZED: completion requires reconciled owner effects")


def latest_assessment_revision(revision, read_revision):
    """Asset/native observation revisions preserve, rather than erase, intent.

    Stop at the latest actual assessment; an earlier matching goal cannot cover
    a later different Human decision. Invalid/cyclic ancestry fails closed.
    """
    seen = set()
    while revision is not None and revision.id not in seen:
        seen.add(revision.id)
        if revision.source_assessment_id is not None:
            return revision
        revision = read_revision(revision.previous_revision_id) if revision.previous_revision_id else None
    return None


def blocking_action_arguments(action):
    """Typed operation requirements, independent of uncertainty prose.

    Repository workspace location and other owner defaults are not Human-owned
    effect targets. A missing mandatory target or explicitly unresolved argument
    remains blocking; optional descriptive uncertainty stays in the IR.
    """
    required = {
        CanonicalOperation.ACQUIRE_REPOSITORY: {"repository_source"},
        CanonicalOperation.CREATE_BRANCH: {"target_branch"},
        CanonicalOperation.SWITCH_BRANCH: {"target_branch"},
        CanonicalOperation.CREATE_AND_SWITCH_BRANCH: {"target_branch"},
        CanonicalOperation.SEARCH_GITHUB: {"query"},
        CanonicalOperation.SEARCH_WEB: {"query"},
        CanonicalOperation.FETCH_PUBLIC_RESOURCE: {"url"},
        CanonicalOperation.REQUEST_PREVIEW: {"candidate_revision"},
        CanonicalOperation.ACCEPT_CANDIDATE: {"candidate_revision"},
        CanonicalOperation.AUTHORIZE_DELIVERY: {"manifest_id", "candidate_revision", "target_branch"},
        CanonicalOperation.PUSH_BRANCH: {"authorization_id", "candidate_revision"},
        CanonicalOperation.CREATE_PR: {"authorization_id", "candidate_revision", "base_branch", "title", "body"},
    }.get(canonical_operation(action.operation), set())
    return (required - action.arguments.keys()) | set(action.unresolved_arguments)


def current_step_semantic_items(ir):
    """Current effects and their prerequisites, never unrelated future decisions.

    Without an executable step, advisory/Human decisions remain visible. An
    explicitly governed dependency still blocks its dependent current operation.
    """
    if ir is None:
        return ()
    by_id = {item.item_id: item for item in ir.items}
    current = {item.item_id for item in ir.items if (
        item.action and item.action.current and item.action.speech_act in {
            ActionSpeechAct.EXPLICIT_REQUEST, ActionSpeechAct.READ_ONLY_QUERY}) or (
        item.production and item.production.current)}
    if not current:
        return ir.items
    def include(identity):
        for dependency in by_id[identity].depends_on:
            if dependency not in current:
                current.add(dependency)
                include(dependency)
    for identity in tuple(current):
        include(identity)
    return tuple(item for item in ir.items if item.item_id in current)


def executable_semantic_actions(ir, *, operations=None):
    """Only already-governed current actions; uncertainty never grants effects."""
    if ir is None:
        return ()
    return tuple(item for item in ir.operational_requests if item.confidence >= .8
        and not item.requires_human and not item.action.conditional and not blocking_action_arguments(item.action)
        and (operations is None or canonical_operation(item.action.operation) in operations))


def legacy_action_projection(ir):
    """Compatibility DTO derived from IR, never a second semantic authority."""
    from spg.domain.interaction_actions import InteractionActionCandidate
    result = []
    for item in ir.items:
        if item.action is None:
            continue
        human = next((p for p in item.provenance if p.source_record_id == ir.source_record_id
            and p.origin in {SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}), None)
        if human is None:
            continue
        args = item.action.arguments
        operation = canonical_operation(item.action.operation)
        operation = {CanonicalOperation.QUERY_CURRENT_BRANCH: CanonicalOperation.QUERY_BRANCH,
            CanonicalOperation.AUTHORIZE_DELIVERY: CanonicalOperation.REQUEST_DELIVERY}.get(operation, operation)
        result.append(InteractionActionCandidate(operation=operation,
            speech_act=item.action.speech_act, source_record_id=human.source_record_id,
            source_text=human.source_text,
            target_branch=None if "target_branch" not in args else args["target_branch"].value,
            repository_source=None if "repository_source" not in args else args["repository_source"].value,
            confidence=item.confidence))
    return tuple(result)


def production_evidence(ir):
    """Compatibility shape for admitted production consumers, derived only from IR."""
    from spg.domain.response_contract import ProductionIntentEvidence
    current = bool(ir and ir.current_production)
    source = None if ir is None else ir.repository_source
    return ProductionIntentEvidence(production_request=current, repository_relevant=current,
        action_requested=current, repository_source=source)


def current_dependent_analysis_requests(ir) -> tuple[str, ...]:
    """Current Human analysis requests that depend on the current product goal."""
    if ir is None:
        return ()
    goals = {item.item_id for item in ir.items
        if item.production is not None and item.production.current}
    requested = {item_id for clause in ir.clauses
        if clause.source_record_id == ir.source_record_id
        and clause.speech_act is ActionSpeechAct.EXPLICIT_REQUEST
        and clause.polarity == "AFFIRMATIVE" and clause.modality == "REQUEST"
        and clause.temporal_scope == "CURRENT" for item_id in clause.semantic_item_ids}
    return tuple(dict.fromkeys(item.statement for item in ir.items
        if item.kind is SemanticKind.ANALYSIS and item.answer is None
        and item.item_id in requested and goals.intersection(item.depends_on)))


def project_interaction_candidate(candidate, ir):
    """WIC consumes canonical IR; all compatibility values have one source."""
    from spg.domain.conversation import ConversationTurnIntent as I
    updates = {"semantic_intent": ir, "action_candidates": legacy_action_projection(ir),
        "neutral_semantic_extractions": ir.neutral_semantic_extractions,
        "semantic_fact_candidates": ir.semantic_fact_candidates,
        "unresolved_material_questions": tuple(dict.fromkeys(
            q.question for q in ir.questions if q.blocks_current_step and not q.safe_reversible_assumption))}
    current_request_ids = {item_id for clause in ir.clauses
        if clause.source_record_id == ir.source_record_id
        and clause.speech_act is ActionSpeechAct.EXPLICIT_REQUEST
        and clause.polarity == "AFFIRMATIVE" and clause.modality == "REQUEST"
        and clause.temporal_scope == "CURRENT" for item_id in clause.semantic_item_ids}
    requested_analysis = tuple(item.statement for item in ir.items
        if item.item_id in current_request_ids and item.kind is SemanticKind.ANALYSIS
        and item.answer is None)
    constraints = tuple(item.statement for item in ir.items if item.kind is SemanticKind.CONSTRAINT)
    updates["candidate_constraints"] = tuple(dict.fromkeys((
        *((candidate.candidate_constraints) if ir.legacy_typed_projection else ()), *constraints,
        *(value for goal in ir.current_production for value in goal.scope),
        *(f"Excluded from this Work: {value}" for goal in ir.current_production
            for value in goal.exclusions))))
    if not ir.legacy_typed_projection:
        from spg.domain.interaction import InterpretationMeaning, InterpretationMeaningKind as M, WorkFocusClassification as F
        mapping = {SemanticKind.OPERATIONAL_ACTION: M.REQUEST, SemanticKind.PRODUCTION_INTENT: M.OBJECTIVE_OR_SCOPE_CHANGE,
            SemanticKind.FACT: M.FACT, SemanticKind.CONSTRAINT: M.CONSTRAINT, SemanticKind.CORRECTION: M.CORRECTION,
            SemanticKind.QUESTION: M.QUESTION, SemanticKind.STATUS_QUERY: M.QUESTION, SemanticKind.ANALYSIS: M.QUESTION}
        updates["meanings"] = tuple(InterpretationMeaning(kind=mapping.get(item.kind,M.CONTEXT),
            statement=item.statement,source_record_ids=tuple(dict.fromkeys(source.source_record_id
                for source in item.provenance if source.source_record_id)) or (ir.source_record_id,),
            confidence=item.confidence,clarification_required=item.requires_human,
            rationale=f"Governed semantic item: {ir.id}:{item.item_id}") for item in ir.items)
        updates["candidate_context"] = tuple(item.statement for item in ir.items if item.kind is SemanticKind.FACT)
        updates["current_requests"] = ()
        updates["design_intent_frame"] = next((item.design_frame for item in ir.items
            if item.kind is SemanticKind.DESIGN and item.design_frame is not None), None)
        updates["focus_classification"] = F.ON_TOPIC if ir.current_production or ir.operational_requests else F.RELEVANT_EXPLORATION
        if any(goal.new_work for goal in ir.current_production):
            updates["focus_classification"] = F.UNRELATED_NEW_DEMAND
    else:
        # Historical/test advisory ports retain readable questions; they cannot
        # discover any omitted operation or current production goal from prose.
        updates["unresolved_material_questions"] = candidate.unresolved_material_questions
    if ir.current_production:
        goals = ir.current_production
        from spg.domain.design_intent import (
            DesignIntentFrame, DesignObjectType, DesignScopeLevel, DesignCollaborationMode,
        )
        systemic = any(goal.systemic_design for goal in goals)
        bounded = all(goal.bounded_change for goal in goals)
        # A parallel legacy design frame cannot inflate canonical production
        # into an unrequested system-wide design/prerequisite artifact cycle.
        updates["design_intent_frame"] = DesignIntentFrame(
            design_subject="; ".join(goal.objective for goal in goals),
            object_type=DesignObjectType.PRODUCT_SYSTEM if systemic else DesignObjectType.FEATURE,
            scope_level=DesignScopeLevel.PRODUCT if systemic else
                DesignScopeLevel.IMPLEMENTATION if bounded else DesignScopeLevel.CAPABILITY,
            collaboration_mode=DesignCollaborationMode.DESIGN if systemic else DesignCollaborationMode.EXECUTION,
            desired_outcome="; ".join(goal.primary_change for goal in goals),
            ambiguities=tuple(value for goal in goals for value in goal.unresolved),
            confidence=min(item.confidence for item in ir.items if item.production and item.production.current))
        outcomes = [goal.primary_change for goal in goals]
        if any(goal.preview_required for goal in goals):
            outcomes.append("Provide an independently verified Preview of the exact produced Candidate for Human review.")
        updates.update(interpreted_motive="; ".join(goal.objective for goal in goals),
            desired_outcome="; ".join(outcomes),
            current_requests=tuple(dict.fromkeys((
                *(goal.primary_change for goal in goals), *requested_analysis))),
            turn_intent=candidate.turn_intent if candidate.turn_intent in {I.BUILD, I.MODIFY, I.CONTINUE_CURRENT_WORK}
                else I.ACTION_REQUEST)
    elif ir.operational_requests:
        updates["turn_intent"] = I.ACTION_REQUEST if any(
            item.action.speech_act is ActionSpeechAct.EXPLICIT_REQUEST for item in ir.operational_requests) else I.DIRECT_QUESTION
    elif any(item.kind in {SemanticKind.QUESTION, SemanticKind.ANALYSIS, SemanticKind.STATUS_QUERY} for item in ir.items):
        updates["turn_intent"] = I.DIRECT_QUESTION
    return candidate.model_copy(update=updates)
