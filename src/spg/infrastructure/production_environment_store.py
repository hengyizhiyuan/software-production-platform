"""Durable local store for the Brownfield Production Environment slice.

Immutable facts are create-only. Mutable current pointers are atomically
replaced and guarded by expected versions inside one process. A distributed
store/lock is deliberately outside this first vertical slice.
"""

from __future__ import annotations

import json
from hashlib import sha256
import os
from pathlib import Path
from threading import RLock
from uuid import UUID, uuid4

from pydantic import BaseModel

from spg.domain.brownfield_delivery import BrownfieldReviewSessionV1
from spg.domain.production_environment import (
    CandidatePreviewSessionV1,
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

    def create_candidate_preview(self, preview: CandidatePreviewSessionV1) -> CandidatePreviewSessionV1:
        with self._lock:
            pointer = self.root / "candidate-previews" / "by-work" / f"{preview.work_id}.json"
            if pointer.exists():
                raise ProductionEnvironmentStoreConflict("Work already has a current Candidate Preview")
            self._write_candidate_preview(preview)
            self._replace_atomic(pointer, preview.model_dump_json(include={"id", "work_id"}))
        return preview

    def current_candidate_preview(self, work_id: UUID) -> CandidatePreviewSessionV1 | None:
        pointer = self.root / "candidate-previews" / "by-work" / f"{work_id}.json"
        if not pointer.exists():
            return None
        preview_id = UUID(json.loads(pointer.read_text(encoding="utf-8"))["id"])
        return self.get_candidate_preview(preview_id)

    def get_candidate_preview(self, preview_id: UUID) -> CandidatePreviewSessionV1 | None:
        return self._read(
            self.root / "candidate-previews" / "sessions" / str(preview_id) / "current.json",
            CandidatePreviewSessionV1,
        )

    def advance_candidate_preview(
        self, before: CandidatePreviewSessionV1, after: CandidatePreviewSessionV1,
    ) -> CandidatePreviewSessionV1:
        if before.id != after.id or after.version != before.version + 1:
            raise ProductionEnvironmentStoreConflict("Candidate Preview transition has invalid lineage")
        with self._lock:
            if self.get_candidate_preview(before.id) != before:
                raise ProductionEnvironmentStoreConflict("Candidate Preview changed before transition")
            self._write_candidate_preview(after)
        return after

    def replace_current_candidate_preview(self, preview: CandidatePreviewSessionV1) -> CandidatePreviewSessionV1:
        with self._lock:
            pointer = self.root / "candidate-previews" / "by-work" / f"{preview.work_id}.json"
            self._write_candidate_preview(preview)
            self._replace_atomic(pointer, preview.model_dump_json(include={"id", "work_id"}))
        return preview

    def _write_candidate_preview(self, preview: CandidatePreviewSessionV1) -> None:
        directory = self.root / "candidate-previews" / "sessions" / str(preview.id)
        encoded = preview.model_dump_json(indent=2)
        self._write_new(directory / "versions" / f"{preview.version}.json", encoded)
        self._replace_atomic(directory / "current.json", encoded)

    def save_candidate_preview_boundary_evidence(
        self, preview_id: UUID, change_reality: dict, guardian_intake: dict,
    ) -> tuple[str, str]:
        directory = self.root / "candidate-previews" / "evidence" / str(preview_id)
        change = directory / "ecf-change-reality.json"
        guardian = directory / "guardian-intake.json"
        with self._lock:
            for path, payload in ((change, change_reality), (guardian, guardian_intake)):
                encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str, indent=2)
                if path.exists():
                    if path.read_text(encoding="utf-8") != encoded:
                        raise ProductionEnvironmentStoreConflict("Preview boundary evidence identity changed")
                else:
                    self._write_new(path, encoded)
        return str(change), str(guardian)

    def save_candidate_preview_failure_detail(self, preview_id: UUID, detail: str) -> dict:
        path = self.root / "candidate-previews" / "evidence" / str(preview_id) / "failure.log"
        encoded = detail[-50_000:]
        with self._lock:
            self._write_new(path, encoded)
        return {"reference": str(path), "sha256": sha256(encoded.encode("utf-8")).hexdigest()}

    def save_candidate_preview_reality_evidence(self, preview_id: UUID,
        version: int, payload: dict) -> str:
        path = (self.root / "candidate-previews" / "evidence" / str(preview_id)
            / "preview-reality" / f"{version}.json")
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str, indent=2)
        with self._lock:
            if path.exists():
                if path.read_text(encoding="utf-8") != encoded:
                    raise ProductionEnvironmentStoreConflict("Preview Reality version changed")
            else:
                self._write_new(path, encoded)
        return str(path)

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

    def _read(self, path: Path, model):
        with self._lock:
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
