"""
角色表 — 权限体系的枢纽。

角色是用户、权限、菜单三者之间的桥梁：
  User ←→ Role ←→ Permission  （用户能做什么操作）
  User ←→ Role ←→ Menu        （用户能看到什么菜单）

设计思想（RBAC — 基于角色的访问控制）：
  - 不给用户直接分配权限，而是通过角色间接分配
  - 管理员给角色配好权限/菜单，然后把角色分配给用户
  - 修改角色的权限 → 所有拥有该角色的用户自动生效
"""

from sqlalchemy import String, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.associations import user_roles, role_permissions, role_menus


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    # ---- 主键 ----
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # ---- 基本字段 ----
    code: Mapped[str] = mapped_column(String(50), unique=True)    # 唯一编码，如 admin、editor、viewer
    name: Mapped[str] = mapped_column(String(50))                 # 显示名，如"管理员"
    description: Mapped[str | None] = mapped_column(String(200))  # 描述

    # ---- 系统角色标记 ----
    # is_system=True → 不允许删除和修改 code（种子数据创建的 admin 角色）
    # 防止管理员误删系统关键角色
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    # ---- 关系 ----
    # 多对多：一个角色可以分配给多个用户
    users = relationship("User", secondary=user_roles, back_populates="roles")

    # 多对多：一个角色可以拥有多个权限
    permissions = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )

    # 多对多：一个角色可以拥有多个菜单
    menus = relationship(
        "Menu", secondary=role_menus, back_populates="roles"
    )
