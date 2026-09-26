"""Generic failure-map invariants, independent of FSI names or target paths."""
import pytest
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


@pytest.mark.parametrize('human_input', [
    '把页面上的旧标签改为新标签。其他行为不变。',
    '请启动这个项目让我查看实际效果。',
    '我想要一个收集联系信息的页面。',
    '我想让网站支持反馈。',
    '我希望应用具备现有数据的搜索能力。',
])
def test_explicit_change_and_outcome_grammar_does_not_depend_on_one_case(human_input):
    from spg.domain.response_contract import production_intent_evidence
    assert production_intent_evidence(human_input).production_request


@pytest.mark.parametrize('human_input', [
    '如何启动这个项目？', '我想知道反馈页面为什么这样设计。',
    '搜索 GitHub 和 Web 中成熟的实现，给出真实来源。',
])
def test_knowledge_and_retrieval_do_not_gain_production_authority(human_input):
    from spg.domain.response_contract import production_intent_evidence
    assert not production_intent_evidence(human_input).production_request


def test_explicit_new_root_web_and_schema_files_are_not_lost():
    from spg.application.work import WorkApplicationService
    assert WorkApplicationService._explicit_repository_paths(
        'Create contact.html with contact.js and schema.sql; keep the other files unchanged.'
    ) == ('contact.html', 'contact.js', 'schema.sql')


def test_repository_url_with_port_never_becomes_a_write_target():
    from spg.application.work import WorkApplicationService
    assert WorkApplicationService._explicit_repository_paths(
        'Use http://source-host:8080/project.git\nCreate contact.html.'
    ) == ('contact.html',)
