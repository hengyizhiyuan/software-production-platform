"""Deterministic qualification before a decision becomes Human Attention."""
from spg.domain.steering import (HumanDecisionNeed, HumanDecisionEffect,
    SteeringInvariantViolation)
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.interaction_store import InteractionStore


def canonical_ir_for_work(session, work_id):
    product = ProductStore(session)
    revision = product.current_work_reality_revision(work_id)
    seen = set()
    while revision is not None and revision.id not in seen:
        seen.add(revision.id)
        assessment = (InteractionStore(session).assessment(revision.source_assessment_id)
                      if revision.source_assessment_id else None)
        if assessment is not None and assessment.semantic_ir is not None:
            return assessment.semantic_ir
        revision = product.work_reality_revision(revision.previous_revision_id) if revision.previous_revision_id else None
    return None


def qualify_human_decision(need: HumanDecisionNeed | None, *, evidence,
                           semantic_ir=None, owner_boundary: str | None = None) -> tuple[str, ...]:
    if need is None:
        return ("DECISION_OBJECT_MISSING",)
    failures = []
    for field, minimum in (("decision_subject",5),("question",8),("why_human_owns_it",10),
                           ("why_now",10),("material_effect",10),("blocking_reason",10)):
        value=getattr(need,field)
        if len(value.strip()) < minimum or not any(ch.isalnum() for ch in value):
            failures.append("DECISION_OBJECT_INCOMPLETE")
    if need.safe_default_possible:
        failures.append("SAFE_AUTONOMOUS_CONTINUATION")
    if not need.required_now:
        failures.append("NOT_REQUIRED_NOW")
    available = set(evidence)
    if not set(need.evidence) <= available or any(
            not set(option.evidence) <= available for option in need.supported_options):
        failures.append("OPTIONS_NOT_GROUNDED")
    if len({option.label.strip().casefold() for option in need.supported_options}) < 2:
        failures.append("NO_DISTINCT_OPTIONS")
    forbidden = ("material risk or cost", "resolve the material semantic", "select the bounded direction",
                 "MATERIAL_RISK_OR_COST_DECISION", "Choose how to handle", "Establish the Motive")
    if any(token.casefold() in need.question.casefold() or token.casefold() in need.decision_subject.casefold()
           for token in forbidden):
        failures.append("GENERIC_TEMPLATE")
    explicit = bool(semantic_ir is not None
        and need.governed_semantic_ir_id == semantic_ir.id
        and (any(q.question == need.question and q.requires_human and q.blocks_current_step and not q.safe_reversible_assumption
                for q in semantic_ir.questions) or any(d.required_before_production
                    and d.subject == need.decision_subject
                    and tuple(o.value for o in d.options) == tuple(o.label for o in need.supported_options)
                    for d in semantic_ir.human_decisions)))
    owned_boundary = (owner_boundary == "EXACT_CANDIDATE_REVIEW" and need.effect is HumanDecisionEffect.ACCEPTANCE
        or owner_boundary == "EXACT_PROPOSAL_REVIEW" and need.effect is HumanDecisionEffect.AUTHORITY
        or owner_boundary == "SCOPE_EXPANSION" and need.effect is HumanDecisionEffect.AUTHORITY
        or owner_boundary == "CONVERGENCE_BUDGET_EXHAUSTED" and need.effect is HumanDecisionEffect.COST_OR_RISK)
    if not (explicit or owned_boundary):
        failures.append("HUMAN_OWNERSHIP_NOT_ESTABLISHED")
    return tuple(failures)


def require_human_decision(need, **basis):
    failures = qualify_human_decision(need, **basis)
    if failures:
        raise SteeringInvariantViolation("ATTENTION_NOT_QUALIFIED: " + ", ".join(failures))


