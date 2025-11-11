"""create ai_chats table

Revision ID: create_ai_chats
Revises: c64a70a64aab
Create Date: 2025-01-15 10:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "create_ai_chats"
down_revision = "c64a70a64aab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ai_chats table
    op.create_table(
        "ai_chats",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True, server_default=""),
        sa.Column("messages", postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ai_chats_user_id", "ai_chats", ["user_id"])
    op.create_index("idx_ai_chats_created_at", "ai_chats", ["created_at"])
    op.create_index("idx_ai_chats_updated_at", "ai_chats", ["updated_at"])


def downgrade() -> None:
    op.drop_index("idx_ai_chats_updated_at", table_name="ai_chats")
    op.drop_index("idx_ai_chats_created_at", table_name="ai_chats")
    op.drop_index("idx_ai_chats_user_id", table_name="ai_chats")
    op.drop_table("ai_chats")

