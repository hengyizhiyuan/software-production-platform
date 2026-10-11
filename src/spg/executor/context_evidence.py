"""Lossless execution views of immutable contracts, with scoped evidence reads.

Only typed Formation audit history is factored out. Accepted requirements,
bindings, current verification and authority remain in the execution view.
The original PWU contract remains the evidence consumed by governance Owners.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from spg.domain.native_execution import (
    ExecutionBindingV2, PWUContractVersionRecord, canonical_digest,
)


class NativeContextEvidenceError(RuntimeError):
    """A derived execution view cannot prove its immutable evidence binding."""


class NativeContractExecutionView:
    """Derive and resolve evidence references inside one admitted PWU snapshot.

    References are content addressed and contract scoped, never filesystem
    paths or model supplied lookup expressions. Reads return a copy of the
    original record; they do not confer effect permissions or Assurance.
    """

    def __init__(self, binding: ExecutionBindingV2, contract: PWUContractVersionRecord):
        if (binding.pwu_id != contract.pwu_id
                or binding.pwu_contract_version_id != contract.id
                or binding.pwu_contract_digest != contract.contract_digest
                or canonical_digest(contract.contract_payload) != contract.contract_digest):
            raise NativeContextEvidenceError("NATIVE_CONTEXT_CONTRACT_BINDING_INVALID")
        self.binding = binding
        self.contract = contract
        self.payload = deepcopy(contract.contract_payload)
        self._records: dict[str, dict[str, Any]] = {}
        self._locations: dict[str, list[str]] = {}
        self._receipt_digests: dict[str, str] = {}
        self.references: list[dict[str, Any]] = []
        completion = self.payload.get("completion_contract")
        if not isinstance(completion, dict):
            return
        paths = []
        plan = completion.get("production_plan")
        if isinstance(plan, dict) and "fulfillment_formation_receipts" in plan:
            paths.append((plan, "fulfillment_formation_receipts",
                          "/completion_contract/production_plan/fulfillment_formation_receipts"))
        bindings = completion.get("fulfillment_bindings", [])
        if isinstance(bindings, list):
            for index, item in enumerate(bindings):
                receipt = item.get("formation_receipt") if isinstance(item, dict) else None
                if isinstance(receipt, dict) and "candidate_attempts" in receipt:
                    paths.append((receipt, "candidate_attempts",
                                  f"/completion_contract/fulfillment_bindings/{index}/formation_receipt/candidate_attempts"))
        for parent, key, pointer in paths:
            rows = parent[key]
            if not isinstance(rows, list):
                raise NativeContextEvidenceError("NATIVE_CONTEXT_HISTORY_CONTRACT_INVALID")
            parent[key] = [self._reference(row, f"{pointer}/{index}")
                           for index, row in enumerate(rows)]
        self.references = [
            {**self._reference_metadata(digest), "original_locations": locations}
            for digest, locations in self._locations.items()
        ]

    def _reference(self, row: Any, pointer: str) -> dict[str, Any]:
        # This is an audit record contract, not a semantic field-name whitelist.
        # Unknown/non-Owner history cannot disappear into an opaque reference.
        if (not isinstance(row, dict) or not row.get("receipt_id")
                or not row.get("owner") or not row.get("schema")
                or not row.get("stage") or not row.get("inventory_fingerprint")
                or row.get("work_id") != str(self.binding.work_id)
                or row.get("candidate_is_authority") is not False):
            raise NativeContextEvidenceError("NATIVE_CONTEXT_HISTORY_OWNER_BINDING_INVALID")
        digest = canonical_digest(row)
        prior = self._receipt_digests.setdefault(row["receipt_id"], digest)
        if prior != digest:
            raise NativeContextEvidenceError("NATIVE_CONTEXT_RECEIPT_IDENTITY_DRIFT")
        self._records[digest] = deepcopy(row)
        self._locations.setdefault(digest, []).append(pointer)
        return {"historical_owner_evidence": self._reference_metadata(digest)}

    def _reference_metadata(self, digest: str) -> dict[str, Any]:
        row = self._records[digest]
        return {
            "reference": f"native-contract:{self.contract.id}:evidence:{digest}",
            "content_digest": digest,
            "receipt_reference": f"work-plan-receipt:{row['receipt_id']}",
            "owner": row["owner"], "stage": row["stage"],
            "inventory_fingerprint": row["inventory_fingerprint"],
            "work_reality_revision_id": row.get("work_reality_revision_id"),
            "source_revision": row.get("source_revision"),
        }

    def resolve(self, reference: str) -> dict[str, Any]:
        prefix = f"native-contract:{self.contract.id}:evidence:"
        if not reference.startswith(prefix):
            raise NativeContextEvidenceError("NATIVE_CONTEXT_EVIDENCE_SCOPE_MISMATCH")
        digest = reference[len(prefix):]
        row = self._records.get(digest)
        if row is None or canonical_digest(row) != digest:
            raise NativeContextEvidenceError("NATIVE_CONTEXT_EVIDENCE_NOT_FOUND")
        return deepcopy(row)

    def contract_fact(self) -> dict[str, Any]:
        fact = {
            "fact_type": "PWU_CONTRACT",
            "contract_version_id": str(self.contract.id),
            "contract_digest": self.contract.contract_digest,
            "payload": self.payload,
        }
        if self.references:
            fact.update({
                "payload_representation": "LOSSLESS_EXECUTION_VIEW",
                "execution_view_digest": canonical_digest(self.payload),
                "historical_evidence_references": self.references,
                "evidence_read_endpoint": (
                    f"/api/works/{self.binding.work_id}/native-context/"
                    f"{self.binding.attempt_id}/evidence/{{content_digest}}"
                ),
                "rule": (
                    "The immutable contract_digest identifies the complete original contract. "
                    "Only historical Formation audit records are represented by exact references. "
                    "All current requirements and gates remain in payload. Historical evidence "
                    "is available through the scoped Owner read endpoint; a reference is not "
                    "proof of fulfillment, authority or permission. Governance Owners consume "
                    "the complete original contract, not this derived execution view."
                ),
            })
        return fact
