"""Server-owned delivery facts in the existing append-only audit ledger.

Client action hints are declarations, never authority or proof of receipt.
This observer does not publish, authorize, accept, repair or promote anything.
"""
from datetime import UTC, datetime
from enum import StrEnum
from io import BytesIO
from uuid import UUID, uuid4
from zipfile import ZipFile

from sqlalchemy import insert, select, func, or_, and_
from spg.application.delivery import fingerprint
from spg.domain.product import ProductInvariantViolation
from spg.infrastructure.persistence.connector_schema import connector_audit_events as ledger
from spg.infrastructure.persistence.product_schema import product_works
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.performance import current_request_id

NAMESPACE = 'DELIVERY_ACTION'
SURFACES = {'PRODUCT_SOURCE_EXPORT', 'WORK_DELIVERY', 'DELIVERABLE', 'DIRECT_API'}

class DeliveryAction(StrEnum):
    OFFICIAL = 'DOWNLOAD_OFFICIAL_PRODUCT_SOURCE'
    SOURCE_REVISION = 'DOWNLOAD_PRODUCT_SOURCE_REVISION'
    CANDIDATE_SOURCE = 'DOWNLOAD_CANDIDATE_SOURCE'
    AUTHORIZED = 'DOWNLOAD_CURRENT_AUTHORIZED_DELIVERY'
    ARTIFACT = 'DOWNLOAD_DELIVERY_ARTIFACT'
    CANDIDATE_ARTIFACT = 'DOWNLOAD_CANDIDATE_ARTIFACT'


def classify_delivery(expected, selected, response=None):
    if response is not None and (not response['complete'] or not 200 <= response['http_status'] < 300):
        return 'NOT_SERVED'
    if not expected or not expected.get('revision'):
        return 'UNAVAILABLE'
    if not selected:
        return 'UNRESOLVED'
    for key in ('product_id','work_id','candidate_id','candidate_fingerprint','runtime_commit_id','manifest_id','revision'):
        if expected.get(key) is not None and selected.get(key) != expected[key]:
            return 'OBSERVED_DELIVERY_DIVERGENCE'
    if response is not None and expected.get('payload_sha256') and response['sha256']!=expected['payload_sha256']:
        return 'OBSERVED_DELIVERY_DIVERGENCE'
    return 'PASS'


def archive_inventory(data, canonical_artifacts=None, software=False):
    # Central-directory metadata only; do not rehash/decompress source blobs.
    known = {(('source/' if software else 'artifacts/') + a.path):
             {'sha256':a.sha256,'size_bytes':a.size_bytes} for a in canonical_artifacts or ()}
    with ZipFile(BytesIO(data)) as archive:
        files = [i for i in archive.infolist() if not i.is_dir()]
        return {'complete':len(files)<=2000,'file_count':len(files),
            'files':[{'path':i.filename,'size_bytes':i.file_size,'crc32':i.CRC,
                      **known.get(i.filename,{})} for i in files[:2000]],
            'hash_basis':'SHA-256 of actual HTTP payload; per-artifact SHA-256 from immutable Manifest when present'}


