"""Derive evidence-only controls; preserve the previous frozen validator path."""
from pathlib import Path
import ast
import hashlib
import json

HERE = Path(__file__).parent
OLD = HERE.parent / 'live-model-verification-1'
probe = (OLD / 'verify_live_model.py').read_text(encoding='utf-8')
controller = (OLD / 'run_authorized_verification.py').read_text(encoding='utf-8')
baseline = {'probe_sha256': hashlib.sha256(probe.encode()).hexdigest(),
    'controller_sha256': hashlib.sha256(controller.encode()).hexdigest()}

def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)

probe = probe.replace('from dataclasses import asdict', 'from dataclasses import asdict, replace')
probe = probe.replace('from spg.domain.model_runtime import ModelPurpose', 'from spg.domain.model_runtime import ModelPurpose, PurposeProfileRouter')
probe = probe.replace('live-model-result.json', 'reasoning-mode-result.json')
probe = probe.replace('c3-authorized-capacity-model-plan-v1', 'c3-authorized-reasoning-none-control-v1')
probe = probe.replace('Human 2026-10-10 approved the exact live-model-decision-package; one formation and conditional one review',
    'Human 2026-10-10 approved one isolation contrast: Formation none, conditional Review low, zero retries')
probe = replace_once(probe, '        factory = provider.runtime_factory',
    '        factory = provider.runtime_factory\n        preflight_operation = "formation"')
probe = replace_once(probe, '            profile = runtime.profile(ModelPurpose.STEERING_SEMANTIC)', '''            base_profile = runtime.profile(ModelPurpose.STEERING_SEMANTIC)
            assert base_profile.reasoning_effort == "low", "BASE_PROFILE_DRIFT"
            operation = active["operation"] if active is not None else preflight_operation
            profile = replace(base_profile, reasoning_effort="none" if operation == "formation" else "low")
            runtime.router = PurposeProfileRouter({ModelPurpose.STEERING_SEMANTIC: profile})''')
probe = probe.replace('"reasoning_effort": "low",\n                "timeout_seconds": 120',
    '"reasoning_effort": "none" if operation == "formation" else "low",\n                "timeout_seconds": 120')
probe = probe.replace('            row["profile"] = actual_profile',
    '            row.setdefault("profiles", {})[operation] = actual_profile')
probe = probe.replace('len(active["http_request_hooks"]) <= 2', 'len(active["http_request_hooks"]) <= 1')
probe = replace_once(probe, '''                if active["operation"] == "formation":
                    assert len(entity) == 54365 and sha256(entity).hexdigest() == "9e9e5ab4753c4e20115e721b2c933cd9db20a1c36a7744dd7e037073eea3041d", "FORMATION_REQUEST_DRIFT"''', '''                if active["operation"] == "formation":
                    low_payload = adapter._payload(profile=base_profile, instructions=kwargs["instructions"], input_text=kwargs["input_text"], output_schema=kwargs["output_schema"])
                    low_entity = httpx2.Request("POST", "https://api.deepseek.com/responses", json=low_payload).content
                    assert len(low_entity) == 54365 and sha256(low_entity).hexdigest() == "9e9e5ab4753c4e20115e721b2c933cd9db20a1c36a7744dd7e037073eea3041d", "BASE_FORMATION_REQUEST_DRIFT"
                    comparable = dict(payload)
                    comparable["reasoning"] = {"effort": "low"}
                    assert payload["reasoning"] == {"effort": "none"} and comparable == low_payload, "UNAUTHORIZED_PAYLOAD_DIFFERENCE"
                    active["request_contrast"] = {"status": "ONLY_REASONING_EFFORT_DIFFERS", "baseline_effort": "low", "actual_effort": "none", "baseline_body_sha256": sha256(low_entity).hexdigest(), "baseline_body_bytes": len(low_entity)}''')
probe = replace_once(probe, '''                    checkpoint()
                result = original_generate(**kwargs, on_stage=stage)''', '''                    checkpoint()
                    if name == "provider_transport_recovery":
                        active["transport_retry_blocked_before_replay"] = True
                        checkpoint()
                        raise RuntimeError("DIAGNOSTIC_TRANSPORT_RETRY_FORBIDDEN")
                result = original_generate(**kwargs, on_stage=stage)''')
probe = replace_once(probe, '''        local_runtime = runtime_factory()
        local_runtime.close()''', '''        for preflight_operation in ("formation", "semantic_review"):
            local_runtime = runtime_factory()
            local_runtime.close()''')
probe = probe.replace('"source_count": 26, "profile": row["profile"]', '"source_count": 26, "profiles": row["profiles"]')
probe = probe.replace('        "self_refine_calls": 0,', '        "retry_policy": "NO_LOGICAL_OR_TRANSPORT_RETRY",\n        "self_refine_calls": 0,')
probe = probe.replace('assert row["logical_model_entries"] <= 2, "LOGICAL_REQUEST_LIMIT"',
    'assert row["logical_model_entries"] == (1 if active["operation"] == "formation" else 2), "LOGICAL_REQUEST_ORDER_OR_LIMIT"')

controller = controller.replace('live-model-verification-1', 'reasoning-none-control-1')
controller = controller.replace('live-model-result.json', 'reasoning-mode-result.json')
controller = controller.replace("'watt-c3-capacity-' + mode", "'watt-c3-reasoning-none-' + mode")
controller = controller.replace('C3-authorized-capacity-plan', 'C3-authorized-reasoning-none-control')
controller = controller.replace('Human 2026-10-10 exact decision-package approval', 'Human 2026-10-10 exact reasoning-none contrast approval; no retry')
for name, value in (('verify_live_model.py', probe), ('run_authorized_verification.py', controller)):
    target = HERE / name
    assert not target.exists()
    ast.parse(value)
    target.write_bytes(value.encode('utf-8'))
print(json.dumps({'status': 'DERIVED_SYNTAX_PASS', 'baseline': baseline,
    'changes': ['Formation request-local profile none; Review original low', 'exact payload difference guard', 'stop before any transport replay'],
    'application_source_change': False}, sort_keys=True))
