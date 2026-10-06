"""Read-only ECF source adapter for the first governed Managed Product production.

No context truth is stored here. IRK/Work/Governance records remain the owners.
A context role is typed by IRK; this adapter never classifies Human prose.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID
from spg.domain.intent_realization import GovernedSemanticIR, SemanticKind
from spg.domain.semantic_provenance import SemanticOrigin
from spg.application.decision_context import DecisionContextAuthorityMissing


@dataclass(frozen=True)
class ManagedGreenfieldContext:
    product_id: UUID
    work_id: UUID
    source_revision: str
    provenance: str
    intent: str
    invariants: tuple[tuple[str, str], ...] = ()
    decisions: tuple[tuple[str, str], ...] = ()
    constraints: tuple[str, ...] = ()
    required_classes: tuple[str, ...] = ()

    @property
    def applicability(self):
        present={'PRODUCT_INTENT':bool(self.intent),'PRODUCT_INVARIANT':bool(self.invariants),
                 'APPROVED_DECISION':bool(self.decisions),'APPROVED_CONSTRAINT':bool(self.constraints)}
        return {key:('REQUIRED_AND_PRESENT' if value and key in self.required_classes else
                     'REQUIRED_AND_MISSING' if key in self.required_classes else
                     'PRESENT_AND_APPLICABLE' if value else 'NOT_YET_ESTABLISHED_BUT_NON_BLOCKING')
                for key,value in present.items()}


def project_greenfield_context(*, product_id, work, revision, ir, governance, semantic_history=()):
    """Project only a source-owned admitted revision, never compiler candidates."""
    if (revision is None or ir is None or not isinstance(ir,GovernedSemanticIR)
            or revision.work_id!=work.id or governance is None
            or str(governance['id'])!=str(revision.governance_record_id)
            or not governance['authority_identity']
            or str(governance['subject_identity'])!=str(work.id)
            or str(governance['scope'].get('work_reality_revision_id'))!=str(revision.id)):
        raise DecisionContextAuthorityMissing('MANAGED_GREENFIELD_CONTEXT_OWNER_BASIS_MISSING')
    history=tuple(dict((value.id,value) for value in (ir,*semantic_history)).values())
    goals=next((value.current_production for value in history if value.current_production),())
    initial_greenfield=any(g.current and g.new_work and not g.repository_required and g.repository_reference is None
                          for value in history for g in value.current_production)
    if not goals or not initial_greenfield or any(g.repository_required or g.repository_reference is not None for g in goals):
        return None
    intent=json.dumps({'desired_outcome':revision.desired_outcome,
                      'governed_production_intents':[g.model_dump(mode='json') for g in goals]},ensure_ascii=False,sort_keys=True)
    required={'PRODUCT_INTENT'};invariants=[];decisions=[]
    superseded={ref for value in history for item in value.items for ref in item.supersedes}
    for meaning in history:
        for item in meaning.items:
            if f'{meaning.id}:{item.item_id}' in superseded:continue
            if item.subject not in {'product_invariant','approved_product_decision'}:continue
            cls='PRODUCT_INVARIANT' if item.subject=='product_invariant' else 'APPROVED_DECISION'
            required.add(cls)
            # Only actual Human declarations, not inferred guidance or questions.
            expected=SemanticKind.CONSTRAINT if cls=='PRODUCT_INVARIANT' else SemanticKind.FACT
            human=tuple(p for p in item.provenance if p.origin in {SemanticOrigin.HUMAN_EXPLICIT,SemanticOrigin.HUMAN_CORRECTION})
            current=any(c.polarity=='AFFIRMATIVE' and c.temporal_scope=='CURRENT'
                        and c.modality in {'ASSERTION','REQUEST'} and item.item_id in c.semantic_item_ids for c in meaning.clauses)
            correction=item.kind is SemanticKind.CORRECTION and bool(item.supersedes)
            if (item.kind is not expected and not correction) or item.requires_human or not human or not current:continue
            if cls=='PRODUCT_INVARIANT' and item.statement not in revision.constraints:continue
            # Preserve the exact declaration span; do not turn paraphrase into approval.
            value='\n'.join(dict.fromkeys(p.source_text for p in human))
            (invariants if cls=='PRODUCT_INVARIANT' else decisions).append((str(meaning.id)+':'+item.item_id,value))
    if any(d.required_before_production for d in ir.human_decisions) or any(q.blocks_current_step and q.requires_human and not q.safe_reversible_assumption for q in ir.questions):
        required.add('APPROVED_DECISION')
        # A present choice does not discharge a separate unresolved reserved choice.
        decisions=[]
    # Work-scoped restrictions remain constraints, never invented Product invariants.
    constraints=tuple(c for c in revision.constraints if c not in {i.statement for value in history for i in value.items if i.subject=='product_invariant'})
    if constraints:required.add('APPROVED_CONSTRAINT')
    payload={'work_revision':revision.revision_fingerprint,'ir':[value.basis_fingerprint for value in history],
             'governance':dict(governance),'constraints':list(revision.constraints)}
    source_revision=sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()
    provenance=f'product:{product_id};work:{work.id};work-reality:{revision.id}@{revision.revision_fingerprint};'+ ';'.join(f'semantic-ir:{value.id}@{value.basis_fingerprint}' for value in history)+f';governance:{revision.governance_record_id}'
    return ManagedGreenfieldContext(product_id,work.id,source_revision,provenance,intent,
                                    tuple(invariants),tuple(decisions),constraints,tuple(sorted(required)))


def read_managed_greenfield_context(session, *, work, product_id, repository_identity):
    from sqlalchemy import select
    from spg.infrastructure.persistence.product_schema import product_managed_sources,work_source_bases
    from spg.infrastructure.persistence.runtime_schema import governance_records
    from spg.infrastructure.persistence.product_store import ProductStore
    from spg.application.human_attention import canonical_ir_for_work
    source=session.execute(select(product_managed_sources).where(product_managed_sources.c.product_id==product_id)).mappings().one_or_none()
    basis=session.execute(select(work_source_bases).where(work_source_bases.c.work_id==work.id)).mappings().one_or_none()
    if source is None or basis is None or source['provider_kind']!='gitea' or source['origin'] or basis['source_version']!=0:
        return None
    store=ProductStore(session);revision=store.current_work_reality_revision(work.id)
    if revision is None:return None
    governance=session.execute(select(governance_records).where(governance_records.c.id==revision.governance_record_id)).mappings().one_or_none()
    from spg.infrastructure.persistence.interaction_store import InteractionStore
    history=[];seen=set();prior=revision
    while prior is not None and prior.id not in seen:
        seen.add(prior.id)
        assessment=InteractionStore(session).assessment(prior.source_assessment_id) if prior.source_assessment_id else None
        if assessment is not None and assessment.semantic_ir is not None:history.append(assessment.semantic_ir)
        prior=store.work_reality_revision(prior.previous_revision_id) if prior.previous_revision_id else None
    return project_greenfield_context(product_id=product_id,work=work,revision=revision,
                                      ir=canonical_ir_for_work(session,work.id),governance=governance,semantic_history=history)
