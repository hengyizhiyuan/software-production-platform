"""Execution context factoring must be reversible, not evidence deletion."""
from copy import deepcopy
import json
from uuid import uuid4

import pytest

from spg.domain.native_execution import canonical_digest
from spg.executor.context import NativeContextAssembler, NativeContextCapacityError
from spg.executor.context_evidence import NativeContractExecutionView, NativeContextEvidenceError
from tests.test_native_executor_contracts import _binding, _plan


def _proof_contract():
    binding, contract = _binding()
    rows = [{
        "schema": "formation-owner-receipt-v1", "receipt_id": str(uuid4()),
        "owner": "fulfillment-formation", "stage": "CANDIDATE",
        "work_id": str(binding.work_id), "work_reality_revision_id": str(uuid4()),
        "inventory_fingerprint": "b" * 64, "source_revision": "c" * 40,
        "candidate_is_authority": False, "candidate_output": "historic" * 40000,
    }]
    retained = {
        "task_contract": {"scope": ["CREATE:src/new.html"], "forbidden": ["deploy"]},
        "semantic_fact_obligations": [{"relation": "BOUND", "value": ["F01", "F02"],
                                        "scope": {"exclusive": True}, "qualifiers": ["ordered"]}],
        "fulfillment_bindings": [{"source_ref": "fact:required", "phase": "CURRENT",
                                 "evidence_method": "ARTIFACT_CONTENT", "formation_receipt": {
                                     "receipt_refs": ["work-plan-receipt:" + rows[0]["receipt_id"]],
                                     "semantic_review": {"accepted": True, "receipt_id": str(uuid4())},
                                     "candidate_attempts": deepcopy(rows)}}],
        "production_plan": {"fulfillment_formation_receipts": deepcopy(rows),
                            "future_human_gate": {"status": "PENDING"}},
    }
    payload = {"objective": contract.objective, "completion_contract": retained}
    contract = contract.model_copy(update={"contract_payload": payload,
                                           "contract_digest": canonical_digest(payload)})
    binding = binding.model_copy(update={"pwu_contract_digest": contract.contract_digest})
    return binding, contract


def _restore(view):
    payload = deepcopy(view.payload)
    for ref in view.references:
        for pointer in ref["original_locations"]:
            parts = pointer.strip("/").split("/")
            parent = payload
            for part in parts[:-1]:
                parent = parent[int(part)] if isinstance(parent, list) else parent[part]
            parent[int(parts[-1])] = view.resolve(ref["reference"])
    return payload


def test_history_is_losslessly_factored_and_original_contract_never_mutates():
    binding, contract = _proof_contract()
    original = deepcopy(contract.contract_payload)
    view = NativeContractExecutionView(binding, contract)
    assert len(view.references) == 1
    assert len(view.references[0]["original_locations"]) == 2
    assert _restore(view) == original == contract.contract_payload
    assert canonical_digest(_restore(view)) == contract.contract_digest
    assert view.payload["completion_contract"]["task_contract"] == original["completion_contract"]["task_contract"]
    assert view.payload["completion_contract"]["semantic_fact_obligations"] == original["completion_contract"]["semantic_fact_obligations"]
    assert view.payload["completion_contract"]["production_plan"]["future_human_gate"]["status"] == "PENDING"
    assert view.payload["completion_contract"]["fulfillment_bindings"][0]["formation_receipt"]["semantic_review"] == original["completion_contract"]["fulfillment_bindings"][0]["formation_receipt"]["semantic_review"]


def test_exact_history_reference_resolves_to_copy_without_new_permission():
    binding, contract = _proof_contract()
    view = NativeContractExecutionView(binding, contract)
    ref = view.references[0]["reference"]
    row = view.resolve(ref)
    assert canonical_digest(row) == view.references[0]["content_digest"]
    row["owner"] = "spoofed"
    assert view.resolve(ref)["owner"] != "spoofed"
    assert "capability_grants" not in view.contract_fact()
    assert binding.capability_grants == _binding()[0].capability_grants


