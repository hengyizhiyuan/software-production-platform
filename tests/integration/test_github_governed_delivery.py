from pathlib import Path
import subprocess
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert
from spg.application.connectors import ConnectorManagement, ConnectorResolver
from spg.domain.connectors import CapabilityRequirement
from spg.infrastructure.persistence.connector_schema import connector_audit_events, connector_controls

from spg.application.github_delivery import (
    GitHubDeliveryError, GitHubDeliveryService, github_repository,
)
from spg.config import Settings
from spg.infrastructure.persistence.product_schema import engineering_resources
from spg.infrastructure.persistence.github_delivery_schema import (
    github_access_grants, remote_delivery_authorizations, remote_delivery_receipts,
)
from spg.infrastructure.production_environment import GitRepositoryAcquirer


pytestmark = pytest.mark.postgresql
URL = "https://github.com/example/watt-case.git"
REVISION = "a" * 40


@pytest.fixture(autouse=True)
def _clean_github_delivery(postgres_database):
    def clean():
        with postgres_database.engine.begin() as connection:
            for table in (remote_delivery_receipts,
                remote_delivery_authorizations, connector_audit_events,
                connector_controls, github_access_grants):
                connection.execute(delete(table))
            connection.execute(delete(engineering_resources).where(
                engineering_resources.c.repository_identity == URL))
    clean()
    yield
    clean()


class _AcceptedDelivery:
    def __init__(self, manifest_id):
        self.manifest_id = manifest_id

    def view(self, work_id):
        return {"deliveries": [{"current": True,
            "acceptance": {"decision": "ACCEPT"},
            "manifest": {"id": str(self.manifest_id),
                "repository_identity": URL,
                "repository_revision": REVISION,
                "software": {"repository_ref": "refs/heads/feature"}}}]}


def test_github_grant_is_separate_from_delivery_authorization(
    postgres_database, monkeypatch,
):
    manifest_id, work_id = uuid4(), uuid4()
    service = GitHubDeliveryService(postgres_database,
        Settings(github_write_token="not-a-real-token"),
        delivery=_AcceptedDelivery(manifest_id))
    with pytest.raises(GitHubDeliveryError, match="write grant"):
        service.authorize("human:owner", work_id=work_id,
            manifest_id=manifest_id, expected_revision=REVISION,
            target_branch="feature", expected_remote_revision=None,
            rationale="Ship the accepted result")
    monkeypatch.setattr(service, "_api", lambda *args, **kwargs:
        {"permissions": {"pull": True, "push": True}})
    grant = service.grant("human:owner", URL, "WRITE")
    assert grant["credential_ref"] == "SPG_GITHUB_WRITE_TOKEN"
    authorization = service.authorize("human:owner", work_id=work_id,
        manifest_id=manifest_id, expected_revision=REVISION,
        target_branch="feature", expected_remote_revision=None,
        rationale="Ship the accepted result")
    assert authorization["condition"] == "AUTHORIZED"
    service.revoke("human:owner", grant_id=__import__("uuid").UUID(grant["grant_id"]))
    with pytest.raises(GitHubDeliveryError, match="write grant"):
        service.push(__import__("uuid").UUID(authorization["authorization_id"]),
            actor_id="human:owner")


def test_rotated_github_credential_requires_fresh_permission_observation(
    postgres_database, monkeypatch,
):
    service = GitHubDeliveryService(postgres_database,
        Settings(github_read_token="first-test-token"))
    observations = []
    def api(*_args, **_kwargs):
        observations.append(True)
        return {"permissions": {"pull": True, "push": False}}
    monkeypatch.setattr(service, "_api", api)
    service.grant("human:owner", URL, "READ")
    service.settings = Settings(github_read_token="rotated-test-token")
    with pytest.raises(GitHubDeliveryError) as failure:
        service.active_token("human:owner", URL, "READ")
    assert failure.value.code == "GRANT_STALE"
    service.grant("human:owner", URL, "READ")
    assert service.active_token("human:owner", URL, "READ") == "rotated-test-token"
    assert len(observations) == 2


