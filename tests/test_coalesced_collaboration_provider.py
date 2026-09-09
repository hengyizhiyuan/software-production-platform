from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from threading import Event, Thread
from types import SimpleNamespace
from uuid import UUID

import pytest
from openai_codex import ApprovalMode, Sandbox

from spg.domain.conversation import (
    ConversationResponseCandidate,
    ConversationTurnIntent,
    StructuredCollaborationResult,
)
from spg.domain.interaction import (
    Interaction,
    InteractionActor,
    InteractionCondition,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InteractionRecord,
    InteractionSemanticCandidate,
)
from spg.providers.codex_interaction import CodexSdkWorkInteractionCapability


def _basis() -> InteractionInterpretationInput:
    now = datetime(2026, 9, 9, tzinfo=UTC)
    return InteractionInterpretationInput(
        interaction=Interaction(
            id=UUID(int=1), condition=InteractionCondition.OPEN,
            created_by="human", updated_by="human", created_at=now, updated_at=now,
        ),
        records=(InteractionRecord(
            id=UUID(int=2), interaction_id=UUID(int=1), sequence=1,
            actor=InteractionActor.HUMAN, source="human",
            content="Not an operation plan. I want a Web application system.",
            content_fingerprint="a" * 64, created_at=now,
        ),),
        basis_fingerprint="b" * 64,
    )


def _semantic() -> InteractionSemanticCandidate:
    return InteractionSemanticCandidate(
        interpreted_motive="Build an operations management Web application",
        desired_outcome="A Web system supporting Watt promotion",
        candidate_context=("Audience: individual developers and small teams",),
        candidate_constraints=("Build a Web application system",),
        current_requests=("Correct the system design",),
        collaboration=StructuredCollaborationResult(
            turn_intent=ConversationTurnIntent.CORRECTION,
            current_objective="Build a Web application system",
            response_language="English",
        ),
        provider_identity="test:semantic",
    )


def _semantics_payload() -> dict:
    payload = _semantic().model_dump(mode="json", exclude={"provider_identity", "model_identity"})
    payload["collaboration"] = {
        key: payload["collaboration"][key] for key in (
            "turn_intent", "direct_answer", "design_intent_frame",
            "recommended_next_action", "concise_basis",
            "detailed_explanation_requested", "response_language",
        )
    }
    return {**payload, "retained_prior_meaning_indexes": [],
            "reuse_prior_design_intent_frame": False}


def _envelope(wording: str, *, reversed_order=False, semantics=None) -> str:
    semantics = _semantics_payload() if semantics is None else semantics
    items = (("natural_response", wording), ("semantics", semantics))
    return json.dumps(dict(reversed(items) if reversed_order else items), ensure_ascii=True)


class _Turn:
    def __init__(self, payload, clock, *, chunks=None, gate=None, completed_at=40.0):
        self.id = "turn-" + str(id(self))
        self.payload = payload
        self.clock = clock
        self.chunks = chunks or ((2.0, payload),)
        self.gate = gate
        self.completed_at = completed_at

    def stream(self):
        for index, (at, text) in enumerate(self.chunks):
            self.clock[0] = at
            yield SimpleNamespace(
                method="item/agentMessage/delta", payload=SimpleNamespace(delta=text)
            )
            if index == 0 and self.gate is not None:
                if not self.gate.wait(5):
                    raise RuntimeError("Test did not release the semantic envelope")
        self.clock[0] = self.completed_at
        yield SimpleNamespace(
            method="item/completed",
            payload=SimpleNamespace(item=SimpleNamespace(type="agentMessage", text=self.payload)),
        )
        yield SimpleNamespace(
            method="turn/completed",
            payload=SimpleNamespace(turn=SimpleNamespace(status="completed", error=None)),
        )

    def interrupt(self):
        if self.gate is not None:
            self.gate.set()


class _Client:
    def __init__(self, turn):
        self.scripted_turn = turn
        self.id = "thread-" + str(id(self))
        self.thread_calls = []
        self.turn_calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def thread_start(self, **options):
        self.thread_calls.append(options)
        return self

    def turn(self, instruction, **options):
        self.turn_calls.append((instruction, options))
        return self.scripted_turn


