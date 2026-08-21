"""email verification, password recovery and free trial

Revision ID: 20260820_03
Revises: 20260820_02
Create Date: 2026-08-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260820_03"
down_revision: Union[str, None] = "20260820_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

auth_token_purpose = sa.Enum("VERIFY_EMAIL", "RESET_PASSWORD", name="authtokenpurpose")


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE users SET email_verified_at = now()")
    op.add_column("subscriptions", sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("subscriptions", sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        WITH eligible_trials AS (
            UPDATE subscriptions
            SET status = 'TRIALING',
                trial_started_at = now(),
                trial_ends_at = now() + interval '3 days',
                current_period_end = now() + interval '3 days'
            WHERE status = 'PENDING'
              AND provider_subscription_id IS NULL
              AND trial_started_at IS NULL
            RETURNING tenant_id
        )
        UPDATE tenants AS tenant
        SET status = CASE
            WHEN EXISTS (
                SELECT 1
                FROM whatsapp_connections AS connection
                WHERE connection.tenant_id = tenant.id
                  AND connection.status = 'CONNECTED'
            ) THEN 'ACTIVE'::tenantstatus
            ELSE 'AWAITING_WHATSAPP'::tenantstatus
        END
        FROM eligible_trials
        WHERE tenant.id = eligible_trials.tenant_id
        """
    )
    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", auth_token_purpose, nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])
    op.create_index("ix_auth_tokens_purpose", "auth_tokens", ["purpose"])
    op.create_index("ix_auth_tokens_token_hash", "auth_tokens", ["token_hash"], unique=True)
    op.create_index("ix_auth_tokens_expires_at", "auth_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_table("auth_tokens")
    op.drop_column("subscriptions", "trial_ends_at")
    op.drop_column("subscriptions", "trial_started_at")
    op.drop_column("users", "email_verified_at")
    auth_token_purpose.drop(op.get_bind(), checkfirst=True)
