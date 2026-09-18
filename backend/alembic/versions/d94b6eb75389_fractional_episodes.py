"""Support inserted fractional episode numbers and their sort order."""
from alembic import op
import sqlalchemy as sa

revision = "d94b6eb75389"
down_revision = "c83a5da64278"
branch_labels = None
depends_on = None


def guard():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite" and bind.exec_driver_sql("PRAGMA foreign_keys").scalar():
        raise RuntimeError("Use the project's Alembic connection with SQLite foreign_keys=OFF.")


def upgrade():
    guard()
    with op.batch_alter_table("catalog_episodes", table_kwargs={"sqlite_autoincrement": True}) as batch:
        batch.alter_column("number", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=False)
        batch.alter_column("sort_order", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=False)


def downgrade():
    guard()
    if op.get_bind().execute(sa.text("SELECT id FROM catalog_episodes WHERE number != CAST(number AS INTEGER) OR sort_order != CAST(sort_order AS INTEGER) LIMIT 1")).first():
        raise RuntimeError("Fractional episodes exist; resolve them before downgrading. No episodes were changed.")
    with op.batch_alter_table("catalog_episodes", table_kwargs={"sqlite_autoincrement": True}) as batch:
        batch.alter_column("number", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=False)
        batch.alter_column("sort_order", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=False)
