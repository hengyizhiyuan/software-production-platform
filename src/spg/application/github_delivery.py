"""GitHub access grants and explicitly authorized exact remote effects."""

from __future__ import annotations

from datetime import UTC, datetime
from contextlib import contextmanager
import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import insert, select, text, update

from spg.application.delivery import DeliveryApplicationService
from spg.infrastructure.persistence.github_delivery_schema import (
    github_access_grants, remote_delivery_authorizations, remote_delivery_receipts,
)
from spg.infrastructure.persistence.product_schema import engineering_resources


class GitHubDeliveryError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class GitHubGrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repository_url: str
    capability: str = Field(pattern="^(READ|WRITE)$")


class RemoteDeliveryAuthorizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    manifest_id: UUID
    expected_revision: str
    target_branch: str
    expected_remote_revision: str | None = None
    rationale: str = Field(min_length=1)


class PullRequestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base: str
    title: str = Field(min_length=1)
    body: str = ""


def github_repository(url: str) -> tuple[str, str, str]:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != "github.com"
            or parsed.port is not None or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment):
        raise GitHubDeliveryError("INVALID_REPOSITORY", "Use a credential-free GitHub HTTPS repository URL")
    match = re.fullmatch(r"/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?", parsed.path)
    if match is None or match[1] in {".", ".."} or match[2] in {".", ".."}:
        raise GitHubDeliveryError("INVALID_REPOSITORY", "GitHub owner and repository are required")
    owner, repo = match[1], match[2]
    return owner, repo, f"https://github.com/{owner}/{repo}.git"


def _valid_branch(branch: str) -> bool:
    if not branch or len(branch) > 200:
        return False
    return subprocess.run(["git", "check-ref-format", "--branch", branch],
        capture_output=True, timeout=5).returncode == 0


