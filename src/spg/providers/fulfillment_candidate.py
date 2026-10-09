"""Open, read-only fulfillment candidates beneath existing Work governance.

The model chooses a consumer capability from admitted meaning. It cannot return
satisfaction, modify facts, supply evidence or authorize an effect.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
import json
import re

from spg.domain.governed_obligation import (FulfillmentProjectionCandidate, FulfillmentSemanticReviewCandidate,
    fulfillment_candidate_fingerprint, fulfillment_components_fingerprint)
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

    def form(self, inventory, capabilities, *, validation_feedback=None, receipt_callback=None):
        from spg.providers.semantic_wire import _provider_strict_output_schema
        self.last_observation = None
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
                    "Every route must carry component_basis with exact source_span_start/end and "
                    "source_component_quote from the immutable source text, plus only original linked_fact_refs. "
                    "The union of component spans must preserve every source contribution. Current intent "
                    "does not imply every contribution is an HTML constraint: Candidate sealing and Human "
                    "authorization bind actual lifecycle gates. Separate mixed content from lifecycle without "
                    "losing independent current content requirements, original values, order or scope. "
                    "Represent EVERY supplied source_ref and EVERY work_constraint index, allowing multiple "
                    "routes for mixed meaning. A WORK_CONSTRAINT source must carry only its own index; "
                    "all other source kinds carry no work_constraint_indices. supporting_source_refs cite exact "
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
                    "same_basis_validation_feedback": validation_feedback}, ensure_ascii=False),
                output_schema=_provider_strict_output_schema(FulfillmentProjectionCandidate.model_json_schema()))
            self.last_observation = {"request_id": result.request_id,
                "provider": result.provider.value,
                "requested_model": result.requested_model, "effective_model": result.effective_model,
                "usage": asdict(result.usage), "timing": asdict(result.timing),
                "transport_retry_count": result.retry_count,
                "output_sha256": sha256(result.output_text.encode()).hexdigest(),
                "output_bytes": len(result.output_text.encode())}
            from spg.providers.verification_receipts import _safe_output
            safe_output, output_digest, output_bytes = _safe_output(result.output_text)
            if receipt_callback is not None:
                receipt_callback(candidate_output=safe_output, candidate_output_sha256=output_digest,
                    candidate_output_bytes=output_bytes, candidate_retained=safe_output is not None,
                    model=self.last_observation)
            if safe_output is None:
                raise ValueError("OBLIGATION_FORMATION_RECEIPT_LIMIT")
            return FulfillmentProjectionCandidate.model_validate_json(safe_output)
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
        from spg.providers.verification_receipts import _safe_output
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
                    "negative typed clause effects; do not infer permissions from absence of logs. Reject missing, "
                    "wrong or unsupported semantic correspondence. UNRESOLVED preserves uncertainty. Return only the "
                    "review candidate with exact supplied fingerprints and one result per source. This review is only "
                    "derived-plan semantic validation, not Assurance, Verification PASS, a fact or Human authority."),
                input_text=json.dumps({"immutable_inventory": inventory,
                    "untrusted_fulfillment_candidate": candidate.model_dump(mode="json"),
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
            output, digest, count = _safe_output(result.output_text)
            if receipt_callback is not None:
                receipt_callback(review_output=output, review_output_sha256=digest, review_output_bytes=count,
                    review_retained=output is not None, model=self.last_observation)
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
