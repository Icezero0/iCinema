"""add room settings seek auto pause

Revision ID: 4c2d8b7e9a10
Revises: 3f6f0a9c2d18
Create Date: 2026-06-29 22:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "4c2d8b7e9a10"
down_revision: str | None = "3f6f0a9c2d18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("room_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "seek_auto_pause",
                sa.Boolean(),
                server_default=sa.true(),
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("room_settings", schema=None) as batch_op:
        batch_op.drop_column("seek_auto_pause")
