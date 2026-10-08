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
    accepted_source_version_id: UUID | None = None
    accepted_source_revision: str | None = None
    accepted_source_provenance: str | None = None

    @property
    def applicability(self):
        present={'PRODUCT_INTENT':bool(self.intent),'PRODUCT_INVARIANT':bool(self.invariants),
                 'APPROVED_DECISION':bool(self.decisions),'APPROVED_CONSTRAINT':bool(self.constraints)}
        return {key:('REQUIRED_AND_PRESENT' if value and key in self.required_classes else
                     'REQUIRED_AND_MISSING' if key in self.required_classes else
                     'PRESENT_AND_APPLICABLE' if value else 'NOT_YET_ESTABLISHED_BUT_NON_BLOCKING')
                for key,value in present.items()}


def _assert_admitted_revision(work, revision, ir, governance):
    if (revision is None or ir is None or not isinstance(ir,GovernedSemanticIR)
            or revision.work_id!=work.id or governance is None
            or str(governance['id'])!=str(revision.governance_record_id)
            or not governance['authority_identity']):
        raise DecisionContextAuthorityMissing('MANAGED_GREENFIELD_CONTEXT_OWNER_BASIS_MISSING')
    scope=governance.get('scope') or {}
    assessment_id=getattr(revision,'source_assessment_id',None)
    previous_revision_id=getattr(revision,'previous_revision_id',None)
    initial_admission=(
        governance.get('decision_type')=='ADMIT_LONG_LIVED_WORK'
        and governance.get('subject_type')=='PRODUCT_WORK'
        and str(governance['subject_identity'])==str(work.id)
        and str(scope.get('work_reality_revision_id'))==str(revision.id)
    )
    revision_admission=(
        governance.get('decision_type')=='ADMIT_WORK_REALITY_REVISION'
        and governance.get('subject_type')=='WORK_REALITY_REVISION_CANDIDATE'
        and str(scope.get('work_id'))==str(work.id)
        and assessment_id is not None and previous_revision_id is not None
        and str(scope.get('assessment_id'))==str(assessment_id)
        and str(scope.get('previous_revision_id'))==str(previous_revision_id)
        and str(governance['subject_identity'])==f'interaction-assessment:{assessment_id}'
    )
    if not (initial_admission or revision_admission):
        raise DecisionContextAuthorityMissing('MANAGED_GREENFIELD_CONTEXT_OWNER_BASIS_MISSING')


def project_greenfield_context(*, product_id, work, revision, ir, governance,
                               semantic_history=(), managed_source_identity=None):
    """Project only a source-owned admitted revision, never compiler candidates."""
    _assert_admitted_revision(work, revision, ir, governance)
    history=tuple(dict((value.id,value) for value in (ir,*semantic_history)).values())
    goals=next((value.current_production for value in history if value.current_production),())
    def uses_exact_managed_genesis(goal):
        if not goal.repository_required and goal.repository_reference is None:
            return True
        reference=goal.repository_reference
        return bool(managed_source_identity and goal.repository_required and reference
            and reference.value==managed_source_identity
            and reference.provenance.origin is SemanticOrigin.REPOSITORY_OBSERVED
            and reference.provenance.evidence_reference==f'product-source:{product_id}:0')
    initial_greenfield=any(uses_exact_managed_genesis(g)
                          for value in history for g in value.current_production)
    if not goals or not initial_greenfield or any(not uses_exact_managed_genesis(g) for g in goals):
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


def project_accepted_successor_context(*, product_id, work, revision, ir,
                                       governance, accepted_version, inherited):
    """Carry only accepted Product facts into a new Work's exact source basis."""
    _assert_admitted_revision(work, revision, ir, governance)
    if (accepted_version['product_id'] != product_id
            or accepted_version['version'] < 1
            or not all(accepted_version.get(key) for key in
                       ('work_id','candidate_id','acceptance_id','revision','tree'))
            or inherited.product_id != product_id):
        raise DecisionContextAuthorityMissing('MANAGED_ACCEPTED_SOURCE_BASIS_MISSING')
    # A new explicit Product policy declaration needs its own governed projection;
    # this continuity path may not silently discard or auto-approve it.
    if any(item.subject in {'product_invariant','approved_product_decision'}
           for item in ir.items):
        raise DecisionContextAuthorityMissing('MANAGED_PRODUCT_POLICY_CHANGE_REQUIRES_GOVERNANCE')
    constraints=tuple(revision.constraints)
    required=set(inherited.required_classes)-{'APPROVED_CONSTRAINT'}
    if constraints: required.add('APPROVED_CONSTRAINT')
    payload={'accepted_source_version_id':str(accepted_version['id']),
             'accepted_revision':accepted_version['revision'],
             'accepted_tree':accepted_version['tree'],
             'acceptance_id':str(accepted_version['acceptance_id']),
             'inherited_context_revision':inherited.source_revision,
             'current_work_revision':revision.revision_fingerprint,
             'current_governance_id':str(revision.governance_record_id)}
    source_revision=sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    provenance=(f"product-source-version:{accepted_version['id']}@{accepted_version['revision']};"
                f"human-acceptance:{accepted_version['acceptance_id']};"
                f"inherited:{inherited.provenance};"
                f"work-reality:{revision.id}@{revision.revision_fingerprint};"
                f"governance:{revision.governance_record_id}")
    return ManagedGreenfieldContext(
        product_id,work.id,source_revision,provenance,inherited.intent,
        inherited.invariants,inherited.decisions,constraints,tuple(sorted(required)),
        accepted_version['id'],accepted_version['revision'],provenance,
    )


