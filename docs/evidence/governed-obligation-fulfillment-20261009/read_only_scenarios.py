"""Read persisted original N1 scenario identities without mutating Work Reality."""

import json
from sqlalchemy import create_engine, text
from spg.config import Settings


PREFIXES = {"G0": "6899ad34%", "G3": "e50a9566%", "G4": "c616ab6b%"}


def main():
    engine = create_engine(Settings().database_url)
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        for case, prefix in PREFIXES.items():
            row = connection.execute(text("""
                SELECT pw.id AS work_id, wr.id AS revision_id,
                       wr.revision_number, wr.source_revision,
                       wr.engineering_semantic_facts, wr.constraints,
                       pwu.id AS pwu_id, pwu.completion_contract
                FROM product_works pw
                JOIN work_reality_revisions wr
                  ON wr.id = pw.current_work_reality_revision_id
                LEFT JOIN work_runtime_bindings b ON b.work_id = pw.id
                LEFT JOIN production_work_units pwu ON pwu.id = b.work_unit_id
                WHERE pw.id::text LIKE :prefix
                ORDER BY b.cycle_number DESC NULLS LAST LIMIT 1
            """), {"prefix": prefix}).mappings().first()
            if row is None:
                print(json.dumps({"case": case, "found": False}))
                continue
            facts = row["engineering_semantic_facts"] or []
            completion = row["completion_contract"] or {}
            task = completion.get("task_contract") or {}
            lineage = task.get("decision_context") or {}
            protected = lineage.get("protected_obligations") or []
            bindings = completion.get("fulfillment_bindings") or []
            print(json.dumps({
                "case": case, "found": True, "work_id": str(row["work_id"]),
                "work_reality_revision_id": str(row["revision_id"]),
                "revision_number": row["revision_number"],
                "source_revision": row["source_revision"],
                "fact_count": len(facts),
                "fact_ids": [str(fact.get("id") or fact.get("fact_id")) for fact in facts],
                "fact_keys": sorted(facts[0]) if facts else [],
                "work_constraint_count": len(row["constraints"] or []),
                "pwu_id": str(row["pwu_id"]) if row["pwu_id"] else None,
                "protected_obligation_count": len(protected),
                "fulfillment_binding_count": len(bindings),
            }, sort_keys=True))


if __name__ == "__main__":
    main()
