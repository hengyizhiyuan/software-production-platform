"""Canonical Quality ledger; mutations never update production owner tables."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from sqlalchemy import select, insert, update, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from spg.evaluation.contracts import (CaseDefinition, Cohort, Evaluation, Evaluator,
    ExperimentRequest, PreferenceRequest, AttributionRequest, PromotionRequest,
    QualityError, objective_verdict, earliest_divergence, fingerprint)
from spg.infrastructure.persistence.quality_schema import (
    quality_cases as cases, quality_case_versions as versions, quality_campaigns as campaigns,
    quality_campaign_members as members, quality_campaign_runs as runs, quality_case_runs as attempts,
    quality_evaluations as evaluations, quality_findings as findings, quality_experiments as experiments,
    quality_preferences as preferences, quality_learning_signals as signals,
    quality_promotion_decisions as promotions)


def now():
    return datetime.now(UTC)


def json_record(record):
    return record.model_dump(mode="json")


class QualityService:
    def __init__(self, database, settings):
        self.database, self.settings = database, settings

    @staticmethod
    def _one(session, table, identity, *, lock=False):
        q = select(table).where(table.c.id == identity)
        if lock:
            q = q.with_for_update()
        r = session.execute(q).mappings().first()
        if r is None:
            raise QualityError("QUALITY_RECORD_NOT_FOUND")
        return dict(r)

    def register_case(self, definition: CaseDefinition):
        from spg.evaluation.catalog import recipes
        if definition.runner_key not in recipes():
            raise QualityError("UNREGISTERED_QUALITY_RECIPE")
        recipe = recipes()[definition.runner_key]
        if definition.runner_key not in {"sealed-live-intent", "unqualified-scenario"}:
            if (definition.key != "watt." + recipe.key or definition.motive != recipe.title
                or definition.invariants != (recipe.invariant,)
                or definition.stage != recipe.stage
                or definition.context.get("execution_environment") != "ISOLATED_QUALIFICATION"):
                raise QualityError("CASE_DOES_NOT_MATCH_REVIEWED_RECIPE")
        if definition.runner_key == "sealed-live-intent" and (
            definition.cohorts != (Cohort.FRESH_HOLDOUT,) or not definition.private_material.get("human_text")
            or definition.private_material.get("expected") != {"current_production": True,
                "repository_required": False, "repository_reference": None}):
            raise QualityError("INVALID_SEALED_INTENT_RECIPE")
        if Cohort.FRESH_HOLDOUT in definition.cohorts and len(definition.cohorts) != 1:
            raise QualityError("HOLDOUT_MUST_REMAIN_UNSEEN")
        cid = uuid5(NAMESPACE_URL, "watt:quality:case:" + definition.key)
        payload = json_record(definition)
        material = {k: v for k, v in payload.items() if k not in {"aliases", "cohorts"}}
        digest = fingerprint(material)
        with self.database.unit_of_work() as u:
            u.session.execute(pg_insert(cases).values(id=cid, key=definition.key,
                lifecycle="ACTIVE", cohorts=payload["cohorts"], aliases=payload["aliases"])
                .on_conflict_do_nothing(index_elements=[cases.c.key]))
            row = self._one(u.session, cases, cid, lock=True)
            if ((Cohort.FRESH_HOLDOUT in row["cohorts"]) != (Cohort.FRESH_HOLDOUT in definition.cohorts)):
                raise QualityError("HOLDOUT_MUST_REMAIN_UNSEEN")
            merged_cohorts = sorted(set(row["cohorts"]) | set(payload["cohorts"]))
            merged_aliases = sorted(set(row["aliases"]) | set(payload["aliases"]))
            u.session.execute(update(cases).where(cases.c.id == cid).values(
                cohorts=merged_cohorts, aliases=merged_aliases))
            old = u.session.execute(select(versions).where(versions.c.case_id == cid,
                versions.c.fingerprint == digest)).mappings().first()
            if old:
                u.commit()
                return dict(old)
            number = 1 + (u.session.scalar(select(func.max(versions.c.version)).where(
                versions.c.case_id == cid)) or 0)
            vid = uuid4()
            u.session.execute(insert(versions).values(id=vid, case_id=cid,
                version=number, fingerprint=digest, definition=payload))
            u.commit()
            return self._one(u.session, versions, vid)

    def list_cases(self):
        with self.database.unit_of_work() as u:
            rows = u.session.execute(select(cases).order_by(cases.c.key)).mappings().all()
            out = []
            for r in rows:
                v = u.session.execute(select(versions).where(versions.c.case_id == r["id"])
                    .order_by(versions.c.version.desc()).limit(1)).mappings().one()
                d = dict(v["definition"])
                d.pop("private_material", None)
                if Cohort.FRESH_HOLDOUT in r["cohorts"]:
                    for key in ("motive", "invariants", "context", "runner_key", "provenance"):
                        d.pop(key, None)
                    d["sealed"] = True
                out.append({**dict(r), "current_version": v["version"], "version_id": v["id"],
                    "fingerprint": v["fingerprint"], "definition": d})
            return out

    def register_campaign(self, key, name, case_version_ids):
        if not case_version_ids or len(set(case_version_ids)) != len(case_version_ids):
            raise QualityError("INVALID_CAMPAIGN_MEMBERS")
        digest = fingerprint([str(x) for x in case_version_ids])
        with self.database.unit_of_work() as u:
            selected = [self._one(u.session, versions, vid) for vid in case_version_ids]
            stages = {v["definition"]["stage"] for v in selected}
            if not key.startswith("fresh-holdout-"):
                # New relevant campaign versions cannot omit a promoted incident.
                required = u.session.execute(select(cases).where(cases.c.lifecycle == "ACTIVE").order_by(cases.c.key)).mappings().all()
                for c in required:
                    if Cohort.REGRESSION not in c["cohorts"]:
                        continue
                    v = u.session.execute(select(versions).where(versions.c.case_id == c["id"])
                        .order_by(versions.c.version.desc()).limit(1)).mappings().one()
                    if (key == "core-production-v1" or v["definition"]["stage"] in stages) and v["id"] not in case_version_ids:
                        case_version_ids = [*case_version_ids, v["id"]]
            cohort_snapshot = {vid: list(self._one(u.session, cases,
                self._one(u.session, versions, vid)["case_id"])["cohorts"]) for vid in case_version_ids}
            digest = fingerprint([{ "case_version_id": str(x), "cohorts": cohort_snapshot[x]} for x in case_version_ids])
            # Serializes versions of the same campaign without locking owner state.
            u.session.execute(select(func.pg_advisory_xact_lock(
                int(fingerprint(key)[:15], 16))))
            prior = u.session.execute(select(campaigns).where(campaigns.c.key == key,
                campaigns.c.fingerprint == digest)).mappings().first()
            if prior:
                return dict(prior)
            number = 1 + (u.session.scalar(select(func.max(campaigns.c.version)).where(
                campaigns.c.key == key)) or 0)
            cid = uuid4()
            u.session.execute(insert(campaigns).values(id=cid, key=key, name=name,
                version=number, fingerprint=digest))
            for i, vid in enumerate(case_version_ids):
                self._one(u.session, versions, vid)
                u.session.execute(insert(members).values(campaign_id=cid, case_version_id=vid, ordinal=i, cohorts=cohort_snapshot[vid]))
            u.commit()
            return self._one(u.session, campaigns, cid)

    def campaigns(self):
        with self.database.unit_of_work() as u:
            out = []
            for c in u.session.execute(select(campaigns).order_by(campaigns.c.created_at.desc())).mappings():
                ids = u.session.scalars(select(members.c.case_version_id).where(
                    members.c.campaign_id == c["id"]).order_by(members.c.ordinal)).all()
                out.append({**dict(c), "case_version_ids": ids})
            return out

    def configuration(self):
        s = self.settings
        return {"version": "quality-policy-v1", "runtime_profile": s.runtime_profile,
            "model": s.native_executor_inference_model or "UNCONFIGURED",
            "provider": s.native_executor_inference_provider,
            "search_provider": s.web_search_provider, "owner_runtime_mode": s.owner_runtime_mode,
            "wic_mode": s.wic_runtime_mode, "wic_model": s.wic_provider_model,
            "wic_provider": s.wic_provider_adapter, "conversation_model": s.conversation_provider_model,
            "verification_adapter": s.verification_adapter, "executor_adapter": s.executor_adapter}

    def request_run(self, request, actor):
        if not self.settings.runtime_revision:
            raise QualityError("WATT_VERSION_NOT_BOUND")
        config = self.configuration()
        with self.database.unit_of_work() as u:
            campaign = self._one(u.session, campaigns, request.campaign_id)
            selected_ids = list(u.session.scalars(select(members.c.case_version_id).where(
                members.c.campaign_id == campaign["id"])))
            selected = [self._one(u.session, versions, vid) for vid in selected_ids]
            stages = {v["definition"]["stage"] for v in selected}
            if not campaign["key"].startswith("fresh-holdout-"):
                for c in u.session.execute(select(cases).where(cases.c.lifecycle == "ACTIVE")).mappings():
                    if Cohort.REGRESSION not in c["cohorts"]:
                        continue
                    v = u.session.execute(select(versions).where(versions.c.case_id == c["id"])
                        .order_by(versions.c.version.desc()).limit(1)).mappings().one()
                    if (campaign["key"] == "core-production-v1" or v["definition"]["stage"] in stages) and v["id"] not in selected_ids:
                        raise QualityError("CAMPAIGN_REGRESSION_VERSION_STALE")
            if bool(request.experiment_id) != bool(request.variant_key):
                raise QualityError("EXACT_EXPERIMENT_VARIANT_REQUIRED")
            if request.experiment_id:
                e = self._one(u.session, experiments, request.experiment_id)
                variant = next((v for v in e["definition"]["variants"]
                    if v["key"] == request.variant_key), None)
                if not variant:
                    raise QualityError("UNKNOWN_EXPERIMENT_VARIANT")
                config = {**config, "experiment_variant": variant}
            rid = uuid4()
            u.session.execute(insert(runs).values(id=rid, campaign_id=request.campaign_id,
                experiment_id=request.experiment_id, variant_key=request.variant_key,
                watt_revision=self.settings.runtime_revision, policy_fingerprint=fingerprint(config),
                configuration=config, state="QUEUED", authority_identity=actor))
            u.commit()
            return self._one(u.session, runs, rid)

    def claim_run(self):
        with self.database.unit_of_work() as u:
            # One isolated recipe database has one durable qualification slot.
            u.session.execute(select(func.pg_advisory_xact_lock(690106)))
            # A killed recipe may have partially written only its isolated test DB.
            expired = u.session.execute(select(runs).where(runs.c.state == "RUNNING",
                runs.c.lease_expires_at < now()).with_for_update(skip_locked=True)).mappings().all()
            for r in expired:
                u.session.execute(update(attempts).where(attempts.c.campaign_run_id == r["id"],
                    attempts.c.state == "RUNNING").values(state="INTERRUPTED", finished_at=now()))
                u.session.execute(update(runs).where(runs.c.id == r["id"]).values(state="QUEUED"))
            if u.session.scalar(select(func.count()).select_from(runs).where(runs.c.state == "RUNNING")):
                u.commit()
                return None
            r = u.session.execute(select(runs).where(runs.c.state == "QUEUED")
                .order_by(runs.c.created_at).limit(1).with_for_update(skip_locked=True)).mappings().first()
            if r is None:
                u.commit()
                return None
            if r["watt_revision"] != self.settings.runtime_revision:
                u.session.execute(update(runs).where(runs.c.id == r["id"]).values(state="BLOCKED", finished_at=now()))
                u.commit()
                return None
            token = uuid4()
            u.session.execute(update(runs).where(runs.c.id == r["id"]).values(state="RUNNING",
                lease_token=token, lease_expires_at=now() + timedelta(minutes=30)))
            u.commit()
            return self._one(u.session, runs, r["id"])

    def run_members(self, run_id):
        with self.database.unit_of_work() as u:
            r = self._one(u.session, runs, run_id)
            return [dict(x) for x in u.session.execute(select(versions).join(members,
                members.c.case_version_id == versions.c.id).where(
                members.c.campaign_id == r["campaign_id"]).order_by(members.c.ordinal)).mappings()]

    def begin_case(self, run, version_id):
        with self.database.unit_of_work() as u:
            current = self._one(u.session, runs, run["id"], lock=True)
            if current["lease_token"] != run["lease_token"] or current["state"] != "RUNNING":
                raise QualityError("QUALITY_LEASE_FENCED")
            previous = u.session.execute(select(attempts).where(attempts.c.campaign_run_id == run["id"],
                attempts.c.case_version_id == version_id).order_by(attempts.c.attempt.desc()).limit(1)).mappings().first()
            if previous and previous["state"] in {"PASS", "FAIL", "BLOCKED"}:
                return None
            aid = uuid4()
            number = 1 if previous is None else previous["attempt"] + 1
            if number > 2:
                raise QualityError("QUALITY_RETRY_BUDGET_EXHAUSTED")
            u.session.execute(insert(attempts).values(id=aid, campaign_run_id=run["id"],
                case_version_id=version_id, attempt=number, state="RUNNING", lineage={}))
            u.session.execute(update(runs).where(runs.c.id == run["id"]).values(
                lease_expires_at=now() + timedelta(minutes=30)))
            u.commit()
            return aid

    def finish_case(self, run, attempt_id, results, lineage, elapsed):
        results = tuple(Evaluation.model_validate(r) for r in results)
        verdict = objective_verdict(results)
        if verdict == "UNKNOWN":
            verdict = "BLOCKED"
        divergence = earliest_divergence(results)
        with self.database.unit_of_work() as u:
            current = self._one(u.session, runs, run["id"], lock=True)
            if current["lease_token"] != run["lease_token"] or current["state"] != "RUNNING":
                raise QualityError("QUALITY_LEASE_FENCED")
            a = self._one(u.session, attempts, attempt_id, lock=True)
            if a["campaign_run_id"] != run["id"] or a["state"] != "RUNNING":
                raise QualityError("QUALITY_CASE_NOT_RUNNING")
            for e in results:
                u.session.execute(insert(evaluations).values(id=uuid4(), case_run_id=attempt_id,
                    evaluator=e.evaluator.value, outcome=e.outcome, record=json_record(e)))
                if e.evaluator in {Evaluator.DETERMINISTIC, Evaluator.RUNTIME, Evaluator.GUARDIAN} and e.outcome in {"FAIL", "BLOCKED"}:
                    # Common owner + typed error + exact oracle identify a cluster;
                    # model prose is never the clustering key.
                    signature = fingerprint({"stage": e.stage, "code": e.finding_code,
                        "oracle": e.details.get("oracle_id"), "evaluator": e.evaluator,
                        "uncertain_case": None if e.finding_code else str(a["case_version_id"])})
                    u.session.execute(insert(findings).values(id=uuid4(), case_run_id=attempt_id,
                        cluster_key=signature, stage=e.stage, finding_code=e.finding_code or "UNATTRIBUTED_FAILURE",
                        certainty="OBSERVED" if e.stage else "UNKNOWN", state="OPEN", evidence_refs=list(e.evidence_refs)))
            u.session.execute(update(attempts).where(attempts.c.id == attempt_id).values(
                state=verdict, lineage={**lineage, "divergence": divergence},
                elapsed_seconds=elapsed, finished_at=now()))
            u.commit()

    def finish_run(self, run):
        with self.database.unit_of_work() as u:
            current = self._one(u.session, runs, run["id"], lock=True)
            if current["lease_token"] != run["lease_token"]:
                raise QualityError("QUALITY_LEASE_FENCED")
            expected = u.session.scalar(select(func.count()).select_from(members).where(
                members.c.campaign_id == current["campaign_id"]))
            latest = u.session.execute(select(attempts).where(attempts.c.campaign_run_id == run["id"])
                .distinct(attempts.c.case_version_id).order_by(attempts.c.case_version_id,
                    attempts.c.attempt.desc())).mappings().all()
            states = [r["state"] for r in latest]
            status = "FAIL" if "FAIL" in states else "PASS" if len(latest) == expected and all(
                x == "PASS" for x in states) else "BLOCKED"
            u.session.execute(update(runs).where(runs.c.id == run["id"]).values(
                state=status, finished_at=now(), lease_expires_at=None))
            u.commit()
            return self._one(u.session, runs, run["id"])

    def run_detail(self, rid):
        with self.database.unit_of_work() as u:
            r = self._one(u.session, runs, rid)
            results = []
            for a in u.session.execute(select(attempts).where(attempts.c.campaign_run_id == rid)
                    .order_by(attempts.c.created_at)).mappings():
                c = self._one(u.session, versions, a["case_version_id"])
                row = self._one(u.session, cases, c["case_id"])
                es = u.session.scalars(select(evaluations.c.record).where(
                    evaluations.c.case_run_id == a["id"])).all()
                sealed = Cohort.FRESH_HOLDOUT in row["cohorts"]
                results.append({**dict(a), "case_key": row["key"], "title": c["definition"]["title"],
                    "evaluations": [{k: v for k, v in e.items() if not sealed or k != "details"} for e in es],
                    "lineage": {"sealed": True} if sealed else a["lineage"]})
            return {**r, "cases": results}

    def recent_runs(self):
        with self.database.unit_of_work() as u:
            return [dict(r) for r in u.session.execute(select(runs).order_by(
                runs.c.created_at.desc()).limit(30)).mappings()]

    def clusters(self):
        with self.database.unit_of_work() as u:
            rows = u.session.execute(select(findings).order_by(findings.c.created_at)).mappings().all()
            out = {}
            for f in rows:
                a = self._one(u.session, attempts, f["case_run_id"])
                v = self._one(u.session, versions, a["case_version_id"])
                item = out.setdefault(f["cluster_key"], {"key": f["cluster_key"], "stage": f["stage"],
                    "finding_code": f["finding_code"], "first_seen": f["created_at"], "last_seen": f["created_at"],
                    "occurrence_count": 0, "affected_cases": [], "findings": [], "closure_state": "OPEN",
                    "regression_status": "NOT_PROMOTED"})
                item["last_seen"] = f["created_at"]
                item["occurrence_count"] += 1
                item["affected_cases"] = sorted(set(item["affected_cases"]) | {str(v["case_id"])})
                item["findings"].append(str(f["id"]))
                if f["state"] == "CLOSED":
                    item["closed_occurrences"] = item.get("closed_occurrences", 0) + 1
                if f["regression_case_id"]:
                    item["regression_status"] = "PERMANENT_CASE"
            for item in out.values():
                item["closure_state"] = "CLOSED" if item.get("closed_occurrences", 0) == item["occurrence_count"] else "OPEN"
            return list(out.values())

    def promote_regression(self, fid, actor):
        with self.database.unit_of_work() as u:
            f = self._one(u.session, findings, fid, lock=True)
            a = self._one(u.session, attempts, f["case_run_id"])
            v = self._one(u.session, versions, a["case_version_id"])
            c = self._one(u.session, cases, v["case_id"], lock=True)
            if Cohort.FRESH_HOLDOUT in c["cohorts"]:
                raise QualityError("HOLDOUT_CANNOT_ENTER_OPTIMIZATION")
            u.session.execute(update(cases).where(cases.c.id == c["id"]).values(
                cohorts=sorted(set(c["cohorts"]) | {Cohort.REGRESSION.value})))
            u.session.execute(update(findings).where(findings.c.id == fid).values(regression_case_id=c["id"],
                regression_promotion={"authority_identity": actor, "created_at": now().isoformat(),
                    "source_finding_id": str(fid), "case_identity_preserved": True}))
            u.commit()
            return {"case_id": c["id"], "finding_id": fid, "authority_identity": actor,
                "status": "PERMANENT_REGRESSION", "same_case_identity": True}

    def create_experiment(self, request: ExperimentRequest, actor):
        with self.database.unit_of_work() as u:
            c = self._one(u.session, cases, request.case_id, lock=True)
            if Cohort.FRESH_HOLDOUT in c["cohorts"]:
                raise QualityError("HOLDOUT_CANNOT_ENTER_OPTIMIZATION")
            v = u.session.execute(select(versions).where(versions.c.case_id == c["id"])
                .order_by(versions.c.version.desc()).limit(1)).mappings().one()
            number = 1 + (u.session.scalar(select(func.max(experiments.c.version)).where(
                experiments.c.case_id == c["id"])) or 0)
            eid = uuid4()
            u.session.execute(insert(experiments).values(id=eid, case_id=c["id"], case_version_id=v["id"],
                version=number, fingerprint=fingerprint(json_record(request)), definition=json_record(request),
                authority_identity=actor))
            u.commit()
            result = self._one(u.session, experiments, eid)
        campaign = self.register_campaign("experiment-" + str(eid), request.name, [result["case_version_id"]])
        return {**result, "campaign_id": campaign["id"]}

    def preference(self, request: PreferenceRequest, actor):
        with self.database.unit_of_work() as u:
            e = self._one(u.session, experiments, request.experiment_id)
            keys = {v["key"] for v in e["definition"]["variants"]}
            if (len(request.ranking) != len(set(request.ranking)) or set(request.ranking) != keys
                or set(request.acceptability) != keys or set(request.case_run_ids) != keys):
                raise QualityError("EXACT_ARENA_CANDIDATES_REQUIRED")
            provenance = {}
            for key, aid in request.case_run_ids.items():
                a = self._one(u.session, attempts, aid)
                r = self._one(u.session, runs, a["campaign_run_id"])
                if (a["case_version_id"] != e["case_version_id"] or r["experiment_id"] != e["id"]
                    or r["variant_key"] != key or a["state"] not in {"PASS", "FAIL", "BLOCKED"}):
                    raise QualityError("ARENA_EVIDENCE_MISMATCH")
                provenance[key] = {"case_run_id": str(aid), "campaign_run_id": str(r["id"]),
                    "watt_revision": r["watt_revision"], "policy_fingerprint": r["policy_fingerprint"],
                    "configuration": r["configuration"], "lineage": a["lineage"], "objective_state": a["state"]}
            pid = uuid4()
            record = {**json_record(request), "candidate_provenance": provenance,
                "objective_override": False, "winner": request.ranking[0]}
            u.session.execute(insert(preferences).values(id=pid, experiment_id=e["id"],
                case_id=e["case_id"], record=record, authority_identity=actor))
            for key, aid in request.case_run_ids.items():
                judgment = Evaluation(evaluator=Evaluator.HUMAN,
                    outcome="PREFERRED" if key == request.ranking[0] else "REJECTED",
                    evidence_refs=("quality:preference:" + str(pid),), evaluator_version="human-preference-v1",
                    details={"confidence": request.confidence, "acceptable": request.acceptability[key],
                        "authority_identity": actor, "objective_override": False})
                u.session.execute(insert(evaluations).values(id=uuid4(), case_run_id=aid,
                    evaluator=judgment.evaluator, outcome=judgment.outcome, record=json_record(judgment)))
            u.commit()
            return self._one(u.session, preferences, pid)

    def attribute(self, request: AttributionRequest, actor):
        with self.database.unit_of_work() as u:
            table = preferences if request.source_kind == "PREFERENCE" else findings
            source = self._one(u.session, table, request.source_id)
            if request.source_kind == "PREFERENCE":
                cid = source["case_id"]
            else:
                a = self._one(u.session, attempts, source["case_run_id"])
                cid = self._one(u.session, versions, a["case_version_id"])["case_id"]
            c = self._one(u.session, cases, cid)
            if Cohort.FRESH_HOLDOUT in c["cohorts"]:
                raise QualityError("HOLDOUT_CANNOT_ENTER_OPTIMIZATION")
            ids = []
            for owner in set(request.owners):
                sid = uuid4()
                u.session.execute(insert(signals).values(id=sid, case_id=cid,
                    source_kind=request.source_kind, source_id=request.source_id, owner=owner.value,
                    record={**json_record(request), "interpretation": "HYPOTHESIS", "changes_production": False},
                    authority_identity=actor))
                ids.append(sid)
            u.commit()
            return {"learning_signal_ids": ids, "changes_production": False}

    def promote(self, request: PromotionRequest, actor):
        with self.database.unit_of_work() as u:
            e = self._one(u.session, experiments, request.experiment_id)
            if request.variant_key not in {v["key"] for v in e["definition"]["variants"]}:
                raise QualityError("UNKNOWN_EXPERIMENT_VARIANT")
            cohorts = set()
            version = None
            config_digest = None
            for rid in request.campaign_run_ids:
                r = self._one(u.session, runs, rid)
                if (r["state"] != "PASS" or r["experiment_id"] != e["id"]
                    or r["variant_key"] != request.variant_key):
                    raise QualityError("PROMOTION_REQUIRES_EXACT_QUALIFIED_EXPERIMENT")
                if version is not None and version != r["watt_revision"]:
                    raise QualityError("PROMOTION_VERSION_MISMATCH")
                version = r["watt_revision"]
                if config_digest is not None and config_digest != r["policy_fingerprint"]:
                    raise QualityError("PROMOTION_CONFIGURATION_MISMATCH")
                config_digest = r["policy_fingerprint"]
                for member in u.session.execute(select(members).where(
                        members.c.campaign_id == r["campaign_id"])).mappings():
                    v = self._one(u.session, versions, member["case_version_id"])
                    c = self._one(u.session, cases, v["case_id"])
                    # Cohorts used for qualification come from the pinned version,
                    # never a later mutable relabeling of a Case.
                    declared = set(member["cohorts"])
                    if Cohort.FRESH_HOLDOUT in declared and v["created_at"] <= e["created_at"]:
                        raise QualityError("PROMOTION_HOLDOUT_NOT_FRESH")
                    cohorts.update(declared)
            if not {Cohort.GOLDEN.value, Cohort.REGRESSION.value, Cohort.FRESH_HOLDOUT.value} <= cohorts:
                raise QualityError("PROMOTION_REQUIRES_GOLDEN_REGRESSION_FRESH_HOLDOUT")
            if version != self.settings.runtime_revision:
                raise QualityError("PROMOTION_WATT_VERSION_STALE")
            old = u.session.execute(select(promotions).where(promotions.c.experiment_id == e["id"],
                promotions.c.variant_key == request.variant_key)).mappings().first()
            if old:
                return dict(old)
            pid = uuid4()
            u.session.execute(insert(promotions).values(id=pid, experiment_id=e["id"],
                variant_key=request.variant_key, authority_identity=actor, record={**json_record(request),
                    "watt_revision": version, "decision": "APPROVED_FOR_GOVERNED_CHANGE",
                    "runtime_policy_changed": False}))
            u.commit()
            return self._one(u.session, promotions, pid)

    def arena(self):
        with self.database.unit_of_work() as u:
            return {name: [dict(r) for r in u.session.execute(select(table).order_by(
                table.c.created_at.desc()).limit(50)).mappings()] for name, table in
                (("experiments", experiments), ("preferences", preferences),
                 ("learning_signals", signals), ("promotion_decisions", promotions))}

    def llm_evaluation(self, aid):
        from spg.evaluation.judgment import evaluate
        with self.database.unit_of_work() as u:
            a = self._one(u.session, attempts, aid)
            if a["state"] not in {"PASS", "FAIL", "BLOCKED"}:
                raise QualityError("EVALUATION_REQUIRES_COMPLETED_OBSERVATION")
            v = self._one(u.session, versions, a["case_version_id"])
            c = self._one(u.session, cases, v["case_id"])
            if Cohort.FRESH_HOLDOUT in c["cohorts"]:
                raise QualityError("HOLDOUT_CANNOT_ENTER_OPTIMIZATION")
            observed = u.session.scalars(select(evaluations.c.record).where(
                evaluations.c.case_run_id == aid)).all()
        e = evaluate(self.settings, case_run_id=aid, case_definition=v["definition"], observed_results=observed)
        with self.database.unit_of_work() as u:
            u.session.execute(insert(evaluations).values(id=uuid4(), case_run_id=aid,
                evaluator=e.evaluator, outcome=e.outcome, record=json_record(e)))
            u.commit()
        return {"evaluation": json_record(e), "objective_state": a["state"], "objective_override": False}

    def guardian_evaluations(self):
        with self.database.unit_of_work() as u:
            return [dict(r) for r in u.session.execute(select(evaluations).where(
                evaluations.c.evaluator == Evaluator.GUARDIAN.value).order_by(
                evaluations.c.created_at.desc()).limit(30)).mappings()]

    def case_history(self, cid):
        from spg.infrastructure.persistence.evaluation_schema import evaluation_runs
        with self.database.unit_of_work() as u:
            c = self._one(u.session, cases, cid)
            vs = list(u.session.execute(select(versions).where(versions.c.case_id == cid)
                .order_by(versions.c.version)).mappings())
            ids = [v["id"] for v in vs]
            tested = [dict(r) for r in u.session.execute(select(attempts.c.id, attempts.c.campaign_run_id,
                attempts.c.case_version_id, attempts.c.state, attempts.c.created_at).where(
                attempts.c.case_version_id.in_(ids)).order_by(attempts.c.created_at.desc()).limit(100)).mappings()]
            legacy = []
            for r in u.session.execute(select(evaluation_runs).order_by(evaluation_runs.c.created_at.desc()).limit(50)).mappings():
                if any(x.get("case") in c["aliases"] for x in r["report"].get("cases", [])):
                    legacy.append({"owner_reference": "evaluation-run:" + str(r["id"]),
                        "watt_revision": r["revision"], "version": r["version"], "created_at": r["created_at"],
                        "qualification": r["qualification"], "historical_only": True})
            return {"case_id": cid, "versions": [{k: v[k] for k in ("id", "version", "fingerprint", "created_at")} for v in vs],
                "case_runs": tested, "legacy_owner_references": legacy}

    def close_finding(self, fid, request, actor):
        with self.database.unit_of_work() as u:
            f = self._one(u.session, findings, fid, lock=True)
            if f["state"] == "CLOSED":
                return f
            qualified = self._one(u.session, attempts, request.qualified_case_run_id)
            v = self._one(u.session, versions, qualified["case_version_id"])
            c = self._one(u.session, cases, v["case_id"])
            failed = self._one(u.session, attempts, f["case_run_id"])
            failed_version = self._one(u.session, versions, failed["case_version_id"])
            eligible = ((f["regression_case_id"] == c["id"] and Cohort.REGRESSION in c["cohorts"])
                or (Cohort.FRESH_HOLDOUT in c["cohorts"] and failed_version["case_id"] == c["id"]))
            if (not eligible or qualified["state"] != "PASS" or qualified["created_at"] <= f["created_at"]):
                raise QualityError("FINDING_CLOSURE_REQUIRES_LATER_QUALIFIED_REGRESSION")
            u.session.execute(update(findings).where(findings.c.id == fid).values(state="CLOSED",
                closure={**json_record(request), "authority_identity": actor, "created_at": now().isoformat()}))
            u.commit()
            return self._one(u.session, findings, fid)
