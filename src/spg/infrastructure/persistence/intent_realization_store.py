"""Durable IRK ledger; owner reconciliation is required for satisfaction."""
from datetime import UTC, datetime
from sqlalchemy import insert, select, update

from spg.application.intent_realization import (
    IntentRealizationKernel, IntentRealizationViolation, reconcile_obligation,
    validate_turn_completion,
)
from spg.domain.intent_realization import (
    GovernedSemanticIR, ObligationState, RealizationRefinement,
    TERMINAL_OBLIGATION_STATES, TurnObligation,
    ObligationSupersession, ObservedEffect, SemanticKind, SemanticOrigin,
)
from spg.infrastructure.persistence.intent_realization_schema import (
    realization_refinements, turn_obligations, turn_realizations,
    turn_semantic_envelopes,
)


class IntentRealizationStore:
    def __init__(self, session):
        self.session = session

    def create_envelope(self, *, turn_id, source_record_id, human_content_hash,
            provenance_basis):
        self.session.execute(insert(turn_semantic_envelopes).values(
            turn_id=turn_id, source_record_id=source_record_id,
            human_content_hash=human_content_hash,
            provenance_basis=provenance_basis, state="COMPILING", attempt=0,
            basis_fingerprint=None, semantic_ir_id=None, blocker=None,
            history=[]))

    def begin_compilation(self, turn_id):
        row = self.session.execute(select(turn_semantic_envelopes).where(
            turn_semantic_envelopes.c.turn_id == turn_id).with_for_update()).mappings().one_or_none()
        if row is None or row["state"] == "GOVERNED":
            return
        attempt = row["attempt"] + 1
        self.session.execute(update(turn_semantic_envelopes).where(
            turn_semantic_envelopes.c.turn_id == turn_id).values(
                state="COMPILING", attempt=attempt, blocker=None,
                history=[*row["history"], {"state": "COMPILING", "attempt": attempt,
                    "at": datetime.now(UTC).isoformat()}]))

    def compilation_failed(self, turn_id, *, code, evidence):
        row = self.session.execute(select(turn_semantic_envelopes).where(
            turn_semantic_envelopes.c.turn_id == turn_id).with_for_update()).mappings().one_or_none()
        if row is None or row["state"] == "GOVERNED":
            return
        blocker = {"code": code, "evidence": evidence}
        self.session.execute(update(turn_semantic_envelopes).where(
            turn_semantic_envelopes.c.turn_id == turn_id).values(
                state="SEMANTIC_COMPILATION_FAILED", blocker=blocker,
                history=[*row["history"], {"state": "SEMANTIC_COMPILATION_FAILED",
                    "attempt": row["attempt"], "at": datetime.now(UTC).isoformat(),
                    "blocker": blocker}]))

    def semantic_envelope(self, turn_id):
        row = self.session.execute(select(turn_semantic_envelopes).where(
            turn_semantic_envelopes.c.turn_id == turn_id)).mappings().one_or_none()
        if row is None:
            return None
        return {**dict(row), "turn_id": str(row["turn_id"]),
            "source_record_id": str(row["source_record_id"]),
            "semantic_ir_id": None if row["semantic_ir_id"] is None else str(row["semantic_ir_id"])}

    def semantic_ir(self, turn_id):
        row = self.session.execute(select(turn_realizations.c.payload).where(
            turn_realizations.c.turn_id == turn_id)).scalar_one_or_none()
        return None if row is None else GovernedSemanticIR.model_validate(row)

    def assessment_id(self, turn_id):
        return self.session.execute(select(turn_realizations.c.assessment_id).where(
            turn_realizations.c.turn_id == turn_id)).scalar_one_or_none()

    def initialize(self, turn_id, assessment_id, ir, *, work_question_step_id=None):
        existing = self.semantic_ir(turn_id)
        if existing is not None:
            if existing != ir:
                raise IntentRealizationViolation("SEMANTIC_TYPE_MISMATCH: immutable Turn interpretation already exists")
            return self.obligations(turn_id)
        self.session.execute(insert(turn_realizations).values(turn_id=turn_id,
            semantic_ir_id=ir.id, assessment_id=assessment_id, payload=ir.model_dump(mode="json")))
        envelope = self.session.execute(select(turn_semantic_envelopes).where(
            turn_semantic_envelopes.c.turn_id == turn_id).with_for_update()).mappings().one_or_none()
        if envelope is not None:
            self.session.execute(update(turn_semantic_envelopes).where(
                turn_semantic_envelopes.c.turn_id == turn_id).values(
                    state="GOVERNED", semantic_ir_id=ir.id,
                    basis_fingerprint=ir.basis_fingerprint, blocker=None,
                    history=[*envelope["history"], {"state": "GOVERNED",
                        "attempt": envelope["attempt"], "at": datetime.now(UTC).isoformat(),
                        "semantic_ir_id": str(ir.id)}]))
        obligations = IntentRealizationKernel().obligations(ir, turn_id,
            work_question_step_id=work_question_step_id)
        for obligation in obligations:
            self.session.execute(insert(turn_obligations).values(id=obligation.id,
                turn_id=turn_id, semantic_item_id=obligation.semantic_item_id,
                state=obligation.state.value, version=obligation.version,
                payload=obligation.model_dump(mode="json")))
        return obligations

    def obligations(self, turn_id):
        rows = self.session.execute(select(turn_obligations.c.payload).where(
            turn_obligations.c.turn_id == turn_id).order_by(turn_obligations.c.semantic_item_id)).scalars()
        return tuple(TurnObligation.model_validate(row) for row in rows)

    def supersede(self, prior, *, replacement_ir, replacement_item_id, owner_disposition=None):
        persisted = self.session.execute(select(turn_realizations.c.payload).where(
            turn_realizations.c.semantic_ir_id == replacement_ir.id)).scalar_one_or_none()
        previous = self.semantic_ir(prior.turn_id)
        from spg.infrastructure.persistence.interaction_store import InteractionStore
        records = InteractionStore(self.session)
        previous_record = None if previous is None else records.record(previous.source_record_id)
        replacement_record = records.record(replacement_ir.source_record_id)
        if (persisted is None or GovernedSemanticIR.model_validate(persisted) != replacement_ir
                or previous is None or previous.interaction_id != replacement_ir.interaction_id
                or previous_record is None or replacement_record is None
                or previous_record.sequence >= replacement_record.sequence):
            raise IntentRealizationViolation("ACTION_ARGUMENT_PROVENANCE_INVALID: supersession needs a persisted subsequent Turn in the same Interaction")
        item = next((i for i in replacement_ir.items if i.item_id == replacement_item_id), None)
        if (item is None or item.kind is not SemanticKind.CORRECTION or str(prior.id) not in item.supersedes
                or not any(p.source_record_id == replacement_ir.source_record_id and p.origin in {
                    SemanticOrigin.HUMAN_EXPLICIT, SemanticOrigin.HUMAN_CORRECTION} for p in item.provenance)):
            raise IntentRealizationViolation("ACTION_SCOPE_INFLATION: replacement needs current Human correction naming the exact obligation")
        if prior.state is ObligationState.PENDING:
            disposition = ObservedEffect(owner="turn-obligation-ledger",
                evidence_references=(f"obligation:{prior.id}:not-dispatched:version:{prior.version}",),
                facts={"obligation_id":str(prior.id),"dispatch_status":"NOT_DISPATCHED"})
        elif (prior.state is ObligationState.RUNNING and prior.observed_effect is not None
                and owner_disposition is not None and owner_disposition.owner == prior.observed_effect.owner
                and owner_disposition.facts.get("cancelled_obligation_id") == str(prior.id)
                and owner_disposition.facts.get("cancellation_acknowledged") is True):
            disposition = owner_disposition
        else:
            raise IntentRealizationViolation("ACTION_REQUIRES_REALITY_REFRESH: running effect needs its owner's cancellation acknowledgement")
        lineage = ObligationSupersession(replacement_ir_id=replacement_ir.id,
            replacement_item_id=item.item_id,prior_obligation_id=prior.id,owner_disposition=disposition)
        return self.transition(prior,state=ObligationState.SUPERSEDED,
            blocker_reference=f"semantic-ir:{replacement_ir.id}:item:{item.item_id}",_supersession=lineage)

    def transition(self, prior, *, state=None, observation=None, blocker_reference=None, running_evidence=None, _supersession=None):
        stored = self.session.execute(select(turn_obligations.c.payload).where(
            turn_obligations.c.id == prior.id).with_for_update()).scalar_one_or_none()
        if stored is None or TurnObligation.model_validate(stored) != prior:
            raise IntentRealizationViolation("ACTION_REQUIRES_REALITY_REFRESH: obligation state or basis is stale")
        if prior.state in TERMINAL_OBLIGATION_STATES:
            raise IntentRealizationViolation("ACTION_SCOPE_INFLATION: terminal obligation cannot be replayed")
        if observation is not None:
            next_value = reconcile_obligation(prior, observation)
        else:
            if state is ObligationState.SUPERSEDED and _supersession is None:
                raise IntentRealizationViolation("ACTION_SCOPE_INFLATION: use validated supersession with owner disposition")
            if state not in {ObligationState.RUNNING, ObligationState.BLOCKED_WITH_EVIDENCE,
                    ObligationState.REQUIRES_HUMAN, ObligationState.SUPERSEDED}:
                raise IntentRealizationViolation("EXPECTED_EFFECT_NOT_REALIZED: only owner evidence can satisfy an obligation")
            if running_evidence is not None and (state is not ObligationState.RUNNING or not running_evidence.facts.get("owner_running")):
                raise IntentRealizationViolation("RESPONSE_ACTION_INCONSISTENCY: running status requires actual owner evidence")
            next_value = prior.model_copy(update={"state": state, "blocker_reference": blocker_reference,
                "observed_effect": running_evidence or prior.observed_effect,
                "supersession": _supersession or prior.supersession,
                "version": prior.version + 1})
        next_value = TurnObligation.model_validate(next_value.model_dump())
        result = self.session.execute(update(turn_obligations).where(
            turn_obligations.c.id == prior.id, turn_obligations.c.version == prior.version).values(
                state=next_value.state.value, version=next_value.version,
                payload=next_value.model_dump(mode="json")))
        if result.rowcount != 1:
            raise IntentRealizationViolation("ACTION_REQUIRES_REALITY_REFRESH: obligation version is stale")
        return next_value

    def refinements(self, turn_id):
        rows = self.session.execute(select(realization_refinements.c.payload).where(
            realization_refinements.c.turn_id == turn_id).order_by(
                realization_refinements.c.attempt, realization_refinements.c.id)).scalars()
        return tuple(RealizationRefinement.model_validate(row) for row in rows)

    def record_refinement(self, value):
        value = RealizationRefinement.model_validate(value.model_dump())
        signature = f"{value.scope.value}:{value.obligation_id}"
        previous = [r for r in self.refinements(value.turn_id)
            if f"{r.scope.value}:{r.obligation_id}" == signature]
        if value.attempt != len(previous) + 1 or any(r.attempt_budget != value.attempt_budget for r in previous):
            raise IntentRealizationViolation("TURN_NON_CONVERGING: durable attempt budget cannot reset")
        if previous and value.parent_id != previous[-1].id:
            raise IntentRealizationViolation("TURN_NON_CONVERGING: refinement lineage must continue")
        self.session.execute(insert(realization_refinements).values(
            id=value.id, turn_id=value.turn_id, obligation_id=value.obligation_id,
            parent_id=value.parent_id, scope=value.scope.value, attempt=value.attempt,
            signature=signature, payload=value.model_dump(mode="json")))

    def validate_completion(self, turn_id):
        ir = self.semantic_ir(turn_id)
        obligations = self.obligations(turn_id)
        validate_turn_completion(ir, obligations)
        expected = IntentRealizationKernel().obligations(ir, turn_id)
        if {o.id for o in expected} != {o.id for o in obligations}:
            raise IntentRealizationViolation("EXPLICIT_ACTION_LOST_BEFORE_EXECUTION: incomplete persistent obligation ledger")

    def projection(self, turn_id):
        ir = self.semantic_ir(turn_id)
        envelope = self.semantic_envelope(turn_id)
        return {"semantic_ir": None if ir is None else ir.model_dump(mode="json"),
            "semantic_envelope": envelope,
            "obligations": [o.model_dump(mode="json") for o in self.obligations(turn_id)],
            "refinements": [r.model_dump(mode="json") for r in self.refinements(turn_id)],
            "historical_without_ir": ir is None and envelope is None}
