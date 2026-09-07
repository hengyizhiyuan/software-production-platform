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
    state_javascript = (WEB_ROOT / "state.js").read_text(encoding="utf-8")
    combined = f"{html}\n{javascript}".lower()

    assert "what would you like watt to understand?" in combined
    assert "goal" in combined
    assert "works" in combined
    assert "human authority" in combined
    assert "attention required" in combined
    assert "work result" in combined
    assert "artifact target" in combined
    assert "artifact operation" in combined
    assert 'id="interaction-history"' in html
    assert 'id="shared-understanding"' in html
    assert 'id="interaction-readiness"' in html
    assert 'id="admit-work-control"' in html
    assert 'id="interaction-authority-identity"' in html
    assert 'id="interaction-resource"' in html
    assert 'id="interaction-scope"' in html
    assert 'id="current-work-focus"' in html
    assert 'id="interaction-focus-classification"' in html
    assert 'id="interaction-impact-disposition"' in html
    assert 'id="interaction-candidate-change"' in html
    assert 'id="work-revision-admission-status"' in html
    assert 'id="work-revision-admission"' in html
    assert 'id="work-revision-authority-identity"' in html
    assert 'id="approve-work-revision"' in html
    assert 'id="reject-work-revision"' in html
    assert 'id="refine-work-revision"' in html
    assert 'id="work-satisfaction-state"' in html
    assert 'id="interaction-relationship-state"' in html
    assert 'id="work-focus-history"' in html
    assert 'id="work-transition-summary"' in html
    assert 'id="work-transition-decision"' in html
    assert 'id="continue-current-work"' in html
    assert 'id="start-new-work"' in html
    assert 'id="dismiss-work-transition"' in html
    assert "admit governed work" in combined
    assert "ready to form work" in combined
    assert 'id="work-mode"' not in html
    assert 'id="work-tags"' not in html
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
    assert 'id="execution-progress"' in html
    assert 'id="execution-signal"' in html
    assert 'id="execution-updated"' in html
    assert 'aria-live="polite"' in html
    assert "transitions completed · total unknown" in state_javascript
    assert "progress.percentComplete" not in javascript
    assert "project selector" not in combined
    assert "chat thread" not in combined

    for route in (
        "/api/interactions",
        "/admit-work",
        "/work-revision-decisions",
        "/work-transition-decisions",
        "/api/goals",
        "/api/works",
        "/refine",
        "/advance",
        "/api/attention",
        "/result",
    ):
        assert route in javascript
    assert "PENDING_HUMAN" in javascript
    assert "candidate_change" in javascript
    assert "new_work_formation_pending" in javascript
    assert "CURRENTLY_SATISFIED" in javascript
    assert "START_NEW_WORK" in javascript

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
    assert 'apiRequest("/api/works", { method: "POST"' not in javascript
    assert "No Work was created" in javascript
    assert "assessment_id: assessment.assessment_id" in javascript
    assert "basis_fingerprint: assessment.basis_fingerprint" in javascript
    assert 'elements.admitWorkControl.addEventListener("click", admitInteractionWork)' in javascript
    assert "No Work or production authority was created." in javascript
    assert "setTimeout" in javascript
    assert "countdown" not in combined


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
