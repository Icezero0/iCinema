"""Persist the selected Omofun playback snapshot independently of cache refresh."""
from alembic import op
import sqlalchemy as sa

revision = "b38fa2fb9723"
down_revision = "a27e91ea8612"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("room_settings", sa.Column("omofun_source", sa.JSON(), nullable=True))


def downgrade():
    op.execute("UPDATE room_settings SET selected_room_video_source_type='external_url' WHERE selected_room_video_source_type='omofun'")
    op.drop_column("room_settings", "omofun_source")