def read_managed_greenfield_context(session, *, work, product_id, repository_identity,
                                    _historical=False, _pinned_revision_id=None):
    from sqlalchemy import select
    from spg.infrastructure.persistence.product_schema import (product_managed_sources,
        product_source_versions,work_source_bases,work_runtime_bindings,engineering_resources)
    from spg.infrastructure.persistence.runtime_schema import governance_records,baseline_candidates
    from spg.infrastructure.persistence.product_store import ProductStore
    from spg.application.human_attention import canonical_ir_for_work
    source=session.execute(select(product_managed_sources).where(product_managed_sources.c.product_id==product_id)).mappings().one_or_none()
    basis=session.execute(select(work_source_bases).where(work_source_bases.c.work_id==work.id)).mappings().one_or_none()
    resource_identity=(None if basis is None else session.execute(
        select(engineering_resources.c.repository_identity).where(
            engineering_resources.c.id==basis['resource_id'])).scalar_one_or_none())
    if (source is None or basis is None or source['provider_kind']!='gitea'
            or source['origin'] or resource_identity!=repository_identity
            or basis['product_id']!=product_id):
        return None
    if not _historical and (source['version'],source['accepted_revision'],source['accepted_tree']) != (
            basis['source_version'],basis['source_revision'],basis['source_tree']):
        raise DecisionContextAuthorityMissing('MANAGED_ACCEPTED_SOURCE_CHANGED')
    store=ProductStore(session)
    revision=(store.work_reality_revision(_pinned_revision_id) if _pinned_revision_id
              else store.current_work_reality_revision(work.id))
    if revision is None:return None
    governance=session.execute(select(governance_records).where(governance_records.c.id==revision.governance_record_id)).mappings().one_or_none()
    from spg.infrastructure.persistence.interaction_store import InteractionStore
    history=[];seen=set();prior=revision
    while prior is not None and prior.id not in seen:
        seen.add(prior.id)
        assessment=InteractionStore(session).assessment(prior.source_assessment_id) if prior.source_assessment_id else None
        if assessment is not None and assessment.semantic_ir is not None:history.append(assessment.semantic_ir)
        prior=store.work_reality_revision(prior.previous_revision_id) if prior.previous_revision_id else None
    ir=(next(iter(history),None) if _pinned_revision_id else
        canonical_ir_for_work(session,work.id))
    if basis['source_version']==0:
        return project_greenfield_context(product_id=product_id,work=work,revision=revision,
                                          ir=ir,governance=governance,semantic_history=history,
                                          managed_source_identity=source['repository_identity'])
    accepted=session.execute(select(product_source_versions).where(
        product_source_versions.c.product_id==product_id,
        product_source_versions.c.version==basis['source_version'])).mappings().one_or_none()
    if (accepted is None or accepted['revision']!=basis['source_revision']
            or accepted['tree']!=basis['source_tree'] or accepted['work_id']==work.id):
        raise DecisionContextAuthorityMissing('MANAGED_ACCEPTED_SOURCE_BASIS_MISSING')
    candidate=session.execute(select(baseline_candidates).where(
        baseline_candidates.c.id==accepted['candidate_id'])).mappings().one_or_none()
    binding=(None if candidate is None else session.execute(select(work_runtime_bindings).where(
        work_runtime_bindings.c.work_id==accepted['work_id'],
        work_runtime_bindings.c.production_run_id==candidate['production_run_id']
    )).mappings().one_or_none())
    if (candidate is None or binding is None
            or candidate['proposed_commit_identity']!=accepted['revision']
            or binding['work_reality_revision_id'] is None):
        raise DecisionContextAuthorityMissing('MANAGED_ACCEPTED_SOURCE_LINEAGE_MISSING')
    parent=store.work(accepted['work_id']) if accepted['work_id'] else None
    if parent is None:
        raise DecisionContextAuthorityMissing('MANAGED_ACCEPTED_SOURCE_BASIS_MISSING')
    parent_identity=session.execute(select(engineering_resources.c.repository_identity)
        .join(work_source_bases,work_source_bases.c.resource_id==engineering_resources.c.id)
        .where(work_source_bases.c.work_id==parent.id)).scalar_one_or_none()
    if parent_identity is None:
        raise DecisionContextAuthorityMissing('MANAGED_ACCEPTED_SOURCE_LINEAGE_MISSING')
    inherited=read_managed_greenfield_context(session,work=parent,product_id=product_id,
        repository_identity=parent_identity,_historical=True,
        _pinned_revision_id=binding['work_reality_revision_id'])
    if inherited is None:
        # Imported/declared Product source may instead carry ECF classes in
        # README.md. Let the ordinary repository policy validate those facts.
        return None
    return project_accepted_successor_context(product_id=product_id,work=work,
        revision=revision,ir=ir,governance=governance,accepted_version=accepted,
        inherited=inherited)
