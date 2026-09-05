"""Focused product and packaging contracts for the MVP control-room UI."""

from importlib.resources import files
from pathlib import Path

from fastapi.testclient import TestClient

from spg.api import create_http_application
from spg.domain.runtime_activation import (
    RuntimeActivationProjection,
    RuntimeActivationState,
)


WEB_ROOT = Path(str(files("spg.web")))


class _StaticOnlyDatabase:
    def check(self) -> None:
        return None


class _StaticOnlyWorkService:
    database = _StaticOnlyDatabase()

    def list_works(self) -> tuple[()]:
        return ()


class _StaticOnlyOrchestrator:
    def resume_safely_eligible_works(self) -> tuple[()]:
        return ()

    def shutdown(self) -> None:
        return None


class _StaticOnlySteeringDriver:
    def resume_safely_eligible_works(self) -> tuple[()]:
        return ()

    def shutdown(self) -> None:
        return None


class _StaticRuntimeActivation:
    def project(self) -> RuntimeActivationProjection:
        return RuntimeActivationProjection(
            state=RuntimeActivationState.ACTIVE_AT_TRUSTED_BASELINE,
            active_application_revision="test-revision",
            current_trusted_baseline_revision="test-revision",
            reason="Static route test Runtime is converged.",
        )


def _client() -> TestClient:
    return TestClient(
        create_http_application(
            application=object(),  # Static routes do not require Runtime composition.
            database=_StaticOnlyDatabase(),
            work_service=_StaticOnlyWorkService(),
            orchestrator=_StaticOnlyOrchestrator(),
            steering_driver=_StaticOnlySteeringDriver(),
            runtime_activation=_StaticRuntimeActivation(),
        )
    )


def test_ui_01_02_19_root_app_and_installed_assets_are_available() -> None:
    with _client() as client:
        root = client.get("/", follow_redirects=False)
        assert root.status_code == 307
        assert root.headers["location"] == "/app"

        page = client.get("/app")
        assert page.status_code == 200
        assert page.headers["content-type"].startswith("text/html")
        assert 'id="work-form"' in page.text

        for asset_name, content_marker in (
            ("styles.css", ".control-room"),
            ("state.js", "SPGViewModel"),
            ("app.js", "startControlRoom"),
        ):
            packaged = WEB_ROOT / asset_name
            assert packaged.is_file()
            response = client.get(f"/assets/{asset_name}")
            assert response.status_code == 200
            assert content_marker in response.text

        activation = client.get("/api/runtime-activation")
        assert activation.status_code == 200
        assert activation.json()["state"] == "ACTIVE_AT_TRUSTED_BASELINE"


def test_ui_03_through_ui_18_product_surface_contract_is_bounded() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    combined = f"{html}\n{javascript}".lower()

    assert "what do you want to get done?" in combined
    assert "goal" in combined
    assert "works" in combined
    assert "human authority" in combined
    assert "attention required" in combined
    assert "work result" in combined
    assert "artifact target" in combined
    assert "artifact operation" in combined
    assert 'id="work-mode"' in html
    assert 'value="LONG_LIVED_STEERING" selected' in html
    assert 'value="IMMEDIATE_PRODUCTION"' in html
    assert "mode: elements.workMode.value" in javascript
    assert "placement rationale" in combined
    assert "production plan" in combined
    assert "single-pwu approach" in combined
    assert 'id="plan-steps"' in html
    assert "plan.fit_classification" in javascript
    assert "expected_artifact_path" in javascript
    assert "code change contract" in combined
    assert "code change proposal" in combined
    assert "not production authority" in combined
    assert "proposal confidence" in combined
    assert "conditional targets" in combined
    assert "unresolved questions" in combined
    assert 'id="code-exact-targets"' in html
    assert 'id="code-allowed-areas"' in html
    assert 'id="code-forbidden-areas"' in html
    assert 'id="code-verification-obligations"' in html
    assert "NODE_TEST_TARGET:tests/js/test_web_state.cjs" in html
    assert "code_exact_targets" in javascript
    assert "code_allowed_areas" in javascript
    assert "typedVerificationObligations" in javascript
    assert "work.change_proposal" in javascript
    assert 'work.target_kind === "CODE_WORK"' in javascript
    assert "no artifacts observed" in combined
    assert "no verification evidence available" in combined
    assert "project selector" not in combined
    assert "chat thread" not in combined

    for route in (
        "/api/goals",
        "/api/works",
        "/refine",
        "/advance",
        "/api/attention",
        "/result",
    ):
        assert route in javascript

    for governed_endpoint in ("APPROVE: \"approve\"", "REJECT: \"reject\"", "REQUEST_REFINEMENT: \"request-refinement\""):
        assert governed_endpoint in javascript

    assert "attention.available_actions.forEach" in javascript
    assert "setInterval" not in javascript
    assert "POLL_INTERVAL_MS = 2000" in javascript
    assert "scheduleObservationPolling" in javascript
    assert "globalThis.setTimeout" in javascript
    assert javascript.count("/advance") == 1
    polling = javascript[javascript.index("function scheduleObservationPolling") :]
    assert 'method: "POST"' not in polling.split(
        "async function refreshAfterMutation"
    )[0]
    assert "innerHTML" not in javascript
    assert "SPG_DATABASE_URL" not in javascript
    assert "OPENAI_API_KEY" not in javascript


def test_planb_composer_has_explicit_bounded_collapse_control() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

    assert 'id="composer-toggle"' in html
    assert 'aria-controls="work-form"' in html
    assert 'aria-expanded="true"' in html
    assert "elements.workForm.hidden = !expanded" in javascript
    assert '"Expand composer"' in javascript
    assert '"Collapse composer"' in javascript


def test_ui_20_contains_no_frontend_build_or_remote_runtime_dependency() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert "https://" not in html
    assert "http://" not in html
    assert 'src="/assets/state.js"' in html
    assert 'src="/assets/app.js"' in html
    assert 'href="/assets/styles.css"' in html
