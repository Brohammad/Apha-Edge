"""Alembic migration: strategy deployments for live signal evaluation."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "strategy_deployments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("broker_connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instrument_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_signal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_signal_action", sa.String(10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"]),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
        sa.ForeignKeyConstraint(["broker_connection_id"], ["broker_connections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strategy_deployments_user_id", "strategy_deployments", ["user_id"])
    op.create_index(
        "ix_strategy_deployments_strategy_version_id",
        "strategy_deployments",
        ["strategy_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_strategy_deployments_strategy_version_id", table_name="strategy_deployments")
    op.drop_index("ix_strategy_deployments_user_id", table_name="strategy_deployments")
    op.drop_table("strategy_deployments")
