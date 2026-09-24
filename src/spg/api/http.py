"""FastAPI boundary for the minimal Goal / Work MVP product surface."""

from contextlib import asynccontextmanager
import asyncio
from importlib.resources import files
import json
from pathlib import Path, PurePosixPath
from typing import Annotated
from urllib.parse import quote
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response, FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore

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
    NativeExecutionControlRequest,
    NativeQueueEntryResponse,
    SharedUnderstandingResponse,
    RuntimeActivationResponse,
    SteeringPlanResponse,
    WorkRefineRequest,
    WorkResponse,
    WorkResultResponse,
    WorkSubmitRequest,
    WorkingAgreementCreateRequest,
    WorkingAgreementAbandonRequest,
)
from spg.application.bootstrap import Application, bootstrap
from spg.application.orchestration import ProductionOrchestrator
from spg.application.preview_security import PREVIEW_CONTENT_SECURITY_POLICY
from spg.application.interaction import WorkInteractionService
from spg.application.guided_design import GuidedDesignApplicationService
from spg.application.post_admission import WorkPostAdmissionService
from spg.application.production_admission import ProductionAdmissionTrigger
from spg.application.steering_driver import PlanSteeringDriver
from spg.application.steering_bootstrap import SteeringBootstrapService
from spg.application.runtime_activation import RuntimeActivationService
from spg.application.work import WorkApplicationService
from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.application.native_vector import NativeCandidateVectorService
from spg.application.assets import RepositoryAssetService
from spg.application.control_state import (
    ControlStateSnapshot,
    project_next_owner,
    validate_control_state,
)
from spg.application.delivery import DeliveryApplicationService, artifact_media_type
from spg.application.candidate_preview import CandidatePreviewApplicationService, CandidatePreviewUnavailable
from spg.application.control_room import ControlRoomError, ControlRoomService
from spg.application.connectors import ConnectorResolver
from spg.application.software_runtime import SoftwareRuntimeService
from spg.domain.assets import (
    AssetScopeAdmissionRequest,
    RepositoryAcquisitionFailureCategory,
    RepositoryIntakeRequest,
)
from spg.domain.change import ProductionTargetKind
from spg.domain.delivery import DeliveryTargetRequest, HumanAcceptanceRequest
from spg.domain.product import (
    AttentionAction,
    AttentionKind,
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
from spg.domain.native_execution import (
    BackendControlCommand,
    ExecutionHandle,
    NativeExecutionAdmission,
    NativeExecutionError,
)
from spg.domain.native_vector import (
    CandidateVectorAuthorizationRequest,
    CandidateVectorSealRequest,
)
from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
from spg.infrastructure.persistence import Database, DatabaseConfigurationError
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.candidate_preview_runtime import DockerCandidatePreviewRuntime
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore
from spg.domain.production_environment import CandidatePreviewMode


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
    native_executor_runtime: NativeExecutorRuntimeService | None = None,
    repository_asset_service: RepositoryAssetService | None = None,
) -> FastAPI:
    """Compose one ASGI application over the existing application bootstrap path."""

    container = application or bootstrap()
    selected_database = database
    if work_service is None:
        selected_database = selected_database or container.persistence()
        work_service = container.work(selected_database)
    else:
        selected_database = selected_database or work_service.database

    configured_workspace = getattr(getattr(container, "settings", None), "workspace_root", Path(".spg/workspaces"))
    asset_factory = getattr(container, "repository_asset_service", None)
    asset_service = repository_asset_service or (
        asset_factory(selected_database)
        if callable(asset_factory)
        else RepositoryAssetService(
            selected_database,
            configured_workspace.parent / "repository-assets",
            configured_workspace.parent / "repository-imports",
        )
    )
    delivery_service = DeliveryApplicationService(selected_database)
    settings = getattr(container, "settings", None)
    candidate_runtime_preview = None
    if getattr(settings, "native_executor_enabled", False):
        pe_root = settings.native_executor_production_environment_store_root
        candidate_runtime_preview = CandidatePreviewApplicationService(
            delivery_service,
            JsonProductionEnvironmentStore(pe_root),
            DockerCandidatePreviewRuntime(pe_root / "candidate-preview-runtime",
                verification_image=settings.native_executor_production_environment_image),
        )
    software_runtime = SoftwareRuntimeService(delivery_service,
        enabled=getattr(settings, "delivery_runtime_enabled", False),
        bind_host=getattr(settings, "delivery_runtime_bind_host", "127.0.0.1"),
        first_port=getattr(settings, "delivery_runtime_first_port", 8010),
        port_count=getattr(settings, "delivery_runtime_port_count", 10))
    delivery_service.runtime_probe = software_runtime.probe

    selected_orchestrator = orchestrator or container.production_orchestrator(
        work_service
    )
    configure_orchestrator_guard = getattr(
        selected_orchestrator, "configure_activation_guard", None
    )
    if callable(configure_orchestrator_guard):
        configure_orchestrator_guard(
            getattr(
                asset_service,
                "repository_activation_allowed",
                lambda _work_id: True,
            )
        )
    selected_steering_driver = steering_driver or container.plan_steering_driver(
        selected_database,
        work_service,
        selected_orchestrator,
        repository_assets=asset_service,
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
        activation_guard=getattr(
            asset_service,
            "repository_activation_allowed",
            lambda _work_id: True,
        ),
    )
    selected_guided_design = guided_design_service or (
        container.guided_design(selected_database)
        if hasattr(container, "guided_design")
        else GuidedDesignApplicationService(selected_database)
    )
    selected_interaction = interaction_service
    if selected_interaction is None and hasattr(container, "interaction"):
        selected_interaction = container.interaction(selected_database)
    selected_native_executor = native_executor_runtime or (
        container.native_executor_runtime(selected_database)
        if hasattr(container, "native_executor_runtime")
        else NativeExecutorRuntimeService(selected_database)
    )
    selected_native_vectors = NativeCandidateVectorService(selected_database)
    control_room = ControlRoomService(selected_database, work_service, asset_service)
    production_admission_trigger = None
    if selected_interaction is not None:
        production_admission_trigger = ProductionAdmissionTrigger(
            selected_interaction,
            work_service,
            asset_service,
            selected_post_admission,
        )
        configure_repository_action = getattr(
            selected_steering_driver, "configure_governed_repository_action", None
        )
        if callable(configure_repository_action):
            configure_repository_action(
                lambda work_id, interaction_id, authority_identity:
                    production_admission_trigger.reconcile_governed_branch(
                        work_id,
                        interaction_id=interaction_id,
                        authority_identity=authority_identity,
                    )
            )
        selected_interaction.configure_production_admission(
            production_admission_trigger.execute,
            prepare_handler=production_admission_trigger.prepare,
            reality_provider=production_admission_trigger.projection,
        )
        selected_interaction.configure_governed_branch_handler(
            production_admission_trigger.execute_explicit_branch_turn
        )

        def execution_reality(work_id: UUID) -> tuple[str | None, str | None]:
            projection = work_service.get_work(work_id)
            if (
                projection.status is not WorkStatus.RUNNING
                or projection.current_steering_step_type != "PRODUCE"
                or projection.current_production_run_id is None
            ):
                return None, None
            kind = (
                "DESIGN_ARTIFACT"
                if projection.target_kind is ProductionTargetKind.DOCUMENTATION_WORK
                else "IMPLEMENTATION"
            )
            return kind, f"production-run:{projection.current_production_run_id}"

        selected_interaction.configure_work_execution_reality(execution_reality)

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        software_runtime.restore()
        if candidate_runtime_preview is not None:
            candidate_runtime_preview.restore()
        if production_admission_trigger is not None:
            for work_id in production_admission_trigger.governed_branch_work_ids():
                selected_steering_driver.schedule(work_id)
        if selected_interaction is not None:
            resume_turns = getattr(selected_interaction, "resume_pending_turns", None)
            if callable(resume_turns):
                resume_turns()
            resume_admissions = getattr(
                selected_interaction,
                "schedule_ready_production_admission_recovery",
                None,
            )
            if callable(resume_admissions):
                resume_admissions()
        selected_post_admission.bootstrap_incomplete_ready_long_lived()
        selected_steering_driver.resume_safely_eligible_works()
        selected_orchestrator.resume_safely_eligible_works()
        try:
            yield
        finally:
            software_runtime.shutdown()
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
    api.state.native_executor_runtime = selected_native_executor
    api.state.native_candidate_vectors = selected_native_vectors
    api.state.repository_asset_service = asset_service
    web_root = Path(str(files("spg.web")))
    api.mount("/assets", StaticFiles(directory=web_root), name="assets")

    def work_response(projection: WorkProjection) -> WorkResponse:
        response = WorkResponse.from_projection(projection)

        def with_control_state(candidate: WorkResponse) -> WorkResponse:
            attention = work_service.list_attention(work_id=projection.work_id)
            action_count = sum(
                len(item.available_actions)
                + int(
                    item.kind is AttentionKind.STEERING_DECISION_REQUIRED
                    and bool(item.conversation_prompt)
                )
                for item in attention
            )
            progress = candidate.execution_progress
            active_subject = bool(
                candidate.current_production_run_id
                or (progress is not None and progress.still_working)
            )
            next_owner = project_next_owner(
                work_status=candidate.status.value,
                human_attention_required=(
                    candidate.human_attention_required or action_count > 0
                ),
                automatic_progression_state=candidate.automatic_progression_state,
                active_execution_subject=active_subject,
                external_wait_reason=(
                    candidate.what_happens_next
                    if candidate.automatic_progression_state == "WAITING_RESOURCE"
                    else None
                ),
            )
            snapshot = ControlStateSnapshot(
                work_status=candidate.status.value,
                next_owner=next_owner,
                human_attention_required=(
                    candidate.human_attention_required or action_count > 0
                ),
                actionable_human_actions=action_count,
                automatic_progression_state=candidate.automatic_progression_state,
                active_execution_subject=active_subject,
                external_wait_reason=(
                    candidate.what_happens_next
                    if candidate.automatic_progression_state == "WAITING_RESOURCE"
                    else None
                ),
                human_attention_badges=(
                    1
                    if candidate.human_attention_required or action_count > 0
                    else 0
                ),
            )
            violations = validate_control_state(snapshot)
            return candidate.model_copy(update={
                "next_owner": next_owner or None,
                "human_attention_required": (
                    candidate.human_attention_required or action_count > 0
                ),
                "control_state_valid": not violations,
                "control_state_violations": violations,
            })
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
            return with_control_state(response.model_copy(
                update={
                    "guided_design": (
                        None
                        if guided is None
                        else GuidedDesignResponse.from_projection(guided)
                    )
                }
            ))
        try:
            steering = selected_steering_driver.project(projection.work_id)
        except SteeringRecordNotFound:
            guided = selected_guided_design.get_optional(projection.work_id)
            return with_control_state(response.model_copy(
                update={
                    "guided_design": (
                        None
                        if guided is None
                        else GuidedDesignResponse.from_projection(guided)
                    )
                }
            ))
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
        elif state == "WAITING_RESOURCE" and stop_reason == "CAPABILITY_UNAVAILABLE":
            updates.update(
                {
                    "most_recent_meaningful_event": "STEERING_WAITING_PROVIDER",
                    "what_happens_next": (
                        "Watt is waiting for semantic Provider availability and will retry automatically"
                    ),
                }
            )
        guided = selected_guided_design.get_optional(projection.work_id)
        updates["guided_design"] = (
            None
            if guided is None
            else GuidedDesignResponse.from_projection(guided)
        )
        return with_control_state(response.model_copy(update=updates))

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

    @api.exception_handler(ControlRoomError)
    async def control_room_error_handler(_request: Request, error: ControlRoomError) -> JSONResponse:
        return _error(409, "CONTROL_ROOM_CONFLICT", str(error))

    @api.exception_handler(CandidatePreviewUnavailable)
    async def candidate_preview_unavailable_handler(
        _request: Request, error: CandidatePreviewUnavailable,
    ) -> JSONResponse:
        return _error(409, "CANDIDATE_PREVIEW_UNAVAILABLE", str(error))

    @api.exception_handler(ProductHttpError)
    async def product_http_handler(
        _request: Request,
        error: ProductHttpError,
    ) -> JSONResponse:
        return _error(error.status_code, error.code, str(error))

    @api.exception_handler(NativeExecutionError)
    async def native_execution_error_handler(
        _request: Request, error: NativeExecutionError
    ) -> JSONResponse:
        return _error(409, "NATIVE_EXECUTION_CONFLICT", str(error))

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
        interaction = service.create_interaction(
            human_identity=request.human_identity,
            start_work_context=request.start_work_context,
        )
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

    @api.post(
        "/api/interactions/{interaction_id}/turns/{turn_id}/retry",
        response_model=InteractionTurnResponse,
        status_code=202,
    )
    def retry_interaction_turn(
        interaction_id: UUID,
        turn_id: UUID,
    ) -> InteractionTurnResponse:
        turn = required_interaction_service().retry_turn(interaction_id, turn_id)
        return InteractionTurnResponse.from_turn(turn)

    @api.get("/api/interactions/{interaction_id}/turns/{turn_id}/timing")
    def get_interaction_turn_timing(
        interaction_id: UUID,
        turn_id: UUID,
    ) -> dict[str, object]:
        service = required_interaction_service()
        turn = service.get_turn(turn_id)
        if turn.interaction_id != interaction_id:
            raise InteractionRecordNotFound(f"Interaction Turn not found: {turn_id}")
        timing = service.turn_timing(turn_id)
        if timing is None:
            raise ProductHttpError(
                404,
                "TIMING_OBSERVATION_UNAVAILABLE",
                "Process-local Turn timing is unavailable after restart or eviction",
            )
        return timing

    @api.get("/api/interactions/{interaction_id}/turns/{turn_id}/events")
    async def stream_interaction_turn(
        interaction_id: UUID,
        turn_id: UUID,
        request: Request,
        after_sequence: int = Query(default=0, ge=0),
    ) -> StreamingResponse:
        service = required_interaction_service()
        initial = service.get_turn(turn_id)
        if initial.interaction_id != interaction_id:
            raise InteractionRecordNotFound(f"Interaction Turn not found: {turn_id}")

        async def events():
            if initial.wic_mode.value == "WIC_VNEXT_CONTROLLED":
                cursor = after_sequence
                header_cursor = request.headers.get("last-event-id")
                if header_cursor and header_cursor.isdigit():
                    cursor = max(cursor, int(header_cursor))
                existing_events = await asyncio.to_thread(
                    service.response_events,
                    turn_id,
                    after_sequence=0,
                )
                latest_recovery = next(
                    (
                        event
                        for event in reversed(existing_events)
                        if event.event_type.value == "TURN_RECOVERY_STARTED"
                    ),
                    None,
                )
                if latest_recovery is not None:
                    # A retry reuses the Human Turn identity. Replay only the latest
                    # attempt while retaining prior failure evidence in storage.
                    cursor = max(cursor, latest_recovery.sequence - 1)
                event_names = {
                    "TURN_ACCEPTED": "turn.accepted",
                    "FAST_RECEPTION_STARTED": "fast.started",
                    "PROVISIONAL_RESPONSE": "response.provisional",
                    "FAST_SUPPRESSED": "fast.suppressed",
                    "RESPONSE_REFINEMENT": "response.refinement",
                    "RESPONSE_CORRECTION": "response.correction",
                    "RESPONSE_STREAM_STARTED": "response.stream.started",
                    "RESPONSE_DELTA": "response.delta",
                    "FINAL_RESPONSE": "response.final",
                    "TURN_COMPLETED": "message.completed",
                    "TURN_FAILED": "turn.failed",
                    "TURN_RECOVERY_STARTED": "turn.recovery.started",
                }
                while True:
                    if await request.is_disconnected():
                        return
                    response_events = await asyncio.to_thread(
                        service.response_events,
                        turn_id,
                        after_sequence=cursor,
                    )
                    for response_event in response_events:
                        cursor = response_event.sequence
                        if response_event.event_type.value == "RESPONSE_CONTRACT_READY":
                            # Internal turn decision evidence is not a Human response event.
                            continue
                        payload = response_event.model_dump(mode="json")
                        payload["response_id"] = str(response_event.response_id)
                        if response_event.event_type.value == "TURN_FAILED":
                            current = service.get_turn(turn_id)
                            payload.update(
                                code=current.failure_code,
                                message=current.failure_message,
                            )
                        event_name = event_names[response_event.event_type.value]
                        service.record_turn_stream_event(turn_id)
                        yield (
                            f"id: {cursor}\nevent: {event_name}\ndata: "
                            + json.dumps(payload, ensure_ascii=False)
                            + "\n\n"
                        )
                        if response_event.event_type.value in {"TURN_COMPLETED", "TURN_FAILED"}:
                            if response_event.event_type.value == "TURN_COMPLETED":
                                service.record_turn_stream_completed(turn_id)
                            return
                    yield ": processing\n\n"
                    await asyncio.sleep(0.05)

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
                    service.record_turn_stream_event(turn_id)
                    yield f"event: turn.status\ndata: {json.dumps(payload)}\n\n"
                    last_status = turn.status.value
                delta, stream_offset = service.turn_response_delta(
                    turn_id, stream_offset
                )
                if delta:
                    streamed_response += delta
                    yield (
                        "event: message.delta\ndata: "
                        + json.dumps(
                            {"delta": delta, "trust_stage": "PROVISIONAL"},
                            ensure_ascii=False,
                        )
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
                                    {
                                        "content": response.content,
                                        "trust_stage": "FINAL",
                                    },
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
                                    "trust_stage": "FINAL",
                                }
                            )
                            + "\n\n"
                        )
                        service.record_turn_stream_completed(turn_id)
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
        selected_resource_id = request.engineering_resource_id
        projection = service.get_shared_understanding(interaction_id)
        assessment = projection.latest_assessment
        if (
            assessment is None
            or not projection.latest_assessment_current
            or assessment.id != request.assessment_id
            or assessment.basis_fingerprint != request.basis_fingerprint
            or projection.readiness is None
            or projection.readiness.status.value != "READY"
        ):
            raise InteractionInvariantViolation(
                "Only the exact current READY assessment may prepare repository Reality"
            )
        work = work_service.admit_interaction_work(
            interaction_id,
            engineering_resource_id=selected_resource_id,
            use_default_resource=False,
            assessment_id=request.assessment_id,
            basis_fingerprint=request.basis_fingerprint,
            authority_identity=request.authority_identity,
            rationale=request.rationale,
        )
        repository_observation = None
        if selected_resource_id is None and projection.repository_source:
            attempt_id = uuid5(
                NAMESPACE_URL,
                "watt:interaction-repository:"
                f"{work.work_id}:1:{projection.repository_source}",
            )
            asset_service.start_intake(
                RepositoryIntakeRequest(
                    request_id=attempt_id,
                    source=projection.repository_source,
                    title=(
                        projection.interpreted_motive
                        or "Repository production Work"
                    )[:200],
                    description=(
                        projection.desired_outcome
                        or "Discover repository Reality for the admitted production request."
                    )[:4000],
                    authority_identity=request.authority_identity,
                    interaction_id=interaction_id,
                    work_id=work.work_id,
                    attempt_number=1,
                )
            )
            repository_observation = asset_service.execute_intake(attempt_id)
            if (
                repository_observation.get("condition") == "READY"
                and repository_observation.get("resource_id")
            ):
                try:
                    work = work_service.admit_asset_scope(
                        work.work_id,
                        AssetScopeAdmissionRequest(
                            resource_id=UUID(repository_observation["resource_id"]),
                            expected_work_revision_id=(
                                work.current_work_reality_revision_id
                            ),
                            observation_fingerprint=(
                                repository_observation["fingerprint"]
                            ),
                            authority_identity=request.authority_identity,
                            rationale=(
                                "Bind acquired repository Reality before activating "
                                "manual Work admission."
                            ),
                        ),
                        repository_observation,
                    )
                except Exception as error:
                    repository_observation = asset_service.mark_attempt_failure(
                        attempt_id,
                        category=(
                            RepositoryAcquisitionFailureCategory.ACQUISITION_FAILED_RETRYABLE
                        ),
                        human_message=(
                            "The repository was acquired, but it could not be bound "
                            "to this Work. Retry is available."
                        ),
                        technical_evidence={
                            "phase": "WORK_REALITY_BINDING",
                            "error_type": type(error).__name__,
                            "message": str(error)[:2000],
                        },
                        retryable=True,
                    )
        if (
            selected_resource_id is not None
            or projection.repository_source is None
            or (
                repository_observation is not None
                and repository_observation.get("condition") == "READY"
            )
        ):
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
            # A revision evolves an already admitted Work. Reassess it through
            # the existing Steering lifecycle instead of re-entering the
            # first-admission status gate after the revision has committed.
            selected_steering_driver.schedule(work.work_id)
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

    @api.get("/api/works/{work_id}/self-refine")
    def work_self_refine_events(work_id: UUID) -> dict:
        work_service.get_work(work_id)
        with selected_database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            records = store.list_self_refine_events(work_id=work_id)
            metrics = store.self_refine_metrics(work_id=work_id)
        return {
            "count": len(records),
            "events": [record.model_dump(mode="json") for record in records],
            "metrics": metrics,
        }

    @api.get("/api/self-refine")
    def platform_self_refine_events(
        failure_family: str | None = None,
        component: str | None = None,
        result: str | None = None,
    ) -> dict:
        with selected_database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            records = store.list_self_refine_events(
                failure_family=failure_family, component=component, result=result,
            )
            metrics = store.self_refine_metrics()
        return {
            "count": len(records),
            "events": [record.model_dump(mode="json") for record in records],
            "metrics": metrics,
        }

    @api.get("/api/self-refine/metrics")
    def platform_self_refine_metrics() -> dict:
        with selected_database.unit_of_work() as uow:
            return NativeExecutionStore(uow.session).self_refine_metrics()

    @api.get("/api/self-refine/{event_id}")
    def self_refine_event_detail(event_id: UUID) -> dict:
        with selected_database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            event = store.self_refine_event(event_id)
            actions = store.self_refine_actions(event_id)
        return {
            "event": event.model_dump(mode="json"),
            "actions": [action.model_dump(mode="json") for action in actions],
        }

    @api.get("/api/works/{work_id}/capability-gaps")
    def work_capability_gaps(work_id: UUID) -> list[dict]:
        work_service.get_work(work_id)
        return [
            {
                "gap_id": str(item["id"]),
                "capability_id": item["capability_id"],
                "operation_ref": item["operation_ref"],
                "condition": item["condition"],
                "reason": item["reason"],
            }
            for item in ConnectorResolver(selected_database).gaps_for_work(work_id)
        ]

    @api.post("/api/works/{work_id}/discard-pre-work", status_code=204)
    def discard_pre_work(work_id: UUID, request: HumanDecisionRequest) -> Response:
        work_service.discard_pre_work(
            work_id,
            authority_identity=request.authority_identity,
        )
        return Response(status_code=204)

    @api.get("/api/works/{work_id}/control-room/sources")
    def work_sources(work_id: UUID):
        return control_room.sources(work_id)

    @api.post("/api/works/{work_id}/repository-acquisition/retry")
    def retry_repository_acquisition(
        work_id: UUID, request: HumanDecisionRequest
    ) -> dict:
        if production_admission_trigger is None:
            raise ProductInvariantViolation(
                "Repository acquisition is unavailable in this runtime"
            )
        return production_admission_trigger.retry_work(
            work_id,
            authority_identity=request.authority_identity,
        )

    @api.get("/api/works/{work_id}/control-room/file")
    def work_source_file(work_id: UUID, path: str, revision: str):
        return control_room.file(work_id, path, revision)

    @api.get("/api/works/{work_id}/working-agreements")
    def work_agreements(work_id: UUID):
        return control_room.agreements(work_id)

    @api.post("/api/works/{work_id}/working-agreements", status_code=201)
    def create_work_agreement(work_id: UUID, request: WorkingAgreementCreateRequest):
        return control_room.create_agreement(
            work_id, content=request.content, agreement_type=request.agreement_type,
            actor_identity=request.actor_identity,
        )

    @api.post("/api/works/{work_id}/working-agreements/{agreement_id}/abandon")
    def abandon_work_agreement(work_id: UUID, agreement_id: UUID, request: WorkingAgreementAbandonRequest):
        return control_room.abandon_agreement(
            work_id, agreement_id, actor_identity=request.actor_identity,
        )

    @api.get(
        "/api/native-execution/queue",
        response_model=list[NativeQueueEntryResponse],
    )
    def native_execution_queue(work_id: UUID | None = None) -> list[NativeQueueEntryResponse]:
        reality = selected_native_executor.list_queue_reality(work_id=work_id)
        with selected_database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            bindings = {
                record.pwu_id: product.runtime_binding_for_work_unit(record.pwu_id)
                for record, _observation in reality
            }
        return [
            NativeQueueEntryResponse.from_record(
                record,
                observation,
                production_cycle_number=(
                    None
                    if bindings[record.pwu_id] is None
                    else bindings[record.pwu_id].cycle_number
                ),
                work_reality_revision_id=(
                    None
                    if bindings[record.pwu_id] is None
                    else bindings[record.pwu_id].work_reality_revision_id
                ),
            )
            for record, observation in reality
        ]

    @api.post(
        "/api/native-execution/admissions",
        response_model=NativeQueueEntryResponse,
    )
    def admit_native_execution(
        admission: NativeExecutionAdmission,
    ) -> NativeQueueEntryResponse:
        if not getattr(settings, "native_executor_enabled", False):
            raise ProductHttpError(
                409,
                "NATIVE_EXECUTOR_DISABLED",
                "Watt-native Executor admission is not enabled for this Runtime",
            )
        return NativeQueueEntryResponse.from_record(
            selected_native_executor.admit(admission)
        )

    @api.get("/api/native-execution/pwus/{pwu_id}/events")
    async def native_execution_events(
        pwu_id: UUID,
        request: Request,
        after_sequence: int = Query(default=0, ge=0),
    ) -> StreamingResponse:
        async def stream():
            cursor = after_sequence
            idle_cycles = 0
            while not await request.is_disconnected() and idle_cycles < 60:
                def load_events():
                    with selected_database.unit_of_work() as uow:
                        store = NativeExecutionStore(uow.session)
                        return (
                            store.event_sequence_window(pwu_id),
                            store.events_since(pwu_id, after_sequence=cursor),
                        )

                window, events = await asyncio.to_thread(load_events)
                minimum, high_water = window
                cursor_expired = (
                    cursor > 0
                    and minimum is not None
                    and cursor < minimum - 1
                )
                cursor_ahead = high_water is not None and cursor > high_water
                if cursor_expired or cursor_ahead:
                    reset_to = high_water or 0
                    payload = json.dumps(
                        {
                            "reason": (
                                "CURSOR_EXPIRED" if cursor_expired else "CURSOR_AHEAD"
                            ),
                            "pwu_id": str(pwu_id),
                            "high_water_sequence": reset_to,
                            "snapshot_url": f"/api/native-execution/pwus/{pwu_id}/snapshot",
                        },
                        ensure_ascii=False,
                    )
                    cursor = reset_to
                    yield f"id: {reset_to}\nevent: RESET\ndata: {payload}\n\n"
                    continue
                if not events:
                    idle_cycles += 1
                    yield ": keep-alive\n\n"
                    await asyncio.sleep(0.5)
                    continue
                idle_cycles = 0
                for event in events:
                    cursor = event.sequence
                    payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
                    yield f"id: {event.sequence}\nevent: {event.event_type}\ndata: {payload}\n\n"

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @api.get("/api/native-execution/pwus/{pwu_id}/snapshot")
    def native_execution_snapshot(pwu_id: UUID) -> dict[str, object]:
        with selected_database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            minimum, high_water = store.event_sequence_window(pwu_id)
            attempts = []
            for attempt_id in store.attempt_ids_for_pwu(pwu_id):
                state = store.attempt_state(attempt_id)
                queue = store.queue_for_attempt(attempt_id)
                attempts.append(
                    {
                        "attempt_id": str(attempt_id),
                        "state": state.model_dump(mode="json"),
                        "queue": (
                            queue.model_dump(mode="json") if queue is not None else None
                        ),
                    }
                )
        return {
            "pwu_id": str(pwu_id),
            "minimum_retained_sequence": minimum,
            "high_water_sequence": high_water or 0,
            "attempts": attempts,
        }

    @api.post("/api/native-execution/candidate-vectors")
    def seal_native_candidate_vector(request: CandidateVectorSealRequest):
        if not getattr(settings, "native_executor_enabled", False):
            raise ProductHttpError(
                409, "NATIVE_EXECUTOR_DISABLED",
                "Watt-native Executor Candidate sealing is not enabled",
            )
        return selected_native_vectors.seal(request).model_dump(mode="json")

    @api.get("/api/native-execution/candidate-vectors/{vector_id}")
    def inspect_native_candidate_vector(vector_id: UUID):
        return selected_native_vectors.projection(vector_id).model_dump(mode="json")

    @api.post("/api/native-execution/candidate-vectors/{vector_id}/authorize")
    def authorize_native_candidate_vector(
        vector_id: UUID, request: CandidateVectorAuthorizationRequest
    ):
        if not getattr(settings, "native_executor_enabled", False):
            raise ProductHttpError(
                409, "NATIVE_EXECUTOR_DISABLED",
                "Watt-native Executor Candidate authorization is not enabled",
            )
        if vector_id != request.vector_id:
            raise ProductHttpError(
                409, "VECTOR_ID_MISMATCH", "Route and authorization vector differ"
            )
        return selected_native_vectors.authorize(request).model_dump(mode="json")

    @api.post("/api/native-execution/candidate-vectors/{vector_id}/integrate")
    def integrate_native_candidate_vector(vector_id: UUID):
        if not getattr(settings, "native_executor_enabled", False):
            raise ProductHttpError(
                409, "NATIVE_EXECUTOR_DISABLED",
                "Watt-native Executor integration is not enabled",
            )
        return selected_native_vectors.integrate(vector_id).model_dump(mode="json")

    @api.post("/api/native-execution/candidate-vectors/{vector_id}/commit")
    def commit_native_candidate_vector(vector_id: UUID):
        if not getattr(settings, "native_executor_enabled", False):
            raise ProductHttpError(
                409, "NATIVE_EXECUTOR_DISABLED",
                "Watt-native Executor aggregate commit is not enabled",
            )
        return selected_native_vectors.commit(vector_id).model_dump(mode="json")

    @api.get("/api/native-execution/attempts/{attempt_id}")
    def native_execution_attempt(attempt_id: UUID):
        with selected_database.unit_of_work() as uow:
            store = NativeExecutionStore(uow.session)
            state = store.attempt_state(attempt_id)
            queue = store.queue_for_attempt(attempt_id)
            steps = store.steps_for_attempt(attempt_id)
            effects = store.effects_for_attempt(attempt_id)
            evidence = store.evidence_for_attempt(attempt_id)
            checkpoint = store.latest_checkpoint(attempt_id)
            timing = store.timing_projection(attempt_id)
        handle = ExecutionHandle(
            backend_identity="watt-native",
            dispatch_id=queue.id if queue else attempt_id,
            attempt_id=attempt_id,
            generation=state.generation,
            opaque_reference=f"attempt:{attempt_id}",
        )
        return {
            "observation": selected_native_executor.observe(handle).model_dump(mode="json"),
            "state": state.model_dump(mode="json"),
            "queue": queue.model_dump(mode="json") if queue else None,
            "steps": [item.model_dump(mode="json") for item in steps],
            "effects": [item.model_dump(mode="json") for item in effects],
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "checkpoint": checkpoint.model_dump(mode="json") if checkpoint else None,
            "timing": timing,
        }

    @api.post("/api/native-execution/attempts/{attempt_id}/control")
    def native_execution_control(attempt_id: UUID, request: NativeExecutionControlRequest):
        if not getattr(settings, "native_executor_enabled", False):
            raise ProductHttpError(
                409,
                "NATIVE_EXECUTOR_DISABLED",
                "Watt-native Executor control is not enabled for this Runtime",
            )
        with selected_database.unit_of_work() as uow:
            state = NativeExecutionStore(uow.session).attempt_state(attempt_id)
        handle = ExecutionHandle(
            backend_identity="watt-native",
            dispatch_id=attempt_id,
            attempt_id=attempt_id,
            generation=state.generation,
            opaque_reference=f"attempt:{attempt_id}",
        )
        receipt = selected_native_executor.control(
            BackendControlCommand(
                command_id=request.command_id,
                handle=handle,
                action=request.action,
                expected_control_version=request.expected_control_version,
                actor_identity=request.actor_identity,
                reason=request.reason,
            )
        )
        return receipt.model_dump(mode="json")

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

    @api.post("/api/works/{work_id}/retry-production", response_model=WorkResponse)
    def retry_failed_production(
        work_id: UUID,
        request: HumanDecisionRequest,
    ) -> WorkResponse:
        projection = work_service.retry_failed_production(
            work_id,
            authority_identity=request.authority_identity,
        )
        # The current production cycle is already admitted. Steering may still
        # observe the prior failed Verification as BLOCKED until this successor
        # Attempt runs, so schedule its owner directly and let normal Steering
        # reconcile the resulting evidence afterward.
        selected_orchestrator.schedule(work_id)
        return work_response(projection)

    @api.post("/api/works/{work_id}/retry-steering", response_model=WorkResponse)
    def retry_stopped_steering(
        work_id: UUID,
        request: HumanDecisionRequest,
    ) -> WorkResponse:
        projection = work_service.get_work(work_id)
        if not projection.steering_enabled:
            raise ProductHttpError(
                409,
                "STEERING_NOT_ENABLED",
                "This Work does not use automatic Plan Steering",
            )
        steering = selected_steering_driver.project(work_id)
        recoverable_block = (
            steering.last_stop_reason is not None
            and steering.last_stop_reason.value == "BLOCKED"
        )
        resolved_attention = (
            steering.last_stop_reason is not None
            and steering.last_stop_reason.value == "HUMAN_ATTENTION"
            and projection.status is WorkStatus.READY
            and not work_service.list_attention(work_id=work_id)
        )
        if not (
            steering.automatic_progression_state.value == "STOPPED"
            and (recoverable_block or resolved_attention)
        ):
            raise ProductHttpError(
                409,
                "STEERING_RETRY_NOT_AVAILABLE",
                "Plan Steering is not stopped on a recoverable governed invariant",
            )
        selected_steering_driver.schedule(work_id)
        return work_response(work_service.get_work(work_id))

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
        preview_authorization_work = None
        if request.action is AttentionAction.AUTHORIZE:
            attention = next((item for item in work_service.list_attention()
                if item.id == attention_id), None)
            if attention is not None and attention.kind is AttentionKind.CANDIDATE_AUTHORIZATION:
                context = delivery_service.candidate_context(attention.work_id)
                if context is not None and CandidatePreviewApplicationService.mode_for(context) in {
                    CandidatePreviewMode.FULL_APPLICATION_RUNTIME, CandidatePreviewMode.FRONTEND_RUNTIME,
                }:
                    if candidate_runtime_preview is None:
                        raise CandidatePreviewUnavailable("Functional Candidate Preview is unavailable")
                    candidate_runtime_preview.require_ready(attention.work_id, UUID(context["candidate_id"]))
                    preview_authorization_work = attention.work_id
        projection = work_service.resolve_attention(attention_id, resolution)
        if preview_authorization_work is not None:
            candidate_runtime_preview.record_authorization(
                preview_authorization_work, request.authority_identity,
            )
        if request.action is AttentionAction.APPROVE:
            projection = selected_post_admission.activate(projection.work_id)
        elif projection.status in {WorkStatus.READY, WorkStatus.RUNNING}:
            selected_orchestrator.schedule(projection.work_id)
        return work_response(projection)

    @api.get("/delivery", include_in_schema=False)
    def delivery_page():
        return FileResponse(web_root / "delivery.html")

    @api.get("/api/repository-assets")
    def repository_assets(work_id: UUID | None = None):
        return asset_service.list_assets(work_id)

    @api.post("/api/repository-assets/intake")
    def intake_repository(request: RepositoryIntakeRequest):
        return asset_service.intake(request)

    @api.post("/api/works/{work_id}/asset-scope-admissions")
    def admit_asset_scope(work_id: UUID, request: AssetScopeAdmissionRequest):
        observation = asset_service.observation(request.resource_id)
        work = work_service.admit_asset_scope(work_id, request, observation)
        selected_steering_driver.schedule(work_id)
        return work_response(work)

    @api.get("/api/works/{work_id}/delivery")
    def delivery_view(work_id: UUID):
        return delivery_service.view(work_id)

    @api.get("/api/works/{work_id}/delivery-context")
    def delivery_context(work_id: UUID):
        return delivery_service.context(work_id)

    @api.post("/api/works/{work_id}/candidate-preview")
    def candidate_preview(work_id: UUID):
        context = delivery_service.candidate_context(work_id)
        if context is None:
            return {"status": "NOT_READY", "reason": "No current verified Candidate is available", "downloads": []}
        public = {key: context[key] for key in ("candidate_id", "candidate_fingerprint",
            "repository_revision", "tree", "entrypoint", "preview_kind", "artifacts",
            "verification", "authorization_pending")}
        prefix = f"/api/works/{work_id}"
        fingerprint = context["candidate_fingerprint"]
        entrypoint = context["entrypoint"]
        preview_kind = context["preview_kind"]
        return {**public, "status": "READY" if preview_kind else "NOT_READY",
            "reason": None if preview_kind else "No current preview is available",
            "url": (f"{prefix}/candidate-preview/{fingerprint}/{quote(entrypoint, safe='/')}"
                if preview_kind == "STATIC_WEB" else
                f"{prefix}/candidate-code-diff/{fingerprint}" if preview_kind == "CODE_DIFF" else None),
            "downloads": [{"path": path, "url": (
                f"{prefix}/candidate-download/{fingerprint}/{quote(path, safe='/')}")}
                for path in context["artifacts"]]}

    @api.get("/api/works/{work_id}/functional-preview")
    def functional_candidate_preview(work_id: UUID):
        context = delivery_service.candidate_context(work_id)
        if context is None:
            return {"mode": None, "status": "NOT_READY", "session": None}
        mode = CandidatePreviewApplicationService.mode_for(context)
        session = None if candidate_runtime_preview is None else candidate_runtime_preview.current(work_id)
        return {"mode": None if mode is None else mode.value,
            "status": "NOT_REQUESTED" if session is None else session.status.value,
            "candidate_revision": context["repository_revision"],
            "candidate_fingerprint": context["candidate_fingerprint"],
            "session": None if session is None else session.model_dump(mode="json")}

    @api.post("/api/works/{work_id}/functional-preview")
    def start_functional_candidate_preview(work_id: UUID):
        if candidate_runtime_preview is None:
            raise CandidatePreviewUnavailable("Full-application Preview Runtime is not configured")
        return candidate_runtime_preview.request(work_id).model_dump(mode="json")

    @api.post("/api/works/{work_id}/functional-preview/stop")
    def stop_functional_candidate_preview(work_id: UUID):
        if candidate_runtime_preview is None:
            raise CandidatePreviewUnavailable("Full-application Preview Runtime is not configured")
        return candidate_runtime_preview.stop(work_id).model_dump(mode="json")

    @api.get("/api/works/{work_id}/candidate-code-diff/{candidate_fingerprint}")
    def candidate_code_diff(work_id: UUID, candidate_fingerprint: str):
        return Response(delivery_service.candidate_code_diff(work_id, candidate_fingerprint),
            media_type="text/plain; charset=utf-8", headers={"X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store", "Content-Security-Policy": "default-src 'none'; sandbox"})

    @api.get("/api/works/{work_id}/candidate-preview/{candidate_fingerprint}/{path:path}")
    def candidate_preview_artifact(work_id: UUID, candidate_fingerprint: str, path: str):
        return Response(delivery_service.candidate_artifact(work_id, candidate_fingerprint, path),
            media_type=artifact_media_type(path), headers={"X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
                "Content-Security-Policy": PREVIEW_CONTENT_SECURITY_POLICY})

    @api.get("/api/works/{work_id}/candidate-download/{candidate_fingerprint}/{path:path}")
    def candidate_download_artifact(work_id: UUID, candidate_fingerprint: str, path: str):
        filename = quote(PurePosixPath(path).name)
        return Response(delivery_service.candidate_download(work_id, candidate_fingerprint, path),
            media_type=artifact_media_type(path), headers={"X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
                "Content-Security-Policy": "default-src 'none'; sandbox"})

    @api.post("/api/works/{work_id}/delivery-target")
    def delivery_target(work_id: UUID, request: DeliveryTargetRequest):
        return delivery_service.set_target(work_id, request)

    @api.post("/api/works/{work_id}/deliveries")
    def publish_delivery(work_id: UUID):
        return delivery_service.publish(work_id)

    @api.post("/api/works/{work_id}/deliveries/{manifest_id}/runtime")
    def start_software_runtime(work_id: UUID, manifest_id: UUID):
        return software_runtime.start(work_id, manifest_id)

    @api.get("/api/works/{work_id}/deliveries/{manifest_id}/runtime")
    def get_software_runtime(work_id: UUID, manifest_id: UUID):
        return software_runtime.view(work_id, manifest_id)

    @api.get("/api/works/{work_id}/deliveries/{manifest_id}/artifact")
    def delivery_artifact(work_id: UUID, manifest_id: UUID, path: str):
        return Response(delivery_service.artifact(work_id, manifest_id, path), media_type="text/plain; charset=utf-8",
            headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'none'"})

    @api.get("/api/works/{work_id}/deliveries/{manifest_id}/download")
    def delivery_download(work_id: UUID, manifest_id: UUID):
        return Response(delivery_service.package(work_id, manifest_id), media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="delivery-{manifest_id}.zip"', "X-Content-Type-Options": "nosniff"})

    @api.post("/api/works/{work_id}/deliveries/{manifest_id}/acceptance")
    def human_acceptance(work_id: UUID, manifest_id: UUID, request: HumanAcceptanceRequest):
        return delivery_service.decide(work_id, manifest_id, request)

    @api.get("/api/works/{work_id}/result", response_model=WorkResultResponse)
    def get_work_result(work_id: UUID) -> WorkResultResponse:
        return WorkResultResponse.from_projection(
            work_service.get_work_result(work_id),
            selected_runtime_activation.project(),
        )

    return api
