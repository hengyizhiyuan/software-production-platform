"""Notify Work-scoped changes so the workspace can be pushed instead of polled.

Every insert/update on a table that carries Work progress raises one
`pg_notify('watt_work_changed', <work_id>)`. The payload is only an identity;
listeners re-read through the existing projections. Notifications are
delivered at commit, so a rolled-back write never reaches a client.
"""
from alembic import op

revision = "20261015_73"
down_revision = "20261007_72"
branch_labels = None
depends_on = None

CHANNEL = "watt_work_changed"
# Tables whose own work_id column names the changed Work.
DIRECT = ("executor_queue", "steering_plans", "steering_plan_revisions", "semantic_step_results",
          "self_refine_events", "work_convergence_observations", "work_delivery_manifests",
          "work_delivery_targets", "work_reality_revisions", "work_runtime_bindings",
          "remote_delivery_authorizations", "wic_human_realizations", "guided_design_agenda_revisions",
          "capability_gaps")


def upgrade():
    op.execute(f"""
        CREATE OR REPLACE FUNCTION watt_notify_work_changed() RETURNS trigger AS $$
        DECLARE target uuid;
        BEGIN
          IF TG_TABLE_NAME = 'product_works' THEN target := NEW.id;
          ELSIF TG_TABLE_NAME = 'product_interactions' THEN target := NEW.current_work_id;
          ELSIF TG_TABLE_NAME = 'interaction_turns' THEN
            SELECT current_work_id INTO target FROM product_interactions WHERE id = NEW.interaction_id;
          ELSIF TG_TABLE_NAME = 'native_attempt_states' THEN
            SELECT work_id INTO target FROM executor_queue WHERE attempt_id = NEW.attempt_id
              ORDER BY enqueued_at DESC LIMIT 1;
          ELSIF TG_TABLE_NAME = 'execution_events' THEN
            SELECT work_id INTO target FROM executor_queue WHERE pwu_id = NEW.pwu_id
              ORDER BY enqueued_at DESC LIMIT 1;
          ELSIF TG_TABLE_NAME = 'work_delivery_acceptances' THEN
            SELECT work_id INTO target FROM work_delivery_manifests WHERE id = NEW.manifest_id;
          ELSE target := NEW.work_id;
          END IF;
          IF target IS NOT NULL THEN
            PERFORM pg_notify('{CHANNEL}', target::text);
          END IF;
          RETURN NULL;
        END $$ LANGUAGE plpgsql;
    """)
    for table in (*DIRECT, "product_works", "product_interactions", "interaction_turns",
                  "native_attempt_states", "execution_events", "work_delivery_acceptances"):
        op.execute(f"""
            CREATE TRIGGER watt_notify_work_changed AFTER INSERT OR UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION watt_notify_work_changed();
        """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_executor_queue_pwu ON executor_queue (pwu_id, enqueued_at)")


def downgrade():
    for table in (*DIRECT, "product_works", "product_interactions", "interaction_turns",
                  "native_attempt_states", "execution_events", "work_delivery_acceptances"):
        op.execute(f"DROP TRIGGER IF EXISTS watt_notify_work_changed ON {table}")
    op.execute("DROP FUNCTION IF EXISTS watt_notify_work_changed()")
    op.execute("DROP INDEX IF EXISTS ix_executor_queue_pwu")
