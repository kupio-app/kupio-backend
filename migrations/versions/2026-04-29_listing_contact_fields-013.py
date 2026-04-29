"""listing contact fields

Revision ID: 013
Revises: 012
Create Date: 2026-04-29

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "013"
down_revision: Union[str, Sequence[str], None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("phone", sa.String(20), nullable=True))
    op.add_column("listings", sa.Column("contact_name", sa.String(100), nullable=True))
    op.add_column(
        "listings",
        sa.Column(
            "is_calls_disabled", sa.Boolean(), nullable=False, server_default="false"
        ),
    )


def downgrade() -> None:
    op.drop_column("listings", "is_calls_disabled")
    op.drop_column("listings", "contact_name")
    op.drop_column("listings", "phone")
