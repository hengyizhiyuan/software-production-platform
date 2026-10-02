from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import inspect
from types import SimpleNamespace
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest

from spg.application.conversation import WattNativeConversationContextAssembler
from spg.application.engineering_semantics import (
    admit_semantic_facts,
    bind_engineering_semantic_facts,
)
from spg.application.interaction import _research_repository_source
from spg.domain.conversation import (
    ConversationTurnIntent,
    StructuredCollaborationResult,
)
from spg.domain.engineering_semantics import (
    EngineeringSemanticFactCandidate,
    NeutralExtractionKind,
    NeutralSemanticExtractionCandidate,
    SemanticCandidateOperation,
    SemanticEpistemicStatus,
    SemanticFactAuthority,
    SemanticRelation,
    SemanticReferenceRole,
    SemanticRoleOrigin,
    current_semantic_facts,
    semantic_fact_reference,
)
from spg.domain.interaction import (
    ActiveWorkInterpretationContext,
    Interaction,
    InteractionActor,
    InteractionCondition,
    InteractionInterpretationInput,
    InteractionRecord,
    WorkRealityRevision,
)
from spg.domain.runtime import CompletionContract
from spg.domain.verification import (
    VerificationCapabilityRequest,
    VerificationResultValue,
)
from spg.infrastructure.configured_executor import render_governed_instruction
from spg.providers.deterministic_verifier import DeterministicVerificationProvider


def _record(text: str, sequence: int = 1) -> InteractionRecord:
    return InteractionRecord(
        id=uuid5(NAMESPACE_URL, f"semantic-proof:{sequence}:{text}"),
        interaction_id=UUID(int=10),
        sequence=sequence,
        actor=InteractionActor.HUMAN,
        source="test:human",
        content=text,
        content_fingerprint=hashlib.sha256(text.encode()).hexdigest(),
        created_at=datetime(2026, 9, 18, tzinfo=UTC),
    )


def _extraction(
    record: InteractionRecord,
    *,
    extraction_id: str,
    kind: NeutralExtractionKind,
    values: tuple[str | int | float | bool, ...],
    source_text: str,
    roles: tuple[str | None, ...],
    unit: str | None = None,
) -> NeutralSemanticExtractionCandidate:
    return NeutralSemanticExtractionCandidate(
        extraction_id=extraction_id,
        kind=kind,
        values=values,
        unit=unit,
        source_record_id=record.id,
        source_text=source_text,
        explicit_roles=roles,
    )


def _fact(
    record: InteractionRecord,
    *,
    candidate_id: str,
    subject: str,
    relation: SemanticRelation,
    value,
    source_text: str,
    extraction_id: str | None = None,
    unit: str | None = None,
    scope: str | None = None,
    qualifiers: dict | None = None,
    authority: SemanticFactAuthority = SemanticFactAuthority.HUMAN_EXPLICIT,
    status: SemanticEpistemicStatus = SemanticEpistemicStatus.CONFIRMED,
    role_origin: SemanticRoleOrigin = SemanticRoleOrigin.EXPLICIT,
    supersedes: tuple[UUID, ...] = (),
    operation: SemanticCandidateOperation = SemanticCandidateOperation.UPSERT,
    reference_role: SemanticReferenceRole | None = None,
) -> EngineeringSemanticFactCandidate:
    return EngineeringSemanticFactCandidate(
        candidate_id=candidate_id,
        operation=operation,
        subject=subject,
        relation=relation,
        reference_role=reference_role,
        value=value,
        unit=unit,
        scope=scope,
        qualifiers=qualifiers or {},
        authority=authority,
        epistemic_status=status,
        source_record_ids=(record.id,),
        source_text=source_text,
        source_extraction_ids=() if extraction_id is None else (extraction_id,),
        role_origin=role_origin,
        supersedes_fact_ids=supersedes,
    )


def _bind(record, extractions, facts, *, prior=()):
    return bind_engineering_semantic_facts(
        basis_fingerprint=hashlib.sha256(record.content.encode()).hexdigest(),
        records=(record,),
        extractions=tuple(extractions),
        candidates=tuple(facts),
        prior_facts=tuple(prior),
    )


