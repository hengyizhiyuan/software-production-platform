"""Provider-neutral exact execution input materialized before dispatch."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from spg.domain.preparation import (
    ContextSemanticRole,
    PreparedExecutionRequest,
)


class MaterializedContextArtifact(BaseModel):
    """Exact admitted source content supplied to an Executor."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    semantic_role: ContextSemanticRole
    repository_relative_path: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    blob_fingerprint: str = Field(min_length=1)
    content: str


class MaterializedExecutionInputRecord(BaseModel):
    """Immutable exact Provider input with complete governed lineage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    attempt_id: UUID
    generation: int = Field(ge=1)
    production_run_id: UUID
    work_unit_id: UUID
    plan_revision_id: UUID
    source_baseline_id: UUID
    context_package_id: UUID
    context_package_version: int = Field(ge=1)
    context_package_content_fingerprint: str = Field(min_length=1)
    completion_contract_fingerprint: str = Field(min_length=1)
    prepared_execution_request: PreparedExecutionRequest
    instruction_content: str = Field(min_length=1)
    context_projection: Annotated[
        tuple[MaterializedContextArtifact, ...],
        Field(min_length=1),
    ]
    input_fingerprint: str = Field(min_length=1)
    created_at: datetime

    def provider_input(self) -> str:
        """Render the exact deterministic input consumed by a Provider adapter."""

        sections = ["Governed instruction:\n" + self.instruction_content]
        for artifact in self.context_projection:
            sections.append(
                "Admitted context artifact "
                f"[{artifact.semantic_role.value}] "
                f"{artifact.repository_relative_path}\n"
                f"Source revision: {artifact.source_revision}\n"
                f"Blob fingerprint: {artifact.blob_fingerprint}\n"
                "Content:\n"
                f"{artifact.content}"
            )
        return "\n\n".join(sections)
