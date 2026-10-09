"""Read only the agent-authored last G0 fixture's Fact and IR routing basis."""

import json
from sqlalchemy import create_engine, text
from spg.config import Settings


WORK_ID = "84d7f3a9-b90c-5341-a007-2661fc6399b3"


def main():
    engine = create_engine(Settings().database_url)
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        row = connection.execute(text("""
            SELECT wr.engineering_semantic_facts, wr.constraints, ia.semantic_ir
            FROM product_works pw
            JOIN work_reality_revisions wr ON wr.id = pw.current_work_reality_revision_id
            LEFT JOIN interaction_assessments ia ON ia.id = wr.source_assessment_id
            WHERE pw.id = :work_id
        """), {"work_id": WORK_ID}).mappings().one()
    ir = row["semantic_ir"] or {}
    legacy = ir.get("legacy_typed_projection") or {}
    print(json.dumps({
        "work_id": WORK_ID,
        "facts": [{
            "id": fact.get("id"), "subject": fact.get("subject"),
            "relation": fact.get("relation"), "value": fact.get("value"),
            "qualifiers": fact.get("qualifiers"),
        } for fact in row["engineering_semantic_facts"]],
        "work_constraints": row["constraints"],
        "ir_keys": sorted(ir),
        "semantic_fact_candidates": [{
            "subject": item.get("subject"), "relation": item.get("relation"),
            "value": item.get("value")}
            for item in (ir.get("semantic_fact_candidates") or [])],
        "ir_items": [{
            "subject": item.get("subject"), "statement": item.get("statement"),
            "kind": item.get("kind")}
            for item in (ir.get("items") or [])],
        "legacy_keys": sorted(legacy),
        "legacy_current_production": [{
            "exclusions": goal.get("exclusions"),
            "delivery_authorized": goal.get("delivery_authorized"),
            "preview_required": goal.get("preview_required"),
        } for goal in legacy.get("current_production", [])],
        "current_production": [{
            "exclusions": goal.get("exclusions"),
            "delivery_authorized": goal.get("delivery_authorized"),
            "preview_required": goal.get("preview_required"),
        } for goal in ir.get("current_production", [])],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
