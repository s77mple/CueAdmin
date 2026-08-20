"""
部门表 — 树形结构（自引用），组织架构管理。

与菜单表的树形结构完全相同的模式：
  parent_id → departments.id（自引用外键）
  ondelete="SET NULL"（删部门 → 子部门变顶级）

部门与用户的关系：
  Department.users → 一对多 → User
  删除部门 → 用户的 department_id 变为 NULL（不删除用户）
"""

from sqlalchemy import String, BigInteger, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    # ---- 主键 ----
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")

    # ---- 基本字段 ----
    code: Mapped[str] = mapped_column(String(50), unique=True, comment="唯一编码，如 tech、market")     # 唯一编码，如 tech、market
    name: Mapped[str] = mapped_column(String(50), comment="部门名称，如“技术部”")                  # 部门名称，如"技术部"
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="SET NULL"),  # 删父部门 → 子部门变顶级
        default=None,
        index=True,
        comment="上级部门 ID（自引用，删父部门后子部门变顶级）",
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="同级排序，越小越靠前")    # 同级排序
    description: Mapped[str | None] = mapped_column(Text, comment="部门描述")          # Text 类型 = 无长度限制

    # ---- 自引用关系（树）----
    children = relationship(
        "Department",
        back_populates="parent",
        foreign_keys=[parent_id],
        order_by="Department.sort_order",
    )
    parent = relationship(
        "Department",
        back_populates="children",
        remote_side="Department.id",
    )

    # ---- 一对多 ----
    # 一个部门下有多个用户
    users = relationship("User", back_populates="department", passive_deletes=True)  # 删除部门 → 用户的 department_id 变为 NULL（不删除用户）
