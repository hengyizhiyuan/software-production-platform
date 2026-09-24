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
BRANCH_FACT_SUBJECTS = frozenset({
    "repository.branch_name",
})
BRANCH_EXTRACTION_SUBJECTS = frozenset({
    "repository.branch", "repository.branch_name", "repository.branch.name",
})
_EXACT_CREATE_COMMAND = re.compile(
    r"^\s*(?:请|帮我)?\s*(?:切\s*(?:一个|一条)?\s*新分支"
    r"|(?:创建|新建)\s*(?:一个|一条)?\s*新?分支)"
    r"\s*[:：\s]\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._/-]{0,127})"
    r"\s*[。！!]?\s*$",
    re.IGNORECASE,
)


def exact_branch_creation_command(content: str) -> str | None:
    """Read an unambiguous new-branch command directly from the Human record."""

    match = _EXACT_CREATE_COMMAND.fullmatch(content)
    return None if match is None else match.group("name")


def explicit_human_branch_command(content: str, proposed_branch: str) -> bool:
    """Validate an extracted branch against the cited Human command once, at binding."""

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", proposed_branch):
        return False
    branch = re.compile(
        rf"(?<![A-Za-z0-9/._-]){re.escape(proposed_branch)}(?![A-Za-z0-9/._-])"
    )
    return bool(
        branch.search(content)
        and _CREATE_BRANCH.search(content)
        and not _NON_COMMAND.search(content)
    )


def governed_branch_creation_target(
    facts: Iterable[EngineeringSemanticFact],
    *,
    record_for_id: Callable[[UUID], InteractionRecord | None],
) -> str | None:
    """Accept only the current canonical branch action and target facts.

    Provider vocabulary is normalized at semantic binding. Downstream action
    selection consumes only the admitted canonical action and target fact.
    """

    del record_for_id
    current = current_semantic_facts(tuple(facts))
    canonical_action = any(
        fact.subject == "repository.branch_action"
        and fact.value == "创建新分支"
        and fact.authority is SemanticFactAuthority.HUMAN_EXPLICIT
        for fact in current
    )
    for fact in current:
        if (
            fact.subject not in BRANCH_FACT_SUBJECTS
            or fact.authority is not SemanticFactAuthority.HUMAN_EXPLICIT
            or not isinstance(fact.value, str)
        ):
            continue
        if fact.qualifiers.get("state") == "to_be_created" and canonical_action:
            return fact.value
    return None
