"""WIC's advisory action meaning, grounded before existing owners admit effects.

The model interprets speech acts. This contract validates provenance and literal
arguments, not the wording of an imperative. A candidate is never permission.
"""
from enum import StrEnum
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CanonicalOperation(StrEnum):
    ACQUIRE_REPOSITORY = "ACQUIRE_REPOSITORY"
    INSPECT_REPOSITORY = "INSPECT_REPOSITORY"
    CREATE_AND_SWITCH_BRANCH = "CREATE_AND_SWITCH_BRANCH"
    QUERY_BRANCH = "QUERY_BRANCH"
    SEARCH_WEB = "SEARCH_WEB"
    SEARCH_GITHUB = "SEARCH_GITHUB"
    REQUEST_PREVIEW = "REQUEST_PREVIEW"
    REQUEST_DELIVERY = "REQUEST_DELIVERY"
    OTHER = "OTHER"


class ActionSpeechAct(StrEnum):
    EXPLICIT_REQUEST = "EXPLICIT_REQUEST"
    READ_ONLY_QUERY = "READ_ONLY_QUERY"
    DISCUSSION = "DISCUSSION"
    UNRESOLVED = "UNRESOLVED"


class InteractionActionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: CanonicalOperation
    speech_act: ActionSpeechAct
    source_record_id: UUID
    source_text: str = Field(min_length=1)
    target_branch: str | None = None
    repository_source: str | None = None
    confidence: float = Field(ge=0, le=1)


def validate_action_binding(candidate: InteractionActionCandidate, record) -> None:
    """Bind only the current Human record; never borrow a prior request's consent."""
    if (str(record.actor) != "HUMAN" or candidate.source_record_id != record.id
            or candidate.source_text not in record.content):
        raise ValueError("ACTION_SOURCE_NOT_CURRENT_HUMAN")
    if candidate.target_branch is not None:
        branch = candidate.target_branch
        # Literal grounding is intentionally independent of Chinese/English syntax.
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", branch)
                or not re.search(rf"(?<![A-Za-z0-9._/-]){re.escape(branch)}(?![A-Za-z0-9._/-])", candidate.source_text)):
            raise ValueError("ACTION_ARGUMENT_NOT_HUMAN_SUPPLIED")
    if candidate.repository_source is not None and candidate.repository_source not in candidate.source_text:
        raise ValueError("ACTION_ARGUMENT_NOT_HUMAN_SUPPLIED")
    if (candidate.operation is CanonicalOperation.CREATE_AND_SWITCH_BRANCH
            and candidate.speech_act is ActionSpeechAct.EXPLICIT_REQUEST
            and candidate.target_branch is None):
        raise ValueError("ACTION_BRANCH_TARGET_UNRESOLVED")


def executable_repository_actions(candidates, record):
    """Project grounded meaning into the existing Repository Asset owner."""
    from spg.domain.action_admission import ActionFamily
    from spg.domain.repository_actions import RepositoryAction

    actions = []
    families = {
        CanonicalOperation.ACQUIRE_REPOSITORY: ActionFamily.ACQUIRE_REPOSITORY,
        CanonicalOperation.INSPECT_REPOSITORY: ActionFamily.INSPECT,
        CanonicalOperation.QUERY_BRANCH: ActionFamily.INSPECT,
        CanonicalOperation.CREATE_AND_SWITCH_BRANCH: ActionFamily.LOCAL_BRANCH,
    }
    for candidate in candidates:
        validate_action_binding(candidate, record)
        if candidate.speech_act not in {ActionSpeechAct.EXPLICIT_REQUEST, ActionSpeechAct.READ_ONLY_QUERY}:
            continue
        if candidate.confidence < .8 or candidate.operation not in families:
            continue
        family = families[candidate.operation]
        if family is not ActionFamily.INSPECT and candidate.speech_act is not ActionSpeechAct.EXPLICIT_REQUEST:
            continue
        actions.append(RepositoryAction(family, candidate.repository_source, candidate.target_branch))
    return tuple(dict.fromkeys(actions))
