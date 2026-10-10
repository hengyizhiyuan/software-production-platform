"""Open, read-only fulfillment candidates beneath existing Work governance.

The model chooses a consumer capability from admitted meaning. It cannot return
satisfaction, modify facts, supply evidence or authorize an effect.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from spg.domain.governed_obligation import (FulfillmentProjectionCandidate, FulfillmentSemanticReviewCandidate,
    fulfillment_candidate_fingerprint, fulfillment_components_fingerprint,
    canonical_fingerprint, fulfillment_source_semantic_text, fulfillment_component_id)
from spg.domain.model_runtime import ModelPurpose


def provider_failure_observation(error):
    """Project only normalized typed failure metadata, never exception prose.

    Only typed observed numeric usage and actual replay count are preserved.
    Legacy errors remain UNKNOWN; eligibility never implies actual retries.
    """
    from spg.infrastructure.model_runtime import ModelFailureKind, ModelProviderError
    from spg.domain.model_runtime import ModelUsage
    from spg.providers.verification_receipts import _safe_value
    if not isinstance(error, ModelProviderError):
        return None

    def machine_field(value, limit):
        if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_.:-]{1," + str(limit) + "}", value) is None:
            return None
        return value if _safe_value(value) == value else None

    occurred_at = error.occurred_at
    failure = {
        "kind": error.kind.value if isinstance(error.kind, ModelFailureKind) else None,
        "request_sent": error.request_sent if type(error.request_sent) is bool else None,
        "usage_unknown": error.usage_unknown if type(error.usage_unknown) is bool else None,
        "retryable": error.retryable if type(error.retryable) is bool else None,
        "provider_status": machine_field(error.provider_status, 64),
        "termination_reason": machine_field(error.termination_reason, 120),
        "request_id": machine_field(error.request_id, 200),
        "occurred_at": occurred_at.astimezone(UTC).isoformat()
            if isinstance(occurred_at, datetime) and occurred_at.tzinfo is not None else None,
    }
    observed = error.observed_usage
    usage = asdict(ModelUsage(unknown=True))
    if isinstance(observed, ModelUsage):
        invalid_numeric = False
        for field in ("input_tokens", "output_tokens", "cached_tokens", "reasoning_tokens", "total_tokens"):
            value = getattr(observed, field)
            valid = type(value) is int and value >= 0
            usage[field] = value if valid else None
            invalid_numeric |= value is not None and not valid
        usage["unknown"] = (type(observed.unknown) is not bool or observed.unknown
            or invalid_numeric or any(usage[field] is None for field in
                ("input_tokens", "output_tokens", "total_tokens")))
    retries = error.transport_retry_count
    return {"provider_failure": failure, "usage": usage,
        "transport_retry_count": retries if type(retries) is int and retries >= 0 else None}


_FULFILLMENT_WIRE_VERSION = "fulfillment-compact-v1"
_FULFILLMENT_WIRE_METADATA_KEYS = ("provider_wire_version", "wire_request_fingerprint",
    "wire_table_fingerprint", "wire_schema_fingerprint")


class _FulfillmentWireReceiptIdentityError(RuntimeError):
    """Owner receipt drift is not a model-candidate repair opportunity."""


class _FulfillmentWireValidationError(ValueError):
    """Unadmitted wire observations; never repaired routes or component IDs."""
    def __init__(self, code, diagnostics):
        super().__init__(code)
        self.diagnostics = diagnostics


class _FulfillmentCompactRoute(BaseModel):
    """Ephemeral ordinals over this exact input; never an admitted binding."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    s: StrictInt = Field(ge=0)
    c: StrictInt = Field(ge=0)
    a: StrictInt
    z: StrictInt
    q: str | None = Field(min_length=1, max_length=65536)
    f: tuple[StrictInt, ...]
    t: tuple[StrictInt, ...]
    u: tuple[StrictInt, ...]
    r: str = Field(min_length=1, max_length=1000)