class GitHubDeliveryService:
    def __init__(self, database, settings, *, delivery=None):
        self.database = database
        self.settings = settings
        self.delivery = delivery or DeliveryApplicationService(database)

    @contextmanager
    def _effect_lock(self, identity: UUID, effect: str):
        key = int.from_bytes(sha256(f"github:{effect}:{identity}".encode()).digest()[:8],
            byteorder="big", signed=True)
        with self.database.engine.connect().execution_options(
            isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": key})
            try:
                yield
            finally:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})

    def _credential(self, capability: str) -> tuple[str, str]:
        if capability == "READ":
            name, value = "SPG_GITHUB_READ_TOKEN", self.settings.github_read_token
        elif capability == "WRITE":
            name, value = "SPG_GITHUB_WRITE_TOKEN", self.settings.github_write_token
        else:
            raise GitHubDeliveryError("INVALID_CAPABILITY", "Unknown GitHub grant capability")
        if value is None or not value.get_secret_value():
            raise GitHubDeliveryError("CREDENTIAL_REQUIRED", f"{name} is not configured")
        return name, value.get_secret_value()

    @staticmethod
    def _api(owner: str, repo: str, path: str, token: str,
        *, method: str = "GET", payload: dict | None = None) -> dict | None:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}{path}",
            data=body, method=method, headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                **({"Content-Type": "application/json"} if body is not None else {}),
            })
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read(1_000_000))
        except HTTPError as error:
            if error.code == 404 and method == "GET":
                return None
            raise GitHubDeliveryError("GITHUB_API_FAILED",
                f"GitHub API returned HTTP {error.code}") from error
        except (OSError, URLError, ValueError) as error:
            raise GitHubDeliveryError("GITHUB_API_UNAVAILABLE",
                "GitHub API could not be observed") from error

    def grant(self, actor_id: str, repository_url: str, capability: str) -> dict:
        if actor_id != "human:owner":
            raise GitHubDeliveryError("ACCESS_DENIED", "Current owner authorization is required")
        owner, repo, url = github_repository(repository_url)
        credential_ref, token = self._credential(capability)
        credential_sha256 = sha256(token.encode("utf-8")).hexdigest()
        observed = self._api(owner, repo, "", token)
        if observed is None:
            raise GitHubDeliveryError("REPOSITORY_NOT_FOUND", "GitHub repository is not visible to this credential")
        permissions = observed.get("permissions") or {}
        allowed = permissions.get("pull") is True if capability == "READ" else permissions.get("push") is True
        if not allowed:
            raise GitHubDeliveryError("PERMISSION_DENIED",
                f"GitHub did not confirm {capability.lower()} permission")
        with self.database.unit_of_work() as uow:
            existing = uow.session.execute(select(github_access_grants).where(
                github_access_grants.c.actor_id == actor_id,
                github_access_grants.c.repository_url == url,
                github_access_grants.c.capability == capability,
            )).mappings().one_or_none()
            if existing is None:
                grant_id = uuid4()
                uow.session.execute(insert(github_access_grants).values(
                    id=grant_id, actor_id=actor_id, repository_url=url,
                    capability=capability, credential_ref=credential_ref,
                    credential_sha256=credential_sha256,
                    condition="ACTIVE", observed_permission=permissions))
            else:
                grant_id = existing["id"]
                uow.session.execute(update(github_access_grants).where(
                    github_access_grants.c.id == grant_id).values(
                    credential_ref=credential_ref,
                    credential_sha256=credential_sha256, condition="ACTIVE",
                    observed_permission=permissions, revoked_at=None))
            uow.commit()
        return {"grant_id": str(grant_id), "repository_url": url,
            "capability": capability, "condition": "ACTIVE",
            "credential_ref": credential_ref, "observed_permission": permissions}

    def revoke(self, actor_id: str, grant_id: UUID) -> None:
        with self.database.unit_of_work() as uow:
            result = uow.session.execute(update(github_access_grants).where(
                github_access_grants.c.id == grant_id,
                github_access_grants.c.actor_id == actor_id,
                github_access_grants.c.condition == "ACTIVE").values(
                    condition="REVOKED", revoked_at=datetime.now(UTC)))
            if result.rowcount != 1:
                raise GitHubDeliveryError("GRANT_NOT_FOUND", "Active GitHub grant is unavailable")
            uow.commit()

    def list_grants(self, actor_id: str) -> list[dict]:
        with self.database.unit_of_work() as uow:
            rows = uow.session.execute(select(github_access_grants).where(
                github_access_grants.c.actor_id == actor_id
            )).mappings().all()
        return [{"grant_id": str(row["id"]),
            "repository_url": row["repository_url"],
            "capability": row["capability"], "condition": row["condition"],
            "credential_ref": row["credential_ref"],
            "observed_permission": row["observed_permission"]} for row in rows]

    def active_token(self, actor_id: str, repository_url: str, capability: str) -> str | None:
        _, _, url = github_repository(repository_url)
        with self.database.unit_of_work() as uow:
            grant = uow.session.execute(select(github_access_grants).where(
                github_access_grants.c.actor_id == actor_id,
                github_access_grants.c.repository_url == url,
                github_access_grants.c.capability == capability,
                github_access_grants.c.condition == "ACTIVE",
            )).mappings().one_or_none()
        if grant is None:
            return None
        credential_ref, token = self._credential(capability)
        if (grant["credential_ref"] != credential_ref
                or grant["credential_sha256"] != sha256(token.encode("utf-8")).hexdigest()):
            raise GitHubDeliveryError("GRANT_STALE",
                "GitHub credential changed; observe permission and renew this grant")
        return token

    def _accepted_manifest(self, work_id: UUID, manifest_id: UUID, revision: str) -> dict:
        view = self.delivery.view(work_id)
        match = next((item for item in view["deliveries"]
            if item["manifest"]["id"] == str(manifest_id)), None)
        if (match is None or not match["current"] or match["acceptance"] is None
                or match["acceptance"].get("decision") != "ACCEPT"
                or match["manifest"].get("repository_revision") != revision):
            raise GitHubDeliveryError("HUMAN_ACCEPTANCE_REQUIRED",
                "Exact current software delivery requires Human acceptance")
        manifest = match["manifest"]
        if manifest.get("software") is None:
            raise GitHubDeliveryError("SOFTWARE_REQUIRED", "Remote Git delivery requires a software Candidate")
        return manifest

    def authorize(self, actor_id: str, *, work_id: UUID, manifest_id: UUID,
        expected_revision: str, target_branch: str,
        expected_remote_revision: str | None, rationale: str) -> dict:
        if actor_id != "human:owner":
            raise GitHubDeliveryError("ACCESS_DENIED", "Human owner authority is required")
        if (not re.fullmatch(r"[0-9a-f]{40,64}", expected_revision)
                or expected_remote_revision is not None
                and not re.fullmatch(r"[0-9a-f]{40,64}", expected_remote_revision)
                or not _valid_branch(target_branch) or not rationale.strip()):
            raise GitHubDeliveryError("INVALID_AUTHORIZATION", "Exact remote delivery basis is invalid")
        manifest = self._accepted_manifest(work_id, manifest_id, expected_revision)
        owner, repo, url = github_repository(manifest["repository_identity"])
        if self.active_token(actor_id, url, "WRITE") is None:
            raise GitHubDeliveryError("WRITE_GRANT_REQUIRED", "An active GitHub write grant is required")
        if manifest["software"]["repository_ref"] != f"refs/heads/{target_branch}":
            raise GitHubDeliveryError("BRANCH_MISMATCH", "Delivery branch differs from the exact Candidate")
        authorization_id = uuid4()
        with self.database.unit_of_work() as uow:
            uow.session.execute(insert(remote_delivery_authorizations).values(
                id=authorization_id, work_id=work_id, manifest_id=manifest_id,
                actor_id=actor_id, repository_url=url, target_branch=target_branch,
                expected_revision=expected_revision,
                expected_remote_revision=expected_remote_revision,
                rationale=rationale.strip()))
            uow.commit()
        return {"authorization_id": str(authorization_id), "condition": "AUTHORIZED",
            "repository_url": url, "target_branch": target_branch,
            "expected_revision": expected_revision}

    @staticmethod
    def _git_push(repository: Path, url: str, token: str, revision: str,
        branch: str) -> None:
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        environment = {"PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": f"Authorization: Basic {basic}"}
        result = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C",
            str(repository), "push", "--porcelain", "--", url,
            f"{revision}:refs/heads/{branch}"], env=environment,
            capture_output=True, text=True, timeout=120)
        if result.returncode:
            raise GitHubDeliveryError("PUSH_FAILED",
                "GitHub rejected the exact non-force push; remote state must be re-observed")

    def _branch_revision(self, owner: str, repo: str, branch: str, token: str) -> str | None:
        observed = self._api(owner, repo, f"/branches/{quote(branch, safe='')}", token)
        if observed is None:
            return None
        revision = observed.get("commit", {}).get("sha")
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40,64}", revision):
            raise GitHubDeliveryError("REMOTE_REALITY_INVALID", "GitHub branch revision is unavailable")
        return revision

    def push(self, authorization_id: UUID, *, actor_id: str) -> dict:
        with self._effect_lock(authorization_id, "push"):
            return self._push_locked(authorization_id, actor_id=actor_id)

    def _push_locked(self, authorization_id: UUID, *, actor_id: str) -> dict:
        if self.settings.owner_runtime_mode == "REQUIRED":
            # The independent full-system profile cannot promote a Candidate
            # on Guardian intake alone.  The owner has no decision API yet.
            raise GitHubDeliveryError("GUARDIAN_GATE_UNAVAILABLE",
                "Guardian has not returned an attributable assurance decision for this release")
        with self.database.unit_of_work() as uow:
            authorization = uow.session.execute(select(remote_delivery_authorizations).where(
                remote_delivery_authorizations.c.id == authorization_id)).mappings().one_or_none()
            receipt = uow.session.execute(select(remote_delivery_receipts).where(
                remote_delivery_receipts.c.authorization_id == authorization_id)).mappings().one_or_none()
        if authorization is None:
            raise GitHubDeliveryError("AUTHORIZATION_NOT_FOUND", "Remote delivery authorization is unavailable")
        if authorization["actor_id"] != actor_id:
            raise GitHubDeliveryError("ACCESS_DENIED", "Remote delivery belongs to another actor")
        if receipt is not None:
            return self._receipt(receipt)
        self._accepted_manifest(authorization["work_id"], authorization["manifest_id"],
            authorization["expected_revision"])
        owner, repo, url = github_repository(authorization["repository_url"])
        token = self.active_token(authorization["actor_id"], url, "WRITE")
        if token is None:
            raise GitHubDeliveryError("WRITE_GRANT_REQUIRED", "GitHub write grant is no longer active")
        branch = authorization["target_branch"]
        revision = authorization["expected_revision"]
        remote_before = self._branch_revision(owner, repo, branch, token)
        expected_before = authorization["expected_remote_revision"]
        if remote_before != revision and remote_before != expected_before:
            raise GitHubDeliveryError("REMOTE_DIVERGED", "GitHub branch differs from the Human-authorized remote basis")
        if remote_before != revision:
            with self.database.unit_of_work() as uow:
                path = uow.session.execute(select(engineering_resources.c.location_ref).where(
                    engineering_resources.c.repository_identity.in_((
                        url, url.removesuffix(".git"))))).scalar_one_or_none()
            if path is None:
                raise GitHubDeliveryError("SOURCE_UNAVAILABLE", "Bound Git repository is unavailable")
            self._git_push(Path(path), url, token, revision, branch)
        remote_after = self._branch_revision(owner, repo, branch, token)
        if remote_after != revision:
            raise GitHubDeliveryError("REMOTE_NOT_CONVERGED", "GitHub has not confirmed the exact delivered revision")
        with self.database.unit_of_work() as uow:
            uow.session.execute(insert(remote_delivery_receipts).values(
                authorization_id=authorization_id, remote_before=remote_before,
                remote_after=remote_after, push_condition="OBSERVED"))
            uow.commit()
        return {"authorization_id": str(authorization_id),
            "remote_before": remote_before, "remote_after": remote_after,
            "push_condition": "OBSERVED", "pr_url": None, "pr_number": None}

    @staticmethod
    def _receipt(row) -> dict:
        return {"authorization_id": str(row["authorization_id"]),
            "remote_before": row["remote_before"], "remote_after": row["remote_after"],
            "push_condition": row["push_condition"], "pr_url": row["pr_url"],
            "pr_number": row["pr_number"]}

    def create_pull_request(self, authorization_id: UUID, *, actor_id: str,
        base: str, title: str, body: str) -> dict:
        with self._effect_lock(authorization_id, "pull-request"):
            return self._create_pull_request_locked(authorization_id,
                actor_id=actor_id, base=base, title=title, body=body)

    def _create_pull_request_locked(self, authorization_id: UUID, *, actor_id: str,
        base: str, title: str, body: str) -> dict:
        if not _valid_branch(base) or not title.strip():
            raise GitHubDeliveryError("INVALID_PR", "Pull request base and title are required")
        receipt = self.push(authorization_id, actor_id=actor_id)
        if receipt["pr_url"] is not None:
            return receipt
        with self.database.unit_of_work() as uow:
            authorization = uow.session.execute(select(remote_delivery_authorizations).where(
                remote_delivery_authorizations.c.id == authorization_id)).mappings().one()
        owner, repo, url = github_repository(authorization["repository_url"])
        token = self.active_token(authorization["actor_id"], url, "WRITE")
        if token is None:
            raise GitHubDeliveryError("WRITE_GRANT_REQUIRED", "GitHub write grant is no longer active")
        query = urlencode({"head": f"{owner}:{authorization['target_branch']}",
            "base": base, "state": "open"})
        existing = self._api(owner, repo, f"/pulls?{query}", token)
        observed = existing[0] if isinstance(existing, list) and existing else None
        if observed is None:
            observed = self._api(owner, repo, "/pulls", token,
                method="POST", payload={
                    "head": authorization["target_branch"], "base": base,
                    "title": title.strip(), "body": body,
                })
        if not isinstance(observed, dict) or not isinstance(observed.get("html_url"), str):
            raise GitHubDeliveryError("PR_NOT_OBSERVED", "GitHub did not return a Pull Request")
        pr_number = observed.get("number")
        if not isinstance(pr_number, int):
            raise GitHubDeliveryError("PR_NOT_OBSERVED", "GitHub Pull Request number is unavailable")
        confirmed = self._api(owner, repo, f"/pulls/{pr_number}", token)
        if (not isinstance(confirmed, dict)
                or confirmed.get("head", {}).get("sha") != receipt["remote_after"]
                or confirmed.get("base", {}).get("ref") != base):
            raise GitHubDeliveryError("PR_NOT_CONVERGED",
                "GitHub has not confirmed the Pull Request's exact head and base")
        with self.database.unit_of_work() as uow:
            uow.session.execute(update(remote_delivery_receipts).where(
                remote_delivery_receipts.c.authorization_id == authorization_id).values(
                    pr_url=observed["html_url"], pr_number=str(pr_number)))
            uow.commit()
        return {**receipt, "pr_url": observed["html_url"], "pr_number": str(pr_number)}
