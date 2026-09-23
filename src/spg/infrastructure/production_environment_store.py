"""Durable local store for the Brownfield Production Environment slice.

Immutable facts are create-only. Mutable current pointers are atomically
replaced and guarded by expected versions inside one process. A distributed
store/lock is deliberately outside this first vertical slice.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import RLock
from uuid import UUID, uuid4

from pydantic import BaseModel

from spg.domain.brownfield_delivery import BrownfieldReviewSessionV1
from spg.domain.production_environment import (
    DeliveryIntentV1,
    HumanDeliveryDecision,
    LifecycleTransitionRecord,
    NativeExecutionEnvironmentBindingV1,
    PreviewRuntimeV1,
    ProductionEnvironmentError,
    ProductionEnvironmentV1,
    ProductionRecordV1,
    GitOperationProductionRecordV1,
    ProductionWorkspaceV1,
    ResourceReferenceV1,
)


class ProductionEnvironmentStoreConflict(ProductionEnvironmentError):
    pass


class JsonProductionEnvironmentStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def create_workspace(self, workspace: ProductionWorkspaceV1) -> ProductionWorkspaceV1:
        path = self.root / "workspaces" / f"{workspace.id}.json"
        return self._admit_immutable(path, workspace, ProductionWorkspaceV1)

    def get_workspace(self, workspace_id: UUID) -> ProductionWorkspaceV1 | None:
        return self._read(
            self.root / "workspaces" / f"{workspace_id}.json",
            ProductionWorkspaceV1,
        )

    def create_environment(
        self,
        environment: ProductionEnvironmentV1,
    ) -> ProductionEnvironmentV1:
        with self._lock:
            current = self._environment_current(environment.id)
            if current.exists():
                existing = self._read(current, ProductionEnvironmentV1)
                if existing != environment:
                    raise ProductionEnvironmentStoreConflict(
                        "environment identity already exists"
                    )
                return existing
            self._write_versioned_environment(environment)
            return environment

    def get_environment(self, environment_id: UUID) -> ProductionEnvironmentV1 | None:
        return self._read(
            self._environment_current(environment_id),
            ProductionEnvironmentV1,
        )

    def apply_transition(
        self,
        before: ProductionEnvironmentV1,
        after: ProductionEnvironmentV1,
        transition: LifecycleTransitionRecord,
    ) -> ProductionEnvironmentV1:
        if transition.environment_id != before.id or after.id != before.id:
            raise ProductionEnvironmentStoreConflict("transition identity mismatch")
        if transition.from_state is not before.lifecycle_state:
            raise ProductionEnvironmentStoreConflict("transition basis state mismatch")
        if transition.to_state is not after.lifecycle_state:
            raise ProductionEnvironmentStoreConflict("transition target state mismatch")
        if after.version != before.version + 1:
            raise ProductionEnvironmentStoreConflict("transition must advance one version")
        with self._lock:
            current = self.get_environment(before.id)
            if current is None or current.version != before.version or current != before:
                raise ProductionEnvironmentStoreConflict(
                    "environment changed since transition was decided"
                )
            transition_path = (
                self.root
                / "environments"
                / str(before.id)
                / "transitions"
                / f"{transition.id}.json"
            )
            self._write_new(transition_path, transition.model_dump_json(indent=2))
            self._write_versioned_environment(after)
        return after

    def save_preview(self, preview: PreviewRuntimeV1) -> PreviewRuntimeV1:
        path = self.root / "previews" / f"{preview.id}.json"
        return self._admit_immutable(path, preview, PreviewRuntimeV1)

    def create_delivery_intent(self, intent: DeliveryIntentV1) -> DeliveryIntentV1:
        with self._lock:
            current = self._delivery_current(intent.id)
            if current.exists():
                existing = self._read(current, DeliveryIntentV1)
                if existing != intent:
                    raise ProductionEnvironmentStoreConflict(
                        "delivery intent identity already exists"
                    )
                return existing
            self._write_versioned_delivery(intent)
        return intent

    def get_delivery_intent(self, intent_id: UUID) -> DeliveryIntentV1 | None:
        return self._read(self._delivery_current(intent_id), DeliveryIntentV1)

    def apply_delivery_decision(
        self,
        before: DeliveryIntentV1,
        after: DeliveryIntentV1,
        decision: HumanDeliveryDecision,
    ) -> DeliveryIntentV1:
        if decision.delivery_intent_id != before.id or after.id != before.id:
            raise ProductionEnvironmentStoreConflict("delivery decision identity mismatch")
        if after.version != before.version + 1:
            raise ProductionEnvironmentStoreConflict("delivery decision must advance one version")
        with self._lock:
            current = self.get_delivery_intent(before.id)
            if current is None or current != before:
                raise ProductionEnvironmentStoreConflict(
                    "delivery intent changed since Human decision"
                )
            decision_path = (
                self.root / "delivery-intents" / str(before.id) / "decisions" / f"{decision.id}.json"
            )
            self._write_new(decision_path, decision.model_dump_json(indent=2))
            self._write_versioned_delivery(after)
        return after

    def save_resource_references(
        self,
        references: tuple[ResourceReferenceV1, ...],
    ) -> tuple[ResourceReferenceV1, ...]:
        for reference in references:
            self._admit_immutable(
                self.root / "resource-references" / f"{reference.id}.json",
                reference,
                ResourceReferenceV1,
            )
        return references

    def save_production_record(self, record: ProductionRecordV1) -> ProductionRecordV1:
        path = self.root / "production-records" / f"{record.id}.json"
        return self._admit_immutable(path, record, ProductionRecordV1)

    def save_git_operation_record(self, record: GitOperationProductionRecordV1) -> GitOperationProductionRecordV1:
        path = self.root / "production-records" / f"{record.id}.git-operation.json"
        return self._admit_immutable(path, record, GitOperationProductionRecordV1)

    def get_git_operation_record(self, record_id: UUID) -> GitOperationProductionRecordV1 | None:
        return self._read(
            self.root / "production-records" / f"{record_id}.git-operation.json",
            GitOperationProductionRecordV1,
        )

    def get_production_record(self, record_id: UUID) -> ProductionRecordV1 | None:
        return self._read(
            self.root / "production-records" / f"{record_id}.json",
            ProductionRecordV1,
        )

    def save_review_session(
        self,
        session: BrownfieldReviewSessionV1,
    ) -> BrownfieldReviewSessionV1:
        path = self.root / "review-sessions" / f"{session.id}.json"
        return self._admit_immutable(path, session, BrownfieldReviewSessionV1)

    def get_review_session(self, session_id: UUID) -> BrownfieldReviewSessionV1 | None:
        return self._read(
            self.root / "review-sessions" / f"{session_id}.json",
            BrownfieldReviewSessionV1,
        )

    def save_native_execution_binding(
        self,
        binding: NativeExecutionEnvironmentBindingV1,
    ) -> NativeExecutionEnvironmentBindingV1:
        path = self.root / "native-execution-bindings" / f"{binding.attempt_id}.json"
        return self._admit_immutable(
            path,
            binding,
            NativeExecutionEnvironmentBindingV1,
        )

    def get_native_execution_binding(
        self,
        attempt_id: UUID,
    ) -> NativeExecutionEnvironmentBindingV1 | None:
        return self._read(
            self.root / "native-execution-bindings" / f"{attempt_id}.json",
            NativeExecutionEnvironmentBindingV1,
        )

    def _write_versioned_environment(self, environment: ProductionEnvironmentV1) -> None:
        directory = self.root / "environments" / str(environment.id)
        encoded = environment.model_dump_json(indent=2)
        self._write_new(directory / "versions" / f"{environment.version}.json", encoded)
        self._replace_atomic(directory / "current.json", encoded)

    def _write_versioned_delivery(self, intent: DeliveryIntentV1) -> None:
        directory = self.root / "delivery-intents" / str(intent.id)
        encoded = intent.model_dump_json(indent=2)
        self._write_new(directory / "versions" / f"{intent.version}.json", encoded)
        self._replace_atomic(directory / "current.json", encoded)

    def _environment_current(self, environment_id: UUID) -> Path:
        return self.root / "environments" / str(environment_id) / "current.json"

    def _delivery_current(self, intent_id: UUID) -> Path:
        return self.root / "delivery-intents" / str(intent_id) / "current.json"

    def _admit_immutable(self, path: Path, value: BaseModel, model):
        with self._lock:
            if path.exists():
                existing = model.model_validate_json(path.read_text(encoding="utf-8"))
                if existing != value:
                    raise ProductionEnvironmentStoreConflict(
                        "immutable identity already contains different content"
                    )
                return existing
            self._write_new(path, value.model_dump_json(indent=2))
        return value

    @staticmethod
    def _read(path: Path, model):
        if not path.exists():
            return None
        return model.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_new(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as output:
            output.write(content)

    @staticmethod
    def _replace_atomic(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f".{uuid4().hex}.tmp")
        temporary.write_text(content, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