class _FulfillmentCompactCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    v: Literal[1]
    h: str = Field(pattern=r"^[0-9a-f]{64}$")
    d: str = Field(pattern=r"^[0-9a-f]{64}$")
    routes: tuple[_FulfillmentCompactRoute, ...] = Field(min_length=1, max_length=1024)

    @field_validator("v", mode="before")
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("OBLIGATION_FORMATION_WIRE_VERSION_INVALID")
        return value


def _fulfillment_wire_schema():
    from spg.providers.semantic_wire import _provider_strict_output_schema
    return _provider_strict_output_schema(_FulfillmentCompactCandidate.model_json_schema())


def _fulfillment_wire_context(inventory, capabilities, *, validation_feedback=None, owner_preconditions=None):
    """Construct a reversible, request-local dictionary from original identities."""
    from spg.domain.change import safe_repository_path
    from spg.providers.verification_receipts import _safe_value
    sources = inventory["sources"]
    texts = tuple(fulfillment_source_semantic_text(source) for source in sources)
    source_refs = [source["source_ref"] for source in sources]
    names = [entry["capability"] for entry in capabilities]
    paths = list(inventory["exact_target_paths"])
    if (not source_refs or len(set(source_refs)) != len(source_refs)
            or not names or len(set(names)) != len(names)
            or len(set(paths)) != len(paths)
            or any(not isinstance(text, str) for text in texts)):
        raise ValueError("OBLIGATION_FORMATION_WIRE_TABLE_INVALID")
    for path in paths:
        if safe_repository_path(path) != path:
            raise ValueError("OBLIGATION_FORMATION_WIRE_TABLE_INVALID")
    tables = {"sources": [{"source_ref": source["source_ref"], "kind": source["kind"],
            "text_sha256": sha256(text.encode("utf-8")).hexdigest(), "text_length": len(text)}
            for source, text in zip(sources, texts)],
        "capabilities": deepcopy(list(capabilities)), "target_paths": paths}
    table_fingerprint = canonical_fingerprint(tables)
    schema_fingerprint = canonical_fingerprint(_fulfillment_wire_schema())
    feedback = _safe_value(validation_feedback)
    preconditions = _safe_value(owner_preconditions)
    if preconditions != owner_preconditions:
        raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_OWNER_PRECONDITION_IDENTITY_DRIFT")
    request_fingerprint = canonical_fingerprint({"operation": "work-fulfillment-formation",
        "wire_version": _FULFILLMENT_WIRE_VERSION,
        "inventory_fingerprint": inventory["inventory_fingerprint"],
        "capabilities_fingerprint": canonical_fingerprint(capabilities),
        "table_fingerprint": table_fingerprint, "schema_fingerprint": schema_fingerprint,
        "same_basis_validation_feedback": feedback,
        **({"owner_source_preconditions_fingerprint": canonical_fingerprint(preconditions)}
            if preconditions is not None else {})})
    return {"provider_wire_version": _FULFILLMENT_WIRE_VERSION,
        "wire_request_fingerprint": request_fingerprint,
        "wire_table_fingerprint": table_fingerprint, "wire_schema_fingerprint": schema_fingerprint,
        "tables": tables, "source_texts": texts, "validation_feedback": feedback}


def _wire_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("OBLIGATION_FORMATION_WIRE_DUPLICATE_KEY")
        result[key] = value
    return result


