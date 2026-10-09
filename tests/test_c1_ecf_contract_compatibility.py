"""Real Owner API compatibility at the Watt gateway, not nominal 0.1 mocks."""
from dataclasses import replace
from pathlib import Path
import os
import subprocess
import sys
from types import ModuleType

import pytest

from spg.application.decision_context import (
    DecisionContextOwnerIncompatible,
    WattDecisionContextGateway,
)
from tests.test_managed_greenfield_context import owner_basis, package


CURRENT_MAIN = "c6b568d006022e39b95daebedfecfb55e562ebe5"


def current_main_owner(monkeypatch):
    """Load actual current-main Owner bytes through the actual import boundary.

    Archive qualification can provide C1_ECF_CURRENT_MAIN_SOURCE (its src dir).
    Local qualification reads the same exact Git object in the Owner repository.
    Neither path changes the selected compatible Owner checkout or its source.
    """
    selected = WattDecisionContextGateway._ecf()
    archived_src = os.environ.get("C1_ECF_CURRENT_MAIN_SOURCE")
    if archived_src:
        path = Path(archived_src) / "ecf" / "decision_context.py"
        source = path.read_bytes()
    else:
        repository = Path(selected.__file__).resolve().parents[2]
        result = subprocess.run(
            ["git", "-C", str(repository), "show",
             f"{CURRENT_MAIN}:src/ecf/decision_context.py"],
            capture_output=True, check=True,
        )
        source = result.stdout
        path = repository / CURRENT_MAIN / "src/ecf/decision_context.py"
    module = ModuleType("ecf.decision_context")
    module.__file__ = str(path)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(source, str(path), "exec"), module.__dict__)
    monkeypatch.setattr(sys.modules["ecf"], "decision_context", module)
    return module


def test_selected_owner_managed_request_calls_registered_applicability_contract(tmp_path):
    basis = owner_basis()
    gateway, request, source = package(tmp_path, basis)
    context = gateway.require_ready(
        request, managed_context=source,
        work_statement=basis["revision"].desired_outcome, work_revision="r1",
    )
    assert context.contract.contract_id == "MANAGED_GREENFIELD_PRODUCTION"
    assert {item.value for item in context.contract.required} == {
        "PRODUCT_INTENT", "REPOSITORY_REALITY", "WORK_REALITY",
    }
    assert context.context_status.value == "READY"
    assert gateway._ecf().DecisionType.MANAGED_GREENFIELD_PRODUCTION.value == (
        context.request.decision_type.value
    )


def test_actual_current_main_same_version_rejects_managed_api_explicitly(tmp_path, monkeypatch):
    basis = owner_basis()
    gateway, request, source = package(tmp_path, basis)
    actual = current_main_owner(monkeypatch)
    assert actual.VERSION == "0.1"
    assert not hasattr(actual.DecisionType, "MANAGED_GREENFIELD_PRODUCTION")
    assert "required_context_classes" not in actual.DecisionContextRequest.__dataclass_fields__
    with pytest.raises(DecisionContextOwnerIncompatible) as rejected:
        gateway.assemble(request, managed_context=source,
                         work_statement="Create the admitted artifact", work_revision="r1")
    assert "ECF_MANAGED_CONTRACT_INCOMPATIBLE" in str(rejected.value)
    assert "DecisionType.MANAGED_GREENFIELD_PRODUCTION" in str(rejected.value)
    assert "DecisionContextRequest.required_context_classes" in str(rejected.value)


def test_actual_current_main_retains_its_existing_repository_contract(tmp_path, monkeypatch):
    basis = owner_basis()
    gateway, request, _source = package(tmp_path, basis)
    current_main_owner(monkeypatch)
    context = gateway.assemble(request, work_statement="Change existing source", work_revision="r1")
    assert context.contract.contract_id == "PRODUCT_UI_CHANGE"
    assert context.context_status.value == "INCOMPLETE"
    assert {item.value for item in context.missing_required_classes} == {
        "PRODUCT_INTENT", "PRODUCT_INVARIANT", "APPROVED_DECISION",
    }


@pytest.mark.parametrize("removed", ("REPOSITORY_REALITY", "APPROVED_CONSTRAINT"))
def test_managed_registration_cannot_drop_base_or_required_applicability(tmp_path, monkeypatch, removed):
    basis = owner_basis()
    basis["revision"].constraints = ("Keep the admitted scope unchanged",)
    gateway, request, source = package(tmp_path, basis)
    assert "APPROVED_CONSTRAINT" in source.required_classes
    ecf = gateway._ecf()
    real_contract_for = ecf.contract_for

    def weakened_contract(actual_request):
        registered = real_contract_for(actual_request)
        return replace(registered, required=tuple(
            item for item in registered.required if item.value != removed
        ))

    monkeypatch.setattr(ecf, "contract_for", weakened_contract)
    with pytest.raises(DecisionContextOwnerIncompatible,
                       match="base/applicability contract"):
        gateway.assemble(request, managed_context=source,
                         work_statement="Produce admitted content", work_revision="r1")