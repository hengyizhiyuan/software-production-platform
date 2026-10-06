"""Fixed, reviewable recipes over existing Watt capabilities. No caller-supplied command."""
from dataclasses import dataclass
from functools import lru_cache
from spg.evaluation.contracts import CaseDefinition, Cohort, Stage


@dataclass(frozen=True)
class Recipe:
    key: str
    title: str
    stage: Stage
    selector: str
    invariant: str
    regression: bool = False
    provenance: str = "repository:canonical-production-tests"


CATALOG = (
    Recipe("greenfield-source", "新建项目不误要求已有仓库", Stage.IRK,
        "tests/test_intent_realization_kernel.py::test_greenfield_incident_has_work_obligation_without_repository_action",
        "Greenfield intent owes WORK_ADMITTED and does not invent repository acquisition", True,
        "docs/architecture/intent-realization-kernel/external-qualification.md"),
    Recipe("empty-pwu", "多目标规划拒绝空生产单元", Stage.PLANNING,
        "tests/test_multi_pwu_admission.py::test_invalid_dual_target_node_cannot_materialize_pwu",
        "An empty governed production obligation never reaches execution", True,
        "docs/evidence/systemic-reality-census-20261005.json"),
    Recipe("simple-work", "简单 Work 形成可验证的软件成果", Stage.EXECUTION,
        "tests/integration/test_software_delivery.py::test_work_without_user_repository_uses_managed_workspace_and_delivers",
        "Governed Work, managed workspace, exact Candidate and explicit delivery authority remain connected"),
    Recipe("brownfield", "已有项目保留精确基线", Stage.ACCEPTANCE_PROMOTION,
        "tests/integration/test_product_managed_source_gitea.py::test_brownfield_import_acceptance_next_work_and_provider_fail_closed",
        "Only explicit acceptance advances Product source and next Work inherits the exact revision"),
    Recipe("search", "搜索与读取保留独立来源", Stage.SEARCH,
        "tests/integration/test_external_search_interaction.py::test_combined_github_web_search_merges_real_provider_shapes_without_duplicate_claims",
        "Governed Search and Fetch persist source evidence without becoming project acquisition"),
    Recipe("multi-roots-join", "独立生产单元经验证后汇合", Stage.PWU,
        "tests/integration/test_multi_pwu_runtime.py::test_real_parallel_branch_outputs_join_only_after_verification",
        "Independent roots qualify before explicit JOIN and final Candidate keeps all lineage"),
    Recipe("dependency-chain", "后续单元消费精确前序结果", Stage.PWU,
        "tests/integration/test_multi_pwu_runtime.py::test_three_serial_pwus_inherit_exact_verified_predecessor_baselines",
        "A dependent PWU cannot execute early or consume stale/unqualified source", True),
    Recipe("join-conflict", "汇合冲突不可静默消失", Stage.PWU,
        "tests/integration/test_multi_pwu_runtime.py::test_join_conflict_requires_changed_verified_resolution_tree",
        "Conflicting outputs require a changed independently verified reconciliation tree"),
    Recipe("capacity-wait", "有限容量等待不伪报运行", Stage.EXECUTION,
        "tests/integration/test_native_executor_runtime.py::test_queue_without_live_compatible_worker_becomes_truthful_and_recovers",
        "WAITING has no active Worker claim and becomes runnable only with compatible capacity"),
    Recipe("workspace-continuity", "新 Work 保留原待决事项", Stage.WIC,
        "tests/integration/test_workspace_independent_work.py",
        "Independent typed intent changes focus while prior Work and accepted Product observations remain exact", True),
    Recipe("verification-negative", "失败验证阻止交付", Stage.VERIFICATION,
        "tests/integration/test_software_delivery.py::test_failing_behavior_test_cannot_publish_software",
        "A negative business oracle cannot be replaced by success wording"),
    Recipe("guardian-acceptance", "默认保证门禁先于人工验收", Stage.GUARDIAN,
        "tests/integration/test_software_delivery.py::test_required_guardian_static_review_precedes_explicit_acceptance",
        "Exact default Guardian assurance gates preview/acceptance and does not auto-authorize the Candidate", True,
        "docs/evidence/p0-p1-system-closure-20261006.json"),
    Recipe("promotion-recovery", "基线晋升中断可幂等恢复", Stage.ACCEPTANCE_PROMOTION,
        "tests/integration/test_product_managed_source_gitea.py::test_durable_promotion_replays_exact_authorized_decision_after_interruption",
        "Durable explicit Acceptance survives BEFORE_GIT, AFTER_GIT and BEFORE_SQL_COMMIT without duplicate promotion", True,
        "docs/evidence/p0-p1-system-closure-20261006.json"),
    Recipe("worker-recovery", "Worker 崩溃后不丢失或重复执行", Stage.EXECUTION,
        "tests/integration/test_native_executor_runtime.py::test_cloud_worker_crash_requeues_same_execution_after_lease_expiry",
        "Expired leases fence the old Worker and preserve the exact Execution identity"),
    Recipe("ecf-context", "任务保留受治理的决策上下文", Stage.ECF,
        "tests/integration/test_decision_context_work_admission.py",
        "Task admission retains exact ECF fingerprint and protected obligations"),
)


