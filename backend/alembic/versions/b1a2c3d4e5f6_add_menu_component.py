"""add menu component

Revision ID: b1a2c3d4e5f6
Revises: ea7d6797f6f1
Create Date: 2026-08-03 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b1a2c3d4e5f6'
down_revision: Union[str, None] = 'ea7d6797f6f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("menus", sa.Column("component", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("menus", "component")
