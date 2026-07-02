"""Strategy schema: strategies, strategy_versions, indicators

Revision ID: 003
Revises: 002
Create Date: 2026-07-02
"""

import uuid
from datetime import UTC, datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDICATOR_SEED = [
    {
        "id": str(uuid.uuid4()),
        "name": "sma",
        "category": "trend",
        "parameters_schema": {"period": {"type": "integer", "minimum": 1, "default": 20}},
        "implementation": "python",
    },
    {
        "id": str(uuid.uuid4()),
        "name": "ema",
        "category": "trend",
        "parameters_schema": {"period": {"type": "integer", "minimum": 1, "default": 20}},
        "implementation": "python",
    },
    {
        "id": str(uuid.uuid4()),
        "name": "rsi",
        "category": "momentum",
        "parameters_schema": {"period": {"type": "integer", "minimum": 2, "default": 14}},
        "implementation": "python",
    },
    {
        "id": str(uuid.uuid4()),
        "name": "macd",
        "category": "momentum",
        "parameters_schema": {
            "fast_period": {"type": "integer", "minimum": 1, "default": 12},
            "slow_period": {"type": "integer", "minimum": 1, "default": 26},
            "signal_period": {"type": "integer", "minimum": 1, "default": 9},
        },
        "implementation": "python",
    },
    {
        "id": str(uuid.uuid4()),
        "name": "bollinger",
        "category": "volatility",
        "parameters_schema": {
            "period": {"type": "integer", "minimum": 2, "default": 20},
            "std_dev": {"type": "number", "minimum": 0.1, "default": 2.0},
        },
        "implementation": "python",
    },
]


def upgrade() -> None:
    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("strategy_type", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strategies_user_id", "strategies", ["user_id"])
    op.create_index(
        "ix_strategies_user_name",
        "strategies",
        ["user_id", "name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "strategy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("parameters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("compiled_hash", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("strategy_id", "version", name="uq_strategy_versions_strategy_version"),
    )
    op.create_index("ix_strategy_versions_strategy_id", "strategy_versions", ["strategy_id"])

    op.create_table(
        "indicators",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("parameters_schema", postgresql.JSONB(), nullable=False),
        sa.Column("implementation", sa.String(20), nullable=False, server_default="python"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_indicators_name", "indicators", ["name"], unique=True)

    now = datetime.now(UTC)
    indicators_table = sa.table(
        "indicators",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("category", sa.String),
        sa.column("parameters_schema", postgresql.JSONB),
        sa.column("implementation", sa.String),
    )
    op.bulk_insert(
        indicators_table,
        [
            {
                "id": row["id"],
                "name": row["name"],
                "category": row["category"],
                "parameters_schema": row["parameters_schema"],
                "implementation": row["implementation"],
            }
            for row in INDICATOR_SEED
        ],
    )


def downgrade() -> None:
    op.drop_table("indicators")
    op.drop_table("strategy_versions")
    op.drop_table("strategies")
