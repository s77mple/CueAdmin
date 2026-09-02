"""角色数据访问 — 角色表 + 关联表查询。"""

from typing import Collection

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.paginate import paginate
from app.core.response import PageData
from app.system.models import Role
from app.system.models.associations import user_roles
from app.system.repositories.base import BaseRepository


class RoleRepository(BaseRepository):
    model = Role

    async def get_for_update_with_relations(self, role_id: int) -> Role | None:
        """带行级锁 + 预加载权限和菜单（更新/删除用）。"""
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.permissions), selectinload(Role.menus))
            .where(Role.id == role_id)
            .with_for_update()
        )
        return result.scalars().first()

    async def get_with_relations(self, role_id: int) -> Role | None:
        """按 id 查询并预加载权限和菜单（单查回显用，不加锁）。"""
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.permissions), selectinload(Role.menus))
            .where(Role.id == role_id)
        )
        return result.scalars().first()

    async def list_roles(self, page: int = 1, page_size: int = 100) -> PageData:
        """分页返回角色（预加载权限和菜单）。角色数量少，默认一次返回全部。"""
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions), selectinload(Role.menus))
            .order_by(Role.id.asc())
        )
        return await paginate(self.session, stmt, page, page_size)

    async def get_by_ids(self, role_ids: Collection[int]) -> list[Role]:
        """按 ID 列表查询（角色关联校验用）。"""
        result = await self.session.execute(
            select(Role).where(Role.id.in_(role_ids))
        )
        return result.scalars().all()

    async def get_user_ids(self, role_id: int) -> list[int]:
        """查拥有该角色的所有用户 ID（缓存清除用）。"""
        result = await self.session.execute(
            select(user_roles.c.user_id).where(user_roles.c.role_id == role_id)
        )
        return result.scalars().all()
