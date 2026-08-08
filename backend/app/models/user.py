"""
用户表 — 系统核心实体之一。

表结构：
  users
  ├─ id (BIGINT PK)               — 自增主键
  ├─ username (VARCHAR 50 UNIQUE) — 登录用户名，唯一
  ├─ password_hash (VARCHAR 255)  — bcrypt 哈希后的密码，不存明文
  ├─ display_name (VARCHAR 50)    — 显示名（如"张三"）
  ├─ phone (VARCHAR 20 NULLABLE)  — 手机号
  ├─ is_active (BOOLEAN INDEX)    — 是否启用（禁用 = 不能登录）
  ├─ department_id (FK→departments SET NULL INDEX) — 所属部门（删除部门时置 NULL）
  ├─ created_at / updated_at      — 时间戳（来自 TimestampMixin）

关系：
  User.roles       → 多对多 → Role（通过 user_roles 关联表）
  User.department  → 多对一 → Department

为什么 is_active 要加索引？
  登录时查询 WHERE username=X AND is_active=TRUE，is_active 索引加速。
  列表筛选时 WHERE is_active=FALSE 也用索引。

为什么 department_id 的 FK 是 SET NULL？
  删部门时用户还在，只是变成"无部门"状态。
  如果用 CASCADE 删部门会把用户一起删了——不合理。
"""

from sqlalchemy import String, Boolean, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.associations import user_roles


class User(Base, TimestampMixin):
    __tablename__ = "users"

    # ---- 主键 ----
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # ---- 基本字段 ----
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # bcrypt 哈希，永远不存明文
    display_name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(20))

    # ---- 状态字段 ----
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # ---- 外键 ----
    department_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="SET NULL"),  # 部门删除 → 用户的 department_id 变 NULL
        default=None,
        index=True,
    )

    # ---- 关系 ----
    # secondary=user_roles → 通过关联表做多对多
    roles = relationship("Role", secondary=user_roles, back_populates="users")

    # 多对一：多个用户属于同一部门
    department = relationship("Department", back_populates="users")
