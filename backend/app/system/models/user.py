"""用户表 — 系统核心实体。

为什么 department_id 用 SET NULL 而非 CASCADE：删部门时用户还在，只是变"无部门"，
CASCADE 会把用户一起删掉。is_active 加索引是因为登录/列表筛选都按它过滤。
"""

from sqlalchemy import String, Boolean, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.storage import Base, TimestampMixin
from app.system.models.associations import user_roles


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    username: Mapped[str] = mapped_column(String(50), unique=True, comment="登录用户名，唯一")
    password_hash: Mapped[str] = mapped_column(String(255), comment="bcrypt 哈希后的密码，不存明文")
    display_name: Mapped[str] = mapped_column(String(50), comment="显示名（如：张三）")
    phone: Mapped[str | None] = mapped_column(String(20), comment="手机号")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, comment="是否启用（禁用=不能登录）")
    department_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="SET NULL"),  # 删部门 → 用户变"无部门"，不删用户
        default=None,
        index=True,
        comment="所属部门 ID（删除部门时置 NULL）",
    )

    roles = relationship("Role", secondary=user_roles, back_populates="users", passive_deletes=True)  # 删用户 → user_roles 交给 DB CASCADE
    department = relationship("Department", back_populates="users")

    # role_ids 不是表列：UserRead 回显要的「角色 ID 列表」由服务层现算
    # （roles 预加载后 [role.id for role in user.roles]）以临时属性挂到对象上，模型不背计算。
