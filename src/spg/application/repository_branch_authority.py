"""Resolve branch creation only from admitted Human facts and their source record."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from uuid import UUID

from spg.domain.engineering_semantics import (
    EngineeringSemanticFact,
    SemanticFactAuthority,
    current_semantic_facts,
)
from spg.domain.interaction import InteractionActor, InteractionRecord


_CREATE_BRANCH = re.compile(
    r"(?:创建|新建|create)[^。！？?\n]{0,32}?(?:新分支|分支|new branch|branch)"
    r"|(?:切(?:出|换到)?|checkout|switch to)[^。！？?\n]{0,32}?(?:新分支|new branch)",
    re.IGNORECASE,
)
_NON_COMMAND = re.compile(r"(?:如何|怎么|怎样|为什么|不要|别|不需要|how (?:do|can)|don't|do not)", re.IGNORECASE)


def _cites_explicit_branch_command(
    fact: EngineeringSemanticFact,
    record_for_id: Callable[[UUID], InteractionRecord | None],
) -> bool:
    branch = re.compile(
        rf"(?<![A-Za-z0-9/._-]){re.escape(fact.value)}(?![A-Za-z0-9/._-])"
    )
    for record_id in fact.provenance.source_record_ids:
        record = record_for_id(record_id)
        if (
            record is not None
            and record.actor is InteractionActor.HUMAN
            and branch.search(record.content)
            and _CREATE_BRANCH.search(record.content)
            and not _NON_COMMAND.search(record.content)
        ):
            return True
    return False


def governed_branch_creation_target(
    facts: Iterable[EngineeringSemanticFact],
    *,
    record_for_id: Callable[[UUID], InteractionRecord | None],
) -> str | None:
    """Accept the canonical action fact or an equivalent cited Human command.

    Provider vocabulary such as ``branch_kind=new`` or ``repository.branch`` is
    advisory on its own. It becomes executable only when the cited Human record
    explicitly commands creation of the same branch. Historical Work facts are
    not rewritten.
    """

    current = current_semantic_facts(tuple(facts))
    canonical_action = any(
        fact.subject == "repository.branch_action"
        and fact.value == "创建新分支"
        and fact.authority is SemanticFactAuthority.HUMAN_EXPLICIT
        for fact in current
    )
    for fact in current:
        if (
            fact.subject not in {"repository.branch_name", "repository.branch"}
            or fact.authority is not SemanticFactAuthority.HUMAN_EXPLICIT
            or not isinstance(fact.value, str)
        ):
            continue
        if (
            fact.subject == "repository.branch_name"
            and fact.qualifiers.get("state") == "to_be_created"
            and canonical_action
        ):
            return fact.value
        if (
            fact.subject == "repository.branch_name"
            and fact.qualifiers.get("branch_kind") != "new"
        ):
            continue
        if _cites_explicit_branch_command(fact, record_for_id):
            return fact.value
    return None
