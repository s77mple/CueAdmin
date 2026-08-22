"""菜单表 — 树形结构（自引用），定义前端左侧导航。

目录菜单（component=null）只有子菜单不渲染页面；页面菜单（component=...）对应 views 下的 Vue 文件。
parent_id 自引用 + ondelete="SET NULL"：删父菜单后子菜单变顶级。
"""

from sqlalchemy import String, BigInteger, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.storage import Base, TimestampMixin


class Menu(Base, TimestampMixin):
    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    code: Mapped[str] = mapped_column(String(50), unique=True, comment="唯一编码，用于前端路由 name")
    name: Mapped[str] = mapped_column(String(50), comment="显示名，如“用户管理”")
    icon: Mapped[str | None] = mapped_column(String(50), comment="图标（fa-solid:users 等）")
    path: Mapped[str | None] = mapped_column(String(100), comment="路由路径，如 /users/index")
    component: Mapped[str | None] = mapped_column(String(200), comment="组件路径，如 system/users/index；null=目录菜单")
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("menus.id", ondelete="SET NULL"),  # 删父菜单 → 子菜单变顶级
        default=None,
        index=True,
        comment="上级菜单 ID（自引用，删父菜单后子菜单变顶级）",
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="同级排序，越小越靠前")

    children = relationship(
        "Menu",
        back_populates="parent",
        foreign_keys=[parent_id],
        order_by="Menu.sort_order",
    )
    parent = relationship(
        "Menu",
        back_populates="children",
        remote_side="Menu.id",
    )

    roles = relationship("Role", secondary="role_menus", back_populates="menus", passive_deletes=True)  # 删菜单 → role_menus 交给 DB CASCADE
