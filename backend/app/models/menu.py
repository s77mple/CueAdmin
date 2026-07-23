from sqlalchemy import String, BigInteger, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Menu(Base):
    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    icon: Mapped[str | None] = mapped_column(String(50))
    path: Mapped[str | None] = mapped_column(String(100))           # 叶子节点才有路由路径
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("menus.id", ondelete="SET NULL"), default=None
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)     # 同级排序，越小越前

    # 自引用树形结构
    children = relationship(
        "Menu", back_populates="parent", foreign_keys=[parent_id],
        order_by="Menu.sort_order",
    )
    parent = relationship(
        "Menu", back_populates="children", remote_side="Menu.id",
    )
    roles = relationship("Role", secondary="role_menus", back_populates="menus")
