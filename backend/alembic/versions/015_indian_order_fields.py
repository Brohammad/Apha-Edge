"""Add product_type and exchange_segment to orders."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("product_type", sa.String(10), nullable=False, server_default="CNC"),
    )
    op.add_column(
        "orders",
        sa.Column("exchange_segment", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "exchange_segment")
    op.drop_column("orders", "product_type")
