"""菜单数据访问 — 菜单表 + 树形查询。"""

from typing import Collection

from sqlalchemy import select

from app.system.models import Menu
from app.system.repositories.base import BaseRepository


class MenuRepository(BaseRepository):
    model = Menu

    async def list_menus(self) -> list[Menu]:
        """返回全部菜单（按 sort_order 排序，前端用 parent_id 转树）。"""
        result = await self.session.execute(
            select(Menu).order_by(Menu.sort_order, Menu.id)
        )
        return result.scalars().all()

    async def get_children(self, menu_id: int) -> list[Menu]:
        """查直接子菜单（带锁，删除时子菜单变顶级用）。"""
        result = await self.session.execute(
            select(Menu).where(Menu.parent_id == menu_id).with_for_update()
        )
        return result.scalars().all()

    async def get_parent_id(self, menu_id: int) -> int | None:
        """查父菜单 ID（循环检测沿父链遍历用）。"""
        result = await self.session.execute(
            select(Menu.parent_id).where(Menu.id == menu_id)
        )
        row = result.first()
        return row[0] if row else None

    async def get_by_ids(self, menu_ids: Collection[int]) -> list[Menu]:
        """按 ID 列表查询（父级补全 / 关联校验用）。"""
        result = await self.session.execute(
            select(Menu).where(Menu.id.in_(menu_ids))
        )
        return result.scalars().all()
