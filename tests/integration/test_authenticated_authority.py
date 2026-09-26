from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import insert

from spg.api.authority import install_authority_boundary
from spg.config import Settings
from spg.infrastructure.persistence.auth_schema import authority_resource_access


pytestmark = pytest.mark.postgresql
TOKEN = "watt-test-operator-token-with-32-plus-characters"


def test_server_derives_actor_and_checks_resource_access(postgres_database):
    app = FastAPI()

    @app.post("/api/works/{work_id}/approve")
    async def approve(work_id: str, request: Request):
        return {"actor": request.state.actor_id, "payload": await request.json()}

    install_authority_boundary(app, database=postgres_database,
        settings=Settings(auth_mode="required", operator_token=TOKEN))
    owned = uuid4()
    unowned = uuid4()
    with postgres_database.unit_of_work() as uow:
        uow.session.execute(insert(authority_resource_access).values(
            resource_kind="work", resource_id=str(owned),
            actor_id="human:owner", role="OWNER"))
        uow.commit()
    client = TestClient(app)
    path = f"/api/works/{owned}/approve"
    assert client.post(path, json={"authority_identity": "human:owner"}).status_code == 401
    assert client.post(path, headers={"Authorization": "Bearer wrong"},
        json={"authority_identity": "human:owner"}).status_code == 401
    response = client.post(path, headers={"Authorization": f"Bearer {TOKEN}"},
        json={"authority_identity": "human:forged", "nested": {"actor_identity": "human:forged"}})
    assert response.status_code == 200
    assert response.json() == {"actor": "human:owner", "payload": {
        "authority_identity": "human:owner", "nested": {"actor_identity": "human:owner"}}}
    assert client.post(f"/api/works/{unowned}/approve",
        headers={"Authorization": f"Bearer {TOKEN}"}, json={}).status_code == 403


def test_session_cookie_requires_same_origin_for_governed_post(postgres_database):
    app = FastAPI()

    @app.post("/api/action")
    async def action(request: Request):
        return {"actor": request.state.actor_id}

    install_authority_boundary(app, database=postgres_database,
        settings=Settings(auth_mode="required", operator_token=TOKEN))
    client = TestClient(app)
    login = client.post("/auth/session", json={"token": TOKEN})
    assert login.status_code == 200
    assert "httponly" in login.headers["set-cookie"].lower()
    assert client.post("/api/action", json={}).status_code == 403
    allowed = client.post("/api/action", json={},
        headers={"Origin": "http://testserver"})
    assert allowed.status_code == 200
    assert allowed.json()["actor"] == "human:owner"
