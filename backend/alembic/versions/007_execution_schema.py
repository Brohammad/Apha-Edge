"""Execution schema: broker connections, orders, executions, order events

Revision ID: 007
Revises: 006
Create Date: 2026-07-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "broker_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("broker_name", sa.String(50), nullable=False),
        sa.Column("credentials", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_paper", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_broker_connections_user_id", "broker_connections", ["user_id"])

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("broker_connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("filled_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("limit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("stop_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("broker_order_id", sa.String(100), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
        sa.ForeignKeyConstraint(["broker_connection_id"], ["broker_connections.id"]),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_orders_portfolio_id", "orders", ["portfolio_id"])
    op.create_index("ix_orders_status", "orders", ["status"])

    op.create_table(
        "executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("price", sa.Numeric(18, 8), nullable=False),
        sa.Column("commission", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_executions_order_id", "executions", ["order_id"])

    op.create_table(
        "order_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_events_order_id", "order_events", ["order_id"])


def downgrade() -> None:
    op.drop_table("order_events")
    op.drop_table("executions")
    op.drop_table("orders")
    op.drop_table("broker_connections")
