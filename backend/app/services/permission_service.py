"""
权限码业务逻辑 — 权限的 CRUD + 关联用户缓存主动失效。

从 api/permissions.py 提取而来。
"""

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Permission
from app.models.associations import user_roles, role_permissions
from app.core.exceptions import BusinessException, ErrorCode
from app.core.logger import logger


class PermissionService:
    """权限码管理业务逻辑。"""

    def __init__(self, session: AsyncSession, redis_client: aioredis.Redis | None = None):
        self.session = session
        self.redis = redis_client

    # ============================================================
    # 查询
    # ============================================================

    async def list_permissions(self) -> list[Permission]:
        """返回全部权限（按 resource + action 排序）。权限码是固定枚举，一次全量返回，前端分组展示。"""
        result = await self.session.execute(
            select(Permission).order_by(Permission.resource, Permission.action).limit(500)
        )
        return list(result.scalars().all())

    async def get_permission_for_update(self, perm_id: int) -> Permission:
        """带行级锁获取权限。"""
        result = await self.session.execute(
            select(Permission).where(Permission.id == perm_id).with_for_update()
        )
        perm = result.scalars().first()
        if not perm:
            raise BusinessException(ErrorCode.PERM_NOT_FOUND, f"权限不存在: {perm_id}")
        return perm

    # ============================================================
    # 创建
    # ============================================================

    async def create_permission(self, body) -> Permission:
        """创建权限 — 双重唯一性保护。"""
        if (await self.session.execute(select(Permission).where(Permission.code == body.code))).scalars().first():
            raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")

        perm = Permission(
            code=body.code, name=body.name,
            resource=body.resource, action=body.action,
            description=body.description,
        )
        self.session.add(perm)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")
        await self.session.refresh(perm)
        return perm

    # ============================================================
    # 全量更新
    # ============================================================

    async def update_permission(self, perm_id: int, body) -> Permission:
        """PUT 全量更新 — code 变更时清除关联用户缓存。"""
        perm = await self.get_permission_for_update(perm_id)
        code_changed = False

        if body.code != perm.code:
            if (await self.session.execute(select(Permission).where(Permission.code == body.code))).scalars().first():
                raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")
            perm.code = body.code
            code_changed = True

        perm.name = body.name
        perm.resource = body.resource
        perm.action = body.action
        perm.description = body.description

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")

        if code_changed:
            await self._clear_perm_cache(perm_id)
        return perm

    # ============================================================
    # 删除
    # ============================================================

    async def delete_permission(self, perm_id: int) -> str:
        """删除权限 — 删前清除关联用户缓存。"""
        perm = await self.get_permission_for_update(perm_id)

        await self._clear_perm_cache(perm_id)  # 先清缓存
        await self.session.delete(perm)              # 再删记录
        await self.session.commit()
        return "删除成功"

    # ============================================================
    # 私有 — 缓存清除
    # ============================================================

    async def _clear_perm_cache(self, perm_id: int):
        """权限变更后，清除所有关联用户的 Redis 权限缓存。

        查询路径：perm_id → role_permissions → user_roles → user_id
        """
        try:
            rows = (await self.session.execute(
                select(user_roles.c.user_id)
                .join(role_permissions, role_permissions.c.role_id == user_roles.c.role_id)
                .where(role_permissions.c.permission_id == perm_id)
                .distinct()
            )).all()
        except SQLAlchemyError:
            logger.warning("查询权限关联用户失败，跳过缓存清除")
            return

        for (uid,) in rows:
            if self.redis:
                try:
                    await self.redis.delete(f"perm:{uid}")
                except aioredis.RedisError:
                    pass
        if rows:
            logger.info("权限变更，已清除 {} 个用户缓存", len(rows))
