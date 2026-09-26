"""Provider-neutral model identities shared below Watt role-specific ports."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable, Protocol


class ModelPurpose(StrEnum):
    WIC_FAST_RECEPTION = "WIC_FAST_RECEPTION"
    WIC_SEMANTIC = "WIC_SEMANTIC"
    CONVERSATION_RESPONSE = "CONVERSATION_RESPONSE"
    EXTERNAL_RESEARCH = "EXTERNAL_RESEARCH"
    STEERING_SEMANTIC = "STEERING_SEMANTIC"
    EXECUTOR_PRODUCTION = "EXECUTOR_PRODUCTION"


class ModelProvider(StrEnum):
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    QWEN = "qwen"
    KIMI = "kimi"
    ANTHROPIC = "anthropic"


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    structured_json_schema: bool
    streaming: bool
    usage: bool
    cached_usage: bool = False
    reasoning_usage: bool = False


@dataclass(frozen=True, slots=True)
class ModelProfile:
    purpose: ModelPurpose
    provider: ModelProvider
    model: str
    reasoning_effort: str | None
    timeout_seconds: float
    max_output_tokens: int | None = None

    @property
    def identity(self) -> str:
        return (
            f"{self.purpose.value}:{self.provider.value}:{self.model}:"
            f"{self.reasoning_effort or 'none'}"
        )

    def transport_compatible_with(self, other: "ModelProfile") -> bool:
        return (
            self.provider is other.provider
            and self.model == other.model
            and self.reasoning_effort == other.reasoning_effort
        )


@dataclass(frozen=True, slots=True)
class ModelUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_tokens: int | None = None
    unknown: bool = False


@dataclass(frozen=True, slots=True)
class ModelTiming:
    request_sent_seconds: float | None = None
    first_response_event_seconds: float | None = None
    first_token_seconds: float | None = None
    completed_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class StructuredModelResult:
    output_text: str
    provider: ModelProvider
    requested_model: str
    effective_model: str | None
    request_id: str | None
    usage: ModelUsage
    timing: ModelTiming
    retry_count: int = 0


ModelDeltaCallback = Callable[[str], None]
ModelStageCallback = Callable[[str], None]


class StructuredModelAdapter(Protocol):
    provider: ModelProvider
    capabilities: ModelCapabilities

    def generate(
        self,
        *,
        profile: ModelProfile,
        instructions: str,
        input_text: str,
        output_schema: dict[str, object],
        on_output_delta: ModelDeltaCallback | None = None,
        on_stage: ModelStageCallback | None = None,
    ) -> StructuredModelResult: ...


@dataclass(slots=True)
class ModelProviderRegistry:
    """Small explicit registry; it is not a dynamic model-selection policy."""

    _adapters: dict[ModelProvider, StructuredModelAdapter] = field(
        default_factory=dict
    )

    def register(self, adapter: StructuredModelAdapter) -> None:
        if adapter.provider in self._adapters:
            raise ValueError(f"Provider already registered: {adapter.provider.value}")
        self._adapters[adapter.provider] = adapter

    def adapter(self, provider: ModelProvider) -> StructuredModelAdapter:
        try:
            return self._adapters[provider]
        except KeyError as error:
            raise ValueError(f"Provider is not registered: {provider.value}") from error

    def close(self) -> None:
        for adapter in self._adapters.values():
            close = getattr(adapter, "close", None)
            if callable(close):
                close()


@dataclass(frozen=True, slots=True)
class PurposeProfileRouter:
    """Resolve one exact configured profile per role without dynamic fallback."""

    profiles: dict[ModelPurpose, ModelProfile]

    def resolve(self, purpose: ModelPurpose) -> ModelProfile:
        try:
            return self.profiles[purpose]
        except KeyError as error:
            raise ValueError(f"Model purpose is not configured: {purpose.value}") from error


class WattModelRuntime:
    """Shared low-level runtime beneath independent WIC/Executor contracts."""

    def __init__(
        self,
        registry: ModelProviderRegistry,
        router: PurposeProfileRouter,
    ) -> None:
        self.registry = registry
        self.router = router

    def profile(self, purpose: ModelPurpose) -> ModelProfile:
        return self.router.resolve(purpose)

    def generate(
        self,
        *,
        purpose: ModelPurpose,
        instructions: str,
        input_text: str,
        output_schema: dict[str, object],
        on_output_delta: ModelDeltaCallback | None = None,
        on_stage: ModelStageCallback | None = None,
    ) -> StructuredModelResult:
        profile = self.profile(purpose)
        adapter = self.registry.adapter(profile.provider)
        return adapter.generate(
            profile=profile,
            instructions=instructions,
            input_text=input_text,
            output_schema=output_schema,
            on_output_delta=on_output_delta,
            on_stage=on_stage,
        )

    def close(self) -> None:
        self.registry.close()
