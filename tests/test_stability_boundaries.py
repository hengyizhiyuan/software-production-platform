"""Generic failure-map invariants, independent of FSI names or target paths."""
from spg.domain.response_contract import preserve_explicit_production_outcome
from spg.domain.refinement_contract import test_execution_evidence as execution_evidence
from spg.application.bootstrap import bootstrap
from spg.config import Settings


def test_multiclause_explicit_change_survives_lossy_preview_summary():
    request = "Please fix the Cancel button. Show a preview; wait before delivery."
    outcome = preserve_explicit_production_outcome("Show a preview", request)
    assert request in outcome
    assert preserve_explicit_production_outcome(outcome, request) == outcome
    advisory = "How should I design a customer management system?"
    assert preserve_explicit_production_outcome("Discuss options", advisory) == "Discuss options"


def test_test_collection_cannot_claim_assertion_success():
    assert execution_evidence({"argv": ["python", "-m", "pytest", "--collect-only"],
        "returncode": 0})["diagnostic_code"] == "VERIFICATION_EVIDENCE_INCOMPLETE"
    assert execution_evidence({"argv": ["pytest"], "returncode": 2,
        "stderr": "ModuleNotFoundError: missing_optional"})["diagnostic_code"] == "TEST_ENVIRONMENT_NOT_READY"
    result = execution_evidence({"argv": ["node", "--test", "tests/test_dialog.cjs"], "returncode": 0})
    assert result["verification_evidence"] == "EXECUTED"


def test_runtime_defaults_and_qualification_mode_match():
    status = bootstrap(Settings()).status()
    assert status["wic_runtime_mode"] == status["qualified_wic_runtime_mode"]
    assert status["wic_configuration_parity"] == "PASS"


def test_explicit_git_source_survives_admission_for_existing_custom_host_recipe():
    from spg.domain.response_contract import production_intent_evidence
    source = 'http://qualified-git:8080/business.git'
    evidence = production_intent_evidence(f'这是项目仓库：{source}\n请修复取消按钮并给我预览。')
    assert evidence.repository_source == source
    assert evidence.production_request