def _project_reference(record: InteractionRecord, *, subject: str = "project.source",
                       role: SemanticReferenceRole | None = SemanticReferenceRole.PROJECT_REPOSITORY,
                       value: str = "https://github.com/acme/app.git",
                       candidate_id: str = "repository") -> EngineeringSemanticFactCandidate:
    return _fact(record, candidate_id=candidate_id, subject=subject,
        relation=SemanticRelation.REFERENCE, reference_role=role, value=value,
        source_text=record.content)


def _reference_assessment(records: tuple[InteractionRecord, ...],
                          candidates: tuple[EngineeringSemanticFactCandidate, ...],
                          *, direct: str | None = None):
    from uuid import uuid4
    ir = SimpleNamespace(id=uuid4(), items=(), compiler_reference="test:semantic",
        semantic_fact_candidates=candidates, repository_source=direct)
    facts = bind_engineering_semantic_facts(basis_fingerprint="b" * 64,
        records=records, extractions=(), candidates=candidates, semantic_ir=ir)
    return SimpleNamespace(semantic_ir=ir, engineering_semantic_facts=facts)


@pytest.mark.parametrize("text,subject", (
    ("当前项目仓库是 https://github.com/acme/app.git", "project.source"),
    ("Our project repository is https://github.com/acme/app.git", "project.source"),
    ("当前项目仓库是 https://github.com/acme/app.git", "arbitrary.reference"),
))
def test_typed_project_repository_resolves_independent_of_language_or_subject(text, subject):
    record = _record(text)
    assessment = _reference_assessment((record,), (_project_reference(record, subject=subject),))
    assert _research_repository_source(assessment) == "https://github.com/acme/app.git"
    fact = assessment.engineering_semantic_facts[0]
    assert fact.reference_role is SemanticReferenceRole.PROJECT_REPOSITORY
    assert fact.provenance.source_record_ids == (record.id,)
    assert semantic_fact_reference(fact, work_revision_id=UUID(int=12)).reference_role is SemanticReferenceRole.PROJECT_REPOSITORY
    assert type(fact).model_validate(fact.model_dump(mode="json")).reference_role is SemanticReferenceRole.PROJECT_REPOSITORY


def test_external_reference_repository_is_not_project_source():
    record = _record("参考这个仓库 https://github.com/acme/app.git")
    assessment = _reference_assessment((record,), (_project_reference(record,
        role=SemanticReferenceRole.EXTERNAL_REFERENCE),))
    assert _research_repository_source(assessment) is None


def test_documentation_url_without_project_role_is_not_project_source():
    record = _record("See https://docs.example.com/guide for documentation")
    assessment = _reference_assessment((record,), (_project_reference(record,
        subject="project.repository", role=None,
        value="https://docs.example.com/guide"),))
    assert _research_repository_source(assessment) is None


def test_system_inferred_project_role_cannot_be_admitted():
    record = _record("See https://github.com/acme/app.git")
    with pytest.raises(ValueError, match="PROJECT_REPOSITORY"):
        EngineeringSemanticFactCandidate.model_validate(
            _project_reference(record).model_dump() | {
                "authority": SemanticFactAuthority.SYSTEM_INFERRED,
                "epistemic_status": SemanticEpistemicStatus.WORKING_ASSUMPTION,
                "role_origin": SemanticRoleOrigin.INFERRED,
            })


def test_superseded_project_repository_is_not_selected():
    record = _record("当前项目仓库是 https://github.com/acme/app.git")
    assessment = _reference_assessment((record,), (_project_reference(record),))
    old = assessment.engineering_semantic_facts[0].model_copy(update={
        "epistemic_status": SemanticEpistemicStatus.SUPERSEDED})
    assessment.engineering_semantic_facts = (old,)
    assert _research_repository_source(assessment) is None


