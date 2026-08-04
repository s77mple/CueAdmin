"""add timestamps to menus, permissions, departments

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-08-04 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, None] = 'd6e7f8a9b0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("menus", "permissions", "departments"):
        op.add_column(table, sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
        op.add_column(table, sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    for table in ("departments", "permissions", "menus"):
        op.drop_column(table, "updated_at")
        op.drop_column(table, "created_at")
