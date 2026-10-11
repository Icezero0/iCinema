"""Persist only the selected Bilibili video and part identity for rooms."""

from alembic import op
import sqlalchemy as sa

revision = "7e28c32a16b0"
down_revision = "d50bc41db945"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("room_settings", sa.Column("bilibili_source", sa.JSON(), nullable=True))


def downgrade():
    op.execute("UPDATE room_settings SET selected_room_video_source_type='external_url' WHERE selected_room_video_source_type='bilibili'")
    op.drop_column("room_settings", "bilibili_source")