def _fulfillment_wire_diagnostics(wire, inventory, context):
    """Evaluate independent wire predicates without admitting a partial plan.

    No semantic classification or quote relocation occurs here. An explicit
    quote requiring the existing locator makes raw coverage non-evaluable.
    """
    sources, paths = inventory["sources"], context["tables"]["target_paths"]
    failures, covered, unlocated = [], {}, set()
    def add(code, index=None, **values):
        row = {"code": code, **values}
        if index is not None:
            route = wire.routes[index]
            row.update(route=index, source=route.s, capability=route.c,
                raw_route_fingerprint=canonical_fingerprint(route.model_dump(mode="json")))
        if row not in failures:
            failures.append(row)
    for index, route in enumerate(wire.routes):
        if route.s >= len(sources) or route.c >= len(context["tables"]["capabilities"]):
            add("OBLIGATION_FORMATION_WIRE_SOURCE_OR_CAPABILITY_INDEX_INVALID", index)
        for field, kind, size in (("f", "FACT", len(sources)), ("t", "TARGET", len(paths)),
                                  ("u", "SUPPORT", len(sources))):
            values = getattr(route, field)
            if len(set(values)) != len(values):
                add("OBLIGATION_FORMATION_WIRE_" + kind + "_INDEX_INVALID", index,
                    field=field, condition="DUPLICATE_INDEX")
            for value in values:
                if not 0 <= value < size:
                    add("OBLIGATION_FORMATION_WIRE_" + kind + "_INDEX_INVALID", index,
                        field=field, referenced_source=value, condition="OUT_OF_RANGE")
                elif field == "f" and sources[value]["kind"] != "FACT":
                    add("OBLIGATION_FORMATION_WIRE_FACT_KIND_INVALID", index,
                        field=field, referenced_source=value, expected_kind="FACT",
                        actual_kind=sources[value]["kind"])
        if route.s >= len(sources):
            continue
        text = context["source_texts"][route.s]
        valid_span = 0 <= route.a < route.z <= len(text)
        if route.q is None and not valid_span:
            add("OBLIGATION_FORMATION_WIRE_SPAN_INVALID", index, field="a/z")
        elif valid_span and (route.q is None or route.q == text[route.a:route.z]):
            covered.setdefault(route.s, set()).update(range(route.a, route.z))
        else:
            unlocated.add(route.s)
    for source, text in enumerate(context["source_texts"]):
        if source not in unlocated and any(not char.isspace() and offset not in covered.get(source, ())
                                          for offset, char in enumerate(text)):
            add("OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST", source=source)
    return {"violations": failures[:64], "additional_violation_count": max(0, len(failures)-64),
        "not_evaluable": ["CANONICAL_COMPONENT_VALIDATION", "OWNER_PHASE_EVIDENCE",
            "INDEPENDENT_SEMANTIC_REVIEW", "ACTUAL_OWNER_EVIDENCE", "ASSURANCE"],
        "coverage_not_evaluable_sources": sorted(unlocated)}


def _expand_fulfillment_wire_route(route, inventory, capabilities, context):
    """Expand one structurally valid route without admitting a plan."""
    sources, paths = inventory["sources"], context["tables"]["target_paths"]
    if route.s >= len(sources) or route.c >= len(capabilities):
        raise ValueError("OBLIGATION_FORMATION_WIRE_SOURCE_OR_CAPABILITY_INDEX_INVALID")
    for values, size, kind in ((route.f, len(sources), "FACT"),
                              (route.t, len(paths), "TARGET"), (route.u, len(sources), "SUPPORT")):
        if len(set(values)) != len(values) or any(value < 0 or value >= size for value in values):
            raise ValueError("OBLIGATION_FORMATION_WIRE_" + kind + "_INDEX_INVALID")
    if any(sources[index]["kind"] != "FACT" for index in route.f):
        raise ValueError("OBLIGATION_FORMATION_WIRE_FACT_KIND_INVALID")
    source, text = sources[route.s], context["source_texts"][route.s]
    if route.q is None and not 0 <= route.a < route.z <= len(text):
        raise ValueError("OBLIGATION_FORMATION_WIRE_SPAN_INVALID")
    from spg.domain.governed_obligation import FulfillmentRouteCandidate
    return FulfillmentRouteCandidate(source_ref=source["source_ref"],
        capability=capabilities[route.c]["capability"],
        work_constraint_indices=(source["index"],) if source["kind"] == "WORK_CONSTRAINT" else (),
        target_paths=tuple(paths[index] for index in route.t),
        supporting_source_refs=tuple(sources[index]["source_ref"] for index in route.u),
        rationale=route.r, component_basis={"source_span_start": route.a,
            "source_span_end": route.z, "source_component_quote": text[route.a:route.z] if route.q is None else route.q,
            "linked_fact_refs": tuple(sources[index]["source_ref"] for index in route.f)})


