"""Portfolio and risk schema

Revision ID: 005
Revises: 004
Create Date: 2026-07-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("initial_capital", sa.Numeric(18, 4), nullable=False),
        sa.Column("cash_balance", sa.Numeric(18, 4), nullable=False),
        sa.Column("is_paper", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])

    op.create_table(
        "holdings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("avg_cost", sa.Numeric(18, 8), nullable=False),
        sa.Column("current_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("market_value", sa.Numeric(18, 4), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("portfolio_id", "instrument_id", name="uq_holdings_portfolio_instrument"),
    )
    op.create_index("ix_holdings_portfolio_id", "holdings", ["portfolio_id"])

    op.create_table(
        "rebalance_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_allocation", postgresql.JSONB(), nullable=False),
        sa.Column("proposed_trades", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rebalance_plans_portfolio_id", "rebalance_plans", ["portfolio_id"])

    op.create_table(
        "risk_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("var_95", sa.Numeric(12, 6), nullable=True),
        sa.Column("var_99", sa.Numeric(12, 6), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(10, 4), nullable=True),
        sa.Column("sharpe_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("sortino_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("beta", sa.Numeric(10, 4), nullable=True),
        sa.Column("alpha", sa.Numeric(10, 4), nullable=True),
        sa.Column("volatility", sa.Numeric(10, 4), nullable=True),
        sa.Column("correlation_matrix", postgresql.JSONB(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_snapshots_portfolio_id", "risk_snapshots", ["portfolio_id"])
    op.create_index("ix_risk_snapshots_snapshot_at", "risk_snapshots", ["snapshot_at"])

    op.create_table(
        "risk_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("limit_type", sa.String(50), nullable=False),
        sa.Column("threshold", sa.Numeric(12, 6), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "portfolio_id", "limit_type", name="uq_risk_limits_portfolio_type"
        ),
    )
    op.create_index("ix_risk_limits_portfolio_id", "risk_limits", ["portfolio_id"])


def downgrade() -> None:
    op.drop_table("risk_limits")
    op.drop_table("risk_snapshots")
    op.drop_table("rebalance_plans")
    op.drop_table("holdings")
    op.drop_table("portfolios")
