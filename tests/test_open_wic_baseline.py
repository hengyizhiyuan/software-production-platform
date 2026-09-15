from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from spg.application.bootstrap import Application
from spg.application.interaction import UnavailableWorkInteractionCapability
from spg.config import Settings
from spg.domain.interaction import (
    InteractionAssessmentCandidate,
    InteractionInterpretationInput,
)
from spg.evaluation.open_wic_baseline import (
    ProviderAttribution,
    load_corpus,
    replay_corpus,
)


CORPUS = Path("benchmarks/open_wic/corpus-v1.json")


@dataclass(frozen=True)
class _Evidence:
    provider_call_count: int = 1
    pipeline_mode: str = "fixture"
    coalesced_usage: dict[str, int] | None = None


class _Capability:
    def __init__(self) -> None:
        self.calls = 0
        self.last_pipeline_evidence = None

    def interpret_stream_observed(
        self, basis: InteractionInterpretationInput, *, on_response_delta, on_pipeline_stage
    ) -> InteractionAssessmentCandidate:
        self.calls += 1
        on_pipeline_stage("provider_request_sent")
        response = "我先基于当前信息推进。需要时我们再校准。"
        on_response_delta(response)
        self.last_pipeline_evidence = _Evidence(
            coalesced_usage={"input_tokens": 10, "output_tokens": 8, "total_tokens": 18}
        )
        latest = basis.records[-1]
        return InteractionAssessmentCandidate(
            interpreted_motive=latest.content,
            desired_outcome="形成可验证结果",
            current_requests=(latest.content,),
            supporting_references=latest.supporting_references,
            natural_response=response,
            provider_identity="fixture",
            model_identity="fixture-model",
        )


class _FailingCapability:
    def interpret(self, _basis: InteractionInterpretationInput):
        raise RuntimeError("bounded fixture failure")


def _attribution() -> ProviderAttribution:
    return ProviderAttribution(
        provider_adapter="fixture",
        semantic_model="fixture-model",
        semantic_reasoning_effort="low",
        conversation_model="fixture-model",
        conversation_reasoning_effort="low",
        coalesce_pre_work=True,
        wic_schema_version="wic-assessment-v3",
        code_revision="a" * 40,
        source_fingerprint="b" * 64,
    )


def test_frozen_corpus_loads_with_required_coverage_and_stable_digest() -> None:
    first, first_digest = load_corpus(CORPUS)
    second, second_digest = load_corpus(CORPUS)

    assert len(first.cases) == 8
    assert {case.case_id for case in first.cases} == {
        "OW-A", "OW-B", "OW-C", "OW-D", "OW-E", "OW-F", "OW-G", "OW-H"
    }
    assert first == second
    assert first_digest == second_digest


def test_replay_preserves_provenance_and_separates_raw_from_reference() -> None:
    corpus, digest = load_corpus(CORPUS)
    report = replay_corpus(corpus, digest, _Capability(), _attribution())

    assert report["corpus_digest"] == digest
    assert report["provider_attribution"]["code_revision"] == "a" * 40
    assert report["provider_attribution"]["source_fingerprint"] == "b" * 64
    assert report["summary"]["captured_count"] == 8
    first = report["cases"][0]
    assert "reference_intent" in first
    assert "reference_intent" not in first["raw_turn_outputs"][0]
    assert first["semantic_adjudication"] is None
    assert first["raw_turn_outputs"][0]["candidate"]["provider_identity"] == "fixture"


def test_replay_serializes_metrics_and_cannot_mutate_product_state(tmp_path: Path) -> None:
    corpus, digest = load_corpus(CORPUS)
    report = replay_corpus(corpus, digest, _Capability(), _attribution())
    output = tmp_path / "result.json"
    output.write_text(__import__("json").dumps(report), encoding="utf-8")
    restored = __import__("json").loads(output.read_text(encoding="utf-8"))

    mutation = restored["cases"][0]["mutation_boundary"]
    assert mutation == {
        "production_mutation_attempts": 0,
        "work_or_assessment_admissions": 0,
        "database_dependency_present": False,
    }
    metrics = restored["cases"][0]["raw_turn_outputs"][0]["metrics"]
    assert metrics["provider_call_count"] == 1
    assert metrics["usage"]["total_tokens"] == 18
    assert metrics["ttfms_boundary"].startswith("provider_stream")


def test_failure_is_retained_without_retry() -> None:
    corpus, digest = load_corpus(CORPUS)
    single = corpus.model_copy(update={"cases": (corpus.cases[0],)})
    capability = _FailingCapability()
    report = replay_corpus(single, digest, capability, _attribution())

    assert report["summary"]["failed_count"] == 1
    assert report["cases"][0]["status"] == "FAILED"
    assert report["cases"][0]["failure"]["type"] == "RuntimeError"
    assert len(report["cases"][0]["raw_turn_outputs"]) == 1


def test_current_interaction_composition_uses_extracted_capability_seam(monkeypatch) -> None:
    expected = UnavailableWorkInteractionCapability()
    monkeypatch.setattr(Application, "interaction_capability", lambda _self: expected)
    app = Application(Settings(_env_file=None))
    database = object()

    service = app.interaction(database=database)  # type: ignore[arg-type]

    assert service.database is database
    assert service.capability is expected
