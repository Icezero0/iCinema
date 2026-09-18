"""Add optional resource provider abbreviation."""
from alembic import op
import sqlalchemy as sa

revision = "e05c7fc86490"
down_revision = "d94b6eb75389"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("catalog_providers", sa.Column("abbreviation", sa.String(32), nullable=False, server_default=""))


def downgrade():
    op.drop_column("catalog_providers", "abbreviation")
