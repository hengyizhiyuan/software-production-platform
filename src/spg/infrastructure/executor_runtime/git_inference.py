"""Deterministic Native Executor reasoning for an admitted exact Git obligation."""

from __future__ import annotations

from spg.domain.native_execution import (
    InferenceAction,
    InferenceRequest,
    InferenceResponse,
    ToolCallProposal,
    WorkingPlan,
)


class GovernedGitOperationInferenceAdapter:
    """Execute the Task Contract's exact Git action; accept only its settled receipt."""

    def __init__(self, *, operation: str, arguments: dict[str, object], expected_revision: str) -> None:
        if operation != "branch.create":
            raise ValueError("deterministic Git adapter currently admits branch.create only")
        branch = arguments.get("branch")
        if not isinstance(branch, str) or not branch:
            raise ValueError("branch operation must bind an exact requested branch")
        self.operation = operation
        self.arguments = {"operation": operation, "branch": branch}
        self.expected_revision = expected_revision

    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        plan = WorkingPlan(
            version=request.working_plan.version + 1,
            objective_reference=request.working_plan.objective_reference,
            chosen_approach="Use the admitted Git connector and verify observed branch Reality.",
            approach_rationale="The Human-approved Task Contract binds one exact branch mutation.",
        )
        if not request.previous_results:
            return InferenceResponse(
                action=InferenceAction.CONTINUE,
                summary="Create the exact Human-admitted Work branch.",
                working_plan=plan,
                tool_calls=(ToolCallProposal(
                    proposal_index=0,
                    tool_identity="git.operation",
                    arguments=self.arguments,
                ),),
                residual_obligations=("Observe exact branch and revision",),
            )
        receipt = request.previous_results[-1]
        output = receipt.get("output") or {}
        if (
            receipt.get("tool_identity") == "git.operation"
            and receipt.get("condition") == "SETTLED"
            and output.get("operation") == self.operation
            and output.get("resulting_branch") == self.arguments["branch"]
            and output.get("resulting_revision") == self.expected_revision
        ):
            return InferenceResponse(
                action=InferenceAction.RESULT_READY,
                summary="The Work branch and exact commit were observed after execution.",
                working_plan=plan,
                result_claim={
                    "operation": self.operation,
                    "branch": output["resulting_branch"],
                    "revision": output["resulting_revision"],
                    "tool_output_digest": receipt.get("output_digest"),
                },
            )
        return InferenceResponse(
            action=InferenceAction.UNABLE_TO_COMPLETE,
            summary="The Git operation did not establish the admitted branch Reality.",
            working_plan=plan,
            residual_obligations=("Inspect Git operation failure evidence",),
        )
