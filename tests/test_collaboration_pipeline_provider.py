from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from openai_codex import ApprovalMode, Sandbox

from spg.domain.conversation import StructuredCollaborationResult, ConversationTurnIntent
from spg.domain.interaction import (
    Interaction,
    InteractionActor,
    InteractionCondition,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InteractionRecord,
    InteractionSemanticCandidate,
)
from spg.providers.codex_interaction import (
    CodexSdkInteractionSemanticCapability,
    CodexSdkWorkInteractionCapability,
    _compact_interaction_basis,
)


def _basis(record_count: int = 1) -> InteractionInterpretationInput:
    now = datetime(2026, 9, 9, tzinfo=UTC)
    identity = UUID(int=1)
    return InteractionInterpretationInput(
        interaction=Interaction(
            id=identity,
            condition=InteractionCondition.OPEN,
            created_by="human",
            updated_by="human",
            created_at=now,
            updated_at=now,
        ),
        records=tuple(
            InteractionRecord(
                id=UUID(int=index + 2),
                interaction_id=identity,
                sequence=index + 1,
                actor=InteractionActor.HUMAN,
                source="human",
                content=(
                    "Build a Web application, not an operations plan."
                    if index == 0 else f"Preserve explicit constraint {index}."
                ),
                content_fingerprint="c" * 64,
                supporting_references=(f"record-reference:{index}",),
                created_at=now,
            )
            for index in range(record_count)
        ),
        basis_fingerprint="a" * 64,
    )


def _semantic_payload() -> str:
    semantic = InteractionSemanticCandidate(
        interpreted_motive="Build an operations management Web application",
        desired_outcome="An agreed product design",
        candidate_context=("The audience is individual developers and small teams",),
        candidate_constraints=("Web application",),
        current_requests=("Explain the product scope",),
        collaboration=StructuredCollaborationResult(
            turn_intent=ConversationTurnIntent.NEW_GOAL,
            current_objective="Design the operations application",
            response_language="English",
        ),
        provider_identity="test",
    )
    return semantic.model_dump_json(exclude={"provider_identity", "model_identity"})


class _Turn:
    def __init__(self, payload: str, identity: str) -> None:
        self.payload = payload
        self.id = identity

    def stream(self):
        for offset in range(0, len(self.payload), 13):
            yield SimpleNamespace(
                method="item/agentMessage/delta",
                payload=SimpleNamespace(delta=self.payload[offset : offset + 13]),
            )
        yield SimpleNamespace(
            method="item/completed",
            payload=SimpleNamespace(
                item=SimpleNamespace(type="agentMessage", text=self.payload)
            ),
        )
        yield SimpleNamespace(
            method="turn/completed",
            payload=SimpleNamespace(
                turn=SimpleNamespace(status="completed", error=None)
            ),
        )


class _Thread:
    def __init__(self, owner) -> None:
        self.owner = owner
        self.id = f"thread-{owner.index}"

    def turn(self, instruction, **kwargs):
        self.owner.instruction = instruction
        self.owner.turn_options = kwargs
        return _Turn(self.owner.payload, f"turn-{self.owner.index}")


class _Codex:
    def __init__(self, payload: str, index: int) -> None:
        self.payload = payload
        self.index = index
        self.instruction = None
        self.turn_options = None
        self.thread_options = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def thread_start(self, **kwargs):
        self.thread_options = kwargs
        return _Thread(self)


def test_compact_transport_preserves_all_source_evidence_and_exact_basis() -> None:
    basis = _basis(40)
    original = basis.model_dump(mode="json")

    compact = _compact_interaction_basis(basis)

    assert basis.model_dump(mode="json") == original
    assert compact["basis_fingerprint"] == original["basis_fingerprint"]
    assert len(compact["records"]) == 40
    for original_record, record in zip(original["records"], compact["records"], strict=True):
        for field in ("id", "sequence", "actor", "source", "content", "supporting_references", "work_focus_id"):
            assert record[field] == original_record[field]
        assert "content_fingerprint" not in record
        assert "interaction_id" not in record
        assert "created_at" not in record
    assert len(json.dumps(compact)) < len(json.dumps(original)) * 0.75
    instruction = CodexSdkInteractionSemanticCapability.instruction(basis)
    assert "first_focus" not in instruction
    assert all(record.content in instruction for record in basis.records)


