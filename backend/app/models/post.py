"""岗位表 — 职位标签，与角色维度正交（学 RuoYi sys_post）。"""

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.storage import Base, TimestampMixin
from app.models.associations import user_posts


class Post(Base, TimestampMixin):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    code: Mapped[str] = mapped_column(String(50), unique=True, comment="唯一编码，如 ceo、se（RuoYi post_code）")
    name: Mapped[str] = mapped_column(String(50), comment="岗位名称，如“项目经理”（RuoYi post_name）")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="同级排序，越小越靠前（RuoYi post_sort）")
    description: Mapped[str | None] = mapped_column(String(200), comment="岗位描述（RuoYi remark）")

    users = relationship(
        "User", secondary=user_posts, back_populates="posts", passive_deletes=True
    )  # 删岗位 → user_posts 交给 DB CASCADE
