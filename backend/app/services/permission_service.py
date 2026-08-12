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
from app.core.paginate import paginate
from app.core.logger import logger
from app.schemas.response import PageData


class PermissionService:
    """权限码管理业务逻辑。"""

    def __init__(self, db: AsyncSession, redis_client: aioredis.Redis | None = None):
        self.db = db
        self.redis = redis_client

    # ============================================================
    # 查询
    # ============================================================

    async def list_permissions(self, page: int = 1, page_size: int = 100) -> PageData:
        """分页返回权限（按 resource + action 排序）。权限码数量少，默认 page_size=100 一次返回全部。"""
        stmt = select(Permission).order_by(Permission.resource, Permission.action)
        return await paginate(self.db, stmt, page, page_size)

    async def get_permission_for_update(self, perm_id: int) -> Permission:
        """带行级锁获取权限。"""
        result = await self.db.execute(
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
        if (await self.db.execute(select(Permission).where(Permission.code == body.code))).scalars().first():
            raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")

        perm = Permission(
            code=body.code, name=body.name,
            resource=body.resource, action=body.action,
            description=body.description,
        )
        self.db.add(perm)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")
        await self.db.refresh(perm)
        return perm

    # ============================================================
    # 全量更新
    # ============================================================

    async def update_permission(self, perm_id: int, body) -> Permission:
        """PUT 全量更新 — code 变更时清除关联用户缓存。"""
        perm = await self.get_permission_for_update(perm_id)
        code_changed = False

        if body.code != perm.code:
            if (await self.db.execute(select(Permission).where(Permission.code == body.code))).scalars().first():
                raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")
            perm.code = body.code
            code_changed = True

        perm.name = body.name
        perm.resource = body.resource
        perm.action = body.action
        perm.description = body.description

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")

        if code_changed:
            await self._clear_perm_cache(perm_id)
        return perm

    # ============================================================
    # 部分更新
    # ============================================================

    async def patch_permission(self, perm_id: int, body) -> Permission:
        """PATCH 部分更新。"""
        perm = await self.get_permission_for_update(perm_id)
        data = body.model_dump(exclude_unset=True)
        code_changed = False

        if "code" in data:
            if data["code"] is None:
                raise BusinessException(ErrorCode.VALIDATION_ERROR, "code 不能为 null")
            if data["code"] != perm.code:
                if (await self.db.execute(select(Permission).where(Permission.code == data["code"]))).scalars().first():
                    raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")
                perm.code = data["code"]
                code_changed = True
        if "name" in data:
            if data["name"] is None:
                raise BusinessException(ErrorCode.VALIDATION_ERROR, "name 不能为 null")
            perm.name = data["name"]
        if "resource" in data:
            if data["resource"] is None:
                raise BusinessException(ErrorCode.VALIDATION_ERROR, "resource 不能为 null")
            perm.resource = data["resource"]
        if "action" in data:
            if data["action"] is None:
                raise BusinessException(ErrorCode.VALIDATION_ERROR, "action 不能为 null")
            perm.action = data["action"]
        if "description" in data:
            perm.description = data["description"]

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
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
        await self.db.delete(perm)              # 再删记录
        await self.db.commit()
        return "删除成功"

    # ============================================================
    # 私有 — 缓存清除
    # ============================================================

    async def _clear_perm_cache(self, perm_id: int):
        """权限变更后，清除所有关联用户的 Redis 权限缓存。

        查询路径：perm_id → role_permissions → user_roles → user_id
        """
        try:
            rows = (await self.db.execute(
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
