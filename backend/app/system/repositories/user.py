"""用户数据访问 — 用户表的查询方法。"""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.paginate import paginate
from app.core.response import PageData
from app.system.models import User, Role
from app.system.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    model = User

    async def get_by_username(self, username: str, exclude_user_id: int | None = None) -> User | None:
        """按用户名查询（唯一性校验用，编辑时可排除自己）。"""
        stmt = select(User).where(User.username == username)
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def count_active_admins(self) -> int:
        """统计启用状态的 admin 用户数（最后管理员保护用）。"""
        result = await self.session.execute(
            select(User).join(User.roles).where(
                Role.code == "admin", User.is_active == True
            ).with_for_update()
        )
        return len(result.scalars().all())

    async def get_with_roles(self, user_id: int) -> User | None:
        """按 id 查询并预加载角色 + 部门（commit 后重新查询用）。"""
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles), selectinload(User.department))
            .where(User.id == user_id)
        )
        return result.scalars().first()

    async def get_for_update_with_roles(self, user_id: int) -> User | None:
        """带行级锁 + 预加载角色 + 部门（更新/删除用）。"""
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles), selectinload(User.department))
            .where(User.id == user_id)
            .with_for_update()
        )
        return result.scalars().first()

    async def get_for_login(self, username: str) -> User | None:
        """登录用 — 预加载角色、权限和部门，只查启用中的用户。"""
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.department),
            )
            .where(User.username == username, User.is_active == True)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active(self, user_id: int) -> User | None:
        """查询启用中的用户（refresh 令牌校验用）。"""
        result = await self.session.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        return result.scalars().first()

    async def list_users(
        self,
        role_id: int | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PageData:
        """分页用户列表，支持按角色和启用状态筛选。"""
        stmt = select(User).options(
            selectinload(User.roles), selectinload(User.department)
        )

        if role_id is not None:
            stmt = stmt.join(User.roles).where(Role.id == role_id)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        stmt = stmt.order_by(User.id.asc())
        return await paginate(self.session, stmt, page, page_size)
