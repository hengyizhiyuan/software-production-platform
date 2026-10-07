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
from spg.evaluation.production_trace import ProductionTraceService
from spg.evaluation.admin_projection import cockpit_projection, outcome_projection


def install_admin(api, database, settings, runtime=None):
    quality = QualityService(database, settings)
    operations = OperationsService(database, settings, runtime)
    traces = ProductionTraceService(database, settings, quality)
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
        result = {"quality": {"campaigns": quality.campaigns(), "runs": quality.recent_runs(),
            "clusters": quality.clusters(), "cases": quality.list_cases()},
            "assurance": {**operations.assurance(), "quality_evaluations": quality.guardian_evaluations()}, "operations": operations.snapshot(),
            "watt_revision": settings.runtime_revision, "admin_enabled": settings.admin_enabled}
        from sqlalchemy import text
        with database.unit_of_work() as u:
            ledger = [dict(r) for r in u.session.execute(text("""
                SELECT a.id,a.state,a.created_at,a.case_version_id,a.campaign_run_id,v.case_id,
                    v.definition->>'title' AS title,a.lineage->'divergence'->>'stage' AS divergence_stage,r.watt_revision,r.policy_fingerprint,r.experiment_id,
                    m.cohorts FROM quality_case_runs a
                JOIN quality_case_versions v ON v.id=a.case_version_id
                JOIN quality_campaign_runs r ON r.id=a.campaign_run_id
                JOIN quality_run_members m ON m.run_id=r.id AND m.case_version_id=v.id
                ORDER BY a.created_at DESC LIMIT 500
            """)).mappings()]
        result['cockpit'] = cockpit_projection(result, ledger)
        from spg.evaluation.admin_projection import run_summaries, assurance_summary
        result['assurance']['summary'] = assurance_summary(database, result['assurance'])
        result['quality']['runs'] = run_summaries(database, result['quality']['runs'], result['quality']['campaigns'], ledger)
        active_ids = {r['id'] for r in result['cockpit']['active_runs']}
        result['cockpit']['active_runs'] = [r for r in result['quality']['runs'] if r['id'] in active_ids]
        return result

    @router.get('/dashboard')
    def dashboard(period: str = 'TODAY'):
        from spg.evaluation.admin_dashboard import dashboard
        return dashboard(database, settings, period)

    @router.get('/dashboard/work-outcomes')
    def work_outcomes(period: str = 'TODAY'):
        from datetime import datetime, timezone
        from sqlalchemy import text
        from spg.evaluation.admin_dashboard import period_start
        from spg.infrastructure.performance import projection_scope
        until = datetime.now(timezone.utc)
        since = period_start(period, until)
        @projection_scope
        def read():
            with database.unit_of_work() as u:
                ids = list(u.session.scalars(text("SELECT id FROM product_works WHERE created_at BETWEEN :since AND :until AND condition<>'DISCARDED' ORDER BY created_at LIMIT 501"), {'since': since, 'until': until}))
            if len(ids) > 500:
                return {'completed': None, 'scope': '超过当前有界读范围，不能以部分记录计全量'}
            works = api.state.work_service.get_works(ids)
            return {'completed': sum(w.work_complete for w in works), 'observed': len(works),
                'scope': '本期创建且未丢弃的 Work，按当前规范投影检查；不是本期完成事件统计'}
        return read()

    @router.get('/case-runs/{case_run_id}/trace')
    def case_trace(case_run_id: UUID, view: str = "full"):
        if view not in {"full", "summary"}:
            raise QualityError("TRACE_VIEW_NOT_SUPPORTED")
        return traces.case_trace(case_run_id, detail=view == "full")

    @router.get('/traces/{kind}/{entity_id}')
    def entity_trace(kind: str, entity_id: UUID):
        return traces.entity_trace(kind, entity_id)

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
        result = quality.run_detail(run_id)
        for case in result['cases']:
            case['human_outcome'] = outcome_projection(case)
        return result

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
        from spg.evaluation.admin_projection import experiment_comparisons
        result = quality.arena()
        result['comparison_pairs'] = experiment_comparisons(database, result['experiments'])
        return result

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
