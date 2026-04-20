"""learning_projects table

Revision ID: 0004_learning_projects
Revises: 0003_document_source_fields
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_learning_projects"
down_revision = "0003_document_source_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("suggestions_body", sa.Text(), nullable=False),
        sa.Column("learning_focus", sa.Text(), nullable=False),
        sa.Column("experience_band", sa.String(length=64), nullable=False),
        sa.Column("document_ids_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="not_started"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_learning_projects_id"), "learning_projects", ["id"], unique=False)
    op.create_index(op.f("ix_learning_projects_user_id"), "learning_projects", ["user_id"], unique=False)
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("learning_projects") as batch_op:
            batch_op.alter_column("status", server_default=None)
    else:
        op.alter_column("learning_projects", "status", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_learning_projects_user_id"), table_name="learning_projects")
    op.drop_index(op.f("ix_learning_projects_id"), table_name="learning_projects")
    op.drop_table("learning_projects")
