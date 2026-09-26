"""Turn-scoped external evidence acquisition contracts, not Engineering Truth."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SearchIntent(StrEnum):
    SEARCH_GITHUB_REPOSITORIES = "SEARCH_GITHUB_REPOSITORIES"
    SEARCH_GITHUB_CODE = "SEARCH_GITHUB_CODE"
    SEARCH_GITHUB_ISSUES = "SEARCH_GITHUB_ISSUES"
    FETCH_GITHUB_RESOURCE = "FETCH_GITHUB_RESOURCE"
    SEARCH_WEB = "SEARCH_WEB"
    FETCH_WEB_RESOURCE = "FETCH_WEB_RESOURCE"
    INSPECT_SEARCH_RESULT = "INSPECT_SEARCH_RESULT"


CAPABILITY_FOR_INTENT = {
    SearchIntent.SEARCH_GITHUB_REPOSITORIES: "github.repository.search",
    SearchIntent.SEARCH_GITHUB_CODE: "github.code.search",
    SearchIntent.SEARCH_GITHUB_ISSUES: "github.issue.search",
    SearchIntent.FETCH_GITHUB_RESOURCE: "github.resource.fetch",
    SearchIntent.SEARCH_WEB: "web.search",
    SearchIntent.FETCH_WEB_RESOURCE: "web.resource.fetch",
    SearchIntent.INSPECT_SEARCH_RESULT: "web.resource.fetch",
}


class SearchFailure(StrEnum):
    NO_RESULTS = "NO_RESULTS"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    CREDENTIAL_REQUIRED = "CREDENTIAL_REQUIRED"
    RATE_LIMITED = "RATE_LIMITED"
    FETCH_FAILED = "FETCH_FAILED"
    UNSUPPORTED_SEARCH_TYPE = "UNSUPPORTED_SEARCH_TYPE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class SearchProviderError(RuntimeError):
    def __init__(self, category: SearchFailure, message: str) -> None:
        super().__init__(message)
        self.category = category


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    intent: SearchIntent
    query: str = Field(min_length=2, max_length=240)
    reason: str = Field(min_length=1, max_length=500)
    origin: str = Field(pattern="^(HUMAN_EXPLICIT|MODEL_INFORMATION_GAP)$")

    @property
    def capability_id(self) -> str:
        if self.intent is SearchIntent.INSPECT_SEARCH_RESULT:
            return ("github.resource.fetch" if urlsplit(self.query).hostname == "github.com"
                    else "web.resource.fetch")
        return CAPABILITY_FOR_INTENT[self.intent]


class SearchEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=1)
    source_type: str = Field(pattern="^(GITHUB|WEB)$")
    provider: str = Field(min_length=1)
    query: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    retrieved_at: datetime
    rank: int = Field(ge=1)
    snippet: str = ""
    inspected_content: str | None = None
    metadata: dict[str, str | int | None] = Field(default_factory=dict)
    completeness: str = Field(pattern="^(SEARCH_RESULT|INSPECTED)$")

    @model_validator(mode="after")
    def public_source(self):
        parts = urlsplit(self.url)
        if parts.scheme != "https" or not parts.hostname:
            raise ValueError("external Evidence requires an HTTPS source URL")
        if self.completeness == "INSPECTED" and not self.inspected_content:
            raise ValueError("inspected Evidence requires fetched content")
        return self


class SearchBudget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_queries: int = Field(default=4, ge=1, le=12)
    max_fetches: int = Field(default=3, ge=1, le=12)
    max_seconds: float = Field(default=75, gt=0, le=120)
    max_evidence_characters: int = Field(default=18000, ge=1000, le=100000)
    max_model_tokens: int = Field(default=7000, ge=100, le=20000)


class SearchMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    search_types: tuple[str, ...]
    providers: tuple[str, ...]
    query_count: int = 0
    result_count: int = 0
    fetch_count: int = 0
    refinement_count: int = 0
    latency_ms: int = 0
    model_tokens: int | None = None
    provider_cost: str = "UNREPORTED"
    sufficient: bool = False
    failure_categories: tuple[str, ...] = ()
