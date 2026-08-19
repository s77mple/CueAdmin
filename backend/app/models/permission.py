"""
权限表 — 细粒度操作权限。

权限 code 格式：{resource}:{action}
  例：user:list、user:create、role:delete、menu:update

前端 v-perms 指令：
  <el-button v-perms="['user:create']">新建用户</el-button>
  → 如果当前用户的权限列表里有 user:create，按钮显示；否则隐藏

后端 Security scopes：
  Security(get_current_user, scopes=["user:create"])
  → dependencies.py 里检查当前用户是否有此权限，没有 → 403

权限粒度：
  resource（资源） + action（操作） → code
  5 资源 × 4 操作 = 20 个权限码，覆盖所有管理页面
"""

from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.associations import role_permissions
from app.models.base import TimestampMixin


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    # ---- 主键 ----
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")

    # ---- 基本字段 ----
    code: Mapped[str] = mapped_column(String(100), unique=True, comment="权限码，如 user:list")     # 权限码，如 user:list
    name: Mapped[str] = mapped_column(String(100), comment="显示名，如“用户列表”")                  # 显示名，如"用户列表"
    resource: Mapped[str] = mapped_column(String(50), comment="资源标识，如 user")               # 资源标识，如 user
    action: Mapped[str] = mapped_column(String(50), comment="操作标识，如 list/create/update/delete")                 # 操作标识，如 list/create/update/delete
    description: Mapped[str | None] = mapped_column(String(200), comment="权限描述")    # 描述

    # ---- 多对多 ----
    # 哪些角色拥有这个权限
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