def test_two_current_project_repositories_are_ambiguous():
    first = _record("当前项目仓库是 https://github.com/acme/app.git", sequence=1)
    second = _record("另一个项目仓库是 https://github.com/acme/other.git", sequence=2)
    assessment = _reference_assessment((first, second), (
        _project_reference(first, subject="project.first", candidate_id="first"),
        _project_reference(second, subject="project.second", candidate_id="second",
            value="https://github.com/acme/other.git")))
    assert _research_repository_source(assessment) is None


def test_direct_typed_repository_source_has_priority():
    record = _record("当前项目仓库是 https://github.com/acme/app.git")
    assessment = _reference_assessment((record,), (_project_reference(record),),
        direct="https://git.example.com/owner/typed.git")
    assert _research_repository_source(assessment) == "https://git.example.com/owner/typed.git"


def test_current_admitted_repository_role_survives_later_semantic_ir():
    from uuid import uuid4
    record = _record("当前项目仓库是 https://github.com/acme/app.git")
    assessment = _reference_assessment((record,), (_project_reference(record),))
    assessment.semantic_ir.id = uuid4()
    assert _research_repository_source(assessment) == "https://github.com/acme/app.git"


def test_historical_fact_without_reference_role_deserializes():
    record = _record("当前项目仓库是 https://github.com/acme/app.git")
    assessment = _reference_assessment((record,), (_project_reference(record, role=None),))
    fact = assessment.engineering_semantic_facts[0]
    payload = fact.model_dump(mode="json")
    payload.pop("reference_role")
    historical = type(fact).model_validate(payload)
    assert historical.reference_role is None
    assessment.engineering_semantic_facts = (historical,)
    assert _research_repository_source(assessment) is None


def test_neutral_extraction_pads_missing_roles_without_inventing_meaning() -> None:
    record = _record("倒计时结束后展示文案和动画")

    extraction = NeutralSemanticExtractionCandidate.model_validate(
        {
            "extraction_id": "completion-behavior",
            "kind": "ORDERED_VALUES",
            "values": ["结束文案", "动画"],
            "unit": None,
            "source_record_id": record.id,
            "source_text": record.content,
            "explicit_roles": [],
        }
    )

    assert extraction.explicit_roles == (None, None)


def test_neutral_extraction_still_rejects_surplus_roles() -> None:
    record = _record("倒计时结束后展示文案")

    with pytest.raises(ValueError, match="roles must align"):
        NeutralSemanticExtractionCandidate.model_validate(
            {
                "extraction_id": "completion-behavior",
                "kind": "BEHAVIOR",
                "values": ["结束文案"],
                "unit": None,
                "source_record_id": record.id,
                "source_text": record.content,
                "explicit_roles": ["message", "animation"],
            }
        )


def test_provider_quote_is_canonicalized_to_exact_cited_human_text() -> None:
    record = _record("ul下面加个button再")
    candidate = _fact(
        record,
        candidate_id="add-button",
        subject="list.action",
        relation=SemanticRelation.BEHAVIOR,
        value="add_button",
        source_text="UL 下面加一个 Button",
    )

    facts = _bind(record, (), (candidate,))

    assert facts[0].provenance.source_record_ids == (record.id,)
    assert facts[0].provenance.source_text == record.content


def test_same_compilation_fact_provenance_survives_quote_canonicalization() -> None:
    from types import SimpleNamespace
    from uuid import uuid4
    from spg.domain.interaction import InteractionInvariantViolation

    record = _record("ul下面加个button再")
    candidate = _fact(record, candidate_id="add-button", subject="list.action",
        relation=SemanticRelation.BEHAVIOR, value="add_button",
        source_text="UL 下面加一个 Button")
    ir = SimpleNamespace(id=uuid4(), items=(), compiler_reference="compiler:receipt",
        semantic_fact_candidates=(candidate,))
    facts = bind_engineering_semantic_facts(basis_fingerprint="a" * 64,
        records=(record,), extractions=(), candidates=(candidate,), semantic_ir=ir)
    assert facts[0].provenance.semantic_ir_id == ir.id
    assert facts[0].provenance.governed_provenance[0].source_text == record.content
    changed = candidate.model_copy(update={"value": "uncompiled_claim"})
    with pytest.raises(InteractionInvariantViolation, match="no typed compiler provenance"):
        bind_engineering_semantic_facts(basis_fingerprint="a" * 64,
            records=(record,), extractions=(), candidates=(changed,), semantic_ir=ir)


