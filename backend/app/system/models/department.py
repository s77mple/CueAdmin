"""部门表 — 树形结构（自引用），组织架构管理。

与菜单表同模式：parent_id 自引用 + ondelete="SET NULL"（删父部门 → 子部门变顶级）。
Department.users 一对多关联 User，删部门不删用户（SET NULL）。
"""

from sqlalchemy import String, BigInteger, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.storage import Base, TimestampMixin


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    code: Mapped[str] = mapped_column(String(50), unique=True, comment="唯一编码")
    name: Mapped[str] = mapped_column(String(50), comment="部门名称，如“技术部”")
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="SET NULL"),  # 删父部门 → 子部门变顶级
        default=None,
        index=True,
        comment="上级部门 ID（自引用，删父部门后子部门变顶级）",
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="同级排序，越小越靠前")
    description: Mapped[str | None] = mapped_column(Text, comment="部门描述")  # Text = 无长度限制

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

    users = relationship("User", back_populates="department", passive_deletes=True)  # 删部门 → 用户 department_id 变 NULL
