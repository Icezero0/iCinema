"""Make content categories data-driven; seed the initial category."""
from alembic import op
import sqlalchemy as sa

revision = "d38b0e51f723"
down_revision = "c27a9d40e612"
branch_labels = None
depends_on = None


def upgrade():
    categories = op.create_table("catalog_categories",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False))
    op.bulk_insert(categories, [{"code": "japanese_animation", "name": "日本动画", "sort_order": 0}])


def downgrade():
    op.drop_table("catalog_categories")
