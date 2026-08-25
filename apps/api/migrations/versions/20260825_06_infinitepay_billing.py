"""add InfinitePay orders and paid plan metadata

Revision ID: 20260825_06
Revises: 20260825_05
Create Date: 2026-08-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260825_06"
down_revision: Union[str, None] = "20260825_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("plan_code", sa.String(32), nullable=True))
    op.add_column("subscriptions", sa.Column("billing_interval", sa.String(16), nullable=True))
    op.add_column("subscriptions", sa.Column("amount_paid_cents", sa.Integer(), nullable=True))
    op.add_column("subscriptions", sa.Column("last_payment_method", sa.String(32), nullable=True))
    op.create_table(
        "billing_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("plan_code", sa.String(32), nullable=False),
        sa.Column("billing_interval", sa.String(16), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("checkout_url", sa.Text(), nullable=True),
        sa.Column("provider_transaction_id", sa.String(255), nullable=True),
        sa.Column("provider_invoice_slug", sa.String(255), nullable=True),
        sa.Column("capture_method", sa.String(32), nullable=True),
        sa.Column("installments", sa.Integer(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_transaction_id"),
    )
    op.create_index("ix_billing_orders_tenant_id", "billing_orders", ["tenant_id"])
    op.create_index("ix_billing_orders_subscription_id", "billing_orders", ["subscription_id"])
    op.create_index("ix_billing_orders_provider", "billing_orders", ["provider"])
    op.create_index("ix_billing_orders_status", "billing_orders", ["status"])
    op.create_index("ix_billing_orders_created_at", "billing_orders", ["created_at"])


def downgrade() -> None:
    op.drop_table("billing_orders")
    op.drop_column("subscriptions", "last_payment_method")
    op.drop_column("subscriptions", "amount_paid_cents")
    op.drop_column("subscriptions", "billing_interval")
    op.drop_column("subscriptions", "plan_code")
