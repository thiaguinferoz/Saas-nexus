"""automation bridge tables

Revision ID: 20260820_01
Revises: 20260820_00
Create Date: 2026-08-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260820_01"
down_revision: Union[str, None] = "20260820_00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


workflow_status = sa.Enum("QUEUED", "DISPATCHING", "RUNNING", "SUCCEEDED", "RETRYING", "FAILED", "DEAD_LETTER", name="workflowexecutionstatus")
outbound_status = sa.Enum("QUEUED", "SENDING", "SUBMITTED", "SENT", "DELIVERED", "READ", "FAILED", "DEAD_LETTER", name="outboundmessagestatus")


def upgrade() -> None:
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("webhook_event_id", sa.Uuid(), nullable=False),
        sa.Column("provider_event_id", sa.String(255), nullable=False),
        sa.Column("config_version", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("status", workflow_status, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("n8n_execution_id", sa.String(255), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["webhook_event_id"], ["webhook_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("correlation_id"),
        sa.UniqueConstraint("provider_event_id"),
        sa.UniqueConstraint("webhook_event_id"),
    )
    op.create_index("ix_workflow_executions_tenant_id", "workflow_executions", ["tenant_id"])
    op.create_index("ix_workflow_executions_status", "workflow_executions", ["status"])
    op.create_index("ix_workflow_executions_n8n_execution_id", "workflow_executions", ["n8n_execution_id"], unique=True)
    op.create_table(
        "outbound_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("recipient", sa.String(32), nullable=False),
        sa.Column("recipient_id", sa.String(255), nullable=True),
        sa.Column("message_type", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", outbound_status, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["workflow_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_outbound_messages_tenant_id", "outbound_messages", ["tenant_id"])
    op.create_index("ix_outbound_messages_execution_id", "outbound_messages", ["execution_id"])
    op.create_index("ix_outbound_messages_status", "outbound_messages", ["status"])
    op.create_index("ix_outbound_messages_provider_message_id", "outbound_messages", ["provider_message_id"])


def downgrade() -> None:
    op.drop_table("outbound_messages")
    op.drop_table("workflow_executions")
    outbound_status.drop(op.get_bind(), checkfirst=True)
    workflow_status.drop(op.get_bind(), checkfirst=True)
