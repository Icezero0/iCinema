"""Add manually managed Japanese animation catalog and audit trail."""
from alembic import op
import sqlalchemy as sa

revision = "c27a9d40e612"
down_revision = "b19f06a8c321"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("catalog_contents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("aliases", sa.String(1000), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("region", sa.String(16), nullable=False),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.Column("disabled_reason", sa.String(500), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sqlite_autoincrement=True)
    op.create_index("ix_catalog_contents_title", "catalog_contents", ["title"])
    op.create_index("ix_catalog_contents_status", "catalog_contents", ["status"])
    op.create_table("catalog_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_id", sa.Integer(), sa.ForeignKey("catalog_contents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_catalog_audits_content_id", "catalog_audits", ["content_id"])


def downgrade():
    op.drop_table("catalog_audits")
    op.drop_table("catalog_contents")
