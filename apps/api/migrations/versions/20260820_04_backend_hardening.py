"""harden sessions, billing state and support delivery

Revision ID: 20260820_04
Revises: 20260820_03
Create Date: 2026-08-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260820_04"
down_revision: Union[str, None] = "20260820_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("session_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )

    op.add_column("subscriptions", sa.Column("checkout_attempt_id", sa.Uuid(), nullable=True))
    op.add_column(
        "subscriptions",
        sa.Column("checkout_attempt_created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("subscriptions", sa.Column("grace_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "subscriptions",
        sa.Column("last_provider_event_created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "support_tickets",
        sa.Column("notification_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "support_tickets",
        sa.Column("notification_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "support_tickets",
        sa.Column("notification_last_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("support_tickets", "notification_last_error")
    op.drop_column("support_tickets", "notification_sent_at")
    op.drop_column("support_tickets", "notification_attempts")

    op.drop_column("subscriptions", "last_provider_event_created_at")
    op.drop_column("subscriptions", "grace_ends_at")
    op.drop_column("subscriptions", "checkout_attempt_created_at")
    op.drop_column("subscriptions", "checkout_attempt_id")

    op.drop_column("users", "session_version")
