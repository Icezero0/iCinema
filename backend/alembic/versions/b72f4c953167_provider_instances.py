"""Make the HLS line identifier part of each provider instance."""
from alembic import op
import sqlalchemy as sa

revision = "b72f4c953167"
down_revision = "a61e3b842056"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("catalog_providers", sa.Column("play_from", sa.String(64), nullable=False, server_default=sa.text("''")))
    op.execute("UPDATE catalog_providers SET play_from='jinyingm3u8' WHERE code='jinying'")


def downgrade():
    with op.batch_alter_table("catalog_providers") as batch:
        batch.drop_column("play_from")
