"""Narrow deterministic Production Planner Lite provider."""

import json
from pathlib import PurePosixPath

from uuid import NAMESPACE_URL, uuid5

from spg.domain.planning import (
    OnePwuFitClassification,
    ProductionNodeKind,
    ProductionPlanGraph,
    ProductionPlanNode,
    ProductionPlanProposal,
    ProductionPlanStep,
    ProductionPlanningRequest,
)


class RuleBasedProductionPlanner:
    """Form bounded PWU plans without model calls or independent authority."""

    _MULTI_PWU_MARKERS = (
        "independently governed sequential",
        "separate governed production units",
        "multiple executable pwus",
        "successor baseline",
        "independent baseline progression",
        "多个独立 pwu",
        "多 pwu",
        "逐个基线推进",
    )

    def propose(self, request: ProductionPlanningRequest) -> ProductionPlanProposal:
        normalized = " ".join(request.admitted_requirement.casefold().split())
        graph = self._decompose(request) if not request.refinement_reasons else None
        targets = (
            tuple(item.path for item in request.artifact_targets)
            if request.artifact_targets else
            tuple(item.path for item in request.change_contract.exact_targets)
            if request.change_contract is not None else
            tuple(item.path for item in request.change_proposal.required_targets)
            if request.change_proposal is not None else ()
        )
        oversized = bool(request.target_effort_seconds) and (
            any(node.kind is ProductionNodeKind.PWU
                and node.estimated_duration_seconds > request.max_pwu_duration_seconds
                for node in graph.nodes) if graph is not None else
            sum(request.target_effort_seconds.get(path, 900) for path in targets)
            > request.max_pwu_duration_seconds
        )
        if oversized:
            graph = None
            fit = OnePwuFitClassification.NEEDS_REFINEMENT
            unresolved = ("Estimated PWU effort exceeds its execution envelope without a safe semantic split.",)
        elif graph is not None:
            fit = OnePwuFitClassification.MULTI_PWU_FIT
            unresolved = ()
        elif any(marker in normalized for marker in self._MULTI_PWU_MARKERS):
            fit = OnePwuFitClassification.MULTI_PWU_REQUIRED
            unresolved = (
                "Provide exact change surfaces before independently governed PWUs can be planned.",
            )
        elif request.refinement_reasons:
            fit = OnePwuFitClassification.NEEDS_REFINEMENT
            unresolved = request.refinement_reasons
        else:
            fit = OnePwuFitClassification.ONE_PWU_FIT
            unresolved = ()

        instructions = self._steps(request, fit)
        identity = "|".join(
            (
                str(request.work_id),
                request.source_revision,
                request.production_objective,
                fit.value,
                *(target.path for target in request.artifact_targets),
                json.dumps(
                    None
                    if request.change_proposal is None
                    else request.change_proposal.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                json.dumps(
                    None
                    if request.change_contract is None
                    else request.change_contract.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                *instructions,
            )
        )
        return ProductionPlanProposal(
            proposal_id=uuid5(NAMESPACE_URL, f"spg:production-plan:{identity}"),
            target_kind=request.target_kind,
            objective=request.production_objective,
            desired_outcome=request.desired_outcome,
            ordered_steps=tuple(
                ProductionPlanStep(position=index, instruction=instruction)
                for index, instruction in enumerate(instructions, start=1)
            ),
            graph=graph,
            artifact_targets=request.artifact_targets,
            change_proposal=request.change_proposal,
            change_contract=request.change_contract,
            inherited_constraints=request.constraints,
            verification_approach=request.verification_expectation,
            assumptions=(
                "The admitted Work can be executed through one governed PWU and Attempt lineage.",
            ) if fit is OnePwuFitClassification.ONE_PWU_FIT else (),
            unresolved_questions=unresolved,
            fit_classification=fit,
            engineering_resource_id=request.engineering_resource_id,
            repository_identity=request.repository_identity,
            source_baseline_id=request.source_baseline_id,
            source_revision=request.source_revision,
        )

    @staticmethod
    def _steps(
        request: ProductionPlanningRequest,
        fit: OnePwuFitClassification,
    ) -> tuple[str, ...]:
        if fit not in {
            OnePwuFitClassification.ONE_PWU_FIT,
            OnePwuFitClassification.MULTI_PWU_FIT,
        }:
            return ("Resolve the listed planning blocker before production admission.",)

        steps: list[str] = [
            "Inspect the admitted Source of Truth and existing repository conventions.",
        ]
        for target in request.artifact_targets:
            action = target.operation.value.lower()
            steps.append(
                f"{action.capitalize()} the exact authorized artifact {target.path}."
            )
        if request.change_proposal is not None:
            required = ", ".join(
                target.path for target in request.change_proposal.required_targets
            )
            if required:
                steps.append(f"Prepare the Human-proposed code targets: {required}.")
            if request.change_proposal.allowed_areas:
                areas = ", ".join(request.change_proposal.allowed_areas)
                steps.append(f"Keep any Human-admitted code changes inside: {areas}.")
        if request.change_contract is not None:
            if request.change_contract.exact_targets:
                paths = ", ".join(
                    target.path for target in request.change_contract.exact_targets
                )
                steps.append(f"Modify only the admitted exact code targets: {paths}.")
            if request.change_contract.allowed_areas:
                areas = ", ".join(request.change_contract.allowed_areas)
                steps.append(f"Keep all other code changes inside: {areas}.")
        steps.append("Run the admitted targeted verification and report the resulting evidence.")
        return tuple(dict.fromkeys(steps))

    @staticmethod
    def _decompose(request: ProductionPlanningRequest) -> ProductionPlanGraph | None:
        """Split admitted, exact, naturally separate change surfaces only."""

        targets = (
            tuple(target.path for target in request.artifact_targets)
            if request.artifact_targets else
            tuple(target.path for target in request.change_contract.exact_targets)
            if request.change_contract is not None else
            tuple(target.path for target in request.change_proposal.required_targets)
            if request.change_proposal is not None else ()
        )
        if len(targets) < 2:
            return None
        production_paths = tuple(path for path in targets if not path.startswith("tests/"))
        def family(path: str) -> str:
            pure = PurePosixPath(path)
            stem = pure.stem.removeprefix("test_").removesuffix("_test").removesuffix(".test")
            if pure.suffix == ".html" and stem == "index":
                scripts = tuple(source for source in production_paths if (
                    PurePosixPath(source).parent == pure.parent
                    and PurePosixPath(source).suffix in {".js", ".cjs", ".mjs"}
                ))
                if len(scripts) == 1:
                    return PurePosixPath(scripts[0]).stem
            if path.startswith("tests/"):
                source_stems = {
                    PurePosixPath(source).stem: source for source in production_paths
                }
                if stem not in source_stems:
                    language = "python" if pure.suffix == ".py" else "javascript" if pure.suffix in {".js", ".cjs", ".mjs"} else None
                    compatible = tuple(source for source in production_paths if (
                        (language == "python" and PurePosixPath(source).suffix == ".py")
                        or (language == "javascript" and PurePosixPath(source).suffix in {".js", ".cjs", ".mjs"})
                    ))
                    if len(compatible) == 1:
                        return PurePosixPath(compatible[0]).stem
            return pure.parent.name if stem in {"__init__", "index"} else stem

        grouped: dict[str, list[str]] = {}
        for path in targets:
            grouped.setdefault(family(path), []).append(path)
        if len(grouped) < 2:
            # Source, tests, and documentation for one capability are one
            # coherent production unit, even when they live in different roots.
            return None
        normalized = request.admitted_requirement.casefold()
        coupled = any(token in normalized for token in (
            "shared", "migration", "schema", "interface", "contract", "coupled",
            "共享", "迁移", "接口", "联动", "统一",
        ))
        parallel = not coupled
        groups = tuple(grouped)
        nodes: list[ProductionPlanNode] = [
            ProductionPlanNode(
                node_id=f"group:{group}", kind=ProductionNodeKind.GROUP,
                objective=f"Produce the {group} change surface",
            ) for group in groups
        ]
        prior: str | None = None
        for index, group in enumerate(groups, start=1):
            node_id = f"pwu:{index}"
            paths = tuple(grouped[group])
            context = tuple(ref for ref in request.context_references if (
                family(ref) == group or ref.lower() == "readme.md"
            ))
            nodes.append(ProductionPlanNode(
                node_id=node_id, kind=ProductionNodeKind.PWU,
                objective=f"Produce and verify the {group} capability change",
                parent_id=f"group:{group}",
                dependency_ids=() if parallel or prior is None else (prior,),
                writable_paths=paths,
                context_references=context,
                required_capabilities=("repository.read", "repository.write", "verification.run"),
                authority_scope=tuple(f"WRITE:{path}" for path in paths),
                responsibility_boundary=f"Only the {group} capability and its scoped verification",
                acceptance_criteria=(f"The admitted {group} capability is independently verified",),
                verification_requirements=(request.verification_expectation,),
                estimated_duration_seconds=sum(request.target_effort_seconds.get(path, 900) for path in paths),
                compute_budget_seconds=request.max_pwu_duration_seconds,
            ))
            prior = node_id
        if parallel:
            nodes.append(ProductionPlanNode(
                node_id="pwu:join", kind=ProductionNodeKind.JOIN,
                objective="Reconcile and verify the independently produced branch baselines",
                dependency_ids=tuple(f"pwu:{index}" for index in range(1, len(groups) + 1)),
                writable_paths=targets,
                context_references=tuple(dict.fromkeys(request.context_references)),
                required_capabilities=("repository.read", "repository.write", "verification.run"),
                authority_scope=tuple(f"WRITE:{path}" for path in targets),
                responsibility_boundary="Integrate only verified parent outputs within the admitted Work scope",
                acceptance_criteria=("Integrated tree passes the admitted verification",),
                verification_requirements=(request.verification_expectation,),
                estimated_duration_seconds=min(900, request.max_pwu_duration_seconds),
                compute_budget_seconds=request.max_pwu_duration_seconds,
            ))
        return ProductionPlanGraph(
            nodes=tuple(nodes),
            planning_rationale=(
                "Exact disjoint change surfaces may run in isolation and require an explicit Join."
                if parallel else
                "Coupled change surfaces share an area and advance the baseline serially."
            ),
        )
