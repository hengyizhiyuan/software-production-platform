"""Replaceable Git-backed Managed Source provider boundary.

Only this adapter knows Gitea's API and clone address. Product identities and
accepted revisions are persisted by Watt, not inferred from provider HEAD.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import base64
import json
import os
import re
import subprocess
from tempfile import TemporaryDirectory
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from spg.config import Settings


class ManagedSourceError(RuntimeError):
    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category


@dataclass(frozen=True)
class SourceRevision:
    revision: str
    tree: str


class ManagedSourceProvider(Protocol):
    kind: str
    def provision(self, reference: str, initial_file: str) -> SourceRevision: ...
    def import_repository(self, reference: str, origin: Path) -> SourceRevision: ...
    def inspect(self, reference: str, revision: str) -> SourceRevision: ...
    def materialize(self, reference: str, revision: str, destination: Path, branch: str) -> SourceRevision: ...
    def create_work_lineage(self, reference: str, repository: Path, revision: str, work_ref: str) -> SourceRevision: ...
    def persist_candidate(self, reference: str, repository: Path, revision: str, work_ref: str) -> SourceRevision: ...
    def promote(self, reference: str, revision: str, expected: str) -> SourceRevision: ...
    def clone_access(self, reference: str) -> dict[str, str]: ...


def _git(repository: Path | None, *args: str, env: dict | None = None) -> str:
    command = ["git", "-c", "core.hooksPath=/dev/null"]
    if repository is not None:
        command += ["-C", str(repository)]
    try:
        result = subprocess.run(command + list(args), capture_output=True, text=True,
            timeout=120, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ManagedSourceError("PROVIDER_UNAVAILABLE", "Managed source Git transport is unavailable") from exc
    if result.returncode:
        failure = result.stderr.lower()
        category = ("PERSISTENT_STORAGE_UNAVAILABLE" if "no space left on device" in failure else
                    "AUTHENTICATION_FAILURE" if any(marker in failure for marker in
                        ("authentication failed", "http 401", "http 403")) else
                    "PROVIDER_UNAVAILABLE" if any(marker in failure for marker in
                        ("connection refused", "could not resolve host", "failed to connect")) else
                    "REPOSITORY_MISSING" if any(marker in failure for marker in
                        ("repository not found", "not found", "http 404")) else
                    "SOURCE_REVISION_MISSING" if any(marker in failure for marker in
                        ("unknown revision", "not a valid object name")) else
                    "SOURCE_OPERATION_FAILED")
        raise ManagedSourceError(category, "Managed source Git operation failed")
    return result.stdout.strip()


class GiteaManagedSourceProvider:
    kind = "gitea"

    def __init__(self, settings: Settings):
        if (settings.managed_source_provider != "gitea" or not settings.managed_source_endpoint
                or not settings.managed_source_username or not settings.managed_source_password):
            raise ManagedSourceError("PROVIDER_UNAVAILABLE", "Managed source provider is not configured")
        self.endpoint = settings.managed_source_endpoint.rstrip("/")
        self.public_endpoint = (settings.managed_source_public_endpoint or self.endpoint).rstrip("/")
        self.username = settings.managed_source_username
        self.password = settings.managed_source_password.get_secret_value()
        self.namespace = settings.managed_source_namespace
        if self.namespace != self.username:
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH",
                "Reference provider namespace must match its owning service account")

    def _api(self, method: str, path: str, payload: dict | None = None) -> dict:
        credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        request = Request(self.endpoint + "/api/v1" + path,
            data=None if payload is None else json.dumps(payload).encode(), method=method,
            headers={"Authorization": "Basic " + credentials,
                     "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urlopen(request, timeout=15) as response:
                return json.load(response)
        except HTTPError as exc:
            category = "AUTHENTICATION_FAILURE" if exc.code in (401, 403) else \
                "REPOSITORY_MISSING" if exc.code == 404 else \
                "PERSISTENT_STORAGE_UNAVAILABLE" if exc.code == 507 else "PROVIDER_UNAVAILABLE"
            raise ManagedSourceError(category, f"Managed source API returned HTTP {exc.code}") from exc
        except (URLError, TimeoutError, ValueError) as exc:
            raise ManagedSourceError("PROVIDER_UNAVAILABLE", "Managed source API is unavailable") from exc

    def _url(self, reference: str, *, public: bool = False) -> str:
        if not reference or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in reference):
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Invalid provider repository reference")
        root = self.public_endpoint if public else self.endpoint
        return f"{root}/{quote(self.namespace)}/{reference}.git"

    @staticmethod
    def _exact_revision(revision: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{40,64}", revision):
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Managed source requires an exact revision")

    def _git_env(self) -> dict[str, str]:
        # Askpass keeps credentials out of remote URLs, source control and Git output.
        return {**os.environ, "GIT_TERMINAL_PROMPT": "0",
                "WATT_GIT_USER": self.username, "WATT_GIT_PASSWORD": self.password}

    def _transport(self, directory: Path, *args: str) -> str:
        with TemporaryDirectory(prefix="watt-git-auth-") as temporary:
            askpass = Path(temporary) / "askpass"
            askpass.write_text("#!/bin/sh\ncase \"$1\" in *Username*) printf '%s' \"$WATT_GIT_USER\";; *) printf '%s' \"$WATT_GIT_PASSWORD\";; esac\n")
            askpass.chmod(0o700)
            env = {**self._git_env(), "GIT_ASKPASS": str(askpass)}
            return _git(directory, *args, env=env)

    def _create(self, reference: str) -> bool:
        try:
            self._api("POST", "/user/repos", {"name": reference, "private": True,
                "auto_init": False, "default_branch": "accepted"})
            return True
        except ManagedSourceError as exc:
            if exc.category != "PROVIDER_UNAVAILABLE":
                raise
            # 409 may mean an idempotent retry; inspect the exact expected owner.
            self._api("GET", f"/repos/{quote(self.namespace)}/{quote(reference)}")
            return False

    def resolve_ref(self, reference: str, ref: str = "accepted") -> SourceRevision:
        with TemporaryDirectory(prefix="watt-source-ref-") as temporary:
            repo = Path(temporary) / "source"
            self._transport(Path(temporary), "clone", "--no-checkout", "--",
                self._url(reference), str(repo))
            revision = _git(repo, "rev-parse", f"refs/remotes/origin/{ref}^{{commit}}")
            tree = _git(repo, "rev-parse", f"{revision}^{{tree}}")
            return SourceRevision(revision, tree)

    def provision(self, reference: str, initial_file: str) -> SourceRevision:
        if not self._create(reference):
            existing = self.resolve_ref(reference)
            with TemporaryDirectory(prefix="watt-source-retry-") as temporary:
                checkout = Path(temporary) / "source"
                self.materialize(reference, existing.revision, checkout, "accepted")
                if (_git(checkout, "rev-list", "--count", "HEAD") != "1"
                        or _git(checkout, "ls-tree", "-r", "--name-only", "HEAD") != "README.md"
                        or (checkout / "README.md").read_text(encoding="utf-8") != initial_file):
                    raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH",
                        "Existing provider repository is not the expected Product initialization")
            return existing
        with TemporaryDirectory(prefix="watt-source-init-") as temporary:
            repo = Path(temporary)
            _git(repo, "init", "-b", "accepted")
            _git(repo, "config", "user.name", "Watt Managed Source")
            _git(repo, "config", "user.email", "managed-source@watt.invalid")
            (repo / "README.md").write_text(initial_file, encoding="utf-8")
            _git(repo, "add", "README.md")
            _git(repo, "commit", "-m", "Initialize Watt managed source")
            revision = _git(repo, "rev-parse", "HEAD")
            tree = _git(repo, "rev-parse", "HEAD^{tree}")
            _git(repo, "remote", "add", "origin", self._url(reference))
            self._transport(repo, "push", "origin", "HEAD:refs/heads/accepted")
        return SourceRevision(revision, tree)

    def import_repository(self, reference: str, origin: Path) -> SourceRevision:
        if not origin.is_dir():
            raise ManagedSourceError("EXTERNAL_ORIGIN_UNAVAILABLE", "Import origin is unavailable")
        if not self._create(reference):
            return self.resolve_ref(reference)
        with TemporaryDirectory(prefix="watt-source-import-") as temporary:
            repo = Path(temporary) / "repository"
            try:
                _git(None, "clone", "--no-local", "--", str(origin), str(repo))
            except ManagedSourceError as exc:
                raise ManagedSourceError("IMPORT_FAILURE", "Existing repository import failed") from exc
            revision = _git(repo, "rev-parse", "HEAD")
            tree = _git(repo, "rev-parse", "HEAD^{tree}")
            _git(repo, "remote", "set-url", "origin", self._url(reference))
            self._transport(repo, "push", "origin", f"{revision}:refs/heads/accepted")
        return SourceRevision(revision, tree)

    def materialize(self, reference: str, revision: str, destination: Path, branch: str) -> SourceRevision:
        self._exact_revision(revision)
        if not re.fullmatch(r"[a-z0-9-]+", branch):
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Invalid managed source branch")
        if destination.exists():
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Managed source destination already exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._transport(destination.parent, "clone", "--no-checkout", "--", self._url(reference), str(destination))
        try:
            try:
                resolved = _git(destination, "rev-parse", f"{revision}^{{commit}}")
            except ManagedSourceError as exc:
                raise ManagedSourceError("SOURCE_REVISION_MISSING", "Exact managed source revision is absent") from exc
            if resolved != revision:
                raise ManagedSourceError("SOURCE_REVISION_MISSING", "Exact managed source revision is absent")
            _git(destination, "checkout", "-B", branch, revision)
            tree = _git(destination, "rev-parse", "HEAD^{tree}")
            return SourceRevision(revision, tree)
        except Exception:
            import shutil
            shutil.rmtree(destination, ignore_errors=True)
            raise

    def inspect(self, reference: str, revision: str) -> SourceRevision:
        with TemporaryDirectory(prefix="watt-source-inspect-") as temporary:
            return self.materialize(reference, revision, Path(temporary) / "source", "inspection")

    def create_work_lineage(self, reference: str, repository: Path, revision: str, work_ref: str) -> SourceRevision:
        self._exact_revision(revision)
        if not re.fullmatch(r"refs/heads/work-[0-9a-f]{32}", work_ref):
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Work lineage ref is invalid")
        if _git(repository, "rev-parse", "HEAD") != revision:
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Work source checkout differs from accepted revision")
        tree = _git(repository, "rev-parse", "HEAD^{tree}")
        self._transport(repository, "push", self._url(reference), f"{revision}:{work_ref}")
        branch = work_ref.removeprefix("refs/heads/")
        if self.resolve_ref(reference, branch) != SourceRevision(revision, tree):
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Provider Work ref differs from exact source basis")
        return SourceRevision(revision, tree)

    def persist_candidate(self, reference: str, repository: Path, revision: str, work_ref: str) -> SourceRevision:
        self._exact_revision(revision)
        if not re.fullmatch(r"refs/heads/work-[0-9a-f]{32}", work_ref):
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Candidate Work ref is invalid")
        if _git(repository, "rev-parse", "HEAD") != revision:
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Candidate checkout changed before persistence")
        tree = _git(repository, "rev-parse", "HEAD^{tree}")
        self._transport(repository, "push", self._url(reference), f"{revision}:{work_ref}")
        observed = self.inspect(reference, revision)
        if observed.tree != tree:
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Persisted Candidate tree differs")
        return observed

    def promote(self, reference: str, revision: str, expected: str) -> SourceRevision:
        self._exact_revision(revision)
        self._exact_revision(expected)
        observed = self.inspect(reference, revision)
        current = self.resolve_ref(reference)
        if current.revision == revision:
            return observed
        if current.revision != expected:
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH",
                "Provider accepted ref changed outside the exact Watt promotion basis")
        with TemporaryDirectory(prefix="watt-source-promote-") as temporary:
            repo = Path(temporary) / "source"
            self.materialize(reference, revision, repo, "promotion")
            try:
                _git(repo, "merge-base", "--is-ancestor", expected, revision)
            except ManagedSourceError as exc:
                raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH",
                    "Accepted Candidate does not descend from its Product source basis") from exc
            self._transport(repo, "push", f"--force-with-lease=refs/heads/accepted:{expected}",
                "origin", f"{revision}:refs/heads/accepted")
        if self.resolve_ref(reference) != observed:
            raise ManagedSourceError("SOURCE_IDENTITY_MISMATCH", "Provider accepted ref differs after promotion")
        return observed

    def clone_access(self, reference: str) -> dict[str, str]:
        return {"protocol": "https" if self.public_endpoint.startswith("https:") else "http",
                "url": self._url(reference, public=True),
                "authentication": "Use a separately authorized provider credential"}
