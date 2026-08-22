"""权限表 — 细粒度操作权限。

权限 code 格式 {resource}:{action}（如 user:list），前端 v-perms 判断按钮显隐，后端 Security scopes 鉴权。
"""

from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.system.models.associations import role_permissions
from app.core.storage import Base, TimestampMixin


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    code: Mapped[str] = mapped_column(String(100), unique=True, comment="权限码，如 user:list")
    name: Mapped[str] = mapped_column(String(100), comment="显示名，如“用户列表”")
    resource: Mapped[str] = mapped_column(String(50), comment="资源标识，如 user")
    action: Mapped[str] = mapped_column(String(50), comment="操作标识，如 list/create/update/delete")
    description: Mapped[str | None] = mapped_column(String(200), comment="权限描述")

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions", passive_deletes=True)  # 删权限 → role_permissions 交给 DB CASCADE
