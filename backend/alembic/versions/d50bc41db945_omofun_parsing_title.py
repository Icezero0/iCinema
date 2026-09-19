"""Expose the current parsing title without publishing partial playback data."""
from alembic import op
import sqlalchemy as sa

revision = "d50bc41db945"
down_revision = "c49ab30ca834"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("omofun_cache", sa.Column("parsing_title", sa.String(255), nullable=False, server_default=""))


def downgrade():
    op.drop_column("omofun_cache", "parsing_title")
