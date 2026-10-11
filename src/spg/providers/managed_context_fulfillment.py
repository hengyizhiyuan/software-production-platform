"""Consume Managed Product ECF context at its lawful lifecycle stage.

The ECF package and admitted Work remain immutable.  This adapter assigns
each protected item to an existing evidence owner.  It never converts a
missing current check or missing execution gate into coverage.
"""

from __future__ import annotations

from hashlib import sha256
import json
import subprocess



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
    if kind in {FulfillmentSourceKind.WORK_CONSTRAINT, FulfillmentSourceKind.WORK_CONTEXT}:
        try:
            index = int(check["constraint_item_id"])
            work_revision = UUID(str(check["work_reality_revision_id"]))
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError("OBLIGATION_CHECK_WORK_SOURCE_MISSING") from error
        if index < 0 or work_revision != revision.id or check.get("fact_id") is not None or check.get("constraint_clause_id") is not None:
            raise ValueError("OBLIGATION_CHECK_WORK_SOURCE_MISMATCH")
        prefix = "work-constraint" if kind is FulfillmentSourceKind.WORK_CONSTRAINT else "work-context"
        return f"{prefix}:{work_revision}:{index}"
    if (check.get("fact_id") is not None
            or check.get("work_reality_revision_id") != str(revision.id)
            or not check.get("constraint_item_id")
            or not check.get("constraint_clause_id")):
        raise ValueError("OBLIGATION_CHECK_CONSTRAINT_IDENTITY_MISMATCH")
    if kind is FulfillmentSourceKind.IR_CLAUSE:
        if not check.get("semantic_ir_id"):
            raise ValueError("OBLIGATION_CHECK_IR_IDENTITY_MISSING")
        return f"ir-clause:{UUID(str(check['semantic_ir_id']))}:{check['constraint_item_id']}:{check['constraint_clause_id']}"
    return f"ir-constraint:{check['constraint_item_id']}:{check['constraint_clause_id']}"


def _linked_fact_current_evidence(binding, semantic_checks):
    """Use only the reviewed component's explicit exact current Fact proofs."""
    basis = getattr(binding, "component_basis", None)
    refs = () if basis is None else tuple(basis.linked_fact_refs)
    if not refs:
        return None
    facts = []
    for ref in refs:
        rows = [row for row in semantic_checks if "semantic-fact:" + str(row.get("fact_id")) == ref]
        if len(rows) != 1:
            return {"passed": False, "facts": []}
        row = rows[0]
        routes = [route for route in row.get("fulfillment_bindings", ())
                  if route.get("source_kind", "FACT") == "FACT"
                  and "semantic-fact:" + str(route.get("fact_id")) == ref
                  and route.get("phase") == "CURRENT_VERIFICATION"
                  and route.get("evidence_method") == "EXACT_CANDIDATE_CONTENT"
                  and route.get("work_reality_revision_id") == str(binding.work_reality_revision_id)
                  and route.get("source_revision") == binding.source_revision]
        if (row.get("passed") is not True or row.get("current_evidence_verified") is not True
                or len(routes) != 1 or row.get("scope") not in binding.target_paths
                or row.get("scope") not in routes[0].get("target_paths", ())):
            return {"passed": False, "facts": []}
        facts.append({"source_ref": ref, "fact_id": row["fact_id"],
            "fact_fingerprint": routes[0].get("fact_fingerprint"),
            "work_reality_revision_id": str(binding.work_reality_revision_id),
            "source_revision": binding.source_revision, "target_path": row["scope"],
            "passed": True, "current_evidence_verified": True})
    return {"passed": True, "facts": facts}