def _fulfillment_wire_route_observations(output, inventory, capabilities, *, validation_feedback=None, owner_preconditions=None):
    """Read exact raw routes for Owner diagnostics, never a partial Candidate.

    Identity/schema failures make every route non-evaluable. A malformed route
    cannot provide proof for another route. Full-plan validation is unchanged.
    """
    context = _fulfillment_wire_context(inventory, capabilities, validation_feedback=validation_feedback, owner_preconditions=owner_preconditions)
    try:
        wire = _FulfillmentCompactCandidate.model_validate(json.loads(output, object_pairs_hook=_wire_json_object))
    except ValueError:
        return (), ["RAW_ROUTE_OWNER_PRECONDITIONS"]
    if wire.h != context["wire_request_fingerprint"] or wire.d != context["wire_table_fingerprint"]:
        return (), ["RAW_ROUTE_OWNER_PRECONDITIONS"]
    observations, unavailable = [], []
    for index, raw in enumerate(wire.routes):
        try:
            route = _expand_fulfillment_wire_route(raw, inventory, capabilities, context)
            text = context["source_texts"][raw.s]
            # Quote relocation requires the complete candidate's existing
            # locator; do not invent a location in the diagnostic view.
            if not 0 <= raw.a < raw.z <= len(text) or route.component_basis.source_component_quote != text[raw.a:raw.z]:
                raise ValueError("OBLIGATION_COMPONENT_SOURCE_QUOTE_DRIFT")
        except ValueError:
            unavailable.append(index)
        else:
            observations.append((index, raw.model_dump(mode="json"), route))
    return tuple(observations), unavailable


def _decode_fulfillment_candidate_wire(output, inventory, capabilities, *,
                                     validation_feedback=None, wire_metadata=None, owner_preconditions=None):
    """Expand only metadata; all semantic route choices remain model candidates."""
    from spg.providers.verification_receipts import _safe_output, _safe_value
    context = _fulfillment_wire_context(inventory, capabilities, validation_feedback=validation_feedback, owner_preconditions=owner_preconditions)
    if wire_metadata is not None and any(wire_metadata.get(key) != context[key]
            for key in _FULFILLMENT_WIRE_METADATA_KEYS):
        raise _FulfillmentWireReceiptIdentityError("OBLIGATION_FORMATION_WIRE_RECEIPT_IDENTITY_DRIFT")
    raw_fingerprint = (sha256(output.encode("utf-8")).hexdigest() if isinstance(output, str)
                       else canonical_fingerprint(output))
    diagnostic_basis = {"schema": "fulfillment-wire-diagnostics-v1",
        "wire_output_fingerprint": raw_fingerprint,
        "inventory_fingerprint": inventory["inventory_fingerprint"],
        **{key: context[key] for key in _FULFILLMENT_WIRE_METADATA_KEYS}}
    try:
        if isinstance(output, str):
            output = json.loads(output, object_pairs_hook=_wire_json_object)
        wire = _FulfillmentCompactCandidate.model_validate(output)
    except ValueError as error:
        code = (str(error) if str(error) == "OBLIGATION_FORMATION_WIRE_DUPLICATE_KEY" else
                "OBLIGATION_FORMATION_WIRE_JSON_INVALID" if isinstance(error, json.JSONDecodeError) else
                "OBLIGATION_FORMATION_WIRE_SCHEMA_INVALID")
        raise _FulfillmentWireValidationError(code, {**diagnostic_basis,
            "violations": [{"code": code}], "additional_violation_count": 0,
            "not_evaluable": ["WIRE_ROUTE_VALIDATION", "CANONICAL_COMPONENT_VALIDATION",
                "OWNER_PHASE_EVIDENCE", "INDEPENDENT_SEMANTIC_REVIEW", "ACTUAL_OWNER_EVIDENCE", "ASSURANCE"]}) from error
    if wire.h != context["wire_request_fingerprint"] or wire.d != context["wire_table_fingerprint"]:
        code = "OBLIGATION_FORMATION_WIRE_BASIS_DRIFT"
        raise _FulfillmentWireValidationError(code, {**diagnostic_basis,
            "violations": [{"code": code}], "additional_violation_count": 0,
            "not_evaluable": ["WIRE_ROUTE_VALIDATION", "CANONICAL_COMPONENT_VALIDATION",
                "OWNER_PHASE_EVIDENCE", "INDEPENDENT_SEMANTIC_REVIEW", "ACTUAL_OWNER_EVIDENCE", "ASSURANCE"]})
    diagnostics = _fulfillment_wire_diagnostics(wire, inventory, context)
    if diagnostics["violations"]:
        raise _FulfillmentWireValidationError(diagnostics["violations"][0]["code"],
            {**diagnostic_basis, **diagnostics})
    routes = [_expand_fulfillment_wire_route(route, inventory, capabilities, context) for route in wire.routes]
    candidate = FulfillmentProjectionCandidate(inventory_fingerprint=inventory["inventory_fingerprint"], routes=tuple(routes))
    payload = candidate.model_dump(mode="json")
    # Compare decoded values before JSON escaping can hide a known secret.
    if _safe_value(payload) != payload:
        raise ValueError("OBLIGATION_FORMATION_EXPANDED_SECRET_BACKFILL")
    expanded = candidate.model_dump_json()
    safe_expanded, _digest, _count = _safe_output(expanded)
    if safe_expanded is None:
        raise ValueError("OBLIGATION_FORMATION_EXPANDED_RECEIPT_LIMIT")
    if safe_expanded != expanded:
        raise ValueError("OBLIGATION_FORMATION_EXPANDED_SECRET_BACKFILL")
    return candidate


