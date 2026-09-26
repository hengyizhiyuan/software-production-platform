"""Persist actor, organization membership and resource access.

Revision ID: 20260926_52
Revises: 20260926_51
"""

from alembic import op
import sqlalchemy as sa

revision = "20260926_52"
down_revision = "20260926_51"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("authority_actors",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now()))
    op.create_table("authority_memberships",
        sa.Column("organization_id", sa.String(255), primary_key=True),
        sa.Column("actor_id", sa.String(255),
            sa.ForeignKey("authority_actors.id"), primary_key=True),
        sa.Column("role", sa.String(32), nullable=False))
    op.create_table("authority_resource_access",
        sa.Column("resource_kind", sa.String(32), primary_key=True),
        sa.Column("resource_id", sa.String(64), primary_key=True),
        sa.Column("actor_id", sa.String(255),
            sa.ForeignKey("authority_actors.id"), primary_key=True),
        sa.Column("role", sa.String(32), nullable=False))
    op.execute("INSERT INTO authority_actors (id, kind) VALUES ('human:owner', 'HUMAN')")
    op.execute("INSERT INTO authority_memberships (organization_id, actor_id, role) VALUES ('organization:default', 'human:owner', 'OWNER')")
    for kind, table, column in (
        ("work", "product_works", "id"),
        ("interaction", "product_interactions", "id"),
        ("repository", "engineering_resources", "id"),
        ("goal", "product_goals", "id"),
    ):
        op.execute(sa.text(
            "INSERT INTO authority_resource_access (resource_kind, resource_id, actor_id, role) "
            f"SELECT :kind, {column}::text, 'human:owner', 'OWNER' FROM {table}"
        ).bindparams(kind=kind))
        op.execute(sa.text(f"""
            CREATE OR REPLACE FUNCTION authority_grant_{kind}_owner() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN
                INSERT INTO authority_resource_access
                    (resource_kind, resource_id, actor_id, role)
                VALUES ('{kind}', NEW.{column}::text, 'human:owner', 'OWNER')
                ON CONFLICT DO NOTHING;
                RETURN NEW;
            END $$
        """))
        op.execute(sa.text(f"""
            CREATE TRIGGER authority_{kind}_owner_after_insert
            AFTER INSERT ON {table}
            FOR EACH ROW EXECUTE FUNCTION authority_grant_{kind}_owner()
        """))


def downgrade() -> None:
    for kind, table in (
        ("work", "product_works"),
        ("interaction", "product_interactions"),
        ("repository", "engineering_resources"),
        ("goal", "product_goals"),
    ):
        op.execute(sa.text(f"DROP TRIGGER authority_{kind}_owner_after_insert ON {table}"))
        op.execute(sa.text(f"DROP FUNCTION authority_grant_{kind}_owner()"))
    op.drop_table("authority_resource_access")
    op.drop_table("authority_memberships")
    op.drop_table("authority_actors")
