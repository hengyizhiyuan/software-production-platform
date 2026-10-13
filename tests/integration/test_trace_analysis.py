"""Isolated PostgreSQL API authority and original Owner immutability checks."""
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from spg.api.admin import install_admin
from spg.api.authority import install_authority_boundary
from spg.config import Settings
from spg.domain.native_execution import InferenceAction, InferenceResponse
from spg.infrastructure.persistence import metadata
from tests.integration.test_admin_universal_trace import simple
from tests.integration.test_work_delivery import clean_schema

pytestmark = pytest.mark.postgresql


def test_analysis_api_auth_csrf_scope_and_no_original_owner_mutation(postgres_database, tmp_path):
    db = postgres_database
    target = simple(db, condition="REJECTED", title="Historical failed Work")
    foreign = simple(db, condition="REJECTED", owner="human:foreign")
    settings = Settings(auth_mode="required", operator_token="analysis-test-operator-1234567890",
                        native_executor_storage_root=tmp_path / "native",
                        native_executor_production_environment_store_root=tmp_path / "preview",
                        owner_runtime_store_root=tmp_path / "owner")
    api = FastAPI()
    install_authority_boundary(api, database=db, settings=settings)
    install_admin(api, db, settings)
    class NoConclusion:
        calls = 0
        async def infer(self, request):
            self.calls += 1
            return InferenceResponse(action=InferenceAction.UNABLE_TO_COMPLETE,
                                     summary="Missing source; preserve UNKNOWN",
                                     working_plan=request.working_plan)
    model = NoConclusion()
    api.state.trace_analysis.inference_factory = lambda: model
    api.state.trace_analysis.repository_factory = lambda *_: ({}, ["Historical source unavailable"])
    def counts():
        with db.engine.connect() as conn:
            return {table.name: conn.scalar(select(func.count()).select_from(table))
                    for table in metadata.sorted_tables if table.name != "authority_sessions"}
    with TestClient(api) as client:
        path = f"/api/admin/works/{target}/analyses"
        body = {"request_id": str(uuid4()), "rationale": "Inspect failed Work"}
        assert client.post(path, json=body).status_code == 401
        assert client.get(path).status_code == 401
        client.post("/auth/session", json={"token": "analysis-test-operator-1234567890"})
        before = counts()
        assert client.post(path, json=body).status_code == 403
        headers = {"Origin": "http://testserver"}
        assert client.post(f"/api/admin/works/{foreign}/analyses", json=body, headers=headers).status_code == 409
        assert model.calls == 0
        response = client.post(path, json=body, headers=headers)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["status"] == "FAILED" and result["report"] is None
        assert result["production_work_created"] is False
        assert client.post(path, json=body, headers=headers).json() == result
        assert model.calls == 1
        detail = client.get(path + "/" + body["request_id"] + "?detail=true")
        assert detail.status_code == 200 and detail.json()["execution_history"]
        assert client.get(f"/api/admin/works/{foreign}/analyses/{body['request_id']}?detail=true").status_code == 409
        summary = client.get(path + "/" + body["request_id"] + "?view=summary").json()
        assert "execution_history" not in summary and "event_digests" not in summary
        downloaded = client.get(path + "/" + body["request_id"] + "/report")
        assert downloaded.status_code == 200 and downloaded.headers["content-type"].startswith("text/markdown")
        assert '.md' in downloaded.headers["content-disposition"]
        assert 'UNKNOWN' in downloaded.text and len(downloaded.content) < 20000
        assert client.get(f"/api/admin/works/{foreign}/analyses/{body['request_id']}/report").status_code == 409
        client.cookies.clear()
        assert client.get(path + "/" + body["request_id"] + "/report").status_code == 401
        assert counts() == before