def _safe_fulfillment_response_output(text):
    """Retain only a privacy-safe observation, without repairing the candidate.

    This parse is solely for privacy: keep duplicate values and object keys so
    neither JSON escaping nor a duplicate key can hide a known sensitive value.
    Formal schema and duplicate-key rejection remain the decoder's responsibility.
    """
    from spg.providers.verification_receipts import _safe_output, _safe_value
    output, digest, count = _safe_output(text)
    if output is None:
        return output, digest, count, None
    if output != text:
        return None, digest, count, "SECRET_BACKFILL"
    try:
        decoded = json.loads(text, object_pairs_hook=lambda pairs: [
            [key, value] for key, value in pairs])
    except (json.JSONDecodeError, ValueError, RecursionError):
        # An invalid JSON document with escapes cannot be proved privacy-safe.
        # Preserve its observation identity, without retaining recoverable text.
        if "\\" in text:
            return None, digest, count, "UNSAFE_JSON_RECEIPT"
    else:
        if _safe_value(decoded) != decoded:
            return None, digest, count, "SECRET_BACKFILL"
    return output, digest, count, None


class ModelFulfillmentCandidateProvider:
    def __init__(self, runtime_factory):
        self.runtime_factory = runtime_factory
        self.last_observation = None

    @classmethod
    def from_settings(cls, settings):
        if settings.deepseek_api_key is None or settings.wic_provider_adapter != "deepseek":
            return None
        def runtime_factory():
            from spg.domain.model_runtime import (ModelProfile, ModelProvider,
                ModelProviderRegistry, PurposeProfileRouter, WattModelRuntime)
            from spg.infrastructure.model_runtime import DeepSeekResponsesModelAdapter
            registry = ModelProviderRegistry()
            registry.register(DeepSeekResponsesModelAdapter(
                api_key=lambda: settings.deepseek_api_key.get_secret_value(),
                base_url=settings.deepseek_base_url))
            profile = ModelProfile(purpose=ModelPurpose.STEERING_SEMANTIC,
                provider=ModelProvider.DEEPSEEK, model=settings.wic_provider_model or "deepseek-flash",
                reasoning_effort=settings.wic_provider_reasoning_effort,
                timeout_seconds=settings.collaboration_provider_timeout_seconds,
                max_output_tokens=settings.collaboration_provider_max_output_tokens)
            return WattModelRuntime(registry, PurposeProfileRouter({ModelPurpose.STEERING_SEMANTIC: profile}))
        return cls(runtime_factory)

    def form_wire_metadata(self, inventory, capabilities, *, validation_feedback=None, owner_preconditions=None):
        context = _fulfillment_wire_context(inventory, capabilities, validation_feedback=validation_feedback, owner_preconditions=owner_preconditions)
        return {key: context[key] for key in _FULFILLMENT_WIRE_METADATA_KEYS}

    def form(self, inventory, capabilities, *, validation_feedback=None, receipt_callback=None, owner_preconditions=None):
        self.last_observation = None
        context = _fulfillment_wire_context(inventory, capabilities, validation_feedback=validation_feedback, owner_preconditions=owner_preconditions)
        wire_metadata = {key: context[key] for key in _FULFILLMENT_WIRE_METADATA_KEYS}
        runtime = self.runtime_factory()
        try:
            result = runtime.generate(purpose=ModelPurpose.STEERING_SEMANTIC,
                instructions=(
                    "You propose a derived fulfillment plan for immutable admitted engineering meaning. "
                    "Use the original Fact relation/value/order/scope/qualifiers and governed clause meaning, "
                    "provenance, authority and production context. Subject spelling is not a routing vocabulary. "
                    "Do not reinterpret or replace accepted meaning from raw Human quotes. Quotes identify "
                    "provenance. Distinguish exact artifact outcomes, Git scope, authoritative source identity, "
                    "continuous prohibitions, Candidate sealing, future Human permission and contextual facts. "
                    "A Fact is not necessarily an execution obligation. A future Human gate is pending, never "
                    "already satisfied. A current continuous prohibition must bind an actual execution/delivery gate. "
                    "Return only the supplied temporary compact wire. Echo v=1, h=request fingerprint and "
                    "d=table fingerprint exactly. Every route chooses s=source ordinal, c=capability ordinal, "
                    "a/z=source component character offsets in Python Unicode code points: [a,z), "
                    "a inclusive, z exclusive. A whole source of length L is [0,L), never [0,L-1). "
                    "f=linked FACT source ordinals, "
                    "t=target-path ordinals, u=supporting-source ordinals, and r=bounded rationale. "
                    "The field domains use the SAME source ordinals, not a new index space. f may contain "
                    "only entries listed in f_allowed_source_ordinals; do not copy s into f by default. "
                    "Non-Fact supporting clauses belong in u, never f. On feedback, inspect the bound "
                    "untrusted_previous_wire and its identified failures before proposing a complete new plan. "
                    "u is provenance support, NEVER a component disposition for the referenced source: each "
                    "source still needs its own s routes with complete [a,z) coverage. Equal original text "
                    "does not merge distinct source identities. Consult owner_repair_context when supplied: "
                    "its exact correspondence origins and evidence prerequisites are necessary conditions, "
                    "Consult owner_source_preconditions before the FIRST proposal too. Its minimal support sets "
                    "describe admissible provenance proofs, not semantic matches or preselected routes. Choose a "
                    "semantically correct set; a FACT in f does not replace original clause supports in u. "
                    "Never attach whole-source UNRESOLVED or RETAIN_CONTEXT over an already bound component. "
                    "A current explicit request is not background merely because it also explains the Work. "
                    "not pre-approved routes, evidence or authority. All selected supports must legitimately "
                    "correspond; do not add same-clause references merely because their text looks similar. "
                    "That old proposal is not authority and must not be admitted or blindly copied. Preserve "
                    "all original requirements; correct the failed predicates without introducing new errors. "
                    "Echo the CURRENT h/d from temporary_wire, not those of the previous proposal. "
                    "q=null lets the Owner restore the exact source slice. If exact offsets are uncertain, "
                    "q may be the original exact component quote; the existing unique-quote locator may "
                    "correct offsets, but repeated or invented quotes cannot establish an ambiguous location. "
                    "Choose all component boundaries and semantic links yourself; the Owner only expands metadata. "
                    "The union of component spans must preserve every source contribution. Current intent "
                    "does not imply every contribution is an HTML constraint: Candidate sealing and Human "
                    "authorization bind actual lifecycle gates. Separate mixed content from lifecycle without "
                    "losing independent current content requirements, original values, order or scope. "
                    "Represent EVERY supplied source_ref and EVERY work_constraint index, allowing multiple "
                    "routes for mixed meaning, without merging distinct components to shorten output. "
                    "Same-source same-capability routes require genuinely distinct components, not different rationales "
                    "for an identical component. RETAIN_CONTEXT and UNRESOLVED are component dispositions, not "
                    "extra record-preservation routes to append to executable contributions. Do not lose punctuation "
                    "or silently shorten a source slice. Qualified exclusive file Scope retains its qualifiers and "
                    "uses exact Git-diff evidence; file/page exclusions are not deployment permissions. A prohibition "
                    "Fact must cite its exact negative clause with the same actual gate; do not fabricate a typed effect "
                    "or assign preview prohibition when the original contribution does not require it. "
                    "The Owner restores each WORK_CONSTRAINT source's own index; other sources have no constraint index. "
                    "Supporting source ordinals cite exact "
                    "original typed clauses needed for a continuous or future Work-constraint gate. IR_ITEM "
                    "and WORK_CONTEXT only retain observed/context meaning or remain unresolved. Use only existing "
                    "capability contracts. You may not invent tests, witnesses, Owner records, permissions or PASS. "
                    "If a legal method/phase/source correspondence cannot be established choose UNRESOLVED, "
                    "keeping the original requirement. RETAIN_CONTEXT preserves authoritative context and "
                    "does not prove an execution outcome. Target paths must be exact supplied governed paths; "
                    "GIT_DIFF_SCOPE must preserve the complete supplied path set. Content checks use exact "
                    "candidate content; lifecycle constraints must not be sent to source-string witnesses. "
                    "A negative CURRENT clause may establish a prohibition; a future/hypothetical/affirmative "
                    "clause cannot supply one. Never broaden effect permits, facts or Human authority."),
                input_text=json.dumps({"immutable_inventory": inventory,
                    "existing_capability_contracts": capabilities,
                    **({"owner_source_preconditions": owner_preconditions} if owner_preconditions is not None else {}),
                    "same_basis_validation_feedback": context["validation_feedback"],
                    "temporary_wire": {**wire_metadata,
                        "f_allowed_source_ordinals": [index for index, source in enumerate(inventory["sources"])
                            if source["kind"] == "FACT"],
                        "source_index_table": [{"index": index, **entry} for index, entry in enumerate(context["tables"]["sources"])],
                        "capability_index_table": [{"index": index, "capability": entry["capability"]}
                            for index, entry in enumerate(context["tables"]["capabilities"])],
                        "target_index_table": [{"index": index, "path": path}
                            for index, path in enumerate(context["tables"]["target_paths"])]}}, ensure_ascii=False),
                output_schema=_fulfillment_wire_schema())
            self.last_observation = {"request_id": result.request_id,
                "provider": result.provider.value,
                "requested_model": result.requested_model, "effective_model": result.effective_model,
                "usage": asdict(result.usage), "timing": asdict(result.timing),
                "transport_retry_count": result.retry_count,
                "output_sha256": sha256(result.output_text.encode()).hexdigest(),
                "output_bytes": len(result.output_text.encode())}
            safe_output, output_digest, output_bytes, privacy_failure = (
                _safe_fulfillment_response_output(result.output_text))
            if receipt_callback is not None:
                receipt_callback(candidate_output=safe_output, candidate_output_sha256=output_digest,
                    candidate_output_bytes=output_bytes, candidate_retained=safe_output is not None,
                    model=self.last_observation, **wire_metadata)
            if privacy_failure is not None:
                raise ValueError("OBLIGATION_FORMATION_" + privacy_failure)
            if safe_output is None:
                raise ValueError("OBLIGATION_FORMATION_RECEIPT_LIMIT")
            return _decode_fulfillment_candidate_wire(safe_output, inventory, capabilities,
                validation_feedback=validation_feedback, wire_metadata=wire_metadata, owner_preconditions=owner_preconditions)
        except Exception as error:
            failure = provider_failure_observation(error)
            if failure is not None:
                self.last_observation = failure
            raise
        finally:
            runtime.close()


    def review(self, inventory, candidate, *, capabilities, receipt_callback=None):
        """One independent semantic review; no review retry or authority verdict."""
        from spg.providers.semantic_wire import _provider_strict_output_schema
        self.last_observation = None
        runtime = self.runtime_factory()
        try:
            result = runtime.generate(purpose=ModelPurpose.STEERING_SEMANTIC,
                instructions=("Independently validate a derived fulfillment candidate against the immutable admitted "
                    "engineering inventory. The candidate is untrusted; its rationale is not evidence. For EVERY exact "
                    "source_ref decide whether its complete meaning is preserved by the source-linked component "
                    "spans, original Fact references, selected consumer contracts and fulfillment phases. Do not "
                    "change accepted Fact relation/value/order/scope/qualifiers/provenance/authority. A current request "
                    "may require future Candidate/Human stages; do not mistake grammatical tense for evidence type. "
                    "Pure lifecycle contributions use existing lifecycle gates; mixed artifact requirements must retain "
                    "their own exact current content verification and all governance components. No independent content "
                    "requirement may be replaced by unrelated Fact evidence, delayed as authorization, or retained as "
                    "context. Production.exclusions derivations must preserve their original values and exact original "
                    "negative clause meaning; absent typed effects must remain absent. Do not infer permissions from absence of logs. Reject missing, "
                    "wrong or unsupported semantic correspondence. UNRESOLVED preserves uncertainty. Return only the "
                    "review candidate with exact supplied fingerprints and one result per source, plus one "
                    "component_results entry per supplied (component_id, capability). Verify component nonredundancy, "
                    "exact meaning, all qualifiers, legitimate context-only disposition and actual Owner/Phase/Evidence "
                    "sufficiency. A whole-source reuse cannot conceal a lost semantic component. This review is only "
                    "derived-plan semantic validation, not Assurance, Verification PASS, a fact or Human authority."),
                input_text=json.dumps({"immutable_inventory": inventory,
                    "untrusted_fulfillment_candidate": candidate.model_dump(mode="json"),
                    "component_index_table": [{"component_id": fulfillment_component_id(route, inventory["inventory_fingerprint"]),
                        "capability": route.capability} for route in candidate.routes],
                    "existing_capability_contracts": capabilities,
                    "candidate_fingerprint": fulfillment_candidate_fingerprint(candidate),
                    "components_fingerprint": fulfillment_components_fingerprint(candidate)}, ensure_ascii=False),
                output_schema=_provider_strict_output_schema(FulfillmentSemanticReviewCandidate.model_json_schema()))
            self.last_observation = {"request_id": result.request_id, "provider": result.provider.value,
                "requested_model": result.requested_model, "effective_model": result.effective_model,
                "usage": asdict(result.usage), "timing": asdict(result.timing),
                "transport_retry_count": result.retry_count,
                "output_sha256": sha256(result.output_text.encode()).hexdigest(),
                "output_bytes": len(result.output_text.encode())}
            output, digest, count, privacy_failure = (
                _safe_fulfillment_response_output(result.output_text))
            if receipt_callback is not None:
                receipt_callback(review_output=output, review_output_sha256=digest, review_output_bytes=count,
                    review_retained=output is not None, model=self.last_observation)
            if privacy_failure is not None:
                raise ValueError("OBLIGATION_SEMANTIC_REVIEW_" + privacy_failure)
            if output is None:
                raise ValueError("OBLIGATION_SEMANTIC_REVIEW_RECEIPT_LIMIT")
            return FulfillmentSemanticReviewCandidate.model_validate_json(output)
        except Exception as error:
            failure = provider_failure_observation(error)
            if failure is not None:
                self.last_observation = failure
            raise
        finally:
            runtime.close()