def test_provider_quote_rebinds_to_the_human_record_that_contains_it() -> None:
    first = _record("做一个 ul li 的 HTML 列表页", sequence=1)
    second = _record("ul下面加个button再", sequence=2)
    candidate = _fact(
        first,
        candidate_id="add-button",
        subject="list.action",
        relation=SemanticRelation.BEHAVIOR,
        value="add_button",
        source_text="ul下面加个button",
    )

    facts = bind_engineering_semantic_facts(
        basis_fingerprint=hashlib.sha256(second.content.encode()).hexdigest(),
        records=(first, second),
        extractions=(),
        candidates=(candidate,),
    )

    assert facts[0].provenance.source_record_ids == (second.id,)
    assert facts[0].provenance.source_text == "ul下面加个button"


@pytest.mark.parametrize(
    ("text", "extraction", "facts", "expected"),
    (
        (
            "首页 banner 做成 1920×1080。",
            (NeutralExtractionKind.ORDERED_VALUES, (1920, 1080), "1920×1080", (None, None), "px"),
            (("image.width", SemanticRelation.EQUALITY, 1920, "px", None),
             ("image.height", SemanticRelation.EQUALITY, 1080, "px", None)),
            {("image.width", 1920), ("image.height", 1080)},
        ),
        (
            "做 3 个页面，每页 5 张卡片。",
            (NeutralExtractionKind.QUANTITY, (3, 5), "3 个页面，每页 5 张卡片", ("page", "card_per_page"), None),
            (("page", SemanticRelation.CARDINALITY, 3, None, None),
             ("card", SemanticRelation.MAPPING, 5, None, "per_page")),
            {("page", 3), ("card", 5)},
        ),
        (
            "做 5 条路线，每条 9 格。",
            (NeutralExtractionKind.QUANTITY, (5, 9), "5 条路线，每条 9 格", ("lane", "cell_per_lane"), None),
            (("battlefield.lane", SemanticRelation.CARDINALITY, 5, None, None),
             ("battlefield.cell", SemanticRelation.MAPPING, 9, None, "per_lane")),
            {("battlefield.lane", 5), ("battlefield.cell", 9)},
        ),
        (
            "这个接口响应时间不要超过 30 秒。",
            (NeutralExtractionKind.COMPARISON, (30,), "不要超过 30 秒", ("upper_bound",), "second"),
            (("api.response_time", SemanticRelation.BOUND, 30, "second", "upper_inclusive"),),
            {("api.response_time", 30)},
        ),
        (
            "部门管理员只能修改本部门员工。",
            (NeutralExtractionKind.SCOPE, ("modify",), "部门管理员只能修改本部门员工", ("action",), None),
            (("department_admin", SemanticRelation.SCOPE, "modify", None, "same_department"),),
            {("department_admin", "modify")},
        ),
        (
            "点击按钮后弹出 hello Watt。",
            (NeutralExtractionKind.BEHAVIOR, ("hello Watt",), "点击按钮后弹出 hello Watt", ("result",), None),
            (("button.click", SemanticRelation.BEHAVIOR, "display", None, None),),
            {("button.click", "display")},
        ),
    ),
)
def test_cross_domain_software_cases_use_one_semantic_algebra(
    text, extraction, facts, expected
) -> None:
    record = _record(text)
    kind, values, source_text, roles, extraction_unit = extraction
    neutral = _extraction(
        record,
        extraction_id="n1",
        kind=kind,
        values=values,
        source_text=source_text,
        roles=roles,
        unit=extraction_unit,
    )
    candidates = tuple(
        _fact(
            record,
            candidate_id=f"f{index}",
            subject=subject,
            relation=relation,
            value=value,
            unit=unit,
            scope=scope,
            source_text=source_text,
            extraction_id="n1",
        )
        for index, (subject, relation, value, unit, scope) in enumerate(facts, 1)
    )

    bound = _bind(record, (neutral,), candidates)

    assert {(fact.subject, fact.value) for fact in current_semantic_facts(bound)} == expected
    assert all(fact.provenance.source_record_ids == (record.id,) for fact in bound)


