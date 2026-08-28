"""Provider-neutral Verification / Assurance capability boundary."""

from typing import Protocol

from spg.domain.verification import (
    VerificationCapabilityRequest,
    VerificationCapabilityResult,
    VerificationProviderBinding,
)


class VerificationCapabilityContract(Protocol):
    """Replaceable capability; SPG owns orchestration, not assurance truth."""

    @property
    def binding(self) -> VerificationProviderBinding: ...

    def verify(
        self,
        request: VerificationCapabilityRequest,
    ) -> VerificationCapabilityResult: ...
