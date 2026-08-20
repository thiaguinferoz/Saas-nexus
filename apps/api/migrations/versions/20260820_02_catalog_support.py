"""standard catalog and customer support

Revision ID: 20260820_02
Revises: 20260820_01
Create Date: 2026-08-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260820_02"
down_revision: Union[str, None] = "20260820_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ticket_category = sa.Enum("SUPPORT", "BILLING", "INTEGRATION", "CUSTOM_PLAN", name="supportticketcategory")
ticket_priority = sa.Enum("NORMAL", "HIGH", name="supportticketpriority")
ticket_status = sa.Enum("OPEN", "IN_PROGRESS", "RESOLVED", name="supportticketstatus")


def upgrade() -> None:
    op.create_table(
        "catalog_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(120), nullable=True),
        sa.Column("sku", sa.String(120), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "sku"),
    )
    op.create_index("ix_catalog_items_tenant_id", "catalog_items", ["tenant_id"])
    op.create_index("ix_catalog_items_name", "catalog_items", ["name"])
    op.create_index("ix_catalog_items_category", "catalog_items", ["category"])
    op.create_index("ix_catalog_items_is_active", "catalog_items", ["is_active"])

    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("category", ticket_category, nullable=False),
        sa.Column("priority", ticket_priority, nullable=False),
        sa.Column("status", ticket_status, nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("preferred_channel", sa.String(32), nullable=False),
        sa.Column("contact_value", sa.String(320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_tickets_tenant_id", "support_tickets", ["tenant_id"])
    op.create_index("ix_support_tickets_created_by", "support_tickets", ["created_by"])
    op.create_index("ix_support_tickets_category", "support_tickets", ["category"])
    op.create_index("ix_support_tickets_priority", "support_tickets", ["priority"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])


def downgrade() -> None:
    op.drop_table("support_tickets")
    op.drop_table("catalog_items")
    ticket_status.drop(op.get_bind(), checkfirst=True)
    ticket_priority.drop(op.get_bind(), checkfirst=True)
    ticket_category.drop(op.get_bind(), checkfirst=True)
