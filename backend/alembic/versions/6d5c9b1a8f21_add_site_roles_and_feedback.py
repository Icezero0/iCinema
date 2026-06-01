"""add site roles and feedback

Revision ID: 6d5c9b1a8f21
Revises: 01bf66a2961c
Create Date: 2026-06-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "6d5c9b1a8f21"
down_revision: str | None = "01bf66a2961c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "site_role",
                sa.String(length=16),
                server_default="user",
                nullable=False,
            )
        )

    op.create_table(
        "feedbacks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("handled_by_id", sa.Integer(), nullable=True),
        sa.Column("screenshot_asset_id", sa.Integer(), nullable=True),
        sa.Column("feedback_type", sa.String(length=32), server_default="bug", nullable=False),
        sa.Column("page", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["handled_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["screenshot_asset_id"], ["media_assets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("feedbacks", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_feedbacks_creator_id"), ["creator_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_feedbacks_handled_by_id"), ["handled_by_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_feedbacks_screenshot_asset_id"), ["screenshot_asset_id"], unique=False)
        batch_op.create_index("idx_feedbacks_creator_id_created_at", ["creator_id", "created_at"], unique=False)
        batch_op.create_index("idx_feedbacks_status_created_at", ["status", "created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("feedbacks", schema=None) as batch_op:
        batch_op.drop_index("idx_feedbacks_status_created_at")
        batch_op.drop_index("idx_feedbacks_creator_id_created_at")
        batch_op.drop_index(batch_op.f("ix_feedbacks_screenshot_asset_id"))
        batch_op.drop_index(batch_op.f("ix_feedbacks_handled_by_id"))
        batch_op.drop_index(batch_op.f("ix_feedbacks_creator_id"))
    op.drop_table("feedbacks")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("site_role")
