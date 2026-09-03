"""岗位表 — 职位标签，与角色维度正交（学 RuoYi sys_post）。

RuoYi 模型：sys_user_role（用户↔角色）与 sys_user_post（用户↔岗位）是两条独立的 M2M，
角色管权限/数据范围，岗位只管"在公司担什么职"，岗位不参与权限判断、不影响登录。
删除岗位 → user_posts 关联交给 DB CASCADE（用户保留，只是没了这个岗位）。
"""

from sqlalchemy import String, BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.storage import Base, TimestampMixin
from app.system.models.associations import user_posts


class Post(Base, TimestampMixin):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    code: Mapped[str] = mapped_column(String(50), unique=True, comment="唯一编码，如 ceo、se（RuoYi post_code）")
    name: Mapped[str] = mapped_column(String(50), comment="岗位名称，如“项目经理”（RuoYi post_name）")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="同级排序，越小越靠前（RuoYi post_sort）")
    description: Mapped[str | None] = mapped_column(String(200), comment="岗位描述（RuoYi remark）")

    users = relationship("User", secondary=user_posts, back_populates="posts", passive_deletes=True)  # 删岗位 → user_posts 交给 DB CASCADE
