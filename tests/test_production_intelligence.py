from hashlib import sha256
import json
from uuid import uuid4

import pytest

from spg.application.preparation import completion_contract_fingerprint
from spg.application.production_intelligence import (
    ContextAssemblyRequest,
    TaskContractRequest,
    default_context_orchestrator,
    default_system_capability_reality,
    default_task_contract_builder,
    system_capability_context_candidate,
)
from spg.domain.engineering_semantics import (
    SemanticEpistemicStatus,
    SemanticFactAuthority,
    SemanticFactReference,
    SemanticRelation,
)
from spg.domain.production_intelligence import (
    ContextBudget,
    ContextCandidate,
    ContextSource,
    EngineeringActivity,
)
from spg.domain.runtime import CompletionContract
from spg.infrastructure.configured_executor import render_governed_instruction


def _fact(*, authority=SemanticFactAuthority.HUMAN_EXPLICIT):
    return SemanticFactReference(
        fact_id=uuid4(),
        subject="schedule.period-count",
        relation=SemanticRelation.CARDINALITY,
        value=8,
        unit="periods",
        authority=authority,
        epistemic_status=(
            SemanticEpistemicStatus.CONFIRMED
            if authority is SemanticFactAuthority.HUMAN_EXPLICIT
            else SemanticEpistemicStatus.WORKING_ASSUMPTION
        ),
        source_work_revision_id=uuid4(),
    )


def test_context_orchestrator_prioritizes_truth_and_keeps_patterns_advisory():
    fact = _fact()
    package = default_context_orchestrator().assemble(
        ContextAssemblyRequest(
            basis_fingerprint="a" * 64,
            purpose="test current production decision",
            activity=EngineeringActivity.FEATURE_DELIVERY,
            candidates=(
                ContextCandidate(
                    candidate_id="semantic",
                    source=ContextSource.SEMANTIC_TRUTH,
                    content="period_count = 8",
                    source_reference=f"semantic-fact:{fact.fact_id}",
                    authority=fact.authority.value,
                    provenance=(
                        f"work-reality-revision:{fact.source_work_revision_id}",
                    ),
                    priority=100,
                    authoritative=True,
                    required=True,
                ),
                ContextCandidate(
                    candidate_id="response",
                    source=ContextSource.RESPONSE_CONTRACT,
                    content="Answer the current decision with reasoned tradeoffs",
                    source_reference="response-contract:test",
                    authority="ADVISORY_ONLY",
                    provenance=("interaction:test",),
                    priority=95,
                    required=True,
                ),
            ),
            semantic_facts=(fact,),
            budget=ContextBudget(
                max_items=8, max_characters=3000, max_items_per_source=4
            ),
        )
    )

    assert package.items[0].source is ContextSource.SEMANTIC_TRUTH
    assert package.items[0].authoritative is True
    pattern_items = tuple(
        item for item in package.items if item.source is ContextSource.DOMAIN_PATTERN
    )
    assert pattern_items
    assert all(item.authoritative is False for item in pattern_items)
    assert "governed-meaning-preservation:1" in package.selected_pattern_ids
    assert package.sop_reference == "sop:watt-software-production:1:FEATURE_DELIVERY"


def test_system_capability_reality_is_versioned_context_not_execution_authority():
    reality = default_system_capability_reality()
    candidate = system_capability_context_candidate(required=True)
    package = default_context_orchestrator().assemble(
        ContextAssemblyRequest(
            basis_fingerprint="c" * 64,
            purpose="Answer Watt identity and capability question",
            activity=EngineeringActivity.DISCOVERY,
            candidates=(candidate,),
            budget=ContextBudget(
                max_items=6, max_characters=4000, max_items_per_source=3
            ),
        )
    )

    assert reality.identity == "Watt"
    assert reality.system_type == "AI_NATIVE_SOFTWARE_PRODUCTION_SYSTEM"
    assert any("Create and modify software artifacts" in item for item in reality.capabilities)
    assert any("must not claim" in item for item in reality.boundaries)
    assert package.items[0].source is ContextSource.SYSTEM_CAPABILITY_REALITY
    assert package.items[0].authority == "SYSTEM_CAPABILITY_REALITY"
    assert "AI-native software production system" in package.items[0].content


