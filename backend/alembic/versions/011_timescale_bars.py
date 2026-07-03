"""Optional TimescaleDB extension (hypertable conversion is manual — see docs).

Revision ID: 011
Revises: 010
Create Date: 2026-07-03
"""

from typing import Sequence, Union

from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS timescaledb;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'TimescaleDB extension not available — skipping';
        END $$;
        """
    )


def downgrade() -> None:
    pass
