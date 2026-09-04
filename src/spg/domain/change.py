"""Narrow governed contracts for bounded single-PWU code changes."""

from enum import StrEnum
from pathlib import PurePosixPath
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProductionTargetKind(StrEnum):
    DOCUMENTATION_WORK = "DOCUMENTATION_WORK"
    CODE_WORK = "CODE_WORK"


class ChangeTargetShape(StrEnum):
    EXACT_TARGET_SET = "EXACT_TARGET_SET"
    BOUNDED_REPOSITORY_AREAS = "BOUNDED_REPOSITORY_AREAS"
    EXACT_AND_BOUNDED = "EXACT_AND_BOUNDED"


class ChangeOperation(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"


class CodeVerificationKind(StrEnum):
    PATH_SCOPE = "PATH_SCOPE"
    GIT_DIFF_CHECK = "GIT_DIFF_CHECK"
    PYTHON_COMPILE = "PYTHON_COMPILE"
    PYTEST_TARGET = "PYTEST_TARGET"
    IMPORT_CHECK = "IMPORT_CHECK"
    NODE_TEST_TARGET = "NODE_TEST_TARGET"


class CodeChangeTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    operation: ChangeOperation

    @field_validator("path")
    @classmethod
    def normalize_path(cls, value: str) -> str:
        return safe_repository_path(value)


class CodeVerificationObligation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: CodeVerificationKind
    target: str | None = None

    @model_validator(mode="after")
    def require_typed_target(self) -> "CodeVerificationObligation":
        if self.kind in {
            CodeVerificationKind.PYTEST_TARGET,
            CodeVerificationKind.NODE_TEST_TARGET,
        }:
            if self.target is None:
                raise ValueError(
                    f"{self.kind.value} requires a repository-relative target"
                )
            object.__setattr__(self, "target", safe_repository_path(self.target))
            if self.kind is CodeVerificationKind.NODE_TEST_TARGET and (
                not self.target.startswith("tests/")
                or PurePosixPath(self.target).suffix.casefold()
                not in {".js", ".cjs", ".mjs"}
            ):
                raise ValueError(
                    "NODE_TEST_TARGET requires a JavaScript test below tests/"
                )
        elif self.kind is CodeVerificationKind.IMPORT_CHECK:
            if self.target is None or not re.fullmatch(
                r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", self.target
            ):
                raise ValueError("IMPORT_CHECK requires a dotted Python module")
        elif self.target is not None:
            raise ValueError(f"{self.kind.value} does not accept a target")
        return self

    @property
    def identity(self) -> str:
        return self.kind.value if self.target is None else f"{self.kind.value}:{self.target}"


class CodeChangeContract(BaseModel):
    """Exact Human-admitted write and Verification boundary for code Work."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_kind: ProductionTargetKind = ProductionTargetKind.CODE_WORK
    target_shape: ChangeTargetShape
    engineering_resource_id: UUID
    repository_identity: str = Field(min_length=1)
    source_baseline_id: UUID
    source_revision: str = Field(min_length=1)
    desired_outcome: str = Field(min_length=1)
    constraints: tuple[str, ...] = ()
    exact_targets: tuple[CodeChangeTarget, ...] = ()
    allowed_areas: tuple[str, ...] = ()
    forbidden_areas: tuple[str, ...] = ()
    verification_obligations: tuple[CodeVerificationObligation, ...] = ()
    source_proposal_id: UUID | None = None
    source_proposal_fingerprint: str | None = None

    @field_validator("allowed_areas")
    @classmethod
    def normalize_allowed_areas(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(safe_repository_area(value) for value in values))

    @field_validator("forbidden_areas")
    @classmethod
    def normalize_forbidden_areas(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(safe_repository_scope(value) for value in values))

    @model_validator(mode="after")
    def require_bounded_authority(self) -> "CodeChangeContract":
        if self.target_kind is not ProductionTargetKind.CODE_WORK:
            raise ValueError("Code Change Contract target kind must be CODE_WORK")
        exact_paths = tuple(target.path for target in self.exact_targets)
        if len(exact_paths) != len(set(exact_paths)):
            raise ValueError("Code Change Contract exact targets must be unique")
        if not self.exact_targets and not self.allowed_areas:
            raise ValueError("Code Change Contract cannot grant an empty or repository-wide scope")
        expected_shape = (
            ChangeTargetShape.EXACT_AND_BOUNDED
            if self.exact_targets and self.allowed_areas
            else ChangeTargetShape.EXACT_TARGET_SET
            if self.exact_targets
            else ChangeTargetShape.BOUNDED_REPOSITORY_AREAS
        )
        if self.target_shape is not expected_shape:
            raise ValueError("Code Change Contract target shape does not match its boundaries")
        identities = tuple(item.identity for item in self.verification_obligations)
        if len(identities) != len(set(identities)):
            raise ValueError("Code Verification obligations must be unique")
        required = {
            CodeVerificationKind.PATH_SCOPE,
            CodeVerificationKind.GIT_DIFF_CHECK,
        }
        kinds = {item.kind for item in self.verification_obligations}
        if not required <= kinds:
            raise ValueError("Code Change Contract requires PATH_SCOPE and GIT_DIFF_CHECK")
        for obligation in self.verification_obligations:
            if (
                obligation.kind
                in {
                    CodeVerificationKind.PYTEST_TARGET,
                    CodeVerificationKind.NODE_TEST_TARGET,
                }
                and obligation.target is not None
                and not self.allows_path(obligation.target)
            ):
                raise ValueError(
                    f"{obligation.kind.value} must be inside the admitted change boundary"
                )
            if obligation.kind is CodeVerificationKind.IMPORT_CHECK:
                candidates = python_module_paths(obligation.target or "")
                if not any(self.allows_path(path) for path in candidates):
                    raise ValueError("IMPORT_CHECK module must map inside the admitted change boundary")
        if (self.source_proposal_id is None) != (
            self.source_proposal_fingerprint is None
        ):
            raise ValueError("Change Contract Proposal provenance must be complete")
        return self

    def allows_path(self, path: str) -> bool:
        normalized = safe_repository_path(path)
        if any(path_matches_scope(normalized, scope) for scope in self.forbidden_areas):
            return False
        if normalized in {target.path for target in self.exact_targets}:
            return True
        return any(path_matches_scope(normalized, area) for area in self.allowed_areas)

    @property
    def verification_identities(self) -> tuple[str, ...]:
        return tuple(item.identity for item in self.verification_obligations)


def safe_repository_path(value: str) -> str:
    raw = value.strip()
    if "\\" in raw:
        raise ValueError("repository paths must use POSIX separators")
    if not raw or raw in {".", "**", "**/*"} or re.match(r"^[A-Za-z]:", raw):
        raise ValueError("repository path must be a bounded repository-relative path")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or ".git" in path.parts:
        raise ValueError("repository path is unsafe or addresses Git internals")
    if any(part in {"*", "**"} for part in path.parts):
        raise ValueError("exact repository paths cannot contain wildcards")
    return str(path)


def safe_repository_area(value: str) -> str:
    raw = value.strip().rstrip("/")
    if not raw.endswith("/**"):
        raise ValueError("bounded repository areas must end with /**")
    prefix = raw[:-3].rstrip("/")
    safe_repository_path(prefix)
    return f"{prefix}/**"


def safe_repository_scope(value: str) -> str:
    raw = value.strip().rstrip("/")
    return safe_repository_area(raw) if raw.endswith("/**") else safe_repository_path(raw)


def path_matches_scope(path: str, scope: str) -> bool:
    normalized = safe_repository_path(path)
    if scope.endswith("/**"):
        prefix = scope[:-3].rstrip("/")
        return normalized == prefix or normalized.startswith(f"{prefix}/")
    return normalized == safe_repository_path(scope)


def python_module_paths(module: str) -> tuple[str, ...]:
    stem = module.replace(".", "/")
    return (
        f"src/{stem}.py",
        f"src/{stem}/__init__.py",
        f"{stem}.py",
        f"{stem}/__init__.py",
    )
