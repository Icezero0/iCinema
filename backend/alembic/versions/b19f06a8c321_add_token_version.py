"""Bind sessions to a revocable user credential version."""
from alembic import op
import sqlalchemy as sa

revision = "b19f06a8c321"
down_revision = "a71c5e4d2b90"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_column("token_version")