@pytest.mark.parametrize(
    ("semantic_effort", "conversation_effort"),
    ((None, None), ("medium", "low")),
)
def test_two_stage_pipeline_forwards_effort_and_measures_only_human_deltas(
    monkeypatch, semantic_effort: str | None, conversation_effort: str | None
) -> None:
    wording = "Let's define the Web application's first useful workflow."
    clients = [
        _Codex(_semantic_payload(), 1),
        _Codex(json.dumps({"natural_response": wording}), 2),
    ]
    pending = iter(clients)
    capability = CodexSdkWorkInteractionCapability(
        repository_location=".", coalesce_pre_work=False,
        codex_factory=lambda: next(pending),
        model="semantic-model",
        conversation_model="expression-model",
        reasoning_effort=semantic_effort,
        conversation_reasoning_effort=conversation_effort,
        timeout_seconds=2,
    )
    times = iter((10.0, 14.0, 16.0, 18.0))
    monkeypatch.setattr("spg.providers.codex_interaction.monotonic", lambda: next(times))
    deltas = []

    result = capability.interpret_stream(_basis(), on_response_delta=deltas.append)

    assert result.natural_response == wording
    assert "".join(deltas) == wording
    assert len(clients) == 2
    for client, effort, model in zip(
        clients,
        (semantic_effort, conversation_effort),
        ("semantic-model", "expression-model"),
        strict=True,
    ):
        assert client.thread_options["ephemeral"] is True
        assert client.thread_options["sandbox"] is Sandbox.read_only
        assert client.turn_options["approval_mode"] is ApprovalMode.deny_all
        assert client.turn_options["effort"] == effort
        assert client.turn_options["model"] == model
    evidence = capability.last_pipeline_evidence
    assert evidence is not None
    assert evidence.semantic_seconds == 4.0
    assert evidence.conversation_seconds == 4.0
    assert evidence.first_response_delta_seconds == 6.0
    assert evidence.semantic_prompt_characters == len(clients[0].instruction)
    assert evidence.conversation_prompt_characters == len(clients[1].instruction)
    assert evidence.semantic_reasoning_effort == semantic_effort
    assert evidence.conversation_reasoning_effort == conversation_effort
    assert evidence.semantic_model == "semantic-model"
    assert evidence.conversation_model == "expression-model"
    assert '"candidate_constraints":["Web application"]' in clients[1].instruction
    assert '"current_requests":["Explain the product scope"]' in clients[1].instruction


def test_failed_new_provider_request_does_not_retain_previous_success_evidence() -> None:
    payloads = iter(
        (
            _Codex(_semantic_payload(), 1),
            _Codex('{"natural_response":"Ready."}', 2),
            _Codex("not valid JSON", 3),
        )
    )
    capability = CodexSdkWorkInteractionCapability(
        repository_location=".", coalesce_pre_work=False, codex_factory=lambda: next(payloads), timeout_seconds=2
    )
    capability.interpret(_basis())
    assert capability.last_pipeline_evidence is not None

    with pytest.raises(InteractionInvariantViolation, match="invalid structured result"):
        capability.interpret(_basis())

    assert capability.last_pipeline_evidence is None
    assert capability.last_collaboration_result is None
    assert capability.semantic_capability.last_thread_id is None


def test_transport_omits_prior_provider_metadata_without_rewriting_interpretation() -> None:
    payload = _basis().model_dump(mode="json")
    payload["prior_assessment"] = {
        "id": "prior-assessment",
        "basis_fingerprint": "b" * 64,
        "natural_response": "Is the object a Web application?",
        "candidate_constraints": ["Do not lose the original constraint"],
        "provider_identity": "provider-audit-only",
        "model_identity": "model-audit-only",
        "schema_version": "version-audit-only",
        "created_at": "timestamp-audit-only",
    }
    original = deepcopy(payload)
    basis = SimpleNamespace(model_dump=lambda **_kwargs: deepcopy(payload))

    compact = _compact_interaction_basis(basis)

    assert payload == original
    assert compact["prior_assessment"]["candidate_constraints"] == ["Do not lose the original constraint"]
    assert compact["prior_assessment"]["natural_response"] == original["prior_assessment"]["natural_response"]
    assert compact["prior_assessment"]["basis_fingerprint"] == "b" * 64
    assert "provider_identity" not in compact["prior_assessment"]



