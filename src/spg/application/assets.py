"""Repository observations are evidence; Work admission remains Work-owned."""
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit, urlunsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import insert, select, text, update

from spg.application.runtime import RuntimeService
from spg.application.connectors import ConnectorResolver
from spg.application.native_git_operations import NativeGitOperationRunner
from spg.application.managed_git_source import ManagedGitSource
from spg.application.github_delivery import GitHubDeliveryService
from spg.config import Settings
from spg.application.repository_branch_authority import governed_branch_creation_target
from spg.application.work import WorkApplicationService
from spg.domain.assets import (
    AssetScopeAdmissionRequest,
    RepositoryAcquisitionFailure,
    RepositoryAcquisitionFailureCategory,
    RepositoryIntakeRequest,
)
from spg.domain.connectors import CapabilityRequirement
from spg.domain.action_admission import ActionFacts, ActionFamily, admit_action
from spg.domain.repository_actions import repository_actions
from spg.domain.interaction import InteractionActor
from spg.domain.engineering_semantics import current_semantic_facts
from spg.domain.preparation import ContextSemanticRole
from spg.domain.product import EngineeringContextReference, ProductInvariantViolation, ProductRecordNotFound
from spg.domain.runtime import BootstrapRequest
from spg.infrastructure.persistence.asset_schema import repository_intakes
from spg.infrastructure.persistence.product_schema import engineering_resources
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.interaction_store import InteractionStore
from spg.infrastructure.production_environment import GitRepositoryAcquirer


def canonical_fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


