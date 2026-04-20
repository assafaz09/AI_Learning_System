"""learning_projects source importance description

Revision ID: 0005_learning_projects_meta
Revises: 0004_learning_projects
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0005_learning_projects_meta"
down_revision = "0004_learning_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns("learning_projects")}
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("learning_projects") as batch_op:
            if "source" not in cols:
                batch_op.add_column(sa.Column("source", sa.String(length=16), nullable=False, server_default="ai"))
                batch_op.alter_column("source", server_default=None)
            if "importance" not in cols:
                batch_op.add_column(sa.Column("importance", sa.String(length=16), nullable=False, server_default="medium"))
                batch_op.alter_column("importance", server_default=None)
            if "description" not in cols:
                batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
    else:
        if "source" not in cols:
            op.add_column(
                "learning_projects",
                sa.Column("source", sa.String(length=16), nullable=False, server_default="ai"),
            )
            op.alter_column("learning_projects", "source", server_default=None)
        if "importance" not in cols:
            op.add_column(
                "learning_projects",
                sa.Column("importance", sa.String(length=16), nullable=False, server_default="medium"),
            )
            op.alter_column("learning_projects", "importance", server_default=None)
        if "description" not in cols:
            op.add_column("learning_projects", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("learning_projects", "description")
    op.drop_column("learning_projects", "importance")
    op.drop_column("learning_projects", "source")
