"""prevent deleted room data reuse

Revision ID: a71c5e4d2b90
Revises: 4c2d8b7e9a10
Create Date: 2026-09-15 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a71c5e4d2b90"
down_revision: str | None = "4c2d8b7e9a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _delete_stale_room_rows() -> None:
    # Legacy joined_at used datetime.now(...) as a value at module import, not
    # a callable. A valid membership can therefore predate its room. Neither
    # deleting nor preserving a suspected reused-ID membership is safe without
    # reviewing a backup. Fail before any cleanup rather than guessing access.
    ambiguous = op.get_bind().execute(sa.text("""
        SELECT COUNT(*) FROM room_members
        JOIN rooms ON rooms.id = room_members.room_id
        WHERE rooms.created_at IS NOT NULL
          AND room_members.joined_at IS NOT NULL
          AND room_members.joined_at < rooms.created_at
    """)).scalar_one()
    if ambiguous:
        raise RuntimeError(
            "Ambiguous legacy room memberships: joined_at may be the old server "
            "startup time. No cleanup performed. Review memberships against a "
            "pre-upgrade backup before retrying migration a71c5e4d2b90."
        )
    # Foreign keys were previously disabled for SQLite connections. Remove both
    # true orphans and rows inherited when a deleted room ID was reused.
    op.execute(
        """
        DELETE FROM message_resource_refs
        WHERE message_id IN (
            SELECT messages.id
            FROM messages
            LEFT JOIN rooms ON rooms.id = messages.room_id
            WHERE rooms.id IS NULL
               OR (
                   rooms.created_at IS NOT NULL
                   AND messages.created_at < rooms.created_at
               )
        )
        """
    )
    op.execute(
        """
        DELETE FROM messages
        WHERE NOT EXISTS (
            SELECT 1 FROM rooms WHERE rooms.id = messages.room_id
        )
           OR EXISTS (
            SELECT 1
            FROM rooms
            WHERE rooms.id = messages.room_id
              AND rooms.created_at IS NOT NULL
              AND messages.created_at < rooms.created_at
        )
        """
    )
    op.execute(
        """
        DELETE FROM message_resource_refs
        WHERE NOT EXISTS (
            SELECT 1 FROM messages WHERE messages.id = message_resource_refs.message_id
        )
        """
    )
    op.execute(
        """
        DELETE FROM room_join_requests
        WHERE NOT EXISTS (
            SELECT 1 FROM rooms WHERE rooms.id = room_join_requests.room_id
        )
           OR EXISTS (
            SELECT 1
            FROM rooms
            WHERE rooms.id = room_join_requests.room_id
              AND rooms.created_at IS NOT NULL
              AND room_join_requests.created_at IS NOT NULL
              AND room_join_requests.created_at < rooms.created_at
        )
        """
    )
    op.execute(
        """
        DELETE FROM room_members
        WHERE NOT EXISTS (
            SELECT 1 FROM rooms WHERE rooms.id = room_members.room_id
        )
           OR EXISTS (
            SELECT 1
            FROM rooms
            WHERE rooms.id = room_members.room_id
              AND rooms.created_at IS NOT NULL
              AND room_members.joined_at IS NOT NULL
              AND room_members.joined_at < rooms.created_at
        )
        """
    )
    op.execute(
        """
        DELETE FROM room_settings
        WHERE NOT EXISTS (
            SELECT 1 FROM rooms WHERE rooms.id = room_settings.room_id
        )
           OR EXISTS (
            SELECT 1
            FROM rooms
            WHERE rooms.id = room_settings.room_id
              AND rooms.created_at IS NOT NULL
              AND room_settings.created_at IS NOT NULL
              AND room_settings.created_at < rooms.created_at
        )
        """
    )


def upgrade() -> None:
    _delete_stale_room_rows()

    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(
            "rooms",
            schema=None,
            recreate="always",
            table_kwargs={"sqlite_autoincrement": True},
        ):
            pass


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(
            "rooms",
            schema=None,
            recreate="always",
        ):
            pass
