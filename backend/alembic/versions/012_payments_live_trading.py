"""Marketplace purchases and live-trading acknowledgments

Revision ID: 012
Revises: 011
Create Date: 2026-07-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketplace_purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buyer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("stripe_session_id", sa.String(255), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["strategy_listings.id"]),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_session_id"),
    )
    op.create_index(
        "ix_marketplace_purchases_listing_buyer",
        "marketplace_purchases",
        ["listing_id", "buyer_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_marketplace_purchases_listing_buyer", table_name="marketplace_purchases")
    op.drop_table("marketplace_purchases")
