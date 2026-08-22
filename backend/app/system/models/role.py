"""角色表 — 权限体系的枢纽（RBAC）。

角色是用户/权限/菜单之间的桥：改一个角色的权限，所有拥有该角色的用户自动生效。
is_system=True 的角色不允许删除和修改 code（种子创建的 admin），防止误删系统关键角色。
"""

from sqlalchemy import String, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.storage import Base, TimestampMixin
from app.system.models.associations import user_roles, role_permissions, role_menus


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    code: Mapped[str] = mapped_column(String(50), unique=True, comment="唯一编码，如 admin、editor、viewer")
    name: Mapped[str] = mapped_column(String(50), comment="显示名，如“管理员”")
    description: Mapped[str | None] = mapped_column(String(200), comment="角色描述")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, comment="系统角色标记（True=不允许删除和修改 code）")

    users = relationship("User", secondary=user_roles, back_populates="roles", passive_deletes=True)
    permissions = relationship(
        "Permission", secondary=role_permissions, back_populates="roles", passive_deletes=True
    )
    menus = relationship(
        "Menu", secondary=role_menus, back_populates="roles", passive_deletes=True
    )
