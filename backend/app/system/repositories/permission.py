"""权限数据访问 — 权限表 + 关联表查询。"""

from typing import Collection

from sqlalchemy import select

from app.system.models import Permission
from app.system.models.associations import user_roles, role_permissions
from app.system.repositories.base import BaseRepository


class PermissionRepository(BaseRepository[Permission]):
    model = Permission

    async def list_permissions(self) -> list[Permission]:
        """返回全部权限（按 resource + action 排序，前端分组展示）。"""
        result = await self.session.execute(
            select(Permission).order_by(Permission.resource, Permission.action)
        )
        return list(result.scalars().all())

    async def get_by_codes(self, codes: Collection[str]) -> list[Permission]:
        """按权限 code 列表查询（角色关联校验用）。"""
        result = await self.session.execute(
            select(Permission).where(Permission.code.in_(codes))
        )
        return list(result.scalars().all())

    async def get_user_ids(self, perm_id: int) -> list[int]:
        """查拥有该权限的所有用户 ID（缓存清除用）。

        查询路径：perm_id → role_permissions → user_roles → user_id
        """
        result = await self.session.execute(
            select(user_roles.c.user_id)
            .join(role_permissions, role_permissions.c.role_id == user_roles.c.role_id)
            .where(role_permissions.c.permission_id == perm_id)
            .distinct()
        )
        return [row[0] for row in result.all()]
