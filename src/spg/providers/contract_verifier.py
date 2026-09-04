"""Select the contract-specific repository verifier without hidden targets."""

from spg.domain.verification import (
    VerificationCapabilityRequest,
    VerificationCapabilityResult,
    VerificationProviderBinding,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.providers.repository_code_verifier import RepositoryCodeVerifier
from spg.providers.repository_markdown_verifier import RepositoryArtifactVerifier


class ContractDrivenRepositoryVerifier:
    """Route one exact obligation from the admitted PWU contract type."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.code = RepositoryCodeVerifier(database)
        self.documentation = RepositoryArtifactVerifier(database)
        self._binding = VerificationProviderBinding(
            provider_identity="provider:contract-driven-repository",
            provider_version="v1",
        )

    @property
    def binding(self) -> VerificationProviderBinding:
        return self._binding

    def verify(
        self,
        request: VerificationCapabilityRequest,
    ) -> VerificationCapabilityResult:
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            proposed = store.proposed_snapshot(request.snapshot_id)
            work_unit = (
                None if proposed is None else store.work_unit(proposed.work_unit_id)
            )
        if work_unit is None:
            return self.code.verify(request)
        if work_unit.completion_contract.change_contract is not None:
            return self.code.verify(request)
        return self.documentation.verify(request)
