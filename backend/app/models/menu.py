"""
菜单表 — 树形结构（自引用），定义前端左侧导航菜单。

菜单有两种：
  目录菜单：path=/system, component=null → 只有子菜单，不渲染页面
  页面菜单：path=/users/index, component=system/users/index → 叶子节点，渲染 Vue 文件

前端动态路由的生成过程：
  1. 后端返回用户角色的菜单列表
  2. 前端 routes.ts 的 _build_routes() 把扁平列表转成树
  3. 每个叶子节点的 component 映射到 import.meta.glob 匹配的 Vue 文件
  4. router.addRoute() 动态注册

自引用外键：
  parent_id → menus.id  （一个菜单的"上级"是另一条菜单记录）
  ondelete="SET NULL"   （删除父菜单 → 子菜单变为顶级）
"""

from sqlalchemy import String, BigInteger, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Menu(Base, TimestampMixin):
    __tablename__ = "menus"

    # ---- 主键 ----
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # ---- 基本字段 ----
    code: Mapped[str] = mapped_column(String(50), unique=True)     # 唯一编码，用于前端路由 name
    name: Mapped[str] = mapped_column(String(50))                  # 显示名，如"用户管理"
    icon: Mapped[str | None] = mapped_column(String(50))           # 图标（fa-solid:users 等）
    path: Mapped[str | None] = mapped_column(String(100))          # 路由路径，如 /users/index
    component: Mapped[str | None] = mapped_column(String(200))     # 组件路径，如 system/users/index
                                                                    # null = 目录菜单，非 null = 叶子页面

    # ---- 树形结构 ----
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("menus.id", ondelete="SET NULL"),  # 删父菜单 → 子菜单变顶级
        default=None,
        index=True,  # 经常按 parent_id 查子节点，加索引
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)   # 同级排序，越小越靠前

    # ---- 自引用关系（树）----
    # 子节点集合（一个菜单下的所有子菜单）
    children = relationship(
        "Menu",
        back_populates="parent",
        foreign_keys=[parent_id],
        order_by="Menu.sort_order",  # 自动按 sort_order 排序
    )
    # 父节点（这个菜单属于哪个菜单的下级）
    parent = relationship(
        "Menu",
        back_populates="children",
        remote_side="Menu.id",  # 告诉 SQLAlchemy 外键指向自己
    )

    # ---- 多对多 ----
    # 哪些角色能看到这个菜单
    roles = relationship("Role", secondary="role_menus", back_populates="menus")
