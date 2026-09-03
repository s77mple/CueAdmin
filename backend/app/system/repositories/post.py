"""岗位数据访问 — 岗位表查询。"""

from typing import Collection

from sqlalchemy import select, func

from app.core.paginate import paginate
from app.core.response import PageData
from app.system.models import Post
from app.system.models.associations import user_posts
from app.system.repositories.base import BaseRepository


class PostRepository(BaseRepository):
    model = Post

    async def list_posts(self, page: int = 1, page_size: int = 100) -> PageData:
        """分页岗位列表（按 sort_order 排序）。岗位数量少，默认 page_size=100 一次返回全部。"""
        stmt = select(Post).order_by(Post.sort_order, Post.id)
        return await paginate(self.session, stmt, page, page_size)

    async def list_all(self) -> list[Post]:
        """返回全部岗位（编辑用户的弹窗下拉选项，get_user_detail 用）。"""
        result = await self.session.execute(
            select(Post).order_by(Post.sort_order, Post.id)
        )
        return result.scalars().all()

    async def get_by_ids(self, post_ids: Collection[int]) -> list[Post]:
        """按 ID 列表查询（用户关联岗位时校验用）。"""
        result = await self.session.execute(
            select(Post).where(Post.id.in_(post_ids))
        )
        return result.scalars().all()

    async def count_users(self, post_id: int) -> int:
        """统计担任该岗位的用户数（删除时提示用）。"""
        result = await self.session.execute(
            select(func.count()).select_from(user_posts).where(user_posts.c.post_id == post_id)
        )
        return result.scalar() or 0
