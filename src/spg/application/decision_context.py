"""Watt's bounded consumer of canonical ECF v0.1 Decision Context.

The registry selects decisions; Git/Product/Work retain source truth. ECF owns
context contracts, selection and fingerprints. Watt owns admission and lineage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from uuid import UUID, NAMESPACE_URL, uuid5

from spg.domain.production_intelligence import (
    DecisionContextLineage,
    DecisionContextSourceTrace,
    ProtectedContextObligation,
)
from spg.domain.product import ProductInvariantViolation


POLICY_VERSION = "watt-ecf-decision-context-v1"
WORKSPACE_SURFACE = "WORKSPACE_PRODUCT_UI"
MANAGED_WEB_SURFACE = "MANAGED_PRODUCT_WEB_UI"
ECS_SURFACE = "ALIYUN_ECS_DELIVERY"
MILESTONE_SURFACE = "GOVERNED_MILESTONE_CLOSURE"
SESSION_SURFACE = "GOVERNED_SESSION_BOOTSTRAP"

_WORKSPACE_PATHS = frozenset((
    "src/spg/web/experience.js", "src/spg/web/experience.css",
    "src/spg/web/app.js", "src/spg/web/app.css",
    "tests/js/test_product_workspace_quadrants.cjs",
))
_ECS_PATHS = frozenset((
    "src/spg/application/cloud_delivery.py", "src/spg/domain/cloud_delivery.py",
    "src/spg/infrastructure/aliyun_cloud.py",
    "src/spg/infrastructure/cloud_delivery_network.py",
    "src/spg/infrastructure/cloud_delivery_commands.py",
    "src/spg/web/cloud_delivery.js",
))
_PROTECTED = frozenset((
    "PRODUCT_INTENT", "PRODUCT_INVARIANT", "APPROVED_CONSTRAINT",
    "APPROVED_DECISION",
))
_WORKSPACE_DOC = "docs/product/workspace-first-experience-principles.md"
_ECS_DOC = "docs/operations/aliyun-ecs-delivery.md"
_NORTH_STAR_DOC = "docs/architecture/watt-product-north-star.md"
_WATT_SOURCE_REMOTES = frozenset((
    "git@github.com:hengyizhiyuan/software-production-platform.git",
    "https://github.com/hengyizhiyuan/software-production-platform.git",
))


class DecisionContextNotReady(ProductInvariantViolation):
    def __init__(self, package) -> None:
        self.status = package.context_status.value
        self.missing_classes = tuple(item.value for item in package.missing_required_classes)
        self.stale_risks = package.stale_context_risks
        self.conflict_references = tuple(
            ref.context_id for conflict in package.conflicts for ref in conflict.provenance
        )
        self.package_fingerprint = package.fingerprint
        detail = []
        if self.missing_classes:
            detail.append("缺少 " + ", ".join(self.missing_classes))
        if self.stale_risks:
            detail.append("来源需要重新观察 " + ", ".join(self.stale_risks))
        if self.conflict_references:
            detail.append("冲突来源 " + ", ".join(self.conflict_references))
        super().__init__("决策上下文尚未就绪；" + "；".join(detail))


class DecisionContextChanged(ProductInvariantViolation):
    def __init__(self, old: str, new: str) -> None:
        self.condition = "DECISION_CONTEXT_CHANGED"
        self.previous_fingerprint = old
        self.current_fingerprint = new
        super().__init__("决策依据已变化，当前任务已停止执行并需要重新形成 Task Contract。"
                         f" 原指纹 {old}；当前指纹 {new}")


class DecisionContextAuthorityMissing(ProductInvariantViolation):
    pass


@dataclass(frozen=True)
class DecisionContextRequirement:
    surface: str
    product_id: UUID
    work_id: UUID | None
    subject: str
    repository_path: Path
    repository_revision: str
    repository_identity: str | None = None


@dataclass(frozen=True)
class MilestoneClosureReadiness:
    status: str
    context_status: str
    package_fingerprint: str
    missing_classes: tuple[str, ...]
    stale_risks: tuple[str, ...]
    conflict_references: tuple[str, ...]
    # Domain closure is deliberately absent. Human/Governance owns that decision.


class MilestoneClosureContextService:
    """Mandatory context precondition for a governed milestone closure review."""

    def __init__(self, database,
                 gateway: WattDecisionContextGateway | None = None) -> None:
        self.database = database
        self.gateway = gateway or WattDecisionContextGateway()

    def assess(self, requirement: DecisionContextRequirement, *,
               verification_record_ids: tuple[UUID, ...] = ()) -> MilestoneClosureReadiness:
        if requirement.surface != MILESTONE_SURFACE:
            raise ValueError("Milestone closure requires its registered ECF policy")
        from sqlalchemy import select
        from spg.domain.verification import VerificationResultValue
        from spg.infrastructure.persistence.product_schema import product_works
        from spg.infrastructure.persistence.runtime_store import RuntimeStore
        verified = []
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            for record_id in verification_record_ids:
                record = store.verification_record(record_id)
                if record is None or record.result is not VerificationResultValue.PASS:
                    continue
                work_unit = store.work_unit(record.work_unit_id)
                run = (None if work_unit is None else
                       store.run(work_unit.production_run_id))
                if run is None or not run.intent_ref.startswith("work:"):
                    continue
                try:
                    work_id = UUID(run.intent_ref.split(":")[1])
                except (ValueError, IndexError):
                    continue
                product_id = unit_of_work.session.execute(
                    select(product_works.c.product_id).where(
                        product_works.c.id == work_id)
                ).scalar_one_or_none()
                if (product_id == requirement.product_id
                        and (requirement.work_id is None or work_id == requirement.work_id)):
                    verified.append(f"{record.id}@{record.basis_fingerprint}")
        package = self.gateway.assemble(
            requirement, verification_statement=(
                "Verified exact records: " + ", ".join(sorted(verified))
                if verified else None
            ),
        )
        ready = package.context_status.value == "READY"
        return MilestoneClosureReadiness(
            status="CONTEXT_READY_FOR_GOVERNANCE" if ready
                   else "DECISION_CONTEXT_NOT_READY",
            context_status=package.context_status.value,
            package_fingerprint=package.fingerprint,
            missing_classes=tuple(item.value for item in package.missing_required_classes),
            stale_risks=package.stale_context_risks,
            conflict_references=tuple(
                ref.context_id for conflict in package.conflicts
                for ref in conflict.provenance
            ),
        )

    def assess_work_milestone(self, work_id: UUID) -> MilestoneClosureReadiness:
        """Read the current Product/Work/source/evidence; never mutate closure."""
        from sqlalchemy import select
        from spg.infrastructure.persistence.product_schema import (
            product_managed_sources, product_works,
        )
        from spg.infrastructure.persistence.product_store import ProductStore
        from spg.infrastructure.persistence.runtime_store import RuntimeStore

        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            work = product.work(work_id)
            product_id = unit_of_work.session.execute(
                select(product_works.c.product_id).where(product_works.c.id == work_id)
            ).scalar_one_or_none()
            resource = product.resource_for_work(work_id)
            if work is None or product_id is None or resource is None:
                raise DecisionContextAuthorityMissing(
                    "DECISION_CONTEXT_NOT_READY: exact Product/Work/Repository missing"
                )
            accepted = unit_of_work.session.execute(
                select(product_managed_sources).where(
                    product_managed_sources.c.product_id == product_id,
                    product_managed_sources.c.repository_identity ==
                        resource.repository_identity,
                )
            ).mappings().first()
            if accepted is None:
                raise DecisionContextAuthorityMissing(
                    "DECISION_CONTEXT_NOT_READY: accepted Product source missing"
                )
            binding = product.runtime_binding(work_id)
            summary = None if binding is None else product.runtime_summary(binding)
            runtime = RuntimeStore(unit_of_work.session)
            candidate = (None if summary is None or summary.candidate_id is None
                         else runtime.baseline_candidate(summary.candidate_id))
            verification_ids = (() if candidate is None else
                                candidate.verification_record_ids)
            revision = accepted["accepted_revision"]
        requirement = DecisionContextRequirement(
            surface=MILESTONE_SURFACE, product_id=product_id, work_id=work_id,
            subject=f"milestone:work:{work_id}",
            repository_path=Path(resource.location_ref),
            repository_revision=revision,
            repository_identity=resource.repository_identity,
        )
        return self.assess(requirement,
                           verification_record_ids=tuple(verification_ids))


def policy_for_targets(paths: tuple[str, ...]) -> str | None:
    """Only exact registered source boundaries activate the v0.1 task gate."""
    normalized = frozenset(paths)
    selected = set()
    if normalized & _WORKSPACE_PATHS:
        selected.add(WORKSPACE_SURFACE)
    if normalized & _ECS_PATHS:
        selected.add(ECS_SURFACE)
    if len(selected) > 1:
        raise ValueError("A single Task Contract cannot cross ECF decision policies")
    return next(iter(selected), None)


def lineage_for_work_task(database, *, work_id: UUID,
                          repository_identity: str,
                          repository_path: Path,
                          repository_revision: str,
                          target_paths: tuple[str, ...]) -> DecisionContextLineage | None:
    """Resolve exact Product and current Work Reality before a Task is formed."""
    try:
        remote = _git(repository_path, "remote", "get-url", "origin")
    except ValueError:
        return None
    watt_source = remote in _WATT_SOURCE_REMOTES
    surface = policy_for_targets(target_paths) if watt_source else None
    if not watt_source and target_paths and all(
        Path(path).suffix.lower() in {".html", ".css", ".js"}
        for path in target_paths
    ):
        surface = MANAGED_WEB_SURFACE
    if surface is None:
        return None
    from sqlalchemy import select
    from spg.infrastructure.persistence.product_schema import (
        engineering_resources, product_managed_sources, product_works,
        work_source_bases,
    )
    from spg.infrastructure.persistence.product_store import ProductStore

    with database.unit_of_work() as unit_of_work:
        product_id = unit_of_work.session.execute(
            select(product_works.c.product_id).where(product_works.c.id == work_id)
        ).scalar_one_or_none()
        if watt_source:
            source_owner = unit_of_work.session.execute(
                select(product_managed_sources.c.product_id).where(
                    product_managed_sources.c.repository_identity == repository_identity)
            ).scalar_one_or_none()
        else:
            source_owner = unit_of_work.session.execute(
                select(work_source_bases.c.product_id)
                .join(engineering_resources,
                      engineering_resources.c.id == work_source_bases.c.resource_id)
                .join(product_managed_sources,
                      product_managed_sources.c.product_id == work_source_bases.c.product_id)
                .where(work_source_bases.c.work_id == work_id,
                       engineering_resources.c.repository_identity == repository_identity,
                       product_managed_sources.c.provider_kind == "gitea")
            ).scalar_one_or_none()
            exact = unit_of_work.session.execute(select(work_source_bases.c.source_revision).where(
                work_source_bases.c.work_id == work_id)).scalar_one_or_none()
            if exact != repository_revision:
                from spg.application.multi_pwu_lineage import work_consumes_revision
                if not work_consumes_revision(unit_of_work.session, work_id, repository_identity, repository_revision):
                    source_owner = None
        work = ProductStore(unit_of_work.session).work(work_id)
    if product_id is None or work is None or source_owner != product_id:
        raise DecisionContextAuthorityMissing(
            "DECISION_CONTEXT_NOT_READY: exact Product/Work source authority missing"
        )
    work_statement, revision = _work_basis(work)
    requirement = DecisionContextRequirement(
        surface=surface, product_id=product_id, work_id=work_id,
        subject="|".join(sorted(target_paths)),
        repository_path=repository_path,
        repository_revision=repository_revision,
        repository_identity=repository_identity,
    )
    gateway = WattDecisionContextGateway()
    package = gateway.require_ready(requirement,
                                    work_statement=work_statement,
                                    work_revision=revision)
    return gateway.lineage(package, requirement)


def _work_basis(work) -> tuple[str, str]:
    statement = json.dumps({
        "desired_outcome": work.desired_outcome,
        "production_objective": work.production_objective,
        "constraints": list(work.constraints),
    }, ensure_ascii=False, sort_keys=True)
    revision = (str(work.current_work_reality_revision_id)
                if work.current_work_reality_revision_id else
                sha256(statement.encode()).hexdigest())
    return statement, revision


def assert_task_context_fresh(database, task) -> None:
    """Fail before an Executor effect if current governed context has changed."""
    lineage = task.decision_context
    if lineage is None:
        return
    if lineage.work_id is None:
        raise ValueError("Gated Task Contract requires exact Work")
    from spg.infrastructure.persistence.product_store import ProductStore
    from spg.infrastructure.persistence.product_schema import (
        engineering_resources, product_managed_sources, product_works,
        work_source_bases,
    )
    from sqlalchemy import select
    with database.unit_of_work() as unit_of_work:
        work = ProductStore(unit_of_work.session).work(UUID(lineage.work_id))
        current_product_id = unit_of_work.session.execute(
            select(product_works.c.product_id).where(
                product_works.c.id == UUID(lineage.work_id))
        ).scalar_one_or_none()
        if lineage.repository_identity is None:
            current_source_owner = None
        elif lineage.surface == MANAGED_WEB_SURFACE:
            current_source_owner = unit_of_work.session.execute(
                select(work_source_bases.c.product_id)
                .join(engineering_resources,
                      engineering_resources.c.id == work_source_bases.c.resource_id)
                .join(product_managed_sources,
                      product_managed_sources.c.product_id == work_source_bases.c.product_id)
                .where(work_source_bases.c.work_id == UUID(lineage.work_id),
                       engineering_resources.c.repository_identity == lineage.repository_identity,
                       product_managed_sources.c.provider_kind == "gitea")
            ).scalar_one_or_none()
            exact = unit_of_work.session.execute(select(work_source_bases.c.source_revision).where(
                work_source_bases.c.work_id == UUID(lineage.work_id))).scalar_one_or_none()
            if exact != lineage.repository_revision:
                from spg.application.multi_pwu_lineage import work_consumes_revision
                if not work_consumes_revision(unit_of_work.session, UUID(lineage.work_id), lineage.repository_identity, lineage.repository_revision):
                    current_source_owner = None
        else:
            current_source_owner = unit_of_work.session.execute(
                select(product_managed_sources.c.product_id).where(
                    product_managed_sources.c.repository_identity == lineage.repository_identity)
            ).scalar_one_or_none()
    if work is None:
        raise DecisionContextChanged(lineage.package_fingerprint, "missing-work")
    if (current_product_id != UUID(lineage.product_id)
            or (lineage.repository_identity is not None and
                current_source_owner != current_product_id)):
        raise DecisionContextChanged(lineage.package_fingerprint, "authority-changed")
    statement, revision = _work_basis(work)
    WattDecisionContextGateway().assert_fresh(
        lineage, work_statement=statement, work_revision=revision,
    )


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *args], capture_output=True, text=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(f"Governed Git source unavailable: {' '.join(args)}")
    return result.stdout.strip()


def _section(document: str, heading: str) -> str | None:
    lines = document.splitlines()
    start = next((index for index, line in enumerate(lines)
                  if line.strip() == heading), None)
    if start is None:
        return None
    level = len(heading) - len(heading.lstrip("#"))
    end = next((index for index in range(start + 1, len(lines))
                if lines[index].startswith("#")
                and len(lines[index]) - len(lines[index].lstrip("#")) <= level), len(lines))
    return "\n".join(lines[start:end]).strip()


class WattDecisionContextGateway:
    """Project current Watt-owned sources and call the independent ECF owner."""

    @staticmethod
    def _ecf():
        try:
            import ecf.decision_context as ecf
        except ImportError as error:
            raise RuntimeError("ECF v0.1 owner unavailable for required decision") from error
        if ecf.VERSION != "0.1":
            raise RuntimeError("ECF Decision Context owner version is incompatible")
        return ecf

    def assemble(self, requirement: DecisionContextRequirement, *,
                 work_statement: str | None = None,
                 work_revision: str | None = None,
                 verification_statement: str | None = None,
                 open_gap_statement: str | None = None):
        ecf = self._ecf()
        policy = {
            WORKSPACE_SURFACE: (ecf.ConsumerRole.PRODUCT_DESIGN,
                                ecf.DecisionType.PRODUCT_UI_CHANGE),
            MANAGED_WEB_SURFACE: (ecf.ConsumerRole.PRODUCT_DESIGN,
                                  ecf.DecisionType.PRODUCT_UI_CHANGE),
            ECS_SURFACE: (ecf.ConsumerRole.ARCHITECTURE_DESIGN,
                          ecf.DecisionType.DELIVERY_CAPABILITY_DESIGN),
            MILESTONE_SURFACE: (ecf.ConsumerRole.GOVERNANCE_CLOSURE,
                                ecf.DecisionType.MILESTONE_CLOSURE),
            SESSION_SURFACE: (ecf.ConsumerRole.SESSION_HANDOFF,
                              ecf.DecisionType.SESSION_BOOTSTRAP),
        }.get(requirement.surface)
        if policy is None:
            raise ValueError("Unregistered Decision Context surface")
        scope = ecf.DecisionScope(
            project_id="watt", product_id=str(requirement.product_id),
            work_id=str(requirement.work_id) if requirement.work_id else None,
            subject=requirement.subject,
        )
        owners = ecf.AuthorityContext(
            product_owner="WATT_PRODUCT_GOVERNOR",
            architecture_owner="WATT_ARCHITECTURE_GOVERNOR",
            governance_owner="WATT_GOVERNANCE_GOVERNOR",
            repository_owner="WATT_REPOSITORY",
            work_owner="WATT_WORK",
            verification_owner="WATT_VERIFICATION",
            guardian_owner="GUARDIAN",
        )
        request = ecf.DecisionContextRequest(
            request_id=f"{POLICY_VERSION}:{requirement.surface}:"
                       f"{requirement.product_id}:{requirement.work_id}:"
                       f"{requirement.subject}",
            consumer_role=policy[0], decision_type=policy[1],
            scope=scope, authority_context=owners, as_of=date.today(),
        )
        records = []
        product_scope = ecf.DecisionScope("watt", str(requirement.product_id))
        repo_scope = ecf.DecisionScope("watt", str(requirement.product_id))

        def add(context_id: str, context_class, key: str, record_scope,
                ref: str, revision: str, owner: str, content: dict[str, str],
                provenance: str, *, supersedes: tuple[str, ...] = ()) -> None:
            records.append(ecf.GovernedContextRecord(
                context_id=context_id, classes=(context_class,), semantic_key=key,
                scope=record_scope,
                source=ecf.SourceIdentity(ref=ref, revision=revision,
                    authority_owner=owner, authority_ref=f"governed:{ref}",
                    provenance=provenance), content=content, supersedes=supersedes,
            ))

        def document_record(path: str, heading: str, context_class, key: str,
                            field: str, owner: str, record_scope=product_scope,
                            second_field: str | None = None) -> None:
            try:
                body = _git(requirement.repository_path, "show",
                            f"{requirement.repository_revision}:{path}")
                excerpt = _section(body, heading)
                if not excerpt:
                    return
                blob = _git(requirement.repository_path, "rev-parse",
                            f"{requirement.repository_revision}:{path}")
            except ValueError:
                return
            add(f"{requirement.product_id}:{key}", context_class, key,
                record_scope, f"git:{path}", blob, owner,
                {field: excerpt, **({second_field: excerpt} if second_field else {})},
                f"git:{requirement.repository_revision}:{path}#{heading}")

        if requirement.surface == WORKSPACE_SURFACE:
            document_record(_WORKSPACE_DOC, "## 2. Core product thesis",
                ecf.ContextClass.PRODUCT_INTENT, "workspace-intent", "intent",
                owners.product_owner)
            document_record(_WORKSPACE_DOC, "## 11. Workspace Four-Quadrant Invariant",
                ecf.ContextClass.PRODUCT_INVARIANT, "workspace-four-quadrants",
                "invariant", owners.product_owner)
            document_record(_WORKSPACE_DOC, "## 1. Status, authority, and scope",
                ecf.ContextClass.APPROVED_DECISION, "workspace-governor-decision",
                "decision", owners.governance_owner)
            document_record("docs/product/workspace-first-experience-principles.md",
                "## 4. Workspace is a product projection",
                ecf.ContextClass.APPROVED_CONSTRAINT, "workspace-boundary",
                "constraint", owners.architecture_owner)
        elif requirement.surface == MANAGED_WEB_SURFACE:
            for heading, context_class, key, field, owner in (
                ("## Product Intent", ecf.ContextClass.PRODUCT_INTENT,
                 "managed-product-intent", "intent", owners.product_owner),
                ("## Product Invariant", ecf.ContextClass.PRODUCT_INVARIANT,
                 "managed-product-invariant", "invariant", owners.product_owner),
                ("## Approved Decision", ecf.ContextClass.APPROVED_DECISION,
                 "managed-product-decision", "decision", owners.governance_owner),
            ):
                document_record("README.md", heading, context_class, key,
                                field, owner)
        elif requirement.surface == ECS_SURFACE:
            document_record(_ECS_DOC, "## Product Intent",
                ecf.ContextClass.PRODUCT_INTENT, "ecs-automatic-delivery",
                "intent", owners.product_owner)
            document_record(_ECS_DOC, "## Approved Safety Constraint",
                ecf.ContextClass.APPROVED_CONSTRAINT, "ecs-governed-cloud-effects",
                "constraint", owners.architecture_owner)
        elif requirement.surface == MILESTONE_SURFACE:
            document_record(_NORTH_STAR_DOC, "## 1. Product identity",
                ecf.ContextClass.PRODUCT_NORTH_STAR, "watt-north-star",
                "north_star", owners.product_owner)
            document_record(_NORTH_STAR_DOC, "## 5. Closed-loop software production",
                ecf.ContextClass.PRODUCT_INTENT, "watt-product-intent",
                "intent", owners.product_owner)
            document_record(_WORKSPACE_DOC, "## 11. Workspace Four-Quadrant Invariant",
                ecf.ContextClass.PRODUCT_INVARIANT, "workspace-four-quadrants",
                "invariant", owners.product_owner)
            document_record(_NORTH_STAR_DOC, "## 9. Product-shape essentials and legitimate deferrals",
                ecf.ContextClass.REQUIRED_VS_DEFERRED_BOUNDARY,
                "watt-required-deferred", "required", owners.product_owner,
                second_field="deferred")
            document_record(_NORTH_STAR_DOC, "## 10. Open decisions",
                ecf.ContextClass.OPEN_GAP, "watt-open-decisions",
                "statement", owners.governance_owner)
        if requirement.surface != SESSION_SURFACE:
            try:
                tree = _git(requirement.repository_path, "rev-parse",
                            f"{requirement.repository_revision}^{{tree}}")
                add(f"{requirement.product_id}:repository:{requirement.subject}",
                    ecf.ContextClass.REPOSITORY_REALITY, "repository-revision",
                    repo_scope, f"git:repository:{requirement.repository_path}",
                    requirement.repository_revision, owners.repository_owner,
                    {"statement": f"Repository tree {tree}"},
                    f"git:{requirement.repository_revision}")
            except ValueError:
                pass
        if work_statement and work_revision and requirement.work_id:
            add(f"{requirement.work_id}:work-reality",
                ecf.ContextClass.WORK_REALITY, "work-reality",
                ecf.DecisionScope("watt", str(requirement.product_id),
                                  str(requirement.work_id)),
                f"work:{requirement.work_id}", work_revision, owners.work_owner,
                {"statement": work_statement}, f"work-reality:{work_revision}")
        if verification_statement:
            digest = sha256(verification_statement.encode()).hexdigest()
            add(f"{requirement.product_id}:verification:{requirement.subject}",
                ecf.ContextClass.VERIFICATION_EVIDENCE, "milestone-verification",
                product_scope, f"verification:{requirement.subject}", digest,
                owners.verification_owner, {"statement": verification_statement},
                f"verification:{digest}")
        if open_gap_statement:
            digest = sha256(open_gap_statement.encode()).hexdigest()
            add(f"{requirement.product_id}:open-gap:{requirement.subject}",
                ecf.ContextClass.OPEN_GAP, "milestone-open-gap", product_scope,
                f"governance:open-gap:{requirement.subject}", digest,
                owners.governance_owner, {"statement": open_gap_statement},
                f"governance:{digest}")
        return ecf.assemble_context(request, ecf.SourceSnapshot(tuple(records)))

    def require_ready(self, requirement: DecisionContextRequirement, **source):
        package = self.assemble(requirement, **source)
        self.ensure_ready(package)
        return package

    @staticmethod
    def ensure_ready(package) -> None:
        if package.context_status.value != "READY":
            raise DecisionContextNotReady(package)

    @staticmethod
    def lineage(package, requirement: DecisionContextRequirement) -> DecisionContextLineage:
        obligations = []
        for selected in package.selected:
            record = selected.record
            for context_class in selected.classes:
                if context_class.value not in _PROTECTED:
                    continue
                content = "\n".join(record.content.values())
                obligations.append(ProtectedContextObligation(
                    context_class=context_class.value,
                    semantic_key=record.semantic_key,
                    source_ref=record.source.ref,
                    source_revision=record.source.revision,
                    authority=record.source.authority_owner,
                    content_digest=sha256(content.encode()).hexdigest(),
                    content=content,
                    package_fingerprint=package.fingerprint,
                    verification_ref=("tests/js/test_product_workspace_quadrants.cjs"
                                      if record.semantic_key == "workspace-four-quadrants"
                                      else None),
                ))
        return DecisionContextLineage(
            version=package.version, contract_id=package.contract.contract_id,
            request_id=package.request.request_id,
            package_fingerprint=package.fingerprint,
            surface=requirement.surface, product_id=str(requirement.product_id),
            work_id=str(requirement.work_id) if requirement.work_id else None,
            subject=requirement.subject,
            repository_path=str(requirement.repository_path),
            repository_identity=requirement.repository_identity,
            repository_revision=requirement.repository_revision,
            source_references=tuple(
                f"{trace.source.ref}@{trace.source.revision}"
                for trace in package.generated_from
            ),
            generated_from=tuple(DecisionContextSourceTrace(
                context_id=trace.context_id,
                source_ref=trace.source.ref,
                source_revision=trace.source.revision,
                authority=trace.source.authority_owner,
                authority_ref=trace.source.authority_ref,
                provenance=trace.source.provenance,
                product_id=trace.scope.product_id,
                work_id=trace.scope.work_id,
                subject=trace.scope.subject,
            ) for trace in package.generated_from),
            protected_obligations=tuple(obligations),
        )

    def assert_fresh(self, lineage: DecisionContextLineage, *,
                     work_statement: str | None = None,
                     work_revision: str | None = None) -> None:
        repository = Path(lineage.repository_path)
        current = _git(repository, "rev-parse", "HEAD")
        requirement = DecisionContextRequirement(
            surface=lineage.surface, product_id=UUID(lineage.product_id),
            work_id=UUID(lineage.work_id) if lineage.work_id else None,
            subject=lineage.subject, repository_path=repository,
            repository_revision=current,
            repository_identity=lineage.repository_identity,
        )
        package = self.assemble(requirement, work_statement=work_statement,
                                work_revision=work_revision)
        if package.context_status.value != "READY" or package.fingerprint != lineage.package_fingerprint:
            raise DecisionContextChanged(lineage.package_fingerprint,
                                         package.fingerprint)
