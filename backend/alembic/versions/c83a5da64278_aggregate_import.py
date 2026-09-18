"""Persist multi-provider discovery criteria and progress."""
from alembic import op
import sqlalchemy as sa

revision = "c83a5da64278"
down_revision = "b72f4c953167"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("catalog_import_jobs", sa.Column("query", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade():
    with op.batch_alter_table("catalog_import_jobs") as batch:
        batch.drop_column("query")
