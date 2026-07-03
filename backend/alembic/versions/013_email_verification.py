"""Add email verification fields to users

Revision ID: 013
Revises: 012
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("email_verification_token_hash", sa.String(255), nullable=True),
    )
    op.execute("UPDATE users SET email_verified = true")


def downgrade() -> None:
    op.drop_column("users", "email_verification_token_hash")
    op.drop_column("users", "email_verified")