@pytest.mark.parametrize("kind", ["version", "pwu", "digest", "payload"])
def test_contract_or_binding_drift_cannot_form_view(kind):
    binding, contract = _proof_contract()
    if kind == "version":
        binding = binding.model_copy(update={"pwu_contract_version_id": uuid4()})
    elif kind == "pwu":
        binding = binding.model_copy(update={"pwu_id": uuid4()})
    elif kind == "digest":
        binding = binding.model_copy(update={"pwu_contract_digest": "0" * 64})
    else:
        contract = contract.model_copy(update={"contract_payload": {"objective": "changed"}})
    with pytest.raises(NativeContextEvidenceError, match="BINDING_INVALID"):
        NativeContractExecutionView(binding, contract)


@pytest.mark.parametrize("reference", ["native-contract:foreign:evidence:abc", "../private", "native-contract:{id}:evidence:" + "0" * 64])
def test_foreign_missing_or_arbitrary_evidence_reads_rejected(reference):
    binding, contract = _proof_contract()
    view = NativeContractExecutionView(binding, contract)
    with pytest.raises(NativeContextEvidenceError):
        view.resolve(reference.format(id=contract.id))


@pytest.mark.parametrize("field,value", [("work_id", "foreign"), ("owner", ""),
                                          ("candidate_is_authority", True)])
def test_invalid_owner_record_cannot_be_hidden_by_reference(field, value):
    binding, contract = _proof_contract()
    payload = deepcopy(contract.contract_payload)
    payload["completion_contract"]["production_plan"]["fulfillment_formation_receipts"][0][field] = value
    digest = canonical_digest(payload)
    contract = contract.model_copy(update={"contract_payload": payload, "contract_digest": digest})
    binding = binding.model_copy(update={"pwu_contract_digest": digest})
    with pytest.raises(NativeContextEvidenceError, match="OWNER_BINDING_INVALID"):
        NativeContractExecutionView(binding, contract)


def test_same_owner_receipt_id_with_conflicting_content_rejected():
    binding, contract = _proof_contract()
    payload = deepcopy(contract.contract_payload)
    payload["completion_contract"]["production_plan"]["fulfillment_formation_receipts"][0]["stage"] = "OTHER"
    digest = canonical_digest(payload)
    contract = contract.model_copy(update={"contract_payload": payload, "contract_digest": digest})
    binding = binding.model_copy(update={"pwu_contract_digest": digest})
    with pytest.raises(NativeContextEvidenceError, match="IDENTITY_DRIFT"):
        NativeContractExecutionView(binding, contract)


def test_duplicate_history_fits_unchanged_budget_but_large_current_requirement_still_blocks():
    binding, contract = _proof_contract()
    assert len(json.dumps(contract.contract_payload).encode()) > 512 * 1024
    assembler = NativeContextAssembler()
    request = assembler.assemble(binding=binding, contract=contract, working_plan=_plan(),
                                 step_sequence=1, available_tools=())
    assert assembler.max_request_bytes == 512 * 1024
    assert assembler._size(request) < 15000
    assert request.context_facts[0]["contract_digest"] == contract.contract_digest
    payload = deepcopy(contract.contract_payload)
    payload["completion_contract"]["task_contract"]["required_content"] = "x" * 600000
    digest = canonical_digest(payload)
    contract = contract.model_copy(update={"contract_payload": payload, "contract_digest": digest})
    binding = binding.model_copy(update={"pwu_contract_digest": digest})
    with pytest.raises(NativeContextCapacityError):
        assembler.assemble(binding=binding, contract=contract, working_plan=_plan(),
                           step_sequence=1, available_tools=())


def test_legacy_contract_without_history_retains_exact_representation():
    binding, contract = _binding()
    fact = NativeContractExecutionView(binding, contract).contract_fact()
    assert fact["payload"] == contract.contract_payload
    assert "payload_representation" not in fact