def verify_managed_context(*, request, task, contract, repository, baseline,
                           revision, ir, semantic_checks, static_verifier,
                           fulfillment_bindings=(), receipt_recorder=None, native_record=None):
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
            if check.get("source_kind") in {"IR_CONSTRAINT", "IR_CLAUSE", "WORK_CONSTRAINT"}:
                from spg.domain.governed_obligation import FulfillmentBinding
                typed = FulfillmentBinding.model_validate(binding)
                if (typed.source_kind.value != check.get("source_kind")
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
    from spg.domain.governed_obligation import fulfillment_source_ref
    bindings = tuple(fulfillment_bindings)
    by_constraint = {index: [] for index in range(len(revision.constraints))}
    for binding in bindings:
        indices = binding.work_constraint_indices
        # Compatibility for the existing typed IR_CONSTRAINT path: this is
        # exact original statement identity, never keyword interpretation.
        if not indices and binding.source_kind.value == "IR_CONSTRAINT" and not binding.projection_inventory_fingerprint:
            source_item = next((source for source in ir.items
                                if source.item_id == binding.constraint_item_id), None)
            if source_item is not None:
                indices = tuple(index for index, text in enumerate(revision.constraints)
                                if text == source_item.statement)
        for index in indices:
            if index not in by_constraint:
                raise ValueError("OBLIGATION_CONTEXT_INDEX_INVALID")
            by_constraint[index].append(binding)
    results = {}
    content_items = []
    content_routes = {}
    for index in range(len(revision.constraints)):
        item = by_key[("APPROVED_CONSTRAINT", f"greenfield-constraint:{index}")]
        routes = tuple(by_constraint[index])
        if not routes:
            results[(item.context_class, item.semantic_key)] = _result(
                item, request, coverage="UNVERIFIED", method="NO_LAWFUL_FULFILLMENT_BINDING")
            continue
        observations = []
        for route in routes:
            ref = fulfillment_source_ref(route)
            method = route.evidence_method
            if route.state == "UNRESOLVED" or method == "UNRESOLVED":
                observations.append(("UNVERIFIED", "UNRESOLVED_OWNER_BINDING", (), route))
            elif method == "EXACT_CANDIDATE_CONTENT" and route.phase.value == "CURRENT_VERIFICATION":
                # Content is independently checked against this exact protected
                # item below, not accepted because another Fact happened to pass.
                linked = _linked_fact_current_evidence(route, semantic_checks)
                observations.append(("CONTENT_CHECK_REQUIRED", "EXACT_CANDIDATE_SOURCE_WITNESS", (ref,), route)
                    if linked is None else ("COVERED" if linked["passed"] else "UNVERIFIED",
                        "EXACT_LINKED_FACT_CURRENT_EVIDENCE", tuple(route.component_basis.linked_fact_refs), route))
            elif method == "EXACT_GIT_DIFF_SCOPE" and route.phase.value == "CURRENT_VERIFICATION":
                passed = tuple(route.target_paths) == targets and changed == targets
                observations.append(("COVERED" if passed else "UNVERIFIED", "EXACT_GIT_DIFF_SCOPE",
                    (f"git-diff:{baseline}:{request.proposed_commit_identity}", ref), route))
            elif method == "EXACT_PERMISSION_GATE" and route.phase.value == "CONTINUOUS_FROM_ADMISSION":
                matches = [(source, gate, digest) for source, gate, digest in gate_refs.get(route.component, ())
                           if source == ref and gate == route.gate_ref]
                observations.append(("COVERED" if len(matches) == 1 else "UNVERIFIED",
                    "EXACT_CONTINUOUS_PERMISSION_GATES",
                    tuple(f"{source}:gate:{gate}:binding:{digest}" for source, gate, digest in matches), route))
            elif (method == "EXACT_SEALED_CANDIDATE" and route.phase.value == "CANDIDATE_SEAL"
                  and route.owner.value == "CANDIDATE"
                  and route.gate_ref == "candidate-owner:sealed-after-verification"
                  and _candidate_seal_gate_required(route, revision, ir, bindings)):
                observations.append(("PENDING_CANDIDATE_GATE", "EXACT_CANDIDATE_SEAL_REQUIRED", (ref,), route))
            elif method == "EXACT_HUMAN_AUTHORIZATION":
                # A future authorization cannot be proved by an HTML witness.
                # Its exact route and actual Native gate proof are evaluated by
                # the same helper used for the Fact disposition below.
                proof = _future_gate_proof(route, ir, native_record)
                observations.append(("PENDING_HUMAN_GATE" if proof else "UNVERIFIED",
                    "EXACT_HUMAN_AUTHORIZATION_REQUIRED", (ref,), route))
            elif (method == "RETAIN_AUTHORITATIVE_CONTEXT" and route.phase.value == "CONTEXT_RETENTION"
                  and _retained_binding_proof(route, revision, ir, bindings)):
                observations.append(("CONTEXT_RETAINED", "EXACT_RETAINED_AUTHORITATIVE_CONTEXT", (ref,), route))
            else:
                # An unsupported current requirement can never become retained context.
                observations.append(("UNVERIFIED", "NO_LAWFUL_CURRENT_EVIDENCE_OWNER", (ref,), route))
        statuses = {value[0] for value in observations}
        if "UNVERIFIED" in statuses:
            result = _result(item, request, coverage="UNVERIFIED", method="OBLIGATION_ROUTE_EVIDENCE_MISSING",
                evidence_refs=tuple(ref for value in observations for ref in value[2]))
        elif "CONTENT_CHECK_REQUIRED" in statuses:
            content_items.append(item)
            content_routes[(item.context_class, item.semantic_key)] = observations
            # Non-content routes are retained and must also have valid evidence.
            result = None
        else:
            # Multiple current/future routes keep their distinct evidence. A
            # current proof never claims the future Human decision occurred.
            coverage = ("PENDING_HUMAN_GATE" if "PENDING_HUMAN_GATE" in statuses else
                        "PENDING_CANDIDATE_GATE" if "PENDING_CANDIDATE_GATE" in statuses else
                        "COVERED" if "COVERED" in statuses else "CONTEXT_RETAINED")
            chosen = next(value for value in observations if value[0] == coverage)
            result = _result(item, request, coverage=coverage, method=chosen[1],
                owner=chosen[3].owner.value,
                evidence_refs=tuple(ref for value in observations for ref in value[2]))
        if result is not None:
            result["fulfillment_bindings"] = [route.model_dump(mode="json") for route in routes]
            result["current_component_evidence"] = [
                {"source_ref": fulfillment_source_ref(entry[3]), "binding": entry[3].model_dump(mode="json"),
                 "evidence_method": entry[1], "passed": entry[0] == "COVERED",
                 "candidate_revision": request.proposed_commit_identity, "candidate_tree": request.tree_identity,
                 "source_revision": baseline, "changed_paths": list(changed), "target_paths": list(targets),
                 "linked_fact_evidence": (_linked_fact_current_evidence(entry[3], semantic_checks) or {}).get("facts", [])}
                for entry in observations if entry[3].phase.value == "CURRENT_VERIFICATION"]
            if result["coverage"] == "PENDING_HUMAN_GATE":
                result["future_gate_evidence"] = _future_gate_evidence(routes, native_record)
            results[(item.context_class, item.semantic_key)] = result
    if content_items:
        if static_verifier is None or not static_verifier.supports(contract):
            raise ValueError("OBLIGATION_CONTENT_CONSUMER_UNAVAILABLE")
        observed = static_verifier.verify(request, task, contract, repository,
            baseline, obligations=tuple(content_items), receipt_recorder=receipt_recorder,
            fulfillment_bindings=tuple(route for routes in by_constraint.values() for route in routes))
        for value in observed:
            key = (value["context_class"], value["semantic_key"])
            if key in results:
                raise ValueError("OBLIGATION_CONTENT_DUPLICATE")
            index = next(i for i in by_constraint if key[1] == f"greenfield-constraint:{i}")
            routes = by_constraint[index]
            result = {**value, "evidence_owner": "VERIFICATION",
                "evidence_method": "EXACT_CANDIDATE_SOURCE_WITNESS",
                "evidence_refs": [fulfillment_source_ref(route) for route in routes],
                "fulfillment_bindings": [route.model_dump(mode="json") for route in routes]}
            result["current_component_evidence"] = [
                {"source_ref": fulfillment_source_ref(entry[3]), "binding": entry[3].model_dump(mode="json"),
                 "evidence_method": ("EXACT_CANDIDATE_SOURCE_WITNESS" if entry[0] == "CONTENT_CHECK_REQUIRED" else entry[1]),
                 "passed": value["coverage"] == "COVERED" if entry[0] == "CONTENT_CHECK_REQUIRED" else entry[0] == "COVERED",
                 "candidate_revision": request.proposed_commit_identity, "candidate_tree": request.tree_identity,
                 "source_revision": baseline, "changed_paths": list(changed), "target_paths": list(targets),
                 "witnesses": value.get("witnesses", []), "observed_source_digests": value.get("observed_source_digests", {}),
                 "source_component_evidence": value.get("source_component_evidence", [])}
                for entry in content_routes[key] if entry[3].phase.value == "CURRENT_VERIFICATION"]
            future = [entry for entry in content_routes[key]
                      if entry[0] in {"PENDING_HUMAN_GATE", "PENDING_CANDIDATE_GATE"}]
            if future and value["coverage"] == "COVERED":
                selected = next((entry for entry in future if entry[0] == "PENDING_HUMAN_GATE"), future[0])
                result.update(coverage=selected[0], evidence_method=selected[1],
                    evidence_owner=selected[3].owner.value,
                    current_content_evidence_method="EXACT_CANDIDATE_SOURCE_WITNESS")
                if selected[0] == "PENDING_HUMAN_GATE":
                    result["future_gate_evidence"] = _future_gate_evidence(routes, native_record)
            results[key] = result
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
        result["coverage"] in {"COVERED", "PENDING_CANDIDATE_GATE", "PENDING_HUMAN_GATE", "CONTEXT_RETAINED"}
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


_HUMAN_GATES = {
    "candidate-governance:human-integration": ("HUMAN_GATE", "HUMAN_INTEGRATION"),
    "cloud-delivery:human-authorization-required": ("DELIVERY_GATE", "DELIVERY"),
    "remote-delivery:human-authorization-required": ("DELIVERY_GATE", "DELIVERY"),
}


def _future_gate_proof(binding, ir, native_record):
    if (native_record is None or ir is None or not ir.current_production
            or _HUMAN_GATES.get(binding.gate_ref) != (binding.owner.value, binding.phase.value)
            or not all(goal.acceptance_required for goal in ir.current_production)
            or any(goal.delivery_authorized for goal in ir.current_production)):
        return False
    from spg.domain.governed_obligation import fulfillment_source_ref
    native = native_record.binding
    grants = tuple(getattr(native, "capability_grants", ()))
    if (not grants or binding.work_reality_revision_id != native.production_context.work_reality_revision_id
            or binding.source_revision not in tuple(member.source_commit_oid for member in native.source_vector.members)
            or fulfillment_source_ref(binding)
               not in native.obligation_references):
        return False
    # Native cannot create Human authority or execute an external release.
    forbidden = {"cloud.deploy", "cloud.delivery", "remote.publish", "remote.delivery", "github.publish",
                 "human.authorize", "repository.integrate", "candidate.accept"}
    return not ({grant.identity for grant in grants} & forbidden)


def _future_gate_evidence(bindings, native_record):
    return {"native_attempt_id": str(native_record.attempt_id),
        "native_binding_digest": native_record.binding_digest,
        "authorization_state": "PENDING", "delivery_authorization_state": "NOT_AUTHORIZED",
        "gate_refs": [binding.gate_ref for binding in bindings
                      if binding.evidence_method == "EXACT_HUMAN_AUTHORIZATION"]}


def _retained_context_route(binding, revision, ir, bindings=()):
    from spg.application.governed_obligations import calibrated_background_binding_permitted
    if calibrated_background_binding_permitted(binding, revision, ir, bindings):
        return True
    from spg.application.governed_obligations import is_context_only_clause
    if binding.source_kind.value == "WORK_CONTEXT":
        return not binding.work_constraint_indices
    if binding.source_kind.value == "IR_ITEM":
        item = next((item for item in ir.items if item.item_id == binding.constraint_item_id), None)
        return bool(item is not None and item.kind.value == "FACT" and not item.action and not item.production
            and not item.requires_human and item.provenance
            and all(p.origin.value == "REPOSITORY_OBSERVED" for p in item.provenance))
    if binding.source_kind.value == "WORK_CONSTRAINT":
        # Full supporting source proof is supplied by _retained_binding_proof.
        return False
    if binding.source_kind.value == "IR_CLAUSE":
        return is_context_only_clause(revision, ir, binding.constraint_item_id, binding.constraint_clause_id, bindings=bindings)
    if binding.source_kind.value != "FACT" or binding.work_constraint_indices:
        return False
    fact = next((fact for fact in revision.engineering_semantic_facts if fact.id == binding.fact_id), None)
    if fact is None:
        return False
    observed = fact.provenance.governed_provenance
    return bool((fact.relation.value == "REFERENCE" and fact.reference_role is not None
                 and fact.reference_role.value == "EXTERNAL_REFERENCE") or
                observed and all(p.origin.value == "REPOSITORY_OBSERVED" for p in observed))


def linked_component_dependencies(facts, bindings):
    """Describe the existing linked acceptance consumer, not semantic approval.

    Equality checks consume Candidate source directly even if a proposal carries
    a redundant self reference. Only the mixed acceptance consumer below needs
    completed linked Fact checks. Share that exact classification with admission.
    """
    result = {}
    for fact in facts:
        identity = str(getattr(fact, "fact_id", None) or fact.id)
        routes = tuple(b for b in bindings if str(b.fact_id) == identity)
        content = tuple(b for b in routes if b.evidence_method == "EXACT_CANDIDATE_CONTENT")
        if (fact.relation.value == "ACCEPTANCE_ASSERTION"
                and any(b.phase.value == "CANDIDATE_SEAL" for b in routes)
                and content and all(b.component_basis is not None
                                    and b.component_basis.linked_fact_refs for b in content)):
            result[identity] = tuple(dict.fromkeys(link.removeprefix("semantic-fact:")
                for b in content for link in b.component_basis.linked_fact_refs))
    return result


def linked_component_dependency_failures(facts, bindings):
    """Necessary proof availability; never predict actual Verification PASS."""
    dependencies = linked_component_dependencies(facts, bindings)
    by_id = {str(getattr(f, "fact_id", None) or f.id): f for f in facts}
    pending = set(dependencies)
    available = set(by_id) - pending
    failed = {}
    for identity, links in dependencies.items():
        consumers = [b for b in bindings if str(b.fact_id) == identity
            and b.phase.value == "CURRENT_VERIFICATION"
            and b.evidence_method == "EXACT_CANDIDATE_CONTENT"]
        for consumer in consumers:
            for ref in consumer.component_basis.linked_fact_refs:
                link = ref.removeprefix("semantic-fact:")
                proofs = [b for b in bindings if str(b.fact_id) == link
                    and b.phase.value == "CURRENT_VERIFICATION"
                    and b.evidence_method == "EXACT_CANDIDATE_CONTENT"]
                if (link not in by_id or len(proofs) != 1
                        or proofs[0].work_reality_revision_id != consumer.work_reality_revision_id
                        or proofs[0].source_revision != consumer.source_revision
                        or not set(consumer.target_paths) & set(proofs[0].target_paths)):
                    failed[identity] = "OBLIGATION_LINKED_FACT_CURRENT_PROOF_UNAVAILABLE"
    while pending:
        ready = {identity for identity in pending if identity not in failed
                 and set(dependencies[identity]) <= available}
        if not ready:
            for identity in dependencies:
                if identity in pending:
                    failed.setdefault(identity, "OBLIGATION_LINKED_FACT_DEPENDENCY_UNFULFILLABLE")
            break
        available.update(ready)
        pending -= ready
    return {identity: failed[identity] for identity in dependencies if identity in failed}


def verify_fulfillment_fact_routes(*, repository, request, contract, references,
        admitted_facts, revision, ir, baseline, bindings, plan_repair):
    """Consume typed projected Fact roles while preserving all current checks.

    Legacy requests retain their existing checker. A disposition is not evidence
    that a future Human decision or unrelated reference has already been fulfilled.
    """
    from spg.providers.static_html_semantic_verifier import verify_static_html_semantic_facts
    projected = any(binding.projection_inventory_fingerprint for binding in bindings)
    if not projected:
        return verify_static_html_semantic_facts(repository, request.proposed_commit_identity,
            contract, references, admitted_facts=admitted_facts, plan_repair=plan_repair)
    routes_by_fact = {str(reference.fact_id): tuple(binding for binding in bindings
        if str(binding.fact_id) == str(reference.fact_id)) for reference in references}
    dependencies = linked_component_dependencies(references, bindings)
    linked_components = set(dependencies)
    content = tuple(reference for reference in references if str(reference.fact_id) not in linked_components and any(
        binding.evidence_method == "EXACT_CANDIDATE_CONTENT" and binding.phase.value == "CURRENT_VERIFICATION"
        for binding in routes_by_fact[str(reference.fact_id)]))
    checked = verify_static_html_semantic_facts(repository, request.proposed_commit_identity,
        contract, content, admitted_facts=admitted_facts, plan_repair=plan_repair)
    by_id = {check["fact_id"]: check for check in checked}
    changed = _checked_paths(repository, contract.source_revision, request.proposed_commit_identity)
    targets = tuple(target.path for target in contract.exact_targets)
    result = []
    # Linked components consume completed, identity-bound Fact checks, not raw
    # checker observations. Resolve this bounded local evidence dependency first;
    # cycles/missing proofs still fail, and cannot create evidence by ordering.
    ordered = [ref for ref in references if str(ref.fact_id) not in linked_components]
    available = {str(ref.fact_id) for ref in ordered}
    pending = [ref for ref in references if str(ref.fact_id) in linked_components]
    while pending:
        ready = [ref for ref in pending if all(link.removeprefix("semantic-fact:") in available
            for b in routes_by_fact[str(ref.fact_id)] if b.evidence_method == "EXACT_CANDIDATE_CONTENT"
            for link in b.component_basis.linked_fact_refs)]
        if not ready:
            ordered.extend(pending)
            break
        ordered.extend(ready)
        available.update(str(ref.fact_id) for ref in ready)
        pending = [ref for ref in pending if ref not in ready]
    for reference in ordered:
        identity = str(reference.fact_id)
        routes = routes_by_fact[identity]
        current = tuple(binding for binding in routes if binding.phase.value == "CURRENT_VERIFICATION")
        check = by_id.get(identity)
        evaluations = []
        component_evidence = []
        if check is not None:
            evaluations.append(check["passed"] is True)
        for binding in current:
            if binding.evidence_method == "EXACT_GIT_DIFF_SCOPE":
                evaluations.append(_exact_fact_git_scope(reference, binding, targets, changed,
                    revision=revision, ir=ir, bindings=bindings))
            elif binding.evidence_method == "EXACT_PRODUCT_SOURCE_IDENTITY":
                # These are existing immutable Source Owner identities. A natural
                # language label that has no authoritative link stays unresolved.
                identities = {baseline.repository_identity, baseline.repository_ref,
                              baseline.repository_revision, str(baseline.id)}
                evaluations.append(reference.relation.value == "REFERENCE"
                    and reference.reference_role is not None
                    and reference.reference_role.value == "PROJECT_REPOSITORY"
                    and any(reference.value == identity for identity in identities)
                    and revision.source_baseline_id == baseline.id
                    and revision.source_revision == baseline.repository_revision
                    and revision.repository_identity == baseline.repository_identity
                    and revision.repository_ref == baseline.repository_ref)
            elif binding.evidence_method == "EXACT_CANDIDATE_CONTENT" and identity in linked_components:
                proof = _linked_fact_current_evidence(binding, result)
                evaluations.append(proof is not None and proof["passed"])
                if proof is not None:
                    component_evidence.append({"binding": binding.model_dump(mode="json"),
                        "evidence_method": "EXACT_LINKED_FACT_CURRENT_EVIDENCE", "passed": proof["passed"],
                        "linked_fact_evidence": proof["facts"], "candidate_revision": request.proposed_commit_identity,
                        "candidate_tree": request.tree_identity})
            elif binding.evidence_method != "EXACT_CANDIDATE_CONTENT":
                evaluations.append(False)
        retained = bool(routes and not current and all(_retained_context_route(binding, revision, ir, bindings)
            and binding.phase.value == "CONTEXT_RETENTION" for binding in routes))
        # Continuous gate routes are independently evaluated by the existing
        # Native helper; no future-only Fact can bypass a current contribution.
        only_continuous = bool(routes and not current and all(
            binding.phase.value == "CONTINUOUS_FROM_ADMISSION" for binding in routes))
        passed = bool(evaluations and all(evaluations)) or retained
        disposition = ("CONTEXT_RETAINED" if retained else "VERIFIED_CURRENT" if passed else "UNVERIFIABLE_CURRENT")
        if check is not None and not passed:
            disposition = check["disposition"]
        row = {**(check or {"fact_id": identity, "subject": reference.subject, "scope": reference.scope}),
            "passed": passed, "disposition": disposition,
            "reason": (check["reason"] if check is not None else "EXACT_TYPED_FULFILLMENT_EVIDENCE"
                       if passed else "UNVERIFIABLE_FACT_OWNER_EVIDENCE"),
            "fulfillment_bindings": [binding.model_dump(mode="json") for binding in routes],
            "current_evidence_verified": bool(evaluations and all(evaluations)),
            "future_evidence_status": "PENDING_FUTURE_OWNER_GATE" if any(
                binding.phase.value in {"CANDIDATE_SEAL", "HUMAN_INTEGRATION", "DELIVERY"} for binding in routes) else None}
        if component_evidence:
            row["current_component_evidence"] = component_evidence
        if only_continuous:
            row["disposition"] = "UNVERIFIABLE_CURRENT"
        result.append(row)
    indexed = {row["fact_id"]: row for row in result}
    return tuple(indexed[str(ref.fact_id)] for ref in references)


def _retained_binding_proof(binding, revision, ir, bindings):
    from spg.application.governed_obligations import calibrated_background_binding_permitted
    if calibrated_background_binding_permitted(binding, revision, ir, bindings):
        return True
    if binding.source_kind.value != "WORK_CONSTRAINT":
        return _retained_context_route(binding, revision, ir, bindings)
    from spg.application.governed_obligations import is_context_only_clause
    from spg.domain.governed_obligation import fulfillment_source_ref
    supports = tuple(source for source in bindings if fulfillment_source_ref(source) in binding.supporting_source_refs)
    return bool(supports) and all(source.source_kind.value == "IR_CLAUSE" and is_context_only_clause(
        revision, ir, source.constraint_item_id, source.constraint_clause_id, bindings=bindings) for source in supports)


def verify_binding_inventory(*, request, task, contract, repository, baseline, revision, ir,
        bindings, semantic_checks, protected_checks, static_verifier, receipt_recorder, native_record):
    """Give every canonical binding a visible same-basis current-stage outcome."""
    from spg.domain.governed_obligation import fulfillment_source_ref
    from spg.application.governed_obligations import canonical_fingerprint
    known = []
    for check in protected_checks:
        for evidence in check.get("current_component_evidence", ()):
            known.append(evidence)
    pending_content = []
    linked_checks = []
    results = []
    for binding in bindings:
        ref = fulfillment_source_ref(binding)
        evidence_refs = [ref]
        status = "UNVERIFIABLE"
        method = binding.evidence_method
        if method == "EXACT_CANDIDATE_CONTENT" and binding.phase.value == "CURRENT_VERIFICATION":
            if binding.source_kind.value == "FACT":
                matches = [check for check in semantic_checks if check.get("fact_id") == str(binding.fact_id)]
                status = "VERIFIED_CURRENT" if len(matches) == 1 and matches[0].get("current_evidence_verified") is True else "UNVERIFIABLE"
            else:
                matches = [evidence for evidence in known if evidence.get("binding") == binding.model_dump(mode="json")]
                if len(matches) == 1:
                    status = "VERIFIED_CURRENT" if matches[0].get("passed") is True else "UNVERIFIABLE"
                else:
                    proof = _linked_fact_current_evidence(binding, semantic_checks)
                    if proof is None:
                        pending_content.append(binding)
                        status = "CONTENT_CHECK_REQUIRED"
                    else:
                        status = "VERIFIED_CURRENT" if proof["passed"] else "UNVERIFIABLE"
                        linked_checks.append({"context_class": "DERIVED_VERIFICATION_OBLIGATION", "source_ref": ref,
                            "coverage": "COVERED" if proof["passed"] else "UNVERIFIED",
                            "evidence_method": "EXACT_LINKED_FACT_CURRENT_EVIDENCE", "binding": binding.model_dump(mode="json"),
                            "linked_fact_evidence": proof["facts"],
                            "candidate_revision": request.proposed_commit_identity, "candidate_tree": request.tree_identity})
        elif method in {"EXACT_GIT_DIFF_SCOPE", "EXACT_PERMISSION_GATE"}:
            matches = [check for check in semantic_checks if binding.model_dump(mode="json") in check.get("fulfillment_bindings", ())
                and check.get("passed") is True]
            status = ("GATED_CONTINUOUS" if method == "EXACT_PERMISSION_GATE" else "VERIFIED_CURRENT") if len(matches) == 1 else "UNVERIFIABLE"
        elif method == "EXACT_PRODUCT_SOURCE_IDENTITY":
            matches = [check for check in semantic_checks if binding.source_kind.value == "FACT"
                and binding.fact_id is not None and check.get("fact_id") == str(binding.fact_id)
                and check.get("current_evidence_verified") is True]
            status = "VERIFIED_CURRENT" if len(matches) == 1 else "UNVERIFIABLE"
        elif method == "EXACT_SEALED_CANDIDATE":
            if (binding.gate_ref == "candidate-owner:sealed-after-verification" and ir.current_production
                    and _candidate_seal_gate_required(binding, revision, ir, bindings)
                    and native_record is not None and ref in native_record.binding.obligation_references):
                status = "PENDING_CANDIDATE_GATE"
        elif method == "EXACT_HUMAN_AUTHORIZATION":
            if _future_gate_proof(binding, ir, native_record): status = "PENDING_HUMAN_GATE"
        elif method == "RETAIN_AUTHORITATIVE_CONTEXT" and _retained_binding_proof(binding, revision, ir, bindings):
            status = "CONTEXT_RETAINED"
        results.append({"source_ref":ref,"source_kind":binding.source_kind.value,
            "binding_fingerprint":canonical_fingerprint(binding.model_dump(mode="json")),
            "owner":binding.owner.value,"phase":binding.phase.value,"evidence_method":method,
            "disposition":status,"current_stage_satisfied":status not in {"UNVERIFIABLE","CONTENT_CHECK_REQUIRED"},
            "candidate_revision":request.proposed_commit_identity,"candidate_tree":request.tree_identity,
            "evidence_refs":evidence_refs,"original_fact_unchanged":True})
    derived = tuple(linked_checks)
    if pending_content:
        if static_verifier is None or not static_verifier.supports(contract):
            raise ValueError("OBLIGATION_CURRENT_CONTENT_CONSUMER_UNAVAILABLE")
        derived = (*derived, *static_verifier.verify_fulfillment_bindings(request, task, contract, repository,
            baseline, bindings=tuple(pending_content), receipt_recorder=receipt_recorder))
        for result in results:
            if result["disposition"] != "CONTENT_CHECK_REQUIRED": continue
            matches = [check for check in derived if check["source_ref"] == result["source_ref"]
                and check.get("binding") is not None and canonical_fingerprint(check["binding"]) == result["binding_fingerprint"]]
            result["disposition"] = "VERIFIED_CURRENT" if len(matches) == 1 and matches[0]["coverage"] == "COVERED" else "UNVERIFIABLE"
            result["current_stage_satisfied"] = result["disposition"] == "VERIFIED_CURRENT"
    return tuple(results), tuple(derived)


def _candidate_seal_gate_required(binding, revision, ir, bindings):
    """Seal is a Candidate Owner obligation, not Human acceptance authority.

    Preserve historical contracts. A current calibrated Seal must revalidate
    the entire exact projection and independent Review; a role marker alone
    cannot establish a later gate or create an authorization.
    """
    if not ir.current_production:
        return False
    if all(goal.acceptance_required for goal in ir.current_production):
        return True
    if not bindings or (bindings[0].formation_receipt or {}).get("source_role_contract") != "v3":
        return False
    from spg.application.governed_obligations import validate_fulfillment_projection
    try:
        validate_fulfillment_projection(bindings, revision, ir,
            source_revision=binding.source_revision, exact_target_paths=bindings[0].formation_receipt.get("exact_target_paths", ()))
    except (ValueError, TypeError, IndexError):
        return False
    return binding in bindings and binding.owner.value == "CANDIDATE" and binding.phase.value == "CANDIDATE_SEAL"


def _exact_fact_git_scope(reference, binding, targets, changed, *, revision=None, ir=None, bindings=()):
    """Consume the original SCOPE value; a broad contract never broadens a Fact.

    This capability handles explicit unqualified repository paths. Arbitrary
    New calibrated qualifier interpretations require the exact independently
    reviewed projection; literal value observation alone is never a PASS.
    """
    from spg.domain.governed_obligation import exact_file_scope_paths
    paths = exact_file_scope_paths(reference, qualified=binding.component_basis is not None)
    calibrated = any((b.formation_receipt or {}).get("source_role_contract") == "v3" for b in bindings)
    source_consumption = any((row.get("owner_source_preconditions") or {}).get(
        "review_source_consumption_contract") == "existing-source-consumption-proof-v1"
        for row in ((bindings[0].formation_receipt or {}) if bindings else {}).get("candidate_attempts", ())
        if row.get("stage") == "MODEL_REQUEST_PENDING")
    if source_consumption:
        if revision is None or ir is None or binding not in bindings:
            return False
        from spg.domain.engineering_semantics import semantic_fact_reference
        original = next((fact for fact in revision.engineering_semantic_facts if fact.id == binding.fact_id), None)
        if original is None or (reference != original and
                reference != semantic_fact_reference(original, work_revision_id=revision.id)):
            return False
    if (paths is None or source_consumption) and (reference.qualifiers == {"negated": True} or calibrated) and binding.component_basis is not None:
        if revision is None or ir is None:
            return False
        from spg.application.governed_obligations import validate_fulfillment_projection
        try:
            validate_fulfillment_projection(bindings, revision, ir,
                source_revision=binding.source_revision, exact_target_paths=targets)
        except (ValueError, TypeError):
            return False
        # The negative value remains the original exclusion. The authorized
        # target set is supplied by the Task, not reinterpreted from that value.
        # Full projection validation has re-proved source/qualifier meaning,
        # exact literal-value equality or exact negative-clause correspondence,
        # independent Review and the original Task allowlist.
        paths = binding.target_paths
    if paths is None:
        return False
    return bool(changed and set(binding.target_paths) == set(paths) and set(targets) == set(paths)
                and not set(changed) - set(paths))
