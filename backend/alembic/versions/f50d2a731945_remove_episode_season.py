"""Treat separately named seasons as works, not episode attributes."""
from alembic import op
import sqlalchemy as sa

revision = "f50d2a731945"
down_revision = "e49c1f620834"
branch_labels = None
depends_on = None


def check_batch_connection():
    # The project's Alembic engine uses SQLite's default foreign_keys=OFF.
    # Refuse an externally configured FK-on connection: batch recreation could
    # otherwise cascade-delete playback mappings when dropping the old table.
    bind = op.get_bind()
    if bind.dialect.name == "sqlite" and bind.exec_driver_sql("PRAGMA foreign_keys").scalar():
        raise RuntimeError("Use the project's Alembic migration connection (SQLite foreign_keys=OFF).")


def upgrade():
    check_batch_connection()
    duplicate = op.get_bind().execute(sa.text("""
        SELECT content_id FROM catalog_episodes
        GROUP BY content_id, kind, number HAVING COUNT(*) > 1 LIMIT 1
    """)).first()
    if duplicate:
        raise RuntimeError(
            f"Work {duplicate[0]} has duplicate episode numbers across seasons. "
            "Separate these into named works before removing season; no episodes were modified."
        )
    with op.batch_alter_table("catalog_episodes", table_kwargs={"sqlite_autoincrement": True}) as batch:
        batch.drop_constraint("uq_catalog_episode_identity", type_="unique")
        batch.drop_column("season")
        batch.create_unique_constraint("uq_catalog_episode_identity", ["content_id", "kind", "number"])


def downgrade():
    check_batch_connection()
    # Season values are intentionally removed; rollback restores the legacy default.
    op.add_column("catalog_episodes", sa.Column("season", sa.Integer(), nullable=False, server_default="1"))
    with op.batch_alter_table("catalog_episodes", table_kwargs={"sqlite_autoincrement": True}) as batch:
        batch.drop_constraint("uq_catalog_episode_identity", type_="unique")
        batch.create_unique_constraint("uq_catalog_episode_identity", ["content_id", "season", "kind", "number"])
        batch.alter_column("season", server_default=None)
