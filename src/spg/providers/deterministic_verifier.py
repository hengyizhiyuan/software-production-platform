"""Deterministic FVS Verification Provider using the provider-neutral seam."""

from collections.abc import Mapping

from spg.domain.verification import (
    VerificationCapabilityRequest,
    VerificationCapabilityResult,
    VerificationEvidence,
    VerificationProviderBinding,
    VerificationResultValue,
)


class DeterministicVerificationProvider:
    """Return configured exact-obligation results without external Assurance calls."""

    def __init__(
        self,
        outcomes: Mapping[str, VerificationResultValue],
        *,
        provider_identity: str = "provider:deterministic-verification",
        provider_version: str = "v1",
    ) -> None:
        self._outcomes = dict(outcomes)
        self._binding = VerificationProviderBinding(
            provider_identity=provider_identity,
            provider_version=provider_version,
        )

    @property
    def binding(self) -> VerificationProviderBinding:
        return self._binding

    def verify(
        self,
        request: VerificationCapabilityRequest,
    ) -> VerificationCapabilityResult:
        result = self._outcomes.get(
            request.obligation,
            VerificationResultValue.UNKNOWN,
        )
        return VerificationCapabilityResult(
            result=result,
            evidence=VerificationEvidence(
                obligation=request.obligation,
                subject_commit_identity=request.proposed_commit_identity,
                subject_tree_identity=request.tree_identity,
                expected="verification obligation returns PASS",
                observed=result.value,
                metadata={"mode": "deterministic", "score": None},
            ),
        )
