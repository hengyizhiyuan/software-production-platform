"""Human-authorized exact C3 plan observation; no Work/Owner writes or retry loop."""
import sys
sys.dont_write_bytecode = True
import argparse
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
import inspect
import json
import os
from pathlib import Path
import re
import time

SOURCE = "e0df8196cb51480f542af13b40cfa77fca6b6a6e"
BASIS_SHA = "9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c"
INVENTORY = "7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf"
ATTESTATION_SHA = "fea7676b7c6bdfec6aa6d1fa1e6665a67ac0e205157cc48dc11af158a6823f12"
METADATA = {
    "provider_wire_version": "fulfillment-compact-v1",
    "wire_request_fingerprint": "4b995573e01820631e063d0108388140be8576c3ac385a38da88d8ee87ea62d4",
    "wire_table_fingerprint": "cddd1ffc3429695d19411d42c5d6b741534460496705dbb0a430ff138df9e429",
    "wire_schema_fingerprint": "5668e226eb8d38c0f4bf9004ea8fc7aa363e9d388f64927783252f562d78ad40",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def main(execute):
    from spg.config import Settings
    from spg.domain.interaction import WorkRealityRevision
    from spg.domain.intent_realization import GovernedSemanticIR
    from spg.domain.model_runtime import ModelPurpose, PurposeProfileRouter
    from spg.application.governed_obligations import (
        fulfillment_inventory, fulfillment_capability_contracts,
        locate_projection_components, validate_projection_candidate,
    )
    from spg.domain.governed_obligation import (
        fulfillment_candidate_fingerprint, fulfillment_components_fingerprint,
        canonical_fingerprint,
    )
    from spg.providers.fulfillment_candidate import (
        ModelFulfillmentCandidateProvider, provider_failure_observation,
    )
    from spg.providers.verification_receipts import _safe_value
    from spg.infrastructure.model_runtime import httpx2

    out = Path("/c3-evidence/reasoning-mode-result.json")
    private = Path("/c3-private")
    if execute and out.exists():
        raise RuntimeError("LIVE_RESULT_ALREADY_EXISTS")
    started = now()
    clock = time.monotonic()
    row = {
        "schema": "c3-authorized-reasoning-none-control-v1", "started_at_utc": started,
        "application_source": SOURCE, "application_tree": "d479d61f5fcac075a5af3a274f60cbe3f6e9f53f",
        "guardian_source": "d01bac1ad153e1eadefafe87d2ea4f5d65896ab6",
        "ecf_source": "5aa4f8833c359c15bd059eda5972aa3915bcc18c",
        "authorization": "Human 2026-10-10 approved one isolation contrast: Formation none, conditional Review low, zero retries",
        "new_work_created": False, "historical_owner_mutated": False, "business_database_access": False,
        "retry_policy": "NO_LOGICAL_OR_TRANSPORT_RETRY",
        "self_refine_calls": 0, "holdout_access": False, "production_resource_mutation": False,
        "logical_model_entries": 0, "calls": [], "deterministic_checks": [],
        "candidate_stage": "NOT_REACHED", "semantic_review_stage": "NOT_REACHED",
        "historical_causal_exclusivity": "UNKNOWN", "visible_json_token_count": "UNKNOWN",
        "runtime_consumer_admission": "NOT_EXECUTED; isolated candidate validator only, no Owner or Work admission",
        "qualification_boundary": "isolated derived fulfillment plan only; no Work/Candidate seal, Verification, Guardian or Human authority",
    }
    active = None
    provider = None
    refs = {}

    def write_json(path, value):
        if _safe_value(value) != value:
            raise RuntimeError("EVIDENCE_SAFE_VALUE_REJECTED")
        with path.open("w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")

    def checkpoint():
        if execute:
            write_json(out, row)

    def machine(value, limit=200):
        if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_.:-]{1," + str(limit) + "}", value) is None:
            return None
        return value if _safe_value(value) == value else None

    def private_json(name, value):
        target = private / name
        if target.exists():
            raise RuntimeError("PRIVATE_OBSERVATION_ALREADY_EXISTS")
        write_json(target, value)
        row.setdefault("private_artifacts", []).append({"name": name, "sha256": sha256(target.read_bytes()).hexdigest(), "bytes": target.stat().st_size, "public_content": False})

    def callback(kind, **values):
        output_key = "candidate_output" if kind == "formation" else "review_output"
        text = values.get(output_key)
        active["output_observation"] = {key: value for key, value in values.items() if key != output_key}
        if text is not None:
            # The frozen Provider's privacy check already ran; never retain an altered value.
            if _safe_value(text) != text:
                raise RuntimeError("PRIVATE_OBSERVATION_UNSAFE")
            target = private / (kind + "-safe-wire.txt")
            if target.exists():
                raise RuntimeError("PRIVATE_OBSERVATION_ALREADY_EXISTS")
            with target.open("x", encoding="utf-8") as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(text)
            row.setdefault("private_artifacts", []).append({"name": target.name,
                "sha256": sha256(target.read_bytes()).hexdigest(), "bytes": target.stat().st_size, "public_content": False})
        checkpoint()

    def candidate_summary(candidate):
        return {
            "candidate_fingerprint": fulfillment_candidate_fingerprint(candidate),
            "components_fingerprint": fulfillment_components_fingerprint(candidate),
            "routes": [{"source_ordinal": refs[route.source_ref], "capability": route.capability,
                "constraint_indices": list(route.work_constraint_indices), "target_paths": list(route.target_paths),
                "support_ordinals": [refs.get(ref) for ref in route.supporting_source_refs],
                "component": None if route.component_basis is None else {
                    "start": route.component_basis.source_span_start, "end": route.component_basis.source_span_end,
                    "quote_sha256": sha256(route.component_basis.source_component_quote.encode()).hexdigest(),
                    "fact_ordinals": [refs.get(ref) for ref in route.component_basis.linked_fact_refs]},
                "rationale_sha256": sha256(route.rationale.encode()).hexdigest()} for route in candidate.routes],
        }

    try:
        basis = Path("/basis.json").read_bytes()
        assert sha256(basis).hexdigest() == BASIS_SHA, "BASIS_HASH_DRIFT"
        attestation = Path("/qualified-imports.json").read_bytes()
        assert sha256(attestation).hexdigest() == ATTESTATION_SHA, "ATTESTATION_HASH_DRIFT"
        imported = json.loads(attestation)["actual_imports"]
        checked = {}
        for owner in ("spg", "guardian", "ecf"):
            expected = imported[owner]
            package = Path(expected["package_root"])
            for relative, digest in expected["file_sha256"].items():
                assert sha256((package / relative).read_bytes()).hexdigest() == digest, "INSTALLED_OWNER_HASH_DRIFT"
            checked[owner] = len(expected["file_sha256"])
        row["installed_owner_file_hashes"] = {"status": "PASS", "counts": checked, "attestation_sha256": ATTESTATION_SHA}
        data = json.loads(basis)
        revision = WorkRealityRevision.model_validate(next(item for item in data["datasets"]["work_reality_revisions"]["rows"] if item["id"] == "332a3a38-8719-580c-a1a2-c331ae14a5ae"))
        assessment = next(item for item in data["datasets"]["interaction_assessments"]["rows"] if item["id"] == str(revision.source_assessment_id))
        ir = GovernedSemanticIR.model_validate(assessment["semantic_ir"])
        inventory = fulfillment_inventory(revision, ir, source_revision="465038ded6cf4ba335a11577de76acb1dea55b76", exact_target_paths=("index.html",))
        assert inventory["inventory_fingerprint"] == INVENTORY and len(inventory["sources"]) == 26, "INVENTORY_DRIFT"
        refs = {source["source_ref"]: ordinal for ordinal, source in enumerate(inventory["sources"])}
        capabilities = fulfillment_capability_contracts()
        assert len(capabilities) == 12, "CAPABILITIES_DRIFT"
        settings = Settings()
        provider = ModelFulfillmentCandidateProvider.from_settings(settings)
        assert provider is not None, "CONFIGURED_PROVIDER_UNAVAILABLE"
        assert provider.form_wire_metadata(inventory, capabilities) == METADATA, "WIRE_IDENTITY_DRIFT"
        row.update(basis_sha256=BASIS_SHA, work_id=str(revision.work_id), reality_id=str(revision.id),
            inventory_fingerprint=INVENTORY, source_count=26, capability_count=12,
            capabilities_fingerprint=canonical_fingerprint(capabilities), wire_metadata=METADATA)
        factory = provider.runtime_factory
        preflight_operation = "formation"

        def runtime_factory():
            runtime = factory()
            base_profile = runtime.profile(ModelPurpose.STEERING_SEMANTIC)
            assert base_profile.reasoning_effort == "low", "BASE_PROFILE_DRIFT"
            operation = active["operation"] if active is not None else preflight_operation
            profile = replace(base_profile, reasoning_effort="none" if operation == "formation" else "low")
            runtime.router = PurposeProfileRouter({ModelPurpose.STEERING_SEMANTIC: profile})
            adapter = runtime.registry.adapter(profile.provider)
            actual_profile = {"provider": profile.provider.value, "model": profile.model,
                "reasoning_effort": profile.reasoning_effort, "timeout_seconds": profile.timeout_seconds,
                "max_output_tokens": profile.max_output_tokens, "base_url": adapter.base_url}
            expected_profile = {"provider": "deepseek", "model": "deepseek-flash", "reasoning_effort": "none" if operation == "formation" else "low",
                "timeout_seconds": 120, "max_output_tokens": 16384, "base_url": "https://api.deepseek.com"}
            assert actual_profile == expected_profile, "MODEL_PROFILE_DRIFT"
            row.setdefault("profiles", {})[operation] = actual_profile

            def request_hook(request):
                assert {"bytes": len(request.content), "sha256": sha256(request.content).hexdigest()} == active["request_entity"], "ACTUAL_REQUEST_ENTITY_DRIFT"
                active["http_request_hooks"].append({"at_utc": now(), "body_bytes": len(request.content), "body_sha256": sha256(request.content).hexdigest()})
                assert len(active["http_request_hooks"]) <= 1, "TRANSPORT_ATTEMPT_LIMIT"
                checkpoint()

            def response_hook(response):
                observation = {"status_code": response.status_code, "at_utc": now(),
                    "request_id": machine(response.headers.get("x-request-id") or response.headers.get("request-id"))}
                if response.status_code >= 400:
                    try:
                        payload = json.loads(response.read())
                        error = payload.get("error", {}) if isinstance(payload, dict) else {}
                        if isinstance(error, dict):
                            observation.update(error_code=machine(error.get("code"), 120), error_type=machine(error.get("type"), 120))
                    except Exception as error:
                        observation["error_body_parse_type"] = type(error).__name__
                active["http_responses"].append(observation)
                checkpoint()

            def attach(client):
                client.event_hooks["request"].append(request_hook)
                client.event_hooks["response"].append(response_hook)
                return client

            original_new = adapter._new_client
            adapter._new_client = lambda: attach(original_new())
            attach(adapter._client)
            original_generate = runtime.generate

            def generate(**kwargs):
                assert execute and active is not None, "LIVE_EXECUTION_NOT_AUTHORIZED"
                assert kwargs.get("on_stage") is None and kwargs.get("on_output_delta") is None, "UNEXPECTED_CALLBACK"
                payload = adapter._payload(profile=profile, instructions=kwargs["instructions"], input_text=kwargs["input_text"], output_schema=kwargs["output_schema"])
                entity = httpx2.Request("POST", "https://api.deepseek.com/responses", json=payload).content
                active["request_entity"] = {"bytes": len(entity), "sha256": sha256(entity).hexdigest()}
                if active["operation"] == "formation":
                    low_payload = adapter._payload(profile=base_profile, instructions=kwargs["instructions"], input_text=kwargs["input_text"], output_schema=kwargs["output_schema"])
                    low_entity = httpx2.Request("POST", "https://api.deepseek.com/responses", json=low_payload).content
                    assert len(low_entity) == 54365 and sha256(low_entity).hexdigest() == "9e9e5ab4753c4e20115e721b2c933cd9db20a1c36a7744dd7e037073eea3041d", "BASE_FORMATION_REQUEST_DRIFT"
                    comparable = dict(payload)
                    comparable["reasoning"] = {"effort": "low"}
                    assert payload["reasoning"] == {"effort": "none"} and comparable == low_payload, "UNAUTHORIZED_PAYLOAD_DIFFERENCE"
                    active["request_contrast"] = {"status": "ONLY_REASONING_EFFORT_DIFFERS", "baseline_effort": "low", "actual_effort": "none", "baseline_body_sha256": sha256(low_entity).hexdigest(), "baseline_body_bytes": len(low_entity)}
                row["logical_model_entries"] += 1
                assert row["logical_model_entries"] == (1 if active["operation"] == "formation" else 2), "LOGICAL_REQUEST_ORDER_OR_LIMIT"
                checkpoint()
                def stage(name):
                    active["stages"].append({"stage": machine(name), "at_utc": now()})
                    checkpoint()
                    if name == "provider_transport_recovery":
                        active["transport_retry_blocked_before_replay"] = True
                        checkpoint()
                        raise RuntimeError("DIAGNOSTIC_TRANSPORT_RETRY_FORBIDDEN")
                result = original_generate(**kwargs, on_stage=stage)
                active.update(provider_status="completed", provider_status_source="frozen Runtime completed-terminal contract",
                    request_id=machine(result.request_id), usage=asdict(result.usage), timing=asdict(result.timing),
                    transport_retry_count=result.retry_count, effective_model=machine(result.effective_model),
                    output_bytes=len(result.output_text.encode()), output_sha256=sha256(result.output_text.encode()).hexdigest())
                checkpoint()
                return result
            runtime.generate = generate
            return runtime

        provider.runtime_factory = runtime_factory
        for preflight_operation in ("formation", "semantic_review"):
            local_runtime = runtime_factory()
            local_runtime.close()
        row["preflight"] = "PASS_LOCAL_NO_HTTP"
        if not execute:
            print(json.dumps({"preflight": "PASS", "source": SOURCE, "inventory": INVENTORY,
                "source_count": 26, "profiles": row["profiles"], "wire_metadata": METADATA, "logical_model_entries": 0}, sort_keys=True))
            return
        checkpoint()

        def begin(operation):
            call = {"operation": operation, "started_at_utc": now(), "stages": [], "http_request_hooks": [],
                "http_responses": [], "usage": "UNKNOWN", "provider_status": "UNKNOWN", "visible_json_tokens": "UNKNOWN"}
            row["calls"].append(call)
            return call

        active = begin("formation")
        row["failure_stage"] = "FORMATION"
        candidate = provider.form(inventory, capabilities, receipt_callback=lambda **values: callback("formation", **values))
        active["ended_at_utc"] = now()
        row["candidate_stage"] = "PARSED_NOT_AUTHORITY"
        row["raw_candidate"] = candidate_summary(candidate)
        private_json("formation-expanded-candidate.json", candidate.model_dump(mode="json"))
        row["failure_stage"] = "DETERMINISTIC_CANDIDATE_VALIDATION"
        candidate, adjustments = locate_projection_components(candidate, inventory)
        row["locator_adjustments"] = list(adjustments)
        row["canonical_candidate"] = candidate_summary(candidate)
        private_json("formation-located-candidate.json", candidate.model_dump(mode="json"))
        preliminary = validate_projection_candidate(candidate, revision, ir, inventory, allow_review_pending=True)
        row["deterministic_checks"].append({"stage": "PRE_REVIEW", "status": "PASS", "binding_count": len(preliminary),
            "state_counts": dict(Counter(str(binding.state) for binding in preliminary))})
        if any(binding.state == "UNRESOLVED" for binding in preliminary):
            raise ValueError("OBLIGATION_PROJECTION_UNRESOLVED")
        row["candidate_stage"] = "DETERMINISTIC_VALID_NOT_SEMANTICALLY_REVIEWED"
        checkpoint()
        active = begin("semantic_review")
        row["failure_stage"] = "SEMANTIC_REVIEW"
        review = provider.review(inventory, candidate, capabilities=capabilities,
            receipt_callback=lambda **values: callback("review", **values))
        active["ended_at_utc"] = now()
        row["semantic_review_stage"] = "PARSED_NOT_ASSURANCE"
        private_json("independent-semantic-review.json", review.model_dump(mode="json"))
        row["semantic_review"] = {"inventory_fingerprint": review.inventory_fingerprint,
            "candidate_fingerprint": review.candidate_fingerprint, "components_fingerprint": review.components_fingerprint,
            "source_results": [{"source_ordinal": refs.get(item.source_ref), "complete_and_equivalent": item.complete_and_equivalent,
                "reason_sha256": sha256(item.reason.encode()).hexdigest()} for item in review.source_results]}
        row["failure_stage"] = "FINAL_DETERMINISTIC_SEMANTIC_VALIDATION"
        final = validate_projection_candidate(candidate, revision, ir, inventory, semantic_review=review)
        if any(binding.state == "UNRESOLVED" for binding in final):
            raise ValueError("OBLIGATION_PROJECTION_UNRESOLVED")
        row["deterministic_checks"].append({"stage": "POST_REVIEW", "status": "PASS", "binding_count": len(final),
            "state_counts": dict(Counter(str(binding.state) for binding in final))})
        row["runtime_consumer_admission"] = "NOT_EXECUTED; isolated candidate validator only, no Owner or Work admission"
        row.update(result="ISOLATED_FULFILLMENT_PLAN_QUALIFIED", semantic_review_stage="VALIDATED_NOT_ASSURANCE", failure_stage=None)
    except Exception as error:
        failure = provider_failure_observation(error)
        codes = re.findall(r"\bOBLIGATION_[A-Z0-9_]+\b", str(error))
        row.update(result="STOPPED", exception_type=type(error).__name__,
            failed_predicate=codes[0] if codes else machine(str(error), 120), provider_failure=failure)
        if hasattr(error, "errors"):
            row["schema_errors"] = [{"type": machine(item.get("type")), "location": list(item.get("loc", ())) }
                for item in error.errors(include_input=False, include_url=False, include_context=False)]
        if active is not None:
            active["ended_at_utc"] = now()
            if failure is not None:
                active["failure_observation"] = failure
                active["usage"] = failure["usage"]
                active["provider_status"] = failure["provider_failure"]["provider_status"] or "UNKNOWN"
            active["provider_last_observation"] = getattr(provider, "last_observation", None)
        if not execute:
            print(json.dumps({"preflight": "FAILED", "exception_type": type(error).__name__, "code": row["failed_predicate"]}))
            raise SystemExit(2)
    finally:
        if execute:
            row.update(ended_at_utc=now(), wall_seconds=time.monotonic()-clock,
                http_transmission_attempt_observations=sum(len(call["http_request_hooks"]) for call in row["calls"]),
                transport_recovery_stages=sum(stage["stage"] == "provider_transport_recovery" for call in row["calls"] for stage in call["stages"]),
                token_usage_boundary="Provider-reported numeric fields only; missing fields and visible JSON tokens UNKNOWN; unobserved transmissions may have UNKNOWN usage",
                runtime_or_assurance_pass=False, c3_status="PARTIAL")
            checkpoint()
    print(json.dumps({key: row.get(key) for key in ("result", "failure_stage", "failed_predicate", "logical_model_entries", "http_transmission_attempt_observations", "wall_seconds")}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-authorized-live", action="store_true")
    main(parser.parse_args().execute_authorized_live)
