"""add source fields to documents

Revision ID: 0003_document_source_fields
Revises: 0002_user_document_selection
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_document_source_fields"
down_revision = "0002_user_document_selection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("documents") as batch_op:
            batch_op.add_column(sa.Column("source_type", sa.String(length=32), nullable=False, server_default="file"))
            batch_op.add_column(sa.Column("source_url", sa.String(length=1024), nullable=True))
            batch_op.add_column(sa.Column("external_id", sa.String(length=255), nullable=True))
            batch_op.alter_column("source_type", server_default=None)
    else:
        op.add_column("documents", sa.Column("source_type", sa.String(length=32), nullable=False, server_default="file"))
        op.add_column("documents", sa.Column("source_url", sa.String(length=1024), nullable=True))
        op.add_column("documents", sa.Column("external_id", sa.String(length=255), nullable=True))
        op.alter_column("documents", "source_type", server_default=None)


def downgrade() -> None:
    op.drop_column("documents", "external_id")
    op.drop_column("documents", "source_url")
    op.drop_column("documents", "source_type")
