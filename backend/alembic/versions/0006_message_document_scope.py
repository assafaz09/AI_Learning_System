"""teacher message document scope for repeat-question cache

Revision ID: 0006_message_document_scope
Revises: 0005_learning_projects_meta
Create Date: 2026-04-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_message_document_scope"
down_revision = "0005_learning_projects_meta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("document_scope_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "document_scope_json")
