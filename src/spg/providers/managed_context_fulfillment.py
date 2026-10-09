"""Consume Managed Product ECF context at its lawful lifecycle stage.

The ECF package and admitted Work remain immutable.  This adapter assigns
each protected item to an existing evidence owner.  It never converts a
missing current check or missing execution gate into coverage.
"""

from __future__ import annotations

from hashlib import sha256
import json
import re
import subprocess

from spg.application.governed_obligations import _mentions, _mentions_candidate


def _checked_paths(repository, source_revision, candidate_revision):
    result = subprocess.run(["git", "-C", str(repository), "diff", "--name-only",
                             source_revision, candidate_revision, "--"],
                            capture_output=True, text=True, check=False, timeout=15)
    if result.returncode:
        raise ValueError("OBLIGATION_GIT_DIFF_UNAVAILABLE")
    return tuple(result.stdout.splitlines())


def _exact_source(obligation, revision, index):
    return (obligation is not None
            and obligation.context_class == "APPROVED_CONSTRAINT"
            and obligation.semantic_key == f"greenfield-constraint:{index}"
            and obligation.source_ref ==
                f"work-reality:{revision.work_id}:greenfield-constraint:{index}"
            and obligation.content == revision.constraints[index]
            and obligation.content_digest == sha256(obligation.content.encode()).hexdigest())


def _result(obligation, request, *, coverage, method, evidence_refs=(),
            disposition=None, reason=None, owner=None):
    return {**obligation.model_dump(mode="json"),
        "coverage": coverage,
        "disposition": disposition or coverage,
        "reason": reason or method,
        "evidence_owner": owner or ("CANDIDATE" if coverage == "PENDING_CANDIDATE_GATE"
                                    else "VERIFICATION"),
        "evidence_method": method,
        "evidence_refs": list(evidence_refs),
        "candidate_revision": request.proposed_commit_identity,
        "candidate_tree": request.tree_identity}


def _check_source_ref(check, revision):
    """Reference the actual authority kind, never manufacture a Fact identity."""
    from uuid import UUID
    from spg.domain.governed_obligation import FulfillmentSourceKind

    try:
        kind = FulfillmentSourceKind(check.get("source_kind", "FACT"))
    except ValueError as error:
        raise ValueError("OBLIGATION_CHECK_SOURCE_KIND_INVALID") from error
    if kind is FulfillmentSourceKind.FACT:
        if check.get("constraint_item_id") or check.get("constraint_clause_id"):
            raise ValueError("OBLIGATION_CHECK_SOURCE_IDENTITY_MISMATCH")
        try:
            return f"semantic-fact:{UUID(str(check['fact_id']))}"
        except (ValueError, KeyError) as error:
            raise ValueError("OBLIGATION_CHECK_FACT_IDENTITY_MISSING") from error
    if (check.get("fact_id") is not None
            or check.get("work_reality_revision_id") != str(revision.id)
            or not check.get("constraint_item_id")
            or not check.get("constraint_clause_id")):
        raise ValueError("OBLIGATION_CHECK_CONSTRAINT_IDENTITY_MISMATCH")
    return f"ir-constraint:{check['constraint_item_id']}:{check['constraint_clause_id']}"


