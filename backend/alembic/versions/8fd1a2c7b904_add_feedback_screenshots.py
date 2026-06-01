"""add feedback screenshots

Revision ID: 8fd1a2c7b904
Revises: 6d5c9b1a8f21
Create Date: 2026-06-01 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "8fd1a2c7b904"
down_revision: str | None = "6d5c9b1a8f21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback_screenshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feedback_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["feedback_id"], ["feedbacks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("feedback_screenshots", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_feedback_screenshots_asset_id"), ["asset_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_feedback_screenshots_feedback_id"), ["feedback_id"], unique=False)
        batch_op.create_index(
            "idx_feedback_screenshots_feedback_order",
            ["feedback_id", "sort_order"],
            unique=False,
        )

    op.execute(
        """
        INSERT INTO feedback_screenshots (feedback_id, asset_id, sort_order)
        SELECT id, screenshot_asset_id, 0
        FROM feedbacks
        WHERE screenshot_asset_id IS NOT NULL
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("feedback_screenshots", schema=None) as batch_op:
        batch_op.drop_index("idx_feedback_screenshots_feedback_order")
        batch_op.drop_index(batch_op.f("ix_feedback_screenshots_feedback_id"))
        batch_op.drop_index(batch_op.f("ix_feedback_screenshots_asset_id"))
    op.drop_table("feedback_screenshots")