def test_course_schedule_assumption_and_explicit_axes_override_have_one_lineage() -> None:
    first = _record("做一个 8×5 的小学五年级课程表。")
    ordered = _extraction(
        first,
        extraction_id="n1",
        kind=NeutralExtractionKind.ORDERED_VALUES,
        values=(8, 5),
        source_text="8×5",
        roles=(None, None),
    )
    initial = _bind(
        first,
        (ordered,),
        (
            _fact(
                first, candidate_id="periods", subject="schedule.period",
                relation=SemanticRelation.CARDINALITY, value=8,
                source_text="8×5", extraction_id="n1",
                authority=SemanticFactAuthority.SYSTEM_INFERRED,
                status=SemanticEpistemicStatus.WORKING_ASSUMPTION,
                role_origin=SemanticRoleOrigin.INFERRED,
            ),
            _fact(
                first, candidate_id="weekdays", subject="schedule.weekday",
                relation=SemanticRelation.CARDINALITY, value=5,
                source_text="8×5", extraction_id="n1",
                authority=SemanticFactAuthority.SYSTEM_INFERRED,
                status=SemanticEpistemicStatus.WORKING_ASSUMPTION,
                role_origin=SemanticRoleOrigin.INFERRED,
            ),
        ),
    )
    correction = _record("不是，我说的是 8 列 5 行。", sequence=2)
    explicit = _extraction(
        correction,
        extraction_id="n2",
        kind=NeutralExtractionKind.ORDERED_VALUES,
        values=(8, 5),
        source_text="8 列 5 行",
        roles=("column", "row"),
    )
    corrected = _bind(
        correction,
        (explicit,),
        (
            _fact(
                correction, candidate_id="columns", subject="layout.column",
                relation=SemanticRelation.CARDINALITY, value=8,
                source_text="8 列 5 行", extraction_id="n2",
                supersedes=tuple(fact.id for fact in initial),
            ),
            _fact(
                correction, candidate_id="rows", subject="layout.row",
                relation=SemanticRelation.CARDINALITY, value=5,
                source_text="8 列 5 行", extraction_id="n2",
            ),
        ),
        prior=initial,
    )

    assert {(fact.subject, fact.value) for fact in current_semantic_facts(corrected)} == {
        ("layout.column", 8), ("layout.row", 5),
    }
    assert all(
        fact.epistemic_status is SemanticEpistemicStatus.SUPERSEDED
        for fact in corrected[:2]
    )
    assert corrected[2].supersedes_fact_ids == tuple(fact.id for fact in initial)


def test_reversible_assumption_is_admitted_then_cleanly_corrected() -> None:
    first = _record("列表先用紧凑一点的间距。")
    assumption = _bind(
        first,
        (),
        (
            _fact(
                first, candidate_id="spacing", subject="list.item_spacing",
                relation=SemanticRelation.EQUALITY, value="compact",
                source_text=first.content,
                authority=SemanticFactAuthority.SYSTEM_INFERRED,
                status=SemanticEpistemicStatus.WORKING_ASSUMPTION,
                role_origin=SemanticRoleOrigin.INFERRED,
            ),
        ),
    )
    admitted = admit_semantic_facts(assumption, work_revision_id=UUID(int=20))
    assert admitted[0].epistemic_status is SemanticEpistemicStatus.WORKING_ASSUMPTION
    assert admitted[0].admitted_work_revision_id == UUID(int=20)

    correction = _record("间距明确改成 16 px。", sequence=2)
    corrected = _bind(
        correction,
        (),
        (
            _fact(
                correction, candidate_id="spacing-16", subject="list.item_spacing",
                relation=SemanticRelation.EQUALITY, value=16, unit="px",
                source_text="间距明确改成 16 px",
                supersedes=(admitted[0].id,),
            ),
        ),
        prior=admitted,
    )
    current = current_semantic_facts(corrected)
    assert len(current) == 1 and current[0].value == 16
    assert corrected[0].epistemic_status is SemanticEpistemicStatus.SUPERSEDED