def test_context_orchestrator_obeys_budget_without_dropping_required_truth():
    candidates = (
        ContextCandidate(
            candidate_id="required",
            source=ContextSource.SEMANTIC_TRUTH,
            content="governed truth",
            source_reference="semantic-fact:1",
            authority="HUMAN_EXPLICIT",
            provenance=("work-revision:1",),
            priority=100,
            authoritative=True,
            required=True,
        ),
        *(
            ContextCandidate(
                candidate_id=f"optional-{index}",
                source=ContextSource.ECF_REALITY,
                content=f"optional context {index}",
                source_reference=f"ecf:{index}",
                authority="SOURCE_REALITY",
                provenance=(f"ecf:{index}",),
                priority=20 - index,
            )
            for index in range(6)
        ),
    )
    package = default_context_orchestrator().assemble(
        ContextAssemblyRequest(
            basis_fingerprint="b" * 64,
            purpose="bounded selection",
            activity=EngineeringActivity.INVESTIGATION,
            candidates=candidates,
            budget=ContextBudget(
                max_items=3, max_characters=256, max_items_per_source=2
            ),
        )
    )

    assert len(package.items) == 3
    assert package.items[0].item_id == "required"
    assert package.omitted_candidate_count > 0


def test_sop_covers_extensible_activity_catalog_without_approval_semantics():
    orchestrator = default_context_orchestrator()
    supported = {
        activity
        for sop in orchestrator.sops.sops
        for guidance in sop.activities
        for activity in (guidance.activity,)
    }
    assert supported == set(EngineeringActivity)
    assert all(
        checkpoint.authority_effect == "NONE"
        for sop in orchestrator.sops.sops
        for guidance in sop.activities
        for checkpoint in guidance.checkpoints
    )


def test_task_contract_preserves_semantic_authority_scope_and_lineage():
    fact = _fact()
    task = default_task_contract_builder().build(
        TaskContractRequest(
            objective="Produce the admitted course table candidate",
            scope=("CREATE:index.html",),
            constraints=("Keep product semantics distinct from DOM structure",),
            acceptance_meaning=("Verify eight periods and five weekdays",),
            out_of_scope=("Any path other than index.html",),
            authority_lineage=(
                "work:1",
                "work-reality-revision:2",
                "steering-decision:3",
            ),
            work_reality_references=("work:1", "work-reality-revision:2"),
            ecf_references=("engineering-resource:1", "source-baseline:2@abc"),
            semantic_facts=(fact,),
            decision_reference="steering-decision:3",
        )
    )

    assert task.semantic_fact_references == (fact,)
    assert task.decision_trace.authority_reference == "steering-decision:3"
    assert task.decision_trace.status.value == "ADMITTED"
    assert task.reasoning_summary.raw_chain_of_thought_stored is False
    assert any(
        item.subject_reference == f"semantic-fact:{fact.fact_id}"
        and item.category.value == "HUMAN"
        for item in task.evidence_lineage
    )
    assert any(
        item.source is ContextSource.DOMAIN_PATTERN
        and item.authority == "ADVISORY_ONLY"
        for item in task.relevant_context
    )

    instruction = render_governed_instruction(
        task.objective,
        CompletionContract(
            required_outputs=("index.html",),
            verification_obligations=task.acceptance_meaning,
            semantic_fact_obligations=(fact,),
            task_contract=task,
        ),
    )
    assert f"Identity: {task.task_contract_id}" in instruction
    assert "This projection preserves already admitted intent and lineage" in instruction
    assert f"[{fact.fact_id}]" in instruction
    assert "does not widen execution authority" in instruction


def test_pattern_or_sop_context_cannot_be_promoted_to_authoritative_truth():
    with pytest.raises(ValueError, match="must remain optional guidance"):
        ContextCandidate(
            candidate_id="bad-pattern",
            source=ContextSource.DOMAIN_PATTERN,
            content="guidance",
            source_reference="pattern:test",
            authority="ADVISORY_ONLY",
            provenance=("pattern:test",),
            priority=50,
            authoritative=True,
        )


def test_legacy_completion_contract_fingerprint_does_not_drift():
    contract = CompletionContract(required_outputs=("index.html",))
    payload = contract.model_dump(mode="json")
    payload.pop("task_contract")
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()

    assert completion_contract_fingerprint(contract) == sha256(canonical).hexdigest()
