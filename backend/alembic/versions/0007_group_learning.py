"""group learning sessions and messages

Revision ID: 0007_group_learning
Revises: 0006_message_document_scope
Create Date: 2026-04-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_group_learning"
down_revision = "0006_message_document_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group_learning_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("document_ids_json", sa.Text(), nullable=False),
        sa.Column("next_speaker", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_group_learning_sessions_id"), "group_learning_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_group_learning_sessions_user_id"), "group_learning_sessions", ["user_id"], unique=False)
    op.create_table(
        "group_learning_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["group_learning_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_group_learning_messages_id"), "group_learning_messages", ["id"], unique=False)
    op.create_index(
        op.f("ix_group_learning_messages_session_id"), "group_learning_messages", ["session_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_group_learning_messages_session_id"), table_name="group_learning_messages")
    op.drop_index(op.f("ix_group_learning_messages_id"), table_name="group_learning_messages")
    op.drop_table("group_learning_messages")
    op.drop_index(op.f("ix_group_learning_sessions_user_id"), table_name="group_learning_sessions")
    op.drop_index(op.f("ix_group_learning_sessions_id"), table_name="group_learning_sessions")
    op.drop_table("group_learning_sessions")
