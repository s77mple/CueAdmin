from sqlalchemy import BigInteger, Column, ForeignKey, Index, Table
from app.core.database import Base

user_roles = Table(
    "user_roles", Base.metadata,
    Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_user_roles_role_id", "role_id"),
)

role_permissions = Table(
    "role_permissions", Base.metadata,
    Column("role_id",       BigInteger, ForeignKey("roles.id",       ondelete="CASCADE"), primary_key=True),
    Column("permission_id", BigInteger, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_role_permissions_permission_id", "permission_id"),
)

role_menus = Table(
    "role_menus", Base.metadata,
    Column("role_id", BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("menu_id", BigInteger, ForeignKey("menus.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_role_menus_menu_id", "menu_id"),
)
