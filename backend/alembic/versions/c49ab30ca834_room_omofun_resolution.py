"""Keep the room's parsed work independent of its playing source."""
from alembic import op
import sqlalchemy as sa

revision = "c49ab30ca834"
down_revision = "b38fa2fb9723"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("room_settings", sa.Column("omofun_resolution", sa.JSON(), nullable=True))
    # Existing selected works become the initial parsed work, without modifying playback.
    op.execute("""UPDATE room_settings SET omofun_resolution = json_object(
        'work_id', json_extract(omofun_source, '$.omofun.work_id'),
        'state', 'ready', 'revision', 'migrated')
        WHERE json_extract(omofun_source, '$.omofun.work_id') IS NOT NULL""")


def downgrade():
    op.drop_column("room_settings", "omofun_resolution")
