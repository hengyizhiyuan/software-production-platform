"""Explicit application composition for the S1-A foundation."""

from dataclasses import dataclass
from pathlib import Path

from spg.config import Settings
from spg.application.runtime import RuntimeService
from spg.application.guided_design import GuidedDesignApplicationService
from spg.application.preparation import PreparationService
from spg.application.materialization import ExecutionInputMaterializationService
from spg.application.execution import ExecutionService
from spg.application.completion import CompletionService
from spg.application.verification import VerificationService
from spg.application.governance import CandidateGovernanceService
from spg.application.integration import RepositoryIntegrationService
from spg.application.interaction import (
    UnavailableWorkInteractionCapability,
    WorkInteractionService,
)
from spg.application.wic_reception import (
    DeterministicFastReceptionCapability,
    ShadowFastReceptionRuntime,
)
from spg.domain.wic_response import WicRuntimeMode
from spg.application.runtime_commit import RuntimeCommitService
from spg.application.recovery import RecoveryAssessmentService
from spg.application.reconciliation import RecoveryReconciliationService
from spg.application.attempt_recovery import AttemptRecoveryService
from spg.application.maintenance_recovery import VerifiedMaintenanceRecoveryService
from spg.application.orchestration import ProductionOrchestrator
from spg.application.post_admission import WorkPostAdmissionService
from spg.application.steering import SteeringApplicationService
from spg.application.steering_decision import (
    DeterministicPlanSteeringCapability,
    PlanFrameAssembler,
    SteeringDecisionApplicationService,
)
from spg.application.steering_driver import PlanSteeringDriver
from spg.application.steering_bootstrap import (
    InitialSteeringPlanFormationCapability,
    SteeringBootstrapService,
)
from spg.application.runtime_activation import RuntimeActivationService
from spg.application.executor_runtime import NativeExecutorRuntimeService
from spg.application.work import WorkApplicationService
from spg.domain.executor import ExecutorCapabilityContract
from spg.domain.interaction import WorkInteractionCapability
from spg.domain.preparation import ExecutorBinding
from spg.domain.planning import ProductionPlanner
from spg.domain.steering import PlanSteeringCapability, SemanticStepCapability
from spg.domain.verifier import VerificationCapabilityContract
from spg.infrastructure.persistence import Database