def owner_decision_boundary(session, work_id, step_id, reason, *, database=None):
    """Owner evidence, never a provider's claim of materiality."""
    from spg.infrastructure.persistence.steering_store import SteeringStore
    from spg.infrastructure.executor_runtime.postgres_store import NativeExecutionStore
    from spg.domain.steering import SteeringAttentionReason
    product = ProductStore(session)
    binding = product.runtime_binding(work_id)
    summary = None if binding is None else product.runtime_summary(binding)
    if reason is SteeringAttentionReason.PRODUCT_ACCEPTANCE_REQUIRED and summary is not None and summary.candidate_id:
        return "EXACT_CANDIDATE_REVIEW"
    result = SteeringStore(session).latest_semantic_result_for_step(step_id)
    if (reason is SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED and result is not None
            and result.completion_satisfied and result.proposed_production is not None):
        return "EXACT_PROPOSAL_REVIEW"
    history = NativeExecutionStore(session).work_convergence_history(work_id)
    if reason is SteeringAttentionReason.MATERIAL_RISK_OR_COST_DECISION and history and history[-1].condition in {"NON_CONVERGING", "ESCALATED"}:
        if database is not None and binding is None:
            from spg.application.steering_production import SteeringProductionService
            from spg.domain.product import ProductInvariantViolation
            try:
                context = SteeringProductionService(database).context_readiness(work_id)
            except (ProductInvariantViolation, SteeringInvariantViolation):
                context = None
            if context and context.get('owner') == 'ECF' and context['status'] == 'NOT_READY':
                # A missing software prerequisite is not evidence that the Human
                # must pause or redefine their intent. Preserve the budget halt;
                # the safe default is to stay stopped and expose the actual cause.
                return None
        return "CONVERGENCE_BUDGET_EXHAUSTED"
    return None


def boundary_decision(subject, question, effect, refs, options, *, why_now, impact):
    from spg.domain.steering import HumanDecisionOption
    return HumanDecisionNeed(decision_subject=subject, question=question,
        why_human_owns_it="Only Human may change the admitted boundary or accept the exact result.",
        why_now=why_now, material_effect=impact, effect=effect,
        supported_options=tuple(HumanDecisionOption(label=label, consequence=consequence, evidence=refs)
                                for label, consequence in options),
        evidence=refs, safe_default_possible=False, required_now=True,
        blocking_reason="Continuing would cross the exact Human-owned authority boundary.")


def attention_from_semantic_decisions(ir, *, product_id, product_name):
    """A pre-production reserved choice is not an authorization or a fabricated Work."""
    if ir is None:return []
    from uuid import uuid5
    from spg.domain.steering import RealityReference,RealityReferenceKind,HumanDecisionOption
    refs=(RealityReference(kind=RealityReferenceKind.SEMANTIC_IR,identity=ir.id),)
    items=[]
    for index,decision in enumerate(ir.human_decisions):
        if not decision.required_before_production:continue
        need=HumanDecisionNeed(decision_subject=decision.subject,question=decision.question,
            why_human_owns_it="Human 明确保留最终选择权：" + decision.authority_provenance.source_text,
            why_now=decision.why_now,material_effect='；'.join(decision.material_effects),
            effect=decision.effect,supported_options=tuple(HumanDecisionOption(label=o.value,
                consequence=effect,evidence=refs) for o,effect in zip(decision.options,decision.material_effects)),
            evidence=refs,safe_default_possible=False,blocking_reason=decision.why_now,
            required_now=True,governed_semantic_ir_id=ir.id)
        if qualify_human_decision(need,evidence=refs,semantic_ir=ir):continue
        items.append({'id':str(uuid5(ir.id,f'human-decision:{index}')),'work_id':None,
            'product_id':str(product_id),'product_name':product_name,'work_title':decision.subject,
            'kind':'IRK_DECISION_REQUIRED','decision':decision.subject,'reason':decision.why_now,
            'human_decision_need':need.model_dump(mode='json'),'actions':[],
            'conversation_prompt':decision.question,'governed_subject_ref':f'semantic-ir:{ir.id}',
            'interaction_id':str(ir.interaction_id)})
    return items
