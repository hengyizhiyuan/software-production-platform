"""Provider-neutral rendering of admitted production instructions."""

from spg.domain.preparation import PreparedExecutionRequest
from spg.domain.runtime import CompletionContract
from spg.domain.engineering_semantics import semantic_fact_statement


def render_governed_instruction(
    objective: str,
    completion_contract: CompletionContract,
    *,
    execution: PreparedExecutionRequest | None = None,
    repository_ref: str | None = None,
    sandbox_policy: str | None = None,
    max_internal_turns: int = 1,
    time_budget_seconds: float | None = None,
) -> str:
    """Render only approved Runtime facts into the Provider instruction."""

    outputs = "\n".join(f"- {item}" for item in completion_contract.required_outputs)
    changes = "\n".join(f"- {item}" for item in completion_contract.required_changes)
    artifact = completion_contract.artifact_contract
    change_contract = completion_contract.change_contract
    plan = completion_contract.production_plan
    plan_section = ""
    if plan is not None:
        steps = "\n".join(
            f"{step.position}. {step.instruction}" for step in plan.ordered_steps
        )
        plan_constraints = "\n".join(
            f"- {item}" for item in plan.inherited_constraints
        )
        plan_section = (
            f"Desired outcome:\n{plan.desired_outcome}\n\n"
            f"Admitted Production Plan objective:\n{plan.objective}\n\n"
            "Ordered Plan steps:\n"
            "Non-authoritative strategy hints; Executor owns HOW.\n"
            f"{steps}\n\n"
            "Inherited constraints:\n"
            f"{plan_constraints or '- None beyond the admitted contract.'}\n\n"
            f"Verification approach:\n{plan.verification_approach}\n\n"
        )
    markers = "\n".join(f"- {item}" for item in completion_contract.required_markers)
    forbidden_changes = "\n".join(
        f"- {item}" for item in completion_contract.forbidden_changes
    )
    blocking_conditions = "\n".join(
        f"- {item}" for item in completion_contract.blocking_conditions
    )
    generic_verifications = "\n".join(
        f"- {item}" for item in completion_contract.verification_obligations
    )
    semantic_obligations = "\n".join(
        f"- [{item.fact_id}] {semantic_fact_statement(item)}"
        for item in completion_contract.semantic_fact_obligations
    )
    task_contract = completion_contract.task_contract
    task_contract_section = ""
    if task_contract is not None:
        task_scope = "\n".join(f"- {item}" for item in task_contract.scope)
        task_acceptance = "\n".join(
            f"- {item}" for item in task_contract.acceptance_meaning
        )
        task_evidence = "\n".join(
            f"- [{item.category.value}] {item.statement}"
            for item in task_contract.evidence_requirements
        )
        task_out_of_scope = "\n".join(
            f"- {item}" for item in task_contract.out_of_scope
        )
        task_prerequisites = "\n".join(
            f"- {item}" for item in task_contract.required_prerequisites
        ) or "- None"
        prerequisite_evidence = "\n".join(
            f"- {item}" for item in task_contract.prerequisite_evidence
        ) or "- None"
        task_capabilities = "\n".join(
            f"- {item}" for item in task_contract.required_capabilities
        ) or "- None"
        task_contract_section = (
            "Task Contract projection:\n"
            f"- Identity: {task_contract.task_contract_id}\n"
            f"- Engineering activity: {task_contract.activity.value}\n"
            f"- Task mode: {task_contract.task_mode.value}\n"
            f"- Objective: {task_contract.objective}\n"
            f"- SOP lineage: {task_contract.sop_reference or 'None'}\n"
            f"Scope:\n{task_scope}\n"
            f"Acceptance meaning:\n{task_acceptance}\n"
            f"Required evidence direction:\n{task_evidence}\n"
            f"Required execution prerequisites:\n{task_prerequisites}\n"
            f"Required executable capabilities:\n{task_capabilities}\n"
            f"Persisted prerequisite evidence:\n{prerequisite_evidence}\n"
            f"Out of scope:\n{task_out_of_scope}\n"
            "This projection preserves already admitted intent and lineage. It does "
            "not widen execution authority; the target contracts below remain decisive.\n\n"
        )
    authority = (
        completion_contract.change_contract
        or completion_contract.artifact_contract
        or completion_contract.production_plan
    )
    governed_basis = ""
    if authority is not None:
        governed_basis = (
            "Governed Resource / Source Basis:\n"
            f"- Engineering Resource: {authority.engineering_resource_id}\n"
            f"- Repository identity: {authority.repository_identity}\n"
            f"- Repository ref: {repository_ref or 'not separately projected'}\n"
            f"- Source Baseline: {authority.source_baseline_id}\n"
            f"- Source revision: {authority.source_revision}\n"
        )
        if execution is not None:
            governed_basis += (
                f"- PWU: {execution.work_unit_id}\n"
                f"- Attempt: {execution.attempt_id}\n"
                f"- Generation: {execution.generation}\n"
                f"- Workspace: {execution.workspace.workspace_identity}\n"
            )
        governed_basis += "\n"
    execution_policy = (
        "Bounded Executor policy:\n"
        f"- Sandbox: {sandbox_policy or 'admitted by the Executor binding'}\n"
        f"- Maximum internal Provider Turns: {max_internal_turns}\n"
        f"- Total Provider time budget seconds: "
        f"{time_budget_seconds if time_budget_seconds is not None else 'binding-defined'}\n"
        "- Before every continuation, the PWU, Attempt, generation, Workspace, "
        "Source Basis, Authority, Completion Contract, and remaining budget must "
        "still be valid.\n"
        "- Stop and return BOUNDARY_CROSSING_REQUIRED before widening Scope, "
        "changing Resource/repository, entering a forbidden area, changing the "
        "Completion Contract, or making a Human-owned decision.\n"
        "- Stop on budget exhaustion or lost execution continuity. Never rebase, "
        "commit, push, or change a Git ref.\n\n"
        "At the end of each internal Provider Turn, return the supplied structured "
        "control claim. Use CONTINUE only when another bounded diagnose, repair, or "
        "validation Turn is necessary. Use RESULT_READY only when the best candidate "
        "is ready for independent SPG observation and Verification.\n\n"
    )
    artifact_authority = ""
    if artifact is not None:
        constraints = "\n".join(f"- {item}" for item in artifact.constraints)
        artifact_authority = (
            "Artifact Target:\n"
            f"- Path: {artifact.artifact_path}\n"
            f"- Operation: {artifact.operation.value}\n"
            f"- Desired outcome: {artifact.expected_outcome}\n"
            "- Document format verification: write UTF-8 text with no trailing spaces/tabs "
            "and no extra blank line at EOF. Markdown two-space hard breaks also fail "
            "the existing git diff --check requirement. Inspect newly created/untracked "
            "files explicitly: plain git diff --check does not cover untracked files.\n"
            f"- Constraints:\n{constraints or '- None beyond the admitted contract.'}\n\n"
        )
    change_authority = ""
    if change_contract is not None:
        exact_targets = "\n".join(
            f"- {target.operation.value} {target.path}"
            for target in change_contract.exact_targets
        )
        allowed_areas = "\n".join(
            f"- {area}" for area in change_contract.allowed_areas
        )
        forbidden_areas = "\n".join(
            f"- {area}" for area in change_contract.forbidden_areas
        )
        verifications = "\n".join(
            f"- {item.identity}" for item in change_contract.verification_obligations
        )
        constraints = "\n".join(
            f"- {item}" for item in change_contract.constraints
        )
        change_authority = (
            "Code Change Contract:\n"
            f"- Target shape: {change_contract.target_shape.value}\n"
            f"- Desired outcome: {change_contract.desired_outcome}\n"
            f"Exact targets:\n{exact_targets or '- None.'}\n"
            f"Bounded allowed areas:\n{allowed_areas or '- None.'}\n"
            f"Forbidden paths/areas:\n{forbidden_areas or '- None beyond the admitted boundary.'}\n"
            f"Constraints:\n{constraints or '- None beyond the admitted contract.'}\n"
            f"Required Verification:\n{verifications}\n\n"
        )
    return (
        "Complete exactly the admitted software-production objective below.\n\n"
        f"Objective:\n{objective.strip()}\n\n"
        f"{governed_basis}"
        f"{task_contract_section}"
        f"{plan_section}"
        f"{artifact_authority}"
        f"{change_authority}"
        f"Authorized output paths:\n{outputs}\n\n"
        f"Authorized changed paths:\n{changes}\n\n"
        f"Required markers:\n{markers or '- None.'}\n\n"
        f"Forbidden changes:\n{forbidden_changes or '- None beyond the admitted target/scope contracts.'}\n\n"
        f"Blocking conditions:\n{blocking_conditions or '- None.'}\n\n"
        f"Verification obligations:\n{generic_verifications or '- None beyond the admitted target/change contracts.'}\n\n"
        "Governed Engineering Semantic Facts (Product semantics; do not reinterpret "
        "their source text or reduce them to a particular implementation shape):\n"
        f"{semantic_obligations or '- None structured for this Work.'}\n\n"
        f"{execution_policy}"
        "Do not modify any other repository path outside the exact targets or "
        "bounded areas admitted above. Never widen the Change Contract yourself. "
        "Work only inside the supplied "
        "Attempt workspace. Do not commit, push, or change a Git ref. Internal "
        "tests are advisory; only SPG independent "
        "Verification can establish trusted satisfaction."
    )