def test_p1_q3_connector_disable_health_and_credential_rotation_are_governed(
    postgres_database, monkeypatch,
):
    management = ConnectorManagement(postgres_database)
    capability = next(item for item in management.list()
                      if item["capability_id"] == "git.branch.current" and item["scope"] == "PLATFORM")
    control_id = __import__("uuid").UUID(capability["id"])
    requirement = CapabilityRequirement(capability_id="git.branch.current",
        work_id=uuid4(), user_id="human:owner", operation_ref="p1-q3")
    resolver = ConnectorResolver(postgres_database)
    assert resolver.resolve(requirement, record_gap=False).executable
    management.control(control_id, "human:owner", enabled=False)
    assert not resolver.resolve(requirement, record_gap=False).executable
    management.control(control_id, "human:owner", enabled=True,
        health="UNHEALTHY", failure_code="PROVIDER_DOWN", evidence_ref="probe:p1-q3")
    assert not resolver.resolve(requirement, record_gap=False).executable
    restored = management.control(control_id, "human:owner", health="HEALTHY",
                                  evidence_ref="probe:p1-q3-restored")
    assert restored["failure_count"] == 1
    assert restored["failure_count_scope"] == "HEALTH_OBSERVATIONS"
    assert restored["usage_count"] is None
    assert restored["usage_count_status"] == "NOT_INSTRUMENTED"
    assert restored["last_success_at"] is None
    assert restored["last_success_status"] == "NOT_INSTRUMENTED"
    assert resolver.resolve(requirement, record_gap=False).executable
    assert len(management.history("CONNECTOR", str(control_id))) == 3

    service = GitHubDeliveryService(postgres_database,
        Settings(github_read_token="first-test-token"))
    monkeypatch.setattr(service, "_api", lambda *_args, **_kwargs:
        {"permissions": {"pull": True, "push": False}})
    grant = service.grant("human:owner", URL, "READ")
    assert service.list_grants("human:owner")[0]["credential_status"] == "ACTIVE"
    service.settings = Settings(github_read_token="rotated-test-token")
    assert service.list_grants("human:owner")[0]["credential_status"] == "INVALID"
    with pytest.raises(GitHubDeliveryError, match="renew"):
        service.active_token("human:owner", URL, "READ")
    service.grant("human:owner", URL, "READ")
    assert service.list_grants("human:owner")[0]["credential_status"] == "ACTIVE"
    service.revoke("human:owner", __import__("uuid").UUID(grant["grant_id"]))
    assert service.list_grants("human:owner")[0]["credential_status"] == "REVOKED"
    assert [item["action"] for item in management.history("GITHUB_GRANT", grant["grant_id"])] == [
        "CREATED", "ROTATED", "REVOKED"]


def test_exact_push_observes_remote_and_does_not_repeat_effect(
    postgres_database, monkeypatch, tmp_path: Path,
):
    manifest_id, work_id = uuid4(), uuid4()
    service = GitHubDeliveryService(postgres_database,
        Settings(github_write_token="not-a-real-token"),
        delivery=_AcceptedDelivery(manifest_id))
    monkeypatch.setattr(service, "_api", lambda *args, **kwargs:
        {"permissions": {"pull": True, "push": True}})
    service.grant("human:owner", URL, "WRITE")
    with postgres_database.unit_of_work() as uow:
        uow.session.execute(insert(engineering_resources).values(
            id=uuid4(), kind="REPOSITORY", repository_identity=URL,
            location_ref=str(tmp_path), authoritative_ref="refs/heads/feature",
            context_references=[]))
        uow.commit()
    authorization = service.authorize("human:owner", work_id=work_id,
        manifest_id=manifest_id, expected_revision=REVISION,
        target_branch="feature", expected_remote_revision=None,
        rationale="Ship the accepted result")
    states = iter((None, REVISION))
    monkeypatch.setattr(service, "_branch_revision", lambda *args: next(states))
    pushed = []
    monkeypatch.setattr(service, "_git_push", lambda *args:
        pushed.append(args))
    identity = __import__("uuid").UUID(authorization["authorization_id"])
    first = service.push(identity, actor_id="human:owner")
    second = service.push(identity, actor_id="human:owner")
    assert first == second
    assert first["remote_after"] == REVISION
    assert len(pushed) == 1
    def pr_api(_owner, _repo, path, _token, **_kwargs):
        if path.startswith("/pulls?"):
            return [{"html_url": "https://github.com/example/watt-case/pull/7",
                "number": 7}]
        if path == "/pulls/7":
            return {"head": {"sha": REVISION}, "base": {"ref": "main"}}
        raise AssertionError(path)
    monkeypatch.setattr(service, "_api", pr_api)
    pr = service.create_pull_request(identity, actor_id="human:owner",
        base="main", title="Accepted change", body="Exact revision")
    assert pr["pr_number"] == "7"
    assert service.create_pull_request(identity, actor_id="human:owner",
        base="main", title="Accepted change", body="Exact revision") == pr


def test_repository_parser_rejects_credentials_and_other_hosts():
    assert github_repository(URL) == ("example", "watt-case", URL)
    for invalid in ("https://bad.example/x/y.git",
        "https://token@github.com/x/y.git", "https://github.com/x/y.git?token=secret"):
        with pytest.raises(GitHubDeliveryError):
            github_repository(invalid)


def test_full_system_profile_blocks_push_without_guardian_owner_decision(
    postgres_database, monkeypatch,
):
    service = GitHubDeliveryService(postgres_database,
        Settings(owner_runtime_mode="REQUIRED", github_write_token="not-a-real-token"))
    monkeypatch.setattr(service, "_branch_revision", lambda *args:
        pytest.fail("Remote branch must not be touched before assurance gate"))
    with pytest.raises(GitHubDeliveryError) as failure:
        service.push(uuid4(), actor_id="human:owner")
    assert failure.value.code == "GUARDIAN_GATE_UNAVAILABLE"


def test_private_acquisition_passes_credential_outside_git_arguments(
    monkeypatch, tmp_path: Path,
):
    observed = {}
    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["environment"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, "", "")
    monkeypatch.setattr("spg.infrastructure.production_environment.subprocess.run", fake_run)
    GitRepositoryAcquirer().acquire(tmp_path, URL, tmp_path / "copy",
        credential="secret-read-token")
    assert "secret-read-token" not in " ".join(observed["command"])
    assert observed["environment"]["GIT_CONFIG_KEY_0"] == \
        "http.https://github.com/.extraheader"
