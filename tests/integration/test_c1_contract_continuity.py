"""C1: real PostgreSQL/Git/Owner contract composition, not live AI production.

IRK uses an explicit typed semantic oracle. Local output is deterministic. The
immediate Work input includes an explicit typed authority fixture; the Steering
planning input uses actual proposal/planner Owners with controlled persistence.
Both actual contract constructors and downstream Native/Verification/Candidate/
Guardian services run. No Integration/Acceptance or remote Deploy/Publish is
authorized. The fixture database must be dedicated and local.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
from threading import Thread
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect, insert, select, update

from spg.application.completion import CompletionService
from spg.application.delivery import DeliveryApplicationService
from spg.application.execution import ExecutionService
from spg.application.engineering_semantics import admit_semantic_facts
from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.application.governance import CandidateGovernanceService
from spg.application.governed_obligations import materialize_continuous_gates
from spg.application.guardian_assurance import GuardianAssuranceClient
from spg.application.interaction import WorkInteractionService
from spg.application.preparation import PreparationService
from spg.application.runtime import RuntimeService
from spg.application.steering import SteeringApplicationService
from spg.application.steering_production import SteeringProductionService
from spg.application.verification import VerificationService
from spg.domain.engineering_semantics import (
    EngineeringSemanticFactCandidate, SemanticEpistemicStatus,
    SemanticFactAuthority, SemanticRelation, SemanticRoleOrigin,
)
from spg.domain.execution import ExecutorDispatchRequest, ProviderReportedOutcome
from spg.domain.governance import CandidateSealRequest
from spg.domain.change import ProductionTargetKind
from spg.application.work import WORK_REALITY_SCHEMA_VERSION
from spg.domain.interaction import InteractionAssessmentCandidate, WorkRealityRevision
from spg.domain.planning import ProductionPlanningRequest
from spg.domain.intent_realization import (
    ProductionIntent, SemanticArgument, SemanticClause, SemanticItem, SemanticKind,
)
from spg.domain.preparation import (
    ContextArtifactSelection, ContextPackageRequest, ContextSemanticRole, ExecutorBinding,
)
from spg.domain.product import WorkMode, WorkRefinementRequest
from spg.domain.production_environment import (
    CandidatePreviewMode, CandidatePreviewSessionV1, PreviewRuntimeStatus,
)
from spg.domain.semantic_provenance import SemanticOrigin, SemanticProvenance
from spg.domain.steering import (
    CreateSteeringPlanRequest, SteeringStepSpec, SteeringStepState, SteeringStepType,
)
from spg.domain.verification import VerificationResultValue
from spg.infrastructure.executor_runtime.native_compatibility_executor import NativeQueuedExecutorCapability
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.persistence.auth_schema import authority_actors, authority_memberships
from spg.infrastructure.persistence.product_schema import (
    product_managed_sources, product_works, software_products, work_source_bases,
)
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_schema import production_work_units
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore
from spg.providers.deterministic_executor import (
    DeterministicExecutionSpecification, DeterministicFileOperation,
    DeterministicFileOperationType, DeterministicTestExecutor,
)
from spg.providers.protected_context_verifier import StaticProtectedContextVerifier
from spg.providers.repository_code_verifier import RepositoryCodeVerifier
from tests.irk_test_fixtures import semantic_candidate
from tests.integration.test_wic_governed_work_admission import _admit, _services_for_resource

pytestmark = pytest.mark.postgresql
ROOT = Path(__file__).resolve().parents[2]
HEADING = "C1 continuity"
CONTENT = f"<!doctype html><html><body><h1>{HEADING}</h1></body></html>\n"
CONSTRAINTS = (
    "index.html changes alone",
    "Excluded from this Work: deployment, publishing",
    "A reviewable Candidate is left for Human acceptance",
)
FACT_QUOTE = f"h1 text in index.html equals {HEADING}"
REQUIREMENT = "Create index.html\n" + FACT_QUOTE + "\n" + "\n".join(CONSTRAINTS)


def _git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


@pytest.fixture(autouse=True)
def c1_schema(postgres_database, monkeypatch):
    """Never truncate a provided business database; only this explicit sandbox."""
    url = postgres_database.engine.url
    assert url.host in {"localhost", "127.0.0.1", "::1"}
    assert url.database == "c1_contract_continuity"
    monkeypatch.setenv("SPG_DATABASE_URL", url.render_as_string(hide_password=False))
    command.upgrade(Config(ROOT / "alembic.ini"), "head")
    names = [name for name in inspect(postgres_database.engine).get_table_names()
             if name != "alembic_version"]
    with postgres_database.engine.begin() as connection:
        if names:
            connection.exec_driver_sql("TRUNCATE TABLE " + ",".join(
                '"' + name.replace('"', '""') + '"' for name in names) + " CASCADE")
        # Restore the migration-owned single-owner seed removed by truncation.
        # This is the same initialization as 20260926_52, not a lifecycle
        # Integration, Acceptance or Delivery authorization.
        connection.execute(insert(authority_actors).values(id="human:owner", kind="HUMAN"))
        connection.execute(insert(authority_memberships).values(
            organization_id="organization:default", actor_id="human:owner", role="OWNER"))
    yield


class DeclaredC1Fulfillment:
    """Controlled source-to-capability candidates for the declared C1 fixture.

    Production validates this complete candidate through the same validator used
    for model candidates. This oracle is neither live-model nor Human authority.
    """
    last_observation = None

    def form(self, inventory, capabilities, *, validation_feedback=None):
        from spg.domain.governed_obligation import (FulfillmentProjectionCandidate, FulfillmentRouteCandidate,
            FulfillmentComponentBasis, fulfillment_source_semantic_text)
        routes = []
        clause_sources = {source.get("item_id"): source["source_ref"] for source in inventory["sources"]
            if source["kind"] in {"IR_CLAUSE", "IR_CONSTRAINT"}}
        production_sources = tuple(source for source in inventory["sources"] if source["kind"] in {"IR_CLAUSE", "IR_CONSTRAINT"}
            and source["payload"]["item"].get("production") is not None)
        fact_refs = tuple(source["source_ref"] for source in inventory["sources"] if source["kind"] == "FACT")
        for source in inventory["sources"]:
            ref = source["source_ref"]
            item = source.get("item_id")
            supports = ()
            indices = ()
            if source["kind"] == "FACT": selected = ("ARTIFACT_CONTENT",)
            elif source["kind"] in {"WORK_CONTEXT", "IR_ITEM"}: selected = ("RETAIN_CONTEXT",)
            elif source["kind"] == "WORK_CONSTRAINT":
                indices = (source["index"],)
                content = source["payload"]["content"]
                # Fixture-declared meanings, never production keyword routing.
                meanings = {CONSTRAINTS[0]:("change-scope",("GIT_DIFF_SCOPE",)),
                            CONSTRAINTS[1]:("external-boundary",("DENY_DEPLOY","DENY_PUBLISH")),
                            CONSTRAINTS[2]:("candidate-handoff",("CANDIDATE_SEAL",))}
                if content in meanings:
                    original, selected = meanings[content]
                    supports = (clause_sources[original],)
                else:
                    # Exact values already produced by the unchanged typed C1 IR.
                    producer = next(entry for entry in production_sources
                        if content in tuple("Excluded from this Work: "+value for value in entry["payload"]["item"]["production"]["exclusions"]))
                    declared_effects = {"Excluded from this Work: deployment":("DENY_DEPLOY",),
                        "Excluded from this Work: publishing":("DENY_PUBLISH",)}
                    selected = declared_effects[content]
                    supports = (producer["source_ref"], clause_sources["external-boundary"])
            elif item == "change-scope": selected = ("GIT_DIFF_SCOPE",)
            elif item == "external-boundary": selected = ("DENY_DEPLOY","DENY_PUBLISH")
            elif item == "candidate-handoff": selected = ("CANDIDATE_SEAL",)
            else: selected = ("ARTIFACT_CONTENT",)
            for method in selected:
                routes.append(FulfillmentRouteCandidate(source_ref=ref, capability=method,
                    work_constraint_indices=indices,supporting_source_refs=supports,
                    target_paths=("index.html",) if method in {"ARTIFACT_CONTENT","GIT_DIFF_SCOPE"} else (),
                    rationale="Explicit declared C1 contract fixture responsibility.",
                    component_basis=FulfillmentComponentBasis(source_span_start=0,
                        source_span_end=len(fulfillment_source_semantic_text(source)),
                        source_component_quote=fulfillment_source_semantic_text(source),
                        linked_fact_refs=fact_refs if source in production_sources else ())))
        return FulfillmentProjectionCandidate(inventory_fingerprint=inventory["inventory_fingerprint"], routes=tuple(routes))

    def review(self, inventory, candidate):
        return DeclaredC1SemanticReview().review(inventory, candidate)


class DeclaredC1SemanticReview:
    """Separate controlled semantic oracle for original C1 source contributions."""
    def review(self, inventory, candidate):
        from spg.domain.governed_obligation import (FulfillmentSemanticReviewCandidate,
            FulfillmentSemanticSourceReview, fulfillment_candidate_fingerprint,
            fulfillment_components_fingerprint, fulfillment_source_semantic_text)
        results=[]
        for source in inventory["sources"]:
            routes=[route for route in candidate.routes if route.source_ref==source["source_ref"]]
            methods={route.capability for route in routes}
            item=source.get("item_id")
            if source["kind"]=="FACT": expected={"ARTIFACT_CONTENT"}
            elif source["kind"] in {"IR_ITEM","WORK_CONTEXT"}: expected={"RETAIN_CONTEXT"}
            elif source["kind"]=="WORK_CONSTRAINT":
                expected={CONSTRAINTS[0]:{"GIT_DIFF_SCOPE"},CONSTRAINTS[1]:{"DENY_DEPLOY","DENY_PUBLISH"},
                    CONSTRAINTS[2]:{"CANDIDATE_SEAL"},"Excluded from this Work: deployment":{"DENY_DEPLOY"},
                    "Excluded from this Work: publishing":{"DENY_PUBLISH"}}[source["payload"]["content"]]
            elif item=="change-scope":expected={"GIT_DIFF_SCOPE"}
            elif item=="external-boundary":expected={"DENY_DEPLOY","DENY_PUBLISH"}
            elif item=="candidate-handoff":expected={"CANDIDATE_SEAL"}
            else:expected={"ARTIFACT_CONTENT"}
            preserved=methods==expected and all(route.component_basis is not None
                and route.component_basis.source_component_quote==fulfillment_source_semantic_text(source) for route in routes)
            results.append(FulfillmentSemanticSourceReview(source_ref=source["source_ref"],
                complete_and_equivalent=preserved,reason="Controlled C1 original source meaning and consumer contract comparison."))
        return FulfillmentSemanticReviewCandidate(inventory_fingerprint=inventory["inventory_fingerprint"],
            candidate_fingerprint=fulfillment_candidate_fingerprint(candidate),
            components_fingerprint=fulfillment_components_fingerprint(candidate),source_results=tuple(results))


class DeclaredC1Meaning:
    """Typed fixture oracle, no live-model/generic language claim."""
    def interpret(self, basis):
        record = basis.records[-1]
        source = SemanticProvenance(origin=SemanticOrigin.HUMAN_EXPLICIT,
            source_record_id=record.id, source_text=record.content)
        scoped_source = source.model_copy(update={"source_text": CONSTRAINTS[0]})
        constraint_source = source.model_copy(update={"source_text": CONSTRAINTS[1]})
        handoff_source = source.model_copy(update={"source_text": CONSTRAINTS[2]})
        scope_item = SemanticItem(item_id="change-scope", kind=SemanticKind.CONSTRAINT,
            subject="repository-change-boundary", statement=CONSTRAINTS[0], confidence=1,
            provenance=(scoped_source,))
        constraint = SemanticItem(item_id="external-boundary", kind=SemanticKind.CONSTRAINT,
            subject="release-boundary", statement=CONSTRAINTS[1], confidence=1,
            provenance=(constraint_source,))
        handoff_item = SemanticItem(item_id="candidate-handoff", kind=SemanticKind.CONSTRAINT,
            subject="review-handoff", statement=CONSTRAINTS[2], confidence=1,
            provenance=(handoff_source,))
        target_source = source.model_copy(update={"source_text": "Create index.html"})
        production = ProductionIntent(objective=REQUIREMENT, primary_change="Create index.html",
            target_paths=(SemanticArgument(value="index.html", provenance=target_source),),
            exclusions=("deployment", "publishing"), current=True, new_work=True,
            bounded_change=True, acceptance_required=True, delivery_authorized=False)
        raw = semantic_candidate(record, production=production,
                                 extra_items=(scope_item, constraint, handoff_item))
        # The default helper clause covers the production item only. Every
        # protected constraint has one exact Human quote and typed clause.
        production_clause = raw.clauses[0].model_copy(update={
            "semantic_item_ids": (raw.items[0].item_id,)})
        raw = raw.model_copy(update={"clauses": (production_clause,
            SemanticClause(clause_id="change-scope", source_record_id=record.id,
                source_text=CONSTRAINTS[0], semantic_item_ids=(scope_item.item_id,),
                polarity="AFFIRMATIVE", modality="ASSERTION", temporal_scope="CURRENT",
                requested_effects=("RESTRICT_CHANGE_SCOPE",)),
            SemanticClause(clause_id="external-boundary", source_record_id=record.id,
                source_text=CONSTRAINTS[1], semantic_item_ids=(constraint.item_id,),
                polarity="NEGATED", modality="ASSERTION", temporal_scope="CURRENT",
                requested_effects=("PROHIBIT_DEPLOY", "PROHIBIT_PUBLISH")),
            SemanticClause(clause_id="candidate-handoff", source_record_id=record.id,
                source_text=CONSTRAINTS[2], semantic_item_ids=(handoff_item.item_id,),
                polarity="AFFIRMATIVE", modality="ASSERTION", temporal_scope="CURRENT",
                requested_effects=()))})
        return InteractionAssessmentCandidate(provider_identity="fixture:c1-declared-meaning",
            interpreted_motive=REQUIREMENT, desired_outcome=REQUIREMENT,
            candidate_constraints=CONSTRAINTS, semantic_intent=raw,
            semantic_fact_candidates=(EngineeringSemanticFactCandidate(
                candidate_id="heading", subject="page.h1", relation=SemanticRelation.EQUALITY,
                value=HEADING, scope="index.html", qualifiers={"element": "h1"}, authority=SemanticFactAuthority.HUMAN_EXPLICIT,
                epistemic_status=SemanticEpistemicStatus.CONFIRMED,
                source_record_ids=(record.id,), source_text=FACT_QUOTE,
                role_origin=SemanticRoleOrigin.EXPLICIT),),
            natural_response="Produce the bounded content; preserve the pending Human gates.")


def _never_generate():
    raise AssertionError("C1 fixture requires only existing deterministic evidence methods")


@dataclass
class ContractChain:
    database: object
    works: object
    work_id: UUID
    revision: object
    ir: object
    repository: Path
    baseline: object
    pwu: object
    prepared: object
    native: object
    executor: object
    execution: object
    completion: object
    verification: object
    snapshot: object
    records: tuple
    candidate: object
    guardian: object
    preview: object
    projection: dict


@contextmanager
def _candidate_http(candidate, repository):
    """Loopback exact Git blob; Guardian observes HTTP itself, no observation stub."""
    body = subprocess.check_output(["git", "-C", str(repository), "show",
                                    f"{candidate.proposed_commit_identity}:index.html"])
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200 if self.path in {"/", "/index.html"} else 404)
            self.send_header("Content-Type", "text/html")
            self.send_header("X-Candidate-Revision", candidate.proposed_commit_identity)
            self.send_header("X-Candidate-Tree", candidate.proposed_tree_identity)
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *_args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _attach_immediate_fixture_reality(database, works, draft, ready, resource, baseline):
    """Typed authority fixture for the immediate Work constructor's input.

    WIC admission only exposes LONG_LIVED_STEERING. This explicit fixture does
    not claim a normal immediate IRK entrance exists. submit/refine/approve and
    all downstream production/evidence constructors remain actual services.
    No admitted Steering Work is converted or rewound to fabricate that path.
    """
    assessment = ready.latest_assessment
    basis_records = tuple(item for item in ready.records
                          if item.sequence <= assessment.basis_last_sequence)
    scope = draft.engineering_scope
    now, revision_id, governance_id = datetime.now(UTC), uuid4(), uuid4()
    facts = admit_semantic_facts(assessment.engineering_semantic_facts,
                                work_revision_id=revision_id)
    payload = dict(id=revision_id, work_id=draft.work_id, revision_number=1,
        basis_fingerprint=assessment.basis_fingerprint,
        source_interaction_id=ready.interaction.id, source_assessment_id=assessment.id,
        source_record_ids=tuple(item.id for item in basis_records),
        motive=assessment.interpreted_motive, desired_outcome=assessment.desired_outcome,
        context_facts=assessment.candidate_context, constraints=assessment.candidate_constraints,
        requests=assessment.current_requests, engineering_semantic_facts=facts,
        engineering_scope_id=scope.id, engineering_resource_id=resource.id,
        scope_basis_fingerprint=scope.fingerprint, repository_identity=resource.repository_identity,
        repository_ref=resource.authoritative_ref, source_baseline_id=baseline.id,
        source_revision=baseline.repository_revision, governance_record_id=governance_id,
        supporting_references=tuple(f"INTERACTION_RECORD:{item.id}" for item in basis_records),
        change_set=(), rationale="SyntheticAuthorityFixture: controlled C1 typed authority for immediate constructor",
        admitted_by="fixture:human:c1", schema_version=WORK_REALITY_SCHEMA_VERSION,
        created_at=now)
    json_payload = json.loads(json.dumps(payload, default=str))
    json_payload["engineering_semantic_facts"] = [item.model_dump(mode="json") for item in facts]
    revision = WorkRealityRevision(**payload,
        revision_fingerprint=works._fingerprint(json_payload))
    with database.unit_of_work() as uow:
        runtime, product = RuntimeStore(uow.session), ProductStore(uow.session)
        # Existing initial-admission evidence shape, explicitly synthetic test
        # authority. Its legacy decision name is not a claim that this immediate
        # Work used normal WIC long-lived admission or gained future authority.
        runtime.insert_governance(dict(id=governance_id,
            decision_type="ADMIT_LONG_LIVED_WORK", authority_identity="fixture:human:c1",
            subject_type="PRODUCT_WORK", subject_identity=str(draft.work_id),
            scope={"fixture_only": True, "authority_fixture": "SyntheticAuthorityFixture",
                   "work_mode": WorkMode.IMMEDIATE_PRODUCTION.value,
                   "source_interaction_id": str(ready.interaction.id),
                   "source_assessment_id": str(assessment.id),
                   "assessment_basis_fingerprint": assessment.basis_fingerprint,
                   "work_reality_revision_id": str(revision.id),
                   "engineering_scope_id": str(scope.id), "scope_fingerprint": scope.fingerprint,
                   "resource_id": str(resource.id), "repository_identity": resource.repository_identity,
                   "repository_ref": resource.authoritative_ref,
                   "source_baseline_id": str(baseline.id), "source_revision": baseline.repository_revision,
                   "desired_outcome": assessment.desired_outcome,
                   "constraints": list(assessment.candidate_constraints),
                   "artifact_target": None, "source_change_proposal_fingerprint": None},
            rationale=revision.rationale, created_at=now))
        values=revision.model_dump(mode="python")
        for key in ("source_record_ids", "supporting_references", "change_set",
                    "context_facts", "constraints", "requests"):
            values[key]=[str(item) for item in values[key]]
        values["engineering_semantic_facts"]=[item.model_dump(mode="json") for item in facts]
        product.insert_work_reality_revision(values)
        product.update_work(draft.work_id, {"current_work_reality_revision_id": revision.id,
                                           "updated_at": now})
        uow.commit()
    return revision


def _materialize_steering_fixture_plan(database, works, admitted, resource, baseline):
    """Actual proposal/planner Owners; explicit controlled planning input only."""
    proposal=works._repository_change_proposal(work_id=admitted.work_id,
        raw=REQUIREMENT, request=WorkRefinementRequest(code_exact_targets=("index.html",)),
        existing=None, resource=resource, baseline_id=baseline.id,
        source_ref=baseline.repository_ref, source_revision=baseline.repository_revision,
        desired_outcome=REQUIREMENT, constraints=CONSTRAINTS)
    verification=works._proposal_verification_summary(proposal)
    plan=works.planning.propose(ProductionPlanningRequest(work_id=admitted.work_id,
        target_kind=ProductionTargetKind.CODE_WORK, admitted_requirement=REQUIREMENT,
        desired_outcome=REQUIREMENT, production_objective=REQUIREMENT,
        change_proposal=proposal, constraints=CONSTRAINTS,
        verification_expectation=verification,
        engineering_scope_summary=admitted.engineering_scope.summary,
        engineering_resource_id=resource.id, repository_identity=resource.repository_identity,
        source_baseline_id=baseline.id, source_revision=baseline.repository_revision,
        context_references=("AI_context.md",)))
    # No status/mode/scope/accepted facts are changed. Planning is the controlled
    # fixture boundary, not a live-model design or production qualification.
    with database.unit_of_work() as uow:
        ProductStore(uow.session).update_work(admitted.work_id, {
            "production_plan_proposal":plan.model_dump(mode="json"),
            "code_change_proposal":proposal.model_dump(mode="json"),
            "verification_expectation":verification,"updated_at":datetime.now(UTC)})
        uow.commit()


def _admit_c1(database, tmp_path, route):
    works, _ = _services_for_resource(database, tmp_path, "test://c1-contract-" + uuid4().hex)
    works.fulfillment_provider = DeclaredC1Fulfillment()
    interactions = WorkInteractionService(database, capability=DeclaredC1Meaning())
    origin = interactions.create_interaction(human_identity="fixture:human:c1")
    ready = interactions.append_and_assess(origin.id, REQUIREMENT, human_identity="fixture:human:c1")
    if route == "work":
        admitted = works.submit_work(REQUIREMENT, mode=WorkMode.IMMEDIATE_PRODUCTION)
    else:
        admitted = _admit(works, ready, authority_identity="fixture:human:c1")
    interactions.shutdown()
    with database.unit_of_work() as uow:
        product = ProductStore(uow.session)
        resource = product.default_resource()
        repository = Path(resource.location_ref)
        _git(repository, "remote", "add", "origin", "http://gitea.invalid/c1-fixture.git")
        baseline = works.runtime.current_baseline(repository_identity=resource.repository_identity,
                                                   repository_ref=resource.authoritative_ref)
        product_id = uuid4()
        uow.session.execute(insert(software_products).values(id=product_id,
            owner_id="fixture:human:c1", name="C1 controlled Product", lifecycle="ACTIVE",
            description="Controlled contract fixture, no Human Product acceptance"))
        uow.session.execute(update(product_works).where(product_works.c.id == admitted.work_id).values(
            product_id=product_id))
        uow.session.execute(insert(product_managed_sources).values(product_id=product_id,
            repository_identity=resource.repository_identity + ":product", provider_kind="gitea",
            provider_reference="fixture:c1", accepted_ref="refs/heads/main",
            accepted_revision=baseline.repository_revision,
            accepted_tree=baseline.repository_tree_identity, origin={}, version=0))
        uow.session.execute(insert(work_source_bases).values(work_id=admitted.work_id,
            product_id=product_id, resource_id=resource.id, source_version=0,
            source_revision=baseline.repository_revision, source_tree=baseline.repository_tree_identity,
            work_ref=resource.authoritative_ref))
        uow.commit()
    if route == "work":
        draft = works.refine_work(admitted.work_id, WorkRefinementRequest(
            code_exact_targets=("index.html",),
            constraints=ready.latest_assessment.candidate_constraints))
        revision = _attach_immediate_fixture_reality(database, works, draft, ready, resource, baseline)
        works.approve_work(draft.work_id, authority_identity="fixture:human:c1")
    else:
        with database.unit_of_work() as uow:
            revision = ProductStore(uow.session).current_work_reality_revision(admitted.work_id)
        _materialize_steering_fixture_plan(database, works, admitted, resource, baseline)
        SteeringApplicationService(database).create_plan(CreateSteeringPlanRequest(
            work_id=admitted.work_id, rationale="C1 controlled production admission",
            steps=(SteeringStepSpec(type=SteeringStepType.PRODUCE,
                objective="Create index.html", completion_condition="Exact contract output verified",
                state=SteeringStepState.CURRENT),)))
        bridge = SteeringProductionService(database, fulfillment_provider=DeclaredC1Fulfillment())
        bridge.admit_cycle(bridge.materialize_request(admitted.work_id))
    with database.unit_of_work() as uow:
        product = ProductStore(uow.session)
        binding = product.runtime_binding(admitted.work_id)
        pwu = RuntimeStore(uow.session).work_unit(binding.work_unit_id)
        assert product.current_work_reality_revision(admitted.work_id) == revision
    from spg.application.governed_obligations import validate_continuous_gates
    bindings = pwu.completion_contract.fulfillment_bindings
    validate_continuous_gates(bindings, revision, ready.latest_assessment.semantic_ir,
        source_revision=baseline.repository_revision, exact_target_paths=("index.html",))
    assert all(binding.projection_inventory_fingerprint for binding in bindings)
    assert {binding.component for binding in bindings} >= {
        "artifact-content", "git-diff-scope", "deploy", "publish", "reviewable-candidate"}
    assert set(CONSTRAINTS) <= set(revision.constraints)
    assert {index for binding in bindings for index in binding.work_constraint_indices} == set(range(len(revision.constraints)))
    original_gates = tuple(binding for binding in bindings if binding.source_kind.value == "IR_CONSTRAINT"
        and binding.component in {"git-diff-scope", "deploy", "publish"})
    assert {binding.component: (binding.phase.value, binding.evidence_method, binding.target_paths)
        for binding in original_gates} == {
        "git-diff-scope": ("CURRENT_VERIFICATION", "EXACT_GIT_DIFF_SCOPE", ("index.html",)),
        "deploy": ("CONTINUOUS_FROM_ADMISSION", "EXACT_PERMISSION_GATE", ()),
        "publish": ("CONTINUOUS_FROM_ADMISSION", "EXACT_PERMISSION_GATE", ())}
    assert len(original_gates) == 3 and all(binding.fact_id is None for binding in original_gates)
    assert pwu.completion_contract.semantic_fact_obligations
    assert pwu.completion_contract.task_contract.semantic_fact_references == pwu.completion_contract.semantic_fact_obligations
    return works, admitted.work_id, revision, ready.latest_assessment.semantic_ir, repository, baseline, pwu


@pytest.fixture(params=("work", "steering"))
def admitted_contract(postgres_database, tmp_path, request):
    return _admit_c1(postgres_database, tmp_path, request.param)


def _produce_chain(database, tmp_path, admitted):
    works, work_id, revision, ir, repository, baseline, pwu = admitted
    runtime = RuntimeService(database)
    attempt = runtime.create_initial_attempt(pwu.id)
    preparation = PreparationService(database)
    package = preparation.assemble_context_package(pwu.id, repository, ContextPackageRequest(
        artifacts=(ContextArtifactSelection(semantic_role=ContextSemanticRole.PROJECT_CONTEXT,
                                             repository_relative_path="AI_context.md"),)))
    prepared = preparation.prepare_attempt(attempt.id, package.id, ExecutorBinding(
        binding_ref="binding:c1-contract", capability_identity="capability:watt-native-executor",
        profile_identity="profile:c1-controlled"), repository, tmp_path / "attempt-workspaces")
    native_runtime = NativeExecutorRuntimeService(database)
    native_executor = NativeQueuedExecutorCapability(database, native_runtime,
        provider_profile="fixture:c1", resource_profile="standard", environment_profile="fixture:c1",
        strict_production_context=True)
    local_output = DeterministicTestExecutor(DeterministicExecutionSpecification(
        operations=(DeterministicFileOperation(operation=DeterministicFileOperationType.CREATE,
            repository_relative_path="index.html", content=CONTENT),),
        reported_outcome=ProviderReportedOutcome.SUCCESS, summary="Controlled C1 contract output"))
    class NativeBoundFixtureExecutor:
        def dispatch(self, request):
            admission = native_executor._admission(request)
            native_runtime.admit(admission)
            return local_output.dispatch(request)
    execution = ExecutionService(database, preparation=preparation)
    produced = execution.dispatch_and_observe(attempt.id, NativeBoundFixtureExecutor())
    assert produced.provider_report.outcome is ProviderReportedOutcome.SUCCESS
    completion = CompletionService(database, observer=execution.observer).evaluate_observation(produced.observation.id)
    verification = VerificationService(database, observer=execution.observer)
    snapshot = verification.create_proposed_snapshot(completion.evaluation.id)
    provider = RepositoryCodeVerifier(database, context_verifier=StaticProtectedContextVerifier(_never_generate))
    records = tuple(verification.verify_obligation(snapshot.id, obligation, provider)
                    for obligation in pwu.completion_contract.verification_obligations)
    assert all(item.result is VerificationResultValue.PASS for item in records), [
        item.evidence.metadata for item in records]
    satisfied = verification.evaluate_admissibility(snapshot.id)
    candidate = CandidateGovernanceService(database).seal_candidate(CandidateSealRequest(
        proposed_snapshot_id=snapshot.id, production_admissibility_id=satisfied.admissibility.id,
        expected_work_unit_version=satisfied.work_unit.version))
    from guardian.runtime import JsonSoftwareAssuranceStore
    guardian_store = JsonSoftwareAssuranceStore(tmp_path / "guardian")
    previews = JsonProductionEnvironmentStore(tmp_path / "previews")
    guardian = GuardianAssuranceClient(DeliveryApplicationService(database), previews, guardian_store)
    with database.unit_of_work() as uow:
        native = NativeExecutionStore(uow.session).attempt_binding(attempt.id)
    return ContractChain(database, works, work_id, revision, ir, repository, baseline, pwu,
        prepared, native, native_executor, execution, completion, verification, snapshot,
        records, candidate, guardian, previews, {})


@pytest.fixture
def chain(postgres_database, tmp_path, admitted_contract):
    return _produce_chain(postgres_database, tmp_path, admitted_contract)


def _assess(chain):
    with _candidate_http(chain.candidate, chain.repository) as endpoint:
        now = datetime.now(UTC)
        session = CandidatePreviewSessionV1(id=uuid4(), work_id=chain.work_id,
            candidate_id=chain.candidate.id, candidate_fingerprint=chain.candidate.fingerprint,
            repository_identity=chain.candidate.repository_identity,
            repository_revision=chain.candidate.proposed_commit_identity,
            repository_tree=chain.candidate.proposed_tree_identity, workspace_id=uuid4(),
            environment_id=uuid4(), mode=CandidatePreviewMode.STATIC_PREVIEW,
            status=PreviewRuntimeStatus.READY, definition_version="fixture:c1-loopback-v1",
            endpoint=endpoint, image_reference="fixture:c1-local-git-blob",
            service_identities=("c1-loopback-http",), created_at=now, updated_at=now)
        return chain.guardian.assess_ready_preview(session)


def test_both_actual_admission_paths_reach_independent_guardian(chain, record_property):
    projection = _assess(chain)
    assert projection["gate"] == "PASS", projection
    _saved_assurance_request(chain)
    _persist_contract_chain_evidence(chain, projection)
    assert chain.candidate.proposed_commit_identity != chain.baseline.repository_revision
    assert chain.native.binding.source_vector.members[0].source_commit_oid == chain.baseline.repository_revision
    check_record = next(item for item in chain.records if "static_html_semantic_checks" in item.evidence.metadata)
    checks = check_record.evidence.metadata["static_html_semantic_checks"]
    assert any(item.get("fact_id") for item in checks)
    assert any(item.get("source_kind") == "IR_CONSTRAINT" and not item.get("fact_id") for item in checks)
    assert any(item["coverage"] == "PENDING_CANDIDATE_GATE"
               for item in check_record.evidence.metadata["protected_context_checks"])
    with chain.database.unit_of_work() as uow:
        runtime = RuntimeStore(uow.session)
        assert runtime.human_authorizations_for_candidate(chain.candidate.id) == ()
    for name, value in {"work":chain.work_id, "work_revision":chain.revision.id,
        "pwu":chain.pwu.id, "attempt":chain.native.attempt_id,
        "candidate":chain.candidate.id, "candidate_fingerprint":chain.candidate.fingerprint,
        "source_baseline":chain.baseline.repository_revision,
        "candidate_output":chain.candidate.proposed_commit_identity,
        "verification_ids":','.join(str(item.id) for item in chain.records)}.items():
        record_property(name, str(value))

def _request_for_actual_snapshot(chain, **changes):
    from spg.domain.verification import VerificationCapabilityRequest
    task = chain.pwu.completion_contract.task_contract
    lineage = task.decision_context
    obligation = next(item.obligation for item in chain.records
                      if "static_html_semantic_checks" in item.evidence.metadata)
    return VerificationCapabilityRequest(verification_identity=uuid4(), obligation=obligation,
        semantic_fact_obligations=chain.pwu.completion_contract.semantic_fact_obligations,
        task_contract_id=task.task_contract_id,
        decision_context_fingerprint=lineage.package_fingerprint,
        protected_context_obligations=lineage.protected_obligations,
        snapshot_id=chain.snapshot.id, proposed_commit_identity=chain.snapshot.proposed_commit_identity,
        tree_identity=chain.snapshot.tree_identity,
        completion_evaluation_id=chain.completion.evaluation.id,
        plan_revision_id=chain.pwu.plan_revision_id,
        source_baseline_id=chain.baseline.id).model_copy(update=changes)


@pytest.mark.parametrize("corruption", ("missing", "stale", "injected", "constraint_identity"))
def test_native_rejects_binding_loss_drift_and_injection(chain, corruption):
    """Mutate only sandbox PWU projection; original IR/Work Reality stays exact."""
    completion = chain.pwu.completion_contract
    bindings = completion.fulfillment_bindings
    if corruption == "missing":
        bindings = ()
    elif corruption == "stale":
        bindings = (bindings[0].model_copy(update={"source_revision": "0" * 40}), *bindings[1:])
    elif corruption == "injected":
        bindings = (*bindings, bindings[0])
    else:
        bindings = (bindings[0].model_copy(update={"constraint_item_id": "unadmitted"}), *bindings[1:])
    wrong = completion.model_copy(update={"fulfillment_bindings": bindings})
    with chain.database.unit_of_work() as uow:
        uow.session.execute(update(production_work_units).where(
            production_work_units.c.id == chain.pwu.id).values(
                completion_contract=wrong.model_dump(mode="json")))
        uow.commit()
    prepared = chain.prepared.execution_request
    with pytest.raises(ValueError, match="OBLIGATION_(GATE_BINDING_DRIFT|PROJECTION_SOURCE_REVISION_DRIFT|PROJECTION_DUPLICATE_ROUTE|SOURCE_INVENTORY_INCOMPLETE|WORK_CONSTRAINT_INVENTORY_INCOMPLETE|PROJECTION_MIXED_BASIS)"):
        chain.executor._admission(ExecutorDispatchRequest(dispatch_id=uuid4(), execution=prepared))
    with chain.database.unit_of_work() as uow:
        assert ProductStore(uow.session).current_work_reality_revision(chain.work_id) == chain.revision


@pytest.mark.parametrize("corruption", ("fact_identity", "work_revision", "candidate_revision", "candidate_tree"))
def test_actual_repository_verification_rejects_source_identity_drift(chain, corruption):
    request = _request_for_actual_snapshot(chain)
    if corruption in {"fact_identity", "work_revision"}:
        facts = request.semantic_fact_obligations
        wrong = facts[0].model_copy(update={
            "fact_id" if corruption == "fact_identity" else "source_work_revision_id": uuid4()})
        request = request.model_copy(update={"semantic_fact_obligations": (wrong, *facts[1:])})
    else:
        request = request.model_copy(update={
            "proposed_commit_identity" if corruption == "candidate_revision" else "tree_identity": "0" * 40})
    result = RepositoryCodeVerifier(chain.database,
        context_verifier=StaticProtectedContextVerifier(_never_generate)).verify(request)
    assert result.result is not VerificationResultValue.PASS


def _saved_assurance_request(chain):
    from guardian.contracts.software_assurance import AssuranceRequest
    paths = list((chain.guardian.guardian_store.root / "requests").glob("*.json"))
    assert len(paths) == 1
    request = AssuranceRequest.model_validate_json(paths[0].read_text(encoding="utf-8"))
    assert request.evidence_contract_version == "governed-obligation-v2"
    assert request.production_lineage.source_baseline_revision == chain.baseline.repository_revision
    assert request.source_revision == chain.candidate.proposed_commit_identity
    assert request.production_lineage.qualified_output_revision == request.source_revision
    assert request.acceptance_state == "PENDING"
    assert request.delivery_authorization_state == "NOT_AUTHORIZED"
    return request


def _assess_saved_request(chain, transform):
    assert _assess(chain)["gate"] == "PASS"
    request = transform(_saved_assurance_request(chain))
    with _candidate_http(chain.candidate, chain.repository) as endpoint:
        request = request.model_copy(update={"request_id": uuid4(), "runtime_url": endpoint})
        return chain.guardian.guardian_store.assess(request)


@pytest.mark.parametrize("field", (
    "source_baseline_revision", "source_baseline_tree", "work_reality_revision_id", "pwu_id",
    "qualified_output_revision", "qualified_output_tree",
))
def test_guardian_independently_rejects_input_output_and_work_lineage_drift(chain, field):
    def corrupt(request):
        value = uuid4() if field in {"work_reality_revision_id", "pwu_id"} else "0" * 40
        return request.model_copy(update={"production_lineage": request.production_lineage.model_copy(
            update={field: value})})
    result = _assess_saved_request(chain, corrupt)
    assert result.gate.value == "BLOCKED", result.model_dump(mode="json")
    assert any(item.category.value == "CONTEXT_COVERAGE_GAP" for item in result.findings)


@pytest.mark.parametrize("missing_kind", (
    "verification", "candidate", "native-attempt", "source-baseline", "proposed-snapshot", "pwu",
))
def test_guardian_rejects_missing_independent_owner_records(chain, missing_kind):
    assert _assess(chain)["gate"] == "PASS"
    request = _saved_assurance_request(chain)
    resolver = chain.guardian.guardian_store.owner_evidence_resolver
    # Fault-inject a missing Owner record at the real resolver boundary. All
    # remaining records are actual DB records; no caller coverage assertion helps.
    chain.guardian.guardian_store.owner_evidence_resolver = lambda reference: (
        None if reference.startswith(missing_kind + ":") else resolver(reference))
    with _candidate_http(chain.candidate, chain.repository) as endpoint:
        result = chain.guardian.guardian_store.assess(request.model_copy(update={
            "request_id": uuid4(), "runtime_url": endpoint}))
    assert result.gate.value == "BLOCKED", result.model_dump(mode="json")
    assert result.findings


@pytest.mark.parametrize("component", ("deploy", "publish"))
def test_real_delivery_authorization_entrypoints_deny_prohibited_effects(chain, component, tmp_path):
    from spg.application.cloud_delivery import CloudDeliveryError, CloudDeliveryService
    from spg.application.github_delivery import GitHubDeliveryError, GitHubDeliveryService
    from spg.config import Settings
    settings = Settings(database_url=chain.database.engine.url.render_as_string(hide_password=False),
                        owner_runtime_store_root=tmp_path / "unused-owner-runtime")
    if component == "deploy":
        service = CloudDeliveryService(chain.database, DeliveryApplicationService(chain.database), settings)
        with pytest.raises(CloudDeliveryError, match="OBLIGATION_DELIVERY_PROHIBITED"):
            service.authorize("fixture:human:c1", chain.work_id, object())
    else:
        service = GitHubDeliveryService(chain.database, settings)
        with pytest.raises(GitHubDeliveryError) as error:
            service.authorize("fixture:human:c1", work_id=chain.work_id, manifest_id=uuid4(),
                expected_revision=chain.candidate.proposed_commit_identity, target_branch="main",
                expected_remote_revision=None, rationale="Negative authorization probe")
        assert error.value.code == "OBLIGATION_DELIVERY_PROHIBITED"
    with chain.database.unit_of_work() as uow:
        assert RuntimeStore(uow.session).human_authorizations_for_candidate(chain.candidate.id) == ()


@pytest.mark.parametrize("field,value", (
    ("acceptance_state", "ACCEPTED"), ("delivery_authorization_state", "AUTHORIZED"),
))
def test_guardian_contract_rejects_fabricated_future_human_authority(chain, field, value):
    from guardian.contracts.software_assurance import AssuranceRequest
    from pydantic import ValidationError
    assert _assess(chain)["gate"] == "PASS"
    request = _saved_assurance_request(chain)
    payload = request.model_dump(mode="json")
    payload[field] = value
    with pytest.raises(ValidationError, match="cannot inherit Acceptance or Delivery authority"):
        AssuranceRequest.model_validate(payload)


# C1 negative API compatibility is qualified at the actual independent Owner
# import/call boundary by tests/test_c1_ecf_contract_compatibility.py::
# test_actual_current_main_same_version_rejects_managed_api_explicitly.
# It uses the real unsupported current-main module, not a mocked '0.1' string.

def _persist_contract_chain_evidence(chain, projection):
    """Optional safe receipt export before the isolated fixture DB is truncated.

    No database URL/settings/credential is exported. All source Human content
    belongs to DeclaredC1Meaning above, not preserved production/incident data.
    Archive source/image identity is supplied by the runner's separate manifest;
    an unset revision remains UNKNOWN rather than labeling dirty code as HEAD.
    """
    output = os.environ.get("C1_EVIDENCE_OUTPUT")
    if not output:
        return
    request = _saved_assurance_request(chain)
    result = chain.guardian.guardian_store.get_result(request.request_id)
    assert result is not None and result.gate.value == "PASS"
    with chain.database.unit_of_work() as uow:
        runtime = RuntimeStore(uow.session)
        product = ProductStore(uow.session)
        work = product.work(chain.work_id)
        revision = product.current_work_reality_revision(chain.work_id)
        assert revision == chain.revision
        pwu = runtime.work_unit(chain.pwu.id)
        native = NativeExecutionStore(uow.session).attempt_binding(chain.native.attempt_id)
        authorizations = runtime.human_authorizations_for_candidate(chain.candidate.id)
        assert authorizations == ()
        payload = {
            "kind": "C1_CONTROLLED_CONTRACT_INTEGRATION",
            "evidence_level": "E2",
            "captured_at_utc": datetime.now(UTC).isoformat(),
            "application_revision": os.environ.get("C1_APPLICATION_REVISION", "UNKNOWN"),
            "guardian_revision": os.environ.get("C1_GUARDIAN_REVISION", "UNKNOWN"),
            "ecf_revision": os.environ.get("C1_ECF_REVISION", "UNKNOWN"),
            "admission_path": ("WorkApplicationService.approve_work"
                if work.mode is WorkMode.IMMEDIATE_PRODUCTION
                else "SteeringProductionService.admit_cycle"),
            "fixture_lifecycle_selection": work.mode.value,
            "source_fixture": "Controlled managed genesis V0; no accepted V1 or Human acceptance",
            "authority_fixture": ("SyntheticAuthorityFixture" if work.mode is WorkMode.IMMEDIATE_PRODUCTION
                                  else "actual WIC initial Work admission with declared typed oracle"),
            "fixture_admission_boundary": (
                "actual submit/refine; controlled typed authority WorkReality; actual approve"
                if work.mode is WorkMode.IMMEDIATE_PRODUCTION else
                "actual IRK Work admission; controlled actual proposal/planner output persistence; actual Steering admission"),
            "live_model_production": False,
            "human_integration_authorized": False,
            "human_delivery_accepted": False,
            "semantic_ir": chain.ir.model_dump(mode="json"),
            "work_reality_revision": revision.model_dump(mode="json"),
            "source_baseline": runtime.snapshot(chain.baseline.id).model_dump(mode="json"),
            "runtime_binding": product.runtime_binding(chain.work_id).model_dump(mode="json"),
            "task_and_completion_contract": pwu.completion_contract.model_dump(mode="json"),
            "pwu": pwu.model_dump(mode="json"),
            "native_binding": native.model_dump(mode="json"),
            "proposed_snapshot": runtime.proposed_snapshot(chain.snapshot.id).model_dump(mode="json"),
            "completion_evaluation": chain.completion.evaluation.model_dump(mode="json"),
            "verification_records": [runtime.verification_record(item.id).model_dump(mode="json")
                                     for item in chain.records],
            "candidate": runtime.baseline_candidate(chain.candidate.id).model_dump(mode="json"),
            "human_authorizations": [],
            "guardian_request": request.model_dump(mode="json"),
            "guardian_result": result.model_dump(mode="json"),
            "watt_guardian_projection": projection,
        }
    directory = Path(output).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (work.mode.value.casefold() + "-" + str(chain.work_id) + ".json")
    with target.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")