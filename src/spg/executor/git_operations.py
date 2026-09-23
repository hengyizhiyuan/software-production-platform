"""Bounded Git operation recipes for the existing Native Tool Host boundary."""

from __future__ import annotations

import re
from pathlib import PurePosixPath


_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}\Z")
_REVISION = re.compile(r"[0-9a-fA-F]{40,64}\Z")
_READ_ONLY = frozenset({
    "status", "branch.list", "branch.current", "diff", "log",
    "ancestry", "remote.inspect",
})


def _ref(value: object) -> str:
    if not isinstance(value, str) or not _REF.fullmatch(value):
        raise ValueError("Git ref must be a bounded branch or tag name")
    if any(part in {"", ".", ".."} or part.startswith("-") or part.endswith(".lock") for part in value.split("/")):
        raise ValueError("Git ref has unsafe components")
    if ".." in value or "@{" in value or value.endswith(("/", ".")):
        raise ValueError("Git ref has unsafe syntax")
    return value


def _revision(value: object) -> str:
    if not isinstance(value, str) or not _REVISION.fullmatch(value):
        raise ValueError("Git revision must be an exact commit object ID")
    return value.lower()


def _paths(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or len(value) > 100:
        raise ValueError("Git commit requires a bounded list of paths")
    result = []
    for raw in value:
        if not isinstance(raw, str) or "\\" in raw:
            raise ValueError("Git path must be workspace-relative")
        path = PurePosixPath(raw)
        if path.is_absolute() or raw in {"", "."} or ".." in path.parts or ".git" in path.parts:
            raise ValueError("Git path must stay inside the workspace")
        result.append(str(path))
    return tuple(result)


def git_operation_commands(arguments: dict[str, object]) -> tuple[tuple[str, ...], ...]:
    """Return fixed argv recipes; Human/model text never becomes Git options."""

    operation = arguments.get("operation")
    if operation == "status":
        return (("git", "status", "--porcelain=v1", "--untracked-files=all"),)
    if operation == "branch.list":
        return (("git", "branch", "--list", "--format=%(refname:short) %(objectname)"),)
    if operation == "branch.current":
        return (("git", "branch", "--show-current"),)
    if operation == "branch.create":
        return (("git", "-c", "core.hooksPath=/dev/null", "switch", "-c", _ref(arguments.get("branch"))),)
    if operation == "checkout":
        return (("git", "-c", "core.hooksPath=/dev/null", "switch", _ref(arguments.get("branch"))),)
    if operation == "fetch":
        return (("git", "-c", "core.hooksPath=/dev/null", "fetch", "--no-tags", "--no-recurse-submodules", "origin", _ref(arguments.get("branch"))),)
    if operation == "revision.checkout":
        return (("git", "-c", "core.hooksPath=/dev/null", "switch", "--detach", _revision(arguments.get("revision"))),)
    if operation == "diff":
        return (("git", "diff", "--no-ext-diff", "--binary"),)
    if operation == "log":
        return (("git", "log", "-n", "30", "--format=%H %P %s"),)
    if operation == "ancestry":
        return (("git", "merge-base", "--is-ancestor", _revision(arguments.get("ancestor")), _revision(arguments.get("descendant"))),)
    if operation == "commit":
        paths = _paths(arguments.get("paths"))
        message = arguments.get("message")
        if not isinstance(message, str) or not message.strip() or len(message) > 200 or "\n" in message:
            raise ValueError("Git commit requires one bounded message")
        return (
            ("git", "add", "--", *paths),
            ("git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=Watt", "-c", "user.email=watt@localhost", "commit", "-m", message.strip(), "--", *paths),
        )
    if operation == "tag":
        return (("git", "-c", "core.hooksPath=/dev/null", "tag", _ref(arguments.get("tag")), _revision(arguments.get("revision"))),)
    if operation == "remote.inspect":
        return (("git", "remote", "-v"),)
    raise ValueError("Git operation is not installed")


def git_operation_is_read_only(operation: str) -> bool:
    return operation in _READ_ONLY
