"""FastAPI boundary for the minimal Goal / Work MVP product surface."""

from contextlib import asynccontextmanager
from importlib.resources import files
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from spg.api.dto import (
    AttentionResolveRequest,
    AttentionResponse,
    ErrorResponse,
    ExecutionProgressResponse,
    GoalCreateRequest,
    GoalResponse,
    GoalSummaryResponse,
    HealthResponse,
    HumanDecisionRequest,
    RuntimeActivationResponse,
    SteeringPlanResponse,
    WorkRefineRequest,
    WorkResponse,
    WorkResultResponse,
    WorkSubmitRequest,
)
from spg.application.bootstrap import Application, bootstrap
from spg.application.orchestration import ProductionOrchestrator
from spg.application.post_admission import WorkPostAdmissionService
from spg.application.steering_driver import PlanSteeringDriver
from spg.application.steering_bootstrap import SteeringBootstrapService
from spg.application.runtime_activation import RuntimeActivationService
from spg.application.work import WorkApplicationService
from spg.domain.product import (
    AttentionAction,
    AttentionResolutionRequest,
    ProductInvariantViolation,
    ProductRecordNotFound,
    WorkRefinementRequest,
    WorkProjection,
    WorkStatus,
)
from spg.domain.steering import SteeringRecordNotFound
from spg.infrastructure.persistence import Database, DatabaseConfigurationError


class ProductHttpError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(code=code, message=message)
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def _invariant_code(error: ProductInvariantViolation) -> str:
    message = str(error).lower()
    if "refinement" in message or "refined" in message:
        return "NEEDS_REFINEMENT"
    if "approval" in message or "authority" in message or "await" in message:
        return "HUMAN_APPROVAL_REQUIRED"
    if "blocked" in message or "reality" in message or "overridden" in message:
        return "BLOCKED_PRODUCTION_REALITY"
    return "INVALID_STATE_TRANSITION"