class RepositoryAssetService:
    _MANAGED_REPOSITORY_EXCLUDES = (
        "__pycache__/",
        "*.py[cod]",
        ".pytest_cache/",
    )

    def __init__(
        self,
        database,
        asset_root: Path,
        import_root: Path,
        repository_acquirer: GitRepositoryAcquirer | None = None,
        native_git_operations: NativeGitOperationRunner | None = None,
        settings: Settings | None = None,
    ):
        self.database = database
        self.asset_root = asset_root.resolve()
        self.import_root = import_root.resolve()
        self.repository_acquirer = repository_acquirer or GitRepositoryAcquirer()
        self.native_git_operations = native_git_operations
        self.managed_source = ManagedGitSource(database)
        self.github_delivery = GitHubDeliveryService(database, settings or Settings())

    @contextmanager
    def _lock(self, identity):
        key = int(sha256(identity.encode()).hexdigest()[:15], 16)
        with self.database.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": key})
            try:
                yield
            finally:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})

    @staticmethod
    def _git(path, *args):
        try:
            return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(path), *args],
                check=True, capture_output=True, timeout=90).stdout.decode("utf-8").strip()
        except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
            raise ProductInvariantViolation("Repository operation failed; inspect the intake receipt and repository availability") from exc

    def _source(self, source):
        if source is None:
            return None
        url = urlsplit(source)
        if url.scheme in {"http", "https"}:
            if not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ProductInvariantViolation("Use a Git HTTPS address without embedded credentials, query or fragment")
            return urlunsplit((url.scheme, url.netloc.lower(), url.path.rstrip("/"), "", ""))
        path = Path(source).resolve()
        if not path.is_relative_to(self.import_root) or not path.is_dir():
            raise ProductInvariantViolation("Local repository imports must be inside the configured import directory")
        return str(path)

    @staticmethod
    def _identity(source: str | None, request: RepositoryIntakeRequest) -> str:
        if request.operation_kind in {"CREATE_BRANCH", "CREATE_BRANCH_ONLY", "SWITCH_BRANCH"}:
            branch_digest = sha256(
                (f"{source}:{request.operation_kind}:{request.target_branch}:{request.base_resource_id}"
                 + (f":{request.expected_base_revision}:{request.expected_base_tree}"
                    if request.expected_base_revision is not None else "")).encode("utf-8")
            ).hexdigest()[:20]
            return f"watt://work-branches/{request.work_id or request.interaction_id}/{branch_digest}"
        return source or f"watt://repositories/{request.request_id}"

    @staticmethod
    def _attempt_metadata(request: RepositoryIntakeRequest) -> dict[str, object]:
        return {
            "interaction_id": (
                None if request.interaction_id is None else str(request.interaction_id)
            ),
            "work_id": None if request.work_id is None else str(request.work_id),
            "attempt_number": request.attempt_number,
            "previous_attempt_id": (
                None
                if request.previous_attempt_id is None
                else str(request.previous_attempt_id)
            ),
            "operation_kind": request.operation_kind,
            "target_branch": request.target_branch,
            "base_resource_id": (
                None if request.base_resource_id is None
                else str(request.base_resource_id)
            ),
        }

    def start_intake(self, request: RepositoryIntakeRequest) -> dict:
        """Persist an acquisition operation before any Git effect is attempted."""

        if request.source_record_id is not None:
            self._require_interaction_authority(request)
        if request.operation_kind in {"CREATE_BRANCH", "CREATE_BRANCH_ONLY", "SWITCH_BRANCH"}:
            self._require_current_branch_authority(request)
        source = self._source(request.source)
        identity = self._identity(source, request)
        payload = request.model_dump(mode="json")
        with self._lock(identity):
            with self.database.unit_of_work() as uow:
                row = uow.session.execute(select(repository_intakes).where(repository_intakes.c.id == request.request_id)).mappings().one_or_none()
                if row is not None:
                    if RepositoryIntakeRequest.model_validate(row["request"]) != request:
                        raise ProductInvariantViolation("Intake request identity already belongs to a different request")
                    if row["observation"] is not None:
                        return row["observation"]
                else:
                    uow.session.execute(
                        insert(repository_intakes).values(
                            id=request.request_id,
                            request=payload,
                            created_at=datetime.now(UTC),
                        )
                    )
                requested = {
                    "resource_id": None,
                    "repository_identity": identity,
                    "repository_ref": None,
                    "revision": None,
                    "tree": None,
                    "paths": [],
                    "context_path": None,
                    "observed_at": datetime.now(UTC).isoformat(),
                    "source": source,
                    "title": request.title,
                    "description": request.description,
                    "intake_request_id": str(request.request_id),
                    "condition": "REQUESTED",
                    "failure_category": None,
                    "human_message": (
                        f"Local branch {request.target_branch} creation has been requested."
                        if request.operation_kind in {"CREATE_BRANCH", "CREATE_BRANCH_ONLY", "SWITCH_BRANCH"}
                        else "Repository acquisition has been requested."
                    ),
                    "technical_evidence": None,
                    **self._attempt_metadata(request),
                }
                requested["fingerprint"] = canonical_fingerprint(requested)
                uow.session.execute(
                    update(repository_intakes)
                    .where(repository_intakes.c.id == request.request_id)
                    .values(observation=requested)
                )
                uow.commit()
                return requested

    def _require_current_branch_authority(self, request: RepositoryIntakeRequest) -> None:
        """A branch request must be backed by current, admitted Human Work truth."""

        if request.work_id is None and request.source_record_id is not None:
            self._require_interaction_authority(request)
            return
        if request.work_id is None or request.base_resource_id is None:
            raise ProductInvariantViolation("Branch creation requires a bound Work repository")
        with self.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            revision = product.current_work_reality_revision(request.work_id)
            base = product.resource_for_work(request.work_id)
            target = (
                None if revision is None else governed_branch_creation_target(
                    revision.engineering_semantic_facts,
                    record_for_id=InteractionStore(uow.session).record,
                )
            )
        if revision is None or base is None or base.id != request.base_resource_id:
            raise ProductInvariantViolation("Branch creation requires the current Work repository")
        if revision.admitted_by != request.authority_identity:
            raise ProductInvariantViolation("Branch creation authority differs from current Work Reality")
        if request.source_record_id is not None:
            self._require_interaction_authority(request)
            return
        if target != request.target_branch:
            raise ProductInvariantViolation("Branch creation requires the current Human-admitted branch action")

    def interaction_observation(self, interaction_id: UUID) -> dict | None:
        history = self.attempts_for_interaction(interaction_id)
        if not history:
            return None
        latest = history[-1]
        if latest.get("condition") == "READY" and latest.get("resource_id"):
            current = self.observation(UUID(latest["resource_id"]))
            # resource_id uniquely identifies the original intake anchor. Reused
            # acquisitions retain their own current receipt and Interaction identity.
            current.update({key: latest.get(key) for key in (
                "intake_request_id", "interaction_id", "work_id", "attempt_number",
                "previous_attempt_id", "operation_kind", "target_branch",
                "base_resource_id", "source", "title", "description", "request")})
            current["fingerprint"] = canonical_fingerprint(
                {key: value for key, value in current.items()
                    if key not in {"fingerprint", "request"}})
            return current
        return latest

    def attempts_for_interaction(self, interaction_id: UUID) -> tuple[dict, ...]:
        with self.database.unit_of_work() as uow:
            rows = uow.session.execute(select(repository_intakes).where(
                repository_intakes.c.request["interaction_id"].astext == str(interaction_id)
            ).order_by(repository_intakes.c.created_at, repository_intakes.c.id)).mappings().all()
        return tuple({**(row["observation"] or {}), "request": row["request"]} for row in rows)

    def _bound_interaction_actions(self, interaction_id, record, assessment=None):
        from spg.application.intent_realization import executable_semantic_actions
        from spg.domain.interaction_actions import CanonicalOperation as O
        from spg.domain.repository_actions import RepositoryAction
        if assessment is None:
            with self.database.unit_of_work() as uow:
                assessment = next((item for item in reversed(
                    InteractionStore(uow.session).assessments(interaction_id))
                    if item.basis_last_sequence == record.sequence), None)
        ir = None if assessment is None else assessment.semantic_ir
        if ir is None or ir.source_record_id != record.id:
            return ()
        families = {O.ACQUIRE_REPOSITORY: ActionFamily.ACQUIRE_REPOSITORY,
            O.INSPECT_REPOSITORY: ActionFamily.INSPECT,
            O.SEARCH_REPOSITORY: ActionFamily.INSPECT,
            O.QUERY_CURRENT_BRANCH: ActionFamily.INSPECT,
            O.CREATE_AND_SWITCH_BRANCH: ActionFamily.LOCAL_BRANCH,
            O.CREATE_BRANCH: ActionFamily.LOCAL_BRANCH, O.SWITCH_BRANCH: ActionFamily.LOCAL_BRANCH}
        actions = []
        for item in executable_semantic_actions(ir, operations=set(families)):
            args = item.action.arguments
            actions.append(RepositoryAction(families[O(item.action.operation)],
                None if "repository_source" not in args else args["repository_source"].value,
                None if "target_branch" not in args else args["target_branch"].value,
                operation=item.action.operation,
                expected_base_revision=None if "base_revision" not in args else args["base_revision"].value,
                expected_base_tree=None if "base_tree" not in args else args["base_tree"].value,
                authorized_effects=tuple(effect.effect for effect in item.action.atomic_branch_effects)))
        return tuple(dict.fromkeys(actions))

    def _require_interaction_authority(self, request: RepositoryIntakeRequest) -> None:
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            interaction = store.interaction(request.interaction_id)
            record = store.record(request.source_record_id)
            records = store.records(request.interaction_id) if interaction else ()
            bound_resource = None
            if request.work_id is not None:
                if interaction is None or interaction.current_work_id != request.work_id:
                    raise ProductInvariantViolation("Action Work differs from current Interaction focus")
                bound_resource = ProductStore(uow.session).resource_for_work(request.work_id)
            if self.github_delivery.settings.auth_mode == 'required':
                from spg.infrastructure.persistence.auth_schema import authority_memberships, authority_resource_access
                membership = uow.session.execute(select(authority_memberships.c.role).where(
                    authority_memberships.c.organization_id == 'organization:default',
                    authority_memberships.c.actor_id == request.authority_identity,
                )).scalar_one_or_none()
                access = uow.session.execute(select(authority_resource_access.c.role).where(
                    authority_resource_access.c.resource_kind == 'interaction',
                    authority_resource_access.c.resource_id == str(request.interaction_id),
                    authority_resource_access.c.actor_id == request.authority_identity,
                )).scalar_one_or_none()
                if membership != 'OWNER' or access != 'OWNER':
                    raise RepositoryAcquisitionFailure(RepositoryAcquisitionFailureCategory.AUTH_REQUIRED,
                        'Current actor authority is required for this Interaction action.',
                        technical_evidence={'signal': 'ACTION_AUTHORITY_MISSING'}, retryable=False)
        if (interaction is None or record is None or record not in records
                or record.actor is not InteractionActor.HUMAN
                or record.source != request.authority_identity
                or interaction.created_by != request.authority_identity):
            raise ProductInvariantViolation("Interaction action requires its Human owner's explicit record")
        actions = self._bound_interaction_actions(request.interaction_id, record)
        branch = request.operation_kind in {"CREATE_BRANCH", "CREATE_BRANCH_ONLY", "SWITCH_BRANCH"}
        matching = tuple(action for action in actions if (
            action.family is ActionFamily.LOCAL_BRANCH and action.branch == request.target_branch
            and {"CREATE_AND_SWITCH_BRANCH": "CREATE_BRANCH", "CREATE_BRANCH": "CREATE_BRANCH_ONLY", "SWITCH_BRANCH": "SWITCH_BRANCH"}.get(action.operation) == request.operation_kind
            if branch else action.family in {ActionFamily.ACQUIRE_REPOSITORY, ActionFamily.INSPECT}
        ))
        if not matching:
            raise ProductInvariantViolation("Action is not explicitly authorized by its Human record")
        if branch:
            required_effects = {
                "CREATE_BRANCH": {"CREATE_BRANCH", "SWITCH_BRANCH"},
                "CREATE_BRANCH_ONLY": {"CREATE_BRANCH"},
                "SWITCH_BRANCH": {"SWITCH_BRANCH"},
            }[request.operation_kind]
            if not any(len(action.authorized_effects) == len(required_effects)
                    and set(action.authorized_effects) == required_effects for action in matching):
                raise ProductInvariantViolation("Atomic branch effects lack exact current Human authority")
        if branch and not any((action.expected_base_revision, action.expected_base_tree) ==
                (request.expected_base_revision, request.expected_base_tree) for action in matching):
            raise ProductInvariantViolation("Action exact baseline differs from governed semantic IR")
        history = self.attempts_for_interaction(request.interaction_id)
        ready = tuple(item for item in history if item.get("condition") == "READY")
        if branch:
            if not any(item.get("resource_id") == str(request.base_resource_id) for item in ready) and not (
                    bound_resource is not None and bound_resource.id == request.base_resource_id):
                raise ProductInvariantViolation("Branch source does not belong to this Interaction")
        elif not any(action.source == request.source for action in matching):
            if not any(item.get("source") == request.source for item in ready):
                raise ProductInvariantViolation("Acquisition source differs from explicit Human authority")

    def execute_interaction_actions(self, interaction_id, assessment, record, *, work_id=None) -> str | None:
        """Execute independently admitted preparatory actions without forming Work."""
        actions = self._bound_interaction_actions(interaction_id, record, assessment)
        if not actions:
            return None
        previous = self.interaction_observation(interaction_id)
        if work_id is not None:
            with self.database.unit_of_work() as uow:
                store = ProductStore(uow.session)
                selected = store.resource_for_work(work_id)
            if selected is not None:
                previous = {**self.observation(selected.id),
                    "source": (previous or {}).get("source") or selected.repository_identity,
                    "product_id": (previous or {}).get("product_id")}
        messages = []
        for action in actions:
            if action.target_ambiguous:
                messages.append("你提供了多个仓库地址；请指定要操作哪一个。尚未执行仓库操作。")
                break
            prior_product_id = (previous or {}).get('product_id')
            source = action.source or (previous or {}).get("source")
            if action.family is ActionFamily.LOCAL_BRANCH:
                if previous is None or previous.get("condition") != "READY":
                    messages.append("尚无已获取的仓库；请指定要操作的仓库。")
                    break
                operation = {"CREATE_BRANCH": "CREATE_BRANCH_ONLY", "SWITCH_BRANCH": "SWITCH_BRANCH"}.get(action.operation, "CREATE_BRANCH")
                if previous.get("repository_ref") == f"refs/heads/{action.branch}":
                    messages.append(f"当前本地分支已经是 {action.branch}；没有重复创建或推送。")
                    continue
            elif action.source is None and previous is not None and action.family is ActionFamily.INSPECT:
                if previous.get("condition") == "READY":
                    messages.append(self._inspection_answer(previous, branch_only=bool(assessment and assessment.semantic_ir and any(
                        item.action.operation == "QUERY_CURRENT_BRANCH"
                        for item in assessment.semantic_ir.operational_requests))))
                else:
                    messages.append(f"仓库尚未就绪：{previous.get('condition')}。")
                continue
            else:
                operation = "ACQUIRE"
            if source is None:
                messages.append("请指定一个仓库地址，以便获取或检查；尚未执行仓库操作。")
                break
            from time import monotonic
            deadline = monotonic() + 300
            count = 0
            while count < 3:
                history = self.attempts_for_interaction(interaction_id)
                same = [item for item in history if item.get("request", {}).get("source_record_id") == str(record.id)
                    and item.get("operation_kind") == operation
                    and item.get("target_branch") == action.branch]
                if same and same[-1].get("condition") not in {"REQUESTED", "RUNNING", "FAILED_RETRYABLE"}:
                    previous = same[-1]
                    break
                if len(same) >= 3 or (same and monotonic() >= deadline):
                    previous = same[-1]
                    break
                capability = ConnectorResolver(self.database).resolve(CapabilityRequirement(
                    capability_id="git.checkout" if operation == "SWITCH_BRANCH" else "git.branch.create" if operation in {"CREATE_BRANCH", "CREATE_BRANCH_ONLY"} else "git.repository.acquire",
                    work_id=work_id, user_id=record.source, operation_ref=f"interaction-record:{record.id}",
                ))
                decision = admit_action(action.family, ActionFacts(explicit=True,
                    authority=True, capability=capability.executable,
                    repository_ready=bool(previous and previous.get("condition") == "READY"),
                    retryable=bool(same), attempts=len(same)))
                if not decision.execute:
                    messages.append(f"操作未执行：{decision.signal}；没有新增生产或远端写入授权。")
                    return "\n".join(messages)
                number = len(same) + 1
                if same and same[-1].get("condition") in {"REQUESTED", "RUNNING"}:
                    previous = self.execute_intake(UUID(same[-1]['intake_request_id']))
                    count += 1
                    if previous.get('condition') != 'FAILED_RETRYABLE' or previous.get('failure_category') != 'NETWORK_FAILURE':
                        break
                    continue
                request = RepositoryIntakeRequest(
                    request_id=uuid5(NAMESPACE_URL, f"interaction-action:{record.id}:{operation}:{action.branch}:{number}"),
                    source=source, title=f"Interaction {operation}", description=record.content[:4000],
                    authority_identity=record.source, interaction_id=interaction_id, work_id=work_id,
                    source_record_id=record.id, attempt_number=number,
                    previous_attempt_id=UUID(same[-1]["intake_request_id"]) if same else None,
                    operation_kind=operation,
                    base_resource_id=UUID(previous["resource_id"]) if operation in {"CREATE_BRANCH", "CREATE_BRANCH_ONLY", "SWITCH_BRANCH"} else None,
                    target_branch=action.branch,
                    expected_base_revision=action.expected_base_revision,
                    expected_base_tree=action.expected_base_tree,
                )
                try:
                    previous = self.intake(request)
                except RepositoryAcquisitionFailure as failure:
                    messages.append(f"操作被阻止：{failure.human_message}")
                    return "\n".join(messages)
                count += 1
                if previous.get("failure_category") != "NETWORK_FAILURE" or previous.get("condition") != "FAILED_RETRYABLE":
                    break
                from time import sleep
                sleep(min(2 ** (number - 1), 4))
            if previous and previous.get('attempt_number', 1) > 1:
                self._record_interaction_action_refinement(interaction_id, record, previous)
            if previous is None or previous.get("condition") != "READY":
                messages.append(f"仓库操作未成功：{(previous or {}).get('condition', 'BLOCKED')}；{(previous or {}).get('human_message', '')}")
                break
            from spg.application.product_assets import ProductAssetService
            products = ProductAssetService(self.database)
            if prior_product_id and operation == 'CREATE_BRANCH':
                products.attach_asset(UUID(prior_product_id), record.source,
                    kind='REPOSITORY', reference=previous['repository_identity'],
                    resource_id=UUID(previous['resource_id']),
                    metadata={key: previous[key] for key in ('repository_ref','revision','tree')})
                product_id = UUID(prior_product_id)
            else:
                product_id = products.ensure_repository_work(None, UUID(previous['resource_id']),
                    record.source, revision=previous['revision'],
                    repository_ref=previous['repository_ref'], tree=previous['tree'])
            previous = {**previous, 'product_id': str(product_id)}
            previous['fingerprint'] = canonical_fingerprint({key: value for key, value in previous.items()
                if key not in {'fingerprint','request'}})
            with self.database.unit_of_work() as uow:
                uow.session.execute(update(repository_intakes).where(
                    repository_intakes.c.id == UUID(previous['intake_request_id'])).values(
                        observation={key: value for key,value in previous.items() if key != 'request'}))
                uow.commit()
            messages.append(self._inspection_answer(previous,
                branch_only=action.family is not ActionFamily.INSPECT))
        return "\n".join(messages) + ("\n生产 Work 尚未准入；没有修改源码或推送远端。" if work_id is None else
            "\n本轮操作沿用当前 Work 权限；没有修改源码或推送远端。") if messages else None

    def _record_interaction_action_refinement(self, interaction_id, record, observation):
        from spg.domain.wic_response import WicResponseEventType
        from uuid import uuid4
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            turn = next((item for item in store.turns(interaction_id)
                if item.request_record_id == record.id), None)
            if turn is None:
                return
            evidence_reference = f"repository-intake:{observation['intake_request_id']}"
            if any(event.metadata.get('evidence_reference') == evidence_reference
                   for event in store.response_events(turn.id)):
                return
            store.insert_response_event({
                'id': uuid4(), 'interaction_id': interaction_id, 'turn_id': turn.id,
                'response_id': turn.id, 'sequence': store.next_response_event_sequence(turn.id),
                'event_type': WicResponseEventType.RESPONSE_REFINEMENT.value,
                'content': None, 'basis_fingerprint': None, 'reconciliation': None,
                'event_metadata': {'component': 'repository/acquisition',
                    'signal': 'ACTION_RETRYABLE', 'automatic': True,
                    'recovery_scope': 'INTERACTION_ACTION_ONLY', 'work_converged': False,
                    'attempt_budget': 3, 'time_budget_seconds': 300,
                    'attempt_count': observation['attempt_number'],
                    'final_condition': observation['condition'],
                    'evidence_reference': f"repository-intake:{observation['intake_request_id']}"},
                'created_at': datetime.now(UTC),
            })
            uow.commit()

    def restore_interaction_actions(self):
        """Resume durable requested operations without synthesizing Human intent."""
        with self.database.unit_of_work() as uow:
            rows = uow.session.execute(select(repository_intakes.c.request).where(
                repository_intakes.c.observation['condition'].astext.in_(['REQUESTED', 'RUNNING', 'FAILED_RETRYABLE'])
            )).scalars().all()
        for payload in rows:
            request = RepositoryIntakeRequest.model_validate(payload)
            if request.work_id is not None or request.source_record_id is None:
                continue
            with self.database.unit_of_work() as uow:
                record = InteractionStore(uow.session).record(request.source_record_id)
            if record is not None:
                self.execute_interaction_actions(request.interaction_id, None, record)

    def _inspection_answer(self, observation, *, branch_only=False):
        branch = observation['repository_ref'].removeprefix('refs/heads/')
        answer = f"仓库已就绪，本地分支：{branch}；提交：{observation['revision']}；文件树：{observation['tree']}。"
        if branch_only:
            return answer
        packet = self.research_context(turn_id=UUID(observation['intake_request_id']),
            interaction_id=UUID(observation['interaction_id']), source=observation['source'],
            authority_identity="unused", observation=observation)
        for material in packet['materials']:
            if Path(material['path']).name in {'package.json', 'pyproject.toml'}:
                answer += f"\n证据 {observation['revision']}:{material['path']}（SHA256 {material['content_sha256']}）：\n{material['content'][:4000]}"
        if not packet['materials']:
            answer += "\n未发现可用于确认技术栈的材料，不能推断使用的框架。"
        return answer

    def intake(self, request: RepositoryIntakeRequest):
        observation = self.start_intake(request)
        if observation.get("condition") not in {"REQUESTED", "RUNNING"}:
            return observation
        return self.execute_intake(request.request_id)

    def record_waiting_source(self, request: RepositoryIntakeRequest) -> dict:
        observation = self.start_intake(request)
        waiting = {
            **observation,
            "condition": "WAITING_FOR_REPOSITORY_SOURCE",
            "human_message": "A repository source is required before acquisition can start.",
            "message": "A repository source is required before acquisition can start.",
        }
        waiting["fingerprint"] = canonical_fingerprint(
            {key: value for key, value in waiting.items() if key != "fingerprint"}
        )
        with self.database.unit_of_work() as uow:
            uow.session.execute(
                update(repository_intakes)
                .where(repository_intakes.c.id == request.request_id)
                .values(observation=waiting)
            )
            uow.commit()
        return waiting

    def execute_intake(self, request_id: UUID) -> dict:
        """Execute exactly one persisted acquisition Attempt."""

        try:
            return self._execute_intake(request_id)
        except ProductRecordNotFound:
            raise
        except RepositoryAcquisitionFailure as error:
            return self.mark_attempt_failure(
                request_id, category=error.category, human_message=error.human_message,
                technical_evidence=error.technical_evidence, retryable=error.retryable,
            )
        except Exception as error:
            # Once an Attempt exists, an unexpected adapter, observation, or
            # persistence failure must not leave durable Reality at RUNNING.
            # Preserve the technical cause while exposing only a safe message.
            return self.mark_attempt_failure(
                request_id,
                category=(
                    RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE
                ),
                human_message=(
                    "Repository acquisition could not be completed and can be retried."
                ),
                technical_evidence={
                    "phase": "REPOSITORY_ACQUISITION",
                    "error_type": type(error).__name__,
                    "message": str(error)[:2000],
                },
                retryable=True,
            )

    def _execute_intake(self, request_id: UUID) -> dict:
        """Internal effectful phase; ``execute_intake`` owns terminalization."""

        with self.database.unit_of_work() as uow:
            row = uow.session.execute(
                select(repository_intakes).where(repository_intakes.c.id == request_id)
            ).mappings().one_or_none()
        if row is None:
            raise ProductRecordNotFound("Repository acquisition Attempt does not exist")
        request = RepositoryIntakeRequest.model_validate(row["request"])
        if request.source_record_id is not None:
            self._require_interaction_authority(request)
        if request.operation_kind in {"CREATE_BRANCH", "CREATE_BRANCH_ONLY", "SWITCH_BRANCH"}:
            self._require_current_branch_authority(request)
        observation = row["observation"]
        if observation is None:
            observation = self.start_intake(request)
        if observation.get("condition") not in {"REQUESTED", "RUNNING"}:
            return observation

        source = self._source(request.source)
        identity = self._identity(source, request)
        with self._lock(identity):
            if request.expected_base_revision is not None:
                with self.database.unit_of_work() as uow:
                    base = ProductStore(uow.session).resource(request.base_resource_id)
                if base is None:
                    raise ProductInvariantViolation("Bound repository baseline is missing")
                actual_revision = self._git(Path(base.location_ref), "rev-parse", base.authoritative_ref + "^{commit}")
                actual_tree = self._git(Path(base.location_ref), "rev-parse", base.authoritative_ref + "^{tree}")
                if (actual_revision, actual_tree) != (request.expected_base_revision, request.expected_base_tree):
                    return self.mark_attempt_failure(request.request_id,
                        category=RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_TERMINAL,
                        human_message="The repository baseline changed before the branch operation; no branch was written.",
                        technical_evidence={"signal": "ACTION_REQUIRES_REALITY_REFRESH",
                            "expected_revision": request.expected_base_revision,
                            "expected_tree": request.expected_base_tree,
                            "actual_revision": actual_revision, "actual_tree": actual_tree,
                            "effect_observed": False}, retryable=False)
            with self.database.unit_of_work() as uow:
                current = uow.session.execute(
                    select(repository_intakes.c.observation).where(
                        repository_intakes.c.id == request.request_id
                    )
                ).scalar_one()
                if current is not None and current.get("condition") not in {
                    "REQUESTED",
                    "RUNNING",
                }:
                    return current
                if current is not None and current.get("condition") == "REQUESTED":
                    current = {
                        **current,
                        "condition": "RUNNING",
                        "human_message": (
                            f"Creating local branch {request.target_branch}."
                            if request.operation_kind in {"CREATE_BRANCH", "CREATE_BRANCH_ONLY", "SWITCH_BRANCH"}
                            else "Repository acquisition is running."
                        ),
                        "observed_at": datetime.now(UTC).isoformat(),
                    }
                    current["fingerprint"] = canonical_fingerprint(
                        {
                            key: value
                            for key, value in current.items()
                            if key != "fingerprint"
                        }
                    )
                    uow.session.execute(
                        update(repository_intakes)
                        .where(repository_intakes.c.id == request_id)
                        .values(observation=current)
                    )
                    uow.commit()
                existing = uow.session.execute(
                    select(engineering_resources.c.id).where(
                        engineering_resources.c.repository_identity == identity
                    )
                ).scalar_one_or_none()
            if existing is not None:
                if (identity.startswith("watt://repositories/")
                        or self.managed_source.has_source(identity)):
                    restored = self.asset_root / str(request.request_id)
                    if not self.managed_source.has_source(identity):
                        with self.database.unit_of_work() as uow:
                            existing_path = uow.session.execute(
                                select(engineering_resources.c.location_ref).where(
                                    engineering_resources.c.id == existing)
                            ).scalar_one()
                        if Path(existing_path).is_dir():
                            self.managed_source.sync(identity, Path(existing_path))
                    self.managed_source.recover(identity, restored)
                    with self.database.unit_of_work() as uow:
                        uow.session.execute(update(engineering_resources).where(
                            engineering_resources.c.id == existing).values(
                                location_ref=str(restored)))
                        uow.commit()
                observed = {
                    **self.observation(existing),
                    "intake_request_id": str(request.request_id),
                    **self._attempt_metadata(request),
                }
                observed["fingerprint"] = canonical_fingerprint(
                    {key: value for key, value in observed.items() if key != "fingerprint"}
                )
                with self.database.unit_of_work() as uow:
                    uow.session.execute(
                        update(repository_intakes)
                        .where(repository_intakes.c.id == request.request_id)
                        .values(observation=observed)
                    )
                    uow.commit()
                return observed
            self.asset_root.mkdir(parents=True, exist_ok=True)
            repository = self.asset_root / str(request.request_id)
            connector_capability = None
            native_result = None
            managed_branch = False
            if request.operation_kind in {"CREATE_BRANCH", "CREATE_BRANCH_ONLY", "SWITCH_BRANCH"}:
                with self.database.unit_of_work() as uow:
                    base_for_source = ProductStore(uow.session).resource(
                        request.base_resource_id)
                managed_branch = bool(base_for_source and (
                    base_for_source.repository_identity.startswith(
                        "watt://repositories/") or self.managed_source.has_source(
                            base_for_source.repository_identity)))
            if not repository.exists():
                if request.operation_kind in {"CREATE_BRANCH", "CREATE_BRANCH_ONLY", "SWITCH_BRANCH"} and request.work_id is None:
                    requirement = CapabilityRequirement(
                        capability_id="git.branch.create", work_id=None,
                        user_id=request.authority_identity,
                        operation_ref=f"repository-intake:{request.request_id}",
                    )
                    resolution = ConnectorResolver(self.database).resolve(requirement)
                    if not resolution.executable:
                        return self.mark_attempt_failure(request.request_id,
                            category=RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_TERMINAL,
                            human_message="Local branch capability is unavailable.",
                            technical_evidence={"signal": "CAPABILITY_MISSING"}, retryable=False)
                    connector_capability = resolution.capability
                    with self.database.unit_of_work() as uow:
                        base = ProductStore(uow.session).resource(request.base_resource_id)
                    self.repository_acquirer.realize_local_branch(
                        self.asset_root, Path(base.location_ref),
                        base.authoritative_ref.removeprefix("refs/heads/"),
                        source, repository, request.target_branch, operation=request.operation_kind,
                        expected_base_revision=request.expected_base_revision,
                        expected_base_tree=request.expected_base_tree,
                    )
                elif request.operation_kind in {"CREATE_BRANCH", "CREATE_BRANCH_ONLY", "SWITCH_BRANCH"}:
                    requirement = CapabilityRequirement(
                        capability_id="git.checkout" if request.operation_kind == "SWITCH_BRANCH" else "git.branch.create",
                        work_id=request.work_id,
                        user_id=request.authority_identity,
                        operation_ref=f"repository-intake:{request.request_id}",
                        resume_point={
                            "intake_request_id": str(request.request_id),
                            "target_branch": request.target_branch,
                        },
                    )
                    resolution = ConnectorResolver(self.database).resolve(requirement)
                    if not resolution.executable:
                        return self.mark_attempt_failure(
                            request.request_id,
                            category=RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE,
                            human_message="The Git branch capability is unavailable; this Work is resumable after a connector is bound.",
                            technical_evidence={
                                "capability_id": requirement.capability_id,
                                "gap_id": str(resolution.gap_id),
                                "operation_ref": requirement.operation_ref,
                            },
                            retryable=True,
                        )
                    connector_capability = resolution.capability
                    with self.database.unit_of_work() as uow:
                        base = ProductStore(uow.session).resource(
                            request.base_resource_id
                        )
                    if base is None:
                        raise ProductInvariantViolation(
                            "Bound repository baseline is missing"
                        )
                    if self.native_git_operations is None:
                        return self.mark_attempt_failure(
                            request.request_id,
                            category=RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE,
                            human_message="Native Git execution is unavailable; this branch Work remains resumable.",
                            technical_evidence={"phase": "NATIVE_GIT_EXECUTOR_UNCONFIGURED"},
                            retryable=True,
                        )
                    native_result = self.native_git_operations.create_branch(
                        work_id=request.work_id,
                        intake_id=request.request_id,
                        source_repository=Path(base.location_ref),
                        source_identity=base.repository_identity,
                        source_ref=base.authoritative_ref,
                        source_url=source,
                        target_branch=request.target_branch,
                        authority_identity=request.authority_identity,
                        operation_kind=request.operation_kind,
                    )
                    if native_result["condition"] == "RUNNING":
                        with self.database.unit_of_work() as uow:
                            current = uow.session.execute(
                                select(repository_intakes.c.observation).where(
                                    repository_intakes.c.id == request.request_id
                                )
                            ).scalar_one()
                            running = {
                                **current,
                                "condition": "RUNNING",
                                "human_message": "Native Git branch execution is in progress.",
                                "technical_evidence": {
                                    "native_attempt_id": native_result.get("native_attempt_id"),
                                    "checkpoint_id": native_result.get("checkpoint_id"),
                                },
                                "observed_at": datetime.now(UTC).isoformat(),
                            }
                            running["fingerprint"] = canonical_fingerprint({
                                key: value for key, value in running.items() if key != "fingerprint"
                            })
                            uow.session.execute(
                                update(repository_intakes)
                                .where(repository_intakes.c.id == request.request_id)
                                .values(observation=running)
                            )
                            uow.commit()
                        return running
                    if native_result["condition"] != "READY":
                        return self.mark_attempt_failure(
                            request.request_id,
                            category=RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE,
                            human_message="Native Git branch execution has not established the requested branch; retry remains available.",
                            technical_evidence={
                                "phase": "NATIVE_GIT_EXECUTION",
                                "native_attempt_id": native_result.get("native_attempt_id"),
                                "checkpoint_id": native_result.get("checkpoint_id"),
                                "terminal_outcome": native_result.get("terminal_outcome"),
                                "progress_summary": native_result.get("progress_summary"),
                                "tool_result_conditions": native_result.get("tool_result_conditions"),
                            },
                            retryable=True,
                        )
                    self.repository_acquirer.acquire(
                        self.asset_root,
                        str(native_result["workspace_path"]),
                        repository,
                    )
                    if source is None:
                        self._git(repository, "remote", "remove", "origin")
                    else:
                        self._git(repository, "remote", "set-url", "origin", source)
                    expected_current = (base.authoritative_ref.removeprefix("refs/heads/")
                        if request.operation_kind == "CREATE_BRANCH_ONLY" else request.target_branch)
                    if request.operation_kind == "CREATE_BRANCH_ONLY":
                        # A clone retains other local branches as remote tracking
                        # refs. Materialize the already-produced exact local ref;
                        # preserve HEAD and do not perform another creation effect.
                        self._git(repository,"fetch","--no-tags","--no-recurse-submodules",
                            str(native_result["workspace_path"]),
                            f"refs/heads/{request.target_branch}:refs/heads/{request.target_branch}")
                    if (
                        self._git(repository, "branch", "--show-current") != expected_current
                        or self._git(repository, "rev-parse", "HEAD") != native_result["revision"]
                    ):
                        raise ProductInvariantViolation("Native Git result changed during repository asset materialization")
                elif source is None:
                    repository.mkdir()
                    self._git(repository, "init", "-b", "main")
                    exclude = repository / ".git" / "info" / "exclude"
                    existing_excludes = exclude.read_text(encoding="utf-8")
                    additions = tuple(
                        pattern
                        for pattern in self._MANAGED_REPOSITORY_EXCLUDES
                        if pattern not in existing_excludes.splitlines()
                    )
                    if additions:
                        exclude.write_text(
                            existing_excludes.rstrip("\n")
                            + "\n"
                            + "\n".join(additions)
                            + "\n",
                            encoding="utf-8",
                        )
                    # Only initialization facts; design is produced later through SPG.
                    (repository / "README.md").write_text("# Work Repository\n\nInitialized for governed Work production.\n", encoding="utf-8")
                    self._git(repository, "add", "--", "README.md")
                    self._git(repository, "-c", "user.name=Watt", "-c", "user.email=watt@localhost", "commit", "-m", "Initialize repository asset")
                else:
                    if request.work_id is not None or request.source_record_id is not None:
                        requirement = CapabilityRequirement(
                            capability_id="git.repository.acquire",
                            work_id=request.work_id,
                            user_id=request.authority_identity,
                            operation_ref=f"repository-intake:{request.request_id}",
                            resume_point={
                                "intake_request_id": str(request.request_id),
                                "source": source,
                            },
                        )
                        resolution = ConnectorResolver(self.database).resolve(requirement)
                        if not resolution.executable:
                            return self.mark_attempt_failure(
                                request.request_id,
                                category=RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE,
                                human_message="Repository acquisition capability is unavailable; this Work can resume when a connector is bound.",
                                technical_evidence={
                                    "capability_id": requirement.capability_id,
                                    "gap_id": str(resolution.gap_id),
                                    "operation_ref": requirement.operation_ref,
                                },
                                retryable=True,
                            )
                        connector_capability = resolution.capability
                    try:
                        # Repository intake preserves complete history for the
                        # selected default branch without fetching unrelated
                        # remote branches. Production Environment remains the
                        # owner of the eventual execution Workspace.
                        credential = None
                        if urlsplit(source).hostname == "github.com":
                            credential = self.github_delivery.active_token(
                                request.authority_identity, source, "READ")
                        if credential is None:
                            self.repository_acquirer.acquire(
                                self.asset_root, source, repository)
                        else:
                            self.repository_acquirer.acquire(
                                self.asset_root, source, repository,
                                credential=credential)
                    except RepositoryAcquisitionFailure as failure:
                        if repository.exists() and repository.parent == self.asset_root:
                            shutil.rmtree(repository, ignore_errors=True)
                        condition = (
                            "WAITING_FOR_AUTHORIZATION"
                            if failure.category
                            is RepositoryAcquisitionFailureCategory.AUTH_REQUIRED
                            else "FAILED_RETRYABLE"
                            if failure.retryable
                            else "FAILED_TERMINAL"
                        )
                        candidate = {
                            "resource_id": None,
                            "repository_identity": source,
                            "repository_ref": None,
                            "revision": None,
                            "tree": None,
                            "paths": [],
                            "context_path": None,
                            "observed_at": datetime.now(UTC).isoformat(),
                            "source": source,
                            "title": request.title,
                            "description": request.description,
                            "intake_request_id": str(request.request_id),
                            "condition": condition,
                            "failure_category": failure.category.value,
                            "human_message": failure.human_message,
                            "technical_evidence": failure.technical_evidence,
                            **self._attempt_metadata(request),
                            "authorization": {
                                capability: "UNKNOWN"
                                for capability in (
                                    "READ",
                                    "WRITE",
                                    "CREATE_BRANCH",
                                    "CREATE_PR",
                                    "PUSH",
                                )
                            },
                            "message": failure.human_message,
                        }
                        candidate["fingerprint"] = canonical_fingerprint(candidate)
                        with self.database.unit_of_work() as uow:
                            uow.session.execute(
                                update(repository_intakes)
                                .where(repository_intakes.c.id == request.request_id)
                                .values(observation=candidate)
                            )
                            uow.commit()
                        return candidate
            # Capture complete Git history before exposing a managed checkout.
            # The checkout remains disposable; PostgreSQL owns canonical bytes.
            if source is None and request.operation_kind == "ACQUIRE":
                self.managed_source.sync(identity, repository)
            elif managed_branch:
                self.managed_source.sync(identity, repository, internal_branch=True)
            # A previous interrupted intake may leave a valid repository: observe, never overwrite.
            ref = self._git(repository, "symbolic-ref", "HEAD")
            revision = self._git(repository, "rev-parse", "HEAD")
            tree = self._git(repository, "rev-parse", "HEAD^{tree}")
            paths = self._git(repository, "ls-tree", "-r", "--name-only", revision).splitlines()
            context = next(
                (
                    name
                    for name in paths
                    if Path(name).name.casefold().startswith("readme")
                ),
                None,
            )
            if context is None:
                context = next((name for name in paths if name.endswith(".md")), None)
            if context is None:
                context = next(iter(paths), None)
            if context is None:
                raise ProductInvariantViolation(
                    "Repository acquisition requires at least one tracked file"
                )
            runtime = RuntimeService(self.database)
            with self.database.unit_of_work() as uow:
                from spg.infrastructure.persistence.runtime_store import RuntimeStore
                pointer = RuntimeStore(uow.session).current_pointer(repository_identity=identity, repository_ref=ref)
            if pointer is None:
                runtime.bootstrap_trusted_baseline(BootstrapRequest(repository_path=repository, repository_identity=identity,
                    repository_ref=ref, authority_identity=request.authority_identity,
                    scope={"intake_request_id": str(request.request_id), "purpose": "Repository Asset baseline observation"}))
            with self.database.unit_of_work() as uow:
                resource_id = uow.session.execute(select(engineering_resources.c.id).where(engineering_resources.c.repository_identity == identity)).scalar_one_or_none()
            if resource_id is None:
                resource = WorkApplicationService(self.database).register_engineering_resource(
                    repository_identity=identity, location_ref=str(repository), authoritative_ref=ref,
                    context_references=(EngineeringContextReference(semantic_role=ContextSemanticRole.PROJECT_CONTEXT, repository_relative_path=context),), is_default=False)
                resource_id = resource.id
            observation = {"resource_id": str(resource_id), "repository_identity": identity, "repository_ref": ref,
                "revision": revision, "tree": tree, "branches": self._git(repository, "for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines(), "paths": paths[:200], "context_path": context,
                "observed_at": datetime.now(UTC).isoformat(), "source": source, "title": request.title,
                "description": request.description, "intake_request_id": str(request.request_id),
                "condition": "READY", "failure_category": None,
                "human_message": (
                    f"Local branch {request.target_branch} is ready."
                    if request.operation_kind in {"CREATE_BRANCH", "CREATE_BRANCH_ONLY", "SWITCH_BRANCH"}
                    else "Repository is ready."
                ), "technical_evidence": None,
                **self._attempt_metadata(request)}
            if request.operation_kind in {"CREATE_BRANCH", "CREATE_BRANCH_ONLY", "SWITCH_BRANCH"}:
                observation["operation_evidence"] = {
                    "capability_id": "git.branch.create",
                    "connector_id": (
                        connector_capability.connector_id
                        if connector_capability is not None
                        else "builtin:git"
                    ),
                    "operation_ref": f"repository-intake:{request.request_id}",
                    "workspace_reference": str(repository),
                    "resulting_branch": ref,
                    "resulting_revision": revision,
                    "base_resource_id": str(request.base_resource_id),
                    "verified": (request.target_branch in self._git(repository, "for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines()
                        if request.operation_kind == "CREATE_BRANCH_ONLY" else ref == f"refs/heads/{request.target_branch}"),
                    "native_attempt_id": None if native_result is None else native_result["native_attempt_id"],
                    "pwu_id": None if native_result is None else native_result["pwu_id"],
                    "task_contract_id": None if native_result is None else native_result["task_contract_id"],
                    "checkpoint_id": None if native_result is None else native_result["checkpoint_id"],
                    "environment_id": None if native_result is None else native_result["environment_id"],
                    "production_record_id": None if native_result is None else native_result["production_record_id"],
                }
                if not observation["operation_evidence"]["verified"]:
                    raise ProductInvariantViolation("Created branch observation differs from the Human-requested branch")
            elif connector_capability is not None:
                observation["operation_evidence"] = {
                    "capability_id": "git.repository.acquire",
                    "connector_id": connector_capability.connector_id,
                    "operation_ref": f"repository-intake:{request.request_id}",
                    "workspace_reference": str(repository),
                    "resulting_branch": ref,
                    "resulting_revision": revision,
                    "verified": bool(ref and revision),
                }
            observation["fingerprint"] = canonical_fingerprint(observation)
            with self.database.unit_of_work() as uow:
                uow.session.execute(update(repository_intakes).where(repository_intakes.c.id == request.request_id).values(resource_id=resource_id, observation=observation))
                uow.commit()
            return observation

    def mark_attempt_failure(
        self,
        request_id: UUID,
        *,
        category: RepositoryAcquisitionFailureCategory,
        human_message: str,
        technical_evidence: dict[str, object],
        retryable: bool,
    ) -> dict:
        with self.database.unit_of_work() as uow:
            observation = uow.session.execute(
                select(repository_intakes.c.observation).where(
                    repository_intakes.c.id == request_id
                )
            ).scalar_one_or_none()
            if observation is None:
                raise ProductRecordNotFound(
                    "Repository acquisition Attempt does not exist"
                )
            failed = {
                **observation,
                "condition": "FAILED_RETRYABLE" if retryable else "FAILED_TERMINAL",
                "failure_category": category.value,
                "human_message": human_message,
                "technical_evidence": technical_evidence,
                "message": human_message,
                "observed_at": datetime.now(UTC).isoformat(),
            }
            failed["fingerprint"] = canonical_fingerprint(
                {key: value for key, value in failed.items() if key != "fingerprint"}
            )
            uow.session.execute(
                update(repository_intakes)
                .where(repository_intakes.c.id == request_id)
                .values(observation=failed)
            )
            uow.commit()
        return failed

    def attempts_for_work(self, work_id: UUID) -> tuple[dict, ...]:
        identity = str(work_id)
        with self.database.unit_of_work() as uow:
            rows = uow.session.execute(
                select(
                    repository_intakes.c.id,
                    repository_intakes.c.request,
                    repository_intakes.c.observation,
                    repository_intakes.c.created_at,
                ).order_by(repository_intakes.c.created_at, repository_intakes.c.id)
            ).mappings().all()
        return tuple(
            {
                **(row["observation"] or {}),
                "intake_request_id": str(row["id"]),
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
            if str(row["request"].get("work_id")) == identity
        )

    def latest_attempt_for_work(self, work_id: UUID) -> dict | None:
        attempts = self.attempts_for_work(work_id)
        return attempts[-1] if attempts else None

    def next_attempt_number(self, work_id: UUID) -> int:
        attempts = self.attempts_for_work(work_id)
        return 1 + max(
            (int(item.get("attempt_number") or 0) for item in attempts),
            default=0,
        )

    def repository_activation_allowed(self, work_id: UUID) -> bool:
        latest = self.latest_attempt_for_work(work_id)
        if latest is not None:
            if latest.get("condition") != "READY":
                return False
            with self.database.unit_of_work() as uow:
                selected = ProductStore(uow.session).resource_for_work(work_id)
            return selected is not None and str(selected.id) == latest.get("resource_id")
        with self.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            if product.resource_for_work(work_id) is not None:
                return True
            revision = product.current_work_reality_revision(work_id)
        if revision is None:
            return True
        repository_required = any(
            fact.subject == "repository.url"
            for fact in current_semantic_facts(
                revision.engineering_semantic_facts
            )
        )
        return not repository_required

    def ensure_managed_execution_workspace(
        self,
        work_service: WorkApplicationService,
        work_id: UUID,
    ):
        """Allocate one local Git-backed execution workspace within admitted Work authority."""
        with self.database.unit_of_work() as uow:
            selected = ProductStore(uow.session).resource_for_work(work_id)
        if selected is not None:
            if (selected.repository_identity.startswith("watt://repositories/")
                    or self.managed_source.has_source(selected.repository_identity)):
                if not self.managed_source.has_source(selected.repository_identity):
                    if not Path(selected.location_ref).is_dir():
                        raise ProductInvariantViolation(
                            "Legacy managed repository checkout and canonical source are unavailable")
                    self.managed_source.sync(
                        selected.repository_identity, Path(selected.location_ref))
                self.managed_source.recover(
                    selected.repository_identity, Path(selected.location_ref))
            return work_service.get_work(work_id)

        request_id = uuid5(
            NAMESPACE_URL,
            f"watt:managed-execution-workspace:{work_id}",
        )
        authority = "system:watt-managed-execution-workspace"
        observation = self.intake(
            RepositoryIntakeRequest(
                request_id=request_id,
                title="Watt-managed execution workspace",
                description=(
                    "Local execution substrate allocated only when this admitted Work "
                    "reaches production readiness."
                ),
                authority_identity=authority,
            )
        )
        projection = work_service.get_work(work_id)
        with self.database.unit_of_work() as uow:
            selected = ProductStore(uow.session).resource_for_work(work_id)
        if selected is not None:
            return projection
        if observation.get("resource_id") is None:
            raise ProductInvariantViolation(
                "Watt-managed execution workspace could not be observed"
            )
        return work_service.admit_asset_scope(
            work_id,
            AssetScopeAdmissionRequest(
                resource_id=UUID(observation["resource_id"]),
                expected_work_revision_id=projection.current_work_reality_revision_id,
                observation_fingerprint=observation["fingerprint"],
                authority_identity=authority,
                rationale=(
                    "Allocate Watt-owned local execution substrate within the already "
                    "admitted Work authority; no external repository authority is implied."
                ),
            ),
            observation,
            managed_execution_workspace=True,
        )

    def observation(self, resource_id: UUID):
        """Keep historical intake intact; refresh only against trusted owner truth."""
        from spg.infrastructure.persistence.runtime_store import RuntimeStore
        from spg.domain.runtime import SnapshotCondition
        with self.database.unit_of_work() as uow:
            row = uow.session.execute(select(repository_intakes.c.observation).where(
                repository_intakes.c.resource_id == resource_id).order_by(
                    repository_intakes.c.created_at.desc(), repository_intakes.c.id.desc()).limit(1)).scalar_one_or_none()
            if row is None:
                raise ProductRecordNotFound("Repository has no product intake observation")
            resource = ProductStore(uow.session).resource(resource_id)
            binding_failure = (row.get("technical_evidence") or {}).get("phase") == "WORK_REALITY_BINDING"
            if (row.get("condition") != "READY" and not binding_failure) or resource is None:
                return row
            runtime = RuntimeStore(uow.session)
            pointer = runtime.current_pointer(repository_identity=resource.repository_identity,
                repository_ref=resource.authoritative_ref)
            snapshot = None if pointer is None else runtime.snapshot(pointer.snapshot_id)
        path = Path(resource.location_ref)
        try:
            revision = self._git(path, "rev-parse", resource.authoritative_ref + "^{commit}")
            tree = self._git(path, "rev-parse", resource.authoritative_ref + "^{tree}")
            branch = self._git(path, "symbolic-ref", "HEAD")
        except ProductInvariantViolation:
            unavailable = {**row, "condition": "BLOCKED",
                "human_message": "Current repository observation is unavailable; historical evidence is preserved.",
                "technical_evidence": {"signal": "ACTION_REQUIRES_REALITY_REFRESH", "actual_git_observed": False}}
            unavailable["fingerprint"] = canonical_fingerprint({k:v for k,v in unavailable.items() if k != "fingerprint"})
            return unavailable
        trusted = bool(snapshot and snapshot.condition is SnapshotCondition.TRUSTED
            and snapshot.repository_revision == revision
            and snapshot.repository_tree_identity == tree and branch == resource.authoritative_ref)
        if row.get("condition") == "READY" and (revision, tree, branch) == (row.get("revision"), row.get("tree"), row.get("repository_ref")):
            return row
        evidence = {"signal": "ACTION_REQUIRES_REALITY_REFRESH", "actual_revision": revision,
            "actual_tree": tree, "actual_ref": branch,
            "trusted_snapshot_id": None if snapshot is None else str(snapshot.id)}
        paths = self._git(path, "ls-tree", "-r", "--name-only", revision).splitlines()
        refreshed = {**row, "condition": "READY" if trusted else "BLOCKED",
            "revision": revision, "tree": tree, "repository_ref": branch,
            "branches": self._git(path, "for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines(),
            "paths": paths[:200],
            "technical_evidence": evidence,
            "human_message": "Repository reflects the trusted current Runtime baseline." if trusted
                else "Repository differs from its trusted owner baseline; no new action is authorized."}
        if trusted:
            refreshed["observed_at"] = pointer.updated_at.isoformat()
            refreshed["current_trusted_snapshot_id"] = str(snapshot.id)
        refreshed["fingerprint"] = canonical_fingerprint({k:v for k,v in refreshed.items() if k != "fingerprint"})
        return refreshed

    def research_context(self, *, turn_id: UUID, interaction_id: UUID,
                         source: str, authority_identity: str, observation: dict | None = None) -> dict:
        """Observe a Human-supplied repository for advice without admitting Work.

        Acquisition reuses durable Asset intake. Only committed, bounded text is
        supplied as untrusted Evidence; no branch, PWU or Delivery is created.
        """
        observation = observation or self.intake(RepositoryIntakeRequest(
            request_id=uuid5(NAMESPACE_URL, f"interaction-research:{turn_id}:{source}"),
            source=source, title="Interaction repository research",
            description="Read committed project context for the Human's research request",
            authority_identity=authority_identity, interaction_id=interaction_id,
        ))
        packet = {key: observation.get(key) for key in (
            "intake_request_id", "condition", "repository_identity", "revision",
            "tree", "observed_at", "failure_category")}
        packet["materials"] = []
        if observation.get("condition") != "READY":
            return packet
        with self.database.unit_of_work() as uow:
            resource = ProductStore(uow.session).resource(UUID(observation["resource_id"]))
        if resource is None:
            raise ProductRecordNotFound("Research repository Asset is unavailable")
        repository = Path(resource.location_ref)
        suffixes = {".md", ".py", ".js", ".cjs", ".mjs", ".ts", ".tsx",
                    ".html", ".css", ".json", ".toml", ".sql"}
        observed_paths = self._git(repository, 'ls-tree', '-r', '--name-only', observation['revision']).splitlines()
        paths = tuple(path for path in observed_paths
            if Path(path).suffix.lower() in suffixes
            and not any(part.startswith('.') for part in Path(path).parts)
            and not any(part in {"node_modules", "vendor", "dist", "build"} for part in Path(path).parts))
        paths = sorted(paths, key=lambda path: (
            path not in {"package.json", "pyproject.toml"},
            not Path(path).name.lower().startswith('readme'), path))[:8]
        remaining = 24000
        for path in paths:
            raw = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(repository),
                "show", f"{observation['revision']}:{path}"], check=True,
                capture_output=True, timeout=15).stdout
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if remaining <= 0:
                break
            excerpt = content[:min(8000, remaining)]
            remaining -= len(excerpt)
            packet["materials"].append({"path": path, "content": excerpt,
                "content_sha256": sha256(raw).hexdigest(),
                "truncated": len(content) != len(excerpt)})
        packet["bounded_inspection"] = True
        return packet

    def list_assets(self, work_id=None):
        with self.database.unit_of_work() as uow:
            observations = uow.session.execute(select(repository_intakes.c.observation).where(repository_intakes.c.observation.is_not(None))).scalars().all()
            product = ProductStore(uow.session)
            scope = None if work_id is None else product.scope_for_work(work_id)
            bound = set() if scope is None else {str(item.resource_id) for item in scope.bindings}
            selected = None if work_id is None else product.resource_for_work(work_id)
            return [{**row, "bound": row["resource_id"] is not None and row["resource_id"] in bound,
                "selected_for_production": selected is not None and str(selected.id) == row["resource_id"]} for row in observations]
