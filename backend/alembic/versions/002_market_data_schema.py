"""Market data schema: instruments, bars, ingestion jobs

Revision ID: 002
Revises: 001
Create Date: 2026-07-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=True),
        sa.Column("asset_class", sa.String(20), nullable=False),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_instruments_symbol", "instruments", ["symbol"], unique=True)

    op.create_table(
        "bars",
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(18, 8), nullable=False),
        sa.Column("high", sa.Numeric(18, 8), nullable=False),
        sa.Column("low", sa.Numeric(18, 8), nullable=False),
        sa.Column("close", sa.Numeric(18, 8), nullable=False),
        sa.Column("volume", sa.Numeric(18, 4), nullable=False),
        sa.Column("vwap", sa.Numeric(18, 8), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("instrument_id", "timeframe", "timestamp"),
    )
    op.create_index(
        "ix_bars_instrument_timeframe_ts",
        "bars",
        ["instrument_id", "timeframe", "timestamp"],
    )

    op.create_table(
        "data_ingestion_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("symbols", postgresql.JSONB(), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("records_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_ingestion_jobs_status", "data_ingestion_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("data_ingestion_jobs")
    op.drop_table("bars")
    op.drop_table("instruments")
