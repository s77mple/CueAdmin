"""
多对多关联表 — 纯 SQLAlchemy Core Table（没有 ORM 类）。

三张关联表的含义：
  user_roles         → 用户拥有哪些角色
  role_permissions   → 角色拥有哪些权限
  role_menus         → 角色拥有哪些菜单

为什么用 Table 而不是 Model？
  关联表只是两个 ID 的组合，没有自己的业务字段，
  用 Table 更轻量，SQLAlchemy 自动处理 INSERT/DELETE。

为什么用 CASCADE 外键？
  ondelete="CASCADE" → 删除用户时自动删关联记录，
  不用手动先清关联再删用户。

为什么加反向索引？
  大部分查询是从 role_id/menu_id/permission_id 查关联的实体，
  加索引避免全表扫描。比如：
    - 查某角色有哪些用户 → WHERE role_id = X （有索引）
    - 查某菜单被哪些角色使用 → WHERE menu_id = X （有索引）
"""

from sqlalchemy import BigInteger, Column, ForeignKey, Index, Table
from app.core.database import Base


# ============================================================
# 1. user_roles — 用户 ↔ 角色
# ============================================================
# 一个用户可以有多个角色（admin、普通用户等）
# 一个角色可以分配给多个用户

user_roles = Table(
    "user_roles", Base.metadata,

    # 联合主键：同一用户不能重复拥有同一角色
    Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, comment="用户 ID"),
    Column("role_id", BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True, comment="角色 ID"),

    # 按角色查用户时用：SELECT user_id FROM user_roles WHERE role_id = X
    Index("ix_user_roles_role_id", "role_id"),
)


# ============================================================
# 2. role_permissions — 角色 ↔ 权限
# ============================================================

role_permissions = Table(
    "role_permissions", Base.metadata,

    Column("role_id",       BigInteger, ForeignKey("roles.id",       ondelete="CASCADE"), primary_key=True, comment="角色 ID"),
    Column("permission_id", BigInteger, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True, comment="权限 ID"),

    # 按权限查使用它的角色：SELECT role_id FROM role_permissions WHERE permission_id = X
    Index("ix_role_permissions_permission_id", "permission_id"),
)


# ============================================================
# 3. role_menus — 角色 ↔ 菜单
# ============================================================

role_menus = Table(
    "role_menus", Base.metadata,

    Column("role_id", BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True, comment="角色 ID"),
    Column("menu_id", BigInteger, ForeignKey("menus.id", ondelete="CASCADE"), primary_key=True, comment="菜单 ID"),

    # 按菜单查使用它的角色：SELECT role_id FROM role_menus WHERE menu_id = X
    Index("ix_role_menus_menu_id", "menu_id"),
)
