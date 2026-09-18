"""Independent on-demand Omofun snapshot cache."""
from alembic import op
import sqlalchemy as sa

revision = "a27e91ea8612"
down_revision = "f16d80d97501"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("omofun_cache",
        sa.Column("work_id", sa.String(20), primary_key=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parsed_at", sa.Float(), nullable=True),
        sa.Column("state", sa.String(16), nullable=False, server_default="empty"),
        sa.Column("error", sa.String(64), nullable=False, server_default=""),
        sa.Column("token", sa.String(32), nullable=False, server_default=""),
        sa.Column("lease_until", sa.Float(), nullable=False, server_default="0"),
        sa.Column("attempted_at", sa.Float(), nullable=False, server_default="0"),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_table("omofun_cache")