class DeliveryObservationService:
    def __init__(self, database): self.database=database

    def lineage(self, work_id, revision=None):
        if work_id is None: return {}
        with self.database.unit_of_work() as u:
            p=ProductStore(u.session);binding=p.runtime_binding(work_id)
            if binding is None:return {'work_id':str(work_id)}
            summary=p.runtime_summary(binding);r=RuntimeStore(u.session)
            commit=r.runtime_commit(summary.runtime_commit_id) if summary.runtime_commit_id else None
            if commit is None or revision is not None and revision!=commit.repository_revision:
                return {'work_id':str(work_id)}
            return {'work_id':str(work_id),'source_resource_id':str(binding.resource_id),'candidate_id':str(commit.candidate_id),
                'candidate_fingerprint':commit.candidate_fingerprint,'runtime_commit_id':str(commit.id),
                'revision':commit.repository_revision,'tree':commit.repository_tree_identity,
                'authorization_id':str(commit.human_authorization_id)}

    def begin(self, request, *, operation, semantic, product_id=None, work_id=None):
        declared=request.query_params.get('action_semantic')
        if declared is not None:
            try:semantic=DeliveryAction(declared)
            except ValueError:raise ProductInvariantViolation('Unknown delivery action semantic') from None
        allowed = {
            'PRODUCT_SOURCE_EXPORT': {DeliveryAction.OFFICIAL, DeliveryAction.SOURCE_REVISION, DeliveryAction.CANDIDATE_SOURCE, DeliveryAction.AUTHORIZED},
            'DELIVERY_PACKAGE': {DeliveryAction.AUTHORIZED},
            'DELIVERY_ARTIFACT': {DeliveryAction.ARTIFACT},
            'CANDIDATE_ARTIFACT': {DeliveryAction.CANDIDATE_ARTIFACT},
        }
        if semantic not in allowed[operation]:
            raise ProductInvariantViolation('Delivery semantic does not belong to this operation')
        context=request.query_params.get('context_work_id')
        if context is not None and work_id is None:
            try:work_id=UUID(context)
            except ValueError:raise ProductInvariantViolation('Invalid delivery Work context') from None
        with self.database.unit_of_work() as u:
            if work_id is not None:
                bound=u.session.scalar(select(product_works.c.product_id).where(product_works.c.id==work_id))
                if product_id is not None and bound!=product_id:
                    raise ProductInvariantViolation('Delivery action context belongs to another Product')
                product_id=bound
        initiating=request.query_params.get('initiating_action_id')
        try:initiating=str(UUID(initiating)) if initiating else None
        except ValueError:raise ProductInvariantViolation('Invalid initiating action identity') from None
        surface=request.query_params.get('surface','DIRECT_API')
        if surface not in SURFACES:raise ProductInvariantViolation('Unknown delivery surface')
        requested_revision=request.query_params.get('revision')
        # Never persist arbitrary query strings, URLs, credentials or browser metadata.
        if requested_revision is not None:
            import re
            if re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}', requested_revision) is None:
                raise ProductInvariantViolation('Delivery revision must be an exact Git identity')
        data={'action_id':str(uuid4()),'occurred_at':datetime.now(UTC).isoformat(),
            'actor_identity':getattr(request.state,'actor_id','human:owner'),
            'actor_type':'AUTHENTICATED_OWNER' if hasattr(request.state,'actor_id') else 'TEST_ONLY_NO_AUTH','request_id':current_request_id() or str(uuid4()),
            'operation':operation,'action_semantic':str(semantic),'semantic_basis':'CLIENT_DECLARED' if declared else 'ENDPOINT_DEFAULT',
            'surface':surface,'surface_basis':'CLIENT_DECLARED' if surface!='DIRECT_API' else 'ENDPOINT_ONLY',
            'initiating_action_id':initiating,'product_id':str(product_id) if product_id else None,
            'work_id':str(work_id) if work_id else None,'requested_revision':requested_revision,
            'client_received':'UNAVAILABLE','client_saved':'UNAVAILABLE'}
        observation=DeliveryObservation(self,data);request.state.delivery_observation=observation
        observation.append('USER_ACTION_INITIATED')
        return observation

    def append(self, data, phase):
        detail={**data,'phase':phase};detail['fingerprint']=fingerprint(detail)
        with self.database.unit_of_work() as u:
            u.session.execute(insert(ledger).values(id=uuid4(),actor_id=data['actor_identity'],
                subject_kind=NAMESPACE,subject_id=data['action_id'],action=phase,detail=detail,
                created_at=datetime.now(UTC)));u.commit()

    def for_work(self, work_id, product_id):
        # Product-only actions are explicitly labelled, not retroactively owned by a Work.
        scope=or_(ledger.c.detail['work_id'].astext==str(work_id),and_(
            ledger.c.detail['work_id'].astext.is_(None),ledger.c.detail['product_id'].astext==str(product_id)))
        with self.database.unit_of_work() as u:
            identities=list(u.session.scalars(select(ledger.c.subject_id).where(
                ledger.c.subject_kind==NAMESPACE,scope).group_by(ledger.c.subject_id)
                .order_by(func.max(ledger.c.created_at).desc()).limit(50)))
            if not identities:return []
            rows=u.session.execute(select(ledger).where(ledger.c.subject_kind==NAMESPACE,
                ledger.c.subject_id.in_(identities)).order_by(ledger.c.created_at)).mappings().all()
        by_id={}
        for row in rows:
            data=dict(row['detail']);claimed=data.pop('fingerprint',None)
            valid=fingerprint(data)==claimed
            previous=by_id.get(row['subject_id'],{})
            by_id[row['subject_id']]={**data,'audit_record_valid':valid and previous.get('audit_record_valid',True),
                'event_ids':previous.get('event_ids',[])+[str(row['id'])],
                'phases':previous.get('phases',[])+[row['action']],
                'association':'EXACT_WORK_CONTEXT' if data.get('work_id') else 'PRODUCT_ONLY'}
        for action in by_id.values():
            if not action['audit_record_valid']:
                action['classification']='AUDIT_EVIDENCE_INVALID'
        return [by_id[i] for i in identities]


class DeliveryObservation:
    def __init__(self, service, data):self.service,self.data=service,data
    def append(self,phase):self.service.append(self.data,phase)
    def resolve(self, *, expected, selected, policy, basis):
        self.data.update(expected=expected,selected=selected,resolver_policy=policy,resolution_basis=basis,
            classification=classify_delivery(expected,selected))
        self.append('SERVER_RESOLVED')
    def inventory(self,inventory):self.data['inventory']=inventory
    def finish(self,response):
        self.data['response']=response
        self.data['classification']=classify_delivery(self.data.get('expected'),self.data.get('selected'),response)
        self.append('SERVER_SERVED' if response['complete'] and 200<=response['http_status']<300 else 'SERVER_NOT_SERVED')
