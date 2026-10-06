"""Optional semantic judgment through the existing model runtime, never an oracle waiver."""
import json
from spg.domain.model_runtime import (ModelPurpose, ModelProvider, ModelProfile,
    ModelProviderRegistry, PurposeProfileRouter, WattModelRuntime)
from spg.infrastructure.model_runtime import DeepSeekResponsesModelAdapter
from spg.evaluation.contracts import Evaluation, Evaluator, QualityError


def evaluate(settings, *, case_run_id, case_definition, observed_results, model_runtime=None):
    if "FRESH_HOLDOUT" in case_definition["cohorts"]:
        raise QualityError("HOLDOUT_CANNOT_ENTER_OPTIMIZATION")
    owned = model_runtime is None
    if owned:
        if not settings.deepseek_api_key:
            raise QualityError("QUALITY_EVALUATOR_CREDENTIAL_REQUIRED")
        registry = ModelProviderRegistry()
        registry.register(DeepSeekResponsesModelAdapter(api_key=lambda: settings.deepseek_api_key.get_secret_value(),
            base_url=settings.deepseek_base_url))
        profile = ModelProfile(purpose=ModelPurpose.QUALITY_EVALUATION,
            provider=ModelProvider.DEEPSEEK, model=settings.native_executor_inference_model or "deepseek-flash",
            reasoning_effort="low", timeout_seconds=60, max_output_tokens=800)
        model_runtime = WattModelRuntime(registry, PurposeProfileRouter({ModelPurpose.QUALITY_EVALUATION: profile}))
    try:
        result = model_runtime.generate(purpose=ModelPurpose.QUALITY_EVALUATION,
            instructions="Give a bounded semantic quality opinion about the observed qualification. "
                "Do not claim unobserved behavior. Never overrule deterministic failure. Return JSON only. "
                "This opinion cannot authorize production, change policy or accept a Candidate.",
            input_text=json.dumps({"motive": case_definition["motive"],
                "invariants": case_definition["invariants"], "evaluations": observed_results}, ensure_ascii=False)[:14000],
            output_schema={"type": "object", "additionalProperties": False,
                "properties": {"outcome": {"type": "string", "enum": ["PASS", "FAIL", "UNKNOWN"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "rationale": {"type": "string"}}, "required": ["outcome", "confidence", "rationale"]})
        obj = json.loads(result.output_text)
        if obj.get("outcome") not in {"PASS", "FAIL", "UNKNOWN"} or not 0 <= obj.get("confidence", -1) <= 1:
            raise QualityError("QUALITY_EVALUATOR_RESULT_INVALID")
        return Evaluation(evaluator=Evaluator.LLM, outcome=obj["outcome"],
            evidence_refs=("quality:case-run:" + str(case_run_id),), evaluator_version="semantic-quality-opinion-v1",
            details={"model": result.effective_model or result.requested_model,
                "provider": result.provider.value, "provider_request_id": result.request_id,
                "confidence": obj["confidence"], "rationale": str(obj.get("rationale", ""))[:2000],
                "objective_override": False})
    finally:
        if owned:
            model_runtime.close()
