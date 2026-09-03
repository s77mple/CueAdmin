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
        """按 id 查询并预载角色（get_user_detail 现算 role_ids 用；部门不回显，不预载）。"""
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )
        return result.scalars().first()

    async def get_for_update_with_roles(self, user_id: int) -> User | None:
        """带行级锁 + 预载角色（更新/删除用：admin 保护、角色关联比较）。"""
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
            .with_for_update()
        )
        return result.scalars().first()

    async def get_for_login(self, username: str) -> User | None:
        """登录用 — 预载角色及权限（权限码 + roles 回显都要），只查启用用户。"""
        stmt = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
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
        dept_ids: set[int] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PageData:
        """分页用户列表，支持按角色、启用状态、部门集合（含子孙）筛选。

        dept_ids 由 service 层用 collect_subtree_ids 展开好（dept_id → 该部门+子孙的
        id 集合）再传入；repo 只做 IN 过滤，不感知部门树的形状。
        """
        # 列表行要渲染「部门」列 + 「角色」tag 列 → 预载 department / roles 两个对象
        stmt = select(User).options(
            selectinload(User.roles), selectinload(User.department)
        )

        if role_id is not None:
            stmt = stmt.join(User.roles).where(Role.id == role_id)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if dept_ids:
            # 学 RuoYi：deptId 匹配「该部门 + 全部子孙部门」（若依靠 ancestors + find_in_set）
            stmt = stmt.where(User.department_id.in_(dept_ids))

        stmt = stmt.order_by(User.id.asc())
        return await paginate(self.session, stmt, page, page_size)
