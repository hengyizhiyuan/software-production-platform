"""FastAPI boundary for the minimal Goal / Work MVP product surface."""

from contextlib import asynccontextmanager
import asyncio
from importlib.resources import files
import json
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
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
    GuidedDesignResponse,
    HealthResponse,
    HumanDecisionRequest,
    InteractionCreateRequest,
    InteractionMessageRequest,
    InteractionTurnResponse,
    InteractionWorkAdmissionRequest,
    InteractionWorkRevisionDecisionRequest,
    InteractionWorkTransitionDecisionRequest,
    SharedUnderstandingResponse,
    RuntimeActivationResponse,
    SteeringPlanResponse,
    WorkRefineRequest,
    WorkResponse,
    WorkResultResponse,
    WorkSubmitRequest,
)
from spg.application.bootstrap import Application, bootstrap
from spg.application.orchestration import ProductionOrchestrator
from spg.application.interaction import WorkInteractionService
from spg.application.guided_design import GuidedDesignApplicationService
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
from spg.domain.interaction import (
    InteractionInvariantViolation,
    InteractionRecordNotFound,
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
    interaction_service: WorkInteractionService | None = None,
    guided_design_service: GuidedDesignApplicationService | None = None,
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
    selected_guided_design = guided_design_service or (
        container.guided_design(selected_database)
        if hasattr(container, "guided_design")
        else GuidedDesignApplicationService(selected_database)
    )
    selected_interaction = interaction_service
    if selected_interaction is None and hasattr(container, "interaction"):
        selected_interaction = container.interaction(selected_database)

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        if selected_interaction is not None:
            resume_turns = getattr(selected_interaction, "resume_pending_turns", None)
            if callable(resume_turns):
                resume_turns()
        selected_post_admission.bootstrap_incomplete_ready_long_lived()
        selected_steering_driver.resume_safely_eligible_works()
        selected_orchestrator.resume_safely_eligible_works()
        try:
            yield
        finally:
            selected_steering_driver.shutdown()
            selected_orchestrator.shutdown()
            if selected_interaction is not None:
                shutdown_interaction = getattr(selected_interaction, "shutdown", None)
                if callable(shutdown_interaction):
                    shutdown_interaction()

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
    api.state.interaction_service = selected_interaction
    web_root = Path(str(files("spg.web")))
    api.mount("/assets", StaticFiles(directory=web_root), name="assets")

    def work_response(projection: WorkProjection) -> WorkResponse:
        response = WorkResponse.from_projection(projection)
        progress_reader = getattr(selected_orchestrator, "progress", None)
        if callable(progress_reader):
            progress = progress_reader(projection.work_id)
            if progress is not None:
                percent_complete = None
                if progress.transitions_total is not None:
                    percent_complete = min(
                        100,
                        round(
                            100
                            * progress.transitions_completed
                            / progress.transitions_total
                        ),
                    )
                response = response.model_copy(update={
                    "execution_progress": ExecutionProgressResponse(
                        phase=progress.phase,
                        activity=progress.activity,
                        transitions_completed=progress.transitions_completed,
                        transitions_total=progress.transitions_total,
                        percent_complete=percent_complete,
                        started_at=progress.started_at,
                        updated_at=progress.updated_at,
                        elapsed_seconds=progress.elapsed_seconds,
                        still_working=progress.still_working,
                        blocked_reason=progress.blocked_reason,
                    )
                })
        if not projection.steering_enabled:
            guided = selected_guided_design.get_optional(projection.work_id)
            return response.model_copy(
                update={
                    "guided_design": (
                        None
                        if guided is None
                        else GuidedDesignResponse.from_projection(guided)
                    )
                }
            )
        try:
            steering = selected_steering_driver.project(projection.work_id)
        except SteeringRecordNotFound:
            guided = selected_guided_design.get_optional(projection.work_id)
            return response.model_copy(
                update={
                    "guided_design": (
                        None
                        if guided is None
                        else GuidedDesignResponse.from_projection(guided)
                    )
                }
            )
        state = steering.automatic_progression_state.value
        stop_reason = (
            None
            if steering.last_stop_reason is None
            else steering.last_stop_reason.value
        )
        updates: dict[str, object] = {
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
        guided = selected_guided_design.get_optional(projection.work_id)
        updates["guided_design"] = (
            None
            if guided is None
            else GuidedDesignResponse.from_projection(guided)
        )
        return response.model_copy(update=updates)

    @api.exception_handler(ProductRecordNotFound)
    @api.exception_handler(SteeringRecordNotFound)
    @api.exception_handler(InteractionRecordNotFound)
    async def not_found_handler(
        _request: Request,
        error: ProductRecordNotFound | SteeringRecordNotFound | InteractionRecordNotFound,
    ) -> JSONResponse:
        return _error(404, "NOT_FOUND", str(error))

    @api.exception_handler(ProductInvariantViolation)
    async def invariant_handler(
        _request: Request,
        error: ProductInvariantViolation,
    ) -> JSONResponse:
        return _error(409, _invariant_code(error), str(error))

    @api.exception_handler(InteractionInvariantViolation)
    async def interaction_invariant_handler(
        _request: Request,
        error: InteractionInvariantViolation,
    ) -> JSONResponse:
        return _error(409, "INTERACTION_INVARIANT", str(error))

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

    def required_interaction_service() -> WorkInteractionService:
        if selected_interaction is None:
            raise ProductHttpError(
                503,
                "INTERACTION_UNAVAILABLE",
                "Work Interaction capability is unavailable",
            )
        return selected_interaction

    @api.post(
        "/api/interactions",
        response_model=SharedUnderstandingResponse,
        status_code=201,
    )
    def create_interaction(
        request: InteractionCreateRequest,
    ) -> SharedUnderstandingResponse:
        service = required_interaction_service()
        interaction = service.create_interaction(human_identity=request.human_identity)
        return SharedUnderstandingResponse.from_projection(
            service.get_shared_understanding(interaction.id)
        )

    @api.get(
        "/api/interactions",
        response_model=list[SharedUnderstandingResponse],
    )
    def list_interactions() -> list[SharedUnderstandingResponse]:
        return [
            SharedUnderstandingResponse.from_projection(item)
            for item in required_interaction_service().list_interactions()
        ]

    @api.get(
        "/api/interactions/{interaction_id}",
        response_model=SharedUnderstandingResponse,
    )
    def get_interaction(interaction_id: UUID) -> SharedUnderstandingResponse:
        return SharedUnderstandingResponse.from_projection(
            required_interaction_service().get_shared_understanding(interaction_id)
        )

    @api.get(
        "/api/interactions/{interaction_id}/shared-understanding",
        response_model=SharedUnderstandingResponse,
    )
    def get_shared_understanding(interaction_id: UUID) -> SharedUnderstandingResponse:
        return SharedUnderstandingResponse.from_projection(
            required_interaction_service().get_shared_understanding(interaction_id)
        )

    @api.post(
        "/api/interactions/{interaction_id}/records",
        response_model=SharedUnderstandingResponse,
        status_code=201,
    )
    def append_interaction_record(
        interaction_id: UUID,
        request: InteractionMessageRequest,
    ) -> SharedUnderstandingResponse:
        return SharedUnderstandingResponse.from_projection(
            required_interaction_service().append_and_assess(
                interaction_id,
                request.content,
                human_identity=request.human_identity,
                supporting_references=request.supporting_references,
            )
        )

    @api.post(
        "/api/interactions/{interaction_id}/turns",
        response_model=InteractionTurnResponse,
        status_code=202,
    )
    def submit_interaction_turn(
        interaction_id: UUID,
        request: InteractionMessageRequest,
    ) -> InteractionTurnResponse:
        turn = required_interaction_service().submit_turn(
            interaction_id,
            request.content,
            human_identity=request.human_identity,
            supporting_references=request.supporting_references,
        )
        return InteractionTurnResponse.from_turn(turn)

    @api.get(
        "/api/interactions/{interaction_id}/turns/{turn_id}",
        response_model=InteractionTurnResponse,
    )
    def get_interaction_turn(
        interaction_id: UUID,
        turn_id: UUID,
    ) -> InteractionTurnResponse:
        turn = required_interaction_service().get_turn(turn_id)
        if turn.interaction_id != interaction_id:
            raise InteractionRecordNotFound(f"Interaction Turn not found: {turn_id}")
        return InteractionTurnResponse.from_turn(turn)

    @api.get("/api/interactions/{interaction_id}/turns/{turn_id}/events")
    async def stream_interaction_turn(
        interaction_id: UUID,
        turn_id: UUID,
        request: Request,
    ) -> StreamingResponse:
        service = required_interaction_service()
        initial = service.get_turn(turn_id)
        if initial.interaction_id != interaction_id:
            raise InteractionRecordNotFound(f"Interaction Turn not found: {turn_id}")

        async def events():
            last_status: str | None = None
            stream_offset = 0
            streamed_response = ""
            while True:
                if await request.is_disconnected():
                    return
                turn = service.get_turn(turn_id)
                if turn.status.value != last_status:
                    payload = InteractionTurnResponse.from_turn(turn).model_dump(
                        mode="json"
                    )
                    yield f"event: turn.status\ndata: {json.dumps(payload)}\n\n"
                    last_status = turn.status.value
                delta, stream_offset = service.turn_response_delta(
                    turn_id, stream_offset
                )
                if delta:
                    streamed_response += delta
                    yield (
                        "event: message.delta\ndata: "
                        + json.dumps({"delta": delta}, ensure_ascii=False)
                        + "\n\n"
                    )
                if turn.status.value == "COMPLETED":
                    projection = service.get_shared_understanding(interaction_id)
                    response = next(
                        (
                            message
                            for message in projection.conversation_messages
                            if message.turn_id == turn_id
                            and message.actor.value == "WATT"
                        ),
                        None,
                    )
                    if response is not None:
                        if response.content.startswith(streamed_response):
                            final_delta = response.content[len(streamed_response) :]
                            if final_delta:
                                yield (
                                    "event: message.delta\ndata: "
                                    + json.dumps(
                                        {"delta": final_delta},
                                        ensure_ascii=False,
                                    )
                                    + "\n\n"
                                )
                        else:
                            yield (
                                "event: message.reset\ndata: "
                                + json.dumps(
                                    {"content": response.content},
                                    ensure_ascii=False,
                                )
                                + "\n\n"
                            )
                        yield (
                            "event: message.completed\ndata: "
                            + json.dumps(
                                {
                                    "message_id": str(response.id),
                                    "assessment_id": str(turn.assessment_id),
                                }
                            )
                            + "\n\n"
                        )
                    return
                if turn.status.value == "FAILED":
                    yield (
                        "event: turn.failed\ndata: "
                        + json.dumps(
                            {
                                "code": turn.failure_code,
                                "message": turn.failure_message,
                            }
                        )
                        + "\n\n"
                    )
                    return
                yield ": processing\n\n"
                await asyncio.sleep(0.2)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @api.post(
        "/api/interactions/{interaction_id}/admit-work",
        response_model=SharedUnderstandingResponse,
        status_code=201,
    )
    def admit_interaction_work(
        interaction_id: UUID,
        request: InteractionWorkAdmissionRequest,
    ) -> SharedUnderstandingResponse:
        service = required_interaction_service()
        work = work_service.admit_interaction_work(
            interaction_id,
            assessment_id=request.assessment_id,
            basis_fingerprint=request.basis_fingerprint,
            authority_identity=request.authority_identity,
            rationale=request.rationale,
        )
        selected_post_admission.activate(work.work_id)
        return SharedUnderstandingResponse.from_projection(
            service.get_shared_understanding(interaction_id)
        )

    @api.post(
        "/api/interactions/{interaction_id}/work-revision-decisions",
        response_model=SharedUnderstandingResponse,
    )
    def decide_interaction_work_revision(
        interaction_id: UUID,
        request: InteractionWorkRevisionDecisionRequest,
    ) -> SharedUnderstandingResponse:
        service = required_interaction_service()
        work = work_service.decide_interaction_work_revision(
            interaction_id,
            assessment_id=request.assessment_id,
            basis_fingerprint=request.basis_fingerprint,
            expected_previous_revision_id=request.expected_previous_revision_id,
            action=request.action,
            authority_identity=request.authority_identity,
            rationale=request.rationale,
        )
        if request.action is AttentionAction.APPROVE:
            selected_post_admission.activate(work.work_id)
        return SharedUnderstandingResponse.from_projection(
            service.get_shared_understanding(interaction_id)
        )

    @api.post(
        "/api/interactions/{interaction_id}/work-transition-decisions",
        response_model=SharedUnderstandingResponse,
    )
    def decide_interaction_work_transition(
        interaction_id: UUID,
        request: InteractionWorkTransitionDecisionRequest,
    ) -> SharedUnderstandingResponse:
        return SharedUnderstandingResponse.from_projection(
            required_interaction_service().decide_work_transition(
                interaction_id,
                transition_id=request.transition_id,
                expected_originating_work_id=request.expected_originating_work_id,
                choice=request.choice,
                authority_identity=request.authority_identity,
                rationale=request.rationale,
            )
        )

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

    @api.get(
        "/api/works/{work_id}/guided-design",
        response_model=GuidedDesignResponse,
    )
    def get_guided_design(work_id: UUID) -> GuidedDesignResponse:
        return GuidedDesignResponse.from_projection(
            selected_guided_design.get(work_id)
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
