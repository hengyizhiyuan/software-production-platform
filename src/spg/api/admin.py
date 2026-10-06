"""Admin is a projection and Quality command surface behind existing owner authentication."""
from importlib.resources import files
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from spg.api.authority import ACTOR_ID
from spg.evaluation.catalog import import_core, create_fresh_holdout
from spg.evaluation.contracts import (CaseDefinition, CampaignRequest, ExperimentRequest,
    PreferenceRequest, AttributionRequest, PromotionRequest, FindingClosureRequest, RunControlRequest, RerunRequest, QualityError)
from spg.evaluation.service import QualityService
from spg.evaluation.operations import OperationsService


def install_admin(api, database, settings, runtime=None):
    quality = QualityService(database, settings)
    operations = OperationsService(database, settings, runtime)
    api.state.quality_owner = quality
    api.state.operations_observer = operations
    router = APIRouter(prefix="/api/admin")

    @api.exception_handler(QualityError)
    async def quality_error(_request, error):
        return JSONResponse({"code": error.code, "message": str(error)}, status_code=409)

    @api.get("/admin", include_in_schema=False)
    @api.get("/admin/{section}", include_in_schema=False)
    def admin_page(section="overview"):
        return FileResponse(files("spg.web").joinpath("admin.html"), media_type="text/html")

    @router.get("/overview")
    def overview():
        return {"quality": {"campaigns": quality.campaigns(), "runs": quality.recent_runs(),
            "clusters": quality.clusters(), "cases": quality.list_cases()},
            "assurance": {**operations.assurance(), "quality_evaluations": quality.guardian_evaluations()}, "operations": operations.snapshot(),
            "watt_revision": settings.runtime_revision, "admin_enabled": settings.admin_enabled}

    @router.get("/cases")
    def case_list():
        return quality.list_cases()

    @router.get("/cases/{case_id}/history")
    def case_history(case_id: UUID):
        return quality.case_history(case_id)

    @router.post("/cases")
    def create_case(request: CaseDefinition):
        r = quality.register_case(request)
        return {k: r[k] for k in ("id", "case_id", "version", "fingerprint")}

    @router.post("/catalog/import")
    def import_catalog():
        return import_core(quality)

    @router.post("/holdouts/generate")
    def holdout():
        if not settings.runtime_revision:
            raise QualityError("WATT_VERSION_NOT_BOUND")
        return create_fresh_holdout(quality)

    @router.get("/campaigns")
    def campaign_list():
        return quality.campaigns()

    @router.get("/runs")
    def run_list():
        return quality.recent_runs()

    @router.post("/runs")
    def create_run(request: CampaignRequest, http_request: Request):
        return quality.request_run(request, getattr(http_request.state, "actor_id", ACTOR_ID))

    @router.get("/runs/{run_id}")
    def run_detail(run_id: UUID):
        return quality.run_detail(run_id)

    @router.post("/pilot/control-regression")
    def control_regression():
        from spg.evaluation.pilot import register_control_regression
        return register_control_regression(quality)

    @router.post("/pilot/register")
    def pilot():
        from spg.evaluation.pilot import register_pilot
        return register_pilot(quality)

    @router.post("/runs/{run_id}/control")
    def control(run_id: UUID, request: RunControlRequest, http_request: Request):
        return quality.control_run(run_id, request.action, getattr(http_request.state, "actor_id", ACTOR_ID))

    @router.post("/runs/{run_id}/rerun")
    def rerun(run_id: UUID, request: RerunRequest, http_request: Request):
        return quality.rerun(run_id, request, getattr(http_request.state, "actor_id", ACTOR_ID))

    @router.post("/runs/{run_id}/cases/{case_version_id}/skip")
    def skip(run_id: UUID, case_version_id: UUID, http_request: Request):
        return quality.skip_case(run_id, case_version_id, getattr(http_request.state, "actor_id", ACTOR_ID))

    @router.post("/case-runs/{case_run_id}/llm-evaluation")
    def llm_evaluation(case_run_id: UUID):
        return quality.llm_evaluation(case_run_id)

    @router.get("/clusters")
    def cluster_list():
        return quality.clusters()

    @router.post("/findings/{finding_id}/regression")
    def regression(finding_id: UUID, http_request: Request):
        return quality.promote_regression(finding_id, getattr(http_request.state, "actor_id", ACTOR_ID))

    @router.post("/findings/{finding_id}/closure")
    def close_finding(finding_id: UUID, request: FindingClosureRequest, http_request: Request):
        return quality.close_finding(finding_id, request, getattr(http_request.state, "actor_id", ACTOR_ID))

    @router.get("/arena")
    def arena():
        return quality.arena()

    @router.post("/experiments")
    def experiment(request: ExperimentRequest, http_request: Request):
        return quality.create_experiment(request, getattr(http_request.state, "actor_id", ACTOR_ID))

    @router.post("/preferences")
    def preference(request: PreferenceRequest, http_request: Request):
        return quality.preference(request, getattr(http_request.state, "actor_id", ACTOR_ID))

    @router.post("/attributions")
    def attribution(request: AttributionRequest, http_request: Request):
        return quality.attribute(request, getattr(http_request.state, "actor_id", ACTOR_ID))

    @router.post("/promotion-decisions")
    def promotion(request: PromotionRequest, http_request: Request):
        return quality.promote(request, getattr(http_request.state, "actor_id", ACTOR_ID))

    @router.get("/assurance")
    def assurance():
        return {**operations.assurance(), "quality_evaluations": quality.guardian_evaluations()}

    @router.get("/operations")
    def ops():
        return operations.snapshot()

    @router.get("/operations/history")
    def history():
        return operations.history()

    api.include_router(router)
    return operations