class _Factory:
    def __init__(self, *clients):
        self.pending = iter(clients)
        self.calls = []

    def __call__(self):
        client = next(self.pending)
        self.calls.append(client)
        return client


def test_one_turn_streams_only_wording_before_semantic_envelope_is_complete(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("spg.providers.codex_interaction.monotonic", lambda: clock[0])
    wording = 'Understood: a Web application with a "lead inbox". 🚦'
    prefix = '{"natural_response":' + json.dumps(wording, ensure_ascii=True)
    suffix = ',"semantics":' + json.dumps(_semantics_payload()) + '}'
    release = Event()
    first_text = Event()
    client = _Client(_Turn(
        prefix + suffix, clock, chunks=((2.0, prefix), (40.0, suffix)), gate=release,
    ))
    factory = _Factory(client)
    capability = CodexSdkWorkInteractionCapability(
        repository_location=".", codex_factory=factory, model="same-model",
        reasoning_effort="low", conversation_reasoning_effort="low", timeout_seconds=5,
    )
    outcome = {}
    deltas = []

    def publish(delta):
        deltas.append(delta)
        first_text.set()

    def run():
        try:
            outcome["result"] = capability.interpret_stream(_basis(), on_response_delta=publish)
        except Exception as error:
            outcome["error"] = error

    worker = Thread(target=run, daemon=True)
    worker.start()
    try:
        assert first_text.wait(2), "The response field was held behind semantic completion"
        assert "".join(deltas) == wording
        assert outcome == {}  # Provisional wording does not return an admitted candidate.
        assert capability.last_pipeline_evidence is None
        assert worker.is_alive()
    finally:
        release.set()
        worker.join(timeout=5)
    assert not worker.is_alive()
    assert "error" not in outcome, outcome.get("error")
    assert outcome["result"].natural_response == wording
    assert outcome["result"].candidate_constraints == ("Build a Web application system",)
    assert len(factory.calls) == 1
    assert len(client.thread_calls) == len(client.turn_calls) == 1
    assert client.thread_calls[0]["ephemeral"] is True
    assert client.thread_calls[0]["sandbox"] is Sandbox.read_only
    options = client.turn_calls[0][1]
    assert options["approval_mode"] is ApprovalMode.deny_all
    assert options["effort"] == "low"
    assert list(options["output_schema"]["properties"]) == ["natural_response", "semantics"]
    evidence = capability.last_pipeline_evidence
    assert evidence.pipeline_mode == "coalesced_pre_work"
    assert evidence.provider_call_count == 1
    assert evidence.coalesced_thread_id == client.id
    assert evidence.coalesced_turn_id == client.scripted_turn.id
    assert evidence.semantic_thread_id is None
    assert evidence.conversation_thread_id is None
    assert evidence.semantic_seconds is None
    assert evidence.conversation_seconds is None
    assert evidence.first_response_delta_seconds == 2.0
    assert evidence.coalesced_seconds == 40.0


def test_invalid_later_semantics_rejects_candidate_and_clears_previous_success(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("spg.providers.codex_interaction.monotonic", lambda: clock[0])
    invalid = deepcopy(_semantics_payload())
    del invalid["candidate_constraints"]
    factory = _Factory(
        _Client(_Turn(_envelope("Ready."), clock)),
        _Client(_Turn(_envelope("Provisional response.", semantics=invalid), clock)),
    )
    capability = CodexSdkWorkInteractionCapability(
        repository_location=".", codex_factory=factory, model="same-model", timeout_seconds=5,
    )
    capability.interpret(_basis())
    assert capability.last_pipeline_evidence is not None
    deltas = []

    with pytest.raises(InteractionInvariantViolation):
        capability.interpret_stream(_basis(), on_response_delta=deltas.append)

    assert "".join(deltas) == "Provisional response."
    assert capability.last_pipeline_evidence is None
    assert capability.last_collaboration_result is None
    assert len(factory.calls) == 2  # One call per attempt, no permissive retry.


def test_reversed_envelope_order_still_streams_only_the_natural_response(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("spg.providers.codex_interaction.monotonic", lambda: clock[0])
    wording = 'Use the Web system; the audience is not automatically its operators.'
    payload = _envelope(wording, reversed_order=True)
    chunks = tuple((2.0, payload[index:index + 11]) for index in range(0, len(payload), 11))
    factory = _Factory(_Client(_Turn(payload, clock, chunks=chunks)))
    capability = CodexSdkWorkInteractionCapability(
        repository_location=".", codex_factory=factory, model="same-model", timeout_seconds=5,
    )
    deltas = []

    result = capability.interpret_stream(_basis(), on_response_delta=deltas.append)

    assert "".join(deltas) == result.natural_response == wording
    assert "candidate_constraints" not in "".join(deltas)
    assert capability.last_pipeline_evidence.provider_call_count == 1


@pytest.mark.parametrize("route", ("active_work", "different_models", "different_efforts", "opt_out"))
def test_governed_work_and_independent_configuration_keep_two_stages(monkeypatch, route):
    options = {"model": "semantic-model", "conversation_model": "semantic-model"}
    if route == "different_models":
        options["conversation_model"] = "expression-model"
    if route == "different_efforts":
        options.update(reasoning_effort="medium", conversation_reasoning_effort="low")
    if route == "opt_out":
        options["coalesce_pre_work"] = False
    capability = CodexSdkWorkInteractionCapability(repository_location=".", **options)
    basis = _basis()
    if route == "active_work":
        basis = basis.model_copy(update={"active_work_context": object()})
    calls = []
    semantic = _semantic()

    def interpret_semantics(_basis_value):
        calls.append("semantic")
        capability.semantic_capability.last_thread_id = "semantic-thread"
        capability.semantic_capability.last_turn_id = "semantic-turn"
        return semantic

    def compose(_basis_value, collaboration, *, current_semantics, on_response_delta):
        assert collaboration is semantic.collaboration
        assert current_semantics is semantic
        calls.append("conversation")
        capability.conversation_provider.last_thread_id = "conversation-thread"
        capability.conversation_provider.last_turn_id = "conversation-turn"
        return ConversationResponseCandidate(content="Ready.", provider_identity="test:conversation")

    def unexpected_coalesced(*_args, **_kwargs):
        pytest.fail("This route must retain independent semantic and expression stages")

    monkeypatch.setattr(capability.semantic_capability, "interpret_semantics", interpret_semantics)
    monkeypatch.setattr(capability.response_composer, "compose", compose)
    monkeypatch.setattr(capability, "_interpret_coalesced", unexpected_coalesced)
    result = capability.interpret(basis)

    assert result.natural_response == "Ready."
    assert calls == ["semantic", "conversation"]
    assert capability.last_pipeline_evidence.pipeline_mode == "staged"
    assert capability.last_pipeline_evidence.provider_call_count == 2


def test_controlled_stream_proves_serial_semantic_wait_is_removed(monkeypatch):
    # Synthetic clocks model identical serialization boundaries, not real-provider latency.
    clock = [0.0]
    monkeypatch.setattr("spg.providers.codex_interaction.monotonic", lambda: clock[0])
    wording = "Understood: a Web application system."
    factory = _Factory(
        _Client(_Turn(_semantic().model_dump_json(exclude={"provider_identity", "model_identity"}), clock,
                      chunks=((40.0, _semantic().model_dump_json(exclude={"provider_identity", "model_identity"})),))),
        _Client(_Turn(json.dumps({"natural_response": wording}), clock,
                      chunks=((42.0, json.dumps({"natural_response": wording})),), completed_at=45.0)),
    )
    staged = CodexSdkWorkInteractionCapability(
        repository_location=".", codex_factory=factory, model="same-model",
        coalesce_pre_work=False, timeout_seconds=5,
    )
    staged.interpret_stream(_basis(), on_response_delta=lambda _delta: None)
    staged_first_text = staged.last_pipeline_evidence.first_response_delta_seconds
    assert len(factory.calls) == 2
    clock[0] = 0.0
    prefix = '{"natural_response":' + json.dumps(wording)
    suffix = ',"semantics":' + json.dumps(_semantics_payload()) + '}'
    factory = _Factory(_Client(_Turn(
        prefix + suffix, clock, chunks=((2.0, prefix), (40.0, suffix)),
    )))
    coalesced = CodexSdkWorkInteractionCapability(
        repository_location=".", codex_factory=factory, model="same-model", timeout_seconds=5,
    )
    coalesced.interpret_stream(_basis(), on_response_delta=lambda _delta: None)

    assert len(factory.calls) == 1
    assert staged_first_text == 42.0
    assert coalesced.last_pipeline_evidence.first_response_delta_seconds == 2.0
    assert coalesced.last_pipeline_evidence.coalesced_seconds == 40.0


def test_coalesced_wire_contract_is_strict_through_nested_semantics():
    schema = CodexSdkWorkInteractionCapability.coalesced_output_schema()
    pending = [schema]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            if "properties" in node:
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)


def test_whitespace_only_wording_never_completes_successfully(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("spg.providers.codex_interaction.monotonic", lambda: clock[0])
    factory = _Factory(_Client(_Turn(_envelope("   "), clock)))
    capability = CodexSdkWorkInteractionCapability(
        repository_location=".", codex_factory=factory, model="same-model", timeout_seconds=5,
    )

    with pytest.raises(InteractionInvariantViolation, match="empty Human-facing response"):
        capability.interpret(_basis())

    assert capability.last_pipeline_evidence is None
    assert capability.last_collaboration_result is None


def _basis_with_prior_meanings():
    from spg.domain.conversation import ConversationContextMessage
    from spg.domain.interaction import (
        InteractionAssessment, InterpretationMeaning, InterpretationMeaningKind,
        WorkAdmissionReadiness, WorkAdmissionReadinessStatus,
    )

    basis = _basis()
    old = basis.records[0].model_copy(update={"content": "Build a system for small teams."})
    latest = old.model_copy(update={
        "id": UUID(int=4), "sequence": 2,
        "content": "The operators are our marketing team, not the promotion audience.",
    })
    prior = InteractionAssessment(
        id=UUID(int=3), interaction_id=basis.interaction.id,
        basis_fingerprint="c" * 64, basis_last_sequence=1,
        interpreted_motive="Build a system",
        desired_outcome="Support Watt promotion",
        candidate_context=("Old inferred operators: promotion audience",),
        candidate_constraints=(), current_requests=("Build a system",),
        unresolved_material_questions=(),
        meanings=(
            InterpretationMeaning(
                kind=InterpretationMeaningKind.REQUEST,
                statement="Build a system", source_record_ids=(old.id,),
                confidence=0.83, rationale="Exact unchanged historical rationale",
            ),
            InterpretationMeaning(
                kind=InterpretationMeaningKind.FACT,
                statement="Promotion audience will operate the system",
                source_record_ids=(old.id,), confidence=0.4,
                rationale="Old provisional interpretation to supersede",
            ),
        ),
        natural_response="Who will operate it?",
        readiness=WorkAdmissionReadiness(
            status=WorkAdmissionReadinessStatus.NOT_READY, profile="LONG_LIVED_STEERING",
            profile_version="v0", satisfied_requirements=(), missing_information=("Operators",),
            unresolved_material_questions=(), reasons=("Clarify the actual operators",),
            basis_fingerprint="c" * 64,
        ),
        provider_identity="old-provider", schema_version="wic-assessment-v3",
        created_at=old.created_at,
    )
    return basis.model_copy(update={
        "records": (old, latest), "prior_assessment": prior,
        "recent_conversation_messages": (
            ConversationContextMessage(actor="WATT", content=prior.natural_response),
            ConversationContextMessage(actor="HUMAN", content=latest.content),
        ),
    })


def _incremental_payload(basis):
    from spg.domain.interaction import InterpretationMeaning, InterpretationMeaningKind

    payload = _semantics_payload()
    payload["retained_prior_meaning_indexes"] = [0]
    payload["meanings"] = [InterpretationMeaning(
        kind=InterpretationMeaningKind.CORRECTION,
        statement="The marketing team operates the system",
        source_record_ids=(basis.records[-1].id,),
        confidence=0.98, rationale="Human explicitly corrects the operator",
    ).model_dump(mode="json")]
    payload["candidate_context"] = ["The marketing team operates the system"]
    return payload


def _run_observed_payload(monkeypatch, basis, payload):
    clock = [0.0]
    monkeypatch.setattr("spg.providers.codex_interaction.monotonic", lambda: clock[0])
    factory = _Factory(_Client(_Turn(_envelope("Use a team content inbox.", semantics=payload), clock)))
    capability = CodexSdkWorkInteractionCapability(
        repository_location=".", codex_factory=factory, timeout_seconds=5,
    )
    stages = []
    candidate = capability.interpret_stream_observed(
        basis, on_response_delta=lambda _delta: None,
        on_pipeline_stage=lambda name: stages.append(name),
    )
    return candidate, capability, stages


def test_incremental_meanings_preserve_retained_provenance_and_apply_correction(monkeypatch):
    basis = _basis_with_prior_meanings()
    payload = _incremental_payload(basis)

    candidate, capability, stages = _run_observed_payload(monkeypatch, basis, payload)

    assert candidate.meanings[0] is basis.prior_assessment.meanings[0]
    assert candidate.meanings[0].rationale == "Exact unchanged historical rationale"
    assert len(candidate.meanings) == 2
    assert candidate.meanings[-1].source_record_ids == (basis.records[-1].id,)
    assert candidate.candidate_context == ("The marketing team operates the system",)
    assert basis.prior_assessment.meanings[1] not in candidate.meanings
    assert basis.prior_assessment.candidate_context == ("Old inferred operators: promotion audience",)
    assert capability.last_pipeline_evidence.retained_prior_meaning_count == 1
    assert capability.last_pipeline_evidence.new_meaning_count == 1
    assert stages[-1] == "payload_validated"


@pytest.mark.parametrize("indexes", ([0, 0], [-1], [2], [True], ["0"]))
def test_invalid_prior_meaning_indexes_never_validate_a_payload(monkeypatch, indexes):
    basis = _basis_with_prior_meanings()
    payload = _incremental_payload(basis)
    payload["retained_prior_meaning_indexes"] = indexes
    clock = [0.0]
    monkeypatch.setattr("spg.providers.codex_interaction.monotonic", lambda: clock[0])
    capability = CodexSdkWorkInteractionCapability(
        repository_location=".",
        codex_factory=_Factory(_Client(_Turn(_envelope("Provisional.", semantics=payload), clock))),
        timeout_seconds=5,
    )
    stages = []
    with pytest.raises(InteractionInvariantViolation):
        capability.interpret_stream_observed(
            basis, on_response_delta=lambda _delta: None, on_pipeline_stage=stages.append
        )
    assert "payload_validation_started" in stages
    assert "payload_validated" not in stages
    assert capability.last_pipeline_evidence is None
    assert capability.last_collaboration_result is None


def test_reuse_requires_prior_assessment_and_all_meaning_sources_in_exact_basis(monkeypatch):
    original = _basis_with_prior_meanings()
    payload = _incremental_payload(original)
    for basis in (
        original.model_copy(update={"prior_assessment": None}),
        original.model_copy(update={"records": (original.records[-1],)}),
    ):
        with pytest.raises(InteractionInvariantViolation):
            _run_observed_payload(monkeypatch, basis, payload)
    payload["retained_prior_meaning_indexes"] = []
    payload["meanings"][0]["source_record_ids"] = [str(UUID(int=999))]
    with pytest.raises(InteractionInvariantViolation, match="outside the exact basis"):
        _run_observed_payload(monkeypatch, original, payload)


def test_coalesced_context_compacts_reuse_metadata_without_dropping_source_facts():
    from spg.providers.codex_interaction import _compact_interaction_basis

    basis = _basis_with_prior_meanings()
    before = basis.model_dump(mode="json")

    compact = _compact_interaction_basis(basis, coalesced=True)
    instruction = CodexSdkWorkInteractionCapability.coalesced_instruction(basis)

    assert basis.model_dump(mode="json") == before
    assert [record["id"] for record in compact["records"]] == [record["id"] for record in before["records"]]
    assert [record["content"] for record in compact["records"]] == [record["content"] for record in before["records"]]
    assert compact["basis_fingerprint"] == before["basis_fingerprint"]
    assert compact["prior_assessment"]["candidate_context"] == before["prior_assessment"]["candidate_context"]
    assert compact["prior_assessment"]["meanings"][0] == {
        "index": 0, "kind": "REQUEST", "statement": "Build a system",
        "source_record_ids": [str(basis.records[0].id)],
    }
    assert "readiness" not in compact["prior_assessment"]
    assert "natural_response" not in compact["prior_assessment"]
    assert "Available Design Schemas" not in instruction
    assert "retained_prior_meaning_indexes" in instruction
    without_dialogue = basis.model_copy(update={"recent_conversation_messages": ()})
    fallback = _compact_interaction_basis(without_dialogue, coalesced=True)
    assert fallback["prior_assessment"]["natural_response"] == basis.prior_assessment.natural_response


def test_response_closure_observation_waits_for_unescaped_closing_quote(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("spg.providers.codex_interaction.monotonic", lambda: clock[0])
    wording = 'Consider "a" first.'
    encoded = json.dumps(wording)
    split = encoded.index(chr(92) + chr(34)) + 2
    first = '{"natural_response":' + encoded[:split]
    second = encoded[split:]
    tail = ',"semantics":' + json.dumps(_semantics_payload()) + '}'
    client = _Client(_Turn(
        first + second + tail, clock,
        chunks=((1.0, first), (2.0, second), (20.0, tail)), completed_at=30.0,
    ))
    capability = CodexSdkWorkInteractionCapability(
        repository_location=".", codex_factory=_Factory(client), timeout_seconds=5
    )
    stages = []
    result = capability.interpret_stream_observed(
        _basis(), on_response_delta=lambda _delta: None,
        on_pipeline_stage=lambda name: stages.append((name, clock[0])),
    )
    assert result.natural_response == wording
    observed = dict(stages)
    assert observed["natural_response_completed"] == 2.0
    assert observed["semantic_envelope_completed"] == 30.0
    assert observed["payload_validated"] == 30.0
    assert len(stages) == len(observed)
    assert capability.last_pipeline_evidence.coalesced_output_characters == len(client.scripted_turn.payload)


def test_observed_method_preserves_custom_stream_override():
    calls = []

    class ExistingCapability(CodexSdkWorkInteractionCapability):
        def interpret_stream(self, basis, *, on_response_delta):
            calls.append("custom-stream")
            return "custom-result"

    capability = ExistingCapability(repository_location=".")
    result = capability.interpret_stream_observed(
        _basis(), on_response_delta=lambda _delta: None,
        on_pipeline_stage=lambda _name: pytest.fail("Unobserved custom stage must remain unknown"),
    )
    assert result == "custom-result"
    assert calls == ["custom-stream"]



def _prior_frame():
    from spg.domain.design_intent import DesignIntentFrame

    return DesignIntentFrame(
        design_subject="Watt promotion Web platform", object_type="PRODUCT_SYSTEM",
        business_context="The marketing team promotes Watt to small teams",
        desired_outcome="A shared content and campaign workflow", scope_level="product",
        collaboration_mode="design", candidate_assumptions=("The marketing team operates it",),
        ambiguities=("Publishing integrations are provisional",), confidence=0.86,
    )


def _basis_with_prior_frame():
    from spg.domain.conversation import ConversationContextMessage

    basis = _basis_with_prior_meanings()
    latest = basis.records[-1].model_copy(update={"content": "Continue with the proposed content inbox."})
    prior = basis.prior_assessment.model_copy(update={"design_intent_frame": _prior_frame()})
    return basis.model_copy(update={
        "prior_assessment": prior, "records": (basis.records[0], latest),
        "recent_conversation_messages": (
            ConversationContextMessage(actor="WATT", content="Start with a shared content inbox."),
            ConversationContextMessage(actor="HUMAN", content=latest.content),
        ),
    })


def _frame_reuse_payload():
    payload = _semantics_payload()
    payload["reuse_prior_design_intent_frame"] = True
    payload["collaboration"]["turn_intent"] = "CONTINUE_CURRENT_WORK"
    payload["collaboration"]["design_intent_frame"] = None
    return payload


def test_unchanged_frame_reuse_expands_exact_prior_value_before_validation(monkeypatch):
    basis = _basis_with_prior_frame()
    original = basis.model_dump(mode="json")

    candidate, capability, stages = _run_observed_payload(monkeypatch, basis, _frame_reuse_payload())

    assert candidate.design_intent_frame is basis.prior_assessment.design_intent_frame
    assert capability.last_collaboration_result.design_intent_frame is candidate.design_intent_frame
    assert candidate.model_dump(mode="json")["design_intent_frame"] == original["prior_assessment"]["design_intent_frame"]
    assert basis.model_dump(mode="json") == original
    assert capability.last_pipeline_evidence.reused_prior_design_intent_frame is True
    assert stages[-1] == "payload_validated"


@pytest.mark.parametrize("case", (
    "absent_prior", "absent_prior_frame", "replacement_and_reuse", "correction_intent",
    "new_correction_meaning", "implicit_null_reuse", "missing_flag", "string_flag", "integer_flag",
))
def test_invalid_frame_reuse_never_becomes_a_validated_candidate(monkeypatch, case):
    basis = _basis_with_prior_frame()
    payload = _frame_reuse_payload()
    if case == "absent_prior":
        basis = basis.model_copy(update={"prior_assessment": None})
    elif case == "absent_prior_frame":
        basis = _basis_with_prior_meanings()
    elif case == "replacement_and_reuse":
        payload["collaboration"]["design_intent_frame"] = _prior_frame().model_dump(mode="json")
    elif case == "correction_intent":
        payload["collaboration"]["turn_intent"] = "CORRECTION"
    elif case == "new_correction_meaning":
        payload["meanings"] = _incremental_payload(basis)["meanings"]
    elif case == "implicit_null_reuse":
        payload["reuse_prior_design_intent_frame"] = False
        payload["collaboration"]["turn_intent"] = "CORRECTION"
    elif case == "missing_flag":
        del payload["reuse_prior_design_intent_frame"]
    elif case == "string_flag":
        payload["reuse_prior_design_intent_frame"] = "true"
    else:
        payload["reuse_prior_design_intent_frame"] = 1
    clock = [0.0]
    monkeypatch.setattr("spg.providers.codex_interaction.monotonic", lambda: clock[0])
    capability = CodexSdkWorkInteractionCapability(
        repository_location=".", timeout_seconds=5,
        codex_factory=_Factory(_Client(_Turn(_envelope("Provisional answer.", semantics=payload), clock))),
    )
    stages = []

    with pytest.raises(InteractionInvariantViolation):
        capability.interpret_stream_observed(
            basis, on_response_delta=lambda _text: None, on_pipeline_stage=stages.append
        )

    assert "payload_validation_started" in stages
    assert "payload_validated" not in stages
    assert capability.last_pipeline_evidence is None
    assert capability.last_collaboration_result is None


@pytest.mark.parametrize("has_prior", (False, True))
def test_new_or_corrected_frame_is_complete_and_never_merged_with_prior(monkeypatch, has_prior):
    from spg.domain.design_intent import DesignObjectType

    basis = _basis_with_prior_frame() if has_prior else _basis()
    payload = _semantics_payload()
    replacement = _prior_frame().model_copy(update={
        "design_subject": "A scheduling feature in the existing Web platform",
        "object_type": DesignObjectType.FEATURE, "candidate_assumptions": (), "ambiguities": (),
    })
    payload["collaboration"]["design_intent_frame"] = replacement.model_dump(mode="json")

    candidate, capability, _stages = _run_observed_payload(monkeypatch, basis, payload)

    assert candidate.design_intent_frame.model_dump() == replacement.model_dump()
    assert candidate.design_intent_frame.candidate_assumptions == ()
    assert capability.last_pipeline_evidence.reused_prior_design_intent_frame is False
    if has_prior:
        assert basis.prior_assessment.design_intent_frame.candidate_assumptions
    del payload["collaboration"]["design_intent_frame"]["business_context"]
    with pytest.raises(InteractionInvariantViolation, match="invalid structured result"):
        _run_observed_payload(monkeypatch, basis, payload)


def test_frame_reuse_is_strict_coalesced_wire_only_and_active_work_prompt_is_retained():
    from spg.providers.codex_interaction import CodexSdkInteractionSemanticCapability

    schema = CodexSdkWorkInteractionCapability.coalesced_output_schema()
    semantics = schema["$defs"]["_CoalescedSemanticProviderPayload"]
    assert "reuse_prior_design_intent_frame" in semantics["required"]
    assert semantics["properties"]["reuse_prior_design_intent_frame"]["type"] == "boolean"
    assert "reuse_prior_design_intent_frame" not in CodexSdkInteractionSemanticCapability.output_schema()["properties"]
    basis = _basis()
    staged = CodexSdkInteractionSemanticCapability.instruction(basis)
    coalesced = CodexSdkWorkInteractionCapability.coalesced_instruction(basis)
    assert "injecting input into an active cycle" in staged
    assert "injecting input into an active cycle" not in coalesced
    assert "same-Motive continuation" not in coalesced
    assert "reuse_prior_design_intent_frame" in coalesced
    for invariant in (
        "exact persisted basis", "Human decisions", "source_record_ids in the basis",
        "not automatically", "only source_record_ids", "creates no Work",
    ):
        assert invariant in coalesced


def test_compact_handoff_preserves_explicit_answers_and_current_semantics(monkeypatch):
    payload = _semantics_payload()
    payload["collaboration"].update(
        turn_intent="DIRECT_QUESTION", direct_answer="No document has been saved.",
    )
    candidate, capability, _ = _run_observed_payload(monkeypatch, _basis(), payload)
    handoff = capability.last_collaboration_result
    assert handoff.direct_answer == "No document has been saved."
    assert handoff.known_relevant_facts == candidate.candidate_context
    assert handoff.current_objective == candidate.desired_outcome
    assert capability.last_pipeline_evidence.pipeline_reason == "native_pre_work_shared_configuration"
    payload["collaboration"]["direct_answer"] = None
    with pytest.raises(InteractionInvariantViolation, match="invalid structured result"):
        _run_observed_payload(monkeypatch, _basis(), payload)


def test_coalesced_handoff_excludes_duplicate_expression_context_only():
    from spg.providers.codex_interaction import CodexSdkInteractionSemanticCapability

    coalesced = CodexSdkWorkInteractionCapability.coalesced_output_schema()
    staged = CodexSdkInteractionSemanticCapability.output_schema()
    compact_keys = set(coalesced["$defs"]["_CoalescedCollaborationProviderPayload"]["properties"])
    staged_keys = set(staged["$defs"]["_StructuredCollaborationProviderPayload"]["properties"])
    assert compact_keys == {
        "turn_intent", "direct_answer", "design_intent_frame", "recommended_next_action",
        "concise_basis", "detailed_explanation_requested", "response_language",
    }
    assert compact_keys < staged_keys
    assert {"known_relevant_facts", "current_objective", "alternatives", "policy_hints"} <= staged_keys - compact_keys


@pytest.mark.parametrize("options,reason", (
    ({}, "native_pre_work_shared_configuration"),
    ({"coalesce_pre_work": False}, "explicit_opt_out"),
    ({"conversation_model": "other"}, "models_differ"),
    ({"reasoning_effort": "low"}, "reasoning_efforts_differ"),
    ({"reasoning_effort": "low", "conversation_reasoning_effort": "low"},
     "native_pre_work_shared_configuration"),
))
def test_effective_pipeline_selection_can_be_inspected_without_provider_calls(options, reason):
    capability = CodexSdkWorkInteractionCapability(repository_location=".", model="same", **options)
    mode, selected_reason = capability.pipeline_selection(_basis())
    assert selected_reason == reason
    assert mode == ("coalesced_pre_work" if reason.startswith("native_") else "staged")
    assert capability.last_pipeline_evidence is None
