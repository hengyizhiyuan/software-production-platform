"""Persistence adapter for guided design process and agenda revisions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from spg.domain.guided_design import (
    DesignAgendaRevisionCondition,
    DesignAgendaRevisionRecord,
    DesignIssue,
    DesignProcessCondition,
    GuidedDesignProcessRecord,
)
from spg.domain.steering import RealityReference
from spg.infrastructure.persistence.guided_design_schema import (
    guided_design_agenda_revisions,
    guided_design_processes,
)


class GuidedDesignStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_process(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(guided_design_processes).values(**values))

    def insert_revision(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(guided_design_agenda_revisions).values(**values))

    def process_for_work(self, work_id: UUID) -> GuidedDesignProcessRecord | None:
        row = self.session.execute(
            select(guided_design_processes).where(
                guided_design_processes.c.work_id == work_id
            )
        ).mappings().one_or_none()
        return None if row is None else self._process(row)

    def active_revision(self, process_id: UUID) -> DesignAgendaRevisionRecord | None:
        row = self.session.execute(
            select(guided_design_agenda_revisions).where(
                (guided_design_agenda_revisions.c.process_id == process_id)
                & (
                    guided_design_agenda_revisions.c.condition
                    == DesignAgendaRevisionCondition.ACTIVE.value
                )
            )
        ).mappings().one_or_none()
        return None if row is None else self._revision(row)

    def revisions(self, process_id: UUID) -> tuple[DesignAgendaRevisionRecord, ...]:
        rows = self.session.execute(
            select(guided_design_agenda_revisions)
            .where(guided_design_agenda_revisions.c.process_id == process_id)
            .order_by(guided_design_agenda_revisions.c.revision_number)
        ).mappings()
        return tuple(self._revision(row) for row in rows)

    def supersede_revision(self, revision_id: UUID) -> None:
        result = self.session.execute(
            update(guided_design_agenda_revisions)
            .where(
                (guided_design_agenda_revisions.c.id == revision_id)
                & (
                    guided_design_agenda_revisions.c.condition
                    == DesignAgendaRevisionCondition.ACTIVE.value
                )
            )
            .values(condition=DesignAgendaRevisionCondition.SUPERSEDED.value)
        )
        if result.rowcount != 1:
            raise LookupError(f"Active guided design agenda not found: {revision_id}")

    def update_process(
        self,
        process_id: UUID,
        *,
        condition: DesignProcessCondition,
        basis_work_reality_revision_id: UUID | None,
        updated_at,
    ) -> None:
        result = self.session.execute(
            update(guided_design_processes)
            .where(guided_design_processes.c.id == process_id)
            .values(
                condition=condition.value,
                basis_work_reality_revision_id=basis_work_reality_revision_id,
                updated_at=updated_at,
            )
        )
        if result.rowcount != 1:
            raise LookupError(f"Guided design process not found: {process_id}")

    @staticmethod
    def _process(row: Mapping[str, Any]) -> GuidedDesignProcessRecord:
        return GuidedDesignProcessRecord(
            id=row["id"],
            work_id=row["work_id"],
            schema_identity=row["schema_identity"],
            schema_version=row["schema_version"],
            objective=row["objective"],
            condition=DesignProcessCondition(row["condition"]),
            basis_work_reality_revision_id=row["basis_work_reality_revision_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _revision(row: Mapping[str, Any]) -> DesignAgendaRevisionRecord:
        return DesignAgendaRevisionRecord(
            id=row["id"],
            process_id=row["process_id"],
            work_id=row["work_id"],
            revision_number=row["revision_number"],
            condition=DesignAgendaRevisionCondition(row["condition"]),
            supersedes_revision_id=row["supersedes_revision_id"],
            basis_work_reality_revision_id=row["basis_work_reality_revision_id"],
            rationale=row["rationale"],
            reality_refs=tuple(
                RealityReference.model_validate(item) for item in row["reality_refs"]
            ),
            issues=tuple(DesignIssue.model_validate(item) for item in row["issues"]),
            created_at=row["created_at"],
        )
