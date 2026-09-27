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
    SemanticArgument, SemanticClause, SemanticItem, SemanticKind,
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
        represented.update(clause.semantic_item_ids)
        # Coverage is syntax validation, not interpretation of clause meaning.
        start = latest.content.find(clause.source_text)
        while start >= 0:
            covered.update(range(start, start + len(clause.source_text)))
            start = latest.content.find(clause.source_text, start + 1)
    if represented != ids or any(not c.isspace() and n not in covered for n, c in enumerate(latest.content)):
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
                raise IntentRealizationViolation("ACTION_SCOPE_INFLATION: supersession needs current Human correction")
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
                    SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}]
                if not current:
                    raise IntentRealizationViolation("ACTION_SCOPE_INFLATION: model inference is not Human authority")
                for source in current:
                    _validate_provenance(source, records, current_record=latest)
            for key, argument in action.arguments.items():
                validate_source(argument.provenance, argument=argument, key=key)
                if argument.provenance.origin in {SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION}:
                    if argument.value not in argument.provenance.source_text:
                        raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: argument differs from literal source")
                    if key == "target_branch" and not re.search(
                            rf"(?<![A-Za-z0-9._/-]){re.escape(argument.value)}(?![A-Za-z0-9._/-])",
                            argument.provenance.source_text):
                        raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: incomplete literal branch")
                if key in {"target_branch", "repository_source"} and argument.provenance.origin is SemanticOrigin.MODEL_CANDIDATE:
                    raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: inferred effect target is unbound")
            if operation in {CanonicalOperation.CREATE_BRANCH, CanonicalOperation.SWITCH_BRANCH,
                    CanonicalOperation.CREATE_AND_SWITCH_BRANCH} and action.speech_act is ActionSpeechAct.EXPLICIT_REQUEST:
                if "target_branch" not in action.arguments and not action.unresolved:
                    raise IntentRealizationViolation("EXPLICIT_ACTION_LOST_BEFORE_EXECUTION: missing branch target or explicit uncertainty")
            item = item.model_copy(update={"action": action.model_copy(update={"operation": operation.value})})
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

    def obligations(self, ir: GovernedSemanticIR, turn_id: UUID) -> tuple[TurnObligation, ...]:
        identities = {i.item_id: uuid5(turn_id, f"irk-obligation:{i.item_id}") for i in ir.items}
        obligations = []
        effect_ids = {item.item_id for item in ir.items if (
            item.action and item.action.current and item.action.speech_act in {
                ActionSpeechAct.EXPLICIT_REQUEST, ActionSpeechAct.READ_ONLY_QUERY}) or (
            item.production and item.production.current) or (item.kind is SemanticKind.CORRECTION and item.supersedes) or item.kind in {
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


def project_interaction_candidate(candidate, ir):
    """WIC consumes canonical IR; all compatibility values have one source."""
    from spg.domain.conversation import ConversationTurnIntent as I
    updates = {"semantic_intent": ir, "action_candidates": legacy_action_projection(ir),
        "neutral_semantic_extractions": ir.neutral_semantic_extractions,
        "semantic_fact_candidates": ir.semantic_fact_candidates,
        "unresolved_material_questions": tuple(dict.fromkeys(
            q.question for q in ir.questions if q.blocks_current_step and not q.safe_reversible_assumption))}
    constraints = tuple(item.statement for item in ir.items if item.kind is SemanticKind.CONSTRAINT)
    updates["candidate_constraints"] = tuple(dict.fromkeys((
        *((candidate.candidate_constraints) if ir.legacy_typed_projection else ()), *constraints,
        *(value for goal in ir.current_production for value in (*goal.scope, *goal.exclusions)))))
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
            current_requests=tuple(goal.primary_change for goal in goals),
            turn_intent=candidate.turn_intent if candidate.turn_intent in {I.BUILD, I.MODIFY, I.CONTINUE_CURRENT_WORK}
                else I.ACTION_REQUEST)
    elif ir.operational_requests:
        updates["turn_intent"] = I.ACTION_REQUEST if any(
            item.action.speech_act is ActionSpeechAct.EXPLICIT_REQUEST for item in ir.operational_requests) else I.DIRECT_QUESTION
    elif any(item.kind in {SemanticKind.QUESTION, SemanticKind.ANALYSIS, SemanticKind.STATUS_QUERY} for item in ir.items):
        updates["turn_intent"] = I.DIRECT_QUESTION
    return candidate.model_copy(update=updates)