def test_pipeline_first_response_timing_ignores_whitespace_deltas(monkeypatch) -> None:
    clock = [0.0]
    monkeypatch.setattr("spg.providers.codex_interaction.monotonic", lambda: clock[0])
    capability = CodexSdkWorkInteractionCapability(repository_location=".", coalesce_pre_work=False)
    semantic = InteractionSemanticCandidate(
        collaboration=StructuredCollaborationResult(
            turn_intent=ConversationTurnIntent.CONTEXT_ADDITION,
            response_language="English",
        ),
        provider_identity="test:semantic",
    )

    def interpret_semantics(_basis):
        clock[0] = 5.0
        return semantic

    def compose(_basis, _collaboration, *, current_semantics, on_response_delta):
        from spg.domain.conversation import ConversationResponseCandidate

        assert current_semantics is semantic
        on_response_delta("   ")
        clock[0] = 25.0
        on_response_delta("Ready.")
        clock[0] = 30.0
        return ConversationResponseCandidate(content="Ready.", provider_identity="test:wording")

    capability.semantic_capability = SimpleNamespace(
        interpret_semantics=interpret_semantics,
        last_thread_id="semantic-thread",
        last_turn_id="semantic-turn",
    )
    capability.conversation_provider = SimpleNamespace(
        last_thread_id="conversation-thread", last_turn_id="conversation-turn"
    )
    capability.response_composer = SimpleNamespace(compose=compose)
    deltas = []

    capability.interpret_stream(_basis(), on_response_delta=deltas.append)

    assert deltas == ["   ", "Ready."]
    assert capability.last_pipeline_evidence.first_response_delta_seconds == 25.0



@pytest.mark.parametrize(
    "replaced_seam",
    (
        "context_provider",
        "semantic_adapter",
        "conversation_adapter",
        "composer",
        "composer_provider",
    ),
)
def test_explicitly_replaced_collaboration_seams_retain_staged_dispatch(replaced_seam) -> None:
    from spg.application.conversation import (
        ConversationResponseComposer,
        WattNativeConversationContextAssembler,
    )
    from spg.providers.codex_interaction import (
        CodexSdkConversationProvider,
        CodexSdkInteractionSemanticCapability,
    )

    clients = [
        _Codex(_semantic_payload(), 1),
        _Codex('{"natural_response":"Use the supplied collaboration context."}', 2),
    ]
    pending = iter(clients)
    factory = lambda: next(pending)
    capability = CodexSdkWorkInteractionCapability(
        repository_location=".", codex_factory=factory, timeout_seconds=2
    )
    called = []

    if replaced_seam == "context_provider":
        class CustomContext(WattNativeConversationContextAssembler):
            def assemble(self, basis, collaboration):
                called.append("context")
                return super().assemble(basis, collaboration)
        capability.response_composer.context_provider = CustomContext()
    elif replaced_seam == "semantic_adapter":
        class CustomSemantic(CodexSdkInteractionSemanticCapability):
            def interpret_semantics(self, basis):
                called.append("semantic")
                return super().interpret_semantics(basis)
        capability.semantic_capability = CustomSemantic(
            repository_location=".", codex_factory=factory, timeout_seconds=2
        )
    elif replaced_seam == "conversation_adapter":
        class CustomConversation(CodexSdkConversationProvider):
            def respond(self, context, collaboration):
                called.append("conversation")
                return super().respond(context, collaboration)
        capability.conversation_provider = CustomConversation(
            repository_location=".", codex_factory=factory, timeout_seconds=2
        )
        capability.response_composer = ConversationResponseComposer(
            capability.conversation_provider
        )
    elif replaced_seam == "composer":
        class CustomComposer(ConversationResponseComposer):
            def compose(self, *args, **kwargs):
                called.append("composer")
                return super().compose(*args, **kwargs)
        capability.response_composer = CustomComposer(capability.conversation_provider)
    else:
        # A separately supplied native instance is also an explicit replacement.
        replacement = CodexSdkConversationProvider(
            repository_location=".", codex_factory=factory, timeout_seconds=2
        )
        capability.response_composer.provider = replacement
        # Facade evidence currently belongs to the configured adapter. Replacing
        # only the composer provider must not silently bypass it or claim success.
        with pytest.raises(InteractionInvariantViolation, match="does not match the configured Provider"):
            capability.interpret(_basis())
        assert all(client.instruction is None for client in clients)
        assert capability.last_pipeline_evidence is None
        return

    result = capability.interpret(_basis())

    assert result.natural_response == "Use the supplied collaboration context."
    assert called
    assert clients[0].instruction is not None and clients[1].instruction is not None
    assert capability.last_pipeline_evidence.pipeline_mode == "staged"
    assert capability.last_pipeline_evidence.provider_call_count == 2


