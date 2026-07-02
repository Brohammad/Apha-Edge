"""Optimization schema: runs and trials

Revision ID: 006
Revises: 005
Create Date: 2026-07-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "optimization_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column("objective", sa.String(50), nullable=False),
        sa.Column("parameter_space", postgresql.JSONB(), nullable=False),
        sa.Column("backtest_config", postgresql.JSONB(), nullable=False),
        sa.Column("walk_forward_config", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("best_trial_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("total_trials", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_trials", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_optimization_runs_user_id", "optimization_runs", ["user_id"])
    op.create_index("ix_optimization_runs_status", "optimization_runs", ["status"])

    op.create_table(
        "optimization_trials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("optimization_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("backtest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parameters", postgresql.JSONB(), nullable=False),
        sa.Column("objective_value", sa.Numeric(12, 6), nullable=True),
        sa.Column("in_sample_objective", sa.Numeric(12, 6), nullable=True),
        sa.Column("window_index", sa.Integer(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["optimization_run_id"], ["optimization_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["backtest_run_id"], ["backtest_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_optimization_trials_run_id", "optimization_trials", ["optimization_run_id"]
    )

    op.create_foreign_key(
        "fk_optimization_runs_best_trial_id",
        "optimization_runs",
        "optimization_trials",
        ["best_trial_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_optimization_runs_best_trial_id", "optimization_runs", type_="foreignkey")
    op.drop_table("optimization_trials")
    op.drop_table("optimization_runs")
