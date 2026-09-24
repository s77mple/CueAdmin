"""角色表 — 权限体系的枢纽（RBAC）。"""

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.storage import Base, TimestampMixin
from app.models.associations import role_menus, role_permissions, user_roles


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    code: Mapped[str] = mapped_column(String(50), unique=True, comment="唯一编码，如 admin、editor、viewer")
    name: Mapped[str] = mapped_column(String(50), comment="显示名，如“管理员”")
    description: Mapped[str | None] = mapped_column(String(200), comment="角色描述")
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="系统角色标记（True=不允许删除和修改 code）"
    )

    users = relationship("User", secondary=user_roles, back_populates="roles", passive_deletes=True)
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles", passive_deletes=True)
    menus = relationship("Menu", secondary=role_menus, back_populates="roles", passive_deletes=True)
