"""Restore missing owner memberships using the room's authoritative owner."""
from alembic import op

revision = "f16d80d97501"
down_revision = "e05c7fc86490"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        INSERT INTO room_members (room_id, user_id, role)
        SELECT rooms.id, rooms.owner_id, 'owner' FROM rooms
        WHERE NOT EXISTS (
            SELECT 1 FROM room_members
            WHERE room_members.room_id = rooms.id AND room_members.user_id = rooms.owner_id
        )
    """)
    op.execute("""
        UPDATE room_members SET role = 'owner'
        WHERE EXISTS (
            SELECT 1 FROM rooms
            WHERE rooms.id = room_members.room_id AND rooms.owner_id = room_members.user_id
        ) AND role != 'owner'
    """)


def downgrade():
    # Keep repaired memberships: removing them would lock owners out again.
    pass
