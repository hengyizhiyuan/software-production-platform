"""Snapshot the new isolated GOF Work outcomes from persisted owner records."""

import json
from sqlalchemy import create_engine, text
from spg.config import Settings


TRIALS = (
    ("e3de9bf", "32d556bb-a940-5f7d-b760-c1093ad256fe"),
    ("e3de9bf", "5317c219-8167-581c-aa03-651dd6a7a83c"),
    ("3a00dfc", "8f8c379b-a9be-55c3-9323-a06fc629a96a"),
    ("84d16b1", "84d7f3a9-b90c-5341-a007-2661fc6399b3"),
)


def main():
    engine = create_engine(Settings().database_url)
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        for image, work_id in TRIALS:
            rows = connection.execute(text("""
                SELECT pw.id AS work_id, pw.product_id, pw.condition,
                       pw.created_at, pw.current_work_reality_revision_id,
                       b.production_run_id, b.work_unit_id,
                       pwu.completion_contract,
                       ea.id AS attempt_id, nas.terminal_outcome,
                       (SELECT count(*) FROM baseline_candidates c
                        WHERE c.production_run_id = b.production_run_id) AS candidate_count,
                       (SELECT count(*) FROM verification_records v
                        WHERE v.production_run_id = b.production_run_id) AS verification_count
                FROM product_works pw
                LEFT JOIN work_runtime_bindings b ON b.work_id = pw.id
                LEFT JOIN execution_attempts ea ON ea.work_unit_id = b.work_unit_id
                LEFT JOIN production_work_units pwu ON pwu.id = b.work_unit_id
                LEFT JOIN native_attempt_states nas ON nas.attempt_id = ea.id
                WHERE pw.id = :work_id
                ORDER BY b.cycle_number DESC NULLS LAST, ea.generation DESC NULLS LAST
                LIMIT 1
            """), {"work_id": work_id}).mappings().first()
            if rows is None:
                print(json.dumps({"image": image, "work_id": work_id, "found": False}))
                continue
            event = None
            if rows["attempt_id"] is not None:
                event = connection.execute(text("""
                    SELECT id, payload, created_at FROM execution_events
                    WHERE attempt_id = :attempt AND event_type = 'ExecutionWorkspacePreflightRejected'
                    ORDER BY sequence DESC LIMIT 1
                """), {"attempt": rows["attempt_id"]}).mappings().first()
            print(json.dumps({
                "image": image,
                "work_id": str(rows["work_id"]),
                "product_id": str(rows["product_id"]),
                "created_at_utc": rows["created_at"].isoformat(),
                "condition": rows["condition"],
                "work_reality_revision_id": str(rows["current_work_reality_revision_id"]),
                "production_run_id": str(rows["production_run_id"]),
                "pwu_id": str(rows["work_unit_id"]),
                "attempt_id": str(rows["attempt_id"]),
                "terminal_outcome": rows["terminal_outcome"],
                "candidate_count": rows["candidate_count"],
                "verification_count": rows["verification_count"],
                "fulfillment_bindings": [{
                    "fact_id": item.get("fact_id"), "owner": item.get("owner"),
                    "phase": item.get("phase"), "evidence_method": item.get("evidence_method")}
                    for item in (rows["completion_contract"] or {}).get("fulfillment_bindings", [])],
                "preflight_event_id": str(event["id"]) if event else None,
                "preflight_failure": event["payload"].get("failure") if event else None,
                "preflight_at_utc": event["created_at"].isoformat() if event else None,
            }, sort_keys=True))


if __name__ == "__main__":
    main()