@dataclass(frozen=True, slots=True)
class Application:
    """Minimal application container without external side effects."""

    settings: Settings

    def status(self) -> dict[str, str]:
        """Return foundation metadata without fabricating production state."""

        return {
            "application": self.settings.application_name,
            "foundation": "ready",
            "runtime_profile": self.settings.runtime_profile,
        }

    def persistence(self) -> Database:
        """Compose persistence explicitly without affecting foundation status."""

        return Database.from_settings(self.settings)

    def runtime(self, database: Database | None = None) -> RuntimeService:
        """Compose governed Runtime operations over explicit persistence."""

        return RuntimeService(database or self.persistence())

    def native_executor_runtime(
        self,
        database: Database | None = None,
    ) -> NativeExecutorRuntimeService:
        """Compose the additive Watt-native Executor v2 runtime."""

        return NativeExecutorRuntimeService(database or self.persistence())

    def preparation(self, database: Database | None = None) -> PreparationService:
        """Compose S2-A preparation without composing or dispatching an Executor."""

        return PreparationService(database or self.persistence())

    def execution(self, database: Database | None = None) -> ExecutionService:
        """Compose S2-B Runtime orchestration without selecting a real provider."""

        selected_database = database or self.persistence()
        preparation = PreparationService(selected_database)
        return ExecutionService(selected_database, preparation=preparation)

    def execution_input_materialization(
        self,
        database: Database | None = None,
    ) -> ExecutionInputMaterializationService:
        """Compose exact Provider input materialization without selecting a Provider."""

        selected_database = database or self.persistence()
        preparation = PreparationService(selected_database)
        return ExecutionInputMaterializationService(
            selected_database,
            preparation=preparation,
        )

    def completion(self, database: Database | None = None) -> CompletionService:
        """Compose S3-A output evaluation without Verification or Candidate logic."""

        return CompletionService(database or self.persistence())

    def verification(self, database: Database | None = None) -> VerificationService:
        """Compose S3-B without selecting Guardian or creating a Candidate."""

        return VerificationService(database or self.persistence())

    def candidate_governance(
        self,
        database: Database | None = None,
    ) -> CandidateGovernanceService:
        """Compose S3-C without Repository Integration or Runtime Commit."""

        return CandidateGovernanceService(database or self.persistence())

    def repository_integration(
        self,
        database: Database | None = None,
    ) -> RepositoryIntegrationService:
        """Compose S4-A without Runtime Commit or Trusted Baseline advancement."""

        return RepositoryIntegrationService(database or self.persistence())

    def runtime_commit(
        self,
        database: Database | None = None,
    ) -> RuntimeCommitService:
        """Compose S4-B without repository mutation or S5 recovery."""

        return RuntimeCommitService(database or self.persistence())

    def recovery_assessment(
        self,
        database: Database | None = None,
    ) -> RecoveryAssessmentService:
        """Compose S5-A classification without executing recovery."""

        return RecoveryAssessmentService(database or self.persistence())

    def recovery_reconciliation(
        self,
        database: Database | None = None,
    ) -> RecoveryReconciliationService:
        """Compose S5-B without Git mutation or broad automatic recovery."""

        return RecoveryReconciliationService(database or self.persistence())

    def attempt_recovery(
        self,
        database: Database | None = None,
    ) -> AttemptRecoveryService:
        """Compose S5-C salvage/retry preparation without provider dispatch."""

        return AttemptRecoveryService(database or self.persistence())

    def verified_maintenance_recovery(
        self,
        database: Database | None = None,
    ) -> VerifiedMaintenanceRecoveryService:
        """Compose exact R4-B recovery without executing production or mutating Git."""

        return VerifiedMaintenanceRecoveryService(database or self.persistence())

    def work(
        self,
        database: Database | None = None,
        *,
        workspace_root: Path | None = None,
        executor: ExecutorCapabilityContract | None = None,
        verifier: VerificationCapabilityContract | None = None,
        planner: ProductionPlanner | None = None,
        executor_binding: ExecutorBinding | None = None,
    ) -> WorkApplicationService:
        """Compose the goal-centric MVP product flow over governed Runtime services."""

        selected_database = database or self.persistence()
        selected_executor = executor
        selected_verifier = verifier
        selected_binding = executor_binding
        selected_preparation = None
        if selected_executor is None and self.settings.executor_adapter == "codex-sdk":
            from spg.infrastructure.configured_executor import (
                GovernedDedicatedExecutor,
            )

            selected_executor = GovernedDedicatedExecutor(
                selected_database,
                provider_timeout_seconds=self.settings.executor_timeout_seconds,
                max_internal_turns=self.settings.executor_max_internal_turns,
                provider_sandbox_mode=self.settings.executor_sandbox_mode,
            )
            selected_binding = ExecutorBinding(
                binding_ref="binding:codex-sdk-dedicated-process",
                capability_identity="capability:executor",
                profile_identity="profile:local-docker-codex-e2e",
            )
        elif selected_executor is None and self.settings.executor_adapter == "watt-native":
            from spg.application.native_production_environment import (
                NativeProductionEnvironmentRuntime,
            )
            from spg.infrastructure.executor_runtime.native_compatibility_executor import (
                NativeQueuedExecutorCapability,
            )
            from spg.infrastructure.git_workspace import GitCloneAttemptWorkspace
            from spg.infrastructure.production_environment import (
                ContainerProductionEnvironmentProvider,
                DockerCliContainerRuntime,
            )
            from spg.infrastructure.production_environment_store import (
                JsonProductionEnvironmentStore,
            )

            production_environment = NativeProductionEnvironmentRuntime(
                store=JsonProductionEnvironmentStore(
                    self.settings.native_executor_production_environment_store_root
                ),
                provider=ContainerProductionEnvironmentProvider(
                    DockerCliContainerRuntime(
                        workspace_volume=(
                            self.settings.native_executor_production_environment_workspace_volume
                        ),
                        workspace_volume_root=self.settings.workspace_root,
                    )
                ),
                image_reference=(
                    self.settings.native_executor_production_environment_image
                ),
            )

            selected_executor = NativeQueuedExecutorCapability(
                selected_database,
                self.native_executor_runtime(selected_database),
                provider_profile=self.settings.native_executor_provider_profile,
                resource_profile=self.settings.native_executor_resource_profile,
                environment_profile=self.settings.native_executor_worker_profile,
                poll_seconds=self.settings.native_executor_poll_seconds,
                wait_seconds=self.settings.native_executor_compatibility_wait_seconds,
                production_environment=production_environment,
            )
            selected_binding = ExecutorBinding(
                binding_ref="binding:watt-native-queue-v2",
                capability_identity="capability:watt-native-executor",
                profile_identity=self.settings.native_executor_worker_profile,
            )
            selected_preparation = PreparationService(
                selected_database,
                workspaces=GitCloneAttemptWorkspace(),
            )
        if (
            selected_verifier is None
            and self.settings.verification_adapter == "contract-driven-repository"
        ):
            from spg.providers.contract_verifier import (
                ContractDrivenRepositoryVerifier,
            )

            selected_verifier = ContractDrivenRepositoryVerifier(selected_database)
        elif (
            selected_verifier is None
            and self.settings.verification_adapter == "mvp-e2e-markdown"
        ):
            from spg.providers.repository_markdown_verifier import (
                MvpE2eMarkdownVerifier,
            )

            selected_verifier = MvpE2eMarkdownVerifier(selected_database)

        options = {
            "workspace_root": workspace_root or self.settings.workspace_root,
            "executor": selected_executor,
            "verifier": selected_verifier,
            "planner": planner,
        }
        if selected_preparation is not None:
            options["preparation"] = selected_preparation
        if selected_binding is not None:
            options["executor_binding"] = selected_binding
        return WorkApplicationService(
            selected_database,
            **options,
        )

    def interaction(
        self,
        database: Database | None = None,
    ) -> WorkInteractionService:
        """Compose pre-Work interpretation without composing Work or production."""

        selected_database = database or self.persistence()
        return WorkInteractionService(
            selected_database,
            capability=self.interaction_capability(),
            runtime_mode=WicRuntimeMode(self.settings.wic_runtime_mode),
            fast_reception=(
                ShadowFastReceptionRuntime(
                    DeterministicFastReceptionCapability(),
                    timeout_seconds=self.settings.wic_fast_reception_timeout_seconds,
                )
                if self.settings.wic_fast_reception_shadow_enabled
                and self.settings.wic_runtime_mode != "LEGACY_WIC"
                else None
            ),
        )

    def interaction_capability(self) -> WorkInteractionCapability:
        """Compose the configured WIC provider without persistence or admission."""

        capability = UnavailableWorkInteractionCapability()
        semantic_adapter = (
            self.settings.wic_provider_adapter or self.settings.executor_adapter
        )
        conversation_adapter = (
            self.settings.conversation_provider_adapter or semantic_adapter
        )
        if semantic_adapter == "deepseek" and conversation_adapter == "deepseek":
            from spg.domain.model_runtime import (
                ModelProfile,
                ModelProvider,
                ModelProviderRegistry,
                ModelPurpose,
                PurposeProfileRouter,
                WattModelRuntime,
            )
            from spg.infrastructure.model_runtime import DeepSeekResponsesModelAdapter
            from spg.providers.deepseek_interaction import (
                DeepSeekWorkInteractionCapability,
            )

            credential = self.settings.deepseek_api_key
            registry = ModelProviderRegistry()
            registry.register(DeepSeekResponsesModelAdapter(
                api_key=lambda: (
                    "" if credential is None else credential.get_secret_value()
                ),
                base_url=self.settings.deepseek_base_url,
            ))
            timeout = self.settings.collaboration_provider_timeout_seconds
            runtime = WattModelRuntime(
                registry,
                PurposeProfileRouter(profiles={
                    ModelPurpose.WIC_FAST_RECEPTION: ModelProfile(
                        purpose=ModelPurpose.WIC_FAST_RECEPTION,
                        provider=ModelProvider.DEEPSEEK,
                        model="deepseek-flash",
                        reasoning_effort="low",
                        timeout_seconds=self.settings.wic_fast_reception_timeout_seconds,
                        max_output_tokens=self.settings.wic_fast_reception_max_output_tokens,
                    ),
                    ModelPurpose.WIC_SEMANTIC: ModelProfile(
                        purpose=ModelPurpose.WIC_SEMANTIC,
                        provider=ModelProvider.DEEPSEEK,
                        model=self.settings.wic_provider_model or "deepseek-flash",
                        reasoning_effort=self.settings.wic_provider_reasoning_effort,
                        timeout_seconds=timeout,
                        max_output_tokens=(
                            self.settings.collaboration_provider_max_output_tokens
                        ),
                    ),
                    ModelPurpose.CONVERSATION_RESPONSE: ModelProfile(
                        purpose=ModelPurpose.CONVERSATION_RESPONSE,
                        provider=ModelProvider.DEEPSEEK,
                        model=(
                            self.settings.conversation_provider_model
                            or self.settings.wic_provider_model
                            or "deepseek-flash"
                        ),
                        reasoning_effort=(
                            self.settings.conversation_provider_reasoning_effort
                        ),
                        timeout_seconds=timeout,
                        max_output_tokens=(
                            self.settings.collaboration_provider_max_output_tokens
                        ),
                    ),
                    ModelPurpose.EXECUTOR_PRODUCTION: ModelProfile(
                        purpose=ModelPurpose.EXECUTOR_PRODUCTION,
                        provider=ModelProvider(
                            self.settings.native_executor_inference_provider
                        ),
                        model=(
                            self.settings.native_executor_inference_model
                            or "unconfigured"
                        ),
                        reasoning_effort=(
                            self.settings.native_executor_inference_reasoning_effort
                        ),
                        timeout_seconds=self.settings.executor_timeout_seconds,
                    ),
                }),
            )
            capability = DeepSeekWorkInteractionCapability(
                runtime=runtime,
                coalesce_pre_work=self.settings.wic_coalesce_pre_work,
            )
        if semantic_adapter == "codex-sdk" and conversation_adapter == "codex-sdk":
            from spg.providers.codex_interaction import (
                CodexSdkWorkInteractionCapability,
            )

            capability = CodexSdkWorkInteractionCapability(
                repository_location=str(self.settings.repository_path),
                model=self.settings.wic_provider_model,
                conversation_model=(
                    self.settings.conversation_provider_model
                    or self.settings.wic_provider_model
                ),
                timeout_seconds=self.settings.collaboration_provider_timeout_seconds,
                reasoning_effort=self.settings.wic_provider_reasoning_effort,
                coalesce_pre_work=self.settings.wic_coalesce_pre_work,
                conversation_reasoning_effort=(
                    self.settings.conversation_provider_reasoning_effort
                ),
            )
        return capability

    def production_orchestrator(
        self,
        work_service: WorkApplicationService,
    ) -> ProductionOrchestrator:
        """Compose the bounded in-process MVP production driver."""

        return ProductionOrchestrator(
            work_service,
            max_automatic_transitions=(
                self.settings.orchestration_max_automatic_transitions
            ),
        )

    def steering(
        self,
        database: Database | None = None,
    ) -> SteeringApplicationService:
        """Compose persisted Steering truth without a reasoning provider or driver."""

        return SteeringApplicationService(database or self.persistence())

    def guided_design(
        self,
        database: Database | None = None,
    ) -> GuidedDesignApplicationService:
        """Compose reconstructable guided design process truth and projection."""

        return GuidedDesignApplicationService(database or self.persistence())

    def steering_plan_frames(
        self,
        database: Database | None = None,
    ) -> PlanFrameAssembler:
        """Compose provider-free authoritative Plan Frame assembly."""

        return PlanFrameAssembler(database or self.persistence())

    def steering_decisions(
        self,
        database: Database | None = None,
        *,
        capability: PlanSteeringCapability | None = None,
    ) -> SteeringDecisionApplicationService:
        """Compose decision-only Steering without a progression driver."""

        return SteeringDecisionApplicationService(
            database or self.persistence(),
            capability or DeterministicPlanSteeringCapability(),
        )

    def plan_steering_driver(
        self,
        database: Database,
        work_service: WorkApplicationService,
        production_orchestrator: ProductionOrchestrator,
        *,
        capability: PlanSteeringCapability | None = None,
        semantic_capability: SemanticStepCapability | None = None,
    ) -> PlanSteeringDriver:
        """Compose bounded Steering progression over existing governed seams."""

        selected_semantic = semantic_capability
        semantic_adapter = (
            self.settings.wic_provider_adapter or self.settings.executor_adapter
        )
        if selected_semantic is None and semantic_adapter == "codex-sdk":
            from spg.providers.codex_semantic import CodexSdkSemanticStepCapability

            selected_semantic = CodexSdkSemanticStepCapability(
                timeout_seconds=self.settings.executor_timeout_seconds,
            )
        elif selected_semantic is None and semantic_adapter == "deepseek":
            from spg.domain.model_runtime import (
                ModelProfile,
                ModelProvider,
                ModelProviderRegistry,
                ModelPurpose,
                PurposeProfileRouter,
                WattModelRuntime,
            )
            from spg.infrastructure.model_runtime import DeepSeekResponsesModelAdapter
            from spg.providers.deepseek_semantic import DeepSeekSemanticStepCapability

            credential = self.settings.deepseek_api_key
            registry = ModelProviderRegistry()
            registry.register(
                DeepSeekResponsesModelAdapter(
                    api_key=lambda: (
                        "" if credential is None else credential.get_secret_value()
                    ),
                    base_url=self.settings.deepseek_base_url,
                )
            )
            runtime = WattModelRuntime(
                registry,
                PurposeProfileRouter(
                    profiles={
                        ModelPurpose.STEERING_SEMANTIC: ModelProfile(
                            purpose=ModelPurpose.STEERING_SEMANTIC,
                            provider=ModelProvider.DEEPSEEK,
                            model=self.settings.wic_provider_model or "deepseek-flash",
                            reasoning_effort=self.settings.wic_provider_reasoning_effort,
                            timeout_seconds=(
                                self.settings.collaboration_provider_timeout_seconds
                            ),
                            max_output_tokens=(
                                self.settings.collaboration_provider_max_output_tokens
                            ),
                        )
                    }
                ),
            )
            selected_semantic = DeepSeekSemanticStepCapability(runtime)

        return PlanSteeringDriver(
            database,
            work_service,
            production_orchestrator,
            capability=capability,
            semantic_capability=selected_semantic,
        )

    def steering_bootstrap(
        self,
        database: Database | None = None,
        *,
        capability: InitialSteeringPlanFormationCapability | None = None,
    ) -> SteeringBootstrapService:
        """Compose initial long-lived Plan formation without production admission."""

        return SteeringBootstrapService(
            database or self.persistence(),
            capability=capability,
        )

    @staticmethod
    def work_post_admission(
        work_service: WorkApplicationService,
        steering_bootstrap: SteeringBootstrapService,
        steering_driver: PlanSteeringDriver,
        production_orchestrator: ProductionOrchestrator,
    ) -> WorkPostAdmissionService:
        """Compose the shared mode-aware post-admission lifecycle seam."""

        return WorkPostAdmissionService(
            work_service,
            steering_bootstrap,
            steering_driver,
            production_orchestrator,
        )

    def runtime_activation(
        self,
        database: Database | None = None,
    ) -> RuntimeActivationService:
        """Compose the read-only local Runtime activation projection."""

        return RuntimeActivationService(database or self.persistence(), self.settings)


def bootstrap(settings: Settings | None = None) -> Application:
    """Construct the application explicitly from typed settings."""

    return Application(settings=settings or Settings())
