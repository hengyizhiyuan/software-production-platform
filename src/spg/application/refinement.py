"""Authority-safe boundary for repository-aware Change Proposal providers."""

from spg.domain.product import ProductInvariantViolation
from spg.domain.refinement import (
    RepositoryChangeProposal,
    RepositoryChangeProposalProvider,
    RepositoryChangeProposalRequest,
)


class RepositoryChangeProposalService:
    """Accept inspection output only when exact governed lineage is preserved."""

    def __init__(self, provider: RepositoryChangeProposalProvider) -> None:
        self.provider = provider

    def propose(
        self,
        request: RepositoryChangeProposalRequest,
    ) -> RepositoryChangeProposal:
        proposal = self.provider.propose(request)
        if (
            proposal.engineering_resource_id != request.engineering_resource_id
            or proposal.repository_identity != request.repository_identity
        ):
            raise ProductInvariantViolation(
                "Change Proposal Provider changed the Engineering Resource boundary"
            )
        if (
            proposal.source_baseline_id != request.source_baseline_id
            or proposal.source_ref != request.source_ref
            or proposal.source_revision != request.source_revision
        ):
            raise ProductInvariantViolation(
                "Change Proposal Provider changed the exact Source Baseline"
            )
        return proposal