@lru_cache
def recipes():
    extra = (Recipe("sealed-live-intent", "新生成语义 Holdout", Stage.IRK,
        "tests/integration/test_quality_live_holdout.py::test_sealed_unseen_intent_uses_real_compiler_and_irk",
        "An unseen greenfield software intent remains governed production without an invented existing repository"),
        Recipe("unqualified-scenario", "待配方资格的场景", Stage.WIC, "", "Unqualified scenario cannot claim PASS"))
    return {r.key: r for r in (*CATALOG, *extra)}


def definitions():
    from spg.evaluation.release_gate import CORPUS
    out = []
    for r in CATALOG:
        legacy = [c for c in CORPUS if c.selector == r.selector]
        aliases = tuple(c.identity for c in legacy)
        refs = (r.provenance, r.selector) + tuple("release-corpus:" + c.identity for c in legacy)
        out.append(CaseDefinition(key="watt." + r.key, title=r.title,
            source="HISTORICAL_INCIDENT" if r.regression else "GOLDEN_CORPUS",
            motive=r.title, invariants=(r.invariant,), provenance=refs,
            context={"execution_environment": "ISOLATED_QUALIFICATION", "legacy_aliases": list(aliases)},
            runner_key=r.key, stage=r.stage,
            cohorts=(Cohort.GOLDEN, Cohort.REGRESSION) if r.regression else (Cohort.GOLDEN,), aliases=aliases))
    return tuple(out)


def import_core(service):
    versions = [service.register_case(d) for d in definitions()]
    return service.register_campaign("core-production-v1", "Core Production Qualification",
        [v["id"] for v in versions])


def create_fresh_holdout(service):
    """Generate after a Watt revision is pinned. Private inputs never enter optimization APIs."""
    import secrets
    nonce = secrets.token_hex(6)
    company = "云杉" + str(secrets.randbelow(900000) + 100000)
    r = recipes()["sealed-live-intent"]
    definition = CaseDefinition(key="holdout." + nonce, title=r.title, source="FRESH_HOLDOUT",
        motive="SEALED", invariants=(r.invariant,), context={"execution_environment": "ISOLATED_QUALIFICATION"},
        provenance=("quality:generated-after-version-pin:" + str(service.settings.runtime_revision),),
        runner_key=r.key, stage=r.stage, cohorts=(Cohort.FRESH_HOLDOUT,),
        private_material={"human_text": f"我想从零为{company}公司制作一个企业官网首页。没有现有代码项目，本次只完成静态首页。",
            "expected": {"current_production": True, "repository_required": False, "repository_reference": None}})
    version = service.register_case(definition)
    campaign = service.register_campaign("fresh-holdout-" + nonce, "Fresh Holdout",
        [version["id"]])
    return {"case_id": version["case_id"], "campaign": campaign, "sealed": True}
