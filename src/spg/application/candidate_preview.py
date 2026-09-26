"""Governed Candidate Preview lifecycle over the Production Environment provider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import subprocess
import traceback
from threading import RLock, Thread
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import select

from spg.application.delivery import DeliveryApplicationService
from spg.application.production_environment import ProductionEnvironmentLifecycle
from spg.application.production_environment_contracts import (
    change_reality_v1_payload, guardian_assurance_intake_v1_payload,
    preview_reality_v1_payload,
)
from spg.domain.production_environment import (
    CandidatePreviewMode, CandidatePreviewSessionV1, EnvironmentConfiguration,
    EnvironmentLifecycleState, EnvironmentRuntimeState, LifecycleDecisionContext,
    PreviewRuntimeStatus, ProductionEnvironmentV1, ProductionWorkspaceV1,
    RepositoryAcquisitionPolicyV1, RepositoryAssetBinding,
    RepositoryBranchSelection, RuntimeConfiguration,
    DeliveryResultReference, EnvironmentProviderError, ProductionChangeReference, ProductionChangeType,
    ProductionDeliveryState, ProductionRecordV1, RepositoryRevisionReference,
    VerificationOutcome, VerificationResultReference,
)
from spg.infrastructure.candidate_preview_runtime import DockerCandidatePreviewRuntime
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore
from spg.infrastructure.persistence.delivery_schema import work_delivery_manifests, work_delivery_acceptances
from spg.infrastructure.persistence.runtime_schema import runtime_commits


class CandidatePreviewUnavailable(RuntimeError):
    pass


class CandidatePreviewApplicationService:
    """Current preview is keyed by Work and invalidated by exact Candidate lineage."""

    def __init__(self, delivery: DeliveryApplicationService,
        store: JsonProductionEnvironmentStore, provider: DockerCandidatePreviewRuntime) -> None:
        self.delivery = delivery
        self.store = store
        self.provider = provider
        self._lock = RLock()
        self._threads: dict[UUID, Thread] = {}
        self._lifecycle = ProductionEnvironmentLifecycle()

    def retention_decision(self, work_id: UUID, *,
                           hot_retention: timedelta = timedelta(days=30),
                           now: datetime | None = None) -> dict:
        """Keep exact Preview evidence; release only runtime after final review."""
        session = self.store.current_candidate_preview(work_id)
        if session is None:
            raise CandidatePreviewUnavailable("No Preview session exists for this Work")
        current_time = now or datetime.now(UTC)
        if session.status in {PreviewRuntimeStatus.STOPPED, PreviewRuntimeStatus.STALE}:
            classification, reason = "ARCHIVED", "Runtime stopped; immutable Preview evidence remains"
        elif session.status in {PreviewRuntimeStatus.REQUESTED, PreviewRuntimeStatus.PREPARING,
                                PreviewRuntimeStatus.BUILDING, PreviewRuntimeStatus.STARTING,
                                PreviewRuntimeStatus.STOPPING}:
            classification, reason = "ACTIVE", "Preview preparation or cleanup is active"
        else:
            with self.delivery.database.unit_of_work() as uow:
                reviewed = uow.session.execute(select(work_delivery_acceptances.c.id).select_from(
                    work_delivery_acceptances.join(work_delivery_manifests,
                        work_delivery_acceptances.c.manifest_id == work_delivery_manifests.c.id)
                    .join(runtime_commits,
                        work_delivery_manifests.c.runtime_commit_id == runtime_commits.c.id)
                ).where(work_delivery_manifests.c.work_id == work_id,
                        runtime_commits.c.candidate_id == session.candidate_id)).first() is not None
            if not reviewed:
                classification, reason = "RETAINED_FOR_REVIEW", "Exact Candidate has no final Human delivery decision"
            elif current_time - session.updated_at < hot_retention:
                classification, reason = "RETAINED_FOR_REVIEW", "Reviewed Preview remains in hot retention period"
            else:
                classification, reason = "ELIGIBLE_FOR_CLEANUP", "Final review recorded and hot retention expired"
        return {"preview_id": str(session.id), "work_id": str(work_id),
                "candidate_id": str(session.candidate_id),
                "classification": classification, "reason": reason,
                "runtime_action": "STOP" if classification == "ELIGIBLE_FOR_CLEANUP" else None,
                "evidence_action": "RETAIN"}

    def cleanup_expired(self, *, hot_retention: timedelta = timedelta(days=30),
                        limit: int = 100) -> list[dict]:
        results = []
        for session in self.store.list_current_candidate_previews()[:limit]:
            decision = self.retention_decision(session.work_id, hot_retention=hot_retention)
            if decision["classification"] != "ELIGIBLE_FOR_CLEANUP":
                continue
            with self._lock:
                current = self.store.current_candidate_preview(session.work_id)
                if current is None or current.id != session.id:
                    continue
                decision = self.retention_decision(session.work_id, hot_retention=hot_retention)
                if decision["classification"] != "ELIGIBLE_FOR_CLEANUP":
                    continue
                stopped = self.stop(session.work_id)
                results.append({**decision, "cleanup_result": "COMPLETED",
                                "retained_evidence_count": len(stopped.evidence)})
        return results

    @staticmethod
    def mode_for(context: dict) -> CandidatePreviewMode | None:
        repository = Path(context["repository_path"])
        revision = context["repository_revision"]
        required = ("Dockerfile", "pyproject.toml", "uv.lock", "docker/start_app.py", "alembic.ini")
        runtime_change = any(not path.startswith(("docs/", "benchmarks/"))
            and path not in {"README.md", "AI_context.md"}
            for path in context.get("artifacts", ()))
        if runtime_change:
            try:
                if all(subprocess.run(["git", "-C", str(repository), "cat-file", "-e",
                        f"{revision}:{path}"], check=False, capture_output=True, timeout=10).returncode == 0
                        for path in required):
                    return CandidatePreviewMode.FULL_APPLICATION_RUNTIME
                dockerfile = subprocess.run(["git", "-C", str(repository), "show",
                    f"{revision}:Dockerfile"], check=False, capture_output=True,
                    text=True, timeout=10)
                package = subprocess.run(["git", "-C", str(repository), "cat-file", "-e",
                    f"{revision}:package.json"], check=False, capture_output=True, timeout=10)
                if dockerfile.returncode == 0 and package.returncode == 0 and any(
                    line.strip().startswith("EXPOSE ") for line in dockerfile.stdout.splitlines()
                ):
                    return CandidatePreviewMode.FRONTEND_RUNTIME
            except (OSError, subprocess.SubprocessError):
                return None
        if context.get("entrypoint"):
            return CandidatePreviewMode.STATIC_PREVIEW
        return None

    def current(self, work_id: UUID) -> CandidatePreviewSessionV1 | None:
        with self._lock:
            session = self.store.current_candidate_preview(work_id)
            if session is None:
                return None
            self._project_reality(session)
            context = self.delivery.candidate_context(work_id)
            if context is None or context["candidate_fingerprint"] != session.candidate_fingerprint:
                return self._stale(session)
            if session.status is PreviewRuntimeStatus.READY:
                try:
                    ready = self.provider.probe(session.id, session.repository_revision,
                        session.repository_tree, mode=session.mode)
                except Exception as exc:
                    raise CandidatePreviewUnavailable(
                        "Preview runtime cannot currently be inspected; authorization is unavailable"
                    ) from exc
                if not ready:
                    cleanup = self.provider.stop(session.id) or {}
                    return self._fail(session, "RUNTIME_LOST",
                        "Preview services or exact revision are no longer ready", cleanup=cleanup)
            return session

    def request(self, work_id: UUID) -> CandidatePreviewSessionV1:
        with self._lock:
            context = self.delivery.candidate_context(work_id)
            if context is None:
                raise CandidatePreviewUnavailable("No current verified Candidate is available")
            mode = self.mode_for(context)
            if mode not in {CandidatePreviewMode.FULL_APPLICATION_RUNTIME, CandidatePreviewMode.FRONTEND_RUNTIME}:
                raise CandidatePreviewUnavailable("Candidate has no supported container runtime definition")
            previous = self.store.current_candidate_preview(work_id)
            if previous is not None:
                if previous.candidate_fingerprint == context["candidate_fingerprint"] and previous.status in {
                    PreviewRuntimeStatus.REQUESTED, PreviewRuntimeStatus.PREPARING,
                    PreviewRuntimeStatus.BUILDING, PreviewRuntimeStatus.STARTING,
                }:
                    return previous
                if previous.candidate_fingerprint == context["candidate_fingerprint"] and previous.status is PreviewRuntimeStatus.READY:
                    try:
                        if self.provider.probe(previous.id, previous.repository_revision,
                            previous.repository_tree, mode=previous.mode):
                            return previous
                    except EnvironmentProviderError as exc:
                        raise CandidatePreviewUnavailable(
                            "Preview runtime cannot currently be inspected; retry when runtime control is available"
                        ) from exc
                if previous.status not in {PreviewRuntimeStatus.STOPPED, PreviewRuntimeStatus.STALE}:
                    cleanup = self.provider.stop(previous.id) or {}
                    previous = self._advance(previous, PreviewRuntimeStatus.STALE if previous.candidate_fingerprint != context["candidate_fingerprint"]
                        else PreviewRuntimeStatus.STOPPED, endpoint=None,
                        failure_code="CANDIDATE_CHANGED" if previous.candidate_fingerprint != context["candidate_fingerprint"] else None,
                        evidence=previous.evidence + ({"kind": "REPLACED", "at": datetime.now(UTC).isoformat(),
                            **cleanup},))
                    self._destroy_environment(previous)
            now = datetime.now(UTC)
            session = CandidatePreviewSessionV1(
                id=uuid4(), work_id=work_id, candidate_id=UUID(context["candidate_id"]),
                candidate_fingerprint=context["candidate_fingerprint"],
                repository_identity=context["repository_identity"],
                repository_revision=context["repository_revision"],
                repository_tree=context["tree"], workspace_id=uuid4(),
                environment_id=uuid4(), mode=mode, status=PreviewRuntimeStatus.REQUESTED,
                definition_version=self.provider.definition_version if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME
                    else "frontend-docker-runtime-v1",
                created_at=now, updated_at=now,
            )
            source_branch = subprocess.run(["git", "-C", str(context["repository_path"]),
                "symbolic-ref", "--short", "HEAD"], capture_output=True, text=True,
                check=False, timeout=10).stdout.strip() or "candidate-source"
            workspace = ProductionWorkspaceV1(
                id=session.workspace_id, work_id=work_id,
                repository_assets=(RepositoryAssetBinding(
                    asset_id=uuid4(), repository_identity=session.repository_identity,
                    source=str(context["repository_path"]), branch=source_branch,
                    default_branch=source_branch, source_revision=session.repository_revision,
                    source_tree_identity=session.repository_tree,
                    acquisition_policy=RepositoryAcquisitionPolicyV1(
                        branch_selection=RepositoryBranchSelection.REPOSITORY_DEFAULT),
                    mount_path="/workspace/principal", writable=False,
                    provenance_reference=f"baseline-candidate:{session.candidate_id}"),),
                environment_configuration=EnvironmentConfiguration(
                    provider_profile="container-v1",
                    dependency_profile_reference=("candidate:pyproject.toml+uv.lock"
                        if mode is CandidatePreviewMode.FULL_APPLICATION_RUNTIME else "candidate:package.json"),
                    toolchain_references=("candidate:Dockerfile",),
                    lifecycle_policy_references=(self._lifecycle.policy.reference,)),
                runtime_configuration=RuntimeConfiguration(
                    runtime_profile=self.provider.definition_version,
                    preview_enabled=True, network_policy_reference="isolated-internal+fixed-gateway",
                    resource_policy_reference="candidate-preview:single-host-v1"),
                created_at=now,
            )
            environment = ProductionEnvironmentV1(
                id=session.environment_id, work_id=work_id,
                workspace_id=session.workspace_id,
                lifecycle_state=EnvironmentLifecycleState.CREATED,
                runtime_state=EnvironmentRuntimeState.NOT_PROVISIONED,
                created_at=now, updated_at=now,
            )
            self.store.create_workspace(workspace)
            self.store.create_environment(environment)
            self.store.replace_current_candidate_preview(session)
            self._project_reality(session)
            worker = Thread(target=self._prepare, args=(session.id, Path(context["repository_path"])),
                name=f"candidate-preview-{session.id}", daemon=True)
            self._threads[session.id] = worker
            worker.start()
            return session

    def stop(self, work_id: UUID) -> CandidatePreviewSessionV1:
        with self._lock:
            session = self.store.current_candidate_preview(work_id)
            if session is None:
                raise CandidatePreviewUnavailable("No Preview session exists for this Work")
            if session.status in {PreviewRuntimeStatus.STOPPED, PreviewRuntimeStatus.STALE}:
                return session
            if session.status in {PreviewRuntimeStatus.REQUESTED, PreviewRuntimeStatus.PREPARING,
                PreviewRuntimeStatus.BUILDING, PreviewRuntimeStatus.STARTING}:
                raise CandidatePreviewUnavailable("Preview preparation is still running; retry stop when it finishes")
            session = self._advance(session, PreviewRuntimeStatus.STOPPING, endpoint=None)
            cleanup = self.provider.stop(session.id) or {}
            stopped = self._advance(session, PreviewRuntimeStatus.STOPPED,
                evidence=session.evidence + ({"kind": "STOP", "at": datetime.now(UTC).isoformat(),
                    **cleanup},))
            self._destroy_environment(stopped)
            return stopped

    def require_ready(self, work_id: UUID, candidate_id: UUID) -> CandidatePreviewSessionV1:
        context = self.delivery.candidate_context(work_id)
        if context is None or UUID(context["candidate_id"]) != candidate_id:
            raise CandidatePreviewUnavailable("Candidate Preview no longer matches this Work")
        if self.mode_for(context) not in {CandidatePreviewMode.FULL_APPLICATION_RUNTIME, CandidatePreviewMode.FRONTEND_RUNTIME}:
            raise CandidatePreviewUnavailable("Functional Preview requirement has no supported runtime")
        session = self.current(work_id)
        if (session is None or session.status is not PreviewRuntimeStatus.READY
                or session.candidate_id != candidate_id
                or session.candidate_fingerprint != context["candidate_fingerprint"]):
            raise CandidatePreviewUnavailable("Exact Candidate functional Preview is not READY")
        return session

    def require_served_for_delivery(self, work_id: UUID, candidate_id: UUID,
        revision: str, tree: str) -> CandidatePreviewSessionV1:
        """Human acceptance needs the same exact, observed application runtime."""
        session = self.require_ready(work_id, candidate_id)
        if (session.mode is not CandidatePreviewMode.FULL_APPLICATION_RUNTIME
                or session.repository_revision != revision
                or session.repository_tree != tree
                or not any(item.get("kind") == "SERVED_VERIFICATION"
                    and item.get("result") == "PASS"
                    and item.get("candidate_revision") == revision
                    and item.get("candidate_tree") == tree
                    for item in session.evidence)):
            raise CandidatePreviewUnavailable(
                "Full application lacks exact served-runtime verification")
        return session

    def record_authorization(self, work_id: UUID, authority_identity: str) -> CandidatePreviewSessionV1:
        with self._lock:
            session = self.store.current_candidate_preview(work_id)
            if session is None or session.status is not PreviewRuntimeStatus.READY:
                raise CandidatePreviewUnavailable("Functional Preview disappeared before authorization evidence")
            return self._advance(session, PreviewRuntimeStatus.READY,
                evidence=session.evidence + ({"kind": "HUMAN_CANDIDATE_AUTHORIZATION",
                    "authority_identity": authority_identity,
                    "candidate_id": str(session.candidate_id),
                    "candidate_revision": session.repository_revision,
                    "preview_id": str(session.id),
                    "ready_session_version": session.version,
                    "readiness_evidence": tuple(item["kind"] for item in session.evidence
                        if item["kind"] in {"BUILD", "RUNTIME"}),
                    "production_record_reference": next((item["reference"]
                        for item in session.evidence if item["kind"] == "PRODUCTION_RECORD"), None),
                    "endpoint": session.endpoint,
                    "at": datetime.now(UTC).isoformat()},))

    def restore(self) -> None:
        directory = self.store.root / "candidate-previews" / "by-work"
        for pointer in directory.glob("*.json") if directory.exists() else ():
            session = None
            try:
                session = self.store.current_candidate_preview(UUID(pointer.stem))
                if session is None or session.status in {PreviewRuntimeStatus.STOPPED, PreviewRuntimeStatus.STALE, PreviewRuntimeStatus.FAILED}:
                    continue
                if session.status is PreviewRuntimeStatus.READY and self.provider.probe(
                    session.id, session.repository_revision, session.repository_tree, mode=session.mode,
                ):
                    continue
                cleanup = self.provider.stop(session.id) or {}
                self._fail(session, "RESTART_RECONCILIATION",
                    "Preview runtime was not READY after service restart", cleanup=cleanup)
            except EnvironmentProviderError:
                # Runtime observation is unavailable, not evidence of runtime loss.
                # Public current()/require_ready() fail closed until it can be probed.
                continue
            except Exception as exc:
                # A broken probe must never preserve a persisted READY projection.
                if session is not None:
                    try:
                        self._fail(session, "RESTART_RECONCILIATION",
                            f"Preview recovery failed: {type(exc).__name__}")
                    except Exception:
                        pass

    def _prepare(self, preview_id: UUID, repository: Path) -> None:
        try:
            with self._lock:
                session = self._required(preview_id)
                session = self._advance(session, PreviewRuntimeStatus.PREPARING)
                self._transition_environment(session, EnvironmentLifecycleState.INITIALIZING,
                    "Prepare exact Candidate Workspace")
            workspace = self.provider.prepare(preview_id, repository,
                session.repository_revision, session.repository_tree, mode=session.mode)
            with self._lock:
                session = self._advance(self._required(preview_id), PreviewRuntimeStatus.BUILDING,
                    evidence=({"kind": "WORKSPACE", **workspace},))
            build = self.provider.build(preview_id, session.repository_revision, session.repository_tree,
                mode=session.mode)
            with self._lock:
                session = self._advance(self._required(preview_id), PreviewRuntimeStatus.STARTING,
                    image_reference=build["image_id"],
                    evidence=self._required(preview_id).evidence + ({"kind": "BUILD", **build},))
            runtime = self.provider.start(preview_id, session.repository_revision, session.repository_tree,
                mode=session.mode)
            served_verifier = getattr(self.provider, "verify_served", None)
            served_evidence = (
                served_verifier(preview_id, session.repository_revision,
                    session.repository_tree, mode=session.mode)
                if callable(served_verifier) else None
            )
            with self._lock:
                latest_context = self.delivery.candidate_context(session.work_id)
                if latest_context is None or latest_context["candidate_fingerprint"] != session.candidate_fingerprint:
                    self._stale(self._required(preview_id))
                    return
                if not self.provider.probe(preview_id, session.repository_revision, session.repository_tree,
                    mode=session.mode):
                    raise CandidatePreviewUnavailable("Preview readiness or exact revision check failed")
                if served_evidence is not None:
                    session = self._advance(self._required(preview_id),
                        PreviewRuntimeStatus.STARTING,
                        evidence=self._required(preview_id).evidence + (
                            {"kind": "SERVED_VERIFICATION", **served_evidence},))
                self._transition_environment(self._required(preview_id), EnvironmentLifecycleState.ACTIVE,
                    "Candidate image and isolated application passed readiness",
                    provider_reference=build["image_id"],
                    artifact_references=(f"baseline-candidate:{session.candidate_id}",),
                    evidence_references=(build["build_log"],))
                record = self._record_preview_evidence(self._required(preview_id))
                self._advance(self._required(preview_id), PreviewRuntimeStatus.READY,
                    endpoint=runtime["endpoint"], service_identities=runtime["services"],
                    resource_references=runtime["resources"],
                    evidence=self._required(preview_id).evidence + (
                        {"kind": "RUNTIME", **runtime},
                        {"kind": "PRODUCTION_RECORD", "reference": f"production-record:{record.id}",
                            "digest": record.content_digest},
                    ))
        except Exception as exc:
            cleanup = {}
            try:
                cleanup = self.provider.stop(preview_id) or {}
            except Exception:
                pass
            with self._lock:
                current = self.store.get_candidate_preview(preview_id)
                if current is not None and current.status not in {PreviewRuntimeStatus.STALE, PreviewRuntimeStatus.STOPPED}:
                    stage = current.status
                    code, public_reason = {
                        PreviewRuntimeStatus.PREPARING: ("PREPARATION_FAILED", "Exact Candidate Workspace preparation failed"),
                        PreviewRuntimeStatus.BUILDING: ("BUILD_FAILED", "Candidate application build or image verification failed"),
                        PreviewRuntimeStatus.STARTING: ("STARTUP_FAILED", "Candidate application or required service failed readiness"),
                    }.get(stage, ("PREVIEW_FAILED", "Candidate functional Preview could not be prepared"))
                    detail = self.store.save_candidate_preview_failure_detail(
                        preview_id, traceback.format_exc())
                    self._fail(current, code, public_reason,
                        cleanup={**cleanup, "technical_evidence": detail})
        finally:
            with self._lock:
                self._threads.pop(preview_id, None)

    def _required(self, preview_id: UUID) -> CandidatePreviewSessionV1:
        session = self.store.get_candidate_preview(preview_id)
        if session is None:
            raise CandidatePreviewUnavailable("Preview session disappeared")
        return session

    def _advance(self, before: CandidatePreviewSessionV1, status: PreviewRuntimeStatus,
        **changes) -> CandidatePreviewSessionV1:
        after = CandidatePreviewSessionV1.model_validate({**before.model_dump(), **changes,
            "status": status, "version": before.version + 1, "updated_at": datetime.now(UTC)})
        advanced = self.store.advance_candidate_preview(before, after)
        self._project_reality(advanced)
        return advanced

    def _project_reality(self, session: CandidatePreviewSessionV1) -> None:
        self.store.save_candidate_preview_reality_evidence(
            session.id, session.version, preview_reality_v1_payload(session))

    def _fail(self, session: CandidatePreviewSessionV1, code: str, reason: str,
        *, cleanup: dict | None = None) -> CandidatePreviewSessionV1:
        failed = self._advance(session, PreviewRuntimeStatus.FAILED, endpoint=None,
            failure_code=code, failure_reason=reason,
            evidence=session.evidence + ({"kind": "FAILURE", "code": code, "reason": reason,
                "at": datetime.now(UTC).isoformat(), **(cleanup or {})},))
        self._destroy_environment(failed)
        return failed

    def _stale(self, session: CandidatePreviewSessionV1) -> CandidatePreviewSessionV1:
        if session.status is PreviewRuntimeStatus.STALE:
            return session
        cleanup = self.provider.stop(session.id) or {}
        stale = self._advance(session, PreviewRuntimeStatus.STALE, endpoint=None,
            failure_code="CANDIDATE_CHANGED", failure_reason="A newer Candidate superseded this Preview",
            evidence=session.evidence + ({"kind": "SUPERSESSION", "at": datetime.now(UTC).isoformat(),
                **cleanup},))
        self._destroy_environment(stale)
        return stale

    def _transition_environment(self, session: CandidatePreviewSessionV1,
        target: EnvironmentLifecycleState, reason: str, **changes) -> None:
        environment = self.store.get_environment(session.environment_id)
        if environment is None or environment.lifecycle_state is target:
            return
        after, transition = self._lifecycle.transition(environment, target=target,
            context=LifecycleDecisionContext(work_state="CANDIDATE_PREVIEW",
                human_review_pending=target is EnvironmentLifecycleState.ACTIVE,
                cleanup_authorized=target is EnvironmentLifecycleState.DESTROYED),
            actor_reference="watt:candidate-preview:v1", reason=reason,
            decided_at=datetime.now(UTC), **changes)
        self.store.apply_transition(environment, after, transition)

    def _destroy_environment(self, session: CandidatePreviewSessionV1) -> None:
        environment = self.store.get_environment(session.environment_id)
        if environment is None or environment.lifecycle_state is EnvironmentLifecycleState.DESTROYED:
            return
        if environment.lifecycle_state is EnvironmentLifecycleState.CREATED:
            self._transition_environment(session, EnvironmentLifecycleState.INITIALIZING,
                "Preview setup ended before provisioning")
        self._transition_environment(session, EnvironmentLifecycleState.ARCHIVED,
            "Preview resources stopped and evidence retained")
        self._transition_environment(session, EnvironmentLifecycleState.DESTROYED,
            "Preview resources removed after explicit stop or failure")

    def _record_preview_evidence(self, session: CandidatePreviewSessionV1) -> ProductionRecordV1:
        context = self.delivery.candidate_context(session.work_id)
        if context is None or context["candidate_fingerprint"] != session.candidate_fingerprint:
            raise CandidatePreviewUnavailable("Production Record Candidate lineage changed")
        repository = Path(context["repository_path"])
        changes = []
        diff = subprocess.run(["git", "-C", str(repository), "diff", "--name-status",
            "--no-renames", context["source_revision"], session.repository_revision, "--",
            *context["artifacts"]], check=True, capture_output=True, text=True,
            timeout=30).stdout
        change_types = {path: status for status, path in
            (line.split("\t", 1) for line in diff.splitlines() if "\t" in line)}
        for path in context["artifacts"]:
            status = change_types.get(path, "M")
            revision = context["source_revision"] if status == "D" else session.repository_revision
            blob = subprocess.run(["git", "-C", str(repository), "rev-parse",
                f"{revision}:{path}"], check=True, capture_output=True,
                text=True, timeout=10).stdout.strip()
            changes.append(ProductionChangeReference(
                repository_identity=session.repository_identity, path=path,
                change_type={"A": ProductionChangeType.ADDED,
                    "D": ProductionChangeType.DELETED}.get(status, ProductionChangeType.MODIFIED),
                artifact_reference=f"artifact:git-blob:{blob}"))
        now = datetime.now(UTC)
        record = ProductionRecordV1(
            id=uuid5(NAMESPACE_URL, f"watt:candidate-preview-production-record:{session.id}"),
            work_reference=f"work:{session.work_id}",
            task_contract_reference=context["task_contract_reference"],
            repository_revisions=(RepositoryRevisionReference(
                repository_identity=session.repository_identity,
                branch=context["target_branch"],
                before_revision=context["source_revision"],
                after_revision=session.repository_revision,
                diff_reference=f"{context['source_revision']}..{session.repository_revision}"),),
            environment_reference=f"production-environment:{session.environment_id}",
            changes=tuple(changes),
            verification_results=tuple(VerificationResultReference(
                reference=reference, outcome=VerificationOutcome.PASS)
                for reference in (
                    *context["verification_references"],
                    *((f"candidate-preview:{session.id}:served-runtime",)
                        if any(item.get("kind") == "SERVED_VERIFICATION"
                            and item.get("result") == "PASS" for item in session.evidence)
                        else ()),
                )),
            delivery_result=DeliveryResultReference(
                reference=f"candidate-preview:{session.id}",
                state=ProductionDeliveryState.READY_FOR_HUMAN_ACCEPTANCE),
            created_at=now,
        )
        record = self.store.save_production_record(record)
        change = change_reality_v1_payload(record,
            reality_id=uuid5(NAMESPACE_URL, f"watt:candidate-preview-change:{session.id}"),
            observed_at=now, source_reference=f"production-record:{record.id}",
            observed_by="watt:candidate-preview:v1")
        guardian = guardian_assurance_intake_v1_payload(record,
            intake_id=uuid5(NAMESPACE_URL, f"watt:candidate-preview-guardian:{session.id}"),
            submitted_by="watt:candidate-preview:v1", submitted_at=now)
        self.store.save_candidate_preview_boundary_evidence(session.id, change, guardian)
        return record
