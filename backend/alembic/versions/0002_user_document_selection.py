"""add user document selection table

Revision ID: 0002_user_document_selection
Revises: 0001_init
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_user_document_selection"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_document_selection",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "document_id", name="uq_user_document_selection"),
    )
    op.create_index("ix_user_document_selection_user_id", "user_document_selection", ["user_id"])
    op.create_index("ix_user_document_selection_document_id", "user_document_selection", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_user_document_selection_document_id", table_name="user_document_selection")
    op.drop_index("ix_user_document_selection_user_id", table_name="user_document_selection")
    op.drop_table("user_document_selection")
