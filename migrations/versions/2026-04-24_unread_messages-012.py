"""unread messages read tracking

Revision ID: 012
Revises: 011
Create Date: 2026-04-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012"
down_revision: Union[str, Sequence[str], None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("buyer_last_read_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("seller_last_read_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversations", "seller_last_read_at")
    op.drop_column("conversations", "buyer_last_read_at")
