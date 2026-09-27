"""Typed IR inputs for existing Preview, Human governance and delivery owners.

Adapters select no natural-language meaning. They preserve each owner's exact
Candidate, current actor, fingerprint, credential and side-effect checks.
"""
from uuid import UUID

from sqlalchemy import select

from spg.domain.intent_realization import ObservedEffect
from spg.domain.interaction_actions import CanonicalOperation as O
from spg.domain.product import AttentionAction, AttentionKind, AttentionResolutionRequest
from spg.infrastructure.persistence.github_delivery_schema import (
    remote_delivery_authorizations, remote_delivery_receipts,
)


class IntentOwnerAdapters:
    def __init__(self, interaction, work, delivery, preview, github, *, orchestrator=None):
        self.interaction = interaction
        self.work = work
        self.delivery = delivery
        self.preview = preview
        self.github = github
        self.orchestrator = orchestrator

    def install(self):
        for operation in {O.REQUEST_PREVIEW, O.ACCEPT_CANDIDATE, O.AUTHORIZE_DELIVERY,
                O.PUSH_BRANCH, O.CREATE_PR}:
            self.interaction.configure_operational_owner(operation.value, self.execute)
        self.interaction.configure_intent_observations(self.observations)

    def observations(self, interaction_id):
        work_id = self.interaction.get_shared_understanding(interaction_id).governed_work_id
        if work_id is None:
            return ()
        result = []
        try:
            context = self.delivery.candidate_context(work_id)
        except (ValueError, RuntimeError) as error:
            result.append(ObservedEffect(owner="candidate-verification",
                evidence_references=(f"work:{work_id}:candidate-context",),
                facts={"blocker": getattr(error, "code", type(error).__name__)}))
            context = None
        if context is not None:
            result.append(ObservedEffect(owner="candidate-verification",
                evidence_references=(f"baseline-candidate:{context['candidate_id']}",),
                facts={"work_id": str(work_id), "candidate_id": context["candidate_id"],
                    "candidate_fingerprint": context["candidate_fingerprint"],
                    "candidate_revision": context["repository_revision"],
                    "target_branch": context["target_branch"]}))
        for item in self.delivery.view(work_id)["deliveries"]:
            if not item["current"]:
                continue
            manifest = item["manifest"]
            result.append(ObservedEffect(owner="delivery-manifest",
                evidence_references=(f"delivery-manifest:{manifest['id']}",),
                facts={"manifest_id": manifest["id"], "manifest_fingerprint": manifest["fingerprint"],
                    "candidate_revision": manifest["repository_revision"],
                    "repository_ref": manifest.get("software", {}).get("repository_ref")
                        if manifest.get("software") else None}))
        with self.work.database.unit_of_work() as uow:
            authorizations = uow.session.execute(select(remote_delivery_authorizations).where(
                remote_delivery_authorizations.c.work_id == work_id)).mappings().all()
        for value in authorizations:
            result.append(ObservedEffect(owner="remote-delivery-authorization",
                evidence_references=(f"remote-delivery-authorization:{value['id']}",),
                facts={"authorization_id": str(value["id"]), "candidate_revision": value["expected_revision"],
                    "target_branch": value["target_branch"], "expected_remote_revision": value["expected_remote_revision"]}))
        return tuple(result)

    def execute(self, interaction_id, item, actor):
        operation = O(item.action.operation)
        reference = f"interaction-semantic-item:{interaction_id}:{item.item_id}"
        def blocked(signal, evidence=reference):
            return ObservedEffect(owner="lifecycle-action-admission",
                evidence_references=(evidence,), facts={"blocker": signal, "authority_expanded": False})
        args = {key: value.value for key, value in item.action.arguments.items()}
        work_id = self.interaction.get_shared_understanding(interaction_id).governed_work_id
        if work_id is None:
            return blocked("ACTION_REQUIRES_WORK_ADMISSION")
        try:
            if operation is O.REQUEST_PREVIEW:
                if self.preview is None:
                    return blocked("PREVIEW_CAPABILITY_UNAVAILABLE")
                context = self.delivery.candidate_context(work_id)
                if context is None:
                    return blocked("ACTION_REQUIRES_CANDIDATE")
                if args.get("candidate_revision") != context["repository_revision"]:
                    return blocked("EXACT_CANDIDATE_BASIS_REQUIRED")
                session = self.preview.request(work_id)
                current = self.preview.current(work_id)
                if current is None or current.id != session.id:
                    return blocked("ACTION_REQUIRES_REALITY_REFRESH")
                served = any(e.get("kind") == "SERVED_VERIFICATION" and e.get("result") == "PASS"
                    for e in current.evidence)
                return ObservedEffect(owner="candidate-preview",
                    evidence_references=(f"candidate-preview:{current.id}:v{current.version}",),
                    facts={"preview_status": current.status.value,
                        "served_verification": "PASS" if served else "UNQUALIFIED",
                        "owner_running": current.status.value in {"REQUESTED", "PREPARING", "BUILDING", "STARTING"},
                        "candidate_revision": current.repository_revision, "endpoint": current.endpoint,
                        "failure_code": current.failure_code})
            if operation is O.ACCEPT_CANDIDATE:
                context = self.delivery.candidate_context(work_id)
                if context is None:
                    return blocked("ACTION_REQUIRES_CANDIDATE")
                if args.get("candidate_revision") != context["repository_revision"]:
                    return blocked("EXACT_CANDIDATE_BASIS_REQUIRED")
                attention = next((a for a in self.work.list_attention(work_id=work_id)
                    if a.kind is AttentionKind.CANDIDATE_AUTHORIZATION
                    and a.governed_subject_ref == f"baseline-candidate:{context['candidate_id']}"), None)
                if attention is None:
                    return blocked("CURRENT_CANDIDATE_ATTENTION_REQUIRED")
                self.work.resolve_attention(attention.id, AttentionResolutionRequest(
                    action=AttentionAction.AUTHORIZE, authority_identity=actor,
                    rationale=f"Explicit current Human acceptance: {reference}"))
                if self.orchestrator is not None:
                    self.orchestrator.schedule(work_id)
                accepted = self.delivery.candidate_context(work_id)
                authorization_id = None if accepted is None else accepted.get("human_authorization_id")
                if authorization_id is None:
                    return blocked("HUMAN_ACCEPTANCE_NOT_OBSERVED")
                return ObservedEffect(owner="candidate-human-governance",
                    evidence_references=(f"human-authorization:{authorization_id}",),
                    facts={"acceptance": "ACCEPT", "candidate_revision": context["repository_revision"]})
            if operation is O.AUTHORIZE_DELIVERY:
                required = {"manifest_id", "candidate_revision", "target_branch"}
                if not required <= args.keys():
                    return blocked("EXACT_DELIVERY_BASIS_REQUIRED")
                value = self.github.authorize(actor, work_id=work_id,
                    manifest_id=UUID(args["manifest_id"]), expected_revision=args["candidate_revision"],
                    target_branch=args["target_branch"], expected_remote_revision=args.get("expected_remote_revision"),
                    rationale=f"Explicit current Human delivery consent: {reference}")
                return ObservedEffect(owner="remote-delivery-authorization",
                    evidence_references=(f"remote-delivery-authorization:{value['authorization_id']}",),
                    facts={"delivery_authorization_id": value["authorization_id"],
                        "candidate_revision": value["expected_revision"]})
            if not {"authorization_id", "candidate_revision"} <= args.keys():
                return blocked("EXACT_DELIVERY_AUTHORIZATION_REQUIRED")
            identity = UUID(args["authorization_id"])
            with self.work.database.unit_of_work() as uow:
                authorization = uow.session.execute(select(remote_delivery_authorizations).where(
                    remote_delivery_authorizations.c.id == identity)).mappings().first()
                receipt = uow.session.execute(select(remote_delivery_receipts).where(
                    remote_delivery_receipts.c.authorization_id == identity)).mappings().first()
            if (authorization is None or authorization["work_id"] != work_id
                    or authorization["actor_id"] != actor
                    or authorization["expected_revision"] != args["candidate_revision"]):
                return blocked("ACTION_AUTHORITY_OR_CANDIDATE_BASIS_MISMATCH")
            if operation is O.PUSH_BRANCH:
                value = self.github.push(identity, actor_id=actor)
                return ObservedEffect(owner="github-push",
                    evidence_references=(f"remote-delivery-receipt:{identity}",),
                    facts={"remote_revision": value["remote_after"], "candidate_revision": args["candidate_revision"], "target_branch": authorization["target_branch"]})
            # Creating a PR never silently supplies an omitted push request.
            if receipt is None or receipt["push_condition"] != "OBSERVED":
                return blocked("OBSERVED_PUSH_REQUIRED_BEFORE_PR")
            if not {"base_branch", "title", "body"} <= args.keys():
                return blocked("PULL_REQUEST_ARGUMENTS_REQUIRED")
            value = self.github.create_pull_request(identity, actor_id=actor,
                base=args["base_branch"], title=args["title"], body=args["body"])
            return ObservedEffect(owner="github-pull-request",
                evidence_references=(f"remote-delivery-receipt:{identity}",),
                facts={"pull_request_url": value["pr_url"], "candidate_revision": args["candidate_revision"]})
        except (ValueError, RuntimeError) as error:
            # The existing owner retains its evidence; errors never relax its
            # policy, acquire credentials, or imply an execution promise.
            return blocked(getattr(error, "code", type(error).__name__))
