"""add device_id to notification_tokens

Revision ID: 015
Revises: 014
Create Date: 2026-05-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "014"
down_revision: Union[str, Sequence[str], None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification_tokens",
        sa.Column("device_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notification_tokens", "device_id")
