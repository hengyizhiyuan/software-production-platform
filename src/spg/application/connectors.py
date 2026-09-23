"""Narrow resolution of executable capability against governed Work obligations."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import and_, insert, or_, select, update

from spg.application.production_intelligence import default_system_capability_reality
from spg.domain.connectors import (
    CapabilityRequirement,
    CapabilityScope,
    ConnectorCandidate,
    ConnectorAvailability,
    ConnectorMaturity,
    ConnectorResolution,
    ExecutableCapability,
    SideEffectLevel,
)
from spg.domain.native_execution import AttemptTerminalOutcome, EffectCondition, ExecutionMode
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.persistence.connector_schema import capability_gaps, connector_capabilities


class ConnectorResolver:
    """Capability truth only; callers retain Work and Delivery authority checks."""

    def __init__(self, database) -> None:
        self.database = database

    def register_learned(self, capability: ExecutableCapability) -> None:
        if capability.scope not in {CapabilityScope.WORK, CapabilityScope.USER}:
            raise ValueError("runtime promotion supports only WORK and USER")
        if capability.scope is CapabilityScope.WORK and capability.owner_id != str(capability.created_from_work):
            raise ValueError("WORK connector must belong to its originating Work")
        if capability.availability is ConnectorAvailability.AVAILABLE:
            providers = {
                item.execution_provider
                for item in default_system_capability_reality().executable_capabilities
                if item.availability is ConnectorAvailability.AVAILABLE
            }
            if capability.execution_provider not in providers:
                raise ValueError("learned capability provider is not installed")
        now = datetime.now(UTC)
        identity = uuid5(
            NAMESPACE_URL,
            f"watt:connector:{capability.scope}:{capability.owner_id}:{capability.capability_id}:{capability.version}",
        )
        with self.database.unit_of_work() as uow:
            existing = uow.session.execute(
                select(connector_capabilities.c.id).where(connector_capabilities.c.id == identity)
            ).scalar_one_or_none()
            if existing is not None:
                raise ValueError("connector version already registered; register a new version")
            uow.session.execute(insert(connector_capabilities).values(
                id=identity,
                owner_scope=capability.scope.value,
                owner_id=capability.owner_id,
                capability_id=capability.capability_id,
                version=capability.version,
                definition=capability.model_dump(mode="json"),
                enabled=capability.enabled,
                created_at=now,
                updated_at=now,
            ))
            uow.commit()

    def propose_generic_candidate(self, requirement: CapabilityRequirement) -> ConnectorCandidate | None:
        """Inspect installed generic Native tools, preserving the interrupted Work gap."""

        resolution = self.resolve(requirement)
        source = resolution.capability
        if (
            resolution.executable or resolution.gap_id is None or source is None
            or source.availability is not ConnectorAvailability.ADAPTER_READY
            or source.credential_requirements
            or source.side_effect_level in {SideEffectLevel.EXTERNAL_WRITE, SideEffectLevel.DESTRUCTIVE}
            or not source.execution_provider.startswith("native-tool:")
        ):
            return None
        installed = {
            item.execution_provider
            for item in default_system_capability_reality().executable_capabilities
            if item.availability is ConnectorAvailability.AVAILABLE
        }
        if source.execution_provider not in installed:
            return None
        return ConnectorCandidate(
            requirement=requirement,
            gap_id=resolution.gap_id,
            execution_provider=source.execution_provider,
            qualification_tool_identity=source.execution_provider.removeprefix("native-tool:"),
            side_effect_level=source.side_effect_level,
            permissions_required=source.permissions_required,
            provenance=(f"capability-gap:{resolution.gap_id}", *source.provenance),
        )

    def admit_qualified_candidate(
        self, candidate: ConnectorCandidate, *, qualification_attempt_id: UUID,
    ) -> ExecutableCapability:
        """Admit only a settled PE-bound Native sandbox result for this exact Work."""

        with self.database.unit_of_work() as uow:
            native = NativeExecutionStore(uow.session)
            binding = native.attempt_binding(qualification_attempt_id)
            state = native.attempt_state(qualification_attempt_id)
            checkpoint = native.latest_checkpoint(qualification_attempt_id)
            effects = native.effects_for_attempt(qualification_attempt_id)
        if binding.binding.work_id != candidate.requirement.work_id:
            raise ValueError("qualification Attempt belongs to a different Work")
        if not binding.binding.workspace.service_resources:
            raise ValueError("generic adapter qualification requires an isolated Production Environment")
        if (
            state.runtime_mode is not ExecutionMode.FINISHED
            or state.terminal_outcome is not AttemptTerminalOutcome.RESULT_READY
            or checkpoint is None or checkpoint.id != state.current_checkpoint_id
        ):
            raise ValueError("generic adapter has no successful durable Native checkpoint")
        matching = tuple(
            effect for effect in effects
            if effect.tool_identity == candidate.qualification_tool_identity
            and effect.condition is EffectCondition.SETTLED
        )
        if not matching:
            raise ValueError("generic adapter was not exercised by a settled Native tool effect")
        requirement = candidate.requirement
        capability = ExecutableCapability(
            capability_id=requirement.capability_id,
            connector_id=f"learned:{candidate.execution_provider}",
            capability_family=requirement.capability_id.split(".", 1)[0],
            operation=requirement.capability_id.split(".", 1)[-1],
            scope=CapabilityScope.WORK,
            owner_id=str(requirement.work_id),
            maturity=ConnectorMaturity.PROVISIONAL,
            availability=ConnectorAvailability.AVAILABLE,
            permissions_required=candidate.permissions_required,
            side_effect_level=candidate.side_effect_level,
            execution_provider=candidate.execution_provider,
            version=f"1-{str(qualification_attempt_id)[:8]}",
            provenance=(*candidate.provenance, f"native-attempt:{qualification_attempt_id}"),
            created_from_work=requirement.work_id,
            verification_evidence=(
                f"native-checkpoint:{checkpoint.id}",
                *(f"native-effect:{effect.id}" for effect in matching),
            ),
        )
        existing = next(
            (
                item for item in self._overlays(requirement)
                if item.scope is CapabilityScope.WORK and item.version == capability.version
            ),
            None,
        )
        if existing is not None:
            if existing != capability:
                raise ValueError("qualified Connector version conflicts with persisted Work capability")
            self._resolve_gap(requirement)
            return existing
        self.register_learned(capability)
        self._resolve_gap(requirement)
        return capability

    def retain_successful_work_capability_for_user(
        self,
        requirement: CapabilityRequirement,
        *,
        successful_execution_evidence: str,
    ) -> ExecutableCapability | None:
        """Retain a qualified reusable adapter only for the originating Human."""

        if not successful_execution_evidence.startswith("native-checkpoint:"):
            raise ValueError("USER retention requires a durable successful Native checkpoint")
        try:
            checkpoint_id = UUID(successful_execution_evidence.removeprefix("native-checkpoint:"))
        except ValueError as error:
            raise ValueError("USER retention requires a real Native checkpoint identity") from error
        with self.database.unit_of_work() as uow:
            native = NativeExecutionStore(uow.session)
            checkpoint = native.checkpoint(checkpoint_id)
            if checkpoint is None:
                raise ValueError("USER retention checkpoint does not exist")
            binding = native.attempt_binding(checkpoint.attempt_id)
            state = native.attempt_state(checkpoint.attempt_id)
        if (
            binding.binding.work_id != requirement.work_id
            or state.runtime_mode is not ExecutionMode.FINISHED
            or state.terminal_outcome is not AttemptTerminalOutcome.RESULT_READY
            or state.current_checkpoint_id != checkpoint_id
        ):
            raise ValueError("USER retention requires a successful checkpoint for this Work")
        if requirement.user_id == "system":
            return None
        work_capability = next(
            (
                item for item in self._overlays(requirement)
                if item.scope is CapabilityScope.WORK
                and item.maturity is ConnectorMaturity.PROVISIONAL
                and item.availability is ConnectorAvailability.AVAILABLE
                and not item.secret_references
                and not item.credential_requirements
            ),
            None,
        )
        if work_capability is None:
            return None
        retained = work_capability.model_copy(update={
            "scope": CapabilityScope.USER,
            "owner_id": requirement.user_id,
            "provenance": (*work_capability.provenance, successful_execution_evidence),
            "verification_evidence": (
                *work_capability.verification_evidence,
                successful_execution_evidence,
            ),
        })
        existing = next(
            (
                item for item in self._overlays(requirement)
                if item.scope is CapabilityScope.USER
                and item.version == retained.version
            ),
            None,
        )
        if existing is not None:
            if (
                existing.execution_provider != retained.execution_provider
                or existing.created_from_work != retained.created_from_work
            ):
                raise ValueError("USER connector version conflicts with existing ownership")
            return existing
        self.register_learned(retained)
        return retained

    def _overlays(self, requirement: CapabilityRequirement) -> tuple[ExecutableCapability, ...]:
        with self.database.unit_of_work() as uow:
            rows = uow.session.execute(
                select(connector_capabilities).where(
                    connector_capabilities.c.capability_id == requirement.capability_id,
                    connector_capabilities.c.enabled.is_(True),
                    or_(
                        and_(
                            connector_capabilities.c.owner_scope == CapabilityScope.WORK.value,
                            connector_capabilities.c.owner_id == str(requirement.work_id),
                        ),
                        and_(
                            connector_capabilities.c.owner_scope == CapabilityScope.USER.value,
                            connector_capabilities.c.owner_id == requirement.user_id,
                        ),
                    ),
                )
            ).mappings().all()
        visible = []
        for row in rows:
            if (row["owner_scope"], row["owner_id"]) not in {
                (CapabilityScope.WORK.value, str(requirement.work_id)),
                (CapabilityScope.USER.value, requirement.user_id),
            }:
                continue
            visible.append(ExecutableCapability.model_validate(row["definition"]))
        return tuple(sorted(
            visible,
            key=lambda item: (
                item.scope is CapabilityScope.WORK,
                item.version,
            ),
            reverse=True,
        ))

    def visible_capabilities(
        self, work_id: UUID, user_id: str
    ) -> tuple[ExecutableCapability, ...]:
        """Project current executable truth for one Work and one Human owner."""

        with self.database.unit_of_work() as uow:
            rows = uow.session.execute(
                select(connector_capabilities).where(
                    connector_capabilities.c.enabled.is_(True),
                    or_(
                        and_(
                            connector_capabilities.c.owner_scope == CapabilityScope.WORK.value,
                            connector_capabilities.c.owner_id == str(work_id),
                        ),
                        and_(
                            connector_capabilities.c.owner_scope == CapabilityScope.USER.value,
                            connector_capabilities.c.owner_id == user_id,
                        ),
                    ),
                )
            ).mappings().all()
        grouped: dict[str, list[ExecutableCapability]] = {}
        for row in rows:
            if (row["owner_scope"], row["owner_id"]) not in {
                (CapabilityScope.WORK.value, str(work_id)),
                (CapabilityScope.USER.value, user_id),
            }:
                continue
            item = ExecutableCapability.model_validate(row["definition"])
            grouped.setdefault(item.capability_id, []).append(item)
        for item in default_system_capability_reality().executable_capabilities:
            grouped.setdefault(item.capability_id, []).append(item)
        selected = []
        for capability_id, candidates in grouped.items():
            candidates.sort(
                key=lambda item: (
                    item.scope is CapabilityScope.WORK,
                    item.scope is CapabilityScope.USER,
                    item.version,
                ),
                reverse=True,
            )
            selected.append(next(
                (
                    item for item in candidates
                    if item.enabled and item.availability is ConnectorAvailability.AVAILABLE
                ),
                candidates[0],
            ))
        return tuple(sorted(selected, key=lambda item: item.capability_id))

    def resolve(
        self,
        requirement: CapabilityRequirement,
        *,
        record_gap: bool = True,
    ) -> ConnectorResolution:
        built_ins = default_system_capability_reality().executable_capabilities
        matches = self._overlays(requirement) + tuple(
            item for item in built_ins if item.capability_id == requirement.capability_id
        )
        executable = next(
            (
                item for item in matches
                if item.enabled and item.availability is ConnectorAvailability.AVAILABLE
            ),
            None,
        )
        if executable is not None:
            if record_gap:
                self._resolve_gap(requirement)
            return ConnectorResolution(
                requirement=requirement,
                capability=executable,
                executable=True,
                reason="Executable connector is available; Work authority remains separately required.",
            )
        candidate = next(iter(matches), None)
        reason = (
            "Connector requires external authorization or credentials."
            if candidate is not None
            and candidate.availability is ConnectorAvailability.AUTHORIZATION_REQUIRED
            else "No executable provider is installed; external authorization will also be required."
            if candidate is not None
            and candidate.availability is ConnectorAvailability.UNAVAILABLE
            and candidate.credential_requirements
            else "A generic adapter exists but this Work needs a sandbox-qualified binding."
            if candidate is not None
            and candidate.availability is ConnectorAvailability.ADAPTER_READY
            else "No executable connector is installed for this capability."
        )
        gap_id = self._record_gap(requirement, reason) if record_gap else None
        return ConnectorResolution(
            requirement=requirement,
            capability=candidate,
            executable=False,
            reason=reason,
            gap_id=gap_id,
        )

    def require_local_execution(self, requirement: CapabilityRequirement) -> ExecutableCapability:
        resolution = self.resolve(requirement)
        if not resolution.executable or resolution.capability is None:
            raise RuntimeError(f"CAPABILITY_GAP:{requirement.capability_id}:{resolution.gap_id}")
        if resolution.capability.side_effect_level in {
            SideEffectLevel.EXTERNAL_WRITE,
            SideEffectLevel.DESTRUCTIVE,
        }:
            raise ValueError("external or destructive operations require separate Work authorization")
        return resolution.capability

    def _record_gap(self, requirement: CapabilityRequirement, reason: str) -> UUID:
        identity = uuid5(
            NAMESPACE_URL,
            f"watt:capability-gap:{requirement.work_id}:{requirement.capability_id}:{requirement.operation_ref}",
        )
        with self.database.unit_of_work() as uow:
            existing = uow.session.execute(
                select(capability_gaps.c.id).where(capability_gaps.c.id == identity)
            ).scalar_one_or_none()
            if existing is None:
                uow.session.execute(insert(capability_gaps).values(
                    id=identity,
                    work_id=requirement.work_id,
                    capability_id=requirement.capability_id,
                    operation_ref=requirement.operation_ref,
                    resume_point=requirement.resume_point,
                    condition="OPEN",
                    reason=reason,
                    created_at=datetime.now(UTC),
                ))
            else:
                uow.session.execute(update(capability_gaps).where(capability_gaps.c.id == identity).values(
                    condition="OPEN", reason=reason, resolved_at=None,
                ))
            uow.commit()
        return identity

    def _resolve_gap(self, requirement: CapabilityRequirement) -> None:
        identity = uuid5(
            NAMESPACE_URL,
            f"watt:capability-gap:{requirement.work_id}:{requirement.capability_id}:{requirement.operation_ref}",
        )
        with self.database.unit_of_work() as uow:
            uow.session.execute(update(capability_gaps).where(capability_gaps.c.id == identity).values(
                condition="RESOLVED", resolved_at=datetime.now(UTC),
            ))
            uow.commit()

    def gaps_for_work(self, work_id: UUID) -> tuple[dict, ...]:
        with self.database.unit_of_work() as uow:
            rows = uow.session.execute(
                select(capability_gaps).where(capability_gaps.c.work_id == work_id)
            ).mappings().all()
        return tuple(dict(row) for row in rows)
