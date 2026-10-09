"""Read-only snapshot of the last failed isolated G0 binding and IR constraint lineage."""

import json
from sqlalchemy import create_engine, text
from spg.config import Settings


def main():
    engine = create_engine(Settings().database_url)
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        row = connection.execute(text("""
            SELECT wr.id, wr.source_revision, wr.constraints, wr.source_assessment_id,
                   wr.source_record_ids,
                   ia.semantic_ir
            FROM product_works pw
            JOIN work_reality_revisions wr ON wr.id = pw.current_work_reality_revision_id
            LEFT JOIN interaction_assessments ia ON ia.id = wr.source_assessment_id
            WHERE pw.id = '84d7f3a9-b90c-5341-a007-2661fc6399b3'
        """)).mappings().one()
        binding = connection.execute(text("""
            SELECT binding_payload FROM native_attempt_bindings
            WHERE attempt_id = 'e3addc05-7ee4-49f4-9043-c69b6466bcf8'
        """)).scalar_one()
        allocated = connection.execute(text("""
            SELECT payload FROM execution_events
            WHERE attempt_id = 'e3addc05-7ee4-49f4-9043-c69b6466bcf8'
              AND event_type = 'ExecutionCapacityAllocated'
        """)).scalar_one()
    ir = row["semantic_ir"] or {}
    print(json.dumps({
        "revision": str(row["id"]), "source_revision": row["source_revision"],
        "source_assessment_id": str(row["source_assessment_id"]),
        "revision_source_record_ids": row["source_record_ids"],
        "constraints": row["constraints"],
        "ir_id": ir.get("id"), "source_record_id": ir.get("source_record_id"),
        "items": [{
            "item_id": item.get("item_id"), "kind": item.get("kind"),
            "subject": item.get("subject"), "statement": item.get("statement"),
            "provenance": item.get("provenance"),
            "production": item.get("production"),
            "confidence": item.get("confidence"),
        } for item in ir.get("items", [])],
        "clauses": [{
            "id": item.get("clause_id"), "source_record_id": item.get("source_record_id"),
            "source_text": item.get("source_text"),
            "semantic_item_ids": item.get("semantic_item_ids"),
            "polarity": item.get("polarity"), "requested_effects": item.get("requested_effects"),
        } for item in ir.get("clauses", [])],
        "binding_mounts": binding.get("workspace", {}).get("mounts"),
        "allocated_worker_id": allocated.get("worker_id"),
        "source_vector": binding.get("source_vector"),
    }, ensure_ascii=False, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