def verify_managed_context(*, request, task, contract, repository, baseline,
                           revision, ir, semantic_checks, static_verifier):
    """Return one exact result per protected item; no unmentioned deferral."""
    obligations = request.protected_context_obligations
    lineage = task.decision_context
    if (lineage is None or lineage.work_id != str(revision.work_id)
            or lineage.repository_revision != baseline
            or ir is None or not ir.current_production
            or any(item.package_fingerprint != lineage.package_fingerprint
                   for item in obligations)):
        raise ValueError("OBLIGATION_CONTEXT_SOURCE_MISMATCH")
    by_key = {(item.context_class, item.semantic_key): item for item in obligations}
    if len(by_key) != len(obligations):
        raise ValueError("OBLIGATION_CONTEXT_DUPLICATE")
    constraints = tuple(item for item in obligations
                        if item.context_class == "APPROVED_CONSTRAINT")
    if (len(constraints) != len(revision.constraints)
            or any(not _exact_source(by_key.get(
                ("APPROVED_CONSTRAINT", f"greenfield-constraint:{index}")),
                revision, index) for index in range(len(revision.constraints)))):
        raise ValueError("OBLIGATION_CONTEXT_NOT_ADMITTED_WORK")
    if any(item["passed"] is not True for item in semantic_checks):
        raise ValueError("OBLIGATION_ADMITTED_FACT_UNVERIFIED")
    check_sources = tuple(_check_source_ref(check, revision)
                          for check in semantic_checks)
    changed = _checked_paths(repository, baseline, request.proposed_commit_identity)
    targets = tuple(target.path for target in contract.exact_targets)
    if not changed or set(changed) - set(targets):
        raise ValueError("OBLIGATION_CHANGED_PATH_OUTSIDE_CONTRACT")
    gate_refs = {}
    for check, source_ref in zip(semantic_checks, check_sources):
        if check["disposition"] != "GATED_CONTINUOUS":
            continue
        for binding in check.get("fulfillment_bindings", ()):
            if check.get("source_kind") == "IR_CONSTRAINT":
                from spg.domain.governed_obligation import FulfillmentBinding
                typed = FulfillmentBinding.model_validate(binding)
                if (typed.source_kind.value != "IR_CONSTRAINT"
                        or typed.work_reality_revision_id != revision.id
                        or typed.constraint_item_id != check["constraint_item_id"]
                        or typed.constraint_clause_id != check["constraint_clause_id"]
                        or typed.source_revision != baseline):
                    raise ValueError("OBLIGATION_CHECK_BINDING_IDENTITY_MISMATCH")
            digest = check["gate_evidence"].get("native_binding_digest")
            if not digest or len(digest) != 64:
                raise ValueError("OBLIGATION_NATIVE_GATE_EVIDENCE_MISSING")
            gate_refs.setdefault(binding["component"], []).append(
                (source_ref, binding["gate_ref"], digest))
    results = {}
    content_items = []
    for index in range(len(revision.constraints)):
        item = by_key[("APPROVED_CONSTRAINT", f"greenfield-constraint:{index}")]
        content = item.content
        effects = tuple(effect for effect in ("preview", "deploy", "publish")
                        if _mentions(content, effect))
        explicit_exclusions = all(any(_mentions(exclusion, effect)
                                      for goal in ir.current_production
                                      for exclusion in goal.exclusions)
                                  for effect in effects)
        if effects and explicit_exclusions and all(effect in gate_refs for effect in effects):
            results[(item.context_class, item.semantic_key)] = _result(
                item, request, coverage="COVERED", method="EXACT_CONTINUOUS_PERMISSION_GATES",
                owner="EXECUTION_AND_DELIVERY_GATES",
                evidence_refs=tuple(f"{source_ref}:gate:{gate}:binding:{digest}"
                                    for effect in effects for source_ref, gate, digest in gate_refs[effect]))
            continue
        if effects and (content.casefold().startswith("excluded from this work:")
                        or re.search(r"\b(not authorized|do not|no deployment|no publishing)\b",
                                     content.casefold())):
            results[(item.context_class, item.semantic_key)] = _result(
                item, request, coverage="UNVERIFIED", method="CONTINUOUS_GATE_MISSING")
            continue
        if (_mentions_candidate(content)
                and "reviewable" in content.casefold()
                and not re.search(r"\b(no|not|never|without)\b[^.]{0,32}\bcandidate\b",
                                  content.casefold())
                and all(goal.acceptance_required for goal in ir.current_production)
                and not effects):
            results[(item.context_class, item.semantic_key)] = _result(
                item, request, coverage="PENDING_CANDIDATE_GATE",
                method="EXACT_CANDIDATE_SEAL_REQUIRED",
                evidence_refs=(f"task-contract:{task.task_contract_id}",))
            continue
        content_lower = content.casefold()
        if (len(targets) == 1 and targets[0] in content
                and ("change" in content_lower or "changed" in content_lower)
                and not any(word in content_lower for word in
                            ("heading", "paragraph", "h1", "ordered list", "text"))):
            passed = changed == targets
            results[(item.context_class, item.semantic_key)] = _result(
                item, request, coverage="COVERED" if passed else "UNVERIFIED",
                method="EXACT_GIT_DIFF_SCOPE",
                evidence_refs=(f"git-diff:{baseline}:{request.proposed_commit_identity}",))
            continue
        if (len(targets) == 1 and targets[0] in content
                and "one new static" in content_lower
                and not any(word in content_lower for word in
                            ("heading", "paragraph", "h1", "ordered list", "text"))):
            status = subprocess.run(["git", "-C", str(repository), "diff", "--name-status",
                baseline, request.proposed_commit_identity, "--"],
                capture_output=True, text=True, check=False, timeout=15)
            passed = status.returncode == 0 and status.stdout.splitlines() == [f"A\t{targets[0]}"]
            results[(item.context_class, item.semantic_key)] = _result(
                item, request, coverage="COVERED" if passed else "UNVERIFIED",
                method="EXACT_NEW_FILE_GIT_DIFF",
                evidence_refs=(f"git-diff:{baseline}:{request.proposed_commit_identity}",))
            continue
        if (content_lower.startswith("verification ")
                and all(check["passed"] is True for check in semantic_checks)):
            results[(item.context_class, item.semantic_key)] = _result(
                item, request, coverage="COVERED",
                method="ALL_ADMITTED_FACT_CHECKS_AND_EXACT_DIFF",
                evidence_refs=check_sources)
            continue
        content_items.append(item)
    if content_items:
        if static_verifier is None or not static_verifier.supports(contract):
            raise ValueError("OBLIGATION_CONTENT_CONSUMER_UNAVAILABLE")
        observed = static_verifier.verify(request, task, contract, repository,
                                          baseline, obligations=tuple(content_items))
        for item in observed:
            key = (item["context_class"], item["semantic_key"])
            if key in results:
                raise ValueError("OBLIGATION_CONTENT_DUPLICATE")
            results[key] = {**item, "evidence_owner": "VERIFICATION",
                            "evidence_method": "EXACT_CANDIDATE_SOURCE_WITNESS",
                            "evidence_refs": list(check_sources)}
    intents = tuple(item for item in obligations if item.context_class == "PRODUCT_INTENT")
    if len(intents) != 1:
        raise ValueError("OBLIGATION_PRODUCT_INTENT_IDENTITY_MISSING")
    intent = intents[0]
    try:
        observed_intent = json.loads(intent.content)
    except (TypeError, ValueError) as error:
        raise ValueError("OBLIGATION_PRODUCT_INTENT_NOT_STRUCTURED") from error
    expected_intent = {
        "desired_outcome": revision.desired_outcome,
        "governed_production_intents": [goal.model_dump(mode="json")
                                        for goal in ir.current_production],
    }
    all_children = len(results) == len(constraints) and all(
        result["coverage"] in {"COVERED", "PENDING_CANDIDATE_GATE"}
        for result in results.values())
    results[(intent.context_class, intent.semantic_key)] = _result(
        intent, request,
        owner="PRODUCT_SOURCE",
        coverage="COVERED" if observed_intent == expected_intent and all_children
                 and intent.content_digest == sha256(intent.content.encode()).hexdigest()
                 else "UNVERIFIED",
        method="EXACT_ADMITTED_INTENT_AND_CHILD_OBLIGATIONS",
        evidence_refs=tuple(f"ecf:{key[0]}:{key[1]}" for key in results))
    return tuple(results.get((item.context_class, item.semantic_key)) or
                 _result(item, request, coverage="UNVERIFIED",
                         method="NO_LAWFUL_FULFILLMENT_BINDING")
                 for item in obligations)
