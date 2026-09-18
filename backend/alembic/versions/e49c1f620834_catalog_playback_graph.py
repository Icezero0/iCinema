"""Add episodes, source lines and per-episode playback mappings."""
from alembic import op
import sqlalchemy as sa

revision = "e49c1f620834"
down_revision = "d38b0e51f723"
branch_labels = None
depends_on = None


def state_columns():
    return [sa.Column("disabled", sa.Boolean(), nullable=False),
            sa.Column("disabled_reason", sa.String(500), nullable=False)]


def upgrade():
    op.create_table("catalog_episodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_id", sa.Integer(), sa.ForeignKey("catalog_contents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        *state_columns(),
        sa.UniqueConstraint("content_id", "season", "kind", "number", name="uq_catalog_episode_identity"),
        sa.UniqueConstraint("id", "content_id", name="uq_catalog_episode_content"),
        sqlite_autoincrement=True)
    op.create_index("ix_catalog_episodes_content_id", "catalog_episodes", ["content_id"])
    op.create_table("catalog_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_id", sa.Integer(), sa.ForeignKey("catalog_contents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("source_key", sa.String(64), nullable=False),
        sa.Column("line_key", sa.String(64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        *state_columns(),
        sa.UniqueConstraint("content_id", "source_key", "line_key", name="uq_catalog_line_identity"),
        sa.UniqueConstraint("id", "content_id", name="uq_catalog_line_content"),
        sqlite_autoincrement=True)
    op.create_index("ix_catalog_lines_content_id", "catalog_lines", ["content_id"])
    op.create_table("catalog_playbacks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("episode_id", sa.Integer(), nullable=False),
        sa.Column("line_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(4096), nullable=False),
        sa.Column("media_type", sa.String(16), nullable=False),
        sa.Column("source_label", sa.String(255), nullable=False),
        *state_columns(),
        sa.ForeignKeyConstraint(["episode_id", "content_id"], ["catalog_episodes.id", "catalog_episodes.content_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["line_id", "content_id"], ["catalog_lines.id", "catalog_lines.content_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("episode_id", "line_id", name="uq_catalog_playback_mapping"),
        sqlite_autoincrement=True)
    op.create_index("ix_catalog_playbacks_content_id", "catalog_playbacks", ["content_id"])


def downgrade():
    op.drop_table("catalog_playbacks")
    op.drop_table("catalog_lines")
    op.drop_table("catalog_episodes")
