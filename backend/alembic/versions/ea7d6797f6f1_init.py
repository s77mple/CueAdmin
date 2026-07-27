"""init

Revision ID: ea7d6797f6f1
Revises:
Create Date: 2026-06-09 21:30:26.924883
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'ea7d6797f6f1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ====== 用户表 ======
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(50), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    # ====== 角色表 ======
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # ====== 权限表 ======
    op.create_table(
        "permissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(50), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # ====== 菜单表（树形结构） ======
    op.create_table(
        "menus",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("path", sa.String(100), nullable=True),
        sa.Column("parent_id", sa.BigInteger(),
                  sa.ForeignKey("menus.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # ====== 关联表（复合主键，无自增 ID） ======
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.BigInteger(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.BigInteger(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.BigInteger(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "role_menus",
        sa.Column("role_id", sa.BigInteger(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("menu_id", sa.BigInteger(), sa.ForeignKey("menus.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("role_menus")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("menus")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
