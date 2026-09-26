"""Governed application operations for the S1-C durable Runtime spine."""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.domain.change import ChangeTargetShape, CodeVerificationKind
from spg.domain.planning import ProductionNodeKind, ProductionPlanNode, ProductionPlanStep
from spg.domain.production_intelligence import ContextSource

from spg.domain.runtime import (
    CompletionContract,
    AttemptCondition,
    AttemptRequest,
    BootstrapAlreadyInitialized,
    BootstrapRequest,
    BootstrapResult,
    InitialRunRequest,
    InitialRuntimeSpine,
    PlanCondition,
    RunCondition,
    RuntimeInvariantViolation,
    RuntimeNotBootstrapped,
    RuntimeRecordNotFound,
    SnapshotCondition,
    SnapshotRecord,
    ExecutionAttemptRecord,
    WorkUnitCondition,
)
from spg.domain.verification import ProductionAdmissibilityOutcome
from spg.infrastructure.git_repository import GitRepositoryObserver
from spg.infrastructure.git_join import GitJoinReconciler
from spg.infrastructure.git_workspace import GitExactReality
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


RUNTIME_ACTOR = "spg-runtime"


class RuntimeService:
    """Sole S1-C owner of authoritative Runtime lifecycle transitions."""

    def __init__(
        self,
        database: Database,
        repository_observer: GitRepositoryObserver | None = None,
    ) -> None:
        self.database = database
        self.repository_observer = repository_observer or GitRepositoryObserver()

    def bootstrap_trusted_baseline(self, request: BootstrapRequest) -> BootstrapResult:
        """Explicitly observe and admit one initial trusted repository reality."""

        with self.database.unit_of_work() as unit_of_work:
            if RuntimeStore(unit_of_work.session).current_pointer(repository_identity=request.repository_identity, repository_ref=request.repository_ref) is not None:
                raise BootstrapAlreadyInitialized(
                    "a Current Trusted Baseline already exists"
                )

        reality = self.repository_observer.observe(
            request.repository_path,
            request.repository_identity,
            request.repository_ref,
        )
        tree_identity = GitExactReality._git(
            request.repository_path.resolve(), "rev-parse", f"{reality.exact_revision}^{{tree}}",
        )
        timestamp = datetime.now(UTC)
        snapshot_id = uuid4()
        governance_id = uuid4()

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            if store.current_pointer(repository_identity=request.repository_identity, repository_ref=request.repository_ref) is not None:
                raise BootstrapAlreadyInitialized(
                    "a Current Trusted Baseline already exists"
                )

            store.insert_snapshot(
                {
                    "id": snapshot_id,
                    "condition": SnapshotCondition.TRUSTED.value,
                    "repository_identity": reality.repository_identity,
                    "repository_ref": reality.repository_ref,
                    "repository_revision": reality.exact_revision,
                    "repository_tree_identity": tree_identity,
                    "source_baseline_id": None,
                    "created_at": timestamp,
                }
            )
            store.insert_governance(
                {
                    "id": governance_id,
                    "decision_type": "BOOTSTRAP_INITIAL_BASELINE",
                    "authority_identity": request.authority_identity,
                    "subject_type": "PRODUCTION_SNAPSHOT",
                    "subject_identity": str(snapshot_id),
                    "scope": {
                        **request.scope,
                        "repository_identity": reality.repository_identity,
                        "repository_ref": reality.repository_ref,
                        "repository_revision": reality.exact_revision,
                    },
                    "rationale": request.rationale,
                    "created_at": timestamp,
                }
            )
            store.insert_baseline_pointer(
                {
                    "singleton_id": 1,
                    "snapshot_id": snapshot_id,
                    "version": 0,
                    "updated_at": timestamp,
                }
            )
            self._append_transition(
                store,
                entity_type="PRODUCTION_SNAPSHOT",
                entity_id=snapshot_id,
                from_condition=None,
                to_condition=SnapshotCondition.TRUSTED.value,
                reason="BOOTSTRAP_TRUSTED_BASELINE",
                actor=request.authority_identity,
                correlation=snapshot_id,
                timestamp=timestamp,
            )

            snapshot = self._required_snapshot(store, snapshot_id)
            pointer = store.current_pointer(repository_identity=request.repository_identity, repository_ref=request.repository_ref)
            governance = store.governance_for_subject(str(snapshot_id))
            if pointer is None or len(governance) != 1:
                raise RuntimeInvariantViolation("bootstrap records were not constructed")
            result = BootstrapResult(
                snapshot=snapshot,
                pointer=pointer,
                governance=governance[0],
            )
            unit_of_work.commit()
            return result

    def current_baseline(self, *, repository_identity: str | None = None, repository_ref: str | None = None, source_baseline_id: UUID | None = None) -> SnapshotRecord:
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            pointer = store.current_pointer(repository_identity=repository_identity, repository_ref=repository_ref, source_baseline_id=source_baseline_id)
            if pointer is None:
                raise RuntimeNotBootstrapped("no Current Trusted Baseline exists")
            return self._required_snapshot(store, pointer.snapshot_id)

    def create_initial_runtime_spine(
        self,
        request: InitialRunRequest,
    ) -> InitialRuntimeSpine:
        """Atomically construct Run -> active Plan R1 -> proposed generic PWU."""

        timestamp = datetime.now(UTC)
        run_id, plan_id, work_unit_id = uuid4(), uuid4(), uuid4()
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            contract = request.completion_contract
            exact_source = request.source_baseline_id
            for boundary in (contract.artifact_contract, contract.change_contract, contract.production_plan):
                if boundary is not None:
                    if exact_source is not None and exact_source != boundary.source_baseline_id:
                        raise RuntimeInvariantViolation("Run contracts disagree on Source Baseline")
                    exact_source = boundary.source_baseline_id
            pointer = store.current_pointer(source_baseline_id=exact_source, for_update=True)
            if pointer is not None and exact_source is not None and pointer.snapshot_id != exact_source:
                raise RuntimeInvariantViolation("Run Source Baseline is stale")
            if pointer is None:
                raise RuntimeNotBootstrapped("bootstrap is required before Run creation")
            baseline = self._required_snapshot(store, pointer.snapshot_id)
            if baseline.condition is not SnapshotCondition.TRUSTED:
                raise RuntimeInvariantViolation("Current Baseline must be TRUSTED")

            store.insert_run(
                {
                    "id": run_id,
                    "intent_ref": request.intent_ref,
                    "goal": request.goal,
                    "production_horizon": request.production_horizon.value,
                    "source_baseline_id": baseline.id,
                    "integrated_baseline_id": baseline.id,
                    "current_plan_revision_id": None,
                    "condition": RunCondition.OPEN.value,
                    "version": 0,
                    "created_at": timestamp,
                }
            )
            store.insert_plan_revision(
                {
                    "id": plan_id,
                    "production_run_id": run_id,
                    "revision_number": 1,
                    "graph": None if contract.production_plan is None or contract.production_plan.graph is None
                    else contract.production_plan.graph.model_dump(mode="json"),
                    "supersedes_plan_revision_id": None,
                    "source_baseline_id": baseline.id,
                    "condition": PlanCondition.ACTIVE.value,
                    "version": 0,
                    "created_at": timestamp,
                }
            )
            store.bind_run_to_plan(run_id, expected_version=0, plan_id=plan_id)
            graph = None if contract.production_plan is None else contract.production_plan.graph
            if graph is not None and graph.starting_baseline_id not in {None, baseline.id}:
                raise RuntimeInvariantViolation("initial Production Plan starts from another baseline")
            executable = () if graph is None else tuple(
                node for node in graph.nodes if node.kind is not ProductionNodeKind.GROUP
            )
            if executable:
                roots = tuple(node for node in executable if not node.dependency_ids)
                if not roots:
                    raise RuntimeInvariantViolation("Production Plan has no initial READY PWU")
                work_unit_id = uuid5(NAMESPACE_URL, f"spg:plan-node:{plan_id}:{roots[0].node_id}")
            for node in executable or (None,):
                pwu_id = (
                    work_unit_id if node is None else
                    uuid5(NAMESPACE_URL, f"spg:plan-node:{plan_id}:{node.node_id}")
                )
                scoped = contract if node is None else self._scoped_contract(
                    contract, node, baseline.id, baseline.repository_revision,
                )
                store.insert_work_unit(
                    {
                        "id": pwu_id,
                        "production_run_id": run_id,
                        "plan_revision_id": plan_id,
                        "source_baseline_id": baseline.id if node is None or not node.dependency_ids else None,
                        "node_id": None if node is None else node.node_id,
                        "parent_baseline_ids": [] if node is None or not node.dependency_ids else None,
                        "verified_output_baseline_id": None,
                        "reconciliation_evidence": None,
                        "objective": request.initial_work_unit_objective if node is None else node.objective,
                        "completion_contract": scoped.model_dump(mode="json"),
                        "condition": WorkUnitCondition.PROPOSED.value,
                        "version": 0,
                        "current_execution_generation": 0,
                        "created_at": timestamp,
                    }
                )
            for entity_type, entity_id, condition, reason in (
                ("PRODUCTION_RUN", run_id, RunCondition.OPEN.value, "RUN_CREATED"),
                (
                    "PLAN_REVISION",
                    plan_id,
                    PlanCondition.ACTIVE.value,
                    "INITIAL_PLAN_ACTIVATED",
                ),
            ):
                self._append_transition(
                    store,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    from_condition=None,
                    to_condition=condition,
                    reason=reason,
                    actor=RUNTIME_ACTOR,
                    correlation=run_id,
                    timestamp=datetime.now(UTC),
                )
            for unit in store.work_units_for_plan(plan_id):
                self._append_transition(
                    store, entity_type="PRODUCTION_WORK_UNIT", entity_id=unit.id,
                    from_condition=None, to_condition=WorkUnitCondition.PROPOSED.value,
                    reason="WORK_UNIT_PROPOSED", actor=RUNTIME_ACTOR,
                    correlation=run_id, timestamp=datetime.now(UTC),
                )

            result = self._required_spine(store, run_id)
            unit_of_work.commit()
            return result

    @staticmethod
    def _scoped_contract(
        contract, node: ProductionPlanNode, baseline_id: UUID, source_revision: str,
    ):
        """Narrow a Work obligation to one leaf without inventing authority."""

        paths = set(node.writable_paths)
        change = contract.change_contract
        if change is not None:
            targets = tuple(target for target in change.exact_targets if target.path in paths)
            checks = tuple(item for item in change.verification_obligations if (
                item.kind in {CodeVerificationKind.PATH_SCOPE, CodeVerificationKind.GIT_DIFF_CHECK}
                or (item.kind is CodeVerificationKind.PYTHON_COMPILE and any(path.endswith(".py") for path in paths))
                or (item.target is not None and (item.target in paths or any(
                    path.endswith(f"/{item.target.replace('.', '/')}.py") for path in paths
                )))
            ))
            change = change.model_copy(update={
                "target_shape": ChangeTargetShape.EXACT_TARGET_SET,
                "exact_targets": targets, "allowed_areas": (),
                "verification_obligations": checks,
            })
        artifact = contract.artifact_contract
        if artifact is not None and artifact.artifact_path not in paths:
            artifact = None
        task = contract.task_contract
        if task is not None:
            essential_sources = {
                ContextSource.WORK_REALITY, ContextSource.SYSTEM_CAPABILITY_REALITY,
                ContextSource.SEMANTIC_TRUTH, ContextSource.SOP,
            }
            scoped_context = tuple(item for item in task.relevant_context if (
                item.source in essential_sources
                or item.reference in node.context_references
                or any(path in item.reference for path in node.context_references)
            ))
            task = task.model_copy(update={
                "task_contract_id": uuid5(NAMESPACE_URL, f"spg:scoped-task:{task.task_contract_id}:{node.node_id}"),
                "objective": node.objective,
                "scope": node.authority_scope or ("JOIN:verified-parent-baselines",),
                "required_capabilities": node.required_capabilities,
                "relevant_context": scoped_context or task.relevant_context[:1],
                "acceptance_meaning": node.acceptance_criteria,
                "out_of_scope": tuple(dict.fromkeys((
                    *task.out_of_scope,
                    *(f"WRITE:{path}" for path in contract.required_changes if path not in paths),
                ))),
            })
        plan = contract.production_plan
        if plan is not None:
            plan = plan.model_copy(update={
                "artifact_targets": tuple(item for item in plan.artifact_targets if item.path in paths),
                "change_proposal": None,
                "change_contract": change,
                "ordered_steps": (
                    ProductionPlanStep(position=1, instruction=node.objective),
                    ProductionPlanStep(position=2, instruction="Verify the exact scoped result."),
                ),
            })
        return contract.model_copy(update={
            "required_outputs": tuple(path for path in contract.required_outputs if path in paths),
            "required_changes": tuple(path for path in contract.required_changes if path in paths),
            "verification_obligations": (
                tuple(item.identity for item in change.verification_obligations)
                if change is not None else
                contract.verification_obligations if node.kind is ProductionNodeKind.JOIN else
                tuple(item for item in contract.verification_obligations if (
                    ":" not in item or item.split(":", 1)[1] in paths
                ))
            ),
            "task_contract": task,
            "change_contract": change,
            "artifact_contract": artifact,
            "production_plan": plan,
        })

    def inspect_run(self, run_id: UUID) -> InitialRuntimeSpine:
        with self.database.unit_of_work() as unit_of_work:
            return self._required_spine(RuntimeStore(unit_of_work.session), run_id)

    def revise_production_plan(
        self, run_id: UUID, contract: CompletionContract, *, reason: str,
    ) -> InitialRuntimeSpine:
        """Supersede future PWUs at a verified Work integration checkpoint."""

        if not reason.strip() or contract.production_plan is None or contract.production_plan.graph is None:
            raise RuntimeInvariantViolation("re-planning requires reason and executable graph")
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            run = store.run(run_id, for_update=True)
            if run is None or run.current_plan_revision_id is None:
                raise RuntimeRecordNotFound("Production Run or active Plan is missing")
            old = store.plan_revision(run.current_plan_revision_id, for_update=True)
            if old is None or old.graph is None or old.condition is not PlanCondition.ACTIVE:
                raise RuntimeInvariantViolation("re-planning requires an active multi-PWU Plan")
            old_units = store.work_units_for_plan(old.id)
            old_by_node = {unit.node_id: unit for unit in old_units}
            old_nodes = {node.node_id: node for node in old.graph.nodes}

            def plan_ancestors(node_id: str) -> set[str]:
                result: set[str] = set()
                for parent_id in old_nodes[node_id].dependency_ids:
                    result.add(parent_id)
                    result.update(plan_ancestors(parent_id))
                return result

            def integrated_descends_from(snapshot_id: UUID) -> bool:
                cursor = run.integrated_baseline_id
                while cursor is not None:
                    if cursor == snapshot_id:
                        return True
                    current = store.snapshot(cursor)
                    cursor = None if current is None else current.source_baseline_id
                return False

            for unit in old_units:
                if unit.verified_output_baseline_id is not None:
                    if not self._is_integration_checkpoint(old.graph, unit.node_id):
                        joined = any(
                            node.kind is ProductionNodeKind.JOIN
                            and unit.node_id in plan_ancestors(node.node_id)
                            and old_by_node[node.node_id].verified_output_baseline_id is not None
                            and integrated_descends_from(old_by_node[node.node_id].verified_output_baseline_id)
                            for node in old.graph.nodes
                        )
                        if not joined:
                            raise RuntimeInvariantViolation("cannot re-plan while parallel branch output awaits Join")
                    continue
                if unit.condition is not WorkUnitCondition.PROPOSED or unit.current_execution_generation != 0:
                    raise RuntimeInvariantViolation("cannot supersede an in-flight or attempted PWU")
            baseline = store.snapshot(run.integrated_baseline_id)
            if baseline is None or baseline.condition is not SnapshotCondition.TRUSTED:
                raise RuntimeInvariantViolation("Work integrated baseline is not trusted")
            old_paths = {path for node in old.graph.nodes for path in node.writable_paths}
            new_graph = contract.production_plan.graph
            new_paths = {path for node in new_graph.nodes for path in node.writable_paths}
            if not new_paths.issubset(old_paths):
                raise RuntimeInvariantViolation("re-planning cannot expand the admitted path authority")
            if contract.production_plan.source_baseline_id != run.source_baseline_id:
                raise RuntimeInvariantViolation("revised Plan changed the Work delivery source")
            graph = new_graph.model_copy(update={"starting_baseline_id": baseline.id})
            plan_id = uuid4()
            for unit in old_units:
                if unit.verified_output_baseline_id is None:
                    store.supersede_work_unit(unit.id, unit.version)
            store.supersede_plan_revision(old.id, old.version)
            store.insert_plan_revision({
                "id": plan_id, "production_run_id": run.id,
                "revision_number": old.revision_number + 1,
                "graph": graph.model_dump(mode="json"),
                "supersedes_plan_revision_id": old.id,
                "source_baseline_id": run.source_baseline_id,
                "condition": PlanCondition.ACTIVE.value, "version": 0,
                "created_at": timestamp,
            })
            nodes = tuple(node for node in graph.nodes if node.kind is not ProductionNodeKind.GROUP)
            roots = tuple(node for node in nodes if not node.dependency_ids)
            if not roots:
                raise RuntimeInvariantViolation("revised Plan has no READY PWU")
            for node in nodes:
                scoped = self._scoped_contract(contract, node, baseline.id, baseline.repository_revision)
                scoped = self._rebase_scoped_contract(scoped, baseline.id, baseline.repository_revision)
                store.insert_work_unit({
                    "id": uuid5(NAMESPACE_URL, f"spg:plan-node:{plan_id}:{node.node_id}"),
                    "production_run_id": run.id, "plan_revision_id": plan_id,
                    "source_baseline_id": baseline.id if not node.dependency_ids else None,
                    "node_id": node.node_id,
                    "parent_baseline_ids": [] if not node.dependency_ids else None,
                    "verified_output_baseline_id": None, "reconciliation_evidence": None,
                    "objective": node.objective,
                    "completion_contract": scoped.model_dump(mode="json"),
                    "condition": WorkUnitCondition.PROPOSED.value,
                    "version": 0, "current_execution_generation": 0,
                    "created_at": timestamp,
                })
            store.bind_run_to_plan(run.id, run.version, plan_id)
            self._append_transition(
                store, entity_type="PLAN_REVISION", entity_id=plan_id,
                from_condition=None, to_condition=PlanCondition.ACTIVE.value,
                reason=f"REALITY_REPLAN:{reason.strip()[:180]}",
                actor=RUNTIME_ACTOR, correlation=old.id, timestamp=timestamp,
            )
            result = self._required_spine(store, run.id)
            unit_of_work.commit()
            return result

    def publish_verified_pwu_output(
        self, work_unit_id: UUID, proposed_snapshot_id: UUID,
    ) -> SnapshotRecord:
        """Record verified branch output without moving an authoritative Git ref."""

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            work_unit = store.work_unit(work_unit_id, for_update=True)
            if work_unit is None:
                raise RuntimeRecordNotFound(f"PWU not found: {work_unit_id}")
            plan = store.plan_revision(work_unit.plan_revision_id)
            run = store.run(work_unit.production_run_id, for_update=True)
            proposed = store.proposed_snapshot(proposed_snapshot_id)
            if plan is None or plan.graph is None or run is None or proposed is None:
                raise RuntimeInvariantViolation("verified output requires an active multi-PWU Plan")
            if plan.id != run.current_plan_revision_id or plan.condition is not PlanCondition.ACTIVE:
                raise RuntimeInvariantViolation("verified output belongs to a superseded Plan")
            if proposed.work_unit_id != work_unit.id or proposed.source_baseline_id != work_unit.source_baseline_id:
                raise RuntimeInvariantViolation("proposed output does not match the exact PWU input")
            expected_output_id = uuid5(NAMESPACE_URL, f"spg:verified-pwu-baseline:{proposed.id}")
            if work_unit.verified_output_baseline_id is not None:
                if work_unit.verified_output_baseline_id != expected_output_id:
                    raise RuntimeInvariantViolation("verified PWU output cannot be replaced")
                existing_output = store.snapshot(expected_output_id)
                if existing_output is None or existing_output.repository_revision != proposed.proposed_commit_identity:
                    raise RuntimeInvariantViolation("verified PWU output lineage disappeared")
                return existing_output
            admissible = any(
                item.work_unit_id == work_unit.id
                and item.outcome is ProductionAdmissibilityOutcome.ADMISSIBLE
                for item in store.production_admissibility_for_snapshot(proposed.id)
            )
            if work_unit.condition is not WorkUnitCondition.SATISFIED or not admissible:
                raise RuntimeInvariantViolation("PWU output is not independently verified and satisfied")
            node = next(item for item in plan.graph.nodes if item.node_id == work_unit.node_id)
            if node.kind is ProductionNodeKind.JOIN:
                evidence = work_unit.reconciliation_evidence
                if evidence is None:
                    raise RuntimeInvariantViolation("Join has no persisted reconciliation evidence")
                if evidence.get("conflicts") and evidence.get("candidate_tree") == proposed.tree_identity:
                    raise RuntimeInvariantViolation(
                        "Join conflict tree is unchanged; explicit resolution and verification are required"
                    )
                store.mark_join_resolution(work_unit, proposed.id, proposed.tree_identity)
                work_unit = store.work_unit(work_unit.id, for_update=True)
                assert work_unit is not None
            baseline_id = expected_output_id
            existing = store.snapshot(baseline_id)
            if existing is None:
                store.insert_snapshot({
                    "id": baseline_id, "condition": SnapshotCondition.TRUSTED.value,
                    "repository_identity": proposed.repository_identity,
                    "repository_ref": proposed.repository_ref,
                    "repository_revision": proposed.proposed_commit_identity,
                    "repository_tree_identity": proposed.tree_identity,
                    "source_baseline_id": proposed.source_baseline_id,
                    "created_at": datetime.now(UTC),
                })
            elif existing.repository_revision != proposed.proposed_commit_identity:
                raise RuntimeInvariantViolation("verified baseline identity was reused")
            store.set_verified_output(work_unit, baseline_id)
            if self._is_integration_checkpoint(plan.graph, node.node_id):
                if run.integrated_baseline_id != work_unit.source_baseline_id:
                    raise RuntimeInvariantViolation("Work integration baseline diverged")
                store.advance_run_integrated_baseline(run, baseline_id)
            self._activate_successors(store, plan.id)
            self._append_transition(
                store, entity_type="PRODUCTION_WORK_UNIT", entity_id=work_unit.id,
                from_condition=WorkUnitCondition.SATISFIED.value,
                to_condition="VERIFIED_OUTPUT_PUBLISHED", reason="EXACT_VERIFIED_BASELINE_RECORDED",
                actor=RUNTIME_ACTOR, correlation=proposed.id, timestamp=datetime.now(UTC),
            )
            result = store.snapshot(baseline_id)
            assert result is not None
            unit_of_work.commit()
            return result

    def reconcile_join_attempt(self, attempt_id: UUID) -> dict[str, object] | None:
        """Prepare exact parent trees in the normal Join PWU workspace."""

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            attempt = store.attempt(attempt_id)
            if attempt is None:
                raise RuntimeRecordNotFound(f"Attempt not found: {attempt_id}")
            unit = store.work_unit(attempt.work_unit_id)
            plan = None if unit is None else store.plan_revision(unit.plan_revision_id)
            if unit is None or plan is None or plan.graph is None:
                return None
            node = next((item for item in plan.graph.nodes if item.node_id == unit.node_id), None)
            if node is None or node.kind is not ProductionNodeKind.JOIN:
                return None
            preparation = store.attempt_preparation(attempt.id)
            if preparation is None:
                raise RuntimeInvariantViolation("Join Attempt has no isolated workspace")
            if unit.source_baseline_id != attempt.source_baseline_id:
                raise RuntimeInvariantViolation("Join Attempt input baseline changed")
            parents = tuple(store.work_unit_for_node(plan.id, item) for item in node.dependency_ids)
            if any(parent is None or parent.verified_output_baseline_id is None for parent in parents):
                raise RuntimeInvariantViolation("Join parents are not verified")
            exact_ids = tuple(parent.verified_output_baseline_id for parent in parents)
            if unit.parent_baseline_ids != exact_ids:
                raise RuntimeInvariantViolation("Join parent baseline vector changed")
            snapshots = tuple(store.snapshot(item) for item in exact_ids)
            if any(item is None or item.repository_tree_identity is None for item in snapshots):
                raise RuntimeInvariantViolation("Join parent tree identity is unavailable")
            workspace = preparation.workspace
            previous_evidence = unit.reconciliation_evidence
        result = GitJoinReconciler().reconcile(
            repository=workspace.repository_path,
            workspace=workspace.workspace_path,
            input_revision=workspace.source_revision,
            parent_revisions=tuple(item.repository_revision for item in snapshots),
            parent_trees=tuple(item.repository_tree_identity for item in snapshots),
        )
        evidence: dict[str, object] = {
            "input_baseline_id": str(unit.source_baseline_id),
            "parent_baseline_ids": [str(item) for item in exact_ids],
            "parent_revisions": list(result.parent_revisions),
            "candidate_tree": result.candidate_tree,
            "strategy": result.strategy,
            "conflicts": list(result.conflicts),
            "evidence_digest": result.evidence_digest,
            "verification_state": "PENDING",
        }
        if previous_evidence is not None:
            if any(previous_evidence.get(key) != value for key, value in evidence.items() if key != "verification_state"):
                raise RuntimeInvariantViolation("Join restart observed different reconciliation Reality")
            return previous_evidence
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            current = store.work_unit(unit.id, for_update=True)
            if current is None or current.source_baseline_id != unit.source_baseline_id:
                raise RuntimeInvariantViolation("Join input changed during reconciliation")
            store.record_join_reconciliation(current, evidence)
            unit_of_work.commit()
        return evidence

    @staticmethod
    def _is_integration_checkpoint(graph, node_id: str) -> bool:
        if next(node for node in graph.nodes if node.node_id == node_id).kind is ProductionNodeKind.JOIN:
            return True
        joins = tuple(node for node in graph.nodes if node.kind is ProductionNodeKind.JOIN)
        by_id = {node.node_id: node for node in graph.nodes}

        def ancestors(identity: str) -> set[str]:
            result: set[str] = set()
            for dependency in by_id[identity].dependency_ids:
                result.add(dependency)
                result.update(ancestors(dependency))
            return result

        return not any(node_id in ancestors(join.node_id) for join in joins)

    def _activate_successors(self, store: RuntimeStore, plan_id: UUID) -> None:
        plan = store.plan_revision(plan_id)
        assert plan is not None and plan.graph is not None
        for node in plan.graph.nodes:
            if node.kind is ProductionNodeKind.GROUP or not node.dependency_ids:
                continue
            unit = store.work_unit_for_node(plan.id, node.node_id)
            if unit is None or unit.source_baseline_id is not None or unit.condition is not WorkUnitCondition.PROPOSED:
                continue
            parents = tuple(store.work_unit_for_node(plan.id, parent_id) for parent_id in node.dependency_ids)
            if any(parent is None or parent.verified_output_baseline_id is None for parent in parents):
                continue
            outputs = tuple(parent.verified_output_baseline_id for parent in parents)
            if node.kind is ProductionNodeKind.JOIN:
                baseline_id = self._common_baseline_ancestor(store, outputs)
            else:
                baseline_id = outputs[0]
            baseline = store.snapshot(baseline_id)
            assert baseline is not None
            contract = self._rebase_scoped_contract(
                unit.completion_contract, baseline.id, baseline.repository_revision,
            )
            store.bind_work_unit_input(unit, baseline_id, outputs, contract)
            self._append_transition(
                store, entity_type="PRODUCTION_WORK_UNIT", entity_id=unit.id,
                from_condition="DEPENDENCIES_PENDING", to_condition="INPUT_BASELINE_BOUND",
                reason="VERIFIED_PREDECESSORS_ACTIVATED", actor=RUNTIME_ACTOR,
                correlation=plan.id, timestamp=datetime.now(UTC),
            )

    @staticmethod
    def _common_baseline_ancestor(store: RuntimeStore, outputs: tuple[UUID, ...]) -> UUID:
        def lineage(identity: UUID) -> tuple[UUID, ...]:
            result = []
            while True:
                snapshot = store.snapshot(identity)
                if snapshot is None:
                    raise RuntimeInvariantViolation("parent baseline disappeared")
                result.append(snapshot.id)
                if snapshot.source_baseline_id is None:
                    return tuple(result)
                identity = snapshot.source_baseline_id

        first, *others = (lineage(identity) for identity in outputs)
        shared = set(first).intersection(*(set(item) for item in others))
        match = next((identity for identity in first if identity in shared), None)
        if match is None:
            raise RuntimeInvariantViolation("Join parents have no compatible ancestor baseline")
        return match

    @staticmethod
    def _rebase_scoped_contract(contract, baseline_id: UUID, revision: str):
        change = contract.change_contract
        artifact = contract.artifact_contract
        return contract.model_copy(update={
            "change_contract": None if change is None else change.model_copy(update={
                "source_baseline_id": baseline_id, "source_revision": revision,
            }),
            "artifact_contract": None if artifact is None else artifact.model_copy(update={
                "source_baseline_id": baseline_id, "source_revision": revision,
            }),
        })

    def create_initial_attempt(
        self,
        work_unit_id: UUID,
        request: AttemptRequest | None = None,
    ) -> ExecutionAttemptRecord:
        """Create Attempt generation 1 without dispatching an Executor."""

        return self._create_attempt(
            work_unit_id=work_unit_id,
            retry_of=None,
            request=request or AttemptRequest(),
        )

    def retry_attempt(
        self,
        attempt_id: UUID,
        request: AttemptRequest | None = None,
    ) -> ExecutionAttemptRecord:
        """Create a new Attempt identity and generation; never rewrite history."""

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            previous = store.attempt(attempt_id)
            if previous is None:
                raise RuntimeRecordNotFound(f"Attempt not found: {attempt_id}")
            work_unit = store.work_unit(previous.work_unit_id)
            if work_unit is None:
                raise RuntimeInvariantViolation("Attempt refers to a missing PWU")
            if previous.generation != work_unit.current_execution_generation:
                raise RuntimeInvariantViolation("only the current Attempt may be retried")
            supplied = request or AttemptRequest(
                context_ref=previous.context_ref,
                provider_ref=previous.provider_ref,
                workspace_ref=previous.workspace_ref,
            )
            return self._insert_attempt(
                unit_of_work,
                store,
                work_unit,
                supplied,
                retry_of=previous.id,
                reason="ATTEMPT_RETRY_CREATED",
            )

    def attempt_is_current(self, attempt_id: UUID) -> bool:
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            attempt = store.attempt(attempt_id)
            if attempt is None:
                raise RuntimeRecordNotFound(f"Attempt not found: {attempt_id}")
            work_unit = store.work_unit(attempt.work_unit_id)
            if work_unit is None:
                raise RuntimeInvariantViolation("Attempt refers to a missing PWU")
            return attempt.generation == work_unit.current_execution_generation

    def get_attempt(self, attempt_id: UUID) -> ExecutionAttemptRecord:
        with self.database.unit_of_work() as unit_of_work:
            attempt = RuntimeStore(unit_of_work.session).attempt(attempt_id)
            if attempt is None:
                raise RuntimeRecordNotFound(f"Attempt not found: {attempt_id}")
            return attempt

    def _create_attempt(
        self,
        *,
        work_unit_id: UUID,
        retry_of: UUID | None,
        request: AttemptRequest,
    ) -> ExecutionAttemptRecord:
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            work_unit = store.work_unit(work_unit_id)
            if work_unit is None:
                raise RuntimeRecordNotFound(f"PWU not found: {work_unit_id}")
            if work_unit.current_execution_generation != 0 or retry_of is not None:
                raise RuntimeInvariantViolation("initial Attempt already exists")
            return self._insert_attempt(
                unit_of_work,
                store,
                work_unit,
                request,
                retry_of=None,
                reason="INITIAL_ATTEMPT_CREATED",
            )

    def _insert_attempt(
        self,
        unit_of_work,
        store: RuntimeStore,
        work_unit,
        request: AttemptRequest,
        *,
        retry_of: UUID | None,
        reason: str,
        commit: bool = True,
    ) -> ExecutionAttemptRecord:
        run = store.run(work_unit.production_run_id)
        plan = store.plan_revision(work_unit.plan_revision_id)
        if run is None or plan is None:
            raise RuntimeInvariantViolation("PWU Run/Plan binding is incomplete")
        if work_unit.source_baseline_id is None:
            raise RuntimeInvariantViolation("PWU exact input baseline is unresolved")
        if (
            run.current_plan_revision_id != work_unit.plan_revision_id
            or plan.production_run_id != work_unit.production_run_id
            or (plan.graph is None and plan.source_baseline_id != work_unit.source_baseline_id)
            or (plan.graph is None and run.source_baseline_id != work_unit.source_baseline_id)
        ):
            raise RuntimeInvariantViolation("PWU Run/Plan/Baseline bindings do not match")
        if plan.graph is not None:
            node = next((item for item in plan.graph.nodes if item.node_id == work_unit.node_id), None)
            if node is None or node.kind is ProductionNodeKind.GROUP:
                raise RuntimeInvariantViolation("PWU is absent from active Production Plan")
            if node.dependency_ids:
                parents = tuple(store.work_unit_for_node(plan.id, item) for item in node.dependency_ids)
                if any(parent is None or parent.verified_output_baseline_id is None for parent in parents):
                    raise RuntimeInvariantViolation("PWU predecessors are not verified")
                exact_parents = tuple(parent.verified_output_baseline_id for parent in parents)
                if work_unit.parent_baseline_ids != exact_parents:
                    raise RuntimeInvariantViolation("PWU input does not match exact verified predecessors")
                if node.kind is ProductionNodeKind.PWU and work_unit.source_baseline_id != exact_parents[0]:
                    raise RuntimeInvariantViolation("serial successor input is not predecessor output")
            elif work_unit.source_baseline_id != (plan.graph.starting_baseline_id or plan.source_baseline_id):
                raise RuntimeInvariantViolation("root PWU does not consume exact plan baseline")

        timestamp = datetime.now(UTC)
        attempt_id = uuid4()
        generation = work_unit.current_execution_generation + 1
        if retry_of is not None and work_unit.condition not in {
            WorkUnitCondition.PROPOSED,
            WorkUnitCondition.PRODUCED,
        }:
            raise RuntimeInvariantViolation(
                "only an unfinished or produced PWU may create a retry Attempt"
            )
        store.advance_work_unit_generation(
            work_unit.id,
            expected_version=work_unit.version,
            generation=generation,
        )
        if retry_of is not None and work_unit.condition is WorkUnitCondition.PRODUCED:
            self._append_transition(
                store,
                entity_type="PRODUCTION_WORK_UNIT",
                entity_id=work_unit.id,
                from_condition=WorkUnitCondition.PRODUCED.value,
                to_condition=WorkUnitCondition.PROPOSED.value,
                reason="RETRY_REOPENED_WORK_UNIT",
                actor=RUNTIME_ACTOR,
                correlation=attempt_id,
                timestamp=timestamp,
            )
        store.insert_attempt(
            {
                "id": attempt_id,
                "work_unit_id": work_unit.id,
                "generation": generation,
                "plan_revision_id": work_unit.plan_revision_id,
                "source_baseline_id": work_unit.source_baseline_id,
                "context_ref": request.context_ref,
                "provider_ref": request.provider_ref,
                "workspace_ref": request.workspace_ref,
                "condition": AttemptCondition.CREATED.value,
                "retry_of": retry_of,
                "created_at": timestamp,
            }
        )
        self._append_transition(
            store,
            entity_type="EXECUTION_ATTEMPT",
            entity_id=attempt_id,
            from_condition=None,
            to_condition=AttemptCondition.CREATED.value,
            reason=reason,
            actor=RUNTIME_ACTOR,
            correlation=work_unit.id,
            timestamp=timestamp,
        )
        attempt = store.attempt(attempt_id)
        if attempt is None:
            raise RuntimeInvariantViolation("Attempt was not constructed")
        if commit:
            unit_of_work.commit()
        return attempt

    @staticmethod
    def _required_snapshot(store: RuntimeStore, snapshot_id: UUID) -> SnapshotRecord:
        snapshot = store.snapshot(snapshot_id)
        if snapshot is None:
            raise RuntimeInvariantViolation("Baseline pointer refers to a missing Snapshot")
        return snapshot

    @staticmethod
    def _required_spine(store: RuntimeStore, run_id: UUID) -> InitialRuntimeSpine:
        run = store.run(run_id)
        if run is None:
            raise RuntimeRecordNotFound(f"Run not found: {run_id}")
        plan = store.plan_revision(run.current_plan_revision_id)
        work_units = () if plan is None else store.work_units_for_plan(plan.id)
        work_unit = next((item for item in work_units if item.source_baseline_id is not None), None)
        if plan is None or work_unit is None:
            raise RuntimeInvariantViolation("Run spine is incomplete")
        if (
            plan.production_run_id != run.id
            or work_unit.production_run_id != run.id
            or work_unit.plan_revision_id != plan.id
            or plan.source_baseline_id != run.source_baseline_id
            or (plan.graph is None and work_unit.source_baseline_id != run.source_baseline_id)
        ):
            raise RuntimeInvariantViolation("Run spine bindings do not match")
        return InitialRuntimeSpine(run=run, plan_revision=plan, work_unit=work_unit)

    @staticmethod
    def _append_transition(
        store: RuntimeStore,
        *,
        entity_type: str,
        entity_id: UUID,
        from_condition: str | None,
        to_condition: str,
        reason: str,
        actor: str,
        correlation: UUID,
        timestamp: datetime,
    ) -> None:
        store.insert_transition(
            {
                "id": uuid4(),
                "entity_type": entity_type,
                "entity_identity": str(entity_id),
                "from_condition": from_condition,
                "to_condition": to_condition,
                "reason": reason,
                "actor_identity": actor,
                "correlation_identity": str(correlation),
                "created_at": timestamp,
            }
        )