@pytest.mark.parametrize("streaming", (False, True))
def test_staged_pipeline_preserves_original_custom_composer_signature(streaming) -> None:
    clients = [
        _Codex(_semantic_payload(), 1),
        _Codex('{"natural_response":"Legacy composition still works."}', 2),
    ]
    pending = iter(clients)
    capability = CodexSdkWorkInteractionCapability(
        repository_location=".", codex_factory=lambda: next(pending),
        coalesce_pre_work=False, timeout_seconds=2,
    )
    native_composer = capability.response_composer
    calls = []

    class LegacyComposer:
        # Existing custom composers need neither the new argument nor a provider field.
        def compose(self, basis, collaboration, *, on_response_delta=None):
            calls.append(collaboration)
            return native_composer.compose(
                basis, collaboration, on_response_delta=on_response_delta
            )

    capability.response_composer = LegacyComposer()
    deltas = []
    result = (
        capability.interpret_stream(_basis(), on_response_delta=deltas.append)
        if streaming else capability.interpret(_basis())
    )

    assert result.natural_response == "Legacy composition still works."
    assert len(calls) == 1
    assert capability.last_pipeline_evidence.conversation_turn_id == "turn-2"
    assert "".join(deltas) == (result.natural_response if streaming else "")


def test_swapped_composer_provider_after_success_fails_before_work_or_stale_evidence() -> None:
    from spg.providers.codex_interaction import CodexSdkConversationProvider

    clients = [
        _Codex(_semantic_payload(), 1),
        _Codex('{"natural_response":"First."}', 2),
        _Codex(_semantic_payload(), 3),
        _Codex('{"natural_response":"Replacement."}', 4),
    ]
    pending = iter(clients)
    calls = []

    def factory():
        client = next(pending)
        calls.append(client)
        return client

    capability = CodexSdkWorkInteractionCapability(
        repository_location=".", codex_factory=factory,
        coalesce_pre_work=False, timeout_seconds=2,
    )
    capability.interpret(_basis())
    assert capability.last_pipeline_evidence.conversation_turn_id == "turn-2"
    replacement = CodexSdkConversationProvider(
        repository_location=".", codex_factory=factory, timeout_seconds=2
    )
    capability.response_composer.provider = replacement

    with pytest.raises(InteractionInvariantViolation, match="does not match the configured Provider"):
        capability.interpret(_basis())

    assert len(calls) == 2
    assert all(client.instruction is None for client in clients[2:])
    assert replacement.last_turn_id is None
    assert capability.last_pipeline_evidence is None
    assert capability.last_collaboration_result is None


@pytest.mark.parametrize("artifact_path", ("docs/final-design.md", None))
def test_active_work_document_location_uses_governed_facts_and_completion_references(
    artifact_path,
) -> None:
    from spg.domain.interaction import ActiveWorkInterpretationContext, WorkRealityRevision

    basis = _basis()
    revision = WorkRealityRevision(
        id=UUID(int=10), work_id=UUID(int=11), revision_number=1,
        basis_fingerprint="b" * 64, revision_fingerprint="c" * 64,
        source_interaction_id=basis.interaction.id, source_assessment_id=UUID(int=12),
        source_record_ids=(basis.records[0].id,),
        motive="Produce the product design", desired_outcome="A reviewed design document",
        context_facts=(() if artifact_path is None else (f"Design saved at {artifact_path}",)),
        constraints=(), requests=("Write the proposed output docs/proposed-design.md",),
        engineering_scope_id=UUID(int=13), engineering_resource_id=UUID(int=14),
        scope_basis_fingerprint="d" * 64, repository_identity="local:test",
        repository_ref="main", source_baseline_id=UUID(int=15), source_revision="revision-1",
        governance_record_id=UUID(int=16), supporting_references=(), change_set=("initial",),
        rationale="Admitted design production", admitted_by="human", schema_version="v1",
        created_at=basis.interaction.created_at,
    )
    reference = f"COMPLETION:{UUID(int=17)}" + (f":{artifact_path}" if artifact_path else "")
    basis = basis.model_copy(update={"active_work_context": ActiveWorkInterpretationContext(
        work_revision=revision, engineering_scope_fingerprint="e" * 64,
        relevant_reality_references=(reference,),
    )})

    instruction = CodexSdkInteractionSemanticCapability.instruction(basis)

    assert "no design-document file has been generated or saved" not in instruction
    assert "governed Work facts and Reality references" in instruction
    assert "Distinguish a requested output path from a produced artifact" in instruction
    assert "say that its location is unknown" in instruction
    assert "do not infer that no artifact exists" in instruction
    assert reference in instruction
    assert "docs/proposed-design.md" in instruction
    if artifact_path:
        assert artifact_path in instruction