def create_http_application(
    application: Application | None = None,
    *,
    database: Database | None = None,
    work_service: WorkApplicationService | None = None,
    orchestrator: ProductionOrchestrator | None = None,
    steering_driver: PlanSteeringDriver | None = None,
    steering_bootstrap: SteeringBootstrapService | None = None,
    runtime_activation: RuntimeActivationService | None = None,
) -> FastAPI:
    """Compose one ASGI application over the existing application bootstrap path."""

    container = application or bootstrap()
    selected_database = database
    if work_service is None:
        selected_database = selected_database or container.persistence()
        work_service = container.work(selected_database)
    else:
        selected_database = selected_database or work_service.database

    selected_orchestrator = orchestrator or container.production_orchestrator(
        work_service
    )
    selected_steering_driver = steering_driver or container.plan_steering_driver(
        selected_database,
        work_service,
        selected_orchestrator,
    )
    selected_runtime_activation = runtime_activation or container.runtime_activation(
        selected_database
    )
    selected_steering_bootstrap = steering_bootstrap or SteeringBootstrapService(
        selected_database
    )
    selected_post_admission = WorkPostAdmissionService(
        work_service,
        selected_steering_bootstrap,
        selected_steering_driver,
        selected_orchestrator,
    )

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        selected_post_admission.bootstrap_incomplete_ready_long_lived()
        selected_steering_driver.resume_safely_eligible_works()
        selected_orchestrator.resume_safely_eligible_works()
        try:
            yield
        finally:
            selected_steering_driver.shutdown()
            selected_orchestrator.shutdown()

    api = FastAPI(
        title="SPG Product API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    api.state.application = container
    api.state.database = selected_database
    api.state.work_service = work_service
    api.state.production_orchestrator = selected_orchestrator
    api.state.plan_steering_driver = selected_steering_driver
    api.state.steering_bootstrap = selected_steering_bootstrap
    api.state.work_post_admission = selected_post_admission
    web_root = Path(str(files("spg.web")))
    api.mount("/assets", StaticFiles(directory=web_root), name="assets")

    def work_response(projection: WorkProjection) -> WorkResponse:
        response = WorkResponse.from_projection(projection)
        progress_reader = getattr(selected_orchestrator, "progress", None)
        if callable(progress_reader):
            progress = progress_reader(projection.work_id)
            if progress is not None:
                response = response.model_copy(update={
                    "execution_progress": ExecutionProgressResponse(
                        phase=progress.phase,
                        activity=progress.activity,
                        transitions_completed=progress.transitions_completed,
                        transitions_total=progress.transitions_total,
                        percent_complete=None,
                        started_at=progress.started_at,
                        updated_at=progress.updated_at,
                        elapsed_seconds=progress.elapsed_seconds,
                        still_working=progress.still_working,
                        blocked_reason=progress.blocked_reason,
                    )
                })
        if not projection.steering_enabled:
            return response
        try:
            steering = selected_steering_driver.project(projection.work_id)
        except SteeringRecordNotFound:
            return response
        state = steering.automatic_progression_state.value
        stop_reason = (
            None
            if steering.last_stop_reason is None
            else steering.last_stop_reason.value
        )
        updates: dict[str, str | None] = {
            "automatic_progression_state": state,
            "last_stop_reason": stop_reason,
        }
        if state == "STOPPED" and stop_reason == "BLOCKED":
            updates.update(
                {
                    "most_recent_meaningful_event": "STEERING_STOPPED_BLOCKED",
                    "what_happens_next": (
                        "Automatic Steering stopped on a governed invariant; "
                        "inspect the recorded Runtime evidence"
                    ),
                }
            )
        return response.model_copy(update=updates)

    @api.exception_handler(ProductRecordNotFound)
    @api.exception_handler(SteeringRecordNotFound)
    async def not_found_handler(
        _request: Request,
        error: ProductRecordNotFound | SteeringRecordNotFound,
    ) -> JSONResponse:
        return _error(404, "NOT_FOUND", str(error))

    @api.exception_handler(ProductInvariantViolation)
    async def invariant_handler(
        _request: Request,
        error: ProductInvariantViolation,
    ) -> JSONResponse:
        return _error(409, _invariant_code(error), str(error))

    @api.exception_handler(ProductHttpError)
    async def product_http_handler(
        _request: Request,
        error: ProductHttpError,
    ) -> JSONResponse:
        return _error(error.status_code, error.code, str(error))

    @api.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request,
        _error_value: RequestValidationError,
    ) -> JSONResponse:
        return _error(422, "INVALID_REQUEST", "Request validation failed")

    @api.exception_handler(DatabaseConfigurationError)
    @api.exception_handler(SQLAlchemyError)
    async def infrastructure_handler(
        _request: Request,
        _error_value: Exception,
    ) -> JSONResponse:
        return _error(503, "INFRASTRUCTURE_ERROR", "Product infrastructure unavailable")

    @api.exception_handler(Exception)
    async def internal_error_handler(
        _request: Request,
        _error_value: Exception,
    ) -> JSONResponse:
        return _error(500, "INTERNAL_ERROR", "Internal product API error")

    @api.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        selected_database.check()
        return HealthResponse(
            service="available",
            database="available",
            application_initialized=True,
        )

    @api.get(
        "/api/runtime-activation",
        response_model=RuntimeActivationResponse,
    )
    def get_runtime_activation() -> RuntimeActivationResponse:
        return RuntimeActivationResponse.from_projection(
            selected_runtime_activation.project()
        )

    @api.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/app", status_code=307)

    @api.get("/app", include_in_schema=False)
    def product_ui() -> FileResponse:
        return FileResponse(web_root / "index.html", media_type="text/html")

    @api.post("/api/goals", response_model=GoalResponse, status_code=201)
    def create_goal(request: GoalCreateRequest) -> GoalResponse:
        return GoalResponse.from_record(
            work_service.create_goal(request.title, request.description)
        )

    @api.get("/api/goals", response_model=list[GoalResponse])
    def list_goals() -> list[GoalResponse]:
        return [GoalResponse.from_record(goal) for goal in work_service.list_goals()]

    @api.get("/api/goals/{goal_id}", response_model=GoalSummaryResponse)
    def get_goal(goal_id: UUID) -> GoalSummaryResponse:
        return GoalSummaryResponse.from_projection(
            work_service.get_goal_projection(goal_id)
        )

    @api.post("/api/works", response_model=WorkResponse, status_code=201)
    def submit_work(request: WorkSubmitRequest) -> WorkResponse:
        return work_response(
            work_service.submit_work(
                request.requirement,
                goal_id=request.goal_id,
                tags=request.tags,
                mode=request.mode,
            )
        )

    @api.get("/api/works", response_model=list[WorkResponse])
    def list_works(
        goal_id: UUID | None = None,
        status_filter: Annotated[WorkStatus | None, Query(alias="status")] = None,
    ) -> list[WorkResponse]:
        projections = work_service.list_works(goal_id=goal_id)
        if status_filter is not None:
            projections = tuple(
                work for work in projections if work.status is status_filter
            )
        return [work_response(work) for work in projections]

    @api.get("/api/works/{work_id}", response_model=WorkResponse)
    def get_work(work_id: UUID) -> WorkResponse:
        return work_response(work_service.get_work(work_id))

    @api.get(
        "/api/works/{work_id}/steering",
        response_model=SteeringPlanResponse,
    )
    def get_steering_plan(work_id: UUID) -> SteeringPlanResponse:
        return SteeringPlanResponse.from_projection(
            selected_steering_driver.project(work_id)
        )

    @api.post("/api/works/{work_id}/refine", response_model=WorkResponse)
    def refine_work(work_id: UUID, request: WorkRefineRequest) -> WorkResponse:
        refinement = WorkRefinementRequest(**request.model_dump())
        return work_response(
            work_service.refine_work(work_id, refinement)
        )

    @api.post("/api/works/{work_id}/approve", response_model=WorkResponse)
    def approve_work(work_id: UUID, request: HumanDecisionRequest) -> WorkResponse:
        projection = work_service.get_work(work_id)
        if projection.status is WorkStatus.NEEDS_REFINEMENT:
            raise ProductHttpError(
                409,
                "NEEDS_REFINEMENT",
                "Work requires refinement before Human admission",
            )
        projection = work_service.approve_work(
            work_id,
            authority_identity=request.authority_identity,
            rationale=request.rationale,
        )
        return work_response(
            selected_post_admission.activate(projection.work_id)
        )

    @api.post("/api/works/{work_id}/reject", response_model=WorkResponse)
    def reject_work(work_id: UUID, request: HumanDecisionRequest) -> WorkResponse:
        return work_response(
            work_service.reject_work_draft(
                work_id,
                authority_identity=request.authority_identity,
            )
        )

    @api.post(
        "/api/works/{work_id}/request-refinement",
        response_model=WorkResponse,
    )
    def request_refinement(
        work_id: UUID,
        request: HumanDecisionRequest,
    ) -> WorkResponse:
        return work_response(
            work_service.request_work_refinement(
                work_id,
                authority_identity=request.authority_identity,
            )
        )

    @api.post("/api/works/{work_id}/advance", response_model=WorkResponse)
    def advance_work(work_id: UUID) -> WorkResponse:
        return work_response(work_service.advance_work(work_id))

    @api.get("/api/attention", response_model=list[AttentionResponse])
    def list_attention(work_id: UUID | None = None) -> list[AttentionResponse]:
        return [
            AttentionResponse.from_projection(attention)
            for attention in work_service.list_attention(work_id=work_id)
        ]

    @api.post(
        "/api/attention/{attention_id}/resolve",
        response_model=WorkResponse,
    )
    def resolve_attention(
        attention_id: UUID,
        request: AttentionResolveRequest,
    ) -> WorkResponse:
        resolution = AttentionResolutionRequest(
            action=request.action,
            authority_identity=request.authority_identity,
            rationale=request.rationale,
        )
        projection = work_service.resolve_attention(attention_id, resolution)
        if request.action is AttentionAction.APPROVE:
            projection = selected_post_admission.activate(projection.work_id)
        elif projection.status in {WorkStatus.READY, WorkStatus.RUNNING}:
            selected_orchestrator.schedule(projection.work_id)
        return work_response(projection)

    @api.get("/api/works/{work_id}/result", response_model=WorkResultResponse)
    def get_work_result(work_id: UUID) -> WorkResultResponse:
        return WorkResultResponse.from_projection(
            work_service.get_work_result(work_id),
            selected_runtime_activation.project(),
        )

    return api
