"""add threaded replies to support tickets

Revision ID: 20260825_05
Revises: 20260820_04
Create Date: 2026-08-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260825_05"
down_revision: Union[str, None] = "20260820_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "support_ticket_replies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column("author_role", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_ticket_replies_ticket_id", "support_ticket_replies", ["ticket_id"])
    op.create_index("ix_support_ticket_replies_tenant_id", "support_ticket_replies", ["tenant_id"])
    op.create_index("ix_support_ticket_replies_author_id", "support_ticket_replies", ["author_id"])


def downgrade() -> None:
    op.drop_table("support_ticket_replies")