def test_conversation_and_production_consume_the_same_admitted_fact_identity() -> None:
    record = _record("这个接口响应时间不要超过 30 秒。")
    facts = _bind(
        record,
        (),
        (
            _fact(
                record, candidate_id="latency", subject="api.response_time",
                relation=SemanticRelation.BOUND, value=30, unit="second",
                scope="upper_inclusive", source_text="不要超过 30 秒",
            ),
        ),
    )
    revision_id = UUID(int=30)
    facts = admit_semantic_facts(facts, work_revision_id=revision_id)
    revision = WorkRealityRevision(
        id=revision_id, work_id=UUID(int=31), revision_number=1,
        basis_fingerprint="a" * 64, revision_fingerprint="b" * 64,
        source_interaction_id=UUID(int=10), source_assessment_id=UUID(int=11),
        source_record_ids=(record.id,), motive="改进接口", desired_outcome="限制响应时间",
        context_facts=(), constraints=(), requests=(), engineering_semantic_facts=facts,
        engineering_scope_id=UUID(int=32), engineering_resource_id=None,
        scope_basis_fingerprint="c" * 64, source_baseline_id=None,
        governance_record_id=UUID(int=33), supporting_references=(), change_set=(),
        rationale="test", admitted_by="human:test", schema_version="work-reality-v3",
        created_at=datetime(2026, 9, 18, tzinfo=UTC),
    )
    active = ActiveWorkInterpretationContext(
        work_revision=revision,
        engineering_scope_fingerprint="d" * 64,
    )
    basis = InteractionInterpretationInput(
        interaction=Interaction(
            id=UUID(int=10), condition=InteractionCondition.OPEN,
            current_work_id=revision.work_id, created_by="test", updated_by="test",
            created_at=revision.created_at, updated_at=revision.created_at,
        ),
        records=(record,),
        active_work_context=active,
        basis_fingerprint="e" * 64,
    )
    context = WattNativeConversationContextAssembler().assemble(
        basis,
        StructuredCollaborationResult(
            turn_intent=ConversationTurnIntent.CONTEXT_ADDITION,
            response_language="Chinese",
        ),
    )
    reference = semantic_fact_reference(facts[0], work_revision_id=revision_id)
    contract = CompletionContract(
        required_changes=("src/api.py",),
        semantic_fact_obligations=(reference,),
    )
    instruction = render_governed_instruction("实现接口", contract)

    assert context.governed_engineering_semantic_facts[0].id == facts[0].id
    assert f"[{facts[0].id}]" in instruction
    assert "api.response_time" in instruction

    verification = DeterministicVerificationProvider(
        {"LATENCY_BOUND": VerificationResultValue.PASS}
    ).verify(
        VerificationCapabilityRequest(
            verification_identity=UUID(int=40),
            obligation="LATENCY_BOUND",
            semantic_fact_obligations=(reference,),
            snapshot_id=UUID(int=41),
            proposed_commit_identity="commit-41",
            tree_identity="tree-41",
            completion_evaluation_id=UUID(int=42),
            plan_revision_id=UUID(int=43),
            source_baseline_id=UUID(int=44),
        )
    )
    assert verification.evidence.metadata["semantic_fact_ids"] == [
        str(facts[0].id)
    ]


def test_semantic_core_contains_no_business_case_parser_registry() -> None:
    import spg.application.engineering_semantics as semantic_core

    source = inspect.getsource(semantic_core)
    for forbidden in (
        "ScheduleParser", "ImageParser", "GameParser", "TableParser",
        "course_table", "if image", "if game", "if dashboard",
    ):
        assert forbidden not in source
