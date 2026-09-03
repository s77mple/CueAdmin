"""
岗位业务逻辑 — 岗位的 CRUD。

岗位是纯"职位标签"，比角色简单：
  - 不参与权限判断 → 无 is_system 保护、无关联用户权限缓存失效
  - 删除岗位 → user_posts 关联由 DB CASCADE，只在返回消息里告知受影响用户数

数据访问收口到 Repository，本层只做业务校验 + 事务提交。
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.system.models import Post
from app.core.exceptions import BusinessException, ErrorCode
from app.core.response import PageData
from app.system.repositories import PostRepository
from app.system.schemas.post import PostCreate, PostUpdate, PostItem


class PostService:
    """岗位管理业务逻辑。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.posts = PostRepository(session)

    # 查询

    async def list_posts(self, page: int = 1, page_size: int = 100) -> PageData[PostItem]:
        """分页岗位列表（按 sort_order 排序）。"""
        return await self.posts.list_posts(page, page_size)

    async def get_post_for_update(self, post_id: int) -> Post:
        """带行级锁获取岗位。"""
        post = await self.posts.get_for_update(post_id)
        if not post:
            raise BusinessException(ErrorCode.POST_NOT_FOUND, f"岗位不存在: {post_id}")
        return post

    async def get_post(self, post_id: int) -> Post:
        """查询单个岗位（单查回显用）。"""
        post = await self.posts.get(post_id)
        if not post:
            raise BusinessException(ErrorCode.POST_NOT_FOUND, f"岗位不存在: {post_id}")
        return post

    # 创建

    async def create_post(self, body: PostCreate) -> Post:
        """创建岗位 — 双重唯一性保护。"""
        if await self.posts.get_by_code(body.code):
            raise BusinessException(ErrorCode.POST_CODE_EXISTS, "岗位编码已存在")

        post = Post(
            code=body.code, name=body.name,
            sort_order=body.sort_order, description=body.description,
        )
        self.posts.add(post)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise BusinessException(ErrorCode.POST_CODE_EXISTS, "岗位编码已存在")
        await self.session.refresh(post)
        return post

    # 全量更新

    async def update_post(self, post_id: int, body: PostUpdate) -> Post:
        """PUT 全量更新 — code 不可修改。"""
        post = await self.get_post_for_update(post_id)

        post.name = body.name
        post.sort_order = body.sort_order
        post.description = body.description

        await self.session.commit()
        return post

    # 删除

    async def delete_post(self, post_id: int) -> str:
        """删除岗位 — user_posts 关联交给 DB CASCADE，消息告知受影响用户数。"""
        post = await self.get_post_for_update(post_id)

        user_count = await self.posts.count_users(post_id)

        await self.posts.delete(post)
        await self.session.commit()

        if user_count > 0:
            return f"已删除，{user_count} 个用户不再担任该岗位"
        return "删除成功"
