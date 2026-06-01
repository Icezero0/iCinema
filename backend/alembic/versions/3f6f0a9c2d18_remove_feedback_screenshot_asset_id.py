"""remove legacy feedback screenshot asset column

Revision ID: 3f6f0a9c2d18
Revises: 8fd1a2c7b904
Create Date: 2026-06-01 20:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "3f6f0a9c2d18"
down_revision: str | None = "8fd1a2c7b904"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("feedbacks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_feedbacks_screenshot_asset_id"))
        batch_op.drop_column("screenshot_asset_id")


def downgrade() -> None:
    with op.batch_alter_table("feedbacks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("screenshot_asset_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_feedbacks_screenshot_asset_id_media_assets",
            "media_assets",
            ["screenshot_asset_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            batch_op.f("ix_feedbacks_screenshot_asset_id"),
            ["screenshot_asset_id"],
            unique=False,
        )
