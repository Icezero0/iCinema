"""Add provider configuration, stable source identities and bounded import jobs."""
from alembic import op
import sqlalchemy as sa

revision = "a61e3b842056"
down_revision = "f50d2a731945"
branch_labels = None
depends_on = None


def upgrade():
    providers = op.create_table("catalog_providers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("category", sa.String(32), sa.ForeignKey("catalog_categories.code"), nullable=False),
        sa.Column("upstream_category", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("next_request_at", sa.Float(), nullable=False))
    op.bulk_insert(providers, [dict(id=1, code="jinying", name="金鹰资源", enabled=True,
        endpoint="https://jyzyapi.com/provide/vod/from/jinyingm3u8/at/json",
        category="japanese_animation", upstream_category=25, version=1, next_request_at=0.0)])
    op.create_table("catalog_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("catalog_providers.id"), nullable=False),
        sa.Column("upstream_id", sa.Integer(), nullable=False),
        sa.Column("content_id", sa.Integer(), sa.ForeignKey("catalog_contents.id"), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider_id", "upstream_id", name="uq_catalog_source_identity"))
    op.create_index("ix_catalog_sources_content_id", "catalog_sources", ["content_id"])
    op.create_table("catalog_import_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("catalog_providers.id"), nullable=False),
        sa.Column("provider_version", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("start_page", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("lease_token", sa.String(36), nullable=False),
        sa.Column("lease_until", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sqlite_autoincrement=True)
    op.create_index("uq_catalog_active_import", "catalog_import_jobs", ["provider_id"], unique=True,
                    sqlite_where=sa.text("status IN ('queued', 'running')"))


def downgrade():
    op.drop_table("catalog_import_jobs")
    op.drop_table("catalog_sources")
    op.drop_table("catalog_providers")
